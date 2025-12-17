# inbuilt libraries
from copy import deepcopy
import os
import json
import requests
import warnings
from datetime import (
    datetime,
    timedelta
)
from typing import (
    Dict,
    List,
    Tuple, 
    Union,
    Optional
)
from concurrent.futures import (
    ProcessPoolExecutor,
    as_completed,
    ThreadPoolExecutor
)

# third-party libraries
import glob
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
import pyarrow as pa
import pyarrow.parquet as pq
from geo.Geoserver import GeoserverException
from dateutil.relativedelta import relativedelta
from shapely.geometry import (
    Polygon,
    MultiPolygon
)
from shapely.errors import ShapelyDeprecationWarning
from geobr import (
    read_state,
    read_municipality,
    read_health_region
)

# custom libraries

from cube4health.ehipr.utils import (
    chunk_list,
    shp_to_zip,
    check_date_format
)

from cube4health.ehipr.lis import SPATIAL_AGG_LIS, create_LIS_boundaries_shp
from cube4health.ehipr.db import save_data_db
from cube4health.ehipr.config import CPU_COUNT

from cube4health.edpu import (
    STAC,
    GeoServer
)
from cube4health.edpu.utils import (
    get_round_value,
    _check_existence_dirs,
    send_files_ssh
)



# disable the "chained assignment" warning
pd.set_option('mode.chained_assignment', None)

# Root path of the project
ROOT_PATH = '/'.join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1])

JSON_FOLDER_PATH = (
    os.path.join(
        '/'.join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1]),
        'ehipr/jsons/temp'
    )
)

# Abbreviations of the spatial aggregations
SPATIAL_AGG_ABBR = {
    'municipality': 'mun',
    'health_region': 'hr', 
    'state': 'uf'
}

# Abbreviations of the spatial aggregations
TEMPORAL_AGG_ABBR = {"week": "epiweek"}

# Abbreviations of the cardinal directions
REGION_ABBR = {
    'north': 'NO',
    'south': 'SO',
    'east': 'E',
    'west': 'W',
    'northeast': 'NE',
    'northwest': 'NW',
    'southeast': 'SE',
    'southwest': 'SW'
}

# Names of the items' assets in the STAC
ASSET_NAMES = {
    '.png': 'thumbnail',
    '.parquet': 'tabular',
    '.geojson': 'geojson',
    '.zip': 'shapefile',
    '.csv': 'csv'
}

# Default date format
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


# TODO: REMOVer pois esta dentro do edpu
def _check_existence_dirs(paths: List[str]) -> None:
    """
        Check the existence of directories.

    Parameters
    ----------
        paths : List[str]
            The directories path.

    Returns
    -------
            None
    """
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)


def get_indicators_id(provider: str, only_desc: bool=True) -> List[str]:
    """
        Get the identifiers of the indicators.

        Returns
        -------
           A dictionary containing:  
            - "status": bool indicating success or failure of the operation.  
            - "file": (if successful) a JSON string with the identifiers and descriptions of the indicators.  
            - "message": (if failed) a descriptive error message.
    """
    try:

        if not isinstance(provider, str):
            raise Exception("The provider parameter must be a string")

        with open(os.path.join(ROOT_PATH,'ehipr/jsons/info_indicators.json'), 'r') as my_json:
            info = json.load(my_json)
        if only_desc:
            return {
                "status": True,
                "file": json.dumps({indicator['id']: indicator['description'] 
                            for indicator in info[provider]['indicators']}, indent=4)
            } 
        else:
            return {
                "status": True,
                "file": info.get(provider).get('indicators')
            } 
    except Exception as err:
        return {
            "status": False,
            "message": f"Error: {str(err)}"
        }


def _get_indicator_info(id: str, provider: str) -> Union[Dict[str, str], str]:
    """
        Get information from an indicator.

        Parameters
        ----------
        id : str,
            Identifier of the indicator.
        provider : str,
            Data source that provides the indicator.

        Returns
        ----------
            If successful, returns a dictionary containing:
                - "status": True
                - "indicator": a dictionary with indicator information and provider metadata.
            If an error occurs, returns a dictionary with:
                - "status": False
                - "message": a descriptive error message.
            If the JSON file is not found, returns a string with the error message.
    """
    try:
        with open(os.path.join(ROOT_PATH,'ehipr/jsons/info_indicators.json'), 'r') as my_json:
            info = json.load(my_json)
    except FileNotFoundError:
        return "Error: It's necessary to have the info_indicators.json file in the ehipr/jsons folder."

    provider = provider.lower()
    if provider not in info.keys():
        return f"Error: It's necessary to inform an available "\
                f"provider: {', '.join([key for key in info.keys()])}"

    try:
        for indicator in info[provider]['indicators']:
            if indicator['id'] == id:
                indicator.update(
                    {
                        "provider_name": info[provider]['name'],
                        "provider_url": info[provider]['url'],
                        "country": info[provider]['country']
                    }
                )
                return {
                "status": True,
                "indicator": indicator
            } 
        return {
            "status": False,
            "message": f"Error: The indicator ID '{id}' was not found for provider '{provider}'. "
                       f"Available indicators: {', '.join([ind['id'] for ind in info[provider]['indicators']])}"
        }

    except Exception as err:
        return {
            "status": False,
            "message": f"Unexpected error: {str(err)}"
        }


def __get_data_from_source(name: str, 
                           github_settings: Dict[str, str],
                           path: str) -> str:
    """
        Get data from source.

        Parameters
        ----------
        name : str,
            The name of the indicator.
        git_token : str,
            The git token.
        path : str, default value is DATA_PATH,
            The path of the data.

        Returns
        ----------
            A string that contains the path of the data.
    """
    try:
        github_url = github_settings['url']
        github_token = github_settings['token']
    except KeyError:
        return "Error: It's necessary to provide the keys [url, token] to access "\
               "to the GitHub repository."

    headers = {'Authorization': f'token {github_token}'}
    response = requests.get(github_url, headers=headers)
    releases = response.json()
    for release in sorted(releases, key=lambda x: x['published_at'], reverse=True):
        if release['assets']:
            for asset in release['assets']:
                if name in asset['name']:
                    asset_name = os.path.splitext(os.path.basename(asset['name']))[0]
                    path = os.path.join(path, asset_name)
                    _check_existence_dirs([path])
                    path = os.path.join(path, asset['name'])
                    if not os.path.exists(path):
                        print(f"\nDOWNLOADING {asset['name']}...")
                        response = requests.get(asset['browser_download_url'])
                        with open(path, 'wb') as file:
                            file.write(response.content)
                        print("...DONE")
                        return path


def __crop_geometry(gdf: gpd.GeoDataFrame, 
                    file_path: str,
                    columns: Dict[str, str]) -> gpd.GeoDataFrame:
    """
    Crop the geometry of the shapefile.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame with the shapefile.
    file_path : str
        Path of the shapefile.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with the cropped geometry.
    """
    try:
        grid_col, data_col = columns['grid'], columns['crop']
    except KeyError:
        return "Error: It's necessary to provide the keys [grid, data] to crop the geometry."

    # Read crop shapefile and convert to same CRS of the grid shapefile
    gdf_crop = gpd.read_file(file_path)
    gdf_crop = gdf_crop.to_crs(gdf.crs)

    # Convert geocode data column to integer
    gdf_crop[data_col] = gdf_crop[data_col].astype(int)
    gdf[grid_col] = gdf[grid_col].astype(int)

    return gdf.loc[gdf[grid_col].isin(gdf_crop[data_col])]
    # FUNCTION TO CREATE MUNICIPALITY GRID FROM 2010
    #return gpd.sjoin(gdf, gdf_crop, how='inner', predicate='intersects')[gdf.columns]

def __process_crop(df_polygon, grid_info, crop_info, file_crop_geom):
    grid_info_cod = grid_info.get('cod_mun', grid_info['cod'])
    crop_info_cod = crop_info.get('cod_mun', crop_info['cod'])

    df_cropped = __crop_geometry(
        gdf=df_polygon,
        file_path=file_crop_geom,
        columns={'grid': grid_info_cod, 'crop': crop_info_cod}
    )

    # df_cropped = df_cropped.astype({grid_info['cod']: int})
    # cod_polygon = df_cropped[grid_info['cod']].unique()

    return df_cropped
    # return df_cropped, cod_polygon



'''def aggregate_data(indicators: List[str],
                    input_path: str,
                    provider: str,
                    data_columns: List[str],
                    github_settings: Optional[str] = None,
                    spatial_agg: Optional[List[str]] = None, 
                    temp_agg: Optional[List[str]] = None,
                    save: Optional[bool] = False,
                    requests_api: Optional[bool] = False) -> List[Dict[str, pd.DataFrame]]:
    """
        Aggregate data by spatial and temporal aggregations.

        Parameters
        ----------
        indicators : List[str],
            The list of indicators.
        input_path : str,
            The path of the data.
        provider : str,
            The provider of the data.
        spatial_agg : Optional[List[str]],
            The list of spatial aggregations.
        temp_agg : Optional[List[str]],
            The list of temporal aggregations.
        save : bool, default value is False,
            A parameter that modifies the return value. If it's true, will save the 
            data in parquet format.

        Returns
        ----------
            A list of dataframes that contains the aggregated data by each combination of 
            spatial and temporal aggregations.
    """

    # Verifies if the input path exists. If it does not, checks if the git token was provided.
    # If not, returns an error message. If it exists, downloads the data and saves it in the
    # input path.
    path_exists = True

    if not os.path.exists(input_path) and not github_settings:
        return 'Error: Input path does not exist and no git setting '\
               'was provided to download the data.'

    dataframes = []

    # Browse the list of indicators and open the corresponding files. Add a conditional to 
    # check the file extension (.parquet or .csv). After this extension check, see if there 
    # is a file in the input_path that corresponds to the indicator pointed to. If there is, 
    # take the path to read the file. If not, call the __get_data_from_source function.
    for indicator in indicators:
        dfs, new_dfs = [], []

        # Verifies if the indicator is a string
        if not isinstance(indicator, str):
            return f"Error: Indicator name {indicator} must be a string"

        directory = os.path.join(input_path, indicator)

        # Verifies if the directory exists
        _check_existence_dirs([directory])
        files = [os.path.join(directory, file) for file in os.listdir(directory) 
                                                    if os.path.isfile(os.path.join(directory, file))]

        if len(files) == 0:
            # If there is no file in the input_path, call the __get_data_from_source function
            # to download the data
            try:
                path_or_error = __get_data_from_source(name=indicator, 
                                                        github_settings=github_settings, 
                                                        path=input_path)
                # Verifies if the path_or_error is a string and if it is not an error.
                # If it is not an error, adds the path to the files list. Else, returns the error.
                if not 'Error' in path_or_error:
                    files.append(path_or_error)
                else:
                    return path_or_error
            except TypeError:
                return 'Error: there is no file in the input_path'

        for file in files:

            # Verifies if the file has a valid extension (.parquet or .csv)
            extension = ''
            if file.endswith('.parquet'):
                df = pd.read_parquet(file)
                extension = '.parquet'
            elif file.endswith('.csv'):
                df = pd.read_csv(file, dtype=str)
                extension = '.csv'
            else:
                return f"Error: File {file} does not have a valid extension. "\
                        "Only '.parquet' and '.csv' files are accepted."

            # Verifies if the data_columns dictionary contains all the required keys
            try:
                cod_col = data_columns['cod']
                date_col = data_columns['date']
                name_col = data_columns['name']
                spt_col = data_columns['spt_agg']
                temp_col = data_columns['temp_agg']
                value_col = data_columns['value']
            except KeyError:
                return "Error: The data_columns dictionary does not contain all the required keys."\
                        " The dictionary must contain 'cod', 'date', 'name', 'spt_agg', 'temp_agg' "\
                        "and 'value' keys."

            if spatial_agg is None:
                spatial_agg = df[spt_col].unique()

            if temp_agg is None:
                temp_agg = df[temp_col].unique()

            print(f"\nSEPARATING {indicator} BY SPATIAL AND TEMPORAL AGGREGATIONS...")
            for sp in spatial_agg:
                for tm in temp_agg:
                    print(f" - Combination: {sp} - {tm}")
                    df_temp = df.loc[(df[spt_col] == sp) & (df[temp_col] == tm)]
                    if df_temp.empty:
                        return f"Error: No data found for combination {sp} - {tm}. "\
                                "Verify if the aggregation's names correctly match "\
                                "the names in the dataset."
                    dfs.append(df_temp)

            if len(dfs) != 0:
                print("... Done")

            print("\norganizing the datasets...".upper())
            for df in tqdm(dfs):
                dicts = []
                cods = df.loc[df[cod_col].notna()][cod_col].unique()
                for cod in cods:
                    df_temp = df.loc[df[cod_col] == cod]
                    dicts.append(df_temp)
                new_df = pd.concat(dicts, ignore_index=True)

                # Get the spatial and temporal aggregations and the indicator name from 
                # this dataframe
                if provider == 'LIS':
                    from ehipr.lis import SPATIAL_AGG_LIS
                    agg_spt = [value for key, value in SPATIAL_AGG_LIS.items() 
                               if new_df.loc[0][spt_col] == key][0]
                else:
                    agg_spt = new_df.loc[0][spt_col]
                agg_time = new_df.loc[0][temp_col]
                name = new_df.loc[0][name_col]
                print('name: ', name)
                print('name: ', name_col)

                # Creating the path to save the data in the specified format aggregated 
                # by spatial and temporal
                final_path = os.path.join(directory, agg_time, agg_spt)
                _check_existence_dirs([final_path])

                # Get the indicator information and create the file name 
                indi_info = _get_indicator_info(id=name, provider=provider)

                if not indi_info["status"]:
                    return indi_info
                
                indi_info = indi_info.get("indicator")
                filename = f"{indi_info.get(name_col)}_{agg_spt}_{agg_time}.{extension}"
                filepath = os.path.join(final_path, filename)

                # Save the data in the specified format
                if save:
                    if extension == 'parquet':
                        table = pa.Table.from_pandas(new_df)
                        pq.write_table(table, filepath)
                    elif extension == 'csv':
                        new_df.to_csv(filepath)
                    else:
                        return f"Error: File {file} does not have a valid extension. "\
                                "Only '.parquet' and '.csv' files are accepted."
                dataframes.append(
                    {
                        'info': indi_info, 
                        'spatial_agg': agg_spt,
                        'temporal_agg': agg_time,
                        'df': new_df,
                        'extension': extension
                    }
                )

    return dataframes

'''

def aggregate_data(indicators: List[str],
                   input_path: str,
                   provider: str,
                   data_columns: List[str],
                   github_settings: Optional[str] = None,
                   spatial_agg: Optional[List[str]] = None, 
                   temp_agg: Optional[List[str]] = None,
                   save: Optional[bool] = False) -> List[Dict[str, pd.DataFrame]]:
    try:
        dataframes = []

        for indicator in indicators:
            dfs = []

            if not isinstance(indicator, str):
                return f"Error: Indicator name {indicator} must be a string"

            directory = os.path.join(input_path, indicator)

            try:
                _check_existence_dirs([directory])
            except Exception as e:
                return f"Error: Failed to verify or create directory {directory}: {e}"

            try:
                files = [os.path.join(directory, file) for file in os.listdir(directory) 
                         if os.path.isfile(os.path.join(directory, file))]
            except Exception as e:
                return f"Error: Failed to list files in directory {directory}: {e}"

            if len(files) == 0:
                try:
                    path_or_error = __get_data_from_source(name=indicator, 
                                                           github_settings=github_settings, 
                                                           path=input_path)
                    if not 'Error' in path_or_error:
                        files.append(path_or_error)
                    else:
                        return path_or_error
                except Exception as e:
                    return 'Error: Input filepath does not exist and no git setting was provided to download the data.'

            for file in files:
                extension = ''
                try:
                    if file.endswith('.parquet'):
                        df = pd.read_parquet(file)
                        extension = 'parquet'
                    elif file.endswith('.csv'):
                        df = pd.read_csv(file, dtype=str)
                        extension = 'csv'
                    else:
                        return f"Error: File {file} does not have a valid extension. Only '.parquet' and '.csv' files are accepted."

                except Exception as e:
                    return f"Error: Failed to read file {file}: {e}"
                
                # try:
                #     if not data_columns.get('spt_agg', None) in df.keys() and len(spatial_agg) == 1:
                #         temp_col = "agg"
                #         df[temp_col] = spatial_agg[0]
                #         data_columns['spt_agg'] = temp_col

                #     if not data_columns.get('temp_agg', None) in df.keys() and len(temp_agg) == 1:
                #         temp_col = "agg_time"
                #         df[temp_col] = temp_agg[0]
                #         data_columns['temp_agg'] = temp_col
                # except Exception as err:
                #     return f"Error: failed to get temporal and spatial aggregations. Reason: {str(err)}"
                
                try:
                    cod_col = data_columns['cod']
                    date_col = data_columns['date']
                    name_col = data_columns['name']
                    spt_col = data_columns['spt_agg']
                    temp_col = data_columns['temp_agg']
                    value_col = data_columns['value']
                except KeyError:
                    return "Error: The data_columns dictionary does not contain all the required keys."\
                            " The dictionary must contain 'cod', 'date', 'name', 'spt_agg', 'temp_agg' and 'value' keys."

                if spatial_agg is None:
                    spatial_agg = df[spt_col].unique()

                if temp_agg is None:
                    temp_agg = df[temp_col].unique()

                print(f"\nSEPARATING {indicator} BY SPATIAL AND TEMPORAL AGGREGATIONS...")
                for sp in spatial_agg:
                    for tm in temp_agg:
                        print(f" - Combination: {sp} - {tm}")
                        df_temp = df.loc[(df[spt_col] == sp) & (df[temp_col] == tm)]
                        if df_temp.empty:
                            return f"Error: No data found for combination {sp} - {tm}. Verify if the aggregation's names"\
                                    " correctly match the names in the dataset."
                        dfs.append(df_temp)

                if len(dfs) != 0:
                    print("... Done")

                for df in tqdm(dfs, total=len(dfs), desc='Organizing the datasets...'.upper()):
                    dicts = []
                    cods = df.loc[df[cod_col].notna()][cod_col].unique()
                    for cod in cods:
                        df_temp = df.loc[df[cod_col] == cod]
                        dicts.append(df_temp)
                    new_df = pd.concat(dicts, ignore_index=True)

                    if new_df.empty:
                        return f"Error: Resulting dataframe is empty for indicator {indicator}"

                    try:
                        if provider == 'lis':
                            file_agg_spt = [value for key, value in SPATIAL_AGG_LIS.items() 
                                       if new_df.loc[0][spt_col] == key][0]
                        else:
                            file_agg_spt = new_df.loc[0][spt_col]
                        
                        agg_spt = new_df.loc[0][spt_col]
                        agg_time = (
                            new_df.loc[0][temp_col]
                            if new_df.loc[0][temp_col] not in ['week', 'epiweek']
                            else TEMPORAL_AGG_ABBR['week']
                        )
                        name = new_df.loc[0][name_col]
                    except Exception as e:
                        return f"Error: Failed to extract metadata from the dataframe: {e}"

                    final_path = os.path.join(directory, agg_time, file_agg_spt)

                    try:
                        _check_existence_dirs([final_path])

                    except Exception as e:
                        return f"Error: Could not ensure directory {final_path} exists: {e}"

                    indi_info = _get_indicator_info(id=name, provider=provider)
                    if not indi_info["status"]:
                        return indi_info

                    indi_info = indi_info.get("indicator")
                    filename = (
                        f"{indi_info.get(name_col)}_{file_agg_spt}_{agg_time}.{extension}"
                    )
                    filepath = os.path.join(final_path, filename)
                    new_df["name"] = indi_info.get("name")

                    if save:
                        try:
                            if extension == 'parquet':
                                table = pa.Table.from_pandas(new_df)
                                pq.write_table(table, filepath)
                            elif extension == 'csv':
                                new_df.to_csv(filepath)
                            else:
                                return f"Error: Invalid file extension '{extension}' for saving."
                        except Exception as e:
                            return f"Error: Failed to save the file {filepath}: {e}"

                    dataframes.append({
                        'info': indi_info,
                        'spatial_agg': agg_spt,
                        'temporal_agg': agg_time,
                        'df': new_df,
                        'extension': extension
                    })

        return dataframes

    except Exception as e:
        return f"Unexpected error: {e}"


def spatialize_data(indicators: List[str],
                    input_path: str,
                    data_columns: List[str],
                    provider: str,
                    grid: Optional[Tuple[str, dict]] = None, 
                    file_crops_geom: Optional[List[Tuple[str, dict]]] = None,
                    spatial_agg: Optional[List[str]] = None, 
                    temp_agg: Optional[List[str]] = None,
                    github_settings: Optional[Dict[str, str]] = None,
                    publish_later: Optional[bool]=False,
                    requests_api: bool = False) -> Union[List[Dict[str, str]], str]:
    """
        Spatialize the data.

        Parameters
        ----------
        indicators : List[str],
            List of indicators.
        input_path : Optional[str], default value is DATA_PATH,
            Path of the input data.
        spatial_agg : Optional[List[str]], default value is None.
            Spatial aggregation.
        temp_agg : Optional[List[str]], default value is None.
            Temporal aggregation.
        provider : str, default value is 'LIS',
            Data source.
        grid : Optional[Tuple[str, dict]], default value is None.
            Grid information.
        file_crops_geom : Optional[List[Tuple[str, dict]]], default value is None.
            File crop geometry information.
        github_settings : Optional[Dict[str, str]], default value is None.
            Github settings.

        Returns
        -------
            A list of dictionaries with the geopandas dataframes and its information or a 
            string with an error message
    """

    layers = []
    region_crop = None

    publish_path = ''

    # AGGREGATE DATA
    # print('input_path: ', input_path)
    dataframes = aggregate_data(indicators=indicators, 
                                input_path=input_path, 
                                github_settings=github_settings, 
                                spatial_agg=spatial_agg, 
                                temp_agg=temp_agg,
                                provider=provider,
                                data_columns=data_columns)
                                

    if isinstance(dataframes, str):
        return f"Error: failed to aggregate data. Reason: {dataframes}"

    # Get the data columns
    try:
        cod_col = data_columns['cod']
        date_col = data_columns['date']
        # name_col = data_columns['name']
        # spt_col = data_columns['spt_agg']
        temp_col = data_columns['temp_agg']
        value_col = data_columns['value']
    except KeyError:
        return "Error: The data_columns dictionary does not contain all the required keys."\
                " The dictionary must contain 'cod', 'date', 'name', 'spt_agg', 'temp_agg' "\
                "and 'value' keys."

    # Verifies if the temporal aggregation is 'week'. If it is, the csv_week_pd will be used 
    # to format the data in the 'week' format.
    if any([df['temporal_agg'] for df in dataframes if df['temporal_agg'] == 'epiweek']):
        csv_week_pd = pd.read_csv(os.path.join(ROOT_PATH, 
                                  'ehipr/templates/csv/epidemiologicalweeks_ptbr.csv'))
    else:
        csv_week_pd = None

    len_crops = len(file_crops_geom) if file_crops_geom else 1

    provider = provider.lower()

    def __add_geom(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Add geometry to the GeoDataFrame.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame with the shapefile.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with the geometry.
        """
        gdf = gdf.copy()

    # SPATIALIZE DATA
    print(f'\nSPATIALIZING DATA...')
    
    # Suppressing Shapely deprecation and Future warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", message='.*initial implementation of Parquet.*')
        warnings.simplefilter("ignore")

        for index in range(len_crops):

            file_path, polygon_agg = '', ''

            # Get the crop information if the user specifies it
            if file_crops_geom:
                try:
                    file_crop_geom, crop_info = file_crops_geom[index]
                    print(f"Cropping data by shapefile {os.path.basename(file_crop_geom).split('.')[0]}...")
                except IndexError:
                    return f"Error: file_crops_geom must be a list with tuples where each tuple has two"\
                            " elements: the path to the shapefile and a dictionary with the columns names."

            for df_indi in tqdm(dataframes, total=len(dataframes), desc="Processing dataframes..."):
                try:
                    df = df_indi['df']
                    name = df_indi['info']['name']
                    id_indi = df_indi['info']['id']
                    agg_time = df_indi["temporal_agg"] if df_indi["temporal_agg"] != "week" else TEMPORAL_AGG_ABBR["week"]
                    data_country = df_indi['info']['country']
                except KeyError:
                    return "Error: The dictionary provided by aggregate_data does not contain "\
                                   "all the required keys."
                try:
                    agg_spt = SPATIAL_AGG_LIS[df_indi['spatial_agg']
                                            ] if provider == 'lis' else df_indi['spatial_agg']
                except Exception as err:
                    return f"Error: could not find the spatial aggregation '{df_indi['spatial_agg']}' in the SPATIAL_AGG_LIS dictionary."

                if not grid:
                    if provider == 'lis':
                        try:
                            grid_path = glob.glob(os.path.join(ROOT_PATH, f"ehipr/shp_malhas/default_grid/{agg_spt}/BR*_2022.shp"))[0]
                        except IndexError:
                            create_LIS_boundaries_shp(agg=agg_spt)
                            grid_path = glob.glob(os.path.join(ROOT_PATH, f"ehipr/shp_malhas/default_grid/{agg_spt}/BR*_2022.shp"))[0]
                            print(grid_path)

                        grid_info = {
                            'cod': 'GEOCODE', 
                            'name': 'NAME', 
                            'cod_mun': 'CD_MUN',
                            "uf": 'uf'
                        }
                    elif data_country == 'Brazil':
                        if agg_spt == 'state':
                            grid_path = read_state(year=2020)
                            grid_info = {'cod': 'code_state', 'name': 'abbrev_state', 
                                        'cod_mun': 'code_state'}
                        elif agg_spt == 'health_region':
                            grid_path = read_health_region()
                            grid_info = {'cod': 'code_health_region', 'name': 'name_health_region', 
                                        'cod_mun': 'code_health_region'}
                        else:
                            grid_path = read_municipality(code_muni="all", year=2022)
                            grid_info = {'cod': 'code_muni', 'name': 'name_muni', 'cod_mun': 'code_muni'}
                    else:
                        return "Error: The parameter 'grid' for data from outside Brazil must be "\
                                "provided and be a tuple with two elements: "\
                                "the path and the shapefile columns in dict format."
                else:
                    try:
                        grid_path, grid_info = grid
                    except ValueError:
                        return "Error: The parameter 'grid' must be a tuple with two elements: "\
                            "the path and the shapefile columns in dict format."
                    
                    if not {"cod", "name", "uf"}.issubset(grid_info.keys()):
                        return (
                            "Error: The parameter 'grid' informed must have three columns: 'cod', 'name' and 'uf', to "
                            "represent the code, name, and federal unit of each geographic region."
                        )

                final_path = os.path.join(input_path, provider, name, agg_time, agg_spt)

                _check_existence_dirs([final_path])

                filename = f"{df_indi['info']['title'].lower().replace(' ', '_')}"

                if file_crops_geom:
                    if file_crop_geom and file_crop_geom.endswith('shp'):
                        region_crop = os.path.basename(file_crop_geom).split('.')[0]
                        try:
                            filename = filename + "_" + REGION_ABBR[region_crop]
                        except Exception as e:
                            filename = filename + "_" + region_crop

                # Get the spatial and temporal aggregations and the indicator name from this dataframe
                try:
                    filename = f"{filename}_{SPATIAL_AGG_ABBR[agg_spt]}_{agg_time}"
                except KeyError:
                    return f"Error: Some information about the spatial aggregation is wrong: {agg_spt}."

                # TODO - paralelizar esse trecho de código
                try:
                    if polygon_agg != agg_spt:
                        polygon_agg = agg_spt
                        # Read the grid
                        try:
                            df_polygon = gpd.read_file(grid_path)
                        except Exception as e:
                            if agg_spt == 'state':
                                df_polygon = read_state(year=2020)
                                grid_info = {
                                    'cod': 'code_state', 
                                    'name': 'name_state'
                                }
                            elif agg_spt == 'health_region':
                                df_polygon = read_health_region()
                                grid_info = {
                                    'cod': 'code_health_region', 
                                    'name': 'name_health_region'
                                }
                            else:
                                # df_polygon = read_municipality(code_muni="all", year=2022)
                                # grid_info = {
                                #     'cod': 'code_muni', 
                                #     'name': 'name_muni'
                                # }
                                if provider != 'lis':
                                    df_polygon = read_municipality(
                                        code_muni="all", year=2022
                                    )
                                    grid_info = {
                                        "cod": "code_muni", 
                                        "name": "name_muni"
                                    }
                            df_polygon[grid_info['cod']] = df_polygon[grid_info['cod']].astype(int)

                            if df_polygon.crs is None:
                                df_polygon.crs = {'init': 'epsg:3857'}

                            grid_info["uf"] = "abbrev_state"

                        # Crop the polygon if the user specifies to do it
                        if region_crop:
                            with ProcessPoolExecutor(max_workers=CPU_COUNT) as executor:
                                future = executor.submit(__process_crop, df_polygon, grid_info, crop_info, file_crop_geom)
                                df_polygon = future.result()
                            # grid_info_cod = grid_info['cod_mun'] if 'cod_mun' in grid_info.keys() else grid_info['cod']
                            # crop_info = crop_info['cod_mun'] if 'cod_mun' in crop_info.keys() else crop_info['cod']

                            # df_polygon = __crop_geometry(gdf=df_polygon, 
                            #                             file_path=file_crop_geom,
                            #                             columns={'grid': grid_info_cod, 'crop': crop_info})
                    
                        df_polygon = df_polygon.astype({grid_info['cod']: int})
                        cod_polygon = df_polygon[grid_info['cod']].unique()

                    df[cod_col] = pd.to_numeric(df[cod_col], errors="coerce").astype(int)

                    # Filtrando o DataFrame para manter apenas as linhas com códigos presentes em cod_polygon
                    df = df[df[cod_col].isin(cod_polygon)]

                    if df.empty:
                        return "Error: No data found for the selected codes in the grid."

                    df["nome_mun"] = df[cod_col].map(
                        df_polygon.set_index(grid_info["cod"])[grid_info["name"]]
                    )

                    df["uf_mun"] = df[cod_col].map(
                        df_polygon.set_index(grid_info["cod"])[grid_info["uf"]]
                    )

                    # Criando um DataFrame com apenas as colunas necessárias para o merge
                    cols_merge = [cod_name for cod_name in [grid_info.get("cod", None), grid_info.get("name", None), grid_info.get("uf", None)] if cod_name]
                    df_metadata = df_polygon[cols_merge].drop_duplicates()

                    # Fazendo o merge no código
                    df = df.merge(
                        df_metadata,
                        how="left",
                        left_on=cod_col,
                        right_on=grid_info["cod"],
                        suffixes=("", "_polygon")
                    )
  
                    # Criando um dicionário para mapear cada código à sua geometria correspondente
                    cod_geometry_dict = {}

                    # Iterando sobre os códigos únicos e mapeando a geometria correspondente
                    unique_codes = df[cod_col].unique()

                    def get_geometry(codes_chunk):
                        """
                        Create a dictionary of geometries for each unique code in the chunk.

                        Parameters
                        ----------
                        codes_chunk : list
                            A list of unique codes in the chunk.

                        Returns
                        -------
                        dict
                            A dictionary of geometries for each unique code in the chunk.
                        """
                        cod_geometry_dict = {}
                        for cod in tqdm(sorted(codes_chunk), desc="Cropping polygons...", leave=False,  disable=True):
                            geometry = df_polygon.loc[df_polygon[grid_info['cod']] == cod, 'geometry'].iloc[0]
                            cod_geometry_dict[cod] = MultiPolygon([geometry]) if isinstance(geometry, Polygon) else geometry
                        return cod_geometry_dict

                    # Prepare the chunks of unique_codes
                    len_unique_codes = len(unique_codes)
                    n_chunks = len_unique_codes // CPU_COUNT if  len_unique_codes > CPU_COUNT else 1
                    unique_codes_chunks = list(chunk_list(sorted(unique_codes), n_chunks))

                    geometries = {}

                    with ThreadPoolExecutor(max_workers=CPU_COUNT) as executor:
                        # Submit each chunk to the executor
                        futures = [executor.submit(get_geometry, chunk) for chunk in unique_codes_chunks]

                        for i, future in enumerate(tqdm(as_completed(futures), total=len(futures))): #, desc="Processing chunks...")):
                            geometries.update(future.result())

                    # Adicionando a coluna de geometria ao DataFrame original
                    df['geometry'] = df[cod_col].map(geometries)

                    # Convertendo o DataFrame para um GeoDataFrame com o CRS apropriado
                    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')

                    if publish_later:
                        publish_path = os.path.join(JSON_FOLDER_PATH, f"{id_indi}_{agg_spt}_{agg_time}")

                    # Resetando o índice
                    gdf.reset_index(drop=True, inplace=True)

                    # Rounding the 'value' column
                    round_value = get_round_value(gdf, column_name=value_col, only_round=True)
                    if isinstance(round_value, dict):
                        return round_value["message"]
                    gdf[value_col] = pd.to_numeric(gdf[value_col], errors='coerce')
                    gdf[value_col] = gdf[value_col].round(round_value).astype(str)
                    
                    # FORMAT THE GEODATAFRAME DATE FIELD
                    add_to_data = None
                    time_aggregations = gdf[temp_col].unique()
                    name_date_col = ""

                    if len(time_aggregations) == 1 and time_aggregations[0] == 'week':
                        name_date_col = 'epiweek_start_date'
                        name_date_number_col = "epiweek_number"

                        if csv_week_pd is None:
                            return "Error: The csv file with the weekly data isn't available."

                        if not check_date_format(date=gdf[date_col].iloc[0]):
                            gdf_copy = gdf.copy()
                            dates = sorted(list(set([(date[:4], date[5:7]) for date in gdf_copy[date_col].unique()])))
                            try:
                                for year, week in dates:

                                    # Rules to find the week in the pandas table
                                    notna = gdf_copy[date_col].notna()
                                    contains_year_week = gdf_copy[date_col].str.contains(f'{year}-{week}', na=False)

                                    # Selectin the rows that contain the week
                                    gdf_years = gdf_copy.loc[notna & contains_year_week]

                                    filtered_csv_week_pd = csv_week_pd.loc[(csv_week_pd['Year'].astype('int') == int(year)) &
                                                            (csv_week_pd['Week'].astype('int') == int(week)), ["StartDate", "Week"]]

                                    if not filtered_csv_week_pd.empty:
                                        date = filtered_csv_week_pd.iloc[0]
                                        week = filtered_csv_week_pd.iloc[1]
                                        gdf.loc[contains_year_week, [date_col, name_date_number_col]] = [date, week]

                            except:
                                return "Error: Something went wrong when trying to format the "\
                                        f"date column: {date_col}."

                        else:
                            gdf = gdf.merge(
                                csv_week_pd[["StartDate", "Week"]],
                                left_on=date_col,
                                right_on="StartDate",
                                how="left"
                            ).rename(columns={"Week": name_date_number_col}).drop(columns=["StartDate"])

                        # Changes 'week' to 'epiweek' in the column temp_agg
                        gdf[temp_col] = TEMPORAL_AGG_ABBR[time_aggregations[0]]
                    elif len(time_aggregations) == 1 and time_aggregations[0] == 'month':
                        name_date_col = 'month_start_date'
                        name_date_number_col = "month_number"
                        add_to_data = relativedelta(months=1)

                        gdf[date_col] = pd.to_datetime(gdf[date_col], format='%Y-%m') + pd.offsets.MonthBegin(1) - pd.offsets.MonthBegin(1)
                        gdf[name_date_number_col] = gdf[date_col].dt.month
                    else:
                        name_date_col = 'year_start_date'
                        name_date_number_col = "year_number"
                        add_to_data = timedelta(days=365)

                        gdf[date_col] = pd.to_datetime(gdf[date_col], format='%Y')
                        gdf[name_date_number_col] = gdf[date_col].dt.year

                    # Casting the date column to datetime with the format '%Y-%m-%d'
                    gdf[date_col] = pd.to_datetime(gdf[date_col], format='%Y-%m-%d',
                                                   errors='coerce')
                    # Sorting the dataframe by the date column
                    gdf = gdf.sort_values(by=[date_col], 
                                          ascending=True).reset_index(drop=True)
                    
                    # Reordering DataFrame columns to match the expected database schema
                    # order_columns = ['cod', 'date', 'name', 'agg', 'agg_time', 'value', 'geometry']
                    # column_fields = [c for c in order_columns if c in gdf.columns]
                    # gdf = gdf[column_fields]

                    # Converting the date column to a string with the format '%Y-%m-%d'
                    gdf[date_col] = gdf[date_col].dt.strftime(DATE_FORMAT)

                    dates =  gdf[date_col].unique()

                    time_column = "time_agg"

                    # Renomeando as colunas para 'nome_mun' e 'uf_mun'
                    gdf.rename(
                        columns={
                            # Grid Columns
                            grid_info["name"]: "name_mun",
                            # grid_info["uf"]: "uf_mun",
                            grid_info["cod"]: "code_mun",
                            # Data Columns
                            data_columns["value"]: "value",
                            data_columns["spt_agg"]: "spatial_agg",
                            data_columns["temp_agg"]: time_column,
                            data_columns["name"]: "name_indicator",
                            data_columns["date"]: name_date_col,
                        },
                        inplace=True
                    )

                    gdf["data_source"] = provider
                    gdf = gdf.drop(data_columns["cod"], axis=1)

                    gdf = gdf[
                        [
                            "code_mun", "name_mun", "uf_mun", "data_source",
                            "name_indicator", name_date_number_col, name_date_col,
                            "time_agg", "spatial_agg", "value", "geometry"
                        ]
                    ]
                    # Creating the items files for each date
                    for index, date in tqdm(enumerate(dates), total=len(dates), desc='Creating the items files for each date'):
                        temp_gdf = deepcopy(gdf.loc[gdf[name_date_col] == date])

                        if index+1 < len(dates):
                            end_date = datetime.strptime(dates[index+1], 
                                                        DATE_FORMAT) - timedelta(days=1)
                        else:
                            if temp_gdf[time_column].unique()[0] != "epiweek":
                                end_date = (datetime.strptime(date, DATE_FORMAT) + 
                                            add_to_data) - timedelta(days=1)
                            else:
                                end_date = datetime.strptime(date, DATE_FORMAT)

                        end_date = end_date.strftime('%Y-%m-%d')

                        only_date = date.split(" ")[0]
                        filename_date = f"{filename}_{''.join(only_date.split('-'))}_"\
                                        f"{''.join(end_date.split('-'))}"
                        
                        # CREATING .geojson, .zip(from shp) and parquet items files
                        for extension in ['.geojson', '.shp', df_indi['extension']]:
                            file_path = os.path.join(final_path, 'items', only_date)
                            if region_crop:
                                file_path = os.path.join(file_path, region_crop)
                            driver = 'ESRI Shapefile' if extension == '.shp' else 'GeoJSON'
                            if extension == '.shp':
                                file_path = (os.path.join(file_path, 'shapefile'))
                            _check_existence_dirs([file_path])
                            asset_path = os.path.join(file_path, f"{filename_date}{extension}")
                            if extension == 'parquet':
                                asset_path = asset_path.replace('parquet', '.parquet')
                                temp_gdf.drop(columns=["geometry"]).to_parquet(
                                    asset_path
                                )
                            elif extension == '.csv':
                                temp_gdf.to_csv(asset_path, index=False)
                            else:
                                temp_gdf.to_file(asset_path, driver=driver)
                                if extension == '.shp':
                                    zip_file = asset_path.replace(f"{filename_date}"\
                                                                  f"{extension}", '')
                                    asset_path = shp_to_zip(zip_file, zip_file)
                                    # asset_path = shp_to_zip(asset_path.replace(f"{filename_date}"\
                                    #                                             f"{extension}", ''))

                    bbox = ','.join(list(gdf.total_bounds.astype('str')))
                    # CREATING THE STYLE FILE

                    '''if 'alert_level' not in name:
                        style_file = GeoServer.create_health_feature_style(layer_name=filename, 
                                                                            column_name='value', 
                                                                            gdf=gdf)
                    else:
                        style_file = GeoServer.create_health_feature_style(layer_name=filename, 
                                                                            column_name='value', 
                                                                            gdf=gdf,
                                                                            template_name='alert_level')'''
                    template = 'alert_level' if 'alert_level' in name else None
                    style_file = GeoServer.create_health_feature_style(
                        layer_name=filename,
                        column_name='value',
                        gdf=gdf,
                        template_name=template
                    )

                    # Make the file path where the items are stored
                    file_path = os.path.join(final_path, 'items', '*')
                    if region_crop:
                        file_path = os.path.join(file_path, region_crop)
                        publish_path = f'{publish_path}_{region_crop}'
                except KeyError:
                    return "Error: Some column name in the grid or tabular data is wrong!"

            # Making a list with the keywords to be used in the STAC
            # Need to improve the last item (country)
            keywords = [
                {"lang": "en", "subject": "Health"},
                {"lang": "en", "subject": provider},
                {"lang": "en", "subject": df_indi['info']['disease']},
                {"lang": "en", "subject": df_indi['info']['description']},
                {"lang": "en", "subject": "Vector"},
                {"lang": "en", "subject": agg_spt.title()},
                {"lang": "en", "subject": agg_time.title()},
                {"lang": "en", "subject": "Brazil"}
            ]

            if isinstance(region_crop, str):
                keywords.insert(-1, {"lang": "en", "subject": region_crop.title()})
            else:
                keywords.insert(-1, {"lang": "en", "subject": "Brazil"})
                region_crop = 'BR'

            try:
                # CREATING THE LAYER INFORMATION
                if style_file:
                    description = (
                        f"This is the {df_indi['info']['title'].lower()} "
                        f"aggregated by {agg_spt} and {agg_time if not 'epiweek' else 'epidemiological week'} to {region_crop}. "
                        f"This indicator {df_indi['info']['description'].lower()}"
                    )

                    if region_crop.lower() in list(REGION_ABBR.keys()):
                        region_crop = REGION_ABBR[region_crop.lower()]

                    title = f"{df_indi['info']['title'].lower().replace(' ', '_')}_"\
                            f"{region_crop}_{SPATIAL_AGG_ABBR[agg_spt]}_{agg_time}"

                    layer_info = {
                        'name': filename,
                        'title': title,
                        'description': description,
                        'style': style_file,
                        'bbox': bbox,
                        'path': file_path,
                        'keywords': keywords,
                        'gdf': gdf,
                        'attribute_data': name_date_col
                    }

                    if publish_later:

                        geojson_file = f'{publish_path}.geojson'
                        gdf.to_file(geojson_file, driver="GeoJSON")
                        layer_info['gdf'] = geojson_file

                        json_file = f'{publish_path}.json'
                        # Salva o dicionário como JSON
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(layer_info, f, ensure_ascii=False, indent=4)
                        layer_info = json_file

                    layers.append(layer_info)
            except:
                return "Error: Something went wrong with the style file!"

    return layers


def publish_data(layers: List[Dict[str, str]], 
                 gs_store: str,
                 time_regex: str,
                 root_data_path: str,
                 gs_service_url: Optional[str] = 'http://localhost:10190/geoserver', 
                 gs_username: Optional[str] = 'admin', 
                 workspace: Optional[str] = 'harmonize_health',#'bdc_lcc',
                 db_settings: Optional[dict] = None,
                 stac_url: Optional[str] = 'http://localhost:8080/',
                 hostname: Optional[str] = 'localhost',
                 additional_path: Optional[str] = None) -> Union[List[int], str]:
    """
        Publishes data to GeoServer and its metadata in STAC

        Parameters
        ----------
        layers : List[Dict[str, str]]
            List of dictionaries with layer information
        db : str
            Database name
        db_schema : str
            Database schema
        gs_store : str
            GeoServer store
        time_regex : str
            Time regex
        root_data_path : str
            Root data path
        gs_service_url : Optional[str], default value is 'http://localhost:10190/geoserver'
            GeoServer service url
        gs_username : Optional[str], default value is 'admin'
            GeoServer username
        gs_password : Optional[str], default value is 'geoserver'
            GeoServer password
        workspace : Optional[str], default value is 'bdc_lcc'
            GeoServer workspace
        db_username : Optional[str], default value is 'postgres'
            Database username
        db_password : Optional[str], default value is 'postgres'
            Database password
        db_port : Optional[int], default value is 5432
            Database port
        stac_url : Optional[str], default value is 'http://localhost:8080/'
            STAC url
        hostname : Optional[str], default value is 'localhost'
            Database hostname
        additional_path : Optional[str], default value is None
            Additional path

        Returns
        -------
        A list of collections IDs or a string with an error message.
    """
    json_file, geojson_file = '', ''
    remove_temp_files = False

    if not isinstance(layers, (list, dict)):
        return "Error: The 'layers' parameter must be a list with dictionaries or a dictionary!"

    if isinstance(layers, dict):
        print("READING THE FILES TO PUBLISH THE DATA...")
        layers_dict = layers.copy()
        layers = []
        remove_temp_files = True

        required_keys = ["name", "spatial_agg", "temporal_agg", "region"]
        if not all(key in layers_dict for key in required_keys):
            missing = [key for key in required_keys if key not in layers_dict]
            raise KeyError(f"The following keys are missing from the dictionary.: {missing}")
        json_path = os.path.join(JSON_FOLDER_PATH, f"{layers_dict.get('name')}_{layers_dict.get('spatial_agg')}_{layers_dict.get('temporal_agg')}.json")
        if "region" in layers_dict:
            json_file = json_path.replace('.json', f'_{layers_dict.get("region")}.json')
            
        # Abre e carrega o conteúdo
        with open(json_file, "r", encoding="utf-8") as f:
            dados = json.load(f)
        geojson_file = dados.get('gdf')
        gdf = gpd.read_file(geojson_file)
        dados['gdf'] = gdf
        layers.append(dados)        

    all_saved = []    
    gs_service_url = 'https://brazildatacube.dpi.inpe.br/harmonize/dev/'\
                     'geoserver' if hostname != 'localhost' else gs_service_url
    
    geo = GeoServer(
        service_url=gs_service_url, 
        workspace=workspace, 
        hostname=hostname,
        username=gs_username,
        store=gs_store,
        db_settings=db_settings
    )

    db = geo.db
    pg_schema = geo.db_schema
    pg_username = geo.db_user
    pg_password = geo.db_password
    pg_port = geo.db_port

    print(f'\nSAVING DATA IN DATABASE...')
    for layer in tqdm(layers, total=len(layers), desc='Saving data in the database'):
        # Saving data in the database
        response = save_data_db(
            gdf=layer['gdf'], 
            name=layer['name'],
            schema=pg_schema,
            db_columns=layer["gdf"].keys(),
            hostname=hostname, 
            port=pg_port,
            db=db,
            user=pg_username,
            password=pg_password,
            replace_table=True,
        )

        response = True
        all_saved.append(response)

        # Fixing layer path to include root_data_path if the host is not localhost
        if hostname != 'localhost':
            local_paths = glob.glob(layer['path'])
            layer['remote'] = f"{root_data_path}{layer['path'].split(root_data_path)[1]}"
            paths = [(path, f"{root_data_path}{path.split(root_data_path)[1]}") 
                      for path in local_paths]

    if not all(all_saved):
        return "Error: Some layer was not saved. Something went wrong with the database!"


    # Publishing data in GeoServer
    print('\nPUBLISHING DATA IN GEOSERVER AND MAKING THUMBNAILS...')
    
    # Publishing feature data in GeoServer
    try:
        attribute_date = layer.get("attribute_data", 'date')
        geo.publish_feature_data(layers=layers, 
                                 time_regex=time_regex,
                                 attribute=attribute_date, 
                                 dynamic_style=True,
                                 add_tile_cache=False)
    except GeoserverException:
        return "Error: Something went wrong in publishing feature data in GeoServer!"

    # Making thumbnails in GeoServer
    try:
        geo.make_thumbnail(url=gs_service_url, 
                           layers=layers, 
                           time_regex=time_regex)
    except GeoserverException:
        return "Error: Something went wrong in making thumbnails in GeoServer!"

    print("... Done")

    # Sending files to remote server if the host is not localhost
    if hostname != 'localhost':
        print("\nSENDING FILES TO REMOTE SERVER...")
        all_send = send_files_ssh(ssh=geo.connection, paths=paths)

        if all_send:
            print("... Done")
     
    # Adding tile cache in GeoServer
    add_tile_cache = []
    for layer in tqdm(layers, total=len(layers), desc='Adding tile cache in GeoServer layers...'): 
        layer_name = layer['name']
        layer_folder = layer['remote'] if hostname != 'localhost' else layer['path']

        add_tile_cache.append(geo._add_tile_cache(name=layer_name, path=layer_folder,
                                                  time_regex=time_regex, is_vector=True))
    if all(add_tile_cache):
        print("... Done")
     
    # Publishing data in STAC
    print('\nPUBLISHING DATA IN STAC...') 

    stac_url = 'https://brazildatacube.dpi.inpe.br/harmonize/dev/'\
               'stac/v1/' if hostname != 'localhost' else stac_url

    stac = STAC(service_url=stac_url, hostname=hostname)
    col_ids = []

    with stac.app.app_context():
        # Publishing metadata in STAC
        for layer in tqdm(layers, total=len(layers), desc="Publishing metadata in STAC..."):
            name, description = layer['name'], layer['description']
            title = layer['title']
            keywords = layer['keywords']
            version = layer['version'] if 'version' in layer.keys() else 1

            # Making a dictionary with layer metadata to update the STAC template
            # provided by edpu (edpu>templates>jsons>health.json)
            layer_metadata = {
                "name": name,
                "title": title,
                "description": description,
                "keywords": keywords,
                "version": version,
                "metadata": {
                    "wms": {
                        "url": f"{gs_service_url}/bdc_lcc/wms",
                        "layerName": f"bdc_lcc:{name}"
                    },
                    "sources": [{
                        "name": f"{name}",
                        "stacUri": f"{stac_url}collections/{name}-{version}",
                    }],
                    "datacite": {
                        "id": f"{name}",
                        "dates": [{
                            "date": "2024"
                        }],
                        "titles": {
                            "title": f"{name}"
                        },
                        "descriptions": [{
                            "lang": "en",
                            "description": f"{description}",
                            "descriptionType": "Abstract"
                        }],
                        "subjects": keywords
                    }
                }
            }

            # Adding additional path if provided. This step is used to 
            # inform the script the correct path where NGINX server is providing the 
            # items metadata
            args = {}
            if additional_path and isinstance(additional_path, str):
                args['additional_path'] = additional_path

            # Publishing metadata in STAC
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
                items_path = layer['remote'] if hostname != 'localhost' else layer['path']
                col_id = stac.publish_collection(data=layer_metadata, 
                                                 template='health', 
                                                 root_data_path=root_data_path, 
                                                 asset_names=ASSET_NAMES, 
                                                 del_output_file=False, 
                                                 items_path=items_path, **args)
                col_ids.append(col_id)
    if not all(col_ids):
        return "Error: Something went wrong in publishing metadata in STAC!"

    if hasattr(stac, 'connection'):
        response = stac.close_connection()

    if remove_temp_files:
        if os.path.exists(json_file):
            os.remove(json_file)
        if os.path.exists(geojson_file):
            os.remove(geojson_file)        

    print("... Done")
    return col_ids
