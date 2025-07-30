import os
import geopandas as gpd
import pandas as pd
from glob import glob
from natsort import natsorted  # Correct order of filenames
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry # to use .to_postgis()
from tqdm import tqdm


# def process_climate_postgres(indicator_name, shapefile_path, name_db, table_new_db,ncol_epiweek=4, schema_db="climate", host_db="localhost", port_db=5432, user_db="postgres", pass_db="postgres", agg_spat_name="municipality", agg_time_name="epi_week", overwrite=False):
#     """
#     Populate PostgreSQL table from shapefile with temporal and spatial aggregation.

#     Parameters
#     ----------
#     indicator_name : str
#         Name of the indicator to be inserted in the table.
#     shapefile_path : str
#         Path to the input shapefile of the interesting area.
#     name_db : str
#         Name of the PostgreSQL database.
#     table_new_db : str
#         Name of the new table to be created in PostgreSQL.
#     ncol_epiweek : int, optional
#         The number in Attribute Table that starts column with pattern 'w_YYYYMMDD' start. Default is 4.
#     schema_db : str, optional
#         Name of the schema to use. Default is 'climate'.
#     host_db : str, optional
#         Host name or IP of the PostgreSQL server. Default is 'localhost'.
#     port_db : int, optional
#         Port number of the PostgreSQL server. Default is 5432.
#     user_db : str, optional
#         Username for the database. Default is 'postgres'.
#     pass_db : str, optional
#         Password for the database. Default is 'postgres'.
#     agg_spat_name : str, optional
#         Spatial aggregation name. Default is 'municipality'.
#     agg_time_name : str, optional
#         Temporal aggregation name. Default is 'epi_week'.
#     overwrite : bool, optional
#         If True, allows delete the table before, and replace existing data. Default is False, and maintaining existing data.

#     Raises
#     ------
#     ValueError
#         If any required parameters are not defined.

#     Returns
#     -------
#     None
#     """

#     if None in [shapefile_path, name_db, table_new_db, indicator_name]:
#         raise ValueError("Error: shapefile_path, name_db, table_new_db, and indicator_name must be defined.")

#     # Load shapefile
#     study_area_shp = gpd.read_file(shapefile_path)
#     study_area_shp = study_area_shp.to_crs("EPSG:4326")

#     # Lowercase table name
#     table_new_db = table_new_db.lower()

#     # Create SQLAlchemy engine
#     engine = create_engine(
#         f"postgresql+psycopg2://{user_db}:{pass_db}@{host_db}:{port_db}/{name_db}"
#     )

#     with engine.begin() as connection:
#         # Create schema and PostGIS extension if necessary
#         connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_db};"))
#         connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS postgis SCHEMA {schema_db};"))
#         connection.execute(text("UPDATE pg_extension SET extrelocatable = TRUE WHERE extname = 'postgis';"))
#         connection.execute(text(f"ALTER EXTENSION postgis SET SCHEMA {schema_db};"))
#         connection.execute(text(f"ALTER DATABASE {name_db} SET search_path TO public, {schema_db};"))

#         # Create table
#         create_query = f"""
#         CREATE TABLE IF NOT EXISTS {schema_db}.{table_new_db} (
#             gid SERIAL PRIMARY KEY,
#             cod_mun VARCHAR(8) NOT NULL,
#             name_mun VARCHAR(35) NOT NULL,
#             uf_mun VARCHAR(2) NOT NULL,
#             agg_spat VARCHAR(15) NOT NULL,
#             agg_time VARCHAR(15) NOT NULL,
#             indicator VARCHAR(40) NOT NULL,
#             value NUMERIC(10, 2) NOT NULL,
#             date TIMESTAMP NOT NULL,
#             geom geometry(Polygon, 4326)
#         );
#         """
#         connection.execute(text(create_query))

#         # Clear existing data, only if overwrite=True
#         if overwrite:
#             print(f"\nATTENTION: clearing table {schema_db}.{table_new_db} ...\n")
#             connection.execute(text(f"DELETE FROM {schema_db}.{table_new_db};"))

#     print("\nPopulating database with Shapefile values ...")
#     records = []

#     for _, row in tqdm(study_area_shp.iterrows(), total=len(study_area_shp)):
#         if pd.isna(row.get("cod_mun")):
#             continue

#         columns_of_interest = study_area_shp.columns[ncol_epiweek:]
#         date_columns = [col for col in columns_of_interest if re.search(r"\d{8}", col)]

#         for col in date_columns:
#             match = re.search(r"\d{8}", col)
#             if match:
#                 date_val = pd.to_datetime(match.group(), format="%Y%m%d", errors='coerce')
#                 try:
#                     value = float(row[col])
#                 except (ValueError, TypeError):
#                     continue

#                 if pd.isna(value):
#                     continue

#                 records.append({
#                     "cod_mun": row["cod_mun"],
#                     "name_mun": row["name_mun"],
#                     "uf_mun": row["uf_mun"],
#                     "agg_spat": agg_spat_name,
#                     "agg_time": agg_time_name,
#                     "indicator": indicator_name,
#                     "value": value,
#                     "date": date_val,
#                     "geometry": row["geometry"]
#                 })

#     if records:
#         gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
#         gdf.rename(columns={"geometry": "geom"}, inplace=True) # rename column to geom
#         gdf.set_geometry("geom", inplace=True) # define the active geometry
#         gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)
#         gdf.to_postgis(
#             name=table_new_db,
#             con=engine,
#             schema=schema_db,
#             if_exists="append",
#             index=False,
#             dtype={"geom": Geometry(geometry_type="POLYGON", srid=4326)}
#         )

#     print(f"\nDatabase {table_new_db} created successfully!\n")



def process_climate_postgres(geojson_path, name_db, table_new_db=None, schema_db="climate", host_db="localhost", port_db=5432, user_db="postgres", pass_db="postgres", overwrite=False):
    """
    Populate PostgreSQL table from GeoJSON with temporal and spatial aggregation.

    Parameters
    ----------
    geojson_path : str
        Path to the input GeoJSON of the interesting area.
    name_db : str
        Name of the PostgreSQL database.
    table_new_db : str
        Name of the new table to be created in PostgreSQL. Used last directory, if table name is not provided
    schema_db : str, optional
        Name of the schema to use. Default is 'climate'.
    host_db : str, optional
        Host name or IP of the PostgreSQL server. Default is 'localhost'.
    port_db : int, optional
        Port number of the PostgreSQL server. Default is 5432.
    user_db : str, optional
        Username for the database. Default is 'postgres'.
    pass_db : str, optional
        Password for the database. Default is 'postgres'.
    overwrite : bool, optional
        If True, allows delete the table before, and replace existing data. Default is False, and maintaining existing data.

    Raises
    ------
    ValueError
        If any required parameters are not defined.

    Returns
    -------
    None
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
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_db};"))
        connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS postgis SCHEMA {schema_db};"))
        connection.execute(text("UPDATE pg_extension SET extrelocatable = TRUE WHERE extname = 'postgis';"))
        connection.execute(text(f"ALTER EXTENSION postgis SET SCHEMA {schema_db};"))
        connection.execute(text(f"ALTER DATABASE {name_db} SET search_path TO public, {schema_db};"))

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
            geom geometry(Polygon, 4326)
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
        gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
        gdf.rename(columns={"geometry": "geom"}, inplace=True) # rename column to geom
        gdf.set_geometry("geom", inplace=True) # define the active geometry
        gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)
        gdf.to_postgis(
            name=table_new_db,
            con=engine,
            schema=schema_db,
            if_exists="append",
            index=False,
            dtype={"geom": Geometry(geometry_type="POLYGON", srid=4326)}
        )

    print(f"\nDatabase {table_new_db} created successfully!\n")
    print(f"\nInsertion completed: {len(records)} records added to the table '{schema_db}.{table_new_db}'\n")


