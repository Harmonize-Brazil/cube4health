"""Module providing a function work with PNG files."""
import os
import subprocess
import rasterio
import numpy as np
import geopandas as gpd
import pandas as pd  # Adicionado para usar pd.cut
import matplotlib.pyplot as plt
from natsort import natsorted  # Correct order of filenames
import importlib.resources as pkg_resources

# -----------
# Functions:
# -----------

def create_png_from_cog_ind_shell(cog_dir, color_png_file):
    """
    Create PNG files from COG files using a shell script.

    Parameters
    ----------
    cog_dir : str
        Directory path where the COG .tif files are stored.
    color_png_file : str
        Path to the file with the range of colors for PNG.
    """
    if cog_dir is None or color_png_file is None:
        raise ValueError("Error: parameters must be defined.")

    # Normalize paths
    cog_dir = os.path.normpath(cog_dir)
    color_png_file = os.path.normpath(color_png_file)

    # Call the shell script with the arguments using subprocess
    # shell_script = os.path.join(os.path.dirname(__file__), "data", "gdal_script_convert_TIFF_COG_to_Color_PNG.sh")
    shell_script = pkg_resources.files('eclimpr.data').joinpath('gdal_script_convert_TIFF_COG_to_Color_PNG.sh')
    subprocess.run(["bash", shell_script, cog_dir, color_png_file], check=True)

    print("\nCreated PNG files for each epi week date successfully!\n")


def create_png_from_cog_dir(cog_dir, color_png_file):
    """
    Create PNG files from COG files in a directory.

    Parameters
    ----------
    cog_dir : str
        Directory path where the COG .tif files are stored.
    color_png_file : str
        Path to the file with the range of colors for PNG.
    """
    if cog_dir is None or color_png_file is None:
        raise ValueError("Error: parameters must be defined.")

    # Normalize paths
    cog_dir = os.path.normpath(cog_dir)

    # List all COG files in the directory
    list_raster_files = [os.path.join(cog_dir, f) for f in os.listdir(cog_dir) if f.endswith(".tif")]
    list_raster_files = natsorted(list_raster_files)

    if list_raster_files:
        for raster_file in list_raster_files:
            create_png_from_cog_file(raster_tif=raster_file, output_dir=cog_dir, color_png_file=color_png_file)
    else:
        print("Folder is empty!\n")


def create_png_from_cog_file(raster_tif=None, output_dir=None, color_png_file=None):
    """
    Generate a PNG file from a raster GeoTIFF file using a custom color scale.

    Parameters:
    - raster_tif (str): Path to the input raster GeoTIFF file.
    - output_dir (str): Directory where the PNG file will be saved.
    - color_png_file (str): Path to the file containing color definitions.
    """

    # Read the raster file
    with rasterio.open(raster_tif) as src:
        raster_data = src.read(1)
        nodata_value = src.nodata if src.nodata is not None else -9999

    # Print unique values from the raster for debugging
    unique_values_before = np.unique(raster_data)
    #print(f"Unique values in raster before masking: {unique_values_before}")

    # Mask nodata values
    if nodata_value in unique_values_before:
        masked_data = np.ma.masked_values(raster_data, nodata_value)
    else:
        #print(f"Warning: The specified nodata value ({nodata_value}) is not present in the raster.")
        masked_data = np.ma.masked_invalid(raster_data)

    # Print unique values after masking
    #unique_values_after = np.unique(masked_data)
    #print(f"Unique values in raster after masking: {unique_values_after}")

    # Print data range for verification
    #print(f"Raster data range after masking: min={masked_data.min()}, max={masked_data.max()}")

    # Read the color definition file
    color_definition = pd.read_csv(color_png_file, sep='\s+', header=None)
    intervals = color_definition[0].values
    rgb_colors = color_definition[1].apply(lambda x: [int(i) for i in x.split(':')]).tolist()
    rgb_colors = np.array(rgb_colors) / 255.0  # Normalize RGB values to [0, 1]

    # Print intervals for verification
    #print(f"Intervals: {intervals}")

    # Create a new image array for RGB
    color_mapped_data = np.zeros((masked_data.shape[0], masked_data.shape[1], 3), dtype=np.float32)

    # Apply the colormap based on nearest intervals
    for i in range(masked_data.shape[0]):
        for j in range(masked_data.shape[1]):
            if not masked_data.mask[i, j]:
                value = masked_data[i, j]
                idx = (np.abs(intervals - value)).argmin()
                color_mapped_data[i, j, :] = rgb_colors[idx]

    # Plot the RGB image
    plt.figure(figsize=(5, 5))
    plt.imshow(color_mapped_data)
    plt.axis('off')

    # Save the plot as a PNG file
    output_png = os.path.join(output_dir, os.path.splitext(os.path.basename(raster_tif))[0] + ".png")
    plt.savefig(output_png, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close()

    # Print a message indicating that the process was finished successfully
    # print(f"PNG {output_png} was generated successfully.")


def map_anomaly_colors(values, intervals, rgb_colors):
    """
    Map anomaly values to colors using interval logic.

    Parameters
    ----------
    values : array-like
        Array of values from the shapefile.
    intervals : array-like
        Array of interval thresholds.
    rgb_colors : array-like
        Array of RGB colors normalized to [0, 1].

    Returns
    -------
    List of RGBA colors mapped to each value.
    """
    bin_indices = np.digitize(values, intervals, right=True)
    bin_indices[np.isnan(values)] = -1  # Handle NaNs

    mapped_colors = []
    for idx in bin_indices:
        if idx == -1:
            mapped_colors.append([1, 1, 1, 0])  # Transparent
        else:
            mapped_colors.append(rgb_colors[min(idx, len(rgb_colors) - 1)])

    return mapped_colors


# Create PNG colored from SHP
def create_png_from_shp_file(shapefile_dir, color_png_file, anomaly_data=False):
    """
    Create PNG files from Shapefile files.

    Parameters
    ----------
    shapefile_dir : str
        Directory path where the Shapefile .shp files are stored.
    color_png_file : str
        Path to the file with the range of colors for PNG.
    anomaly_data : bool
        If True, handles anomaly data differently. Default is False
    """
    value_column = "value"

    if shapefile_dir is None or color_png_file is None:
        raise ValueError("Error: parameters must be defined.")

    # Extract intervals and colors
    color_definition = pd.read_csv(color_png_file, sep='\s+', header=None)
    intervals = color_definition[0].values
    rgb_colors = color_definition[1].apply(lambda x: [int(i) for i in x.split(':')]).tolist()
    rgb_colors = np.array(rgb_colors) / 255.0  # Normalizar para [0, 1]

    # Read the Shapefile
    shapefile_path = [os.path.join(shapefile_dir, f) for f in os.listdir(shapefile_dir) if f.endswith(".shp")][0]
    study_area_shp = gpd.read_file(shapefile_path)
    study_area_shp = study_area_shp.to_crs("EPSG:4326")  # Transform to WGS84

    # Verify if column value exist
    if value_column not in study_area_shp.columns:
        raise ValueError(f"Column '{value_column}' does not exist.")

    # Obtain the values from interesting column
    values = study_area_shp[value_column].values

    # Map colors for each polygon
    colors = []
    for value in values:
        if np.isnan(value):
            colors.append([1, 1, 1, 0])  # Transparent (RGBA)
        else:
            # Find the index of the interval closest to 'value'.
            # For example, if intervals = [0, 10, 20, 30] and value = 18,
            # then np.abs(intervals - value) = [18, 8, 2, 12], so argmin() returns index 2 (value 20).
            # intervals - value = [0 - 18, 10 - 18, 20 - 18, 30 - 18] = [-18, -8, 2, 12]
            # That index is then used to select the corresponding RGB color.
            idx = (np.abs(intervals - value)).argmin()  # Get nearest index
            colors.append(rgb_colors[idx])

    # Create a custom colormap customizado for plot
    # cmap = ListedColormap(rgb_colors)

    if not anomaly_data:
        # Map values to the intervals with cut function
        fig, ax = plt.subplots(figsize=(5, 5))
        study_area_shp.plot(ax=ax, color=colors, edgecolor="black", linewidth=0.7)
        ax.set_xlim(study_area_shp.total_bounds[[0, 2]])  # xmin, xmax
        ax.set_ylim(study_area_shp.total_bounds[[1, 3]])  # ymin, ymax
        plt.axis('off')
    else:
        # Map values to the intervals with cut function
        mapped_colors = map_anomaly_colors(values, intervals, rgb_colors)
        fig, ax = plt.subplots(figsize=(5, 5))
        study_area_shp.plot(ax=ax, color=mapped_colors, edgecolor="black", linewidth=0.7)
        ax.set_xlim(study_area_shp.total_bounds[[0, 2]])
        ax.set_ylim(study_area_shp.total_bounds[[1, 3]])
        plt.axis('off')

    # Save the plot as a PNG file
    output_png = os.path.join(shapefile_dir, os.path.splitext(os.path.basename(shapefile_path))[0] + ".png")
    plt.savefig(output_png, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close()


    #print(f"PNG {output_png} was generated successfully.")
