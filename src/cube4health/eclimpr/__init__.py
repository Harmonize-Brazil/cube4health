"""Top-level package for eclimpr."""

from .download_era5land_data import get_data_zenodo, get_data_era5land
from .download_cptec_ftp_data import get_data_ftp_cptec
from .utils_bd import process_climate_postgres
from .process_shapefile import processed_shapefile
from .process_climate_indicator import *


__author__ = """Adeline Marinho Maciel"""
__email__ = 'adelinemaciel22@gmail.com'
__version__ = '0.1.0'

__all__ = [
    "get_data_zenodo",
    "get_data_era5land",
    "get_data_ftp_cptec",
    "process_climate_postgres",
    "process_climate_indicator",
    "processed_shapefile"
]
