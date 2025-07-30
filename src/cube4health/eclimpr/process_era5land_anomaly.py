"""Module providing a function to generate temperature files from ERA5-Land."""
import os
import gc
import geopandas as gpd
from shapely.geometry import box

from .utils import (
    write_epiweeks_to_file,
    create_new_dir,
    create_epiweek_dir,
    move_indicators_shapefiles_files_anomaly,
    create_months_dir
)
from .generate_cog_tiff import list_climate_format_files
from .process_shapefile import (
    crop_raster_by_area,
    save_map_shapefile
)
from .extract_aggregations import (
    select_stations_from_area,
    extract_anomaly
)

# -----------
# Functions:
# -----------

def process_era5land_anomaly_epiweek(main_dir, folder_name, shapefile_path, variable_name, years_epi_week, indicator_name, color_png_file, conventional_stations_file, climatological_normals_file, interval_file_path=None, provide_interval=False):
    """
    Process ERA5-Land anomaly data by epidemiological week.

    Parameters
    ----------
    main_dir : str
        Directory path where the NetCDF files are stored.
    folder_name : str
        Name of the folder to be created for output files.
    shapefile_path : str
        Path to the Shapefile of the study area.
    variable_name : str
        Variable name in the NetCDF file.
    years_epi_week : list or str
        List of years or a single year to process.
    indicator_name : str
        Indicator name for output files (max 20 characters).
    color_png_file : str
        Path to the file with color ranges for PNG output.
    conventional_stations_file : str
        CSV file with conventional stations from INMET.
    climatological_normals_file : str
        XLSX file with climatological normal values from INMET.
    interval_file_path : str, optional
        Path to the custom interval file, if provide_interval is True.
    provide_interval : bool, optional
        If True, allows the user to provide a custom interval file. Default is False (use epiweek = epidemiological weeks).

    Returns
    -------
    None
    """
    print("\n--- Starting processing era5land anomaly max temperature by epidemiological week ...\n")

    # Validate input parameters
    if None in [main_dir, folder_name, shapefile_path, variable_name, years_epi_week, indicator_name, color_png_file, conventional_stations_file, climatological_normals_file]:
        raise ValueError("Error: All parameters must be defined.")

    # Ensure years_epi_week is a list since if is declared as year or [year]
    if isinstance(years_epi_week, int):
        years_epi_week = [years_epi_week]  # Convert a single integer in a list

    if not isinstance(years_epi_week, list):
        raise ValueError("Erro: years_epi_week must a list of integers.")

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
    list_climate_format_files(file_paths = main_dir, output_dir = indicator_dir, variable_input = variable_name, indicator_name_local = indic_name, years_work = years_epi_week, extension_folder = "epiweek", type_indicator = "temp", source="era5land")

    # Create a set of folders with epiweek pattern - utils.py
    # Load custom interval file if provided
    if provide_interval is True:
        if interval_file_path is None:
            raise ValueError("provide_interval is True, but interval_file_path is not provided.")
        else:
            print(f"Loaded custom interval data from {interval_file_path}.")
            create_epiweek_dir(epi_week_file = interval_file_path, tifs_dir = daily_tifs_dir, epi_week_dir = epiweek_dir, years_epi_week = years_epi_week)
    else:
        # Generate epidemiological weeks file as CSV
        temporarily_file = write_epiweeks_to_file(years_epi_week, os.path.dirname(epiweek_dir))
        # Load epidemiological week data
        create_epiweek_dir(epi_week_file = temporarily_file, tifs_dir = daily_tifs_dir, epi_week_dir = epiweek_dir, years_epi_week = years_epi_week)

    # Create a set of stack raster for each epiweek folder - process_shapefile.py
    stack_from_muni = crop_raster_by_area(data_dir = epiweek_dir, study_area_bbox = bounding_box)
    del(stack_from_muni)

    # Create a shapefile with a set of columns with climatological normal computed by IDW interpolation - extract_aggregations.py
    study_area_muni_shp = select_stations_from_area(main_dir = indicator_dir, study_area_bbox = bounding_box, shapefile_path = study_area_shp, conv_stations_file_csv = conventional_stations_file, clima_normal_file_xlsx = climatological_normals_file)

    # Create a shapefile with anomaly by each epiweek data - extract_aggregations.py
    dates_shapefile_col = extract_anomaly(data_dir = epiweek_dir, shapefile_idw_nc = study_area_muni_shp, indicator_name_local = [indic_name, folder_name], extension_folder = "epiweek", extension_spatial = "mun")

    # Move shapefiles files to new folder - utils.R
    move_indicators_shapefiles_files_anomaly(main_dir = indicator_dir, indicator_name_local = [indic_name, folder_name], color_png_file = color_png_file, extension_folder = "epiweek", extension_spatial = "mun", dates_col = dates_shapefile_col, anomaly_data = True, data_source = "ERA5-Land (Copernicus)")

    del main_dir, folder_name, shapefile_path, variable_name, years_epi_week, indicator_name, color_png_file
    gc.collect()

    print("\nProcessing finished successfully!\n")
    print("-----------------------------------\n")



def process_era5land_anomaly_month(main_dir, folder_name, shapefile_path, variable_name, years_month, indicator_name, color_png_file, conventional_stations_file, climatological_normals_file):
    """
    Process ERA5-Land anomaly data by epidemiological week.

    Parameters
    ----------
    main_dir : str
        Directory path where the NetCDF files are stored.
    folder_name : str
        Name of the folder to be created for output files.
    shapefile_path : str
        Path to the Shapefile of the study area.
    variable_name : str
        Variable name in the NetCDF file.
    years_month : list or str
        List of years or a single year to process.
    indicator_name : str
        Indicator name for output files (max 20 characters).
    color_png_file : str
        Path to the file with color ranges for PNG output.
    conventional_stations_file : str
        CSV file with conventional stations from INMET.
    climatological_normals_file : str
        XLSX file with climatological normal values from INMET.

    Returns
    -------
    None
    """
    print("\n--- Starting processing era5land anomaly max temperature by month ...\n")

    # Validate input parameters
    if None in [main_dir, folder_name, shapefile_path, variable_name, years_month, indicator_name, color_png_file, conventional_stations_file, climatological_normals_file]:
        raise ValueError("Error: All parameters must be defined.")

    # Ensure years_month is a list since if is declared as year or [year]
    if isinstance(years_month, int):
        years_month = [years_month]  # Convert a single integer in a list

    if not isinstance(years_month, list):
        raise ValueError("Erro: years_month must a list of integers.")

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
    list_climate_format_files(file_paths = main_dir, output_dir = indicator_dir, variable_input = variable_name, indicator_name_local = indic_name, years_work = years_month, extension_folder = "month", type_indicator = "temp", source="era5land")

    # Create a set of folders with month pattern
    create_months_dir(tifs_dir = daily_tifs_dir, month_dir = month_dir, years_month = years_month)

    # Create a set of stack raster for each month folder - process_shapefile.py
    stack_from_muni = crop_raster_by_area(data_dir = month_dir, study_area_bbox = bounding_box)
    del(stack_from_muni)

    # Create a shapefile with a set of columns with climatological normal computed by IDW interpolation - extract_aggregations.py
    study_area_muni_shp = select_stations_from_area(main_dir = indicator_dir, study_area_bbox = bounding_box, shapefile_path = study_area_shp, conv_stations_file_csv = conventional_stations_file, clima_normal_file_xlsx = climatological_normals_file)

    # Create a shapefile with anomaly by each month data - extract_aggregations.py
    dates_shapefile_col = extract_anomaly(data_dir = month_dir, shapefile_idw_nc = study_area_muni_shp, indicator_name_local = [indic_name, folder_name], extension_folder = "month", extension_spatial = "mun")

    # Move shapefiles files to new folder - utils.R
    move_indicators_shapefiles_files_anomaly(main_dir = indicator_dir, indicator_name_local = [indic_name, folder_name], color_png_file = color_png_file, extension_folder = "month", extension_spatial = "mun", dates_col = dates_shapefile_col, anomaly_data = True, data_source = "ERA5-Land (Copernicus)")

    del main_dir, folder_name, shapefile_path, variable_name, years_month, indicator_name, color_png_file
    gc.collect()

    print("\nProcessing finished successfully!\n")
    print("-----------------------------------\n")