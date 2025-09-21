import os
import geopandas as gpd
import pandas as pd
from glob import glob
from natsort import natsorted  # Correct order of filenames
from sqlalchemy import create_engine, text
from tqdm import tqdm
from psycopg2.extras import execute_values
from shapely.wkb import dumps as wkb_dumps


def process_climate_postgres(geojson_path, name_db, table_new_db=None, schema_db="climate", host_db="localhost", port_db=5432, user_db="postgres", pass_db="postgres", overwrite=False):
    """
    Populate a PostgreSQL/PostGIS table from GeoJSON files with temporal and spatial aggregation.

    The function reads GeoJSON files containing climate indicators (with either "epiweek" or "month" as the temporal aggregation unit) and inserts them into a PostgreSQL/PostGIS database table.
    It automatically creates the schema (if not existing), ensures PostGIS is enabled, and handles insertion with overwrite control.

    Parameters
    ----------
    geojson_path : str
        Path to the main directory containing the GeoJSON files. The directory name must contain either "epiweek" or "month" to define the temporal aggregation.
    name_db : str
        Name of the PostgreSQL database.
    table_new_db : str, optional
        Name of the new table to be created in PostgreSQL. If not provided, the last directory name in `geojson_path` is used. Default is None.
    schema_db : str, optional
        Name of the schema to use. Default is 'climate'.
    host_db : str, optional
        Host name or IP address of the PostgreSQL server. Default is 'localhost'.
    port_db : int, optional
        Port number of the PostgreSQL server. Default is 5432.
    user_db : str, optional
        Username for the PostgreSQL database. Default is 'postgres'.
    pass_db : str, optional
        Password for the PostgreSQL database. Default is 'postgres'.
    overwrite : bool, optional
        If True, clears the table before insertion, replacing existing data.
        If False, appends new data without removing existing records. Default is False.

    Raises
    ------
    ValueError
        If `geojson_path` or `name_db` are not defined.
        If the directory name does not contain "epiweek" or "month".
    FileNotFoundError
        If the "shapefiles" subdirectory does not exist inside `geojson_path`.

    Returns
    -------
    None
        The function does not return a value. Data are inserted directly into the PostgreSQL/PostGIS database.

    Notes
    -----
    - PostGIS extension is created and assigned to the schema if not already present.
    - Geometry column is always stored as `geom geometry(Polygon, 4326)`.

    Examples
    --------
    Populate PostgreSQL with monthly climate indicators:

    >>> from cube4health.eclimpr.utils_bd import process_climate_postgres

    >>> process_climate_postgres(
    ...     geojson_path="/path/to/temp_max_NE_mun_month_era5land",
    ...     name_db="harmonize",
    ...     table_new_db="temp_max_NE_mun_month_era5land",
    ...     schema_db="climate",
    ...     host_db="localhost",
    ...     port_db=5432,
    ...     user_db="postgres",
    ...     pass_db="postgres",
    ...     overwrite=True
    ... )
    """

    if None in [geojson_path, name_db]:
        raise ValueError("Error: geojson_path and name_db must be defined.")

    if "epiweek" in geojson_path.lower():
        temporal_unit = "epiweek"
    elif "month" in geojson_path.lower():
        temporal_unit = "month"
    else:
        raise ValueError("The directory name must contain 'epiweek' or 'month' to identify temporal aggregation.")

    # If table name is not provided, use the last directory in the path
    if not table_new_db:
        table_new_db = os.path.basename(os.path.normpath(geojson_path))

    # Always lowercase the table name
    table_new_db = table_new_db.lower()

    # Create SQLAlchemy engine
    engine = create_engine(
        f"postgresql+psycopg2://{user_db}:{pass_db}@{host_db}:{port_db}/{name_db}"
    )

    temporal_fields = ""

    with engine.begin() as connection:
        # Create schema and PostGIS extension if necessary
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_db};"))
        
        if temporal_unit == "epiweek":
            temporal_fields = """
                epiweek_number VARCHAR(2) NOT NULL,
                epiweek_start_date TIMESTAMP NOT NULL,
            """
        elif temporal_unit == "month":
            temporal_fields = """
                month_number VARCHAR(2) NOT NULL,
                month_start_date TIMESTAMP NOT NULL,
            """

        # Create table
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {schema_db}.{table_new_db} (
            gid SERIAL PRIMARY KEY,
            cod_mun VARCHAR(8) NOT NULL,
            name_mun VARCHAR(100) NOT NULL,
            uf_mun VARCHAR(2) NOT NULL,
            data_source VARCHAR(50) NOT NULL,
            name_indicator VARCHAR(40) NOT NULL,
            {temporal_fields}
            time_agg VARCHAR(20) NOT NULL,
            spatial_agg VARCHAR(20) NOT NULL,
            value NUMERIC(10, 4) NOT NULL,
            geom geometry(MULTIPOLYGON, 4326) NOT NULL
        );
        """

        connection.execute(text(create_query))

        # Clear existing data, only if overwrite=True
        if overwrite:
            print(f"\nATTENTION: clearing table {schema_db}.{table_new_db} ...\n")
            connection.execute(text(f"DELETE FROM {schema_db}.{table_new_db};"))

    print("\nPopulating database with Shapefile values ...")
    records = []

    # List all geojsons files in the directory shapefiles
    geojson_paths = os.path.join(geojson_path, "shapefiles")

    if not os.path.exists(geojson_paths):
        raise FileNotFoundError(f"The directory {geojson_paths} does not exist.")

    geojson_files = glob(os.path.join(geojson_paths, "**", "*.geojson"), recursive=True)
    geojson_files = natsorted(geojson_files)

    if not geojson_files:
        print("No .geojson files were found.")
        return

    for file in geojson_files:
        study_area_gjson = gpd.read_file(file).to_crs("EPSG:4326")

        for _, row in tqdm(study_area_gjson.iterrows(), total=len(study_area_gjson), desc=f"Processing {os.path.basename(file)}"):
            if pd.isna(row.get("cod_mun")):
                continue

            try:
                value = float(row["value"])
            except (ValueError, TypeError, KeyError):
                continue

            if pd.isna(value):
                continue

            record = {
                "cod_mun": row["cod_mun"],
                "name_mun": row["name_mun"],
                "uf_mun": row["uf_mun"],
                "data_source": row["data_source"],
                "name_indicator": row["name_indicator"],
                "time_agg": row["time_agg"],
                "spatial_agg": row["spatial_agg"],
                "value": value,
                "geometry": row["geometry"]
            }

            if temporal_unit == "epiweek":
                record["epiweek_number"] = row["epiweek_number"]
                record["epiweek_start_date"] = pd.to_datetime(row["epiweek_start_date"], errors="coerce")
            elif temporal_unit == "month":
                record["month_number"] = row["month_number"]
                record["month_start_date"] = pd.to_datetime(row["month_start_date"], errors="coerce")

            records.append(record)

    if records:
        # mount gdf with CRS 4326
        gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
        if gdf.crs is None:
            gdf = gdf.set_crs(4326, allow_override=True)

        # Define columns according to the temporal unit (keeping names compatible with your CREATE TABLE)
        if temporal_unit == "epiweek": # epiweek
            db_columns = [
                "cod_mun","name_mun","uf_mun","data_source","name_indicator",
                "epiweek_number","epiweek_start_date","time_agg","spatial_agg",
                "value","geom"
            ]
        else:  # month
            db_columns = [
                "cod_mun","name_mun","uf_mun","data_source","name_indicator",
                "month_number","month_start_date","time_agg","spatial_agg",
                "value","geom"
            ]

        # Reorder/rename to match db_columns: your table uses 'geom' (not 'geometry')
        gdf = gdf.rename(columns={"geometry": "geom"})
        gdf = gdf[db_columns]

        # Prepare records: last positions will be WKB of geometry
        records_wkb = []
        for row in gdf.itertuples(index=False, name=None):
            *attrs, geom = row
            if geom is None:
                wkb = None
            else:
                # WKB bytes; SRID handled on the database side via ST_GeomFromWKB(..., 4326)
                wkb = wkb_dumps(geom)
            records_wkb.append(tuple(attrs + [wkb]))

        # Assembles SQL with placeholders; converts geom to database and forces Multi
        cols_sql = ", ".join(db_columns)
        values_sql = "VALUES %s"
        insert_sql = f"""
            INSERT INTO {schema_db}.{table_new_db} ({cols_sql})
            {values_sql}
        """

        # Template: all columns as %s except the last one (geom) wrapped by ST_*
        ncols = len(db_columns)
        template_placeholders = ",".join(["%s"] * (ncols - 1))
        geom_expr = "ST_Multi(ST_GeomFromWKB(%s, 4326))"
        template = f"({template_placeholders}, {geom_expr})"

        # Use SQLAlchemy (psycopg2) raw connection for execute_values
        raw_conn = engine.raw_connection()
        try:
            cur = raw_conn.cursor()
            try:
                execute_values(
                    cur,
                    insert_sql,
                    records_wkb,
                    template=template,
                    page_size=10000
                )
            finally:
                cur.close()
            raw_conn.commit()
        finally:
            raw_conn.close()

    print(f"\nDatabase {table_new_db} created successfully!\n")
    print(f"\nInsertion completed: {len(records)} records added to the table '{schema_db}.{table_new_db}'\n")

