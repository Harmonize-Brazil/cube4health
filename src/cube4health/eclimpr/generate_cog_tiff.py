"""Module providing functions to work with netCDF from ERA5-Land."""
import os
import rasterio
import rioxarray  # .rio in the xarray
import glob
import pandas as pd
import xarray as xr
from osgeo import gdal
from natsort import natsorted  # Correct order of filenames
from tqdm import tqdm

from cube4health.eclimpr.utils import read_files_inputs

# EPSG:4326 - WGS 84/World Geodetic System 1984, used in GPS. Source: https://epsg.io/4326 - Set up transformers, unit EPSG:4326 is degree

# -----------
# Functions to generate COG from netCDF Era5Land:
# -----------

def list_climate_format_files(file_paths, output_dir, variable_input, indicator_name_local, years_work, extension_folder, type_indicator, source):
    """
    List NetCDF or GRIB2 files in a directory, filter them by years, and convert them to Cloud Optimized GeoTIFF (COG).

    Parameters
    ----------
    file_paths : str
        Path with a set of NetCDF or GRIB2 files.
    output_dir : str
        Path to save COG image files.
    variable_input : str
        Name of the NetCDF or GRIB2 variable to be processed.
    indicator_name_local : str
        Indicator name to add to output files.
    years_work : list of str
        List of years to extract (e.g., ["2019", "2020"]).
    extension_folder : str
        Extension folder "epiweek" or "month".
    type_indicator : str
        Type of indicator, which can be: "temp" (temperature), "precip" (precipitation), "dewpoint" (dewpoint temperature), to be processed.
    source: str
        Source of climate data, can be Copernicus ERA5-Land 'era5land' or CPTEC (SAMeT or MERGE) 'cptec'.

    Returns
    -------
    None
    """

    # If data from Copernicus - ERA5Land
    if source == "era5land":

        if type_indicator == "temp" or type_indicator == "precip":

            # List all NetCDF files in the directory
            netcdf_files = [os.path.join(file_paths, f) for f in os.listdir(file_paths) if f.endswith(".nc")]
            netcdf_files = natsorted(netcdf_files)

            # Filter files by years and extension folder
            netcdf_path = read_files_inputs(list_files=netcdf_files, years_work=years_work,
                                            extension_folder=extension_folder, extension_file=".nc")

            print("\nCreating a Cloud Optimized GeoTIFF (.tif) for each NetCDF day file...")

            output_dir1 = os.path.join(output_dir, "aux_tifs")
            os.makedirs(output_dir1, exist_ok=True)

            if type_indicator == "temp":
                # Initialize progress bar
                for i, filename in enumerate(tqdm(netcdf_path, desc="Processing temperature NetCDF files")):
                    generate_geotiff_from_netcdf_temp(output_dir=output_dir1,
                                                      filename=filename,
                                                      variable_name=variable_input,
                                                      indicator_name_local=indicator_name_local,
                                                      source_era5land=True, # It is necessary convert from Kelvin to Celsius
                                                      show_vars=(i == 0))  # Only first file is how the list of variables into netCDF
            elif type_indicator == "precip":
                # Initialize progress bar
                for i, filename in enumerate(tqdm(netcdf_path, desc="Processing precipitation NetCDF files")):
                    generate_geotiff_from_netcdf_precip_era5land(output_dir=output_dir1,
                                                                 filename=filename,
                                                                 variable_name=variable_input,
                                                                 indicator_name_local=indicator_name_local,
                                                                 show_vars=(i == 0))  # Only first file is how the list of variables into netCDF

        elif type_indicator == "rhumidity":
            # Define temp and dewpoint local with input data
            temp_paths = os.path.join(file_paths, "temp")
            dewpoint_paths = os.path.join(file_paths, "dewpoint")

            # Check if both directories exist
            if not os.path.isdir(temp_paths):
                raise FileNotFoundError(f"Temperature directory not found: {temp_paths}")

            if not os.path.isdir(dewpoint_paths):
                raise FileNotFoundError(f"Dewpoint directory not found: {dewpoint_paths}")

            # List all temperature NetCDF files in the directory 'temp'
            temp_files = [os.path.join(temp_paths, f) for f in os.listdir(temp_paths) if f.endswith(".nc")]
            temp_files = natsorted(temp_files)

            # List all dewpoint temperature NetCDF files in the directory 'dewpoint'
            dewpoint_files = [os.path.join(dewpoint_paths, f) for f in os.listdir(dewpoint_paths) if f.endswith(".nc")]
            dewpoint_files = natsorted(dewpoint_files)

            # create temp and dewpoint dirs
            output_temp_dir = os.path.join(output_dir, "aux_tifs", "temp")
            os.makedirs(output_temp_dir, exist_ok=True)
            output_dewpoint_dir = os.path.join(output_dir, "aux_tifs", "dewpoint")
            os.makedirs(output_dewpoint_dir, exist_ok=True)

            # Filter files by years and extension folder
            temp_path = read_files_inputs(list_files=temp_files,
                                          years_work=years_work,
                                          extension_folder=extension_folder,
                                          extension_file=".nc")

            # Filter files by years and extension folder
            dewpoint_path = read_files_inputs(list_files=dewpoint_files,
                                              years_work=years_work,
                                              extension_folder=extension_folder,
                                              extension_file=".nc")

            print("\nCreating a Cloud Optimized GeoTIFF (.tif) for each NetCDF day file...")

            # Initialize progress bar
            for i, filenamet in enumerate(tqdm(temp_path, desc="Processing temperature NetCDF files")):
                generate_geotiff_from_netcdf_temp(output_dir=output_temp_dir,
                                                  filename=filenamet,
                                                  variable_name=variable_input[0],
                                                  indicator_name_local="temp",
                                                  source_era5land=True, # It is necessary convert from Kelvin to Celsius
                                                  show_vars=(i == 0))  # Only first file is how the list of variables into netCDF

            # Initialize progress bar
            for i, filenamed in enumerate(tqdm(dewpoint_path, desc="Processing dewpoint temperature NetCDF files")):
                generate_geotiff_from_netcdf_temp(output_dir=output_dewpoint_dir,
                                                  filename=filenamed,
                                                  variable_name=variable_input[1],
                                                  indicator_name_local="dewpoint",
                                                  source_era5land=True, # It is necessary convert from Kelvin to Celsius
                                                  show_vars=(i == 0))  # Only first file is how the list of variables into netCDF


        else:
            raise ValueError("Erro: type_indicator must be defined.")

    # If data from CPTEC - SAMeT or MERGE
    elif source == "cptec":
        if type_indicator == "temp":

            # List all NetCDF files in the directory
            netcdf_files = [os.path.join(file_paths, f) for f in os.listdir(file_paths) if f.endswith(".nc")]
            netcdf_files = natsorted(netcdf_files)

            # Filter files by years and extension folder
            netcdf_path = read_files_inputs(list_files=netcdf_files, years_work=years_work,
                                            extension_folder=extension_folder, extension_file=".nc")

            print("\nCreating a Cloud Optimized GeoTIFF (.tif) for each NetCDF day file...")

            output_dir1 = os.path.join(output_dir, "aux_tifs")
            os.makedirs(output_dir1, exist_ok=True)

            # Initialize progress bar
            for i, filename in enumerate(tqdm(netcdf_path, desc="Processing temperature NetCDF files")):
                generate_geotiff_from_netcdf_temp(output_dir=output_dir1,
                                                        filename=filename,
                                                        variable_name=variable_input,
                                                        indicator_name_local=indicator_name_local,
                                                        source_era5land=False, # It is not necessary convert from Kelvin to Celsius
                                                        show_vars=(i == 0))  # Only first file is how the list of variables into netCDF
        elif type_indicator == "precip":
            # List all NetCDF files in the directory
            grib2_files = [os.path.join(file_paths, f) for f in os.listdir(file_paths) if f.endswith(".grib2")]
            grib2_files = natsorted(grib2_files)

            # Filter files by years and extension folder
            grib2_path = read_files_inputs(list_files=grib2_files, years_work=years_work,
                                            extension_folder=extension_folder, extension_file=".nc")

            print("\nCreating a Cloud Optimized GeoTIFF (.tif) for each NetCDF day file...")

            output_dir1 = os.path.join(output_dir, "aux_tifs")
            os.makedirs(output_dir1, exist_ok=True)

            # Initialize progress bar
            for i, filename in enumerate(tqdm(grib2_path, desc="Processing precipitation GRIB2 files")):
                generate_geotiff_from_grib2_precip_cptec(output_dir=output_dir1,
                                                        filename=filename,
                                                        variable_name=variable_input,
                                                        indicator_name_local=indicator_name_local,
                                                        show_vars=(i == 0))  # Only first file is how the list of variables into netCDF)

    else:
        raise ValueError("Erro: source must be defined.")

    print("... Done")


def generate_geotiff_from_netcdf_temp(output_dir, filename, variable_name, indicator_name_local, source_era5land, show_vars=False):
    """
    Converts temperature NetCDF data into Cloud Optimized GeoTIFF (COG) format for each day and stores the result in the specified output directory.

    Parameters
    ----------
    output_dir : str, optional
        The directory where the output Cloud Optimized GeoTIFF (COG) files will be stored.
    filename : str
        The NetCDF file to process.
    variable_name : str
        The name of the variable in the NetCDF file to extract (e.g., "2m_temperature").
    indicator_name_local : str
        The local name for the indicator, used in the output filenames (e.g., "max_temperature").
    source_era5land: bool
        Source of climate data, can be Copernicus ERA5-Land or CPTEC (SAMeT). If is True, it's necessary convert from Kelvin to Celsius.
    show_vars : bool, optional
        If True, prints the list of variables available in the NetCDF file. Default is False.

    Returns
    -------
    None
        This function does not return any value. It generates COG files for each day.

    Notes
    -----
    The temperature values are converted from Kelvin to Celsius if are from ERA5-Land.
    """

    # Open the NetCDF file
    dataset = xr.open_dataset(filename)

    # CRS of the NetCDF
    # print(dataset.crs)

    # Show variables
    if show_vars:
        print("Variables:", list(dataset.data_vars))

    # Check if variable exists
    if variable_name not in dataset:
        raise ValueError(f"Error: Variable '{variable_name}' not found in the NetCDF file.")

    # Extract the variable
    raster_days = dataset[variable_name]

    # Loop over each day
    for i in range(raster_days.shape[0]):
        ras = raster_days.isel(time=i)

        if source_era5land is True:
            # If source is from Era5-Land is True, - Convert from Kelvin to Celsius
            ras.values -= 273.15
            # It's not necessary convert from Kelvin to Celsius, SAMeT data is already in Celsius

        # Extract the date from the time dimension
        name_date = pd.to_datetime(ras.time.values).strftime('%Y-%m-%d')

        # Construct output filename
        #tiff_out = os.path.join(output_dir, "aux_tifs", f"daily_{indicator_name_local}_{name_date}.tif")
        tiff_out = os.path.join(output_dir, f"daily_{indicator_name_local}_{name_date}.tif")

        # # Define GeoTIFF metadata
        # lat = dataset['latitude'].values
        # lon = dataset['longitude'].values

        # #transform = from_origin(lon.min(), lat.max(), abs(lon[1]-lon[0]), abs(lat[1]-lat[0]))
        # # Calcula a resolução espacial (tamanho do pixel)
        # res_x = (lon.max() - lon.min()) / (len(lon) - 1)  # Largura do pixel
        # res_y = (lat.max() - lat.min()) / (len(lat) - 1)  # Altura do pixel

        # # Ajuste na origem do canto superior esquerdo adicionando metade do pixel
        # transform = Affine(res_x, 0, lon.min() - res_x / 2, 0, -res_y, lat.max() + res_y / 2)

        # # Profile GeoTIFF
        # profile = {
        #     'driver': 'GTiff',
        #     'count': 1,  # number of bands
        #     'dtype': 'float32',
        #     'crs': 'EPSG:4326',
        #     'transform': transform,
        #     'width': len(lon),
        #     'height': len(lat)
        # }

        # # Open output GeoTIFF file and save data
        # with rasterio.open(tiff_out, 'w', **profile) as dst:
        #     dst.write(ras, 1)

        # https://gis.stackexchange.com/questions/323317/converting-netcdf-dataset-array-to-geotiff-using-rasterio-python
        ras.rio.write_crs("epsg:4326", inplace=True)

        ras.rio.to_raster(tiff_out)

        # Construct output filename
        #cog_out = os.path.join(output_dir, "aux_tifs", f"daily_{indicator_name_local}_{name_date}_COG.tif")
        cog_out = os.path.join(output_dir, f"daily_{indicator_name_local}_{name_date}_COG.tif")

        convert_to_cog_gdal(tiff_out, cog_out)

        os.remove(tiff_out)

    #print(f"Cloud Optimized GeoTIFF file successfully created for {filename}.")


def convert_to_cog_gdal(input_tiff_file, output_cog_file):
    """
    Convert a file GeoTIFF to format Cloud Optimized GeoTIFF (COG).

    Parameters
    ----------
    input_tiff_file : str
        File path of GeoTIFF to be converted
    output_cog_file : str
        File path to save Cloud Optimized GeoTIFF file.

    Returns
    -------
    None
    """

    # block_size = 256 - sets the tile width and height in pixels. Must be divisible by 16. https://gdal.org/drivers/raster/cog.html#general-creation-options - Marcos

    # Calculate statistics for the input GeoTIFF
    input_dataset = gdal.Open(input_tiff_file, gdal.GA_Update)
    for band_num in range(1, input_dataset.RasterCount + 1):
        band = input_dataset.GetRasterBand(band_num)
        band.ComputeStatistics(False)  # False = do not calculate approximated
        band.SetMetadata(band.GetMetadata())  # Update metadata with stats
    input_dataset = None  # Close dataset to save changes

    # Convert the input GeoTIFF to COG
    gdal.Translate(
        output_cog_file,
        input_tiff_file,
        format="COG",     # Use the COG driver
        creationOptions=[
            "COMPRESS=DEFLATE",
            "BLOCKSIZE=256",
            "OVERVIEWS=IGNORE_EXISTING"
        ]
    )

   #print(f"File COG save as {output_cog_file}")


def save_raster(output_path, data, reference_raster):
    """
    Save a raster to a GeoTIFF file.

    Parameters
    ----------
    output_path : str
        Path where the raster will be saved.
    data : numpy.ndarray
        Raster data to save.
    reference_raster : numpy.ndarray
        Reference raster for metadata (e.g., transform, CRS).

    Returns
    -------
    None
    """
    with rasterio.open(reference_raster) as src:
        profile = src.profile.copy()  # Copy metadata
        dtype = src.dtypes[0]   # get dtype of first band
        crs = src.crs
        transform = src.transform

    profile = {
        'driver': 'GTiff',
        'height': data.shape[0],
        'width': data.shape[1],
        'count': 1,
        'dtype': dtype,
        'crs': crs,
        'transform': transform,
        'nodata': -9999  # Define an apropriated value to nodata
    }

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(data, 1)


def generate_geotiff_from_netcdf_precip_era5land(output_dir, filename, variable_name, indicator_name_local, show_vars=False):
    """
    Converts precipitation NetCDF data into Cloud Optimized GeoTIFF (COG) format for each day and stores the result in the specified output directory.

    Parameters
    ----------
    output_dir : str, optional
        The directory where the output Cloud Optimized GeoTIFF (COG) files will be stored.
    filename : str
        The NetCDF file to process.
    variable_name : str
        The name of the variable in the NetCDF file to extract (e.g., "total_precipitation").
    indicator_name_local : str
        The local name for the indicator, used in the output filenames (e.g., "max_precipitation").
    show_vars : bool, optional
        If True, prints the list of variables available in the NetCDF file. Default is False.

    Returns
    -------
    None
        This function does not return any value. It generates COG files for each day.

    Notes
    -----
    The precipitation values are converted from Kelvin to Celsius.
    """
    # Open the NetCDF file
    dataset = xr.open_dataset(filename)

    # CRS of the NetCDF
    # print(dataset.crs)

    # Show variables
    if show_vars:
        print("Variables:", list(dataset.data_vars))

    # Check if variable exists
    if variable_name not in dataset:
        raise ValueError(f"Error: Variable '{variable_name}' not found in the NetCDF file.")

    # Extract the variable
    raster_days = dataset[variable_name]

    # Loop over each day
    for i in range(raster_days.shape[0]):
        ras = raster_days.isel(time=i)

        # Convert from Meter to Millimeter = value * 1000
        ras.values *= 1000

        # Extract the date from the time dimension
        name_date = pd.to_datetime(ras.time.values).strftime('%Y-%m-%d')

        # Construct output filename
        #tiff_out = os.path.join(output_dir, "aux_tifs", f"daily_{indicator_name_local}_{name_date}.tif")
        tiff_out = os.path.join(output_dir, f"daily_{indicator_name_local}_{name_date}.tif")

        ras.rio.write_crs("epsg:4326", inplace=True)

        ras.rio.to_raster(tiff_out)

        # Construct output filename
        #cog_out = os.path.join(output_dir, "aux_tifs", f"daily_{indicator_name_local}_{name_date}_COG.tif")
        cog_out = os.path.join(output_dir, f"daily_{indicator_name_local}_{name_date}_COG.tif")

        convert_to_cog_gdal(tiff_out, cog_out)

        os.remove(tiff_out)

    #print(f"Cloud Optimized GeoTIFF file successfully created for {filename}.")


def generate_geotiff_from_grib2_precip_cptec(output_dir, filename, variable_name, indicator_name_local, show_vars=False):
    """
    Converts precipitation GRIB2 data into Cloud Optimized GeoTIFF (COG) format for each day and stores the result in the specified output directory.

    Parameters
    ----------
    output_dir : str, optional
        The directory where the output Cloud Optimized GeoTIFF (COG) files will be stored.
    filename : str
        The GRIB2 file to process.
    variable_name : str
        The name of the variable in the GRIB2 file to extract (e.g., "total_precipitation").
    indicator_name_local : str
        The local name for the indicator, used in the output filenames (e.g., "max_precipitation").
    show_vars : bool, optional
        If True, prints the list of variables available in the NetCDF file. Default is False.

    Returns
    -------
    None
        This function does not return any value. It generates COG files for each day.

    """
    # Read GRIB2 file - using cfgrib engine to handle GRIB2 structures
    dataset = xr.open_dataset(filename,
                              engine='cfgrib',
                              backend_kwargs={"filter_by_keys": {"typeOfLevel": "surface"}},
                              decode_timedelta=True)

    # CRS of the GRIB2
    # print(dataset.attrs)

    # Show variables
    if show_vars:
        print("Variables:", list(dataset.data_vars))

    # Check if variable exists
    if variable_name not in dataset:
        raise ValueError(f"Error: Variable '{variable_name}' not found in the GRIB2 file.")

    # Extract the variable
    raster_days = dataset[variable_name]

    # Convert from Meter to Millimeter = value * 1000 - It's not necessary for MERGER data
    # raster_days.values *= 1000

    # Adjusts the longitude if it is in the range [0, 360]
    # print(raster_days.longitude.values.min(), raster_days.longitude.values.max())
    if raster_days.longitude.max() > 180:
        raster_days = raster_days.assign_coords(
            longitude=((raster_days.longitude + 180) % 360) - 180
        )
        raster_days = raster_days.sortby("longitude")

    # Define CRS
    raster_days.rio.write_crs("EPSG:4326", inplace=True)

    # Extract the date from the time dimension
    name_date = pd.to_datetime(raster_days.time.values).strftime("%Y-%m-%d")

    # Construct output filename
    #tiff_out = os.path.join(output_dir, "aux_tifs", f"daily_{indicator_name_local}_{name_date}.tif")
    tiff_out = os.path.join(output_dir, f"daily_{indicator_name_local}_{name_date}.tif")

    raster_days.rio.to_raster(tiff_out)

    # Construct output filename
    #cog_out = os.path.join(output_dir, "aux_tifs", f"daily_{indicator_name_local}_{name_date}_COG.tif")
    cog_out = os.path.join(output_dir, f"daily_{indicator_name_local}_{name_date}_COG.tif")

    convert_to_cog_gdal(tiff_out, cog_out)

    os.remove(tiff_out)

    # Finds and removes .idx files associated with GRIB
    idx_pattern = filename + '*.idx'
    for idx_file in glob.glob(idx_pattern):
        os.remove(idx_file)
        #print(f"Deleted: {idx_file}")

    #print(f"Cloud Optimized GeoTIFF file successfully created for {filename}.")

