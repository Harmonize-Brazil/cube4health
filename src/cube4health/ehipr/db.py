# # inbuilt libraries
# from typing import List, Optional

# # third-party libraries
# #import psycopg2
# import numpy as np
# from tqdm import tqdm
# from shapely.wkb import dumps
# from geopandas import GeoDataFrame
# from psycopg2 import (
#     sql,
#     extras,
#     connect,
#     extensions
# )
# #from psycopg2 import sql
# #from psycopg2.extras import execute_values
# from concurrent.futures import (
#     as_completed,
#     ThreadPoolExecutor
# )

# # custom functions
# from .config import CPU_COUNT
# from .utils import chunk_list
# from cube4health.edpu.utils import (
#     get_ip_container_db,
#     get_ports_container_db
# )

# def _insert_data(gdf: GeoDataFrame, 
#                  name: str, 
#                  db_columns: List[str],
#                  schema: str, 
#                  db_params: dict) -> bool:

#     geometry_col = "geometry"
#     columns_no_geom = [col for col in db_columns if col != geometry_col]

#     try:
#         conn = connect(**db_params)
#         cursor = conn.cursor()

#         records = []
#         for row in gdf.itertuples(index=False):
#             values = list(row[:-1])
#             geometry_wkb = dumps(row[-1], srid=gdf.crs.to_epsg())
#             values.append(geometry_wkb)
#             records.append(tuple(values))

#         insert_query = sql.SQL("""
#             INSERT INTO {}.{} ({})
#             VALUES %s;
#         """).format(
#             sql.Identifier(schema),
#             sql.Identifier(name),
#             sql.SQL(', ').join(map(sql.Identifier, db_columns))
#         )

#         extras.execute_values(cursor, insert_query, records)
#         conn.commit()

#         cursor.close()
#         conn.close()
#         return True
#     except Exception as e:
#         print(f"[ERROR] Falha ao inserir dados: {e}")
#         try:
#             conn.rollback()
#             conn.close()
#         except:
#             pass
#         return False


# inbuilt libraries
from typing import List, Optional

# third-party libraries
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
from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor
)

# custom functions
from cube4health.ehipr.config import CPU_COUNT
from cube4health.ehipr.utils import chunk_list
from cube4health.edpu.utils import (
    get_ip_container_db,
    get_ports_container_db
)

def _insert_data(gdf: GeoDataFrame, 
                 name: str, 
                 db_columns: List[str],
                 schema: str, 
                 db_params: dict) -> bool:

    geometry_col = "geometry"
    columns_no_geom = [col for col in db_columns if col != geometry_col]

    try:
        conn = connect(**db_params)
        cursor = conn.cursor()

        records = []
        for row in gdf.itertuples(index=False):
            # ✅ converte numpy types para Python nativo
            values = [v.item() if hasattr(v, "item") else v for v in row[:-1]]

            geometry_wkb = dumps(row[-1], srid=gdf.crs.to_epsg())
            values.append(geometry_wkb)
            records.append(tuple(values))

        insert_query = sql.SQL("""
            INSERT INTO {}.{} ({})
            VALUES %s;
        """).format(
            sql.Identifier(schema),
            sql.Identifier(name),
            sql.SQL(', ').join(map(sql.Identifier, db_columns))
        )

        extras.execute_values(cursor, insert_query, records)
        conn.commit()

        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Falha ao inserir dados: {e}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False


def save_data_db(gdf: GeoDataFrame, 
                 name: str, 
                 schema: str, 
                 db_columns = List[str],
                 hostname: Optional[str] = 'localhost',
                 port : Optional[str] = '5432',
                 db: Optional[str] = 'harmonize', 
                 user: Optional[str] = 'postgres', 
                 password: Optional[str] = 'postgres',
                 replace_table: Optional[bool] = False) -> bool:

    host = hostname if hostname != 'localhost' else get_ip_container_db()
    port = port if port != 5432 else get_ports_container_db()

    try:
        # Conexão inicial apenas para setup
        conn = connect(
            host=host,
            port=port,
            dbname=db,
            user=user,
            password=password
        )
        cursor = conn.cursor()

        # Criar extensão PostGIS
        cursor.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
        conn.commit()

        # Verifica se schema existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.schemata
                WHERE schema_name = %s
            );
        """, (schema,))
        schema_exists = cursor.fetchone()[0]

        if not schema_exists:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            conn.commit()

        # Drop table se necessário
        if replace_table:
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, name)))
            conn.commit()

        # Verifica se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            );
        """, (schema, name))
        table_exists = cursor.fetchone()[0]

        # Detecta campo temporal
        temporal_date_fields = ["epiweek_start_date", "month_start_date", "year_start_date"]
        temporal_date_field = next((field for field in temporal_date_fields if field in db_columns), None)

        temporal_fields = ["epiweek_number", "month_number", "year_number"]
        temporal_field = next((field for field in temporal_fields if field in db_columns), None)

        # ✅ Substitui valores NaN por 0
        if temporal_field in gdf.columns:
            gdf[temporal_field] = gdf[temporal_field].fillna(0)

        if "value" in gdf.columns:
            gdf["value"] = gdf["value"].fillna(0)

        # Casts para tipos seguros
        if temporal_field in gdf.columns:
            gdf[temporal_field] = gdf[temporal_field].astype(int)
        if "value" in gdf.columns:
            gdf["value"] = gdf["value"].astype(float)

        if not table_exists:
            mapeamento_coluna_para_tipo_logico = {
                temporal_date_field: "date",
                "geometry": "geom"
            }

            tipo_por_coluna = {
                "code_mun": "VARCHAR(8) NOT NULL",
                "name_mun": "VARCHAR(50) NOT NULL",
                "uf_mun": "VARCHAR(2) NOT NULL",
                "data_source": "VARCHAR(50) NOT NULL",
                "name_indicator": "VARCHAR(50) NOT NULL",
                temporal_field: "INTEGER NOT NULL",
                "time_agg": "VARCHAR(20) NOT NULL",
                "spatial_agg": "VARCHAR(20) NOT NULL",
                "value": "NUMERIC(10, 2) NOT NULL",
                "date": "TIMESTAMP WITH TIME ZONE NOT NULL",
                "geom": "geometry(MULTIPOLYGON, 4326) NOT NULL"
            }

            campos_formatados = [("id", "SERIAL PRIMARY KEY")]
            for col in db_columns:
                tipo_logico = mapeamento_coluna_para_tipo_logico.get(col, col)
                tipo_sql = tipo_por_coluna[tipo_logico]
                campos_formatados.append((col, tipo_sql))

            campos_sql = sql.SQL(", ").join([
                sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(tipo))
                for col, tipo in campos_formatados
            ])

            create_table_query = sql.SQL("""
                CREATE TABLE {}.{} (
                    {}
                );
            """).format(
                sql.Identifier(schema),
                sql.Identifier(name),
                campos_sql
            )

            cursor.execute(create_table_query)
            conn.commit()

        # Parâmetros de conexão para cada thread
        db_params = dict(
            host=host,
            port=port,
            dbname=db,
            user=user,
            password=password
        )

        # Inserção em chunks
        all_saved = []
        max_rows = 10000
        gdfs = list(chunk_list(list_to_chunk=gdf, 
                                nchunks=len(gdf)//max_rows)) if len(gdf) > max_rows else [gdf]

        with ThreadPoolExecutor(max_workers=CPU_COUNT) as executor:
            futures = [executor.submit(
                _insert_data, gdf, name, db_columns, schema, db_params
            ) for gdf in gdfs]

            for index, future in enumerate(tqdm(as_completed(futures), desc="Processing chunks...")):
                all_saved.append(future.result())

        cursor.close()
        conn.close()
        if all(all_saved):
            return True

    except Exception as e:
        print("[ERROR]", str(e))
        try:
            if conn:
                conn.rollback()
                conn.close()
        except:
            pass
        return False
