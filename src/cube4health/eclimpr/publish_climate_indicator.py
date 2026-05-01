import os
import json
from typing import Optional
import importlib.resources as resources
from pathlib import Path

from cube4health.edpu.geoserver import GeoServer
from cube4health.edpu import stac as stac_mod
import cube4health.edpu.templates.styles as styles_pkg
from cube4health.eclimpr.utils_bd import process_climate_postgres


# function to get the path of the internal STAC climate template (vector or raster)
def get_climate_template(template_type: str) -> str:
    """
    Return the path to the internal STAC climate template.

    Parameters
    ----------
    template_type : str
        Type of template: "vector" or "raster".

    Returns
    -------
    str
        Absolute path to the template file.
    """

    templates = {
        "vector": "climate_vector.json",
        "raster": "climate_raster.json",
    }

    template_type = template_type.lower()

    if template_type not in templates:
        raise ValueError("template_type must be 'vector' or 'raster'.")

    template_file = resources.files("cube4health.eclimpr").joinpath(
        "templates", "jsons", templates[template_type]
    )

    if not template_file.is_file():
        raise FileNotFoundError(
            f"Template '{templates[template_type]}' not found in package "
            "'cube4health.eclimpr/templates/jsons'."
        )

    return str(template_file)
    

def publish_climate_indicator_vector_geoserver(
    files_path, name_db, schema_db = "climate", port_db = 5432, user_db = "postgres", gs_url = "http://localhost:10190/geoserver", gs_workspace = "harmonize_climate", gs_username = "admin", gs_style_file = None, hostname = "localhost"):
    """
    Publish a climate indicator dataset into GeoServer.

    This function automates the publication process of climate indicators (GeoJSON) for visualization through GeoServer.

    It detects temporal aggregation (month or epidemiological week), region of interest, and indicator type (e.g., temperature, precipitation) automatically based on the input folder name.

    Parameters
    ----------
    files_path : str
        Path to the main directory containing the GeoJSON.
        The folder name must include a temporal unit such as "month" or "epiweek".
    name_db : str
        PostgreSQL database name.
    schema_db : str, default="climate"
        Schema name in PostgreSQL.
    port_db : int, default=5432
        PostgreSQL connection port.
    user_db : str, default="postgres"
        PostgreSQL username.
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

    Notes
    -----
    - This function automatically selects an SLD style file based on the indicator name.
    - GeoServer configurations are dynamically generated.
    - Temporal and regional attributes are inferred from the dataset name.

    Examples
    --------
    >>> from cube4health.eclimpr.publish_climate_indicator import publish_climate_indicator_vector_geoserver
    >>> publish_climate_indicator_vector_geoserver(
    ...     files_path="/path/to/temp_max_NE_mun_month_era5land",
    ...     name_db="harmonize",
    ...     schema_db="climate",
    ...     port_db=5432,
    ...     user_db="postgres",
    ...     gs_url="http://localhost:10190/geoserver",
    ...     gs_workspace = "harmonize_climate",
    ...     gs_username="admin",
    ...     hostname = "localhost"
    ... )
    
    Collection temp_max_NE_mun_month_era5land-1 created
    - Total 188 items created.
    Collection id:  4

    """

    # -------------------------
    # PATH NORMALIZATION
    # -------------------------
    if not files_path or not name_db: 
        raise ValueError("Parameters 'files_path' and 'name_db' are required.")

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
    
    local_items_path = os.path.join(
        maindir, 
        filename, 
        "shapefiles"
        )

    # Check if shapefiles dir exists (input data directory)
    if not os.path.exists(local_items_path):
        raise FileNotFoundError(f"Input directory '{local_items_path}' does not exist.")

    # -------------------------
    # SLD SELECTION - Geoserver styles and description and stac features
    # -------------------------
    if "temp" in name_lower and "era5land" in name_lower:
        if "anomaly" in name_lower and "epiweek" in name_lower:
            sld_name = "anomaly_epiweek.sld"
        elif "anomaly" in name_lower and "month" in name_lower:
            sld_name = "anomaly_month.sld"
        else:
            sld_name = "temperature.sld"
    elif "temp" in name_lower and "cptec" in name_lower:
        sld_name = "temperature.sld"
    elif "prec" in name_lower and "era5land" in name_lower:
        sld_name = "precipitation.sld"
    elif "prec" in name_lower and "cptec" in name_lower:
        sld_name = "precipitation.sld"
    elif "humidity" in name_lower:
        sld_name = "humidity.sld"
    else:
        sld_name = "temperature.sld"  # fallback 
 
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

    print("Geoserver published data:", filename)
    return filename
    


# vector data - all climate indicators
def publish_climate_indicator_vector_stac(
    files_path, nginx_path, stac_service_url = "http://localhost:8080", stac_is_public = True, stac_roi = None, gs_url = "http://localhost:10190/geoserver", gs_workspace = "harmonize_climate", hostname = "localhost", ):
    """
    Publish a climate indicator dataset to STAC.

    This function automates the publication process of climate indicators (GeoJSON) to the creation of STAC metadata for catalog integration.

    It detects temporal aggregation (month or epidemiological week), region of interest, and indicator type (e.g., temperature, precipitation) automatically based on the input folder name.

    Parameters
    ----------
    files_path : str
        Path to the main directory containing the GeoJSON.
        The folder name must include a temporal unit such as "month" or "epiweek".
    nginx_path : str
        Path to the default nginx directory containing the GeoJSON files.  
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
    hostname : str, default="localhost"
        Hostname used by the STAC and GeoServer clients.

    Raises
    ------
    ValueError
        If `files_path` and `name_db` is not provided.
   
    Returns
    -------
    str
        The published STAC collection ID.

    Notes
    -----
    - Temporal and regional attributes are inferred from the dataset name.

    Examples
    --------
    >>> from cube4health.eclimpr.publish_climate_indicator import publish_climate_indicator_vector_stac
    >>> publish_climate_indicator_vector_stac(
    ...     files_path="/path/to/temp_max_NE_mun_month_era5land",
    ...     nginx_path="/path/to/nginx_dirdata",
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
    if not files_path or not nginx_path: # or not nginx_path:
        raise ValueError("Parameters 'files_path' and 'nginx_path'are required.")

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
            description = (
                f"Number of consecutive days (cdays) in which the maximum temperature exceeds the climatological normal, representing a temperature anomaly, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from EERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS), and the Maximum Temperature Climatological Normal (INMET)."
                )
            indicator = "anomaly"
            key4 = "Maximum temperature anomaly"
        elif "anomaly" in name_lower and "month" in name_lower:
            description = (
                f"Number of consecutive days (cdays) in which the maximum temperature exceeds the climatological normal, representing a temperature anomaly, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS), and the Maximum Temperature Climatological Normal (INMET)."
                )
            indicator = "anomaly"
            key4 = "Maximum temperature anomaly"
        else:
            description = (
                f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
                )
            indicator = "temperature"
            
    elif "temp" in name_lower and "cptec" in name_lower:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the SAMeT product, available from the CPTEC/INPE."
            )    
        indicator = "temperature"
        
    elif "prec" in name_lower and "era5land" in name_lower:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "precipitation"
        
    elif "prec" in name_lower and "cptec" in name_lower:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the MERGE product, available from the CPTEC/INPE."
            )    
        indicator = "precipitation"
        
    elif "humidity" in name_lower:
        description = (
            f"This is the Relative humidity (percent) from 2m dewpoint temperature and 2m mean temperature, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "humidity"
        key4 = "Relative humidity"
        
    else:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}."
            )
        indicator = "temperature"

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
    # GEOSERVER PARAMETER
    # -------------------------
    gs_url = gs_url.strip().rstrip("/")

    # -------------------------
    # STAC PUBLISHING
    # -------------------------
    stac_service_url = stac_service_url.strip().rstrip("/")
    
    asset_names = {
        ".png": "thumbnail",
        ".geojson": "geojson",
        ".zip": "shapefile",
    }

    new_informations = {
        "name": f"{name_lower}",
        "title": f"{filename}",
        "description": description,
        "version": 1,
        "is_public": stac_is_public,
        "metadata": {
            "wms": {
                "url": f"{gs_url}/{gs_workspace}/wms",
                "layerName": f"{gs_workspace}:{name_lower}",
            },
            "sources": [{
                "name": f"{name_lower}",
                "stacUri": f"{stac_service_url}/collections/{name_lower}-1",
                "descriptionUri": None,
            }],
            "datacite": {
                "id": f"{name_lower}",
                "dates": [{"date": "2025"}],
                "titles": {"lang": "en", "title": f"{name_lower}"},
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
       "keywords": [stac_keywords[k] for k in stac_keywords],
    }

    #  "keywords": [{"lang": "en", "subject": stac_keywords[k]} for k in stac_keywords],

    stac_client = stac_mod.STAC(service_url=stac_service_url, hostname=hostname)

    col_id = stac_client.publish_collection(
        data=new_informations,
        template=get_climate_template("vector"), #"climate",
        items_path=local_items_path,
        #additional_path='dev', # comment when run in localhost
        asset_names=asset_names,
        root_data_path=nginx_path, #local_root_path,
        del_output_file=False,
        workspace=gs_workspace,
    )

    print("Collection id:", col_id)
    return col_id
      

# raster data - all climate indicators
def publish_climate_indicator_raster_stac(
    files_path, nginx_path, stac_service_url = "http://localhost:8080", stac_is_public = True, stac_roi = None, gs_url = "http://localhost:10190/geoserver", gs_workspace = "harmonize_climate", hostname = "localhost", ):
    """
    Publish a climate indicator dataset raster to STAC.

    This function automates the publication process of climate indicators (GeoJSON) to the creation of STAC metadata for catalog integration.

    It detects temporal aggregation (month or epidemiological week), region of interest, and indicator type (e.g., temperature, precipitation) automatically based on the input folder name.

    Parameters
    ----------
    files_path : str
        Path to the main directory containing the GeoJSON.
        The folder name must include a temporal unit such as "month" or "epiweek".
    nginx_path : str
        Path to the default nginx directory containing the GeoJSON files.  
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
    hostname : str, default="localhost"
        Hostname used by the STAC and GeoServer clients.

    Raises
    ------
    ValueError
        If `files_path` and `name_db` is not provided.
   
    Returns
    -------
    str
        The published STAC collection ID.

    Notes
    -----
    - Temporal and regional attributes are inferred from the dataset name.

    Examples
    --------
    >>> from cube4health.eclimpr.publish_climate_indicator import publish_climate_indicator_raster_stac
    >>> publish_climate_indicator_raster_stac(
    ...     files_path="/path/to/temp_max_NE_mun_month_era5land",
    ...     nginx_path="/path/to/nginx_dirdata",
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
    if not files_path or not nginx_path: # or not nginx_path:
        raise ValueError("Parameters 'files_path' and 'nginx_path'are required.")

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
        "images"
        )

    # Check if images dir exists (input data directory)
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
            raise ValueError("The anomaly data does not have raster files.")
        
        elif "anomaly" in name_lower and "month" in name_lower:
            raise ValueError("The anomaly data does not have raster files.")
        
        else:
            description = (
                f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
                )
            indicator = "temperature"
            
    elif "temp" in name_lower and "cptec" in name_lower:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the SAMeT product, available from the CPTEC/INPE."
            )    
        indicator = "temperature"
        
    elif "prec" in name_lower and "era5land" in name_lower:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "precipitation"
        
    elif "prec" in name_lower and "cptec" in name_lower:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}. Dataset provided by the MERGE product, available from the CPTEC/INPE."
            )    
        indicator = "precipitation"
        
    elif "humidity" in name_lower:
        description = (
            f"This is the Relative humidity (percent) from 2m dewpoint temperature and 2m mean temperature, aggregated by municipality and {temporal_unit} for {roi}. Dataset derived from ERA5-Land hourly data, available from the Copernicus Climate Data Store (CDS)."
            )
        indicator = "humidity"
        key4 = "Relative humidity"
        
    else:
        description = (
            f"This is the {' '.join(parts)} aggregated by municipality and {temporal_unit} for {roi}."
            )
        indicator = "temperature"

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
    # GEOSERVER PARAMETER
    # -------------------------
    gs_url = gs_url.strip().rstrip("/")
    gs_store = f"{name_lower}_ras" #name_lower       # name store/DB table
    gs_name = filename

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
        "is_public": stac_is_public,
        "metadata": {
            "wms": {
                "url": f"{gs_url}/{gs_workspace}/wms",
                "layerName": f"{gs_workspace}:{gs_store}",
            },
            "sources": [{
                "name": f"{gs_store}",
                "stacUri": f"{stac_service_url}/collections/{gs_store}-1",
                "descriptionUri": None,
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
       "keywords": [stac_keywords[k] for k in stac_keywords],
    }

    #  "keywords": [{"lang": "en", "subject": stac_keywords[k]} for k in stac_keywords],

    stac_client = stac_mod.STAC(service_url=stac_service_url, hostname=hostname)

    col_id = stac_client.publish_collection(
        data=new_informations,
        template=get_climate_template("raster"), #"climate",
        items_path=local_items_path,
        #additional_path='dev', # comment when run in localhost
        asset_names=asset_names,
        root_data_path=nginx_path, #local_root_path,
        del_output_file=False,
        workspace=gs_workspace,
    )

    print("Collection id:", col_id)
    return col_id

