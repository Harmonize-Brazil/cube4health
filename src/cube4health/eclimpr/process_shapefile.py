"""Module providing functions to work with shapefiles."""
import os
import re
import time
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.mask import mask
from osgeo import gdal
import geobr
import geopandas as gpd
import numpy as np
from natsort import natsorted  # Correct order of filenames
from tqdm import tqdm  # To progress bar
import folium
from shapely.geometry import box
from typing import Literal
import warnings


# -----------
# Functions to work with raster by shapefile and raster:
# -----------

def save_map_shapefile(shapefile_path, indicator_dir):
    """
    Plots a geographic map from a Shapefile and saves it as an interactive HTML file.

    This function reads a Shapefile, reprojects it to WGS84 (EPSG:4326) for visualization, calculates the bounding box and centroid, and creates an interactive map using Folium. The map includes the study area geometry and its bounding box, and is saved as an HTML file.

    Parameters
    ----------
    shapefile_path : str
        Path to the Shapefile containing the geographic data of the study area.
    indicator_dir : str
        Directory path where the generated HTML map file will be saved.

    Returns
    -------
    None
        The function saves the map as an HTML file in the specified directory but does not return any value.
    """

    # Ignore the specific warning about geographic CRS
    warnings.filterwarnings("ignore", category=UserWarning, message="Geometry is in a geographic CRS.*")

    # Load the Shapefile
    gdf = gpd.read_file(shapefile_path)

    # Check and ensure the CRS is WGS84 (EPSG:4326)
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    print("Shapefile CRS:", gdf.crs)

    # Check if geometries are valid
    if not gdf.geometry.is_valid.all():
        print("Some geometries are invalid. Fixing...")
        gdf = gdf[gdf.geometry.is_valid]  # Remove invalid geometries

    # Reproject to a projected CRS (e.g., UTM zone 25S for Brazil)
    gdf_projected = gdf.to_crs("EPSG:32725")  # Use the appropriate UTM zone for your area

    # Calculate the centroid in the projected CRS
    centroid_projected = gdf_projected.geometry.centroid

    # Convert the centroid back to WGS84
    centroid_wgs84 = centroid_projected.to_crs("EPSG:4326")
    centroid_coords = [centroid_wgs84.y.mean(), centroid_wgs84.x.mean()]

    # Calculate the bounding box
    minx, miny, maxx, maxy = gdf.total_bounds
    bounding_box = box(minx, miny, maxx, maxy)  # Create a bounding box polygon
    bounding_box_gdf = gpd.GeoDataFrame(geometry=[bounding_box], crs="EPSG:4326")  # Convert to GeoDataFrame

    # Calculate the centroid to center the map
    centroid = gdf.geometry.centroid
    centroid_coords = [centroid.y.mean(), centroid.x.mean()]

    # Create the Folium map
    m = folium.Map(
        location=centroid_coords,  # Center on the Shapefile's centroid
        zoom_start=10,  # Initial zoom level
        control_scale=True  # Add scale to the map
    )

    # Add the Shapefile to the map
    folium.GeoJson(
        gdf,  # Pass the GeoDataFrame directly
        style_function=lambda x: {
            'color': 'blue',  # Border color
            'weight': 1.5,    # Border thickness
            'fillColor': 'lightblue',  # Fill color
            'fillOpacity': 0.5  # Fill transparency
        },
        name="Shapefile"  # Layer name
    ).add_to(m)

    # Add the bounding box to the map
    folium.GeoJson(
        bounding_box_gdf,  # Pass the bounding box GeoDataFrame
        style_function=lambda x: {
            'color': 'red',  # Border color
            'weight': 2,     # Border thickness
            'fillColor': 'transparent',  # No fill
        },
        name="Bounding Box"  # Layer name
    ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Save the map as an HTML file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    m.save(os.path.join(indicator_dir, f"study_area_map_{timestamp}.html"))


def resample_by_standard_extent(raster_list):
    """
    Resample a list of rasters to a standard extent and resolution.

    Parameters
    ----------
    raster_list : list of rasterio.DatasetReader
        List of raster files to be resampled.

    Returns
    -------
    list of numpy.ndarray
        List of resampled rasters as numpy arrays.

    Raises
    ------
    ValueError
        If the input raster list is empty.
    """
    if not raster_list:
        raise ValueError("List of rasters is empty.")

    # Get the union of all extents
    bounds = [raster.bounds for raster in raster_list]
    min_x = min(b.left for b in bounds)
    max_x = max(b.right for b in bounds)
    min_y = min(b.bottom for b in bounds)
    max_y = max(b.top for b in bounds)
    best_extent = (min_x, min_y, max_x, max_y)

    # Get the resolution of the first raster
    reso = raster_list[0].res
    nrow_ncol = (
        int((max_x - min_x) / reso[0]),
        int((max_y - min_y) / reso[1])
    )

    # Create a template raster with the best extent and resolution
    profile = raster_list[0].profile
    profile.update({
        'width': nrow_ncol[0],
        'height': nrow_ncol[1],
        'transform': rasterio.transform.from_bounds(*best_extent, nrow_ncol[0], nrow_ncol[1])
    })

    # Resample all rasters to the template
    resampled_rasters = []
    for raster in raster_list:
        data = raster.read(1)
        resampled_data = np.zeros((nrow_ncol[1], nrow_ncol[0]), dtype=data.dtype)
        reproject(
            source=data,
            destination=resampled_data,
            src_transform=raster.transform,
            dst_transform=profile['transform'],
            src_crs=raster.crs,
            dst_crs=profile['crs'],
            resampling=Resampling.nearest
        )
        resampled_rasters.append(resampled_data)

    return resampled_rasters



def set_band_names_geotiff(tif_path, band_names):
    """
    Sets band names for a multi-band GeoTIFF using GDAL.

    Parameters
    ----------
    tif_path : str
        Path to the GeoTIFF file.
    band_names : list of str
        List of band names to assign.

    Returns
    -------
    None
    """
    # Open the raster in update mode
    dataset = gdal.Open(tif_path, gdal.GA_Update)

    if dataset is None:
        raise FileNotFoundError(f"Could not open {tif_path}")

    # Ensure the number of band names matches the raster bands
    num_bands = dataset.RasterCount
    if len(band_names) != num_bands:
        raise ValueError(f"Number of band names ({len(band_names)}) does not match number of bands ({num_bands})")

    # Set names for each band
    for i, name in enumerate(band_names):
        dataset.GetRasterBand(i + 1).SetDescription(name)

    # Close dataset to save changes
    dataset = None

    #print(f"Band names successfully updated for {tif_path}")


def cut_raster_create_stack_files(path_files, shape_area, pattern_name, stack_name):
    """
    Crop rasters by a study area and create a stack.

    Parameters
    ----------
    path_files : str
        Path to the directory containing raster files.
    shape_area : geopandas.GeoDataFrame
        Shapefile of the area to use for cropping.
    pattern_name : str
        Pattern in the file name to filter rasters.
    stack_name : str
        Name in the file of the stack raster.

    Returns
    -------
    list of numpy.ndarray
        List of cropped rasters as numpy arrays.
    """
    # List all raster files that match the pattern
    filenames = [os.path.join(path_files, f) for f in os.listdir(path_files) if f.startswith(pattern_name) and f.endswith(".tif")]
    filenames = natsorted(filenames)

    rt_list = []
    names = []
    meta=None

    for filename in filenames:
        with rasterio.open(filename) as src:
            # extract date
            date = re.compile(r"\d{4}-\d{2}-\d{2}")
            # generate layer name for each raster stack
            date_files = re.search(date, filename)
            formatted_name = f"{pattern_name}_{date_files.group().replace('-', '')}"

            # Crop the raster using the bounding box
            out_image, out_transform = mask(dataset=src,
                                            shapes=shape_area.geometry,
                                            crop=True,
                                            pad=True,
                                            nodata=np.nan)
            rt_list.append(out_image[0])  # Assuming single-band rasters
            names.append(formatted_name)

            # Store metadata (first iteration only)
            if meta is None:
                meta = src.meta.copy()
                meta.update({
                    "count": len(filenames),  # Number of layers in the stack
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })

    # Convert list to numpy array (stack)
    raster_stack = np.stack(rt_list, axis=0)

    # Convert NaN by a special value of nodata
    raster_stack = np.nan_to_num(raster_stack, nan=-9999)
    meta.update({"nodata": -9999})

    # Save as a new GeoTIFF file
    output_path = os.path.join(path_files, f"{os.path.basename(path_files)}_{stack_name}_raster.tif")
    with rasterio.open(output_path, "w", **meta) as dst:
        for i in range(raster_stack.shape[0]):
            dst.write(raster_stack[i], i + 1) # Write each band
        # add a general metadata with band names
        # dst.update_tags(band_names =",".join(names))  # Store as unique string. Do not work, using gdal, it is ok

    set_band_names_geotiff(output_path, names)

    #return raster_stack
    return output_path # return the path of stack
    #return rt_list


def crop_raster_by_area(data_dir, study_area_bbox):
    """
    Crop rasters by a study area and create a stack for each directory.

    Parameters
    ----------
    data_dir : str
        Path to the directory containing subdirectories with raster files.
    study_area_bbox : geopandas.GeoDataFrame
        Shapefile of the area bounding box.

    Returns
    -------
    list of list of strings - numpy.ndarray
        List of stacks for each directory.
    """
    set_of_dirs = [os.path.join(data_dir, d) for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    set_of_dirs = natsorted(set_of_dirs)

    crs_dst="EPSG:4326"

    # Convert the bounding box to a GeoDataFrame
    study_area_bbox = gpd.GeoDataFrame(geometry=[study_area_bbox], crs=crs_dst)

    print("\nCreating a stack raster by each folder and study region ...\n")

    stack_from_muni = []
    for y, dir_path in enumerate(tqdm(set_of_dirs)):
        if not os.listdir(dir_path):
            continue  # Skip empty directories

        stack = cut_raster_create_stack_files(dir_path, study_area_bbox, "daily", "stack")
        stack_from_muni.append(stack)

    print("... Done\n")

    return stack_from_muni


def crop_raster_by_area_rhumidity(data_dir, study_area_bbox):
    """
    Crop rasters by a study area and create stacks for temperature and dewpoint.

    Parameters
    ----------
    data_dir : str
        Path to the directory containing subdirectories with raster files.
    study_area_bbox : geopandas.GeoDataFrame
        Shapefile of the area bounding box.

    Returns
    -------
    tuple of list of numpy.ndarray
        Two lists: one for temperature stacks and one for dewpoint stacks.
    """
    set_of_dirs = [os.path.join(data_dir, d) for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    set_of_dirs = natsorted(set_of_dirs)

    crs_dst="EPSG:4326"

    # Convert the bounding box to a GeoDataFrame
    study_area_bbox = gpd.GeoDataFrame(geometry=[study_area_bbox], crs=crs_dst)

    print("\nCreating a stack raster by each folder and study region ...\n")

    stack_from_muni_temp = []
    stack_from_muni_dewpoint = []
    for y, dir_path in enumerate(tqdm(set_of_dirs)):
        if not os.listdir(dir_path):
            continue  # Skip empty directories

        # Temperature
        stack_temp = cut_raster_create_stack_files(dir_path, study_area_bbox,
                                                   "daily_temp", "temp_stack")
        stack_from_muni_temp.append(stack_temp)

        # Dewpoint temperature
        stack_dewpoint = cut_raster_create_stack_files(dir_path, study_area_bbox,
                                                       "daily_dewpoint", "dewpoint_stack")
        stack_from_muni_dewpoint.append(stack_dewpoint)

    print("... Done\n")

    return list[stack_from_muni_temp, stack_from_muni_dewpoint]


# -----------
# Functions to prepare a shapefile to use in the processing:
# -----------

def processed_shapefile(main_dir, own_shapefile=False, shapefile_path=None, list_columns=None, cod_mun=None, uf_name=None, geobr_scope: Literal["municipality", "state"] = "municipality", geobr_year=2022):
    """
    Process a shapefile (from user or geobr) and formats it, extracting specific columns. Case data is from geobr, choose a single municipality or a state code

    Process and standardize a shapefile (from user or geobr) to have exactly three attributes: 'cod_mun', 'name_mun', 'uf_mun' and 'geometry' (WGS84).
    
    Parameters
    ----------
    main_dir : str
        Directory where the processed shapefile will be stored.
    own_shapefile : bool, optional
        If False, data is loaded from geobr. If True, a user-provided shapefile is used.
        Default is False (load from geobr).
    shapefile_path : str, optional
        Path to the user-provided shapefile (required when own_shapefile=True).
    list_columns : list of str, optional
        Mapping of column names in the user-provided shapefile to the expected ones.
        Must have the keys: {'code_muni','name_muni','abbrev_state','geometry'}.
        Example:
            {
                'code_muni': 'CD_MUN',
                'name_muni': 'NM_MUN',
                'uf_state': 'UF',
                'geometry': 'geometry'
            }.
    cod_mun : int, optional
        7-digit municipality code (when loading a single municipality from geobr).
        Required when own_shapefile=False and geobr_scope="municipality".
    uf_name : str, optional
        Two-letter state code (e.g., "RJ", "RN"). Required when
        own_shapefile=False and geobr_scope="state".
    geobr_scope : {"municipality", "state"}, optional
        Scope for geobr download: a single municipality by code, or all municipalities of a state.
        Default is "municipality".
    geobr_year : int, optional
        Reference year for geobr data. Default is 2022.

    Returns
    -------
    gpd.GeoDataFrame
        Processed GeoDataFrame with columns ['cod_mun','name_mun','uf_mun','geometry'] in EPSG:4326.
.

    Raises
    ------
    ValueError
        If required arguments are missing or invalid.
    """

    if main_dir is None:
        raise ValueError("'main_dir' must be defined.")

    # Normalize path
    main_dir = os.path.abspath(main_dir)
    os.makedirs(main_dir, exist_ok=True)

    if own_shapefile is False:
        # --- Load from geobr data loading to a single municipality or state ---
        if geobr_scope == "municipality":
            if cod_mun is None:
                raise ValueError("For geobr_scope='municipality', 'cod_mun' must be provided.")
            try:
                study_area_shp_muni = geobr.read_municipality(code_muni=cod_mun, year=geobr_year)
            except ValueError as e:
                raise ValueError(
                    f" Municipality code '{cod_mun}' is not valid for year {geobr_year}. "
                    f"Check if the code is correct or try another year.\n"
                    f"Original error: {e}"
                )
            except Exception as e:
                raise RuntimeError(
                    f" Unexpected error while loading municipality '{cod_mun}' from geobr: {e}"
                )

        elif geobr_scope == "state":
            if uf_name is None or not isinstance(uf_name, str) or len(uf_name) != 2:
                raise ValueError("For geobr_scope='state', 'uf' must be a two-letter string (e.g., 'RJ').")
            try:
                study_area_shp_muni = geobr.read_municipality(code_muni=uf_name.upper(), year=geobr_year)
            except ValueError as e:
                raise ValueError(
                    f" UF name '{uf_name.upper()}' is not valid for year {geobr_year}. "
                    f"Check if the code is correct or try another year.\n"
                    f"Original error: {e}"
                )
            except Exception as e:
                raise RuntimeError(
                    f" Unexpected error while loading UF municipalities '{uf_name.upper()}' from geobr: {e}"
                )
        else:
            raise ValueError("geobr_scope must be 'municipality' or 'state'.")

        study_area_shp_new = study_area_shp_muni[["code_muni", "name_muni", "abbrev_state", "geometry"]].copy()
        # Ensure integer code (Int64 allows NA if any)
        study_area_shp_new["code_muni"] = study_area_shp_new["code_muni"].astype("Int64")

        study_area_shp_new = study_area_shp_new.rename(
            columns={
                "code_muni": "cod_mun",
                "name_muni": "name_mun",
                "abbrev_state": "uf_mun",
                "geometry": "geometry"
            }
        )

        # Output path
        if geobr_scope == "municipality":
            out_name = f"geobr_{int(cod_mun)}_processed"
        else:
            out_name = f"geobr_{uf_name.upper()}_processed"

        # Transform to WGS84
        study_area_shp_new = study_area_shp_new.to_crs("EPSG:4326")

        # Export processed shapefile
        output_path = os.path.join(main_dir, f"{out_name}.shp")
        study_area_shp_new.to_file(output_path, driver="ESRI Shapefile")

    else:
        # --- User-provided shapefile ---
        # As dictionary
        if shapefile_path is None or list_columns is None:
            raise ValueError("When own_shapefile=True, 'shapefile_path' and 'list_columns' are required.")

        required_keys = {"code_muni", "name_muni", "uf_state", "geometry"}
        if not required_keys.issubset(set(list_columns.keys())):
            raise ValueError("list_columns must contain keys: 'code_muni', 'name_muni', 'uf_state', 'geometry'.")

        # Load the user-provided shapefile
        study_area_shp = gpd.read_file(shapefile_path)

        # Extract columns based on user-provided dictionary
        user_columns = [
            list_columns["code_muni"],
            list_columns["name_muni"],
            list_columns["uf_state"],
            list_columns["geometry"],
        ]
        study_area_shp_new = study_area_shp[user_columns].copy()

        # Rename columns to standard names
        study_area_shp_new.columns = ["cod_mun", "name_mun", "uf_mun", "geometry"]

        # Ensure integer municipality code if possible
        # (use Int64 to preserve missing values if any)
        study_area_shp_new["cod_mun"] = study_area_shp_new["cod_mun"].astype("Int64")

        # Transform to WGS84
        study_area_shp_new = study_area_shp_new.to_crs("EPSG:4326")

        # Save the processed shapefile
        shp_layer = os.path.splitext(os.path.basename(shapefile_path))[0]
        output_path = os.path.join(main_dir, f"{shp_layer}_processed.shp")
        study_area_shp_new.to_file(output_path, driver="ESRI Shapefile")

    print("Created New Shapefile - Done")
    return study_area_shp_new


