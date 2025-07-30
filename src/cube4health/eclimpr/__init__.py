# File: eclimpr/__init__.py

from .download_era5land_data import get_data_zenodo
from .download_era5land_data import get_data_era5land
from .download_cptec_ftp_data import get_data_ftp_cptec
from .utils import *
from .generate_cog_tiff import *
from .generate_png_file import *
from .process_shapefile import *
from .extract_aggregations import *
from .process_era5land_temp import *
from .process_era5land_precip import *
from .process_era5land_anomaly import *
from .process_era5land_rhumidity import *
from .process_cptec_temp import *
from .process_cptec_precip import *
from .utils_bd import process_climate_postgres

__author__ = """Adeline Marinho Maciel"""
__email__ = 'adelinemaciel22@gmail.com'
__version__ = '0.1.0'

# __all__ = (
#     'get_data_zenodo',
#     'get_data_ftp_cptec',
#     'read_files_inputs',
# )
