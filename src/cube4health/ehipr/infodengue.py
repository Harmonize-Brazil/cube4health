# inbuilt libraries
import os
import re
import time
import psutil
from typing import Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

# third-party libraries
import geobr
import requests
import pandas as pd
import geopandas as gpd
from tqdm import tqdm

# custom libraries
from .utils import check_date_format
from .ehipr import _check_existence_dirs, _get_indicator_info # TODO :remover importacao check_exist

from .config import CPU_COUNT

# URL of the API
ROUTE = "https://api.mosqlimate.org/api/datastore/infodengue/"

# IDs of the disease
DISEASE_IDS = {
    'dengue': 'dengue',
    'chikungunya': 'chik', 
    'zika': 'zika'
}


def __batch_generator(data, batch_size):
    batch = []
    for item in data:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

def __check_memory_limit(max_memory_usage: int) -> bool:
    """
    Check if the memory usage is above the limit.

    Parameters
    ----------
    max_memory_usage : int
        The maximum memory usage allowed.

    Returns
    -------
    True if the memory usage is above the limit, False otherwise.
    """
    memory_info = psutil.virtual_memory()
    if memory_info.percent >= max_memory_usage:
        return True
    return False


def compose_url(disease: str, 
                start_date: str, 
                end_date: str, 
                page: Optional[int]=1, 
                code: Optional[Union[str, int]]=None) -> str:
    """
    Composes the URL to fetch data from the API

    Parameters
    ----------
    disease : str
        The disease to fetch data from.
    start_date : str
        The start date to fetch data from.
    end_date : str
        The end date to fetch data from.
    page : Optional[int]
        The page number to fetch data from.
    code : Optional[Union[str, int]]
        The code to fetch data from.

    Returns
    -------
    The URL to fetch data from.
    """
    pagination = f"?page={page}&per_page=100&"

    # Making the filter request according to the code information (geocode or uf)
    if isinstance(code, int) or (isinstance(code, str) and len(code) > 2):
        filters = f"disease={disease}&start={start_date}&end={end_date}&geocode={code}"
    elif isinstance(code, str) and len(code) == 2:
        filters = f"disease={disease}&start={start_date}&end={end_date}&uf={code.upper()}"
    else:
        filters = f"disease={disease}&start={start_date}&end={end_date}"

    return ROUTE + pagination + filters


def fetch_data(session: requests.Session, url: str, headers: dict) -> dict:
    """
    Uses ClientSession to create the async call to the API

    Parameters
    ----------
    session : requests.Session
        The session to use.
    url : str
        The URL to fetch data from.

    Returns
    -------
    The response from the API in JSON format.
    """
    response = session.get(url, headers=headers)
    return response.json()


def attempt_delay(session: requests.Session, url: str, headers: dict) -> dict:
    """
    The request may fail. This method adds a delay to the failing requests

    Parameters
    ----------
    session : requests.Session
        The session to use.
    url : str
        The URL to fetch data from.

    Returns
    -------
    The response from the API in JSON format or calls the function again if it fails.
    """
    try:
        return fetch_data(session=session, url=url, headers=headers)
    except Exception as e:
        time.sleep(0.2)
        return attempt_delay(session=session, url=url, headers=headers)


def __save_to_csv(data: pd.DataFrame, 
                  filename: str, 
                  mode: Optional[str]=None,
                  overwrite: Optional[bool]=False) -> bool:
    """
    Save data to a CSV file.

    Parameters
    ----------
    data : list
        The data to save.
    filename : str
        The name of the file to save to.
    mode : str
        The mode to open the file in.
    """
    # Checking if the directory exists. If not, create it
    _check_existence_dirs([os.path.dirname(filename)])

    # Overwriting the file
    if overwrite:
        if os.path.exists(filename):
            os.remove(filename)
        mode = 'w'

    # Checking if the document exists. If not, set the mode to 'w'
    if not mode:
        mode = 'a' if os.path.exists(filename) else 'w'

    # Casting the data to a DataFrame and saving it to a CSV file
    try:
        data.to_csv(filename, mode=mode, index=False)
        return True
    except Exception as e:
        return False


def __request_data(disease: str, 
                   start_date: str, 
                   end_date: str, 
                   token: str,
                   geocode: Optional[Union[str, int]]=[None]) -> Union[list, str]: # type: ignore
    """
    Fetch infoDengue indicator data from the API.

    Parameters
    ----------
    disease : str
        The disease to get data from.
    start_date : str
        The start date of the data to get.
    end_date : str
        The end date of the data to get.

    Returns
    -------
    The data from the API in JSON format concatened in a list or 
    a string with the error message.

    """
    # Checking if the parameters are strings
    if not all(isinstance(arg, str) for arg in [disease, start_date, end_date]):
        return "Error: The parameters must be a string."

    # Checking if the dates are in the correct format
    if not check_date_format(date=start_date) and not check_date_format(date=end_date):
        return "Error: The start_date and end_date is not in the correct format (YYYY-MM-DD)."    

    #Checking if the geocode is an instance of a dict. If yes, open the shapefile to get the geocodes
    if geocode and isinstance(geocode, dict):
        try:
            geocode = gpd.read_file(geocode['path'])[geocode['code']].tolist()
        except IOError:
            return "Error: The filepath provided for the geocode variable is not valid."

    # Requesting data in parallel
    result = []
    headers = {"X-UID-Key": token}
    with requests.Session() as session:
        for code in tqdm(geocode, desc="Processing geocode"):
            url = compose_url(disease=disease,
                                start_date=start_date,
                                end_date=end_date, 
                                code=code)
            data = attempt_delay(session, url, headers)
            try:
                total_pages = data["pagination"]["total_pages"]
                result.extend(data["items"])
                futures = {}
            except KeyError:
                return 'Error: The API does not return any data. Check the parameters.'

            with ThreadPoolExecutor(max_workers=CPU_COUNT) as executor:
                    # Start the load operations and mark each future with its URL
                    for page in range(1, total_pages + 1):
                        url = compose_url(disease=disease,
                                    start_date=start_date,
                                    end_date=end_date, 
                                    code=code,
                                    page=page)
                        futures[executor.submit(attempt_delay, session,url, headers)] = url
                    for future in tqdm(as_completed(futures), 
                                        total=len(futures), 
                                        desc="Processing results..."):
                        _ = futures[future]
                        resp = future.result()
                        # The conditional is incorporating the first page
                        if result: 
                            resp["items"].extend(result)
                            result = []
                        for i in resp['items']:
                            yield i


def get_infodengue_indicator(indicator: str, 
                             start_date: str, 
                             end_date: str, 
                             mosqlimate_token: str,
                             output_path: Optional[str]=None,
                             geocode: Optional[Union[str, int]]=[None],
                             overwrite: Optional[bool]=False) -> Union[bool, str]:
    """
    Get infoDengue indicator data from the API.

    Parameters
    ----------
    disease : str
        The disease to get data from.
    start_date : str
        The start date of the data to get.
    end_date : str
        The end date of the data to get.
    output_path : str
        The path to save the data to.
    geocode : str or int
        The geocode to get data from.
    overwrite : bool
        Whether to overwrite the data if it already exists.

    Returns
    -------
    A boolean if the data was successfully retrieved and saved in CSV format, or a string
    with the error message if the data could not be retrieved.
    """

    def adjust_df() -> pd.DataFrame:
        """
        Adjusting the dataframe to the desired format.

        Parameters
        ----------
        df : list of dicts
            The list of items to adjust.
        spt_agg : list of bool
            The list of spatial aggregations.

        Returns
        -------
        The adjusted dataframe.
        """
        df = pd.DataFrame(all_items)
        df['agg_time'] = 'week'
        df['agg'] =  'municipality' if all(spt_agg) else 'state'
        df['name'] = indicator
        pd.set_option('future.no_silent_downcasting', True)
        df.fillna(0, inplace=True)
        return df[['name', 'data_iniSE', 'agg', 'agg_time', 'municipio_geocodigo', field_name]]

    # Checking if the disease is in the allowed list
    try:
        indicator_info = _get_indicator_info(provider='infodengue', id=indicator)
        
        if not indicator_info.get("status"):
            return indicator_info.get("message")

        indicator_info = indicator_info.get("indicator")

        field_name = indicator_info.get('field_name')

        disease = indicator_info.get('disease')
        disease_id = DISEASE_IDS[disease.lower()]
    except Exception as e:
        return "Error: The disease must be one of the "\
               "following: %s." % ', '.join(DISEASE_IDS.keys())
    
    try:
        if not isinstance(mosqlimate_token, str) or not mosqlimate_token:
            raise Exception("The 'token' is empty or is not a string.")

        try:
            _, token = mosqlimate_token.split(':')
            _ = re.match(r"^[a-f0-9\-]{36}[a-z]?$", token) is not None
        except ValueError:
            raise Exception("The 'token' is invalid.")
        
    except Exception as e:
        return f"Error: {str(e)}"
    
    try:
        data = __request_data(disease=disease_id,
                            start_date=start_date,
                            end_date=end_date,
                            token=mosqlimate_token,
                            geocode=geocode)
        
        if isinstance(data, str):
            raise Exception(data)

        # Defining if the spatial aggregation is by state or by municipality. If the geocode
        # is None or if the length of the geocode is not 2, the aggregation is by municipality.
        # Otherwise, the aggregation is by state.
        spt_agg = [True if code is None or len(code) != 2 else False for code in geocode]
        all_items = []

    except Exception as e:
        return f"Error: {str(e)}"

    try:
        # Setting the output path to save the data in the csv format
        output_path = os.path.join(output_path, indicator)
        _check_existence_dirs([output_path])
        filepath = os.path.join(output_path, f'{indicator}.csv')

        # Overwriting the file if it already exists
        if os.path.exists(filepath) and overwrite:
            os.remove(filepath)

        # The adjust_df function is used to adjust the dataframe to the desired format. There
        # is no need to pass the spt_agg and the dataframe because they are already defined in the
        # function scope.
        for item in tqdm(data, desc="Saving data to CSV file..."):
            all_items.append(item)
            if len(all_items) == 1000:
                df = adjust_df().drop_duplicates()
                # print(filepath)
                saved = __save_to_csv(data=df, filename=filepath)
                all_items = []

        # Saving the remaining data
        if all_items:
            df = adjust_df().drop_duplicates()
            saved = __save_to_csv(data=df, filename=filepath)
            all_items = []
            return output_path
        raise Exception("Cannot save the indicator!") 
    except KeyError as e:
        return "Error: some parameter is not valid." if 'pagination' in str(e) else "Error: the "\
                "key 'data_iniSE' was not found in the data."
    except TypeError:
        return "Error: something went wrong when parsing the data to a Pandas DataFrame."
    except Exception as e:
        return f"Error: {str(e)}"

