"""Module providing a function to generate relative humidity files from ERA5-Land."""
import os
import gc
import geopandas as gpd
from shapely.geometry import box

from .utils import (
    write_epiweeks_to_file,
    create_new_dir,
    create_epiweek_dir,
    move_rhumidity_COG_files,
    move_rhumidity_shapefiles_files,
    create_months_dir,
    get_default_color_file
)
from .generate_cog_tiff import list_climate_format_files
from .process_shapefile import (
    crop_raster_by_area_rhumidity,
    save_map_shapefile
)
from .extract_aggregations import extract_relative_humidity

# -----------
# Functions:
# -----------

def process_era5land_rhumidity_epiweek(main_dir, output_dir, folder_name, shapefile_path, variable_name, years, indicator_name = "humidity", color_png_file=None, interval_file_path=None, provide_interval=False):
    """
    Process Era5-Land relative humidity data by epidemiological week.

    Calculates relative humidity (RH) using the formula:
    RH (%) = 100 * exp((b * c * (Td - T)) / ((c + Td) * (c + T)))
    where b = 17.625, c = 243.04, T is 2m temperature, and Td is 2m dewpoint temperature.


    Parameters
    ----------
    main_dir : str
        Directory path where the NetCDF files are stored.
    output_dir : str
        Directory path where the indicators generated will be stored. 
    folder_name : str
        Name of the folder to be created for output files.
    shapefile_path : str
        Path to the Shapefile of the study area.
    variable_name : str
        Variable name in the NetCDF file.
    years : list or str
        List of years or a single year to process.
    indicator_name : str
        Indicator name for output files (max 20 characters).
    color_png_file : str
        Path to the file with color ranges for PNG output. Default is provided by package
    interval_file_path : str, optional
        Path to the custom interval file, if provide_interval is True.
    provide_interval : bool, optional
        If True, allows the user to provide a custom interval file. Default is False (use epiweek = epidemiological weeks).

    Returns
    -------
    None

    Notes
    -----
    Formula reference: Alduchov O.A., Eskridge R.E. (1996). Improved Magnus form
    approximation of saturation vapor pressure. Journal of Applied Meteorology
    and Climatology, 35(4), 601-9.
    """
    print("\n--- Starting processing era5land relative humidity by epidemiological week ...\n")

    # Validate input parameters
    if None in [main_dir, output_dir, folder_name, shapefile_path, variable_name, years, indicator_name]:
        raise ValueError("Error: All parameters must be defined.")

    # Check if main_dir exists (input data directory)
    if not os.path.exists(main_dir):
        raise FileNotFoundError(f"Input directory '{main_dir}' does not exist.")

    # Ensure output_dir exists (create if missing)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")

    # Create subfolder 'output_climate_dir' inside output_dir
    output_climate_dir = os.path.join(output_dir, "output_climate_dir")
    os.makedirs(output_climate_dir, exist_ok=True)
    output_dir = output_climate_dir
    print(f"Created climate output directory: {output_climate_dir}")

    # Ensure color_png_file   
    if color_png_file is None:
        color_png_file = get_default_color_file("humidity")  # epiweek vs month not change
    
    color_png_file = os.path.normpath(color_png_file)

    # Ensure years is a list since if is declared as year or [year]
    if isinstance(years, int):
        years = [years]  # Convert a single integer in a list

    if not isinstance(years, list):
        raise ValueError("Erro: years must a list of integers.")

    # Ensure the list has 2 strings (regardless of exact names):
    if (not isinstance(variable_name, list)
        or len(variable_name) != 2
        or not all(isinstance(x, str) for x in variable_name)):
        raise ValueError(
            "Error: variable_name must be a list of 2 strings "
            "(e.g., ['2m_temperature', '2m_dewpoint_temperature'])"
        )

    # Normalize paths
    main_dir = os.path.normpath(main_dir)
    folder_name = folder_name.upper()
    shapefile_path = os.path.normpath(shapefile_path)
    color_png_file = os.path.normpath(color_png_file)

    # Create output directories
    indicator_dir = create_new_dir(main_dir, folder_name)
    daily_tifs_dir = os.path.join(indicator_dir, "aux_tifs")
    os.makedirs(daily_tifs_dir, exist_ok=True)
    epiweek_dir = os.path.join(indicator_dir, "epiweek")
    os.makedirs(epiweek_dir, exist_ok=True)

    # Load shapefile and transform to WGS84
    study_area_shp = gpd.read_file(shapefile_path).to_crs("EPSG:4326")
    bounding_box = box(*study_area_shp.total_bounds)

    save_map_shapefile(shapefile_path=shapefile_path, indicator_dir=indicator_dir)

    print(f'Diretory: {indicator_dir}')

    indic_name = indicator_name.lower()[:20]  # limit to 20 characters

    # Create a set of cog images from NetCDF files - generate_COG.py
    list_climate_format_files(file_paths = main_dir, output_dir = indicator_dir, variable_input = variable_name, indicator_name_local = indic_name, years_work = years, extension_folder = "epiweek", type_indicator = "rhumidity", source="era5land")

    # Create a set of folders with epiweek pattern - utils.py
    # Load custom interval file if provided
    if provide_interval is True:
        if interval_file_path is None:
            raise ValueError("provide_interval is True, but interval_file_path is not provided.")
        else:
            print(f"Loaded custom interval data from {interval_file_path}.")
            create_epiweek_dir(epi_week_file = interval_file_path, tifs_dir = daily_tifs_dir, epi_week_dir = epiweek_dir, years = years)
    else:
        # Generate epidemiological weeks file as CSV
        temporarily_file = write_epiweeks_to_file(years, os.path.dirname(epiweek_dir))
        # Load epidemiological week data
        create_epiweek_dir(epi_week_file = temporarily_file, tifs_dir = daily_tifs_dir, epi_week_dir = epiweek_dir, years = years)

    # Create a set of stack raster for each epiweek folder - process_shapefile.py
    stack_from_muni = crop_raster_by_area_rhumidity(data_dir = epiweek_dir, study_area_bbox = bounding_box)
    del(stack_from_muni)

    # Extract relative humidity values from each stack raster - extract_aggregations.py
    dates_shapefile_col = extract_relative_humidity(data_dir = epiweek_dir, shapefile_edit = study_area_shp, indicator_name_local = [indic_name, folder_name], extension_folder = "epiweek", extension_spatial = "mun")
    #print(dates_shapefile_col)

    # Move COG files to new folder - utils.py
    move_rhumidity_COG_files(main_dir = indicator_dir, output_final_dir = output_dir, indicator_name_local = [indic_name, folder_name], color_png_file = color_png_file, extension_folder = "epiweek", extension_spatial = "mun", source="era5land")

    # Move shapefiles files to new folder - utils.py
    move_rhumidity_shapefiles_files(main_dir = indicator_dir, output_final_dir = output_dir, indicator_name_local = [indic_name, folder_name], color_png_file = color_png_file, extension_folder = "epiweek", extension_spatial = "mun", dates_col = dates_shapefile_col, data_source = "ERA5-Land (Copernicus)", source="era5land")

    del main_dir, folder_name, shapefile_path, variable_name, years, indicator_name, color_png_file
    gc.collect()

    print("\nProcessing finished successfully!\n")
    print("-----------------------------------\n")


def process_era5land_rhumidity_month(main_dir, output_dir, folder_name, shapefile_path, variable_name, years, indicator_name = "humidity", color_png_file=None):
    """
    Process Era5-Land relative humidity data by month.

    Calculates relative humidity (RH) using the formula:
    RH (%) = 100 * exp((b * c * (Td - T)) / ((c + Td) * (c + T)))
    where b = 17.625, c = 243.04, T is 2m temperature, and Td is 2m dewpoint temperature.


    Parameters
    ----------
    main_dir : str
        Directory path where the NetCDF files are stored.
    output_dir : str
        Directory path where the indicators generated will be stored. 
    folder_name : str
        Name of the folder to be created for output files.
    shapefile_path : str
        Path to the Shapefile of the study area.
    variable_name : str
        Variable name in the NetCDF file.
    years : list or str
        List of years or a single year to process.
    indicator_name : str
        Indicator name for output files (max 20 characters).
    color_png_file : str
        Path to the file with color ranges for PNG output. Default is provided by package

    Returns
    -------
    None

    Notes
    -----
    Formula reference: Alduchov O.A., Eskridge R.E. (1996). Improved Magnus form
    approximation of saturation vapor pressure. Journal of Applied Meteorology
    and Climatology, 35(4), 601-9.
    """
    print("\n--- Starting processing era5land relative humidity by month ...\n")

    # Validate input parameters
    if None in [main_dir, output_dir, folder_name, shapefile_path, variable_name, years, indicator_name]:
        raise ValueError("Error: All parameters must be defined.")
    
    # Check if main_dir exists (input data directory)
    if not os.path.exists(main_dir):
        raise FileNotFoundError(f"Input directory '{main_dir}' does not exist.")

    # Ensure output_dir exists (create if missing)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")

    # Create subfolder 'output_climate_dir' inside output_dir
    output_climate_dir = os.path.join(output_dir, "output_climate_dir")
    os.makedirs(output_climate_dir, exist_ok=True)
    output_dir = output_climate_dir
    print(f"Created climate output directory: {output_climate_dir}")

    # Ensure color_png_file   
    if color_png_file is None:
        color_png_file = get_default_color_file("humidity")  # epiweek vs month not change
    
    color_png_file = os.path.normpath(color_png_file)

    # Ensure years is a list since if is declared as year or [year]
    if isinstance(years, int):
        years = [years]  # Convert a single integer in a list

    if not isinstance(years, list):
        raise ValueError("Erro: years must a list of integers.")

    # Ensure the list has 2 strings (regardless of exact names):
    if (not isinstance(variable_name, list)
        or len(variable_name) != 2
        or not all(isinstance(x, str) for x in variable_name)):
        raise ValueError(
            "Error: variable_name must be a list of 2 strings "
            "(e.g., ['2m_temperature', '2m_dewpoint_temperature'])"
        )

    # Normalize paths
    main_dir = os.path.normpath(main_dir)
    folder_name = folder_name.upper()
    shapefile_path = os.path.normpath(shapefile_path)
    color_png_file = os.path.normpath(color_png_file)

    # Create output directories
    indicator_dir = create_new_dir(main_dir, folder_name)
    daily_tifs_dir = os.path.join(indicator_dir, "aux_tifs")
    os.makedirs(daily_tifs_dir, exist_ok=True)
    month_dir = os.path.join(indicator_dir, "month")
    os.makedirs(month_dir, exist_ok=True)

    # Load shapefile and transform to WGS84
    study_area_shp = gpd.read_file(shapefile_path).to_crs("EPSG:4326")
    bounding_box = box(*study_area_shp.total_bounds)

    save_map_shapefile(shapefile_path=shapefile_path, indicator_dir=indicator_dir)

    print(f'Diretory: {indicator_dir}')

    indic_name = indicator_name.lower()[:20]  # limit to 20 characters

    # Create a set of cog images from NetCDF files - generate_COG.py
    list_climate_format_files(file_paths = main_dir, output_dir = indicator_dir, variable_input = variable_name, indicator_name_local = indic_name, years_work = years, extension_folder = "month", type_indicator = "rhumidity", source="era5land")

    # Create a set of folders with month pattern
    create_months_dir(tifs_dir = daily_tifs_dir, month_dir = month_dir, years = years)

    # Create a set of stack raster for each month folder - process_shapefile.py
    stack_from_muni = crop_raster_by_area_rhumidity(data_dir = month_dir, study_area_bbox = bounding_box)
    del(stack_from_muni)

    # Extract relative humidity values from each stack raster - extract_aggregations.py
    dates_shapefile_col = extract_relative_humidity(data_dir = month_dir, shapefile_edit = study_area_shp, indicator_name_local = [indic_name, folder_name], extension_folder = "month", extension_spatial = "mun")
    #print(dates_shapefile_col)

    # Move COG files to new folder - utils.py
    move_rhumidity_COG_files(main_dir = indicator_dir, output_final_dir = output_dir, indicator_name_local = [indic_name, folder_name], color_png_file = color_png_file, extension_folder = "month", extension_spatial = "mun", source="era5land")

    # Move shapefiles files to new folder - utils.py
    move_rhumidity_shapefiles_files(main_dir = indicator_dir, output_final_dir = output_dir, indicator_name_local = [indic_name, folder_name], color_png_file = color_png_file, extension_folder = "month", extension_spatial = "mun", dates_col = dates_shapefile_col, data_source = "ERA5-Land (Copernicus)", source="era5land")

    del main_dir, folder_name, shapefile_path, variable_name, years, indicator_name, color_png_file
    gc.collect()

    print("\nProcessing finished successfully!\n")
    print("-----------------------------------\n")
