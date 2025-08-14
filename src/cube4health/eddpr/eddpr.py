#
# This file is part of EODCtHRS Drone Data PRocessing (EDDPR).
# Copyright (C) 2025 HARMONIZE/INPE.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.
#

"""Utility for Drone images collection creation

   Build JSON files to support STAC catalog creation from drone data (RGB/Multispectral/NDVI/Thermal scenes and mosaics). The Assets (spatiotemporal representation of Earth Observation data) 
   files in COG format that is associated with collections are made using EXIF and XMP tags with metadata: height, width, center coordinates (GPS position of aircraft
   when capturing the image), camera focal length, flight yaw degree; and auxiliaries information: width size of the sensor (millimeters) and flying 
   height (meters) available at a JSON file in the path of the source data or passed using parameters.

   This approach is based on JSON files examples from Sentinel available in 
   the examples -> fixtures folder at https://github.com/brazil-data-cube/bdc-catalog.
   """

# --------------------------
#        Imports
# --------------------------
import os
import sys
import subprocess
from PIL import Image, ExifTags, TiffTags #required version >= 9.5
from pathlib import Path
import json
import rasterio
from pyproj import Transformer
from datetime import datetime
from types import SimpleNamespace
from decimal import Decimal, InvalidOperation
import numpy as np
import pandas as pd
from osgeo import osr, gdal
from timezonefinder import TimezoneFinder
from pytz import timezone, utc
from multiprocessing import cpu_count
from tqdm import tqdm
import tempfile
from argparse import ArgumentParser, SUPPRESS
if __name__ !=  "__main__":
    from .drone_projection_warp import main as drone_projection_warp
    from .drone_correction_projection_warp import main as drone_correction_projection_warp
    from .arghelper import is_valid_file, is_valid_directory, is_valid_namefile
    from .publish_drone_data import main as publish_drone_data 

local_path = os.path.dirname(os.path.abspath(__file__))
parent_path = Path(local_path).parent.absolute()

gdal.UseExceptions()  # this allows GDAL to throw Python Exceptions
Image.MAX_IMAGE_PIXELS = None #to prevent the problem of size image
num_workers = int(cpu_count() - (cpu_count() * 0.20)) # using about 80% of cores
tf = TimezoneFinder()  # reuse
bands_name = {'NIR':'NIR', 'RE':'RED EDGE', 'R':'RED','G':'GREEN','NDVI':'NDVI'}
template_view = ['R','NIR','G']
bands_composition = ['Red','NIR','Green']

# -----------
# Functions:
# -----------
def decimal_coords(coords, ref):
    decimal_degrees = coords[0] + (float(coords[1]) / 60) + (float(coords[2]) / 3600)
    if ref == "S" or ref == "W":
        decimal_degrees = -decimal_degrees
    return decimal_degrees


# Features - https://www.dji.com/br/phantom-3-adv
# The sensor is 6.16mm wide and 4.62mm high. The maximum created still image size is 4000 pixels wide by 3000 tall - https://forum.dji.com/forum.php?mod=redirect&goto=findpost&ptid=28597&pid=197705
# Pixel size at sensor (Square): 1.562 micrometer
# Sensor size at X (TSX): 6.248 mm
# Sensor size at Y (TSY): 4.686 mm

# Features - https://sdk-forum.dji.net/hc/en-us/articles/12325496609689-What-is-the-custom-camera-parameters-for-Mavic-3-Enterprise-series-and-Mavic-3M
# The device have 4 cameras (RGB) and Multispectral (G, Red, Red Edge and Near Infrared)
# Image size	5280x3956 (RGB)	2592x1944 (MS)
# Sensor size at X (TSX): 17.4mm (RGB) 5.2mm (MS)
# Sensor size at Y (TSY): 13mm (RGB) 3.9mm (MS)

# Features - https://enterprise.dji.com/mavic-3-enterprise/specs
# The Mavic 3T's thermal camera offers a 640 × 512 resolution and supports features like point and area temperature measurement, high-temperature alerts, customizable color palettes, and isotherms - 
# Thermal Camera Uncooled VOx Microbolometer
# Pixel size at sensor (Pixel Pitch): 12 micrometer
# Equivalent Focal Length 40mm
# Infrared Wavelength 8-14 μm
# Temperature Measurement Range:
# -20° to 150° C (-4° to 302° F, High Gain Mode)
#   0° to 500° C (32° to 932° F, Low Gain Mode)


def get_exif_info(img_path):
    img = Image.open(img_path)
    if img._getexif() != None:
        exif = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}
       
        try:
            coordenadas = exif['GPSInfo']
            altitude =  coordenadas[6]
            lat = decimal_coords(coordenadas[2], coordenadas[1])
            lon = decimal_coords(coordenadas[4], coordenadas[3])
            
        except KeyError:
            print('No Coordinates')            
    else:
        print('The image has no EXIF information:\n'+img_path)
        return None

    return {'focal_lenght':float(exif['FocalLength']),'date':str(exif['DateTime']),'img_dim_x':int(exif['ExifImageWidth']),'img_dim_y':int(exif['ExifImageHeight']),'center_coords':(float(lat),float(lon)),'altitude':float(altitude)}


def get_tags_info(img_path):
    img = Image.open(img_path)
    xmp_info = img.getxmp()
    if xmp_info != None:
        tags_info = {TiffTags.TAGS[key] : img.tag[key] for key in img.tag_v2 if key in TiffTags.TAGS}

        try:
            altitude =  xmp_info['xmpmeta']['RDF']['Description']['RelativeAltitude']
            lat = xmp_info['xmpmeta']['RDF']['Description']['GpsLatitude']
            lon = xmp_info['xmpmeta']['RDF']['Description']['GpsLongitude']
            
        except KeyError:
            print('No Coordinates')       
    else:
        print('The image does not have XPM metadata information:\n'+img_path)
        return None
    return xmp_info,{'focal_lenght':float(xmp_info['xmpmeta']['RDF']['Description']['PerspectiveFocalLength']),
                     'date':str(tags_info['DateTime'][0]),'bits_per_sample':int(tags_info['BitsPerSample'][0]),
                     'img_dim_x':int(tags_info['ImageWidth'][0]),'img_dim_y':int(tags_info['ImageLength'][0]),
                     'center_coords':(float(lat),float(lon)),'flight_yaw_degree':float(xmp_info['xmpmeta']['RDF']['Description']['FlightYawDegree']),'altitude':float(altitude)}


def is_decimal(s):
    try:
        Decimal(s)
        return True
    except InvalidOperation:
        return False


def get_flight_info(fname_out):
    print('Path target:',fname_out)
    info_example = {'flight': 'Abaetetuba_AM03_20221114', 'flight_height_m': 120, 'sensor_width_mm': 6.248, 'sensor_height_mm': 4.686, 'model': 'DJI Phantom 3 Advanced', 'type': 'diurnal'}
    flight_info = {}
    for key,value in info_example.items():
        info = input('Please, type {} info. Example {} :'.format(key,value))
        if key == 'flight_height_m' or key == 'sensor_width_mm' or key == 'sensor_height_mm':
            while is_decimal(info) != True:
                info = input('Please, type {} info. Example {} :'.format(key,value))
            flight_info[key] = float(info)
        else:
            flight_info[key] = info

    #Store file with flight information in flight path:
    with open(fname_out, 'w') as outfile:
        outfile.write(json.dumps(flight_info, indent=4))

    return flight_info


def get_raster_info(raster_file):
    with rasterio.open(raster_file) as img:
        xmin, ymin, xmax, ymax = img.bounds
        srid =  img.crs.to_epsg() #The coordinate reference system used by the asset data
        if 'blockxsize' in img.profile:
            chunck_x =  img.profile['blockxsize']
            chunck_y =  img.profile['blockxsize']
        else:
            chunck_x =  0
            chunck_y =  0
        img_height = img.height
        img_width = img.width        
        pixel_sizex,pixel_sizey = img.res        
        
        # Convert coords to WGS84
        transformer = Transformer.from_crs(img.crs, "EPSG:4326")
        
    # Bounding box of the Item in the asset coordinate reference system (CRS) in native UTM projection    
    bbox = [xmin, ymin, xmax, ymax]
    bbox_geo = {"type":"Polygon","coordinates":[[[bbox[0],bbox[1]], [bbox[2],bbox[1]], [bbox[2],bbox[3]], [bbox[0],bbox[3]], [bbox[0],bbox[1]]]]}  
    
    # GeoJSON geometry object - Defines the footprint of this Item in native UTM projection
    geometry = bbox_geo

    ul_y_x = transformer.transform(xmin,ymax)
    lr_y_x = transformer.transform(xmax,ymin)

    # The bounding box coordinates for the item, projected to wgs84
    bbox_wgs84 = [min(ul_y_x[1],lr_y_x[1]),min(ul_y_x[0],lr_y_x[0]),max(ul_y_x[1],lr_y_x[1]),max(ul_y_x[0],lr_y_x[0])]
    bbox_wgs84_geo = {"type":"Polygon","coordinates":[[[bbox_wgs84[0],bbox_wgs84[1]], [bbox_wgs84[2],bbox_wgs84[1]], [bbox_wgs84[2],bbox_wgs84[3]], [bbox_wgs84[0],bbox_wgs84[3]], [bbox_wgs84[0],bbox_wgs84[1]]]]}

    # GeoJSON geometry object - The geometry coordinates for the polygon, projected to wgs84.
    geometry_wgs84 = bbox_wgs84_geo

    return bbox_geo,geometry,bbox_wgs84_geo,geometry_wgs84,srid,chunck_x,chunck_y,img_height,img_width,round(pixel_sizex,6)


def prepare_thumbnail_v4(filename_out,file_in,composition):    
    """
    Creates a thumbnail from GeoTIFF multispectral raster mosaic from drone data

       :param filename_out: filename output with mission and data identification.
       :type filename: String

       :param file_in: raster multispectral.
       :type file_in: String

       :param composition: list of band names to create a composition.
       :type composition: List
    """

    #-scale [src_min src_max [dst_min dst_max]]: Rescale the input pixels values from the range src_min to src_max to the range dst_min to dst_max. If omitted the output range is 0 to 255 
    # automatically computed from the source data. Alternatively, you could also retrieve the statistics (per band) and make something up yourself. See https://stackoverflow.com/a/50512290 
    #gdal.Translate(tmp_file, str(tiff_file), scaleParams=[[]], options="-a_nodata "+str(nodata)+"-ot Byte -scale -outsize 10% 10%")

    ms_data = gdal.Open(file_in, gdal.GA_ReadOnly)
    bands = {ms_data.GetRasterBand(i).GetDescription(): i for i in range(1, ms_data.RasterCount + 1)}
    stats = [ms_data.GetRasterBand(i+1).GetStatistics(True, True) for i in range(ms_data.RasterCount)]
    ms_data = None

    enum_bands = ""
    scales = ""
    for i,band in enumerate(composition):
        enum_bands += "-b "+ str(bands[band])+" "
        scales += "-scale_"+str(i+1)+" "+str(stats[bands[band]-1][0])+" "+str(stats[bands[band]-1][1])+ " " #get min and max value from each band

    gdal.Translate(filename_out, file_in, options=enum_bands.strip()+" "+scales.strip()+" -ot Byte -of PNG")


# Adapted from test_geotiff_png.py authored by Adeline
def create_png_from_raster(raster_tif=None, output_file=None, color_png_file=None):
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
        nodata_value = src.nodata if src.nodata is not None else nodata

    # Print unique values from the raster for debugging
    unique_values_before = np.unique(raster_data)

    # Mask nodata values
    if nodata_value in unique_values_before:
        masked_data = np.ma.masked_values(raster_data, nodata_value)
    else:
        masked_data = np.ma.masked_invalid(raster_data)

    im = Image.fromarray(masked_data)
    if color_png_file != None:
        # Read the color definition file
        color_definition = pd.read_csv(color_png_file, sep='\s+', header=None)
        intervals = color_definition[0].values
        rgb_colors = color_definition[1].apply(lambda x: [int(i) for i in x.split(':')]).tolist()

        # Create a new image array for RGB
        color_mapped_data = np.zeros((masked_data.shape[0], masked_data.shape[1], 4), dtype=np.uint8)

        # Apply the colormap based on nearest intervals
        for i in range(masked_data.shape[0]):
            for j in range(masked_data.shape[1]):
                if not masked_data.mask[i, j]:
                    value = masked_data[i, j]
                    idx = (np.abs(intervals - value)).argmin()
                    color_mapped_data[i, j, 0:3] = rgb_colors[idx]
                    color_mapped_data[i, j, 3] = 255
        im = Image.fromarray(color_mapped_data)
    im.save(output_file)



def get_local_utc(exif_info):
    """
    Returns a location's datetime from UTC based on lat and lon coordinators

       :param exif_info: contais information from EXIF tags of image.
       :type exif_info: dict
    """
    lat = exif_info['center_coords'][0]
    lng =  exif_info['center_coords'][1]
    date = exif_info['date'].split()[0].replace(':','-')
    time = exif_info['date'].split()[1]    
    
    local = timezone(tf.timezone_at(lng=lng, lat=lat))
    if local != None:
        naive = datetime.strptime(date+" "+time, "%Y-%m-%d %H:%M:%S")
        local_dt = local.localize(naive, is_dst=None)
        utc_dt = local_dt.astimezone(utc)
        return utc_dt.strftime("%Y-%m-%d"),utc_dt.strftime("%H:%M:%S")
    else:
        raise Exception("Impossible to get timezone from this location")


def get_raster_nodata(fname):
    if os.path.exists(fname):
        src_ds = gdal.Open(str(fname), gdal.GA_ReadOnly)

        arr = src_ds.ReadAsArray()
        global nodata
        nodata = src_ds.GetRasterBand(1).GetNoDataValue()
        if nodata == None:
            if len(arr.shape) > 2:
                nodata = int(arr[0,0,0])
            else:
                nodata = int(arr[0,0])
        del arr    

        
# This function convert raster to COG using a global CRS        
def write_cogtiff_v2(fname, out_fname,type=None):
    """ Convert the Geotiff to COG using gdal
        TILED <boolean>: Switch to tiled format
        COPY_SRC_OVERVIEWS <boolean>: Force copy of overviews of source dataset
        COMPRESS=[NONE/DEFLATE]: Set the compression to use.

        Note: The output file uses EPSG:3395 - WGS 84/World Mercator is global coordinate system with unit in meters. Source: https://epsg.io/3395
    """

    # Set up transformers, EPSG:3395 is metric
    crs_dst = 'EPSG:3395'

    block_size_output = 256 #Sets the tile width and height in pixels. Must be divisible by 16. https://gdal.org/drivers/raster/cog.html#general-creation-options

    # Create a COG file:
    if os.path.exists(out_fname) == False:
        src_ds = gdal.Open(str(fname), gdal.GA_ReadOnly)

        alpha_channel = False
        arr = src_ds.ReadAsArray()
        if type == 'RGB' and len(arr.shape) == 3 and arr.shape[0] > 3:
            alpha_channel = True
            # Create temporary filename
            fd, dst_filename = tempfile.mkstemp(suffix='.tif')
            print('Removing alpha channel...')
            gdal.Translate(dst_filename,str(fname), options="-b 1 -b 2 -b 3 -r NEAREST -co NUM_THREADS="+str(num_workers))
        elif type == 'MS' and len(arr.shape) == 3 and arr.shape[0] > 4:
            alpha_channel = True
            # Create temporary filename
            fd, dst_filename = tempfile.mkstemp(suffix='.tif')
            print('Removing alpha channel...')
            gdal.Translate(dst_filename,str(fname), options="-b 1 -b 2 -b 3 -b 4 -r NEAREST -co NUM_THREADS="+str(num_workers))

        global nodata
        nodata = src_ds.GetRasterBand(1).GetNoDataValue()
        if nodata == None:
            if len(arr.shape) > 3:
                nodata = arr[0,0,0,0]
            elif len(arr.shape) > 2:
                nodata = int(arr[0,0,0])
            else:
                nodata = int(arr[0,0])
        del arr
        
        # Once we're done, close properly the dataset
        del src_ds
        
        # Convert to world reference system:
        # https://gdal.org/drivers/raster/cog.html#raster-cog
        # https://erouault.blogspot.com/2014/10/warping-overviews-and-warped-overviews.html
        # -t_srs - Set target spatial reference, -srcnodata, -nosrcalpha - Prevent the alpha band of a source image to be considered as such (it will be warped as a regular band)
        print('Creating COG file...')
        if alpha_channel:
            if type == 'RGB':
                gdal.Warp(out_fname, dst_filename,
                options="-overwrite -multi -wm 80%  -of COG -r NEAREST -ot Byte  -srcnodata "+str(nodata)+" -dstnodata 0 -t_srs "+ crs_dst +"-oo OVERVIEW_LEVEL=5 -co BLOCKSIZE="+str(block_size_output)+" -co COMPRESS=DEFLATE -co BIGTIFF=IF_SAFER -wo OPTIMIZE_SIZE=TRUE -co NUM_THREADS="+str(num_workers))
            elif type == 'MS':
                gdal.Warp(out_fname, dst_filename,
                options="-overwrite -multi -wm 80%  -of COG -r NEAREST -srcnodata "+str(nodata)+" -dstnodata 0 -t_srs "+ crs_dst +"-oo OVERVIEW_LEVEL=5 -co BLOCKSIZE="+str(block_size_output)+" -co COMPRESS=DEFLATE -co BIGTIFF=IF_SAFER -wo OPTIMIZE_SIZE=TRUE -co NUM_THREADS="+str(num_workers))

            os.remove(dst_filename)    #delete temporary file        
        else:
            if type == 'RGB' or 'Thermal':
                gdal.Warp(out_fname, str(fname),
                options="-overwrite -multi -wm 80%  -of COG -r NEAREST -ot Byte  -srcnodata "+str(nodata)+" -dstnodata 0 -t_srs "+ crs_dst +"-oo OVERVIEW_LEVEL=5 -co BLOCKSIZE="+str(block_size_output)+" -co COMPRESS=DEFLATE -co BIGTIFF=IF_SAFER -wo OPTIMIZE_SIZE=TRUE -co NUM_THREADS="+str(num_workers))
            elif type == 'MS':
                gdal.Warp(out_fname, str(fname),
                options="-overwrite -multi -wm 80%  -of COG -r NEAREST -srcnodata "+str(nodata)+" -dstnodata 0 -t_srs "+ crs_dst +"-oo OVERVIEW_LEVEL=5 -co BLOCKSIZE="+str(block_size_output)+" -co COMPRESS=DEFLATE -co BIGTIFF=IF_SAFER -wo OPTIMIZE_SIZE=TRUE -co NUM_THREADS="+str(num_workers))
           

def calc_ndvi(out_fname, fname):
    """ 
    Calculate NDVI from multispectral mosaic and save to COG file

    :param out_fname: filename output with mission and data identification.
    :type out_fname: String

    :param fname: raster multispectral.
    :type fname: String

    Note: The output file uses EPSG:3395 - WGS 84/World Mercator is global coordinate system with unit in meters. Source: https://epsg.io/3395
    """

    # Set up transformers, EPSG:3395 is metric
    crs_dst = 'EPSG:3395'

    # Create a COG file:
    if os.path.exists(out_fname) == False:
        src_ds = gdal.Open(str(fname), gdal.GA_ReadOnly)
        arr = src_ds.ReadAsArray()

        bands = {src_ds.GetRasterBand(i).GetDescription(): i for i in range(1, src_ds.RasterCount + 1)}
        
        NIR = arr[bands['NIR'],...]
        Red = arr[bands['Red'],...]
        ndvi = (NIR - Red)/(NIR + Red)
        ndvi = np.where((ndvi<-1.)|(ndvi>1.),np.nan,ndvi) #remove outliers
        ndvi[np.isnan(ndvi)] = -9999. # define nodata

        driver = gdal.GetDriverByName('MEM') #To avoid error of overview creation
        dst_ds = driver.Create('', xsize=src_ds.RasterXSize, ysize=src_ds.RasterYSize,
                            bands=1, eType=gdal.GDT_Float32)

        #In case of north up images, the GT(2) and GT(4) coefficients are zero,
        #and the GT(1) is pixel width, and GT(5) is pixel height. 
        #The (GT(0),GT(3)) position is the top left corner of the top left pixel of the raster.

        dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
        dst_ds.SetProjection(src_ds.GetProjection())

        band = dst_ds.GetRasterBand(1)
        band.WriteArray(ndvi)
        band.SetDescription("NDVI") # This sets the band name!
        band.SetNoDataValue(-9999.)
        band.FlushCache()
        del band

        # Resampling	one of "AVERAGE", "AVERAGE_MAGPHASE", "RMS", "BILINEAR", "CUBIC", "CUBICSPLINE", "GAUSS", 
        # "LANCZOS", "MODE", "NEAREST", or "NONE" controlling the downsampling method applied     
        dst_ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32])


        gdal.Warp(out_fname, dst_ds,
                options="-overwrite -multi -wm 80%  -of COG -r NEAREST -t_srs "+ crs_dst +"-co COMPRESS=DEFLATE -co BIGTIFF=IF_SAFER -wo OPTIMIZE_SIZE=TRUE -co NUM_THREADS="+str(num_workers))
        
        # Once we're done, close properly the dataset
        src_ds.FlushCache()
        del src_ds
        dst_ds.FlushCache()
        del dst_ds


def process_flights(flights_path,collections_template,catalog_path,prefix_geoserver_data, publish):
    """
    Processing drone data to produce COGs to publish using Geoserver/Titiler and JSON files used for STAC catalog creation. 

       :param flights_path: List with path names containing drone data for each flight.
       :type flights_path: Path

       :param collections_template: A dictionary of dictionaries containing template information from different collections of scenes/mosaics (RGB, Multispectral, NDVI, and Thermal) 
                                    for supported drone models. Attention: To include support for a new device, it's required to create template JSON files with the required information 
                                    for the drone and the collection wanted. See file example for Mavic 3M Multispectral data (mavic3m_flight_height120m_multispectral_template.json).
       :type collections_template: Dict

       :param catalog_path: Path name for output files (COGs and thumbnails).
       :type catalog_path: String

       :param prefix_geoserver_data: String with the parent path name for the data that will be published with Geoserver. For example, our address for Geoserver 
                                     is <https://brazildatacube.dpi.inpe.br/harmonize/dev/geoserver> by default, the service points toa  path containing data using the prefix "dev".
       :type prefix_geoserver_data: String

       :param publish: String with True or False condition to publish the data collections created using STAC catalogs and Geoserver layers.
       :type publish: String

    """
    flights_path = sorted(flights_path)

    #Inicializing items list:
    for key,value in collections_template.copy().items():
        collections_template[key]['items']  = []
    
    
    print('Processing flights...')
    for path in flights_path:
        mission = '_'.join([os.path.basename(Path(path).parent)[:-4], os.path.basename(Path(path))])

        # Processing RGB images:
        list_of_files = list(Path(os.path.join(path,'NADIR_Images')).rglob('*.JPG'))
        list_of_files.sort()
        for file in tqdm(list_of_files, desc='RGB images '+mission,total=len(list_of_files)):
            fname_json = os.path.join(os.path.dirname(file),'info.json')
            if os.path.exists(fname_json):
                with open(fname_json,'r') as f_json:
                    flight_info = json.load(f_json)
            else:
                flight_info = get_flight_info(fname_json)

            model = flight_info['model'].replace('DJI','').replace(' ','')
            year = mission.split('_')[2][0:4]
            month = mission.split('_')[2][4:6]
            collection_name = model+'_FlightHeight'+str(int(flight_info['flight_height_m']))+'m'
            exif_info = get_exif_info(file)
            if  exif_info:
                #Get UTC from location:
                date, time = get_local_utc(exif_info)

                raster_name = '_'.join(mission.split('_')[0:2])+'_'+date.replace('-','') +'T'+ time.replace(':','')+'_RGB.tif'
                cog_file = os.path.join(os.path.join(os.path.join(os.path.join(catalog_path,collection_name),year),month),raster_name)
            
                if os.path.exists(cog_file) != True:
                    args = SimpleNamespace(drone_image=file, flight_height=flight_info['flight_height_m'], sensor_width=flight_info['sensor_width_mm'], raster_output=cog_file)
                    bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,_ = drone_projection_warp(args)
                else:
                    bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,_ = get_raster_info(cog_file)
                
                name = model+'_'+str(int(flight_info['flight_height_m']))+'m'+'_'+'_'.join(mission.split('_')[0:2])+'_'+ date.replace('-','') + time.replace(':','')
                start = date+'T'+time
                dt_now = datetime.now().isoformat(timespec="seconds")
                collection_idx = model.lower()+'_flight_height'+str(int(flight_info['flight_height_m']))+'m'

                #Ground Sample Distance (cm) based on flying height above ground level, sensor width size (mm), focal lenght (mm), image width (pixels)
                GSD = (flight_info['flight_height_m']  * flight_info['sensor_width_mm']) / (exif_info['img_dim_x'] * exif_info['focal_lenght']) * 100.

                collections_template[collection_idx]['items'].append({"name": name,
                                                                    "start_date": start,
                                                                    "end_date": start,
                                                                    "cloud_cover": 0,
                                                                    "srid": 4326,
                                                                    "bbox": bbox_wgs84,
                                                                    "footprint": geom_wgs84,
                                                                    "metadata_": {
                                                                        "proj:epsg": srid,
                                                                        "proj:bbox": bbox,
                                                                        "proj:geometry": geom,
                                                                        "gsd":GSD/100.0,
                                                                        "platform": [flight_info['model']],
                                                                        "instruments": collections_template[collection_idx]['metadata']['platform']["instruments"],
                                                                        "gps_img_center_coords": exif_info['center_coords'],
                                                                        "altitude": exif_info['altitude'],
                                                                        "mission": mission
                                                                        },
                                                                    "assets": {
                                                                        "file": {
                                                                            "href":  os.path.join(prefix_geoserver_data, os.path.join('data',cog_file.partition("data")[2].lstrip('/').lstrip('\\'))),
                                                                            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                                                                            "roles": ["data" ],
                                                                            "created": dt_now,
                                                                            "updated": dt_now,
                                                                            "bdc:size": os.path.getsize(cog_file),
                                                                            "bdc:chunk_size": {'x': chunck_x, 'y': chunck_y},
                                                                            "bdc:raster_size": {'x':img_width, 'y': img_height},
                                                                            "checksum:multihash": ""
                                                                            },
                                                                        "thumbnail": {
                                                                            "href": os.path.join(prefix_geoserver_data, os.path.join('data',cog_file.partition("data")[2].lstrip('/').lstrip('\\').replace('.tif','.png'))),
                                                                            "type": "image/png",
                                                                            "roles": ["thumbnail"],
                                                                            "created": dt_now,
                                                                            "updated": dt_now,
                                                                            "bdc:size": os.path.getsize(cog_file.replace('.tif','.png')),
                                                                            "checksum:multihash": ""
                                                                            }
                                                                        }
                                                                        }) 

        # Processing RGB Mosaic:           
        list_of_files = [str(file) for file in list(Path(os.path.join(path,'Mosaic')).rglob('*.tif')) if '_MS' not in str(file) and '_T.tif' not in str(file)]
        list_of_files.sort()
        for file in tqdm(list_of_files, desc='RGB Mosaic '+mission,total=len(list_of_files)):
            fname_json = os.path.join(os.path.dirname(file),'info.json')
            if os.path.exists(fname_json):
                with open(fname_json,'r') as f_json:
                    flight_info = json.load(f_json)
            else:
                flight_info = get_flight_info(fname_json)

            model = flight_info['model'].replace('DJI','').replace(' ','')
            year = mission.split('_')[2][0:4]
            month = mission.split('_')[2][4:6]
            collection_name = model+'_FlightHeight'+str(int(flight_info['flight_height_m']))+'m'+'_Mosaic'
            date = os.path.basename(str(Path(os.path.dirname(file)).parent)).split('_')[1]
            
            name = model+'_'+str(int(flight_info['flight_height_m']))+'m'+'_Mosaic_'+'_'.join(mission.split('_')[0:2])+'_'+ date          
            collection_idx = model.lower()+'_flight_height'+str(int(flight_info['flight_height_m']))+'m_mosaic'
            start = date[0:4]+'-'+date[4:6]+'-'+date[6:8]+'T'+'00:00:00'
            bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,GSD = get_raster_info(file)
            dt_now = datetime.now().isoformat(timespec="seconds")           
            
            raster_name = '_'.join(mission.split('_')[0:2])+'_'+date+'_RGB.tif'
            tiff_file = os.path.join(os.path.join(os.path.join(os.path.join(catalog_path,collection_name),year),month),raster_name)
           
            if os.path.exists(tiff_file) != True:
                os.makedirs(os.path.dirname(tiff_file), exist_ok=True)
                print('Coverting mosaic GeoTIFF to COG file...')
                write_cogtiff_v2(file,tiff_file,type='RGB')
                print('The conversion to the COG file was finished!')

            #Create thumbnail
            f_out = tiff_file.replace('.tif','.png')
            if os.path.exists(f_out) != True:
                print('Creating thumbnail...')
                os.environ['GDAL_PAM_ENABLED']='NO' #avoid .xml file creation
                gdal.Translate(f_out, str(file), options="-of PNG -outsize 10% 10%")
                print('Finished thumbnail creation!')

            collections_template[collection_idx]['items'].append({"name": name,
                                                                  "start_date": start,
                                                                  "end_date": start,
                                                                  "cloud_cover": 0,
                                                                  "srid": 4326,
                                                                  "bbox": bbox_wgs84,
                                                                  "footprint": geom_wgs84,
                                                                  "metadata_": {
                                                                      "proj:epsg": srid,
                                                                      "proj:bbox": bbox,
                                                                      "proj:geometry": geom,
                                                                      "gsd":GSD,
                                                                      "platform": [flight_info['model']],
                                                                      "instruments": collections_template[collection_idx]['metadata']['platform']["instruments"],
                                                                      "mission": mission
                                                                      },
                                                                  "assets": {
                                                                      "file": {
                                                                          "href":  os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\'))),
                                                                          "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                                                                          "roles": ["data" ],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file),
                                                                          "bdc:chunk_size": {'x': chunck_x, 'y': chunck_y},
                                                                          "bdc:raster_size": {'x':img_width, 'y': img_height},
                                                                          "checksum:multihash": ""
                                                                          },
                                                                      "thumbnail": {
                                                                          "href": os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\').replace('.tif','.png'))),
                                                                          "type": "image/png",
                                                                          "roles": ["thumbnail"],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file.replace('.tif','.png')),
                                                                          "checksum:multihash": ""
                                                                          }
                                                                       }
                                                                      })
        
        # Processing Thermal Mosaic:
        list_of_files = list(Path(os.path.join(path,'Mosaic')).rglob('*_T.tif'))
        list_of_files.sort()
        for file in tqdm(list_of_files, desc='Thermal Mosaic '+mission,total=len(list_of_files)):
            fname_json = os.path.join(os.path.dirname(file),'info_t.json')
            if os.path.exists(fname_json):
                with open(fname_json,'r') as f_json:
                    flight_info = json.load(f_json)
            else:
                flight_info = get_flight_info(fname_json)

            model = flight_info['model'].replace('DJI','').replace(' ','')
            year = mission.split('_')[2][0:4]
            month = mission.split('_')[2][4:6]
            collection_name = model+'_FlightHeight'+str(int(flight_info['flight_height_m']))+'m'+'_Thermal_Mosaic'
            date = os.path.basename(str(Path(os.path.dirname(file)).parent)).split('_')[1]
            
            name = model+'_'+str(int(flight_info['flight_height_m']))+'m'+'_Thermal_Mosaic_'+'_'.join(mission.split('_')[0:2])+'_'+ date          
            collection_idx = model.lower()+'_flight_height'+str(int(flight_info['flight_height_m']))+'m_thermal_mosaic'
            start = date[0:4]+'-'+date[4:6]+'-'+date[6:8]+'T'+'00:00:00'
            bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,GSD = get_raster_info(file)
            dt_now = datetime.now().isoformat(timespec="seconds")           
            
            raster_name = '_'.join(mission.split('_')[0:2])+'_'+date+'_Thermal.tif'
            tiff_file = os.path.join(os.path.join(os.path.join(os.path.join(catalog_path,collection_name),year),month),raster_name)
           
            if os.path.exists(tiff_file) != True:
                os.makedirs(os.path.dirname(tiff_file), exist_ok=True)
                print('Coverting mosaic GeoTIFF to COG file...')
                write_cogtiff_v2(file,tiff_file,type='Thermal')
                print('The conversion to the COG file was finished!')

            #Create thumbnail
            f_out = tiff_file.replace('.tif','.png')
            if os.path.exists(f_out) != True:
                print('Creating thumbnail...')
                os.environ['GDAL_PAM_ENABLED']='NO' #avoid .xml file creation
                if "nodata" not in locals():
                    get_raster_nodata(str(file))
                
                tmp_file = tiff_file.replace('.tif','_scalled.tif')
                gdal.Translate(tmp_file, str(file), options="-a_nodata "+str(nodata)+" -ot Byte -outsize 10% 10%")
                create_png_from_raster(raster_tif=tmp_file, output_file=f_out, color_png_file=os.path.join(os.path.join(parent_path,'data','temperature-color.txt')))
                os.remove(tmp_file)
                print('Finished thumbnail creation!')

            collections_template[collection_idx]['items'].append({"name": name,
                                                                  "start_date": start,
                                                                  "end_date": start,
                                                                  "cloud_cover": 0,
                                                                  "srid": 4326,
                                                                  "bbox": bbox_wgs84,
                                                                  "footprint": geom_wgs84,
                                                                  "metadata_": {
                                                                      "proj:epsg": srid,
                                                                      "proj:bbox": bbox,
                                                                      "proj:geometry": geom,
                                                                      "gsd":GSD,
                                                                      "platform": [flight_info['model']],
                                                                      "instruments": collections_template[collection_idx]['metadata']['platform']["instruments"],
                                                                      "mission": mission
                                                                      },
                                                                  "assets": {
                                                                      "file": {
                                                                          "href":  os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\'))),
                                                                          "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                                                                          "roles": ["data" ],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file),
                                                                          "bdc:chunk_size": {'x': chunck_x, 'y': chunck_y},
                                                                          "bdc:raster_size": {'x':img_width, 'y': img_height},
                                                                          "checksum:multihash": ""
                                                                          },
                                                                      "thumbnail": {
                                                                          "href": os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\').replace('.tif','.png'))),
                                                                          "type": "image/png",
                                                                          "roles": ["thumbnail"],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file.replace('.tif','.png')),
                                                                          "checksum:multihash": ""
                                                                          }
                                                                       }
                                                                      })
            
        # Processing Multispectral Mosaic:
        list_of_files = list(Path(os.path.join(path,'Mosaic')).rglob('*_MS*.tif'))
        list_of_files.sort()
        for file in tqdm(list_of_files, desc='Multispectral Mosaic '+mission,total=len(list_of_files)):
            fname_json = os.path.join(os.path.dirname(file),'info_ms.json')
            if os.path.exists(fname_json):
                with open(fname_json,'r') as f_json:
                    flight_info = json.load(f_json)
            else:
                flight_info = get_flight_info(fname_json)

            model = flight_info['model'].replace('DJI','').replace(' ','')
            year = mission.split('_')[2][0:4]
            month = mission.split('_')[2][4:6]
            collection_name = model+'_FlightHeight'+str(int(flight_info['flight_height_m']))+'m'+'_MS_Mosaic'
            date = os.path.basename(str(Path(os.path.dirname(file)).parent)).split('_')[1]
            
            name = model+'_'+str(int(flight_info['flight_height_m']))+'m'+'_MS_Mosaic_'+'_'.join(mission.split('_')[0:2])+'_'+ date          
            collection_idx = model.lower()+'_flight_height'+str(int(flight_info['flight_height_m']))+'m_multispectral_mosaic'
            start = date[0:4]+'-'+date[4:6]+'-'+date[6:8]+'T'+'00:00:00'
            bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,GSD = get_raster_info(file)
            dt_now = datetime.now().isoformat(timespec="seconds")           
            
            raster_name = '_'.join(mission.split('_')[0:2])+'_'+date+'_MS.tif'
            tiff_file = os.path.join(os.path.join(os.path.join(os.path.join(catalog_path,collection_name),year),month),raster_name)
           
            if os.path.exists(tiff_file) != True:
                os.makedirs(os.path.dirname(tiff_file), exist_ok=True)
                print('Coverting mosaic GeoTIFF to COG file...')
                write_cogtiff_v2(file,tiff_file,type='MS')
                print('The conversion to the COG file was finished!')

            #Create thumbnail
            f_out = tiff_file.replace('.tif','.png')
            if os.path.exists(f_out) != True:
                print('Creating thumbnail...')
                os.environ['GDAL_PAM_ENABLED']='NO' #avoid .xml file creation             
                tmp_file = tiff_file.replace('.tif','_scalled.tif')                
                gdal.Translate(tmp_file, str(tiff_file), options="-ot Float32 -outsize 10% 10%")
                prepare_thumbnail_v4(f_out, tmp_file, bands_composition)
                os.remove(tmp_file)
                print('Finished thumbnail creation!')



            collections_template[collection_idx]['items'].append({"name": name,
                                                                  "start_date": start,
                                                                  "end_date": start,
                                                                  "cloud_cover": 0,
                                                                  "srid": 4326,
                                                                  "bbox": bbox_wgs84,
                                                                  "footprint": geom_wgs84,
                                                                  "metadata_": {
                                                                      "proj:epsg": srid,
                                                                      "proj:bbox": bbox,
                                                                      "proj:geometry": geom,
                                                                      "gsd":GSD,
                                                                      "platform": [flight_info['model']],
                                                                      "instruments": collections_template[collection_idx]['metadata']['platform']["instruments"],
                                                                      "mission": mission
                                                                      },
                                                                  "assets": {
                                                                      "file": {
                                                                          "href":  os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\'))),
                                                                          "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                                                                          "roles": ["data" ],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file),
                                                                          "bdc:chunk_size": {'x': chunck_x, 'y': chunck_y},
                                                                          "bdc:raster_size": {'x':img_width, 'y': img_height},
                                                                          "checksum:multihash": ""
                                                                          },
                                                                      "thumbnail": {
                                                                          "href": os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\').replace('.tif','.png'))),
                                                                          "type": "image/png",
                                                                          "roles": ["thumbnail"],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file.replace('.tif','.png')),
                                                                          "checksum:multihash": ""
                                                                          }
                                                                       }
                                                                      })
            
        # Processing Multispectral Mosaic to obtain NDVI:
        list_of_files = list(Path(os.path.join(path,'Mosaic')).rglob('*_MS*.tif'))
        list_of_files.sort()
        for file in tqdm(list_of_files, desc='Multispectral Mosaic to obtain NDVI '+mission,total=len(list_of_files)):
            fname_json = os.path.join(os.path.dirname(file),'info_ms.json')
            if os.path.exists(fname_json):
                with open(fname_json,'r') as f_json:
                    flight_info = json.load(f_json)
            else:
                flight_info = get_flight_info(fname_json)

            model = flight_info['model'].replace('DJI','').replace(' ','')
            year = mission.split('_')[2][0:4]
            month = mission.split('_')[2][4:6]
            collection_name = model+'_FlightHeight'+str(int(flight_info['flight_height_m']))+'m'+'_NDVI_Mosaic'
            date = os.path.basename(str(Path(os.path.dirname(file)).parent)).split('_')[1]
            
            name = model+'_'+str(int(flight_info['flight_height_m']))+'m'+'_NDVI_Mosaic_'+'_'.join(mission.split('_')[0:2])+'_'+ date          
            collection_idx = model.lower()+'_flight_height'+str(int(flight_info['flight_height_m']))+'m_ndvi_mosaic'
            start = date[0:4]+'-'+date[4:6]+'-'+date[6:8]+'T'+'00:00:00'
            bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,GSD = get_raster_info(file)
            dt_now = datetime.now().isoformat(timespec="seconds")           
            
            raster_name = '_'.join(mission.split('_')[0:2])+'_'+date+'_NDVI.tif'
            tiff_file = os.path.join(os.path.join(os.path.join(os.path.join(catalog_path,collection_name),year),month),raster_name)
           
            if os.path.exists(tiff_file) != True:
                os.makedirs(os.path.dirname(tiff_file), exist_ok=True)
                print('Calculating NDVI from multispectral mosaic...')
                calc_ndvi(tiff_file,file)
                print('The NDVI created!')

            #Create thumbnail
            f_out = tiff_file.replace('.tif','.png')
            if os.path.exists(f_out) != True:
                print('Creating thumbnail...')
                os.environ['GDAL_PAM_ENABLED']='NO' #avoid .xml file creation             
                tmp_file = tiff_file.replace('.tif','_scalled.tif')                
                gdal.Translate(tmp_file, str(tiff_file), options="-ot Float32 -outsize 10% 10%")
                create_png_from_raster(raster_tif=tmp_file, output_file=f_out, color_png_file=os.path.join(os.path.join(parent_path,'data','ndvi-color.txt')))
                os.remove(tmp_file)
                print('Finished thumbnail creation!')


            collections_template[collection_idx]['items'].append({"name": name,
                                                                  "start_date": start,
                                                                  "end_date": start,
                                                                  "cloud_cover": 0,
                                                                  "srid": 4326,
                                                                  "bbox": bbox_wgs84,
                                                                  "footprint": geom_wgs84,
                                                                  "metadata_": {
                                                                      "proj:epsg": srid,
                                                                      "proj:bbox": bbox,
                                                                      "proj:geometry": geom,
                                                                      "gsd":GSD,
                                                                      "platform": [flight_info['model']],
                                                                      "instruments": collections_template[collection_idx]['metadata']['platform']["instruments"],
                                                                      "mission": mission
                                                                      },
                                                                  "assets": {
                                                                      "file": {
                                                                          "href":  os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\'))),
                                                                          "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                                                                          "roles": ["data" ],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file),
                                                                          "bdc:chunk_size": {'x': chunck_x, 'y': chunck_y},
                                                                          "bdc:raster_size": {'x':img_width, 'y': img_height},
                                                                          "checksum:multihash": ""
                                                                          },
                                                                      "thumbnail": {
                                                                          "href": os.path.join(prefix_geoserver_data, os.path.join('data',tiff_file.partition("data")[2].lstrip('/').lstrip('\\').replace('.tif','.png'))),
                                                                          "type": "image/png",
                                                                          "roles": ["thumbnail"],
                                                                          "created": dt_now,
                                                                          "updated": dt_now,
                                                                          "bdc:size": os.path.getsize(tiff_file.replace('.tif','.png')),
                                                                          "checksum:multihash": ""
                                                                          }
                                                                       }
                                                                      })
                    
        # Processing Multispectral data:        
        template_view = ['R','NIR','G']
        list_of_files = list(Path(os.path.join(path,'NADIR_Images')).rglob('*MS_RE.TIF'))
        list_of_files.sort()
        for file in tqdm(list_of_files, desc='Multispectral images '+mission,total=len(list_of_files)):
            fname_json = os.path.join(os.path.dirname(file),'info_ms.json')
            if os.path.exists(fname_json):
                with open(fname_json,'r') as f_json:
                    flight_info = json.load(f_json)
            else:
                flight_info = get_flight_info(fname_json)

            
            model = flight_info['model'].replace('DJI','').replace(' ','')
            year = mission.split('_')[2][0:4]
            month = mission.split('_')[2][4:6]
            collection_name = model+'_FlightHeight'+str(int(flight_info['flight_height_m']))+'m_MS'
            _,tiff_tags_info = get_tags_info(file)
            
            if  tiff_tags_info:
                #Get UTC from location:
                date, time = get_local_utc(tiff_tags_info)

                template_band = os.path.splitext(file)[0].split('_')[-1]
                raster_name = '_'.join(mission.split('_')[0:2])+'_'+date.replace('-','') +'T'+ time.replace(':','')+'_MS_'+template_band+'.tif'
                cog_file = os.path.join(os.path.join(os.path.join(os.path.join(catalog_path,collection_name),year),month),raster_name)
                thumbnail_file = '_'.join(os.path.splitext(cog_file)[0].split('_')[:-1])+'.png'
            
                if os.path.exists(cog_file) != True or os.path.exists(thumbnail_file) != True :
                    args = SimpleNamespace(drone_image=file, flight_height=flight_info['flight_height_m'], \
                                           sensor_width=flight_info['sensor_width_mm'], raster_output=cog_file, view=template_view)
                    try:
                        bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,_ = drone_correction_projection_warp(args)
                    except Exception as e:
                        print(e)
                        print('Using Green as the template band instead of Red Edge...')
                        prefix = '_'.join(os.path.splitext(file)[0].split('_')[:-1])
                        sufix = os.path.splitext(file)[1]
                        file = prefix + '_G'+ sufix
                        raster_name = '_'.join(mission.split('_')[0:2])+'_'+date.replace('-','') +'T'+ time.replace(':','')+'_MS_G.tif'
                        cog_file = os.path.join(os.path.join(os.path.join(os.path.join(catalog_path,collection_name),year),month),raster_name)
                        args = SimpleNamespace(drone_image=file, flight_height=flight_info['flight_height_m'], \
                                               sensor_width=flight_info['sensor_width_mm'], raster_output=cog_file, view=template_view)
                        try:
                            bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,_ = drone_correction_projection_warp(args)
                        except Exception as e:
                            print(e)
                            continue
                        continue
                else:
                    bbox,geom,bbox_wgs84,geom_wgs84,srid,chunck_x,chunck_y,img_height,img_width,_ = get_raster_info(cog_file)
                
                name = model+'_'+str(int(flight_info['flight_height_m']))+'m'+'_MS_'+'_'.join(mission.split('_')[0:2]) \
                       +'_'+ date.replace('-','') + time.replace(':','')
                start = date+'T'+time
                dt_now = datetime.now().isoformat(timespec="seconds")
                collection_idx = model.lower()+'_flight_height'+str(int(flight_info['flight_height_m']))+'m_multispectral'
                collections_template[collection_idx]['properties']['bdc:visual']['rgb'] = [bands_name[band]  for band in template_view]

                #Ground Sample Distance (cm) based on flying height above ground level, sensor width size (mm), focal lenght (mm), image width (pixels)
                GSD = (flight_info['flight_height_m']  * flight_info['sensor_width_mm']) / (tiff_tags_info['img_dim_x'] * tiff_tags_info['focal_lenght']) * 100.

                # Include assets:
                asset_template = '{"'+bands_name[template_band]+'" : { \
                           "href" :  "'+os.path.join(prefix_geoserver_data, os.path.join('data',cog_file.partition("data")[2].lstrip('/').lstrip('\\')))+'",' + \
                           '"type" : "image/tiff; application=geotiff; profile=cloud-optimized",'+ \
                           '"roles" : ["data"],'+ \
                           '"created" : "'+ str(dt_now) +'",' + \
                           '"updated" : "'+ str(dt_now) +'",' + \
                           '"bdc:size" : {}'.format(os.path.getsize(cog_file)) +',' \
                           '"bdc:chunk_size" : { "x" : ' + str(chunck_x) +', "y" : '+str(chunck_y) +'},' + \
                           '"bdc:raster_size" : { "x" : '+ str(img_width) +', "y" : '+ str(img_height)+'},' + \
                           '"checksum:multihash" : ""},'
                
                prefix = '_'.join(os.path.basename(os.path.splitext(cog_file)[0]).split('_')[:-1])
                files_other_bands = [str(file_other_band) for file_other_band in Path(os.path.dirname(cog_file)).rglob(prefix+'*.tif')]
                files_other_bands.remove(cog_file)
                files_other_bands.sort()
                other_assets = ''
                for file_other_bands in files_other_bands:
                        other_band = os.path.splitext(file_other_bands)[0].split('_')[-1]
                        other_assets = other_assets + '"'+bands_name[other_band]+'" : { \
                           "href" :  "'+os.path.join(prefix_geoserver_data, os.path.join('data',file_other_bands.partition("data")[2].lstrip('/').lstrip('\\')))+'",' + \
                           '"type" : "image/tiff; application=geotiff; profile=cloud-optimized",'+ \
                           '"roles" : ["data"],'+ \
                           '"created" : "'+ str(dt_now) +'",' + \
                           '"updated" : "'+ str(dt_now) +'",' + \
                           '"bdc:size" : {}'.format(os.path.getsize(file_other_bands)) +',' \
                           '"bdc:chunk_size" : { "x" : ' + str(chunck_x) +', "y" : '+str(chunck_y) +'},' + \
                           '"bdc:raster_size" : { "x" : '+ str(img_width) +', "y" : '+ str(img_height)+'},' + \
                           '"checksum:multihash" : ""},'

                prefix = '_'.join(os.path.splitext(cog_file)[0].split('_')[:-1])
                href_png = os.path.join(prefix_geoserver_data, os.path.join('data',prefix.partition("data")[2].lstrip('/').lstrip('\\')+'.png'))       
                thumbnail = '"thumbnail" : {' + \
                            '"href" : "'+href_png+'",' + \
                            '"type" : "image/png",' + \
                            '"roles" : ["thumbnail"],' + \
                            '"created" : "'+str(dt_now)+'",' + \
                            '"updated" : "'+str(dt_now)+'",' + \
                            '"bdc:size" : {}'.format(os.path.getsize(prefix+'.png'))+',' \
                            '"checksum:multihash" : ""}'
                        
                assets = json.loads(asset_template + other_assets + thumbnail + '}')

                collections_template[collection_idx]['items'].append({"name": name,
                                                                    "start_date": start,
                                                                    "end_date": start,
                                                                    "cloud_cover": 0,
                                                                    "srid": 4326,
                                                                    "bbox": bbox_wgs84,
                                                                    "footprint": geom_wgs84,
                                                                    "metadata_": {
                                                                        "proj:epsg": srid,
                                                                        "proj:bbox": bbox,
                                                                        "proj:geometry": geom,
                                                                        "gsd":GSD/100.0,
                                                                        "platform": [flight_info['model']],
                                                                        "instruments": collections_template[collection_idx]['metadata']['platform']["instruments"],
                                                                        "gps_img_center_coords": tiff_tags_info['center_coords'],
                                                                        "altitude": tiff_tags_info['altitude'],
                                                                        "mission": mission
                                                                        },
                                                                    "assets": assets
                                                                        })     
       
    # Store JSON files to created catalogs of collections:
    for key,value in collections_template.items():
         if len(collections_template[key]['items']) > 0:
            path_output = os.path.join(local_path,'output')
            os.makedirs(path_output, exist_ok=True)
            fname_drone_collection = os.path.join(path_output,key + '_collection.json')
            with open(fname_drone_collection, 'w') as outfile:
                json.dump(collections_template[key], outfile, indent=4)

            if publish == 'True':
                args = SimpleNamespace(data_path_input=catalog_path, json_catalog_file=fname_drone_collection)
                publish_drone_data(args)
            else:
                print('\nJSON file for collection creation saved:\n',fname_drone_collection) 


def main(argv):
    """
    Read JSON files with template information for processing drone data to produce COGs files to publish using Geoserver/Titiler and JSON files used for STAC catalog creation. 

       :param argv.server_type: parameter that defines if data will be published using the services (STAC, Geoserver, and Titiler) running with 
                                Docker on localhost or a remote server. Because for a remote server, it will be necessary to supply additional 
                                information at runtime for remote connection to upload files and connection with Geoserver.
       :type argv.server_type: String

       :param argv.root_path: root path filename with drone data to processing (NADIR or Mosaic) of RGB, multispectral, or thermal rasters. 
                              Attention: it's required to follow the EODCtHRS protocol defined for drone data organization!  Please see the document 
                              available at <https://docs.google.com/document/d/1pZ_yBBRXJBnyq6wTk4bMXDYmdHe-aP1BHejxg4-wc4U/edit?usp=sharing> for further information.
       :type argv.root_path: String

       :param argv.data_path_output: path filename to output files processed (COGs and thumbnails).
       :type argv.data_path_output: String
    """ 
    
    class CustomArgumentParser(ArgumentParser):
        def error(self, message):
            sys.stderr.write(f'Error: {message}\n\n')
            self.print_help(sys.stderr)  # Print help to stderr
            sys.exit(2)  # Exit with a non-zero status code

    # Add custom program name with parameters from click and disable default help:
    parser = CustomArgumentParser(prog=' '.join(argv),
                             description='Convert raw images and mosaics to Cloud Optimized GeoTIFF (COG) and create JSON files to build \
                             catalogs using SpatioTemporal Asset Catalog (STAC) specification',
                             add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    # Add back help
    optional.add_argument('-h',action='help',default=SUPPRESS,help='show this help message and exit')
    required.add_argument('--server_type',
                    help='Required server target type localhost or remote',
                        choices=('localhost', 'remote'), required=True)
    required.add_argument('--root_path', type=lambda x: is_valid_directory(parser, x), 
                        required=True, help='Required path to raw and mosaic images from drone. Example /home/user/Desktop/HARMONIZE-Br_Project/src/FieldWorkCampaigns')
    required.add_argument('--data_path_output', type=lambda x: is_valid_directory(parser, x),
                        required=True, help='Required path to save Cloud Optimized GeoTIFF (COG) files. Example /home/user/Docker-Compose/geoserver/data')
    required.add_argument('--publish_data', help='Required parameter to specify a supplementary processing step for automatically publishing data via the BDC STAC service and Geoserver. Note: Additional parameters will be requested after data processing.',
     choices=('True', 'False'), required=True)
    #optional.add_argument('--optional_arg')

    # Check required parameters:
    argv, unknown = parser.parse_known_args()
    
    # option = None
    # if argv.publish_data == 'True':
    #     while(option != 'new' or option != 'update'):
    #         option = input('Please type the required option new (to create) or update (to add new items) to a collection(s)')

    templates = {}
    # Reading templates information about collections of drones: 
    for fname_rpa_template in Path(os.path.join(parent_path,'data')).rglob('*_template.json'):
        with open(fname_rpa_template, 'r') as f:
            templates[os.path.basename(fname_rpa_template).replace('_template.json','')] = json.load(f)

    prefix_geoserver_data = ''
    if argv.server_type == 'remote':
        prefix_geoserver_data = 'harmonize'
        print('\n')
        print('-'*80)
        wms_url = input('Please, enter the URL for the Geoserver application at the remote server.\nExample, https://geolab.inpe.br/bdc/harmonize/geoserver:\n--> ').strip()
        print('\n')
        stac_url = input('Please, enter the URL for the STAC service at the remote server.\nExample, https://geolab.inpe.br/bdc/harmonize/stac/v1:\n--> ').strip()
        
        for collection in templates:
            if templates[collection]['metadata'].get('wms'):
                templates[collection]['metadata']['wms']['url'] = templates[collection]['metadata']['wms']['url'].replace('http://localhost:10190/geoserver', wms_url)
            templates[collection]['metadata']['sources'][0]['stacUri'] = templates[collection]['metadata']['sources'][0]['stacUri'].replace('http://localhost:8080',stac_url)
           
    # List flights for all Fieldwork Campaigns:
    file_list =  set([str(path.parent.parent) for path in Path(argv.root_path).rglob('*') if path.suffix in {".JPG", ".TIF",".tif"}])
    file_list = list(filter(lambda x: 'Nocturnal' not in x, file_list))

    #Processing Drone images to create Cloud Optimized GeoTIFFs (COG) and JSON file to BDC-Catalog load-data tool:
    process_flights(file_list,templates,argv.data_path_output,prefix_geoserver_data, argv.publish_data)



if __name__ == "__main__":

    from drone_projection_warp import main as drone_projection_warp
    from drone_correction_projection_warp import main as drone_correction_projection_warp

    # Process the arguments
    import arghelper

    # Disable default help
    parser = ArgumentParser(description='Convert raw images and mosaics to Cloud Optimized GeoTIFF (COG) and create JSON files to build \
                             catalogs using SpatioTemporal Asset Catalog (STAC) specification',
                            add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    # Add back help
    optional.add_argument('-h','--help',action='help',default=SUPPRESS,help='show this help message and exit')
    required.add_argument('--server_type',
                       help='Required server target type localhost or remote',
                        choices=('localhost', 'remote'), required=True)
    required.add_argument('--root_path', type=lambda x: arghelper.is_valid_directory(parser, x), 
                        required=True, help='Required path to raw and mosaic images from drone. Example /home/user/Desktop/HARMONIZE-Br_Project/src/FieldWorkCampaigns')
    required.add_argument('--data_path_output', type=lambda x: arghelper.is_valid_directory(parser, x),
                        required=True, help='Required path to save Cloud Optimized GeoTIFF (COG) files. Example /home/user/Docker-Compose/geoserver/data')
    required.add_argument('--publish_data', help='Required parameter to specify a supplementary processing step for automatically publishing data via the BDC STAC service and Geoserver. Note: Additional parameters will be requested after data processing.',
     choices=('True', 'False'), required=True) 
    #optional.add_argument('--optional_arg')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    sys.exit(main(parser.parse_args()))
