"""Module providing functions to work with data download from FTP - CPTEC/INPE."""
import os
from datetime import datetime, timedelta
import requests
import pandas as pd
from tqdm import tqdm
from .utils import create_new_dir

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
    Get data from FTP CPTEC/INPE for SAMeT or MERGE products.

    Parameters
    ----------
    output_dir : str
        Directory path where the files will be stored.
    folder_name : str
        Name of the folder to be created.
    product : str
        Product name ("SAMeT" or "MERGE").
    period : list of str
        List with start and end dates in format ["YYYY-MM-DD", "YYYY-MM-DD"].
    aggregation : list of str
        List of aggregations for SAMeT ("max", "min", "mean", or "all").
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
