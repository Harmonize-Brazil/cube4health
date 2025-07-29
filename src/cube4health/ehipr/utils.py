# inbuilt libraries
import os
import re
import zipfile
from typing import Dict, List, Optional
from datetime import datetime 
from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor
)


# third-party libraries
from tqdm import tqdm
from paramiko import SSHClient


# custom libraries
from .config import CPU_COUNT
#from edpu.utils import files_ssh


def shp_to_zip(input_path: str, 
               output_path: Optional[str] = None) -> str:
    """
        This function converts shapefiles to zip.

    Parameters
    ----------
        input_path : str,
            Path of the shapefile.
        output_path : str, defaulta value is None,
            Path of the output zip file.

     Returns
    -------
        Path of the zip file
    """
    files_to_zip = []
    suffixs = ['cpg', 'dbf', 'prj', 'shp', 'shx']
    files = os.listdir(input_path)
    for file in files:
        if any(file.endswith(suffix) for suffix in suffixs):
            files_to_zip.append(os.path.join(input_path, file))

    zip_file= output_path if output_path else os.path.join(input_path, 
                                                          f"{files_to_zip[0].split('.')[0]}.zip")
    with zipfile.ZipFile(zip_file, 'w') as zip_ref:
        for file in files_to_zip:
            zip_ref.write(file, os.path.basename(file))

    return zip_file


def str_to_date(date_str: str) -> datetime.date:
    """
        Convert a string to datetime.date.

    Parameters
    ----------
        date_str : str,
            The string that contains the date.

    Returns
    -------
        The date in datetime.date format.
    """
    return datetime.strptime(date_str, '%Y-%m-%d').date()


def date_to_str(date: datetime.date) -> str:
    """
        Convert a datetime.date to string.

    Parameters
    ----------
        date : datetime.date,
            The datetime.date object.

    Returns
    -------
        A string that contains the date.
    """
    return date.strftime('%Y-%m-%d')


def check_date_format(date: str) -> bool:
    """
        Check if the date is in the correct format.

    Parameters
    ----------
        date : str
            The date to check.

    Returns
    -------
        True if the date is in the correct format, False otherwise.
    """
    DATE_PATTERN = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')
    return True if DATE_PATTERN.match(date) else False


def chunk_list(list_to_chunk: list, 
               nchunks: int) -> List:
    """
        Yield successive n-sized chunks from lst.

    Parameters
    ----------
        list_to_chunk : list
            The list to split.
        nchunks : int
            The size of the chunks.

    Returns
    -------
        Generator with chunks.
    """
    for i in range(0, len(list_to_chunk), nchunks):
        yield list_to_chunk[i:i + nchunks]

