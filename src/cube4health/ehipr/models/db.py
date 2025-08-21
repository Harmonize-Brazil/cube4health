# inbuilt libraries
from typing import List, Optional

# third-party libraries
#import psycopg2
import numpy as np
from tqdm import tqdm
from shapely.wkb import dumps
from geopandas import GeoDataFrame
from psycopg2 import (
    sql,
    extras,
    connect,
    extensions
)
#from psycopg2 import sql
#from psycopg2.extras import execute_values
from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor
)

# custom functions
from ..config import CPU_COUNT
from ..utils import chunk_list
from src.cube4health.edpu.utils import (
    get_ip_container_db,
    get_ports_container_db
)

def _insert_data(gdf: GeoDataFrame, 
                 name: str, 
                 db_columns: List[str],
                 schema: str, 
                 conn: connect,
                 cursor: extensions.cursor) -> bool:

    """
        Saves GeoDataFrame to database

    Parameters
    ----------
        gdf : GeoDataFrame
            GeoDataFrame to save
        name : str
            Name of table
        schema : str
            Schema name
        conn : psycopg2.connect
            Connection to database

    Returns
    -------
        Boolean value of success
    """

    # Nome da coluna de geometria
    geometry_col = "geometry"

    # Remove a geometria da lista para processá-la separadamente (como WKB)
    columns_no_geom = [col for col in db_columns if col != geometry_col]

    try:

        # Converte as linhas em tuplas com geometria como WKB
        records = []

        for row in gdf.itertuples(index=False):
            values = list(row[:-1])  # Todos exceto geometria
            geometry_wkb = dumps(row[-1], srid=gdf.crs.to_epsg())  # Última coluna = geometria
            values.append(geometry_wkb)
            records.append(tuple(values))

        # Monta a query dinamicamente com base em db_columns
        insert_query = sql.SQL("""
            INSERT INTO {}.{} ({})
            VALUES %s;
        """).format(
            sql.Identifier(schema),
            sql.Identifier(name),
            sql.SQL(', ').join(map(sql.Identifier, db_columns))
        )

        # Executa o batch insert
        extras.execute_values(cursor, insert_query, records)
        conn.commit()

        return True
    except Exception as e:
        print(f"[ERROR] Falha ao inserir dados: {e}")
        conn.rollback()
        return False


def save_data_db(gdf: GeoDataFrame, 
                 name: str, 
                 schema: str, 
                 db_columns = List[str],
                 hostname: Optional[str] = 'localhost',
                 port : Optional[int] = 5432,
                 db: Optional[str] = 'harmonize', 
                 user: Optional[str] = 'postgres', 
                 password: Optional[str] = 'postgres',
                 replace_table: Optional[bool] = False) -> bool:

    """
        Saves GeoDataFrame to database

    Parameters
    ----------
        gdf : GeoDataFrame
            GeoDataFrame to save
        name : str
            Name of table
        schema : str
            Schema name
        hostname : Optional[str]
            Hostname for server with collections files, default localhost
        port : Optional[int]
            Port for server with collections files, default 5432
        db : Optional[str]
            Database name, default 'harmonize'
        user : Optional[str]
            User name, default 'postgres'
        password : Optional[str]
            Password, default 'postgres'
        replace_table : Optional[bool]
            Replace table if exists, default False

    Returns
    -------
        Boolean value indicating if the data was stored.
    """

    host = hostname if hostname != 'localhost' else get_ip_container_db()
    port = port if port != 5432 else get_ports_container_db()

    try:
        # Make connection with database
        conn = connect(
            host=host,
            port=port,
            dbname=db,
            user=user,
            password=password
        )

        # Create cursor
        cursor = conn.cursor()

        # Create postgis extension
        cursor.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
        conn.commit()

        # verifies if the schema exists in the database
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.schemata
                WHERE schema_name = %s
            );
        """, (schema,))
        schema_exists = cursor.fetchone()[0]

        # If the schema doesn't exist, create it
        if not schema_exists:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            conn.commit()

        # Defines the full table name
        full_table_name = f'"{schema}"."{name}"'

        # Drop table if it exists and the 'replace_table' flag is True
        if replace_table:
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, name)))
            conn.commit()

        # Verifies if the table exists in the database
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            );
        """, (schema, name))

        table_exists = cursor.fetchone()[0]

        if not table_exists:

            # Mapeia campos alternativos para nomes lógicos que têm tipo definido
            mapeamento_coluna_para_tipo_logico = {
                "epiweek_start_date": "date",  # usa o tipo de date
                "geometry": "geom"             # usa o tipo definido de geom
            }

            # Tipos SQL por campo lógico
            tipo_por_coluna = {
                "code_mun": "VARCHAR(8) NOT NULL",
                "name_mun": "VARCHAR(50) NOT NULL",
                "uf_mun": "VARCHAR(2) NOT NULL",
                "data_source": "VARCHAR(50) NOT NULL",
                "name_indicator": "VARCHAR(50) NOT NULL",
                "epiweek_number": "INTEGER NOT NULL",
                "time_agg": "VARCHAR(20) NOT NULL",
                "spatial_agg": "VARCHAR(20) NOT NULL",
                "value": "NUMERIC(10, 2) NOT NULL",
                "date": "TIMESTAMP WITH TIME ZONE NOT NULL",
                "geom": "geometry(MULTIPOLYGON, 4326) NOT NULL"
            }

            # Monta os campos da tabela
            campos_formatados = [("id", "SERIAL PRIMARY KEY")]

            for col in db_columns:
                tipo_logico = mapeamento_coluna_para_tipo_logico.get(col, col)
                tipo_sql = tipo_por_coluna[tipo_logico]
                campos_formatados.append((col, tipo_sql))

            # Cria o SQL seguro com psycopg2
            campos_sql = sql.SQL(", ").join([
                sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(tipo))
                for col, tipo in campos_formatados
            ])

            # Cria a query final
            create_table_query = sql.SQL("""
                CREATE TABLE {}.{} (
                    {}
                );
            """).format(
                sql.Identifier(schema),
                sql.Identifier(name),
                campos_sql
            )

            # Executes the SQL command to create the table
            cursor.execute(create_table_query)
            conn.commit()

        # Splits the GeoDataFrame into chunks and inserts in the database in parallel
        all_saved = []

        max_rows = 10000
        gdfs = list(chunk_list(list_to_chunk=gdf, 
                                nchunks=len(gdf)//max_rows)) if len(gdf) > max_rows else [gdf]

        with ThreadPoolExecutor(max_workers=CPU_COUNT) as executor:

            futures = [executor.submit(_insert_data, 
                                        gdf, name, db_columns, schema, 
                                        conn, cursor) for gdf in gdfs]

            for index, future in enumerate(tqdm(as_completed(futures), desc="Processing chunks...")):
                all_saved.append(future.result())

        # Close cursor
        cursor.close()
        conn.close()
        if all(all_saved):
            return True
    except Exception as e:
        print("[ERROR]", str(e))
        try:
            if conn:
                conn.rollback()
        except:
            pass
        return False

