# inbuilt libraries
import os
import re
import zipfile
from typing import List, Optional
from datetime import datetime 


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



def shp_to_zip(input_path: str, 
               output_path: Optional[str] = None) -> str:
    """
    Converts a shapefile to a ZIP archive.

    Parameters
    ----------
    input_path : str
        Path of the shapefile.
    output_path : str, optional
        Path of the output ZIP file. If not provided, a ZIP will be created in the same directory as the input.

    Returns
    -------
    str
        Path to the created ZIP file.
    """
    
    files_to_zip = []
    suffixs = ['cpg', 'dbf', 'prj', 'shp', 'shx']
    files = os.listdir(input_path)
    for file in files:
        if any(file.endswith(suffix) for suffix in suffixs):
            file_to_zip = os.path.join(input_path, file)
            _check_existence_dirs([file_to_zip])
            files_to_zip.append(file_to_zip)
    if output_path:
        _check_existence_dirs([output_path])
        zip_file = f"{output_path}.zip"
    else:
        zip_file = os.path.join(input_path, f"{files_to_zip[0].split('.')[0]}.zip")
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
               nchunks: int) -> List: # type: ignore
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

