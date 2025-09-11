"""Module providing function to download era5data files and Copernicus."""
import os
import traceback # Get complete exception message
import requests
import pandas as pd
import cdsapi # to ERA5-land data - https://cds.climate.copernicus.eu/how-to-api
from datetime import datetime, timedelta
from tqdm import tqdm   # progress bar

from .utils import create_new_dir

# -----------
# Function to download from Zenodo repository Raphael Saldanha (https://rfsaldanha.github.io/data-projects/era5land-daily-latin-america.html) and ERA5-Land post-processed daily statistics from 1950 to present (https://cds.climate.copernicus.eu/datasets/derived-era5-land-daily-statistics?tab=overview):
# -----------

def get_data_zenodo(output_dir, folder_name, file_list, zenodo_record_url):
    """
    Download NetCDF files from Zenodo based on a list of files.

    Parameters
    ----------
    output_dir : str
        Directory where the files will be stored.
    folder_name : str
        Name of the folder that will be created.
    file_list : str or list
        Path to a CSV/TXT file containing the list of files or a list of file names.
    zenodo_record_url : str
        URL of the Zenodo repository.
    """
    if not all([output_dir, folder_name, file_list, zenodo_record_url]):
        raise ValueError("Error: All parameters must be defined.")

    output_dir = os.path.abspath(output_dir)
    zenodo_dir = create_new_dir(output_dir, folder_name)

    # Read a file list
    if isinstance(file_list, str) and file_list.endswith(('csv', 'txt')):
        files_df = pd.read_csv(file_list, header=None, names=['files'])
    else:
        files_df = pd.DataFrame({'files': file_list})

     # Create a log file
    log_file = os.path.join(zenodo_dir, f"{folder_name}_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "w") as log:
        log.write(f"\n--- Starting download files from {zenodo_record_url} ...\n")

    print(files_df)

    for file_name in tqdm(files_df['files'], desc="Downloading files", unit="file"):
        try:
            ze_link = f"{zenodo_record_url}/files/{file_name}?download=1"
            ze_output_dir = os.path.join(zenodo_dir, file_name)

            response = requests.get(ze_link, stream=True, timeout=10)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))

            # Download with progress bar
            with open(ze_output_dir, 'wb') as f, tqdm(
                desc=f"- Downloading {file_name}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as pbar:
                for chunk in response.iter_content(chunk_size=1024): #8192
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
                        pbar.update(len(chunk))

        except requests.RequestException as e:
            print(f"Error downloading {ze_link}: {e}")

    with open(log_file, "a") as log:
        log.write("Processing finished successfully!\n")

    print(f"\nSaved log file in {log_file}")
    print("\n... Done\n")


# -----------
# Function to download ERA5-Land post-processed daily statistics from 1950 to present:
# -----------

def validate_area(area):
    """
    Validate the geographic bounding box for the ERA5-land data download.

    Parameters
    ----------
    area : list or tuple of float
        List or tuple containing four elements representing [North, West, South, East].

    Raises
    ------
    ValueError
        If 'area' is not a list or tuple with exactly four numerical elements.
        If coordinates are not within valid latitude/longitude ranges.
        If 'North' is not greater than 'South' or 'East' is not greater than 'West'.

    Returns
    -------
    None
        The function does not return anything. It only raises errors if validation fails.

    Notes
    -----
    - Latitude values (North, South) must be between -90 and 90 degrees.
    - Longitude values (West, East) must be between -180 and 180 degrees.
    - 'North' must be greater than 'South'; 'East' must be greater than 'West'.

    Examples
    --------
    >>> validate_area([5.3, -74.0, -34.7, -33.8])  # Valid for Brazil
    >>> validate_area([90, -180, -90, 180])        # Valid for global
    >>> validate_area([10, 20, 5, 30])             # Valid small area
    """

    if not isinstance(area, (list, tuple)) or len(area) != 4:
        raise ValueError("Error: 'area' must be a list or tuple with exactly 4 elements: [North, West, South, East].")

    if not all(isinstance(coord, (int, float)) for coord in area):
        raise ValueError("Error: All elements in 'area' must be integers or floats.")

    north, west, south, east = area

    if not (-90 <= north <= 90) or not (-90 <= south <= 90):
        raise ValueError("Error: 'North' and 'South' must be between -90 and 90 degrees latitude.")

    if not (-180 <= west <= 180) or not (-180 <= east <= 180):
        raise ValueError(
            "Error: 'West' and 'East' must be between -180 and 180 degrees longitude."
        )

    if north <= south:
        raise ValueError("Error: 'North' value must be greater than 'South' value.")

    if east <= west:
        raise ValueError("Error: 'East' value must be greater than 'West' value.")


def is_leap_year(year):
    """
    Check whether a given year is a leap year.

    Parameters
    ----------
    year : int or str
        The year to check. If a string is provided, it will be converted to an integer.

    Returns
    -------
    bool
        True if the year is a leap year, False otherwise.

    Notes
    -----
    - A year is a leap year if it is divisible by 4 but not divisible by 100, unless it is also divisible by 400.

    Examples
    --------
    >>> is_leap_year(2020)
    True
    >>> is_leap_year(1900)
    False
    >>> is_leap_year(2000)
    True
    >>> is_leap_year("2024")
    True
    """
    year = int(year)
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def get_data_era5land(output_dir, period, token, var, stat, area=None):
    """
    Download NetCDF files using the Climate Data Store (CDS) API to retrieve ERA5-Land daily temperature statistics data. (https://cds.climate.copernicus.eu/datasets/derived-era5-land-daily-statistics?tab=overview)

    The data is downloaded from the Copernicus Climate Data Store (CDS) service. More information:
    https://cds.climate.copernicus.eu/how-to-api
    https://cds.climate.copernicus.eu/datasets/derived-era5-land-daily-statistics?tab=overview

    Parameters
    ----------
    output_dir : str
        Path to the directory where the files will be stored.
    period : list of str
        List containing the start and end periods in the format ["YYYY-MM", "YYYY-MM"].
        Example: ["2025-01", "2025-03"].
    token : str
        User's personal CDS API key (authentication token).
    var : str
        Name of the variable to be downloaded.
        Example: "2m_temperature" or "2m_dewpoint_temperature", with underscore _
    stat : str
        Daily statistic to be retrieved.
        Options: "daily_mean", "daily_maximum", or "daily_minimum".
    area : list of float, optional
        Geographic bounding box to subset the data, specified as [North, West, South, East].
        Coordinates must follow the order: North latitude, West longitude, South latitude, East longitude.
        Example for Brazil: [5.3, -74.0, -33.7, -34.8].
        Default is for Brazil, and data is downloaded.

    Raises
    ------
    ValueError
        If any required parameter is missing or invalid.
        If the period is incorrectly defined (start date after end date).
        If the requested variable or statistic is not properly specified.

    Returns
    -------
    None
        The function saves NetCDF (.nc) files in the specified output directory and writes a log file with the download status.

    Notes
    -----
    - Only valid for temperature variables (e.g., 2m_temperature). Not suitable for precipitation data.
    - The function automatically handles leap years.
    - If a request fails (e.g., due to unavailable data), the error is logged and the download continues.
    - A log file recording successes and failures is saved in the output folder.
    - The area must always be specified in [North, West, South, East] order (not West/South/East/North).

    Examples
    --------
    >>> get_data_era5land(
    ...     output_dir="/path/to/save",
    ...     period=["2025-01", "2025-04"],
    ...     token="your-cdsapi-token",
    ...     var="2m_temperature",
    ...     stat="daily_mean",
    ...     area=[10, -60, -10, -30]
    ... )
    """
    print("\n--- Starting data download...\n")

    if None in [output_dir, period, token, var, stat] or len(period) != 2:
        raise ValueError("Error: All parameters must be defined.")

    # Check that 'var' and 'stat' have only one value
    if not isinstance(var, str):
        raise ValueError("Error: 'var' must be a single string (e.g., '2m_temperature').")

    if not isinstance(stat, str):
        raise ValueError("Error: 'stat' must be a single string (e.g., 'daily_mean', 'daily_maximum', or 'daily_minimum').")

    valid_stats = ['daily_mean', 'daily_maximum', 'daily_minimum']
    if stat not in valid_stats:
        raise ValueError(f"Error: 'stat' must be one of the following: {', '.join(valid_stats)}.")

    # Set default area if not provided
    if area is None:
        area = [5.3, -74.0, -34.7, -33.8] # - Brazil
    else:
        validate_area(area)

    # Normalize output path
    output_dir = os.path.normpath(output_dir)

    # Separate initial period
    year_start, month_start = map(int, period[0].split('-'))
    # Separate final period
    year_end, month_end = map(int, period[1].split('-'))

    # check date
    if (year_start > year_end) or (year_start == year_end and month_start > month_end):
        raise ValueError("Initial date must be earlier than or equal to final date.")

    start_date = datetime(year_start, month_start, 1)
    end_date = datetime(year_end, month_end, 1)

    # Create a new folder for output files
    path = f"{var}_{period[0]}_{period[1]}_{stat}" # 2m_temperature_2023-10_2024-01_daily_mean
    new_dir = create_new_dir(output_dir, path)
    os.makedirs(new_dir, exist_ok=True)

    # Create a log file
    log_file = os.path.join(new_dir, f"{path}_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "w") as log:
        log.write("Starting data download...\n")

    # Base URL
    url = "https://cds.climate.copernicus.eu/api"

    client = cdsapi.Client(url=url, key=token)
    #print(client)

    # list [(year, month2),(year, month2)] with correct dates
    dates = []
    current = start_date
    while current <= end_date:
        dates.append((current.year, f"{current.month:02d}"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # # List months between start and end
    # months = [f"{m:02d}" for m in range(int(month_start), int(month_end) + 1)]

    # # List years between start and end
    # years = [f"{y:04d}" for y in range(int(year_start), int(year_end) + 1)]

    # Default number of days per month (without considering leap years yet)
    days_by_month = {
        "01": 31, "02": 28, "03": 31,
        "04": 30, "05": 31, "06": 30,
        "07": 31, "08": 31, "09": 30,
        "10": 31, "11": 30, "12": 31
    }

    # Loop through years and months
    for year, month in dates:
        year = str(year)
        days_month = days_by_month[month]
        if month == "02" and is_leap_year(year):
            days_month = 29

        days = [f"{i:02d}" for i in range(1, days_month + 1)]
        start_day = days[0]
        end_day = days[-1]

        filename = f"{var}_{year}-{month}-{start_day}_{year}-{month}-{end_day}_{stat}.nc"
        output_path = os.path.join(new_dir, filename)

        request = {
            "variable": [var],
            "year": year,
            "month": month,
            "day": days,
            "daily_statistic": stat,
            "time_zone": "utc-03:00",
            "frequency": "1_hourly",
            "area": area
        }

        print(f"Downloading: {filename}")
        #client.retrieve("derived-era5-land-daily-statistics", request).download(output_path)

        try:
            client.retrieve("derived-era5-land-daily-statistics", request).download(output_path)
            with open(log_file, "a") as log:
                log.write(f"Success: {filename} downloaded.\n")

        except Exception as e:
            error_message = traceback.format_exc()
            print(f"Error downloading {filename}: {str(e)}")
            with open(log_file, "a") as log:
                log.write(f"Failed: {filename}\n")
                log.write(f"Error: {error_message}\n")

    with open(log_file, "a") as log:
        log.write("Processing finished successfully!\n")

    print(f"\nSaved log file in {log_file}")
    print("\n... Done!\n")
