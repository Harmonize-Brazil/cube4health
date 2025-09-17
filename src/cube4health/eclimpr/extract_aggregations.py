"""Module providing functions to extract aggregations or other values from stack."""
import os
import re
import warnings
import glob
import numpy as np
import rasterio
import pandas as pd
import geopandas as gpd
from datetime import datetime
from natsort import natsorted  # Correct order of filenames
from tqdm import tqdm  # Progress bar
from shapely.geometry import Point
from rasterio.transform import from_origin
from unidecode import unidecode
from rasterio.mask import mask
from shapely.geometry import box
from shapely.geometry import Polygon

from cube4health.eclimpr.generate_cog_tiff import (
    convert_to_cog_gdal,
    save_raster
)

# -----------
# Functions to extract max, min and mean values from temperature and precipitation:
# -----------

def extract_max_min_mean_stack(stack_raster, output_dir, indicator_name_local, extension_folder, extension_spatial, aggregation):
    """
    Extract specified aggregated values from a raster stack and save the results as GeoTIFF files.

    Parameters
    ----------
    stack_raster : numpy.ndarray
        Stack of raster data with shape (bands, height, width).
    output_dir : str
        Directory where the output files will be saved.
    indicator_name_local : list of str
        Indicator name to add to the output files.
    extension_folder : str
        Extension folder name ("epiweek" or "month").
    extension_spatial : str
        Spatial aggregation level ("municipality", "health region", or "state").
    aggregation : list of str
        List of aggregations to compute ("max", "min", "mean", or "all").

    Returns
    -------
    dict
        Dictionary containing requested raster arrays and the transform.
    """

    warnings.filterwarnings('ignore', category=RuntimeWarning)

    match = re.search(r"(\d{8}_\d{8})", os.path.basename(output_dir))

    if extension_folder == "epiweek":
        folder_name = f"epiweek_{match.group(1)}"
    elif extension_folder == "month":
        folder_name = f"month_{match.group(1)}"
    else:
        raise ValueError("Extension folder must be 'epiweek' or 'month'.")

    with rasterio.open(stack_raster) as src:
        raster_data = src.read(masked=True).filled(np.nan)
        transform_raster = src.transform

    results = {'transform': transform_raster}

    if 'all' in aggregation or 'max' in aggregation:
        stack_max = np.nanmax(raster_data, axis=0)
        max_out = os.path.join(output_dir, f"{indicator_name_local[0]}_max_{indicator_name_local[1]}_{extension_spatial}_{folder_name}.tif")
        save_raster(max_out, stack_max, stack_raster)
        max_out_cog = os.path.join(output_dir, f"{indicator_name_local[0]}_max_{indicator_name_local[1]}_{extension_spatial}_{folder_name}_COG.tif")
        convert_to_cog_gdal(max_out, max_out_cog)
        os.remove(max_out)
        results['max'] = stack_max

    if 'all' in aggregation or 'min' in aggregation:
        stack_min = np.nanmin(raster_data, axis=0)
        min_out = os.path.join(output_dir, f"{indicator_name_local[0]}_min_{indicator_name_local[1]}_{extension_spatial}_{folder_name}.tif")
        save_raster(min_out, stack_min, stack_raster)
        min_out_cog = os.path.join(output_dir, f"{indicator_name_local[0]}_min_{indicator_name_local[1]}_{extension_spatial}_{folder_name}_COG.tif")
        convert_to_cog_gdal(min_out, min_out_cog)
        os.remove(min_out)
        results['min'] = stack_min

    if 'all' in aggregation or 'mean' in aggregation:
        stack_mean = np.nanmean(raster_data, axis=0)
        mean_out = os.path.join(output_dir, f"{indicator_name_local[0]}_mean_{indicator_name_local[1]}_{extension_spatial}_{folder_name}.tif")
        save_raster(mean_out, stack_mean, stack_raster)
        mean_out_cog = os.path.join(output_dir, f"{indicator_name_local[0]}_mean_{indicator_name_local[1]}_{extension_spatial}_{folder_name}_COG.tif")
        convert_to_cog_gdal(mean_out, mean_out_cog)
        os.remove(mean_out)
        results['mean'] = stack_mean

    return results


def extract_indicators_max_min_mean(data_dir, shapefile_edit, stack_raster, indicator_name_local, extension_folder, extension_spatial, aggregation):
    """
    Extract specified aggregated values from raster stacks and save the results.

    Parameters
    ----------
    data_dir : str
        Directory containing subdirectories with raster stacks.
    shapefile_edit : geopandas.GeoDataFrame
        Shapefile to which the extracted values will be added.
    stack_raster : list of numpy.ndarray
        List of raster stacks.
    indicator_name_local : list of str
        Indicator name to add to the output files.
    extension_folder : str
        Extension folder name ("epiweek" or "month").
    extension_spatial : str
        Spatial aggregation level ("municipality", "health region", or "state").
    aggregation : list of str
        List of aggregations to compute ("max", "min", "mean", or "all").

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the dates of the processed periods.
    """

    set_of_dirs = [os.path.join(data_dir, d) for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    set_of_dirs = natsorted(set_of_dirs)

    # Copy shapefile only if necessary
    if 'all' in aggregation or 'max' in aggregation:
        shapefile_edit_max = shapefile_edit.copy()
    if 'all' in aggregation or 'min' in aggregation:
        shapefile_edit_min = shapefile_edit.copy()
    if 'all' in aggregation or 'mean' in aggregation:
        shapefile_edit_mean = shapefile_edit.copy()

    print("\nGenerating specified aggregated values from each stack raster...\n")

    date_list = []
    for y, dir_path in enumerate(tqdm(set_of_dirs)):
        if not os.listdir(dir_path):
            continue  # Skip empty directories

        # Extract only desired aggregations
        results = extract_max_min_mean_stack(
            stack_raster[y], dir_path, indicator_name_local, extension_folder, extension_spatial, aggregation
        )

        transform = results['transform']

        # Extract epiweek or month number by means of folder name
        if extension_folder == 'epiweek':
            # Extract week number with two, 2, digits
            week_match = re.search(r'epiweek_(\d+)_\d{8}_\d{8}', os.path.basename(dir_path))
            folder_number = f"{int(week_match.group(1)):02d}"  # two, 2, digites equals to epiweek
        elif extension_folder == 'month':
            # Extract month number with two digits and start date
            month_match = re.search(r'month_(\d{8})_\d{8}', os.path.basename(dir_path))
            folder_start_date = datetime.strptime(month_match.group(1), "%Y%m%d").date()
            folder_number = f"{folder_start_date.month:02d}"  # two digits month number
        else:
            raise ValueError(f"Unsupported extension_folder: {extension_folder}")

        # Extract date from directory name
        match = re.search(r"(_\d{8})", os.path.basename(dir_path))
        name_date = f"w{match.group(1)}"
        epiweek_month_str = re.sub("-", "", re.search(r'\d{8}_\d{8}', os.path.basename(set_of_dirs[y])).group(0))
        date_list.append((epiweek_month_str, folder_number, extension_folder, extension_spatial))

        # Add stats in columns
        if 'all' in aggregation or 'max' in aggregation:
            shapefile_edit_max[name_date] = raster_stats(results['max'], shapefile_edit, 'max', transform, all_touched=True)

        if 'all' in aggregation or 'min' in aggregation:
            shapefile_edit_min[name_date] = raster_stats(results['min'], shapefile_edit, 'min', transform, all_touched=True)

        if 'all' in aggregation or 'mean' in aggregation:
            shapefile_edit_mean[name_date] = raster_stats(results['mean'], shapefile_edit, 'mean', transform, all_touched=True)

    # Save shapefiles for only the desired aggregations
    if 'all' in aggregation or 'max' in aggregation:
        shapefile_edit_max.to_file(os.path.join(os.path.dirname(data_dir), f"{indicator_name_local[0]}_max_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}.shp"))

    if 'all' in aggregation or 'min' in aggregation:
        shapefile_edit_min.to_file(os.path.join(os.path.dirname(data_dir), f"{indicator_name_local[0]}_min_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}.shp"))

    if 'all' in aggregation or 'mean' in aggregation:
        shapefile_edit_mean.to_file(os.path.join(os.path.dirname(data_dir), f"{indicator_name_local[0]}_mean_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}.shp"))

    # List to dataframe
    dates_epiweek = pd.DataFrame(date_list, columns=['epiweek_month','epiweek_month_number','time_agg','spatial_agg'])

    print("... Done\n")
    return dates_epiweek


def raster_stats(raster_data, shapefile, stat, transform, all_touched=True):
    """
    Extract statistics from a raster based on a shapefile.

    Parameters
    ----------
    raster_data : numpy.ndarray
        Raster data to extract statistics from.
    shapefile : geopandas.GeoDataFrame
        Shapefile defining the regions for statistics.
    stat : str
        Statistic to calculate ('max', 'min', or 'mean').
    transform : affine.Affine
        The affine transform of the raster.
    all_touched : bool, optional
        If True, include all pixels that are touched by the geometry.
        If False, include only pixels whose center is within the geometry.

    Returns
    -------
    numpy.ndarray
        Array of statistics for each region in the shapefile.

    Raises
    ------
    ValueError
        If an invalid statistic type is provided.
    """

    # Ensure the calculation is done for each region

    # Ignore warnings related to empty slices
    warnings.filterwarnings('ignore', category=RuntimeWarning)

    nodata_value = -9999

    stats = []
    for _, geom in shapefile.iterrows():
        # create a mask for each single geometry
        mask = rasterio.features.geometry_mask([geom['geometry']],
                                               transform=transform,
                                               invert=True,
                                               out_shape=raster_data.shape,
                                               all_touched=all_touched)

        # Apply mask to the raster (True = masked values)
        masked_raster = np.where(mask, raster_data, np.nan)

        # Ensure there are valid pixels for calculation
        if np.isnan(masked_raster).all():
            stats.append(np.nan)
            continue

        # Replace NoData (-9999) by NaN
        masked_raster[masked_raster == nodata_value] = np.nan

        # Filter values ​​within the expected range (if necessary)
        valid_pixels = masked_raster[~np.isnan(masked_raster)]

        if valid_pixels.size == 0:
            stats.append(np.nan)
            continue

        if stat == 'max':
            stat_value = np.nanmax(valid_pixels) # masked_raster
        elif stat == 'min':
            stat_value = np.nanmin(valid_pixels)
        elif stat == 'mean':
            stat_value = np.nanmean(valid_pixels)
        else:
            raise ValueError("Stat must be 'max', 'min', or 'mean'.")

        stats.append(stat_value)

    return np.array(stats)


# -----------
# Functions to deal with anomaly temperature values:
# -----------

def remove_accent_marks(dataframe_file):
    """
    Remove accent marks or diacritics from columns of a dataframe.

    Parameters
    ----------
    dataframe_file : pd.DataFrame
        The dataframe with file.

    Returns
    -------
    pd.DataFrame
        Dataframe without accent marks.
    """
    # col.strip() remove white space in begin or end name column
    dataframe_file.columns = [unidecode(col.strip()) for col in dataframe_file.columns]
    return dataframe_file


def idw_interpolation(xyz_data, grid, power=2):
    """
    Perform Inverse Distance Weighting (IDW) interpolation.

    Parameters
    ----------
    xyz_data : numpy.ndarray
        A 2D array of shape (n, 3) containing the input data points.
        - Column 0: X coordinates (longitude or easting).
        - Column 1: Y coordinates (latitude or northing).
        - Column 2: Z values (values to be interpolated).

    grid : dict
        A dictionary containing the grid coordinates for interpolation.
        - Key 'x': 1D array of X coordinates (longitude or easting).
        - Key 'y': 1D array of Y coordinates (latitude or northing).

    power : float, optional
        The power parameter for IDW, which controls the influence of distant points.
        Higher values give more weight to closer points. Default is 2.

    Returns
    -------
    numpy.ndarray
        A 2D array of shape (len(grid['y']), len(grid['x'])) containing the interpolated values.

    Notes
    -----
    - The IDW method assumes that the influence of a point decreases with distance.
    - If a grid point coincides with a data point, the data point's value is used directly.
    - The function handles division by zero by assigning a large weight (1e12) to coincident points.
    """
    # Extract the coordinates and values of known points
    x_coords, y_coords, z_values = xyz_data[:, 0], xyz_data[:, 1], xyz_data[:, 2]
    # Create the interpolation grid
    grid_x, grid_y = np.meshgrid(grid['x'], grid['y'])

    # Flatten grid arrays for easier calculation
    xi, yi = grid_x.flatten(), grid_y.flatten()

    # Initialize grid_z with zeros
    grid_z = np.zeros_like(xi)
    weights = np.zeros_like(xi)

    # Iterate over each known point
    for x, y, z in zip(x_coords, y_coords, z_values):
        # Calculate the Euclidean distance between the known point and all grid points
        dist = np.sqrt((xi - x)**2 + (yi - y)**2)
        # Calculates weight as the inverse of distance raised to the power
        with np.errstate(divide='ignore'):
            w = 1 / (dist ** power)

        # Handle cases where distance is zero (replace by a very large weight)
        w[np.isinf(w)] = 1e12

        # Accumulates the weighted values and weights
        grid_z += w * z
        weights += w

    # Calculate the interpolated value as the weighted average
    grid_z = np.divide(grid_z, weights, out=np.zeros_like(grid_z), where=weights!=0)

    # Reshape the interpolated array to the original grid format
    return grid_z.reshape(grid_x.shape)


def select_stations_from_area(main_dir, study_area_bbox, shapefile_path, conv_stations_file_csv, clima_normal_file_xlsx):
    """
    Perform IDW interpolation based on conventional stations and climatological normals,
    and save the results as a shapefile with computed monthly climatological normals.

    Parameters
    ----------
    main_dir : str
        The main directory where output files will be saved. Paths are normalized for compatibility
        across operating systems.

    study_area_bbox : list or tuple
        The bounding box of the study area in the format [min_longitude, min_latitude, max_longitude, max_latitude].

    shapefile_path : str
        The path to the shapefile defining the study area boundaries.

    conv_stations_file_csv : str
        The path to the CSV file containing conventional station data. The file should have columns
        for station ID, latitude, longitude, and other relevant attributes.

    clima_normal_file_xlsx : str
        The path to the Excel file containing climatological normals. The file should have columns
        for station ID and monthly normals (e.g., January, February, etc.).

    Returns
    -------
    geopandas.GeoDataFrame
        A GeoDataFrame containing the study area polygons with new columns for monthly climatological
        normals (e.g., 'nc_Jan', 'nc_Feb', etc.).

    Notes
    -----
    - The function performs the following steps:
        1. Reads and filters conventional station data within the study area bounding box.
        2. Reads and merges climatological normals with station data.
        3. Performs IDW interpolation for each month using the station data.
        4. Computes the mean climatological normal for each polygon in the study area.
        5. Saves the results as a shapefile and a multiband GeoTIFF raster stack.

    - The IDW interpolation uses a power parameter of 2 by default.
    """
    # Normalize path for Windows and Linux
    main_dir = os.path.normpath(main_dir)

    # Print a message indicating that the process was started
    print("\nGeneration IDW Interpolation based in conventional stations and climatological normals ...\n")

    # Read conventional stations CSV
    conventional_stations = pd.read_csv(conv_stations_file_csv, sep=";", decimal=",")
    conventional_stations = remove_accent_marks(conventional_stations)

    # Load the study area shapefile
    study_area = shapefile_path
    #study_area = gpd.read_file(shapefile_path)
    #study_area_bbox = box(*study_area.total_bounds)

    # Select conventional_stations into study_area_bbox
    conventional_stations_bbox = conventional_stations[
        (conventional_stations['VL_LATITUDE'] >= study_area_bbox.bounds[1]) &
        (conventional_stations['VL_LATITUDE'] <= study_area_bbox.bounds[3]) &
        (conventional_stations['VL_LONGITUDE'] >= study_area_bbox.bounds[0]) &
        (conventional_stations['VL_LONGITUDE'] <= study_area_bbox.bounds[2])
    ]

    # Create a GeoDataFrame from the filtered stations
    geometry = [Point(xy) for xy in zip(conventional_stations_bbox['VL_LONGITUDE'], conventional_stations_bbox['VL_LATITUDE'])]
    #conventional_stations_gdf = gpd.GeoDataFrame(conventional_stations_bbox, geometry=geometry, crs="EPSG:4326")

    # Read climatological normals Excel file
    normal_clima_tmax = pd.read_excel(clima_normal_file_xlsx, skiprows=2)
    normal_clima_tmax = remove_accent_marks(normal_clima_tmax)

    # Filter climatological normals by stations within the bbox
    normal_clima_tmax_study = normal_clima_tmax[normal_clima_tmax['Codigo'].isin(conventional_stations_bbox['CD_ESTACAO'])]

    # Merge climatological normals with conventional stations
    merged_data = pd.merge(normal_clima_tmax_study, conventional_stations_bbox, left_on='Codigo', right_on='CD_ESTACAO')

    # Convert relevant columns to numeric
    numeric_cols = merged_data.columns[merged_data.columns.isin(['Codigo'] + list(map(str, range(3, 14))) + list(map(str, range(19, 21))))]
    merged_data[numeric_cols] = merged_data[numeric_cols].apply(pd.to_numeric, errors='coerce')

    # Create a GeoDataFrame for the merged data
    geometry = [Point(xy) for xy in zip(merged_data['VL_LONGITUDE'], merged_data['VL_LATITUDE'])]
    climatological_normal_gdf = gpd.GeoDataFrame(merged_data, geometry=geometry, crs="EPSG:4326")

    # Create a grid for interpolation
    res = 0.0104522  # Resolution in degrees
    bounds = study_area.total_bounds
    x_coords = np.arange(bounds[0], bounds[2], res)
    y_coords = np.arange(bounds[1], bounds[3], res)
    grid_x, grid_y = np.meshgrid(x_coords, y_coords)

    # Prepare the grid for IDW interpolation
    grid = {'x': x_coords, 'y': y_coords}

    # Perform IDW interpolation for each month
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Columns in merged_data
    merged_months = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
                     'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    # List to interpolated arrays
    interpolated_arrays = []

    for i, month in enumerate(merged_months):
        # Select the data for the current month
        data = merged_data[['VL_LONGITUDE', 'VL_LATITUDE', month]].copy()  # Avoid warning about SettingWithCopyWarning

        # Convert the month column to numeric, forcing errors to NaN
        data.loc[:, month] = pd.to_numeric(data[month], errors='coerce')

        # Drop rows with NaN values
        data = data.dropna()

        # Verify if there is enough data to interpolate
        if len(data) == 0:
            print(f"Não há dados suficientes para o mês {month}. Pulando...")
            continue

        # Perform IDW interpolation
        interpolated_values = idw_interpolation(data.values, grid)

        # Add interpolated array interpolado to list
        interpolated_arrays.append(interpolated_values)

        # # Rasterize the interpolated values and save each one
        # transform = from_origin(bounds[0], bounds[3], res, res)
        # with rasterio.open(
        #     os.path.join(main_dir, f'interpolated_{months[i]}.tif'),
        #     'w',
        #     driver='GTiff',
        #     height=interpolated_values.shape[0],
        #     width=interpolated_values.shape[1],
        #     count=1,
        #     dtype=interpolated_values.dtype,
        #     crs='EPSG:4326',
        #     transform=transform,
        # ) as dst:
        #     dst.write(interpolated_values, 1)

        # Extract mean values for each polygon in the study area
        study_area[f'nc_{months[i]}'] = study_area.geometry.apply(
            lambda geom: np.nanmean(interpolated_values[
                (grid_x >= geom.bounds[0]) & (grid_x <= geom.bounds[2]) &
                (grid_y >= geom.bounds[1]) & (grid_y <= geom.bounds[3])
            ])
        )

    # Stack the interpolated arrays into a single 3D array
    raster_stack = np.stack(interpolated_arrays, axis=0)  # Format: (number of months, height, width)

    # Defines the raster properties
    transform = from_origin(bounds[0], bounds[3], res, res)
    metadata = {
        'driver': 'GTiff',
        'height': raster_stack.shape[1],
        'width': raster_stack.shape[2],
        'count': raster_stack.shape[0],   # Number of bands (months)
        'dtype': raster_stack.dtype,
        'crs': 'EPSG:4326',
        'transform': transform
    }

    # Saves the raster stack as a multiband GeoTIFF file
    with rasterio.open(os.path.join(main_dir, 'interpolated_stack.tif'), 'w', **metadata) as dst:
        dst.write(raster_stack)

    # Save the final shapefile with the new columns
    output_shapefile_path = os.path.join(main_dir, "climatological_normal_computed_months.shp")
    study_area.to_file(output_shapefile_path)

    # Print a message indicating that the process was finished successfully
    print("... Done\n")

    return study_area



def extract_month(number_month):
    """
    Convert a month number(1-12) in format 'nc_Month' (i.e.: 'nc_Jan').

    Parameters
    ----------
    number_month : int
        Month number (1 - 12)

    Returns
    -------
    str
        String in format 'nc_Month' (i.e.: 'nc_Jan')

    """
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Verify if month number is valid
    if not 1 <= number_month <= 12:
        raise ValueError("Month number must be between 1 and 12")

    month = months[number_month - 1]  # -1 because Python uses index 0-based
    return f"nc_{month}"


def get_band_names(raster_path):
    """
    Returns the band names of a raster file, including descriptions.

    Parameters
    ----------
    raster_path : str
        Path to the raster file

    Returns
    -------
    list
        List of band names
    """
    with rasterio.open(raster_path) as src:
        # Attempts to get the band descriptions
        band_names = []

        for i in range(1, src.count + 1):
            # Checks the main description of the band
            desc = src.descriptions[i-1] if src.descriptions else None

            # If there's no description, checks the tags
            if not desc:
                tags = src.tags(i)
                desc = tags.get('DESCRIPTION', tags.get('description', None))

            # If still not found, uses the default
            band_names.append(desc if desc else f'Band {i}')

    return band_names


def extract_max_from_stack(raster_stack_path, shapefile_normal, month_normal):
    """
    Extracts maximum values from a multiband raster stack for each polygon in the shapefile.

    Parameters
    ----------
    raster_stack_path : str
        Path to the multiband raster stack file
    shapefile_normal : str
        Path to the municipalities shapefile
    month_normal : float
        Climatological normal value to add as a column

    Returns
    -------
    pandas.DataFrame
        DataFrame with maximum values per date and the normal value
    """

    #filename = os.path.basename(raster_stack_path)

    # Creates list of dates
    band_names = get_band_names(raster_stack_path)
    # Extracts dates from filename (format epiweek_XX_YYYYMMDD_YYYYMMDD)
    #start_date = filename.split('_')[2]  # 20190113
    #end_date = filename.split('_')[3]    # 20190119

    dates_found = []
    for name in band_names:
        match = re.search(r'\d{8}', name)  # Looks for 8 consecutive digits
        if match:
            dates_found.append(match.group())

    # Creates complete date range for the raster stack
    start_date = min(dates_found)
    end_date = max(dates_found)

    dates = pd.date_range(start=start_date, end=end_date).strftime('%Y%m%d').tolist()

    # List to store results
    results = []

    with rasterio.open(raster_stack_path) as src:
        # For each municipality in the shapefile
        for idx, row in shapefile_normal.iterrows():

            # Extracts geometry
            geom = [row.geometry.__geo_interface__]

            # List for values from this municipality
            munic_values = []

            # For each band in the raster stack
            for band in range(1, src.count + 1):
                try:
                    # Clips raster to the polygon
                    out_image, _ = rasterio.mask.mask(src, geom, crop=True, nodata=np.nan, indexes=[band], all_touched=True)
                    max_val = np.nanmax(out_image)  # Maximum value ignoring NaNs
                    munic_values.append(max_val)
                except:
                    munic_values.append(np.nan)

            # Adds to results list
            results.append(munic_values)

    # Creates final DataFrame
    df = pd.DataFrame(results, columns=dates)
    # Adds column with normal value
    df['normal'] = shapefile_normal[[month_normal]]

    return df


def count_consecutive_days(row):
    """
    Calculates the maximum number of consecutive days where temperature
    exceeded the normal value.

    Args:
        row (pd.Series): A DataFrame row with temperature values
                         and 'normal' column as last element

    Returns:
        int: Maximum number of consecutive days above normal
    """
    count = 0
    max_consecutive_days = 0
    normal_value = row['normal']  # Accesses by column name

    # Converts Series to numpy array (excluding 'normal' column)
    temp_values = row.drop('normal').values

    for temp in temp_values:
        if temp > normal_value:
            count += 1
            max_consecutive_days = max(max_consecutive_days, count)
        else:
            count = 0

    return max_consecutive_days


def extract_anomaly(data_dir, shapefile_idw_nc, indicator_name_local, extension_folder, extension_spatial):
    """
    Extract the anomaly for each municipality in the study region based on climatological normals.

    Parameters
    ----------
    data_dir : str
        Directory containing raster files organized by epiweek or month.
    shapefile_idw_nc : str
        Path to the shapefile with climatological normals calculated using IDW interpolation.
    indicator_name_local : list of str
        Names of the indicators to be used in the output files (e.g., ["max_temperature", "anomaly"]).
    extension_folder : str
        Type of aggregation folder ("epiweek" or "month").
    extension_spatial : str
        Type of spatial aggregation ("municipality", "health_region", or "state").

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing the dates (epiweeks or months) processed.

    Notes
    -----
    - The function performs the following steps:
        1. Iterates over directories containing raster stacks.
        2. Extracts maximum values for each municipality.
        3. Computes anomalies based on climatological normals.
        4. Saves shapefiles with anomaly results.
    """
    #main_dir = os.path.dirname(data_dir)
    set_of_dirs = [os.path.join(data_dir, d) for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    set_of_dirs = natsorted(set_of_dirs)

    # Copy of shapefile only with interesting columns
    shapefile_edit_ano_num_days = shapefile_idw_nc[["cod_mun", "name_mun", "uf_mun", "geometry"]]
    shapefile_edit_ano_con_days = shapefile_idw_nc[["cod_mun", "name_mun", "uf_mun", "geometry"]]

    print("\nGeneration of shapefile anomaly from each Stack Raster ...\n")

    date_list = []
    for y, dir_path in enumerate(tqdm(set_of_dirs)): #tqdm(set_of_dirs)):
        if not os.listdir(dir_path):
            continue

        # Create a copy of the shapefile for this iteration
        shapefile_edit = shapefile_idw_nc.copy()

        raster_stack = glob.glob(os.path.join(set_of_dirs[y], "*_stack_raster.tif"))[0]

        # Select only file name with extension *_stack_raster.tif (stack)
        filename = os.path.basename(raster_stack)
        # Extract start and end date of period from file name
        all_period_date = re.search(r'\d{8}_\d{8}', os.path.basename(filename)).group(0)
        # Extract firts sequence of 8 digits from input string
        main_date = re.search(r"\d{8}", filename).group()
        # Extract month and convert month to two digits and extract
        main_date_month = int(main_date[4:6])

        # Extract month from stack
        month_stack = extract_month(main_date_month)

        # Compute max values from stack and shapefile
        data_final = extract_max_from_stack(raster_stack_path =raster_stack,
                                     shapefile_normal=shapefile_edit,
                                     month_normal=month_stack)

        # Add multiples columns
        shapefile_edit = pd.concat([shapefile_edit, data_final], axis=1)

        ### 1- Anomaly from number of layers, days, (epiweek or month) that max temperature is greater than climatological normal
        # Calculate number of days where max temp exceeds climatological normal
        # Compare each day's temp to normal value and count exceedances

        # First select only date columns (format YYYYMMDD)
        date_cols = [col for col in data_final.columns if col.isdigit() and len(col) == 8]

        # Make sure 'normal' column exists
        if 'normal' not in data_final.columns:
            raise ValueError("Column 'normal' not found in DataFrame")

        # Use numpy to avoid pandas alignment issues
        temp_values = data_final[date_cols].values
        normal_values = data_final['normal'].values.reshape(-1, 1)  # Convert to column matrix

        # Calculate number of days above normal
        shapefile_edit['num_days'] = (temp_values > normal_values).sum(axis=1)

        # Convert to integer
        shapefile_edit['num_days'] = shapefile_edit['num_days'].astype(int)

        # Add column with 'w_' prefix to anomalies shapefile
        name_date = f"w_{main_date.replace('-', '')}"
        shapefile_edit_ano_num_days = shapefile_edit_ano_num_days.copy() # to avoid warning SettingWithCopyWarning
        shapefile_edit_ano_num_days[name_date] = shapefile_edit['num_days']


        ### 2- Anomaly from number of consecutive columns, layers | days, (epiweek or month) with the max temperature greater than column "normal"
        # Function to count the number of columns consecutive, days, with the max temperature greater than column "normal"
        shapefile_edit['cons_days'] = data_final.apply(count_consecutive_days, axis=1).astype(int)

        shapefile_edit_ano_con_days = shapefile_edit_ano_con_days.copy() # to avoid warning SettingWithCopyWarning
        shapefile_edit_ano_con_days[name_date] = shapefile_edit['cons_days']

        # Save shapefiles
        shapefile_edit.to_file(os.path.join(set_of_dirs[y], f"anomaly_{indicator_name_local[0]}_max_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}_{all_period_date}.shp"))

        # Extract epiweek or month number by means of folder name
        if extension_folder == 'epiweek':
            # Extract week number with two, 2, digits
            week_match = re.search(r'epiweek_(\d+)_\d{8}_\d{8}', os.path.basename(dir_path))
            folder_number = f"{int(week_match.group(1)):02d}"  # two, 2, digites equals to epiweek
        elif extension_folder == 'month':
            # Extract month number with two digits and start date
            month_match = re.search(r'month_(\d{8})_\d{8}', os.path.basename(dir_path))
            folder_start_date = datetime.strptime(month_match.group(1), "%Y%m%d").date()
            folder_number = f"{folder_start_date.month:02d}"  # two digits month number
        else:
            raise ValueError(f"Unsupported extension_folder: {extension_folder}")

        # Extract start and end dates from directory name
        dir_name = os.path.basename(set_of_dirs[y])
        #date_range = '_'.join([part for part in dir_name.split('_') if part.isdigit() and len(part) == 8][:2])
        epiweek_month_str = re.sub("-", "", re.search(r'\d{8}_\d{8}', os.path.basename(set_of_dirs[y])).group(0))
        #date_list.append(date_range)
        date_list.append((epiweek_month_str, folder_number, extension_folder, extension_spatial))

    # Save shapefiles with anomalies
    shapefile_edit_ano_num_days.to_file(os.path.join(os.path.dirname(data_dir), f"anomaly_ndays_{indicator_name_local[0]}_max_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}.shp"))

    shapefile_edit_ano_con_days.to_file(os.path.join(os.path.dirname(data_dir), f"anomaly_cdays_{indicator_name_local[0]}_max_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}.shp"))

    ## List to dataframe
    #dates_epiweek = pd.DataFrame(date_list, columns=['epiweek'])
    # List to dataframe
    dates_epiweek = pd.DataFrame(date_list, columns=['epiweek_month','epiweek_month_number','time_agg','spatial_agg'])

    print("... Done\n")
    return dates_epiweek



# -----------
# Functions to deal with relative humidity values:
# -----------

def extract_relative_humidity(data_dir, shapefile_edit, indicator_name_local, extension_folder, extension_spatial):
    """
    Extract relative humidity for each municipality in the study region.

    Calculates relative humidity using the Magnus formula:
    RH (%) = 100 * exp((b * c * (Td - T)) / ((c + Td) * (c + T)))
    where b = 17.625, c = 243.04, T is 2m temperature, and Td is 2m dewpoint temperature.

    Parameters
    ----------
    data_dir : str
        Directory containing raster data organized by epiweek or month.
    shapefile_edit : gpd.GeoDataFrame
        GeoDataFrame with municipality polygons to add new columns.
    stack_raster : Tuple[List[str], List[str]]
        Tuple containing two lists of raster paths (temperature and dewpoint).
    indicator_name_local : List[str]
        Names for output files (e.g., ["relative_humidity", "study_region"]).
    extension_folder : str
        Time aggregation type ("epiweek" or "month").
    extension_spatial : str
        Spatial aggregation level ("municipality", "health_region", or "state").

    Returns
    -------
    pd.DataFrame
        DataFrame with processed dates (epiweeks or months).

    Notes
    -----
    Formula reference: Alduchov O.A., Eskridge R.E. (1996). Improved Magnus form
    approximation of saturation vapor pressure. Journal of Applied Meteorology
    and Climatology, 35(4), 601-9.
    """

    # Constants for RH calculation
    B = 17.625
    C = 243.04

    # Validate extension_folder
    if extension_folder not in ["epiweek", "month"]:
        raise ValueError("extension_folder must be either 'epiweek' or 'month'")

    # Get all subdirectories (epiweeks/months)
    #main_dir = os.path.dirname(data_dir)
    set_of_dirs = [os.path.join(data_dir, d) for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    set_of_dirs = natsorted(set_of_dirs)

    # Prepare output directory structure
    if extension_folder == "epiweek":
        f_name = "epiweek_"
    elif extension_folder == "month":
        f_name = "month_"
    else:
        raise ValueError("Extension folder must be 'epiweek' or 'month'.")

    # Create a copy of the shapefile for this iteration
    shapefile_edit_mean = shapefile_edit.copy()

    # Print a message indicating that the process is starting
    print("Generation of shapefile relative humidity from each Stack Raster ...")

    date_list = []
    for y, dir_path in enumerate(tqdm(set_of_dirs)): #tqdm(set_of_dirs)):
        # Skip empty directories
        if not os.listdir(dir_path):
            continue

        date_match = re.search(r"\d{8}_\d{8}", os.path.basename(dir_path)).group(0)
        if not date_match:
            warnings.warn(f"Skipping directory with invalid date format: {dir_path}")
            continue

        folder_name  = f"{f_name}{date_match}"

        # This stack into temp and dewpoint
        stack_temp = glob.glob(os.path.join(set_of_dirs[y], "*_temp_stack_raster.tif"))[0]
        stack_dewpoint = glob.glob(os.path.join(set_of_dirs[y], "*_dewpoint_stack_raster.tif"))[0]

        # Creates list of dates
        band_names = get_band_names(stack_dewpoint)
        # Add column with 'l_' prefix to relative humidity shapefile
        # Extracts dates from filename (format 'daily_dewpoint_YYYYMMDD')
        # date_names = [f"l_{name.split('_')[-1]}" for name in band_names]

        # Load temperature and dewpoint rasters
        try:
            with rasterio.open(stack_temp) as temp_src, \
                 rasterio.open(stack_dewpoint) as dewpoint_src:
                # Create nodata mask to onde of the stacks and use this information after, to avoid white border
                nodata_val = dewpoint_src.nodata
                mask = dewpoint_src.read(1) == nodata_val
                transform_raster = dewpoint_src.transform  # Extract the transform from raster

                # Read all bands (layers)
                temp_data = temp_src.read()
                dewpoint_data = dewpoint_src.read()

                # Calculate relative humidity using vectorized operations
                numerator = B * C * (dewpoint_data - temp_data)
                denominator = (C + dewpoint_data) * (C + temp_data)
                relative_humidity_stack = 100 * np.exp(numerator / denominator)

                # Calculate mean across all layers
                stack_mean = np.nanmean(relative_humidity_stack, axis=0)
                # Apply mask to output raster
                stack_mean[mask] = nodata_val

                # Define band names
                # set_band_names_geotiff(stack_mean, date_names)

                # Save mean RH as GeoTIFF
                mean_out = os.path.join(dir_path, f"{indicator_name_local[0]}_percent_{indicator_name_local[1]}_{extension_spatial}_{folder_name}.tif")
                save_raster(mean_out, stack_mean, stack_dewpoint)
                mean_out_cog = os.path.join(dir_path, f"{indicator_name_local[0]}_percent_{indicator_name_local[1]}_{extension_spatial}_{folder_name}_COG.tif")
                convert_to_cog_gdal(mean_out, mean_out_cog)
                os.remove(mean_out)

                # Extract date from directory name
                match = re.search(r"(_\d{8})", os.path.basename(dir_path))
                name_date = f"w{match.group(1)}"    # Create date string to append to column names

                # Extract epiweek or month number by means of folder name
                if extension_folder == 'epiweek':
                    # Extract week number with two, 2, digits
                    week_match = re.search(r'epiweek_(\d+)_\d{8}_\d{8}', os.path.basename(dir_path))
                    folder_number = f"{int(week_match.group(1)):02d}"  # two, 2, digites equals to epiweek
                elif extension_folder == 'month':
                    # Extract month number with two digits and start date
                    month_match = re.search(r'month_(\d{8})_\d{8}', os.path.basename(dir_path))
                    folder_start_date = datetime.strptime(month_match.group(1), "%Y%m%d").date()
                    folder_number = f"{folder_start_date.month:02d}"  # two digits month number
                else:
                    raise ValueError(f"Unsupported extension_folder: {extension_folder}")

                #date_list.append(re.sub("-", "", re.search(r'\d{8}_\d{8}', os.path.basename(set_of_dirs[y])).group(0)))
                epiweek_month_str = re.sub("-", "", re.search(r'\d{8}_\d{8}', os.path.basename(set_of_dirs[y])).group(0))
                date_list.append((epiweek_month_str, folder_number, extension_folder, extension_spatial))

                # Add from rasterio.mask import mask
                # Extract mean values for each municipality
                shapefile_edit_mean[name_date] = raster_stats(stack_mean, shapefile_edit, 'mean', transform_raster, all_touched=True)

        except Exception as e:
            warnings.warn(f"Error processing {dir_path}: {str(e)}")
            continue

    ## List to dataframe
    #dates_epiweek = pd.DataFrame(date_list, columns=['epiweek'])
    # List to dataframe
    dates_epiweek = pd.DataFrame(date_list, columns=['epiweek_month','epiweek_month_number','time_agg','spatial_agg'])

    # Save final shapefile with all mean values
    shapefile_edit_mean.to_file(os.path.join(os.path.dirname(data_dir), f"{indicator_name_local[0]}_percent_{indicator_name_local[1]}_{extension_spatial}_{extension_folder}.shp"))

    # Print a message indicating that the process was finished successfully
    print("... Done\n")

    return(dates_epiweek)

