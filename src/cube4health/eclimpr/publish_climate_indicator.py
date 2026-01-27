import os
from typing import Optional
import importlib.resources as resources
from pathlib import Path

from cube4health.edpu.geoserver import GeoServer
from cube4health.edpu import stac as stac_mod
import cube4health.edpu.templates.styles as styles_pkg
from cube4health.eclimpr.utils_bd import process_climate_postgres

# vector data - all climate indicators
def publish_climate_indicator_vector(
    files_path, name_db, schema_db = "climate", host_db = "localhost", port_db = 5432, user_db = "postgres", overwrite_db = False, *, stac_service_url = "http://localhost:8080", stac_is_public = True, stac_roi = None, gs_url = "http://localhost:10190/geoserver", gs_workspace = "harmonize_climate", gs_username = "admin", gs_style_file = None, hostname = "localhost", ):
    """
    Publish a climate indicator dataset to PostgreSQL/PostGIS, GeoServer, and STAC.

    This function automates the publication process of climate indicators (GeoJSON) into a PostgreSQL/PostGIS database, their visualization through GeoServer, and the creation of STAC metadata for catalog integration.

    It detects temporal aggregation (month or epidemiological week), region of interest, and indicator type (e.g., temperature, precipitation) automatically based on the input folder name.

    Parameters
    ----------
    files_path : str
        Path to the main directory containing the GeoJSON.
        The folder name must include a temporal unit such as "month" or "epiweek".
    nginx_path : str
        Path to the default nginx directory containing the GeoJSON files.  
    name_db : str
        PostgreSQL database name.
    schema_db : str, default="climate"
        Schema name in PostgreSQL.
    host_db : str, default="localhost"
        Database hostname or IP address.
    port_db : int, default=5432
        PostgreSQL connection port.
    user_db : str, default="postgres"
        PostgreSQL username.
    overwrite_db : bool, default=False
        If True, existing data will be replaced.
        If False, data will be appended.
    stac_service_url : str, default="http://localhost:8080"
        Base URL of the STAC service endpoint.
    stac_is_public : bool, default=True
        If True, the collection will be visible in the HARMONIZE Explorer interface.  
        If False, the collection will still be accessible via the STAC API, but it will not appear in the HARMONIZE Explorer.
    stac_roi : str
        The name of the region of interest (roi)     
    gs_url : str, default="http://localhost:10190/geoserver"
        Base URL of the GeoServer service endpoint.
    gs_workspace : str, default="harmonize_climate"
        GeoServer workspace name.
    gs_username : str, default="admin"
        GeoServer username.
    gs_style_file : str
        Path to the user Geoserver style SDL (Styled Layer Descriptor) file.
    hostname : str, default="localhost"
        Hostname used by the STAC and GeoServer clients.

    Raises
    ------
    ValueError
        If `files_path` and `name_db` is not provided.
    FileNotFoundError
        If the required SLD style file is not found.

    Returns
    -------
    str
        The published STAC collection ID.

    Notes
    -----
    - This function automatically selects an SLD style file based on the indicator name.
    - GeoServer and STAC configurations are dynamically generated.
    - Temporal and regional attributes are inferred from the dataset name.

    Examples
    --------
    >>> from cube4health.eclimpr.publish_climate_indicator import publish_climate_indicator_vector
    >>> publish_climate_indicator_vector(
    ...     files_path="/path/to/temp_max_NE_mun_month_era5land",
    ...     nginx_path="/path/to/nginx_dirdata",
    ...     name_db="harmonize",
    ...     schema_db="climate",
    ...     host_db="localhost",
    ...     port_db=5432,
    ...     user_db="postgres",
    ...     overwrite_db=True,
    ...     gs_username="admin",
    ...     gs_url="http://localhost:10190/geoserver",
    ...     gs_workspace = "harmonize_climate",
    ...     stac_service_url="http://localhost:8080",
    ...     stac_is_public=True,
    ...     hostname = "localhost"
    ... )
    
    Collection temp_max_NE_mun_month_era5land-1 created
    - Total 188 items created.
    Collection id:  4

    """

    # -------------------------
    # PATH NORMALIZATION
    # -------------------------
    if not files_path or not name_db: # or not nginx_path:
        raise ValueError("Parameters 'files_path', 'nginx_path' and 'name_db' are required.")

    # Check if main_dir exists (input data directory)
    if not os.path.exists(files_path):
        raise FileNotFoundError(f"Input directory '{files_path}' does not exist.")
    
    # # Check if nginx_path exists (input data directory)
    # if not os.path.exists(nginx_path):
    #     raise FileNotFoundError(f"Input directory '{nginx_path}' does not exist.")
    
    files_path = files_path.strip().rstrip("/")
    filename = os.path.basename(files_path)
    maindir = os.path.dirname(files_path)
    name_lower = filename.lower()
    # Root of published data on host/local nginx
    #local_root_path=nginx_path

    local_items_path = os.path.join(
        maindir, 
        filename, 
        "shapefiles"
        )

    # Check if shapefiles dir exists (input data directory)
    if not os.path.exists(local_items_path):
        raise FileNotFoundError(f"Input directory '{local_items_path}' does not exist.")

    # -------------------------
    # POSTGRES INSERTION
    # -------------------------
    # process_climate_postgres(
    #     geojson_path=os.path.join(maindir,filename),
    #     name_db=name_db,
    #     table_new_db=filename,
    #     schema_db=schema_db,
    #     host_db=host_db,
    #     port_db=port_db,
    #     user_db=user_db,
    #     overwrite_db=overwrite_db,
    # )

    # -------------------------
    # KEYWORD MAP
    # -------------------------
    keyword_map = {
        "max": "maximum",
        "min": "minimum",
        "mean": "mean",
        "temp": "temperature",
        "prec": "precipitation",
        "humidity": "relative humidity",
        "anomaly": "anomaly",
    }

    # Temporal unit
    if "epiweek" in f"_{name_lower}_":
        temporal_unit = "epidemiological week"
    elif "month" in f"_{name_lower}_":
        temporal_unit = "month"
    else:
        temporal_unit = "time period"

    # Region of interest (roi)
    if stac_roi:
        roi = stac_roi
    else:
        if "_ne_" in f"_{name_lower}_":
            roi = "Northeast"
        elif "_no_" in f"_{name_lower}_":
            roi = "North"
        else:
            roi = "Brazil"

    # Extract parts for description/keywords
    parts = [v for k, v in keyword_map.items() if k in name_lower] or ["indicator"]

    # -------------------------
    # PROVIDER AND INDICATOR
    # -------------------------
    # provider
    provider = "ERA5-Land" if "era5land" in name_lower else ("CPTEC" if "cptec" in name_lower else "Unknown")

    # STAC
    key4 = " ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts))

    # -------------------------
    # SLD SELECTION - Geoserver styles and description and stac features
    # -------------------------
    if "temp" in name_lower and "era5land" in name_lower:
        if "anomaly" in name_lower and "epiweek" in name_lower:
            sld_name = "anomaly_epiweek.sld"
            description = (
                f"Number of consecutive days (cdays) in which the maximum temperature exceeds the climatological normal, representing a temperature anomaly, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from EERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS), and the Maximum Temperature Climatological Normal (INMET)."
                )
            indicator = "anomaly"
            key4 = "Maximum temperature anomaly"
        elif "anomaly" in name_lower and "month" in name_lower:
            sld_name = "anomaly_month.sld"
            description = (
                f"Number of consecutive days (cdays) in which the maximum temperature exceeds the climatological normal, representing a temperature anomaly, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS), and the Maximum Temperature Climatological Normal (INMET)."
                )
            indicator = "anomaly"
            key4 = "Maximum temperature anomaly"
        else:
            sld_name = "temperature.sld"
            description = (
                f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
                )
            indicator = "temperature"
            
    elif "temp" in name_lower and "cptec" in name_lower:
        sld_name = "temperature.sld"
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the SAMeT product, available from the CPTEC/INPE."
            )    
        indicator = "temperature"
        
    elif "prec" in name_lower and "era5land" in name_lower:
        sld_name = "precipitation.sld"
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "precipitation"
        
    elif "prec" in name_lower and "cptec" in name_lower:
        sld_name = "precipitation.sld"
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the MERGE product, available from the CPTEC/INPE."
            )    
        indicator = "precipitation"
        
    elif "humidity" in name_lower:
        sld_name = "humidity.sld"
        description = (
            f"This is the Relative humidity (percent) from 2m dewpoint temperature and 2m mean temperature, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "humidity"
        key4 = "Relative humidity"
        
    else:
        sld_name = "temperature.sld"  # fallback 
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}."
            )
        indicator = "temperature"

    # Geoserver Style (SLD)
    if gs_style_file: 
        if Path(gs_style_file).is_file():
            style_file = str(gs_style_file)
        else:
            raise FileNotFoundError(
                f"SLD file not found in {gs_style_file}. Check that the file exists."
            )
    else:
        # try styles/vector/<sld_name> without requiring 'vector' to be package
        candidate = (resources.files(styles_pkg) / "vector" / sld_name)
        #print(candidate)

        if candidate.is_file():
            style_file = str(candidate)
        else:
            raise FileNotFoundError(
                f"SLD '{sld_name}' not found in {candidate}. Check that the file exists."
            )
    
    print("Selected style:", style_file)

    # -------------------------
    # STAC METADATA
    # -------------------------
    
    stac_keywords = {
        "key1": "Climate",
        "key2": provider, 
        "key3": indicator.capitalize(),     # ex.: Temperature
        "key4": key4,                       # ex.: Maximum temperature
        "key5": "Vector",
        "key6": "Municipality",
        "key7": temporal_unit.capitalize(), # Epidemiological week / Month
        "key8": roi,
        "key9": "Brazil",
    }

    # -------------------------
    # GEOSERVER PUBLICATION
    # -------------------------
    gs_url = gs_url.strip().rstrip("/")

    gs_store = name_lower       # name store/DB table
    gs_name = filename
    regex = "regex=[0-9]{8}"
    attribute_date = "epiweek_start_date" if "epiweek" in name_lower else "month_start_date"

    # DB parameters
    db_settings = {
        "db": name_db,
        "schema": schema_db,
        "user": user_db,
        "port": str(port_db),
    }

    # CLIENT
    geo = GeoServer(
        service_url=gs_url,
        workspace=gs_workspace,
        hostname=hostname,
        username=gs_username,
        db_settings=db_settings,
    )

    layers = [{
        "name": gs_store,           # the name of table in db
        "title": gs_name,
        "style": style_file,        # The path to the style file
        "path": local_items_path,
    }]

    # Datastore (create if doesn't exist)
    try:
        ds = geo.geoserver.get_datastore(store_name=gs_store, workspace=gs_workspace)
        if not ds:
            raise Exception("Datastore not found")
    except Exception:
        geo.create_feature_store(workspace=gs_workspace, store=gs_store)

    # PUBLISHING INTO GEOSERVER 
    geo.publish_feature_data(
        layers=layers,
        time_regex=regex,
        attribute=attribute_date,
        workspace=gs_workspace,
        store=gs_store,
    )

    # -------------------------
    # STAC PUBLISHING
    # -------------------------
    # stac_service_url = stac_service_url.strip().rstrip("/")
    
    # asset_names = {
    #     ".png": "thumbnail",
    #     ".geojson": "geojson",
    #     ".zip": "shapefile",
    # }

    # new_informations = {
    #     "name": f"{gs_store}",
    #     "title": f"{gs_name}",
    #     "description": description,
    #     "version": 1,
    #     "is_public": f"{str(stac_is_public).lower()}",
    #     "metadata": {
    #         "wms": {
    #             "url": f"{gs_url}/{gs_workspace}/wms",
    #             "layerName": f"{gs_workspace}:{gs_store}",
    #         },
    #         "sources": [{
    #             "name": f"{gs_store}",
    #             "stacUri": f"{stac_service_url}/collections/{gs_store}-1",
    #             "descriptionUri": "null",
    #         }],
    #         "datacite": {
    #             "id": f"{gs_store}",
    #             "dates": [{"date": "2025"}],
    #             "titles": {"lang": "en", "title": f"{gs_store}"},
    #             "subjects": [
    #                 {"lang": "en", "subject": stac_keywords[k]} for k in stac_keywords
    #             ],
    #             "descriptions": [{
    #                 "lang": "en",
    #                 "description": description,
    #                 "descriptionType": "Abstract",
    #             }],
    #         },
    #     },
    #     "keywords": [{"lang": "en", "subject": stac_keywords[k]} for k in stac_keywords],
    # }

    # stac_client = stac_mod.STAC(service_url=stac_service_url, hostname=hostname)

    # col_id = stac_client.publish_collection(
    #     data=new_informations,
    #     template="climate",
    #     items_path=local_items_path,
    #     #additional_path='dev', # comment when run in localhost
    #     asset_names=asset_names,
    #     root_data_path=local_root_path,
    #     del_output_file=False,
    #     workspace=gs_workspace,
    # )

    # print("Collection id:", col_id)
    # return col_id
    print("Geoserver published data:", filename)
    


# raster data - temperature, precipitation and humidity
def publish_climate_indicator_raster(
    files_path, nginx_path, name_db, schema_db = "climate", host_db = "localhost", port_db = 5432, user_db = "postgres", overwrite_db = False, *, stac_service_url = "http://localhost:8080", stac_is_public = False, stac_roi = None, gs_url = "http://localhost:10190/geoserver", gs_workspace = "harmonize_climate", gs_username = "admin", gs_style_file = None, hostname = "localhost", ):
    """
    Publish a climate indicator dataset to PostgreSQL/PostGIS, GeoServer, and STAC.

    This function automates the publication process of climate indicators (GeoJSON) into a PostgreSQL/PostGIS database, their visualization through GeoServer, and the creation of STAC metadata for catalog integration.

    It detects temporal aggregation (month or epidemiological week), region of interest, and indicator type (e.g., temperature, precipitation) automatically based on the input folder name.

    Parameters
    ----------
    files_path : str
        Path to the main directory containing the GeoJSON.
        The folder name must include a temporal unit such as "month" or "epiweek".
    nginx_path : str
        Path to the default nginx directory containing the GeoJSON files.  
    name_db : str
        PostgreSQL database name.
    schema_db : str, default="climate"
        Schema name in PostgreSQL.
    host_db : str, default="localhost"
        Database hostname or IP address.
    port_db : int, default=5432
        PostgreSQL connection port.
    user_db : str, default="postgres"
        PostgreSQL username.
    overwrite_db : bool, default=False
        If True, existing data will be replaced.
        If False, data will be appended.
    stac_service_url : str, default="http://localhost:8080"
        Base URL of the STAC service endpoint.
    stac_is_public : bool, default=False
        If True, the collection will be visible in the HARMONIZE Explorer interface.  
        If False, the collection will still be accessible via the STAC API, but it will not appear in the HARMONIZE Explorer.
    stac_roi : str
        The name of the region of interest (roi)     
    gs_url : str, default="http://localhost:10190/geoserver"
        Base URL of the GeoServer service endpoint.
    gs_workspace : str, default="harmonize_climate"
        GeoServer workspace name.
    gs_username : str, default="admin"
        GeoServer username.
    gs_style_file : str
        Path to the user Geoserver style SDL (Styled Layer Descriptor) file.
    hostname : str, default="localhost"
        Hostname used by the STAC and GeoServer clients.

    Raises
    ------
    ValueError
        If `files_path`, `nginx_path` and `name_db` is not provided.
    FileNotFoundError
        If the required SLD style file is not found.

    Returns
    -------
    str
        The published STAC collection ID.

    Notes
    -----
    - This function automatically selects an SLD style file based on the indicator name.
    - GeoServer and STAC configurations are dynamically generated.
    - Temporal and regional attributes are inferred from the dataset name.

    Examples
    --------
    >>> from cube4health.eclimpr.publish_climate_indicator import publish_climate_indicator_raster
    >>> publish_climate_indicator_raster(
    ...     files_path="/path/to/temp_max_NE_mun_month_era5land",
    ...     nginx_path="/path/to/nginx_dirdata",
    ...     name_db="harmonize",
    ...     schema_db="climate",
    ...     host_db="localhost",
    ...     port_db=5432,
    ...     user_db="postgres",
    ...     overwrite_db=True,
    ...     gs_username="admin",
    ...     gs_url="http://localhost:10190/geoserver",
    ...     gs_workspace = "harmonize_climate",
    ...     stac_service_url="http://localhost:8080",
    ...     stac_is_public=True,
    ...     hostname = "localhost"
    ... )
    
    Collection temp_max_NE_mun_month_era5land-1 created
    - Total 188 items created.
    Collection id:  4

    """

    # -------------------------
    # PATH NORMALIZATION
    # -------------------------
    if not files_path or not name_db or not nginx_path:
        raise ValueError("Parameters 'files_path', 'nginx_path' and 'name_db' are required.")

    # Check if main_dir exists (input data directory)
    if not os.path.exists(files_path):
        raise FileNotFoundError(f"Input directory '{files_path}' does not exist.")
    
    # Check if nginx_path exists (input data directory)
    if not os.path.exists(nginx_path):
        raise FileNotFoundError(f"Input directory '{nginx_path}' does not exist.")
    
    files_path = files_path.strip().rstrip("/")
    filename = os.path.basename(files_path)
    maindir = os.path.dirname(files_path)
    name_lower = filename.lower()
    # Root of published data on host/local nginx
    local_root_path=nginx_path

    local_items_path = os.path.join(
        maindir, 
        filename, 
        "images"
        )

    # Check if shapefiles dir exists (input data directory)
    if not os.path.exists(local_items_path):
        raise FileNotFoundError(f"Input directory '{local_items_path}' does not exist.")

    # -------------------------
    # KEYWORD MAP
    # -------------------------
    keyword_map = {
        "max": "maximum",
        "min": "minimum",
        "mean": "mean",
        "temp": "temperature",
        "prec": "precipitation",
        "humidity": "relative humidity",
    }

    # Temporal unit
    if "epiweek" in f"_{name_lower}_":
        temporal_unit = "epidemiological week"
    elif "month" in f"_{name_lower}_":
        temporal_unit = "month"
    else:
        temporal_unit = "time period"

    # Region of interest (roi)
    if stac_roi:
        roi = stac_roi
    else:
        if "_ne_" in f"_{name_lower}_":
            roi = "Northeast"
        elif "_no_" in f"_{name_lower}_":
            roi = "North"
        else:
            roi = "Brazil"

    # Extract parts for description/keywords
    parts = [v for k, v in keyword_map.items() if k in name_lower] or ["indicator"]

    # -------------------------
    # PROVIDER AND INDICATOR
    # -------------------------
    # provider
    provider = "ERA5-Land" if "era5land" in name_lower else ("CPTEC" if "cptec" in name_lower else "Unknown")

    # STAC
    key4 = " ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts))

    # -------------------------
    # SLD SELECTION - Geoserver styles and description and stac features
    # -------------------------
    if "temp" in name_lower and "era5land" in name_lower:
        if "anomaly" in name_lower and "epiweek" in name_lower:
            raise ValueError("The anomaly data does not have raster files.")
        
        elif "anomaly" in name_lower and "month" in name_lower:
            raise ValueError("The anomaly data does not have raster files.")
        
        else:
            sld_name = "temperature.sld"
            description = (
                f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
                )
            indicator = "temperature"
            
    elif "temp" in name_lower and "cptec" in name_lower:
        sld_name = "temperature.sld"
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the SAMeT product, available from the CPTEC/INPE."
            )    
        indicator = "temperature"
        
    elif "prec" in name_lower and "era5land" in name_lower:
        sld_name = "precipitation.sld"
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "precipitation"
        
    elif "prec" in name_lower and "cptec" in name_lower:
        sld_name = "precipitation.sld"
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the MERGE product, available from the CPTEC/INPE."
            )    
        indicator = "precipitation"
        
    elif "humidity" in name_lower:
        sld_name = "humidity.sld"
        description = (
            f"This is the Relative humidity (percent) from 2m dewpoint temperature and 2m mean temperature, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "humidity"
        key4 = "Relative humidity"
        
    else:
        sld_name = "temperature.sld"  # fallback 
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}."
            )
        indicator = "temperature"

    # Geoserver Style (SLD)
    if gs_style_file: 
        if Path(gs_style_file).is_file():
            style_file = str(gs_style_file)
        else:
            raise FileNotFoundError(
                f"SLD file not found in {gs_style_file}. Check that the file exists."
            )
    else:
        # try styles/raster/<sld_name> without requiring 'raster' to be package
        candidate = (resources.files(styles_pkg) / "raster" / sld_name)
        #print(candidate)

        if candidate.is_file():
            style_file = str(candidate)
        else:
            raise FileNotFoundError(
                f"SLD '{sld_name}' not found in {candidate}. Check that the file exists."
            )
    
    print("Selected style:", style_file)

    # -------------------------
    # STAC METADATA
    # -------------------------
    
    stac_keywords = {
        "key1": "Climate",
        "key2": provider, 
        "key3": indicator.capitalize(),     # ex.: Temperature
        "key4": key4,                       # ex.: Maximum temperature
        "key5": "Raster",
        "key6": "Municipality",
        "key7": temporal_unit.capitalize(), # Epidemiological week / Month
        "key8": roi,
        "key9": "Brazil",
    }

    # -------------------------
    # GEOSERVER PUBLICATION
    # -------------------------
    gs_url = gs_url.strip().rstrip("/")

    gs_store = f"{name_lower}_ras" #name_lower       # name store/DB table
    gs_name = filename
    regex = "regex=[0-9]{8}"
    attribute_date = "epiweek_start_date" if "epiweek" in name_lower else "month_start_date"

    # DB parameters
    db_settings = {
        "db": name_db,
        "schema": schema_db,
        "user": user_db,
        "port": str(port_db),
    }

    # # CLIENT
    # geo = GeoServer(
    #     service_url=gs_url,
    #     workspace=gs_workspace,
    #     hostname=hostname,
    #     username=gs_username,
    #     db_settings=db_settings,
    # )

    # -------------------------
    # STAC PUBLISHING
    # -------------------------
    stac_service_url = stac_service_url.strip().rstrip("/")
    
    asset_names = {
        ".png": "thumbnail",
        '.tif': 'raster'
    }

    new_informations = {
        "name": f"{gs_store}",
        "title": f"{gs_name}_ras",
        "description": description,
        "version": 1,
        "is_public": f"{str(stac_is_public).lower()}",
        "metadata": {
            "wms": {
                "url": f"{gs_url}/{gs_workspace}/wms",
                "layerName": f"{gs_workspace}:{gs_store}",
            },
            "sources": [{
                "name": f"{gs_store}",
                "stacUri": f"{stac_service_url}/collections/{gs_store}-1",
                "descriptionUri": "null",
            }],
            "datacite": {
                "id": f"{gs_store}",
                "dates": [{"date": "2025"}],
                "titles": {"lang": "en", "title": f"{gs_store}"},
                "subjects": [
                    {"lang": "en", "subject": stac_keywords[k]} for k in stac_keywords
                ],
                "descriptions": [{
                    "lang": "en",
                    "description": description,
                    "descriptionType": "Abstract",
                }],
            },
        },
        "keywords": [{"lang": "en", "subject": stac_keywords[k]} for k in stac_keywords],
    }

    stac_client = stac_mod.STAC(service_url=stac_service_url, hostname=hostname)

    col_id = stac_client.publish_collection(
        data=new_informations,
        template="climate",
        items_path=local_items_path,
        #additional_path='dev', # comment when run in localhost
        asset_names=asset_names,
        root_data_path=local_root_path,
        del_output_file=False,
        workspace=gs_workspace,
    )

    print("Collection id:", col_id)

    # -------------------------
    # CREATE datastore.properties IF NOT EXISTS
    # -------------------------
    # datastore_file = Path(local_items_path) / "datastore.properties"
    # if not datastore_file.exists():
    #     datastore_file.write_text(
    #         "type=ImageMosaic\n"
    #         "reader=org.geotools.gce.imagemosaic.ImageMosaicReader\n"
    #         "timeAttribute=ingestion\n"
    #         "useExistingSchema=true\n"
    #     )
    #     print(f"datastore.properties created in {datastore_file}")
    # else:
    #     print("datastore.properties already exists — jump creation")

    # # PUBLISHING INTO GEOSERVER 
    # geo.create_imagemosaic_store(
    #     data=local_items_path,
    #     layer_name=gs_store,
    #     store_name=gs_store,
    #     workspace=gs_workspace,
    #     title=gs_store,
    #     time_regex=regex,
    #     style=style_file)

    # print('Geoserver published done!')

    return col_id

