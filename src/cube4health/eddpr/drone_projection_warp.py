
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

"""Utility for Drone images projection

   This approach is based on EXIF and XMP metadata tags information and auxiliaries information such as flight height and sensor dimension"""


# --------------------------
#        Imports
# --------------------------
import logging
import sys
import os
import subprocess
import json
from PIL import Image, ExifTags #required version >= 9.5
import geopandas as gpd
from osgeo import osr, gdal
from matplotlib import image
from numpy import array as np_array
from affine import Affine  # For easy manipulation of affine matrix
from geopy import distance, Point
from shapely.geometry import Point as shply_Point
from numpy import array
from pyproj import Transformer
import tempfile
from multiprocessing import cpu_count
from decimal import Decimal, InvalidOperation

result = subprocess.run(['gdal-config','--datadir'], capture_output=True, text=True)
os.environ['GDAL_DATA'] = result.stdout.replace('\n','') #set gdal data path
os.environ['PROJ_LIB'] = result.stdout.replace('\n','').replace('gdal','proj') #set proj path

gdal.UseExceptions()  # this allows GDAL to throw Python Exceptions
Image.MAX_IMAGE_PIXELS = None #to prevent the problem of size image
num_workers = int(cpu_count() - (cpu_count() * 0.20)) # using about 80% of cores


logging.basicConfig(filename='drone_projection_warp.log',\
                        format='%(asctime)s %(levelname)s:%(message)s', datefmt='%d/%m/%Y %I:%M:%S %p',\
                        level=logging.INFO, \
                        filemode = 'w')

# --------------------------
#        Functions
# --------------------------
def is_decimal(s):
    try:
        Decimal(s)
        return True
    except InvalidOperation:
        return False
    

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
# The device have 4 cameras (RGB) and Multispectral(G, Red, Red Edge and Near Infrared)
# Image size	5280x3956 (RGB)	2592x1944 (MS)
# Sensor size at X (TSX): 17.4mm (RGB) 5.2mm (MS)
# Sensor size at Y (TSY): 13mm (RGB) 3.9mm (MS)

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


def get_xmp_info(img_path):
    img = Image.open(img_path)
    xmp_info = img.getxmp()
    if xmp_info != None:
        try:
            flight_yaw_degree = xmp_info['xmpmeta']['RDF']['Description']['FlightYawDegree']            
        except KeyError:
            print('Flight Yaw Degree information not available!')       
    else:
        print('The image does not have XPM metadata information:\n'+img_path)
        return None
    return {'flight_yaw_degree':float(flight_yaw_degree)}


def create_cardinal_points(lat1, lon1, x_size, y_size, GSD, crs_src='EPSG:4326', crs_dst='EPSG:3395'):
    
    """This function create cardinal points coordinates based on center image coordinates,
       bering angle and distance. These points are used to determine upper-left corner coordinates
       of image and write Geotransform array in GDAL format and finally use Affine transformation
       to rotate and project drone images
       
       x_size - columns of image array
       y_size - rows of image array
       GSD - ground sample distance (cm)"""    
    
    #bearing (float) – Bearing in degrees: 0 – North, 90 – East, 180 – South, 270 or -90 – West.
    cardinal_bering = [0.,90.,180.,270.]
    d_meters = [(GSD * y_size/2.)/100.,(GSD * x_size/2.)/100.,(GSD * y_size/2.)/100.,(GSD * x_size/2.)/100.]

    origin = Point(lat1, lon1)
    drone_points = []
    for i,b in enumerate(cardinal_bering):
            # The geodesic distance is the shortest distance on the surface of an ellipsoidal model of the Earth.  
            # The default algorithm uses the method is given by 
            # `Karney (2013) <https://doi.org/10.1007%2Fs00190-012-0578-z>`_ (:class:`.geodesic`);
            # this is accurate to round-off and always converges.
            destination = distance.geodesic(meters=d_meters[i]).destination(origin, bearing=b)
            drone_points.append(shply_Point([destination.longitude,destination.latitude])) #x, y, z : float Easting, northing, and elevation)

    # Set up transformers, EPSG:3395 is metric
    gdf_cardinal_points = gpd.GeoDataFrame({'geometry':drone_points}, geometry='geometry', crs=crs_src)
    gdf_cardinal_points = gdf_cardinal_points.to_crs(crs_dst)
    
    return gdf_cardinal_points


# Some functions declaration for clarify the code
# Adapted from https://gis.stackexchange.com/a/408396

def raster_center(raster):
    """This function return the pixel coordinates of the raster center 
    """

    # We get the size (in pixels) of the raster
    # using gdal
    width, height = raster.RasterXSize, raster.RasterYSize

    # We calculate the middle of raster
    xmed = width / 2
    ymed = height / 2

    return (xmed, ymed)


def rotate_gt(affine_matrix, angle, pivot=None):
    """This function generate a rotated affine matrix
    """

    # The gdal affine matrix format is not the same
    # of the Affine format, so we use a bullit-in function
    # to change it
    # see : https://github.com/sgillies/affine/blob/master/affine/__init__.py#L178
    affine_src = Affine.from_gdal(*affine_matrix)
    # We made the rotation. For this we calculate a rotation matrix,
    # with the rotation method and we combine it with the original affine matrix
    # Be careful, the star operator (*) is surcharged by Affine package. He make
    # a matrix multiplication, not a basic multiplication
    affine_dst = affine_src * affine_src.rotation(angle, pivot)
    # We return the rotated matrix in gdal format
    return affine_dst.to_gdal()


def prepare_thumbnail_v2(filename_out,file_in,flight_yaw_degree):    
    """
    Creates thumbnail from raw images (JPG) of Drones

       :param filename_out: Filename output with mission and data identification.
       :type filename: String

       :param file_in: raw image (JPG).
       :type file_in: String

       :param flight_yaw_degree: angle in degrees related to North from North-East-Down (NED) coordinates, counterclockwise for negative or clockwise for positive values.
       :type arr: Float
    """
    
    if os.path.exists(filename_out) == False:
        input_image = Image.open(file_in).convert("RGBA")
        w,h = input_image.size    
        input_image.thumbnail((int(w*0.1),int(h*0.1))) #scale image keeping aspect ratio

        #rotate image
        rot = input_image.rotate((-1.0) * flight_yaw_degree, resample=Image.NEAREST, expand=True, fillcolor=(255,255,255))
        
        #change white background to transparent
        img = array(rot)
        img_final = img.copy()
        img_final[(img[...,0] == 255) & (img[...,1] == 255) & (img[...,2] == 255),3] = 0
        
        img = Image.fromarray(img_final)
        img.save(filename_out)


def get_geo_coordinates(GT,Xpixel,Yline):
    """Affine GeoTransform
       GDAL datasets have two ways of describing the relationship between raster positions (in pixel/line coordinates) and georeferenced coordinates. The first, and most
       commonly used is the affine transform (the other is GCPs). The affine transform consists of six coefficients returned by GetGeoTransform() which map pixel/line coordinates
       into georeferenced space using the following relationship.
       In case of north up images, the GT(2) and GT(4) coefficients are zero, and the GT(1) is pixel width, and GT(5) is pixel height. The (GT(0),GT(3)) position is the top left corner
       of the top left pixel of the raster. Note that the pixel/line coordinates in the above are from (0.0,0.0) at the top left corner of the top left pixel to 
       (width_in_pixels,height_in_pixels) at the bottom right corner of the bottom right pixel. The pixel/line location of the center of the top left pixel would therefore be (0.5,0.5)."""

    Xgeo = GT[0] + float(Xpixel)*GT[1] + float(Yline)*GT[2]
    Ygeo = GT[3] + float(Xpixel)*GT[4] + float(Yline)*GT[5]

    return {'Xgeo':Xgeo,'Ygeo':Ygeo}


def get_img_bounds(dst_img):
    """The affine transform consists of six coefficients returned by GetGeoTransform() which map pixel/line coordinates into georeferenced space."""
    
    GT = dst_img.GetGeoTransform()
    img_width = dst_img.GetRasterBand(1).XSize #width in pixels
    img_height = dst_img.GetRasterBand(1).YSize #height in pixels

    xmin = min(GT[0], get_geo_coordinates(GT,0.0,img_height)['Xgeo']) #top left/bottom left corners
    xmax = max(get_geo_coordinates(GT,img_width,0.0)['Xgeo'],get_geo_coordinates(GT,img_width,img_height)['Xgeo']) #top right/bottom right corners
    ymin = min(get_geo_coordinates(GT,0.0,img_height)['Ygeo'],get_geo_coordinates(GT,img_width,img_height)['Ygeo']) #bottom left/bottom right corners
    ymax = max(GT[3], get_geo_coordinates(GT,img_width,0.0)['Ygeo']) #top left/top right corners

    return xmin, ymin, xmax, ymax

def get_raster_info(dst_img,blocksize):
    xmin, ymin, xmax, ymax = get_img_bounds(dst_img)
    proj = osr.SpatialReference(wkt=dst_img.GetProjection())
    srid = int(proj.GetAttrValue('AUTHORITY',1)) #The coordinate reference system used by the asset data
    chunck_x = blocksize
    chunck_y = blocksize
    img_height = dst_img.GetRasterBand(1).YSize
    img_width = dst_img.GetRasterBand(1).XSize

    GT = dst_img.GetGeoTransform()
    pixel_sizex = GT[1]
    pixel_sizey = GT[5]

    # Convert coords to WGS84
    transformer = Transformer.from_crs('EPSG:'+str(srid), "EPSG:4326")
        
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


def main(argv):
    logging.info('Started')
    log = logging.getLogger()
       
    flight_info = {'flight_height_m':argv.flight_height,'sensor_width_mm':argv.sensor_width}
    fname_json = os.path.join(os.path.dirname(argv.drone_image),'info.json')
    if (argv.flight_height == None) or (argv.sensor_width == None):        
        if os.path.exists(fname_json):
            with open(fname_json,'r') as f_json:
                flight_info_tmp = json.load(f_json)
            for key,item in flight_info.items():
                if item != None:
                    flight_info_tmp[key] = item
            flight_info = flight_info_tmp
        else:
            print("\n\nWARNING: Flight height (meters) and sensor width (millimeters) parameters are required!\n" \
                  "Please, use command line inputs '--flight_height' and '--sensor_width'.\n" \
                    "For example:\n"\
                    "python drone_projection_warp.py --drone_image DJI_0775.JPG --flight_height 150 --sensor_width 6.41")           
            logging.warning("WARNING: Flight height (meters) and sensor width (millimeters) parameters are required!\n" \
                  "Please, use command line inputs '--flight_height' and '--sensor_width'.\n" \
                    "For example:\n"\
                    "python drone_projection_warp.py --drone_image DJI_0775.JPG --flight_height 150 --sensor_width 6.41")
            raise SystemExit
    elif os.path.exists(fname_json) == False:
         if is_decimal(flight_info['flight_height_m']) and is_decimal(flight_info['sensor_width_mm']):
                    
                    print('\n',flight_info)
                    print('Path to save auxiliary information file:\n',os.path.dirname(fname_json))
                    
                    ch = input("\nDo you want to save these auxiliary informations (flight height and sensor width) for all images in this folder? (y/n)")
                    if ch.lower() == 'y':
                          with open(fname_json, 'w') as outfile:
                               outfile.write(json.dumps(flight_info, indent=4))

    """EPSG:3395 - WGS 84/World Mercator is global coordinate system with unit in meters. Source: https://epsg.io/3395"""
    # Set up transformers, EPSG:3395 is metric
    crs_dst = 'EPSG:3395'

    exif_info = get_exif_info(argv.drone_image)
    xmp_info = get_xmp_info(argv.drone_image)
    if exif_info != None and xmp_info != None:    
        #Ground Sample Distance (cm) based on flying height above ground level, sensor width size (mm), focal lenght (mm), image width (pixels)
        GSD = (flight_info['flight_height_m']  * flight_info['sensor_width_mm']) / (exif_info['img_dim_x'] * exif_info['focal_lenght']) * 100.0
        
        # Get corner coordinates of image based on center coordinates, spatial resolution and dimensions of image:    
        gdf_cardinal_points = create_cardinal_points(exif_info['center_coords'][0], exif_info['center_coords'][1], 
                                                exif_info['img_dim_x'], exif_info['img_dim_y'], GSD,
                                                crs_src='EPSG:4326', #coordinate reference system of lat/lon
                                                crs_dst=crs_dst)
        
        os.makedirs(os.path.dirname(argv.raster_output), exist_ok=True)
        f_thumb_out = os.path.splitext(argv.raster_output)[0]+'.png'
                
        # Create a thumbnail:
        prepare_thumbnail_v2(f_thumb_out, argv.drone_image, xmp_info['flight_yaw_degree'])
        
        # Create a COG file projected using Global Mercator Coordinate System and Flight Yaw Angle:
        if os.path.exists(argv.raster_output) == False:
            block_size_output = 256 #Sets the tile width and height in pixels. Must be divisible by 16. https://gdal.org/drivers/raster/cog.html#general-creation-options
            arr = np_array(Image.open(argv.drone_image))
                        
            driver = gdal.GetDriverByName('MEM') #To avoid error of overview creation
           
            dst_filename = argv.raster_output

            dst_ds = driver.Create('', xsize=arr.shape[1], ysize=arr.shape[0],
                                bands=3, eType=gdal.GDT_Byte)

            ul_x,_,_,ul_y = gdf_cardinal_points.total_bounds
            p_size_meters = GSD / 100.

            #In case of north up images, the GT(2) and GT(4) coefficients are zero,
            #and the GT(1) is pixel width, and GT(5) is pixel height. 
            #The (GT(0),GT(3)) position is the top left corner of the top left pixel of the raster.

            dst_ds.SetGeoTransform([ul_x, p_size_meters, 0, ul_y, 0, -p_size_meters])

            srs = osr.SpatialReference()
            srs.ImportFromEPSG(int(crs_dst.split(':')[1]))
            dst_ds.SetProjection(srs.ExportToWkt())
            band_names = ['Red','Green','Blue']

            for band_nr in range(len(band_names)):
                band = dst_ds.GetRasterBand(band_nr+1)
                band.WriteArray(arr[...,band_nr])
                band.SetDescription(band_names[band_nr]) # This sets the band name!
                band.SetNoDataValue(0)
                if len(band_names) == 3:
                    band.SetColorInterpretation(band_nr + 3)
                    band.FlushCache()
                    del band
            
            # Now we can rotate the raster
            # Adapted from https://gis.stackexchange.com/a/408396

            # First step, we get the affine tranformation matrix of the initial fine
            # More info here : https://gdal.org/tutorials/geotransforms_tut.html#geotransforms-tut
            gt_affine = dst_ds.GetGeoTransform()

            # Second we get the center of the raster to set the rotation center
            # Be carefull, the center is in pixel number, not in projected coordinates
            # More info on the  "raster_center" comment's
            center = raster_center(dst_ds)

            # Third we rotate the destination raster, datase_dst, with setting a new
            # affine matrix made by the "rotate_gt" function.
            # gt_affine is the initial affine matrix. Array is 'North up' reference, but image
            # is rotaded using Flight Yaw degree  basead on the center of raster
            dst_ds.SetGeoTransform(rotate_gt(gt_affine, xmp_info['flight_yaw_degree'], center))

            # Create temporary file
            fd, path = tempfile.mkstemp()
            os.close(fd)
            
            driver = gdal.GetDriverByName('GTiff')
            data_set2 = driver.CreateCopy(path, dst_ds)
            
            # Once we're done, close properly the dataset
            dst_ds.FlushCache()            
            del dst_ds
            data_set2.FlushCache()
            del data_set2

            # Create GeoTIFF with North Up reference:
            #https://gdal.org/drivers/raster/cog.html#raster-cog
            #https://erouault.blogspot.com/2014/10/warping-overviews-and-warped-overviews.html
            
            dst_output = gdal.Warp(dst_filename, path, 
                        options="-overwrite -multi -wm 80%  -of COG -r AVERAGE -oo OVERVIEW_LEVEL=5 -co BLOCKSIZE={}" \
                            " -co COMPRESS=DEFLATE -wo OPTIMIZE_SIZE=TRUE -co NUM_THREADS={}".format(str(block_size_output),str(num_workers)))
            os.remove(path) #remove temporary file
            raster_info = get_raster_info(dst_output,block_size_output)
                

            logging.info('Projected file saved as:\n'+dst_filename)        
            if __name__ == "__main__":
                print('Projected file saved as:\n',dst_filename)
    
    logging.info('Finished')
    if __name__ != "__main__":
        return raster_info


if __name__ == "__main__":

    # Prompt user for (optional) command line arguments, when run from IDLE:
    if 'idlelib' in sys.modules: sys.argv.extend(input("Args: ").split())

    # Process the arguments
    from argparse import ArgumentParser, SUPPRESS
    import arghelper

    # Disable default help
    parser = ArgumentParser(description='Creates a COG file from a Drone image, using EXIF and XMP tags metadata from raw images and auxiliaries \
              information such as flight height and sensor parameters (width and focal distance). \
                Generally, these parameters are defined in the auxiliary file info.json present in the path of the scenes.',
                            add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    # Add back help
    optional.add_argument('-h','--help',action='help',default=SUPPRESS,help='show this help message and exit')   
    required.add_argument('--drone_image', type=lambda x: arghelper.is_valid_file(parser, x),
                          help='Required path to Raw Drone image in JPEG format',
                          metavar='path_to_file', required=True)
    required.add_argument('--raster_output', type=lambda x: arghelper.is_valid_namefile(parser, x), help='Required COG filename output (including path).', required=True)
       
    optional.add_argument('--flight_height',
                       help='Flight height in meters, this information is important to define the spatial resolution of the image (Ground Sample Distance - GSD).',
                       metavar='120', type=int, required=False) 
    optional.add_argument('--sensor_width',
                       help='Camera sensor width size (TSX) in millimeters. For example 6.48 (DJI Phantom 3 Advanced)',
                        metavar='6.48', type=float, required=False)    
   
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    sys.exit(main(parser.parse_args()))


