# inbuilt libraries
from typing import Optional

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
from ..utils import chunk_list
from src.cube4health.edpu.utils import (
    get_ip_container_db,
    get_ports_container_db
)

def _insert_data(gdf: GeoDataFrame, 
                 name: str, 
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

    records = []

    try:
        for row in gdf.itertuples(index=False):
            geometry_wkb = dumps(row[6], srid=gdf.crs.to_epsg())
            records.append((row[0], row[1], row[2], row[3], row[4], row[5], geometry_wkb))

            insert_query = sql.SQL("""
                INSERT INTO {}
                (cod, date, name, agg, agg_time, value, geom)
                VALUES %s;
            """).format(sql.Identifier(schema, name))

            extras.execute_values(cursor, insert_query, records)
            conn.commit()
        return True
    except Exception as e:
        print(str(e))
        return False


def save_data_db(gdf: GeoDataFrame, 
                 name: str, 
                 schema: str, 
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
            # Defines the SQL command to create the table
            create_table_query = sql.SQL("""
                CREATE TABLE {} (
                    id SERIAL PRIMARY KEY,
                    cod VARCHAR(8) NOT NULL,
                    date TIMESTAMP WITH TIME ZONE NOT NULL,
                    name VARCHAR(15) NOT NULL,
                    agg VARCHAR(15) NOT NULL,
                    agg_time VARCHAR(15) NOT NULL,
                    value NUMERIC(10, 2) NOT NULL,
                    geom geometry(MULTIPOLYGON, 4326) NOT NULL
                );
            """).format(sql.Identifier(schema, name))

            # Executes the SQL command to create the table
            cursor.execute(create_table_query)
            conn.commit()

        # Splits the GeoDataFrame into chunks and inserts in the database in parallel
        all_saved = []

        max_rows = 10000
        gdfs = list(chunk_list(list_to_chunk=gdf, 
                                nchunks=len(gdf)//max_rows)) if len(gdf) > max_rows else [gdf]

        with ThreadPoolExecutor(max_workers=10) as executor:

            futures = [executor.submit(_insert_data, 
                                        gdf, name, schema, 
                                        conn, cursor) for gdf in gdfs]

            for index, future in enumerate(tqdm(as_completed(futures), desc="Processing chunks...")):
                all_saved.append(future.result())

        # Close cursor
        cursor.close()
        conn.close()
        if all(all_saved):
            return True
    except Exception as e:
        print(str(e))
        return False
