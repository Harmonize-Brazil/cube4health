"""Module providing functions to work with data download from FTP - CPTEC/INPE."""
import os
from datetime import datetime, timedelta
import requests
import pandas as pd
from tqdm import tqdm

from cube4health.eclimpr.utils import create_new_dir

# -----------
# Functions:
# -----------

def generate_urls(url_name, url_path_name, period, extension):
    """
    Generate URLs according to a time interval and base URL.

    Parameters
    ----------
    url_name : str
        Base URL.
    url_path_name : str
        File name prefix.
    period : list of str
        List with start and end dates in format ["YYYY-MM-DD", "YYYY-MM-DD"].
    extension : str
        File extension (e.g., ".nc" or ".grib2").

    Returns
    -------
    pandas.DataFrame
        DataFrame with generated URLs.
    """

    start_date = datetime.strptime(period[0], "%Y-%m-%d")
    end_date = datetime.strptime(period[1], "%Y-%m-%d")

    urls = []
    current_date = start_date

    while current_date <= end_date:
        year_info = current_date.year
        month_info = f"{current_date.month:02d}"
        day_info = f"{current_date.day:02d}"

        url_base = f"{url_name}/{year_info}/{month_info}/"
        file_in_url = f"{url_path_name}{year_info}{month_info}{day_info}{extension}"

        urls.append(f"{url_base}{file_in_url}")
        current_date += timedelta(days=1)

    return pd.DataFrame(urls, columns=["urls"])


def download_files(urls, output_dir, log_file):
    """
    Download files from a list of URLs.

    Parameters
    ----------
    urls : list of str
        List of URLs to download.
    output_dir : str
        Directory to save downloaded files.
    log_file : str
        Path to the log file.
    """
    with open(log_file, "a", encoding="utf-8") as log:
        for url in tqdm(urls["urls"], desc="Downloading files", unit="file"):
        #for url in urls["urls"]:
            try:
                response = requests.get(url, timeout=2000)
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))

                file_name = os.path.basename(url)
                output_path = os.path.join(output_dir, file_name)

                with open(output_path, "wb") as file, tqdm(
                    #file.write(response.content)
                    desc=f"- Downloading {file_name}",
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    leave=False # continue same bar progress
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=1024): #8192
                        file.write(chunk)
                        pbar.update(len(chunk))

                log.write(f"Downloaded: {url}\n")

            except requests.exceptions.RequestException as e:
                log.write(f"Error downloading {url}: {e}\n")


def get_data_ftp_cptec(output_dir, folder_name, product, period, aggregation="all"):
    """
    Download climate data from the CPTEC/INPE FTP for SAMeT or MERGE products.

    The function retrieves SAMeT (daily maximum, minimum, and mean temperature) or MERGE (precipitation) datasets directly from the official CPTEC/INPE FTP service: https://ftp.cptec.inpe.br/modelos/tempo/

    The downloaded files are stored in a user-defined folder structure, and a log file is generated to record the download process.

    Parameters
    ----------
    output_dir : str
        Path to the directory where the files will be stored.
    folder_name : str
        Name of the folder to be created inside ``output_dir`` to organize the files.
    product : str
        Product name. Options:
        - ``"SAMeT"``: Daily maximum, minimum, and mean temperature.
        - ``"MERGE"``: Daily precipitation (GPM/IMERG-based).
    period : list of str
        List with start and end dates in the format ``["YYYY-MM-DD", "YYYY-MM-DD"]``.
        Example: ``["2010-01-01", "2010-03-31"]``.
    aggregation : str or list of str, optional
        Aggregations available only for ``SAMeT``:
        - ``"max"`` - Maximum temperature (TMAX).
        - ``"min"`` - Minimum temperature (TMIN).
        - ``"mean"`` - Mean temperature (TMED).
        - ``"all"`` - Downloads all three indicators (default).
        If ``MERGE`` is selected, this parameter is ignored.

    Raises
    ------
    ValueError
        If required parameters are missing or incorrectly defined.
        If an invalid product or aggregation is provided.

    Returns
    -------
    None
        The function saves NetCDF (.nc) files for SAMeT or GRIB2 (.grib2) files for MERGE in the specified directory and generates a log file with the download status.

    Notes
    -----
    - Data is downloaded directly from the CPTEC/INPE FTP service.
    - For SAMeT, files are stored in subfolders by indicator (TMAX, TMIN, TMED).
    - For MERGE, files are saved in the specified ``folder_name`` directory.
    - A log file named ``<folder_name>_YYYYMMDD.log`` is created to record the process.
    - The function automatically generates text files listing the requested file names and links.
    
    Examples
    --------
    >>> from cube4health.eclimpr.download_cptec_ftp_data import get_data_ftp_cptec

    Download SAMeT (temperature) data
    
    >>> get_data_ftp_cptec(
    ...     output_dir="/path/to/save",
    ...     folder_name="temperature_samet",
    ...     product="SAMeT",
    ...     aggregation="all",
    ...     period=["2010-01-01", "2010-03-31"]
    ... )

    This will create a folder ``temperature_samet`` containing subfolders ``TMAX``, ``TMIN``, and ``TMED`` with the corresponding NetCDF files for the defined period.

    Download MERGE (precipitation) data

    >>> get_data_ftp_cptec(
    ...     output_dir="/path/to/save",
    ...     folder_name="precipitation_merge",
    ...     product="MERGE",
    ...     period=["2025-01-14", "2025-02-14"]
    ... )

    This will create a folder ``precipitation_merge`` containing the daily GRIB2 precipitation files from 14 January 2025 to 14 February 2025.

    """
    print("\n--- Starting download data ...\n")

    if None in [output_dir, folder_name, product, period] or len(period) != 2:
        raise ValueError("Error: All parameters must be defined.")

    # Normalize paths
    output_dir = os.path.normpath(output_dir)

    # Create a new folder for output files
    new_dir = create_new_dir(output_dir, folder_name)

    # Create a log file
    log_file = os.path.join(new_dir, f"{folder_name}_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "w") as log:
        log.write("Start download data...\n")

    # Base URL
    url = "https://ftp.cptec.inpe.br/modelos/tempo/"

    # Process SAMeT product
    if product.upper() == "SAMET":
        print("\nSAMeT:")

        if aggregation == "all":
            indicators = ["TMAX", "TMIN", "TMED"]
        else:
            indicators = []
            if "max" in aggregation:
                indicators.append("TMAX")
            if "min" in aggregation:
                indicators.append("TMIN")
            if "mean" in aggregation:
                indicators.append("TMED")

        if not indicators:
            raise ValueError("Error: Invalid aggregation. Use 'max', 'min', 'mean', or 'all'.")

        for indicator in indicators:
            daily_dir = os.path.join(new_dir, indicator)
            os.makedirs(daily_dir, exist_ok=True)

            url_link = f"{url}SAMeT/DAILY/{indicator}"
            url_filename = f"SAMeT_CPTEC_{indicator}_"

            urls_list = generate_urls(url_link, url_filename, period, ".nc")
            urls_list.to_csv(os.path.join(daily_dir, f"{product.upper()}_{indicator}_namefiles_links.txt"), index=False, header=False)

            print(f"\n- {indicator}:")

            download_files(urls_list, daily_dir, log_file)

    # Process MERGE product
    elif product.upper() == "MERGE":
        url_link = f"{url}MERGE/GPM/DAILY"
        url_filename = "MERGE_CPTEC_"

        urls_list = generate_urls(url_link, url_filename, period, ".grib2")
        urls_list.to_csv(os.path.join(new_dir, f"{product.upper()}_namefiles_links.txt"), index=False, header=False)

        print("\nMERGE:")

        download_files(urls_list, new_dir, log_file)

    else:
        raise ValueError("Error: Product must be 'SAMeT' or 'MERGE'.")

    with open(log_file, "a") as log:
        log.write("Processing finished successfully!\n")

    print(f"\nSaved log file in {log_file}")
    print("\n... Done!\n")
