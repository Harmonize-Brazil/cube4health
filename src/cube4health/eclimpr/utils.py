"""Module providing a function work with files, such as read inputs."""
import os
import re
import csv
import shutil
from datetime import datetime, timedelta
from datetime import datetime, timedelta
from epiweeks import Week
import zipfile
import pandas as pd
import numpy as np
import geopandas as gpd
from natsort import natsorted  # Correct order of filenames
from tqdm import tqdm

from .generate_png_file import (
    create_png_from_cog_file,
    create_png_from_shp_file
)

# -----------
# Functions:
# -----------

def read_files_inputs(list_files, years_work, extension_folder, extension_file):
    """
    Read a set of NetCDF or GRIB2 files from a directory.

    Parameters
    ----------
    list_files : list of str
        Vector with a set of NetCDF or GRIB2 files.
    years_work : list of str
        Set of years to extract, e.g., ["2019", "2020"].
    extension_folder : str
        This is the extension folder "epiweek" or "month" to add in the output file.
    extension_file : str
        This is the extension file ".nc" or ".grib2" to process.

    Returns
    -------
    list of str
        List of file paths that match the criteria.
    """
    # Ensure years_work is a list since if is declared as year or [year]
    if isinstance(years_work, int):
        years_work = [years_work]

    if not isinstance(years_work, list):
        raise ValueError("Erro: years_work must be a integer or a list of integers.")

    if extension_folder == "epiweek":
        # Filter files by defined year
        output_path = [file for file in list_files if any(str(year) in file for year in years_work)]

        if not output_path:
            raise ValueError(f"Erro: there are no files for the year(s) {years_work}")

        # Interval of 7 days before
        first_element = years_work[0]
        days7_before = [(datetime(first_element - 1, 12, 25) + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        # Select files into the interval
        for file in list_files:
            match = re.search(rf".*_(\d{{8}}){extension_file}$", file)
            if match:
                name_date = datetime.strptime(match.group(1), "%Y%m%d").strftime("%Y-%m-%d")
                if name_date in days7_before:
                    output_path.append(file)

    elif extension_folder == "month":
        # Filter files by defined years
        output_path = [file for file in list_files if any(str(year) in file for year in years_work)]

        if not output_path:
            raise ValueError(f"Erro: there are no files for the year(s) {years_work}")

    else:
        raise ValueError("Erro: extension_folder parameter must be defined.")

    return output_path


# Function to generate epidemiological weeks
def generate_epiweeks(year):
    """
    Generate epidemiological weeks for a given year using the epiweeks package.

    Parameters
    ----------
    year : int
        The year for which to generate the epidemiological weeks.

    Returns
    -------
    list of tuple
        A list of tuples, where each tuple contains:
        - year (int): The year of the epidemiological week.
        - week_number (int): The week number (1 to 52 or 53).
        - start_date (datetime): The start date of the week (Sunday).
        - end_date (datetime): The end date of the week (Saturday).

    Returns a list of tuples: (year, week_number, start_date, end_date)

    """
    weeks = []

    # It starts with the first epidemiological week of the year
    w = Week(year, 1)
    while w.startdate().year <= year:
        # Add week only if at least one day of it belongs to the target year
        if w.startdate().year == year or w.enddate().year == year:
            weeks.append((w.year, w.week, w.startdate(), w.enddate()))
        # Next epiweek
        w = Week.fromdate(w.startdate() + timedelta(days=7))

    return weeks


# Function to write the weeks to a CSV file with header
def write_epiweeks_to_file(year_file, save_dir):
    """
    Write epidemiological weeks data to a CSV file.

    This function generates epidemiological weeks for a given year or list of years
    and saves the data in a CSV file. Each epidemiological week starts on a Sunday
    and ends on a Saturday.

    Parameters
    ----------
    year_file : int or list of int
        The year(s) for which to generate epidemiological weeks. If a single integer
        is provided, it will be treated as a single year. If a list of integers is
        provided, it will generate weeks for all years in the list.
    save_dir : str
        The directory where the CSV file will be saved.

    Returns
    -------
    str
        The full path to the generated CSV file.
    """
    years_epiweek = [year_file] if isinstance(year_file, int) else list(year_file) # a list of years or single year

    epi_weeks = []
    for yr in years_epiweek:
        if isinstance(yr, int):  # yr is a integer before function called
            epi_weeks += generate_epiweeks(yr)
        else:
            raise TypeError(f"Wait a integer, but received {type(yr)}: {yr}")

    csv_filename = os.path.join(save_dir, "epidemiologicalweeks.csv")

    # Creating a file with .csv extension
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # write the header
        writer.writerow(["Year", "Week", "StartDate", "EndDate"])
        # add data
        #week_number = 1
        for week in epi_weeks:
            year, week_number, start_date, end_date = week
            writer.writerow([year, f"{week_number:02d}", start_date.strftime('%d/%m/%Y'), end_date.strftime('%d/%m/%Y')])
        #   week_number += 1

        # Return the file temporary name
        return f.name


def create_epiweek_dir(epi_week_file, tifs_dir, epi_week_dir, years_epi_week):
    """
    Create a set of epidemiological week folders based on the provided CSV file with epidemiological dates.

    Parameters
    ----------
    epi_week_file : str
        Path to the CSV file with epidemiological dates.
    tifs_dir : str
        Path to the directory containing the TIFF files.
    epi_week_dir : str
        Path to the directory where the epidemiological week folders will be created.
    years_epi_week : list of int
        List of years to process (e.g., [2019, 2020]).

    Returns
    -------
    None
    """
    print("\nCreating epidemiological week folders ...\n")

    # Ensure years_epi_week is a list since if is declared as year or [year]
    if isinstance(years_epi_week, int):
        years_epi_week = [years_epi_week]

    # Generate epidemiological weeks file as CSV
    #temp_file = write_epiweeks_to_file(years_epi_week, os.path.dirname(epi_week_dir))

    # Read the CSV file with epidemiological dates
    week_data = pd.read_csv(epi_week_file) #temp_file)

    # Check for required columns
    required_columns = {'Year', 'Week', 'StartDate', 'EndDate'}
    if required_columns.issubset(week_data.columns):
        if len(week_data) == 0:
            raise ValueError("Interval file is empty.")
    else:
        missing_columns = required_columns - set(week_data.columns)
        raise ValueError(f"Interval file is missing the following required columns: {', '.join(missing_columns)}.")

    week_data["Week"] = week_data["Week"].apply(lambda x: str(x).zfill(2))  # Add leading zero to weeks 1-9

    # Filter data for the specified years
    year_data = week_data[week_data["Year"].isin(years_epi_week)]

    # Check if "dewpoint" and "temp" folders exist
    dewpoint_exists = os.path.exists(os.path.join(tifs_dir, "dewpoint"))
    temp_exists = os.path.exists(os.path.join(tifs_dir, "temp"))

    # Get list of TIFF files
    if dewpoint_exists and temp_exists:
        dewpoint_path = os.path.join(tifs_dir, "dewpoint")
        temp_path = os.path.join(tifs_dir, "temp")
        filenames = (
            [os.path.join(dewpoint_path, f) for f in os.listdir(dewpoint_path) if f.endswith(".tif")] +
            [os.path.join(temp_path, f) for f in os.listdir(temp_path) if f.endswith(".tif")]
        )
    else:
        filenames = [os.path.join(tifs_dir, f) for f in os.listdir(tifs_dir) if f.endswith(".tif")]

    # Move daily TIFFs to each folder with epi week
    for _, row in year_data.iterrows():
        by_week = row
        bydate = f"epiweek_{by_week['Week']}_{datetime.strptime(by_week['StartDate'], '%d/%m/%Y').strftime('%Y%m%d')}_{datetime.strptime(by_week['EndDate'], '%d/%m/%Y').strftime('%Y%m%d')}"
        os.makedirs(os.path.join(epi_week_dir, bydate), exist_ok=True)

        # Convert start and end dates to YYYYMMDD format
        start_date = datetime.strptime(by_week["StartDate"], "%d/%m/%Y").strftime("%Y%m%d")
        end_date = datetime.strptime(by_week["EndDate"], "%d/%m/%Y").strftime("%Y%m%d")

        for filename in filenames:
            # Extract date from filename (assuming format YYYY-MM-DD)
            file_date_pattern = re.search(r"\d{4}-\d{2}-\d{2}", filename)
            if file_date_pattern:
                date_pattern = file_date_pattern.group(0).replace("-", "")

                # Verify if file date is within the epi week
                if start_date <= date_pattern <= end_date:
                    # Copy file to the epi week folder
                    shutil.copy(filename, os.path.join(epi_week_dir, bydate, os.path.basename(filename)))

    remove_empty_directories(epi_week_dir)

    print("... Done\n")


def remove_empty_directories(directory):
    """
    Remove all empty directories into a directory.

    Parameters
    ----------
    directory : str
        Directory path where empty subdirectories will be removed.

    Returns
    -------
    None
    """
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Verify if directory is empty
                if not os.listdir(dir_path):
                    #print(f"Removendo diretório vazio: {dir_path}")
                    os.rmdir(dir_path)  # Removes the empty directory
            except Exception as e:
                print(f"Processing error {dir_path}: {e}")


def create_months_dir(tifs_dir, month_dir, years_month):
    """
    Create a set of month folders based on dates and move TIFF files into the corresponding folders.

    Parameters
    ----------
    tifs_dir : str
        Path to the directory containing the TIFF files.
    month_dir : str
        Path to the directory where the month folders will be created.
    years_month : list of int
        List of years to process (e.g., [2019, 2020]).

    Returns
    -------
    None
    """
    print("\nCreating month folders ...\n")

    # Check if there are two folders "dewpoint" and "temp" in case of relative humidity
    dewpoint_exists = os.path.exists(os.path.join(tifs_dir, "dewpoint"))
    temp_exists = os.path.exists(os.path.join(tifs_dir, "temp"))

    # Get list of TIFF files
    if dewpoint_exists and temp_exists:
        dewpoint_path = os.path.join(tifs_dir, "dewpoint")
        temp_path = os.path.join(tifs_dir, "temp")
        filenames = (
            [os.path.join(dewpoint_path, f) for f in os.listdir(dewpoint_path) if f.endswith(".tif")] +
            [os.path.join(temp_path, f) for f in os.listdir(temp_path) if f.endswith(".tif")]
        )
    else:
        filenames = [os.path.join(tifs_dir, f) for f in os.listdir(tifs_dir) if f.endswith(".tif")]

    # Extract dates from filenames
    all_dates = [re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(f)).group(0) for f in filenames]

    # Convert to datetime objects and extract unique year-month combinations
    unique_months = sorted(set(datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m") for date in all_dates))

    # Filter months by the specified years
    unique_months = [month for month in unique_months if int(month.split("-")[0]) in years_month]

    # Move daily TIFFs to each folder with month
    for month in unique_months:
        # Create folder name (e.g., "month_YYYYMMDD_YYYYMMDD")
        start_date = datetime.strptime(month, "%Y-%m")
        end_date = start_date.replace(day=28) + timedelta(days=4)  # Move to next month and subtract one day
        end_date = end_date - timedelta(days=end_date.day)
        bydate = f"month_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        os.makedirs(os.path.join(month_dir, bydate), exist_ok=True)

        # Move files that match the month
        for filename in filenames:
            file_date_pattern = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(filename))
            if file_date_pattern and month in file_date_pattern.group(0):
                shutil.copy(filename, os.path.join(month_dir, bydate, os.path.basename(filename)))

    print("... Done\n")


def create_new_dir(output_dir, folder_name):
    """
    Create a new directory. If a directory with the same name already exists, a new one will be created with a suffix.

    Parameters
    ----------
    output_dir : str
        Path where the new directory will be created.
    folder_name : str
        Name of the new directory.

    Returns
    -------
    str
        Path to the newly created directory.
    """
    if output_dir is None or folder_name is None:
        raise ValueError("Error: parameters must be defined.")

    new_dir = None

    try:
        # Path to the new folder
        new_folder_path = os.path.join(output_dir, folder_name)

        # Check if the folder already exists
        if not os.path.exists(new_folder_path):
            # If it does not exist, create the folder
            os.makedirs(new_folder_path)
            new_dir = new_folder_path
        else:
            # If the folder already exists, add a suffix
            temp = folder_name
            count = 1
            new_name = f"{temp}_{count}"

            # Check if the new name already exists
            while os.path.exists(os.path.join(output_dir, new_name)):
                count += 1
                new_name = f"{temp}_{count}"

            # Create the folder with the new name
            new_folder_path = os.path.join(output_dir, new_name)
            os.makedirs(new_folder_path)
            new_dir = new_folder_path

    except Exception as e:
        raise RuntimeError(f"Error encountered: {str(e)}")

    return new_dir


def move_indicators_cog_files(main_dir, indicator_name_local, color_png_file, extension_folder, extension_spatial, aggregation="all"):
    """
    Move COG files to new folders based on specified max, min, and/or mean indicators.

    Parameters
    ----------
    main_dir : str
        Folder containing epiweeks or months with TIFF files.
    indicator_name_local : list of str
        List containing the indicator name to add in output files.
    color_png_file : str
        Path to the file containing the range of colors for PNG files.
    extension_folder : str
        Extension folder ("epiweek" or "month") to add in output files.
    extension_spatial : str
        Aggregation spatial ("municipality", "mun", "health region", "hr", or "state") to add in output files.
    aggregation : str or list of str, optional
        Aggregations to process: "all", or list containing any of ["max", "min", "mean"].

    Returns
    -------
    None
    """

    # Ensure aggregation is a list
    if isinstance(aggregation, str):
        if aggregation == "all":
            aggregation = ["max", "min", "mean"]
        else:
            aggregation = [aggregation]

    search_terms = aggregation

    # Read a list of files with specified aggregation values of each epi week or month folder
    filenames = [os.path.join(root, file)
                 for root, dirs, files in os.walk(main_dir)
                 for file in files if file.endswith("_COG.tif") and any(term in file for term in search_terms)]
    filenames = natsorted(filenames)

    # Create directories only for requested aggregations
    dirs = {}
    img_dirs = {}
    for agg in aggregation:
        agg_dir = os.path.join(main_dir, f"{indicator_name_local[0]}_{agg}_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}")
        agg_img_dir = os.path.join(agg_dir, "images")
        os.makedirs(agg_dir, exist_ok=True)
        os.makedirs(agg_img_dir, exist_ok=True)
        dirs[agg] = agg_dir
        img_dirs[agg] = agg_img_dir

    print("\nMoving raster .COG to specified aggregation folders...\n")

    listdates = []
    for filepath in tqdm(filenames):
        basename = os.path.basename(filepath)
        date_match = re.search(r"\d{8}", basename)
        if not date_match:
            continue
        date = np.datetime64(date_match.group())

        for agg in aggregation:
            if f"_{agg}_" in basename:
                shutil.copy(filepath, img_dirs[agg])
                listdates.append(date)
                create_png_from_cog_file(raster_tif=filepath, output_dir=img_dirs[agg], color_png_file=color_png_file)
                break  # found matching agg, skip others

    # Remove duplicates and sort
    df = np.unique(listdates)
    df.sort()

    np.savetxt(os.path.join(main_dir, "timeline_indicator.txt"), df, fmt='%s')

    print("... Done\n")


def shapefile_add_info(shapefile_edit, data_source, indicator_name, epiweek_month_number, start_date, time_agg, spatial_agg):
    """
    Builds a GeoDataFrame with descriptive columns and aggregated values.

    Parameters
    ----------
    shapefile_edit : geopandas.GeoDataFrame
        GeoDataFrame containing columns such as cod_mun, name_mun, uf_mun, and geometry.
    data_source : str, optional
        Name of the data source used to generate the shapefiles. This information will be added to the file metadata and may include sources such as "ERA5-Land (Copernicus)", "MERGE (CPTEC/INPE)", "SAMeT (CPTEC/INPE)", or other climate or environmental datasets.
    values : list or array
        Computed values (e.g., from raster_stats).
    indicator_name : str
        Name of the indicator and with type of aggregation ('max', 'min', or 'mean')..
    epiweek_month_number : number
        Number of epidemiological week or month. Disconsidering two digits (01) as used in folder creation
    start_date : str
        Date string in 'YYYYMMDD' format.
    time_agg : str
        Temporal aggregation level (e.g., 'epiweek' or 'month').
    spatial_agg : str
        Spatial aggregation level (e.g., 'municipality').

    Returns
    -------
    GeoDataFrame
        A GeoDataFrame with additional descriptive columns and the aggregated values.
    """

    if spatial_agg == 'mun':
        spatial_agg = "municipality"

    if time_agg == 'epiweek':
        df_out = shapefile_edit.copy()
        df_out["data_source"] = data_source
        df_out["name_indicator"] = indicator_name
        df_out["epiweek_number"] = epiweek_month_number
        df_out["epiweek_start_date"] = start_date
        df_out["time_agg"] = time_agg
        df_out["spatial_agg"] = spatial_agg
    elif time_agg == 'month':
        df_out = shapefile_edit.copy()
        df_out["data_source"] = data_source
        df_out["name_indicator"] = indicator_name
        df_out["month_number"] = epiweek_month_number
        df_out["month_start_date"] = start_date
        df_out["time_agg"] = time_agg
        df_out["spatial_agg"] = spatial_agg

    # Reorder columns to keep 'geometry' as the last column
    cols = [col for col in df_out.columns if col not in ['value', 'geometry']] + ['value', 'geometry']
    df_out = df_out[cols]

    return df_out


def create_shp_from_epiweek(main_dir, shapefile_path, dates_col, indicator_name_loc=None, ncol_epiweek=4, color_png_file=None, anomaly_data=None, data_source_name = None):
    """
    Generate shapefiles and GeoJSON files by epi_week and save them in a folder called 'shapefiles'.

    Parameters
    ----------
    main_dir : str
        The directory path where the NetCDF files (.nc) are stored.
    shapefile_path : str
        The path to the Shapefile of the area of interest.
    dates_col : pd.DataFrame
        A DataFrame containing a list of epiweeks start and end dates in the format '20221030_20221105'.
    indicator_name_loc : List[str]
        Indicator name plus aggregation. Example: "temp_min" or "temp_max"
    ncol_epiweek : int, optional
        The index of the column in the attribute table that starts with the pattern w_YYYYMMDD (default is 4).
    color_png_file : str, optional
        The path of the file with the range of colors to be used for generating PNGs.
    anomaly_data : bool, optional
        If False, normal data processing is used. If True, an alternate processing method for anomaly data is used.
    data_source_name : str, optional
        Name of the data source used to generate the shapefiles. This information will be added to the file metadata and may include sources such as "ERA5-Land (Copernicus)", "MERGE (CPTEC/INPE)", "SAMeT (CPTEC/INPE)", or other climate or environmental datasets.

    """

    # Normalize the directory path
    main_dir = os.path.normpath(main_dir)

    # Create the shapefiles directory
    shap_dir = os.path.join(main_dir, "shapefiles")
    if not os.path.exists(shap_dir):
        os.makedirs(shap_dir)
    else:
        count = 1
        while os.path.exists(shap_dir):
            shap_dir = os.path.join(main_dir, f"shapefiles_{count}")
            count += 1
        os.makedirs(shap_dir)

    # Load the shapefile
    study_area_shp = gpd.read_file(shapefile_path)
    study_area_shp = study_area_shp.to_crs("EPSG:4326")
    shp_layer = os.path.splitext(os.path.basename(shapefile_path))[0]

    # Initialize progress bar
    progress_bar = tqdm(total=len(study_area_shp.columns) - ncol_epiweek-1, desc="Processing Shapefiles")

    count_shp = 0

    for y in range(ncol_epiweek-1, len(study_area_shp.columns)):
        # Select columns with data
        by_week = study_area_shp.iloc[:, list(range(ncol_epiweek-1)) + [y]]
        # Add geometry column
        by_week = by_week.assign(geometry=study_area_shp.geometry)

        col_interest = ", ".join([col for col in by_week.columns if re.match(r"^w+_\d", col)])

        if not col_interest:
            continue
        else:
            # Only start date of data
            date_extract = col_interest.split('_')[1]
            # Extract entire row
            row_extracted = dates_col[dates_col['epiweek_month'].str.contains(date_extract, regex=True)].head(1)
            # Extract start and end date of data
            date_extracted = row_extracted['epiweek_month'].values[0] # only string
            # Rename column name
            by_week = by_week.rename(columns={col_interest: "value"})

            # Required parameters
            epiweek_month_number = row_extracted['epiweek_month_number']
            start_date = datetime.strptime(date_extracted.split('_')[0], '%Y%m%d').strftime('%Y-%m-%d')
            time_agg = row_extracted['time_agg']
            spatial_agg = row_extracted['spatial_agg']

            # Create new folder by each week dir
            by_week_shap_dir = os.path.join(shap_dir, datetime.strptime(date_extracted.split('_')[0], '%Y%m%d').strftime('%Y-%m-%d'))
            os.makedirs(by_week_shap_dir, exist_ok=True)

            by_week = gpd.GeoDataFrame(by_week, geometry='geometry')

            # Add additional descriptive columns using shapefile_add_info
            by_week = shapefile_add_info(
                data_source = str(data_source_name),
                shapefile_edit = by_week,
                indicator_name=str(indicator_name_loc),
                epiweek_month_number=int(epiweek_month_number.values[0]),
                start_date=str(start_date),
                time_agg=str(time_agg.values[0]),
                spatial_agg=str(spatial_agg.values[0])
            )

            for date_col in ['epiweek_start_date', 'month_start_date']:
                if date_col in by_week.columns:
                    by_week[date_col] = pd.to_datetime(by_week[date_col]).dt.strftime('%Y-%m-%d').astype(str)

            # Save geojson
            geojson_path = os.path.join(by_week_shap_dir, f"{shp_layer}_{date_extracted}.geojson")
            by_week.to_file(geojson_path, driver='GeoJSON')

            # Save shapefile
            shp_path = os.path.join(by_week_shap_dir, f"{shp_layer}_{date_extracted}.shp")
            # Rename columns to <= 10 characters
            by_week.columns = [col[:10] for col in by_week.columns]
            by_week.to_file(shp_path, driver='ESRI Shapefile')

            # Create ZIP file
            zip_path = os.path.join(by_week_shap_dir, f"{shp_layer}_{date_extracted}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(by_week_shap_dir):
                    for file in files:
                        if file.endswith(('.shp', '.shx', '.dbf', '.prj', 'cpg')):
                            zipf.write(os.path.join(root, file), file)

            # Placeholder for PNG creation
            create_png_from_shp_file(by_week_shap_dir, color_png_file, anomaly_data)

        count_shp += 1
        progress_bar.update(1)

    progress_bar.close()

    print(f"\n... Created {count_shp} Shapefiles. Done.")


def move_indicators_shapefiles_files(main_dir, indicator_name_local, color_png_file, extension_folder, extension_spatial, dates_col, anomaly_data=None, aggregation="all", data_source = None):
    """
    Move shapefiles to new folders with max, min and/or mean data.

    Parameters
    ----------
    main_dir : str
        Folder with epiweeks and TIFs.
    indicator_name_local : List[str]
        Indicator name to add in output files.
    color_png_file : str
        Path to file with the range of colors for PNG.
    extension_folder : str
        Extension folder type ('epiweek' or 'month').
    extension_spatial : str
        Spatial aggregation type ('municipality', 'health region', or 'state').
    dates_col : pd.DataFrame
        DataFrame with a list of epiweeks start and end dates.
    anomaly_data : bool, optional
        If False, uses cut. If True, another function is used to handle anomaly data.
    aggregation : str or list of str, optional
        Aggregations to process: "all" (default), or list containing any of ["max", "min", "mean"].
    data_source : str, optional
        Name of the data source used to generate the shapefiles. This information will be added to the file metadata and may include sources such as "ERA5-Land (Copernicus)", "MERGE (CPTEC/INPE)", "SAMeT (CPTEC/INPE)", or other climate or environmental datasets.

    Returns
    -------
    None
    """

    print("\nCreating a Shapefiles directory ...\n")

    # Ensure aggregation is a list
    if isinstance(aggregation, str):
        if aggregation == "all":
            aggregation = ["max", "min", "mean"]
        else:
            aggregation = [aggregation]

    # Prepare lists of files for each aggregation
    filenames_dict = {}
    copied_files_dict = {}  # New dict to store path of the copied files
    for agg in aggregation:
        filenames_dict[agg] = [os.path.join(main_dir, f)
                              for f in os.listdir(main_dir)
                              if os.path.isfile(os.path.join(main_dir, f)) and re.search(f'_{agg}_', f)]
        # start empty list for each aggregation
        copied_files_dict[agg] = []

    # Create directories for each aggregation
    dirs = {}
    for agg in aggregation:
        agg_dir = os.path.join(main_dir, f"{indicator_name_local[0]}_{agg}_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}")
        os.makedirs(agg_dir, exist_ok=True)
        dirs[agg] = agg_dir

    # Process files for each aggregation
    for agg in aggregation:
        filenames = filenames_dict[agg]
        target_dir = dirs[agg]

        # Copy files to new folder ('.shp', '.shx', '.dbf', '.prj', 'cpg')
        for file in filenames:
            dest_path = shutil.copy(file, target_dir)
            copied_files_dict[agg].append(dest_path)  # save new path target_dir

        # List shapefiles in target directory
        shapefiles = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith('.shp')]

        if shapefiles:
            create_shp_from_epiweek(
                main_dir=target_dir,
                shapefile_path=shapefiles[0],
                dates_col=dates_col,
                indicator_name_loc=f"{indicator_name_local[0]}_{agg}",
                ncol_epiweek=4, # 4 cod_mun, name_mun, uf_mun and w_YYYYMMDD...
                color_png_file=color_png_file,
                anomaly_data=anomaly_data,
                data_source_name = data_source
            )

        # Remove original files
        for file in filenames:
            os.remove(file)

    # Remove original files (all shapefile components from original into target_dir)
    for agg in aggregation:
        for copied_file in copied_files_dict[agg]:
            if os.path.exists(copied_file):
                os.remove(copied_file)
                #print(f"{copied_file}")

    print("\n... Done\n")


# -----------
# Functions to deal with anomaly data:
# -----------

def move_indicators_shapefiles_files_anomaly(main_dir, indicator_name_local, color_png_file,extension_folder, extension_spatial, dates_col, anomaly_data= None, data_source=None):
    """
    Move shapefiles to new folders with anomaly data.

    Parameters
    ----------
    main_dir : str
        Folder with epiweeks and TIFs.
    indicator_name_local : List[str]
        Indicator names to add in output files (e.g., ["temp"]).
    color_png_file : str
        Path to file with the range of colors for PNG.
    extension_folder : str
        Extension folder type ('epiweek' or 'month').
    extension_spatial : str
        Spatial aggregation type ('municipality', 'health_region', or 'state').
    dates_col : pd.DataFrame
        DataFrame with a list of epiweeks start and end dates.
    anomaly_data : bool, optional
        If False, uses cut. If True, another function is used to handle anomaly data.
   data_source : str, optional
        Name of the data source used to generate the shapefiles. This information will be added to the file metadata and may include sources such as "ERA5-Land (Copernicus)", "MERGE (CPTEC/INPE)", "SAMeT (CPTEC/INPE)", or other climate or environmental datasets.

    Notes
    -----
    Creates separate directories for consecutive days and number of days anomalies,
    moves shapefiles to their respective directories, processes them, and removes
    the original files.
    """

    print("\nCreating a Shapefiles directory ...\n")

    # Find anomaly files
    filenames_con = [os.path.join(main_dir, f)
                    for f in os.listdir(main_dir)
                    if os.path.isfile(os.path.join(main_dir, f)) and 'anomaly_cdays' in f]

    filenames_num = [os.path.join(main_dir, f)
                    for f in os.listdir(main_dir)
                    if os.path.isfile(os.path.join(main_dir, f)) and 'anomaly_ndays' in f]

    # Create target directories
    max_con = os.path.join(main_dir, f"anomaly_cdays_{indicator_name_local[0]}_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}")
    max_num = os.path.join(main_dir, f"anomaly_ndays_{indicator_name_local[0]}_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}")

    os.makedirs(max_con, exist_ok=True)
    os.makedirs(max_num, exist_ok=True)

    # Move and process consecutive days files ('.shp', '.shx', '.dbf', '.prj', 'cpg')
    copied_files_dict = []  # New list to store path of the copied files
    for file in filenames_con:
        dest_path = shutil.copy(file, max_con)
        copied_files_dict.append(dest_path)  # save new path max_con

    con_shapefiles = [os.path.join(max_con, f) for f in os.listdir(max_con) if f.endswith('.shp')]
    if con_shapefiles:
        create_shp_from_epiweek(
            main_dir=max_con,
            shapefile_path=con_shapefiles[0],
            indicator_name_loc="temp_max_anomaly",
            ncol_epiweek=4, # 4 cod_mun, name_mun, uf_mun and w_YYYYMMDD...
            color_png_file=color_png_file,
            dates_col=dates_col,
            anomaly_data=anomaly_data,
            data_source_name = data_source
        )

    # Move and process number of days files ('.shp', '.shx', '.dbf', '.prj', 'cpg')
    for file in filenames_num:
        dest_path2 = shutil.copy(file, max_num)
        copied_files_dict.append(dest_path2)  # save new path max_num

    num_shapefiles = [os.path.join(max_num, f) for f in os.listdir(max_num) if f.endswith('.shp')]
    if num_shapefiles:
        create_shp_from_epiweek(
            main_dir=max_num,
            shapefile_path=num_shapefiles[0],
            indicator_name_loc="temp_max_anomaly",
            ncol_epiweek=4, # 4 cod_mun, name_mun, uf_mun and w_YYYYMMDD...
            color_png_file=color_png_file,
            dates_col=dates_col,
            anomaly_data=anomaly_data,
            data_source_name = data_source
        )

    # Remove original files
    for file in filenames_con + filenames_num:
        try:
            os.remove(file)
        except OSError:
            pass

    # Remove original files (all shapefile components from original into both directories)
    for copied_file in copied_files_dict:
        if os.path.exists(copied_file):
            os.remove(copied_file)
            #print(f"{copied_file}")

    print("\n... Done\n")


# -----------
# Functions to deal with relative humidity data:
# -----------

def move_rhumidity_COG_files(main_dir, indicator_name_local, color_png_file, extension_folder, extension_spatial):
    """
    Move COG files to new folders to relative humidity.

    Parameters
    ----------
    main_dir : str
        Folder containing epiweeks or months with TIFF files.
    indicator_name_local : list of str
        List containing the indicator name to add in output files.
    color_png_file : str
        Path to the file containing the range of colors for PNG files.
    extension_folder : str
        Extension folder ("epiweek" or "month") to add in output files.
    extension_spatial : str
        Aggregation spatial ("municipality", "mun", "health region", "hr", or "state") to add in output files.

    Returns
    -------
    None
    """

    # Read a list of files with max and min values of each epi week or month folder
    filenames = [os.path.join(root, file)
                 for root, dirs, files in os.walk(main_dir)
                 for file in files if file.endswith("_COG.tif") and "percent" in file]
    filenames = natsorted(filenames)

    # Create directories for mean relative humidity
    mean_dir = os.path.join(main_dir, f"{indicator_name_local[0]}_percent_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}")
    os.makedirs(mean_dir, exist_ok=True)

    img_mean_dir = os.path.join(mean_dir, "images")
    os.makedirs(img_mean_dir, exist_ok=True)

    # Print a message indicating that the process was finished successfully
    print("\nMove relative raster .COG to new folders ...\n")

    # Initialize the progress bar
    listdates = []
    for y, by_week in enumerate(tqdm(filenames)):
        # Verify if file date is into epi week
        if f"_percent_{indicator_name_local[1]}" in os.path.basename(by_week):
            # Copy files mean temperature
            shutil.copy(by_week, img_mean_dir)
            date = re.search(r"\d{8}", os.path.basename(by_week)).group()
            listdates.append(np.datetime64(date))
            # Create PNG files to new folder - create_PNG_colored_from_COG.R
            create_png_from_cog_file(raster_tif=by_week, output_dir=img_mean_dir, color_png_file=color_png_file)

    # Convert list to numpy array and remove duplicates
    df = np.unique(listdates)

    # Sort the array
    df.sort()

    # Save in directory
    np.savetxt(os.path.join(main_dir, "timeline_indicator.txt"), df, fmt='%s')

    # Print a message indicating that the process was finished successfully
    print("... Done\n")


def move_rhumidity_shapefiles_files(main_dir, indicator_name_local, color_png_file,extension_folder, extension_spatial, dates_col, data_source=None):
    """
    Move shapefiles to new folders with relative humidity data.

    Parameters
    ----------
    main_dir : str
        Folder with epiweeks and TIFs.
    indicator_name_local : List[str]
        Indicator names to add in output files (e.g., ["temp"]).
    color_png_file : str
        Path to file with the range of colors for PNG.
    extension_folder : str
        Extension folder type ('epiweek' or 'month').
    extension_spatial : str
        Spatial aggregation type ('municipality', 'health_region', or 'state').
    dates_col : pd.DataFrame
        DataFrame with a list of epiweeks start and end dates.
    data_source : str, optional
        Name of the data source used to generate the shapefiles. This information will be added to the file metadata and may include sources such as "ERA5-Land (Copernicus)", "MERGE (CPTEC/INPE)", "SAMeT (CPTEC/INPE)", or other climate or environmental datasets.


    Returns
    -------
    None
    """

    print("\nCreating a Shapefiles directory ...\n")

    # Find anomaly files
    filenames_mean = [os.path.join(main_dir, f)
                    for f in os.listdir(main_dir)
                    if os.path.isfile(os.path.join(main_dir, f)) and '_percent_' in f]

    # Create target directories
    mean_dir = os.path.join(main_dir, f"{indicator_name_local[0]}_percent_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}")
    os.makedirs(mean_dir, exist_ok=True)

    # Move relative data files
    copied_files_dict = []  # New list to store path of the copied files
    for file in filenames_mean:
        dest_path = shutil.copy(file, mean_dir)
        copied_files_dict.append(dest_path)  # save new path mean_dir

    mean_shapefiles = [os.path.join(mean_dir, f) for f in os.listdir(mean_dir) if f.endswith('.shp')]
    if mean_shapefiles:
        create_shp_from_epiweek(
            main_dir=mean_dir,
            shapefile_path=mean_shapefiles[0],
            indicator_name_loc="relative_humidity",
            ncol_epiweek=4, # 4 cod_mun, name_mun, uf_mun and w_YYYYMMDD...
            color_png_file=color_png_file,
            dates_col=dates_col,
            anomaly_data=False,
            data_source_name = data_source
        )

    # Remove original files
    for file in filenames_mean:
        try:
            os.remove(file)
        except OSError:
            pass

    # Remove original files (all shapefile components from original into mean_dir)
    for copied_file in copied_files_dict:
        if os.path.exists(copied_file):
            os.remove(copied_file)
            #print(f"{copied_file}")

    print("\n... Done\n")
