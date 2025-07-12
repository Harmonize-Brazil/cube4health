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

"""Utility for correction, alignment and projection of multispectral drone images

   This approach is based on TiFF and XPM metadata tags information and auxiliaries information such as flight height and sensor dimension"""


# --------------------------
#        Imports
# --------------------------
import logging
import sys
import os
import subprocess
import json
from PIL import Image, TiffTags #required version >= 9.5
from pathlib import Path
import geopandas as gpd
from osgeo import osr, gdal
from affine import Affine  # For easy manipulation of affine matrix
from geopy import distance, Point
from shapely.geometry import Point as shply_Point
import numpy as np
from decimal import Decimal, InvalidOperation
from pyproj import Transformer
import cv2
from time import perf_counter as pc
from multiprocessing import Pool, cpu_count
import shutil
from itertools import repeat
import tempfile
from .drone_projection_warp import get_exif_info


""" Settings """
# Define termination criteria for the image registration algorithm, empirically determined:
number_of_iterations = 100
termination_eps = 1e-6

local_path = os.path.dirname(os.path.abspath(__file__))
gdal.UseExceptions()  # this allows GDAL to throw Python Exceptions
Image.MAX_IMAGE_PIXELS = None #to prevent the problem of size image
num_workers = int(cpu_count() - (cpu_count() * 0.20)) # using about 80% of cores

bands_definition = {'NIR':'Near Infrared', 'RE':'Red Edge', 'R':'Red','G':'Green','NDVI':'Normalized Difference Vegetation Index'}
bands_nodata = {'NIR':0, 'RE':0, 'R':0,'G':0,'NDVI':-9999}
bands_gdal_type = {'NIR':gdal.GDT_UInt32, 'RE':gdal.GDT_UInt32, 'R':gdal.GDT_UInt32,'G':gdal.GDT_UInt32,'NDVI':gdal.GDT_Int16}

# GDAL colour interpretation values - source https://gdal.org/java/org/gdal/gdalconst/gdalconstConstants.html:
# GCI_BlueBand(5) : Blue band of RGBA image (color interpretation) GCI_GrayIndex(1) : greyscale (color interpretation)
# GCI_GreenBand(4) : Green band of RGBA image (color interpretation) GCI_RedBand(3) : Red band of RGBA image (color interpretation)
# GCI_Undefined(0) : undefined (color interpretation)
bands_colour_interpretation = {'NIR':1, 'RE':1, 'R':3,'G':4,'NDVI':1}
bands_colour_definition = {1:'Gray', 3:'Red', 4:'Green'}
default_scale = 10000  

logging.basicConfig(filename=os.path.join(local_path,'drone_correction_projection_warp.log'),\
                        format='%(asctime)s %(levelname)s:%(message)s', datefmt='%d/%m/%Y %I:%M:%S %p',\
                        level=logging.INFO, \
                        filemode = 'w')

# --------------------------
#        Functions
# --------------------------
# Adapted from https://www.pyimagesearch.com/2015/04/06/zero-parameter-automatic-canny-edge-detection-with-python-and-opencv/
def auto_canny(image, sigma=0.33):
    # Normalize image to between 0 and 255
    image *= (255.0/image.max())
    image = np.round(image).astype('uint8')
    
    # compute the median of the single channel pixel intensities
    v = np.ma.median(image)

    # apply automatic Canny edge detection using the computed median
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))

    edged = cv2.Canny(image, lower, upper)

    # return the edged image
    return edged


def image_histogram_equalization(image, number_bins=256):
    """It is a method that improves the contrast in an image, in order to stretch out the intensity range
       Source: https://docs.opencv.org/3.4/d4/d1b/tutorial_histogram_equalization.html"""
    # from http://www.janeriksolem.net/histogram-equalization-with-python-and.html

    # get image histogram
    image_histogram, bins = np.histogram(image.flatten(), number_bins, density=True)
    cdf = image_histogram.cumsum() # cumulative distribution function
    cdf = (number_bins-1) * cdf / cdf[-1] # normalize

    # use linear interpolation of cdf to find new pixel values
    image_equalized = np.interp(image.flatten(), bins[:-1], cdf)

    return image_equalized.reshape(image.shape) 


def find_warp_matrix_by_downscale_pyramids(img1,img2,warp_mode,criteria):
    """Speed up the computation of the homography matrix by iteratively computing it on scaled down images. 
     Number of scaling levels (pyramid size), empirically determined to maximimize speed"""

    image1_float = np.float32(img1)
    image2_float = np.float32(img2)
    pixels_count = image1_float.size
    sz = image1_float.shape
    warp_matrix = np.eye(3, 3, dtype=np.float32)
    
    print('Using downscale pyramids...')    
    n_level = 4 
    for level in range(n_level):
        scale = 1/2**(n_level-1-level)
        rszImg1 = cv2.resize(image1_float, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        rszImg2 = cv2.resize(image2_float, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        try:
            # Run the ECC algorithm. The results are stored in warp_matrix.
            cc, warp_matrix = cv2.findTransformECC(rszImg1, rszImg2, warp_matrix, warp_mode, criteria, inputMask=None)
        except cv2.error as error:
            if getattr(error, 'code', False) != False and getattr(error, 'code') == -7 and level == n_level-1: #Iterations do not converge/finished pyramid levels                    
                try:
                    print('Try using the full-resolution image...')
                    warp_matrix = warp_matrix = np.eye(3, 3, dtype=np.float32)
                    cc, warp_matrix = cv2.findTransformECC(image1_float, image2_float, warp_matrix, warp_mode, criteria, inputMask=None)
                except cv2.error as error:
                    if getattr(error, 'code', False) != False and getattr(error, 'code') == -7: #Iterations do not converge with full-resolution image
                        return None,None,None,error
                else:
                    # Align the final image using the homography matrix
                    image2_aligned = cv2.warpPerspective(img2, warp_matrix, (sz[1], sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
                    if (image2_aligned == 0.0).sum() < (pixels_count * 0.05): # the threshold for identification of misalignment  caused by wrong warp-matrix adjustment
                        return cc,image2_aligned,warp_matrix,True
                    else:
                        return None,None,None,None

        if level != n_level-1: # scale up for the next pyramid level
            warp_matrix = warp_matrix * np.array([[1., 1., 2.], [1., 1., 2.], [1./2., 1./2., 1.]], dtype=np.float32)

    # Align the final image using the homography matrix
    image2_aligned = cv2.warpPerspective(img2, warp_matrix, (sz[1], sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
    if (image2_aligned == 0.0).sum() < (pixels_count * 0.05): # the threshold for identification of misalignment  caused by wrong warp-matrix adjustment
        return cc,image2_aligned,warp_matrix,True
    else:
        return None,None,None,None   


def find_warp_matrix_by_histogram_equalization(img1,img2,warp_mode,criteria):
    """Apply histogram equalization to improve the contrast of the image adopting the cumulative distribution function (CDF) for intensities transformation. """

    pixels_count = img1.size
    sz = img1.shape
    warp_matrix = np.eye(3, 3, dtype=np.float32)
    img1_hist = image_histogram_equalization(np.float32(img1)).astype('float32')
    img2_hist = image_histogram_equalization(np.float32(img2)).astype('float32')

    print('Using the full-resolution image with histogram equalization...')   
    try:
        cc, warp_matrix = cv2.findTransformECC(img1_hist, img2_hist, warp_matrix, warp_mode, criteria, inputMask=None)
    except cv2.error as error:
        if getattr(error, 'code', False) != False and getattr(error, 'code') == -7: #Iterations do not converge with full-resolution image
            return None,None,None,error
    else:
        # Align the final image using the homography matrix
         image2_aligned = cv2.warpPerspective(img2, warp_matrix, (sz[1], sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
         if (image2_aligned == 0.0).sum() < (pixels_count * 0.05): # the threshold for identification of misalignment  caused by wrong warp-matrix adjustment
            return cc,image2_aligned,warp_matrix,True
         else:
            return None,None,None,None


def find_warp_matrix_by_edge_detection(img1,img2,warp_mode,criteria):
    """Apply Canny edge detection to avoid correlation problems due to different distributions of pixel values. """
    pixels_count = img1.size
    sz = img1.shape
    warp_matrix = np.eye(3, 3, dtype=np.float32)
    img1_edge = auto_canny(img1.copy().astype('float32'))
    img2_edge = auto_canny(img2.copy().astype('float32'))

    print('Using the full-resolution image with edge detection...')    
    try:
        cc, warp_matrix = cv2.findTransformECC(img1_edge, img2_edge, warp_matrix, warp_mode, criteria, inputMask=None)
    except cv2.error as error:
        if getattr(error, 'code', False) != False and getattr(error, 'code') == -7: #Iterations do not converge with full-resolution image
            return None,None,None,error
    else:
        # Align the final image using the homography matrix
         image2_aligned = cv2.warpPerspective(img2, warp_matrix, (sz[1], sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
         if (image2_aligned == 0.0).sum() < (pixels_count * 0.05): # the threshold for identification of misalignment  caused by wrong warp-matrix adjustment
            return cc,image2_aligned,warp_matrix,True
         else:
            return None,None,None,None


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

def get_tags_info(img_path):
    img = Image.open(img_path)
    xmp_info = img.getxmp()
    if xmp_info != None:
        tags_info = {TiffTags.TAGS[key] : img.tag[key] for key in img.tag_v2 if key in TiffTags.TAGS}

        try:
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
                     'center_coords':(float(lat),float(lon)),'flight_yaw_degree':float(xmp_info['xmpmeta']['RDF']['Description']['FlightYawDegree']),
                     'img_description':tags_info['ImageDescription'][0]}


def vignetting_correction(filename):

    """
    This function realizes a vignetting correction based on metadata information of images and steps described in the guide of image processing from DJI Mavic 3 M. 
    The fall-off pixel intensity from the center towards the edges of the image (vignetting) is prejudicial for image analysis, generally this effect 
    assume radial characteristics
    
    filename - path for image"""
    xmp_info,tiff_tags_info = get_tags_info(filename)
    
    # https://numpy.org/doc/stable/reference/generated/numpy.meshgrid.html
    # 1-D arrays representing the coordinates of a grid
    x = np.arange(tiff_tags_info['img_dim_x'])
    y = np.arange(tiff_tags_info['img_dim_y'])

    # list of coordinate matrices from coordinate vectors
    xv, yv = np.meshgrid(x, y, indexing='xy')

    # CenterX and CenterY are coordinates of center of the vignettee, which can be found from the items
    # [Calibrated Optical Center X] and [Calibrated Optical Center Y] in [XMP: drone-dji] in the metadata.
    CenterX = float(xmp_info['xmpmeta']['RDF']['Description']['CalibratedOpticalCenterX'])
    CenterY = float(xmp_info['xmpmeta']['RDF']['Description']['CalibratedOpticalCenterY'])

    # r is the distance between pixel (x, y) and the center of the vignette in pixels, which can be obtained by:
    r = np.sqrt((xv - CenterX)**2 + (yv - CenterY)**2) #(Eq. 8)

    # Matrix k shows the polynomial coefficients for vignetting correction, which can be found from
    # [Vignetting Data] in [XMP: drone-dji] in the metadata.
    k = [float(value) for value in xmp_info['xmpmeta']['RDF']['Description']['VignettingData'].split(',')]

    # input image:
    img = np.array(Image.open(filename))

    # We apply the vignetting correction model shown in Eq. 7 to the input image I(x,y):
    vig_correction_factor = (k[5] * r**6 + k[4] * r**5 + k[3] * r**4 + k[2] * r**3 + k[1] * r**2 + k[0] * r + 1.0)
    img_vig_corrected = img * vig_correction_factor #Eq. 7
    
    return img_vig_corrected


def save_with_metadata(array_img,ndtype,filename_src,filename_target,note=""):
    # Open source image    
    sourceimg = Image.open(filename_src)

    # Get the TIFF tags from the source image
    tiffinfo = sourceimg.tag_v2

     # Tag number 270 is the ImageDescription tag
    tiffinfo[270] = " ".join([tiffinfo[270].replace('default',''),note]).lstrip()

    # Save the target image with the correct tags
    im = Image.fromarray(np.round(array_img).astype(ndtype))
    im.save(filename_target, tiffinfo=tiffinfo)


def calc_reflectance(array_img,filename_input,filename_output):
    """For further details on how reflectance is obtained from multispectral images and sunlight sensor values from the Mavic 3M. Please refer 
    to Mavic 3M Image Processing Guide v1.0 2023.08 available at https://dl.djicdn.com/downloads/DJI_Mavic_3_Enterprise/20230829/Mavic_3M_Image_Processing_Guide_EN.pdf
    
    array_img - image array with vignetting correction applied and aligned
    filename_input - path to raw drone image 
    filename_nir_corrected - path to file with vignetting correction applied"""

    xmp_info,tiff_tags_info = get_tags_info(filename_input)
    array_img = np.where(array_img==0., np.nan, array_img)
    # The normalized raw pixel value:
    i_band = array_img / (2**tiff_tags_info['bits_per_sample'])

    # Black Level (BlackCurrent) 3200 for 16 bits or 12 for 8bits. The normalized black level value:
    i_blacklevel = float(xmp_info['xmpmeta']['RDF']['Description']['BlackCurrent']) / (2**tiff_tags_info['bits_per_sample'])

    # The sensor gain setting (similar to the sensor ISO):
    band_gain = float(xmp_info['xmpmeta']['RDF']['Description']['SensorGain'])

    # The camera exposure time:
    band_etime = float(xmp_info['xmpmeta']['RDF']['Description']['ExposureTime'])

    band_camera = (i_band - i_blacklevel)/(band_gain * (band_etime/10**6))   # Eq. 9

    """In addition, because the sensitivity can be different for each camera within the array and between different sunlight sensors, calibrations are required to ensure 
    that cameras of different bands and different sunlight sensors have the same signal value under the same lighting conditions. All bands are calibrated against
    the standard NIR band. The calibration parameters are 𝑝𝐶𝑎𝑚𝑥 (Sensor Gain Adjustment) and 𝑝𝐿𝑆𝑥, respectively. """
    # Gain compensation coefficient of the multispectral image sensor relative to standard NIR module
    pCam_band = float(xmp_info['xmpmeta']['RDF']['Description']['SensorGainAdjustment'])

    # Then, we need to obtain signal values relevant to the sunlight sensor, band𝐿𝑆 and 𝑝𝐿𝑆band, and calculate
    # their product. The product of band𝐿𝑆 ×  𝑝𝐿𝑆band is saved as [Irradiance] in [XMP: drone-dji] in the metadata
    BandLS_pLSband = float(xmp_info['xmpmeta']['RDF']['Description']['Irradiance'][1]) # Sunsensor value after compensation by built-in algorithm.

    Band_ref = (band_camera * pCam_band / BandLS_pLSband)
    
    # Store result:
    sourceimg = Image.open(filename_input)

    # Get the TIFF tags from the source image
    tiffinfo = sourceimg.tag_v2

    # Tag number 270 is the ImageDescription tag
    tiffinfo[270] = "Reflectance"


    # Save the target image with the correct tags
    #im = Image.fromarray(np.float32(ndvi))
    #im.save(filename_nir_corrected.replace('_NIR_','_NDVI_'), tiffinfo=tiffinfo)
    

def calc_ndvi(nir_img,red_img,filename_nir_corrected):
    """For further details on how to calculate NDVI values using multispectral images and sunlight sensor values from the Mavic 3M. Please refer 
    to Mavic 3M Image Processing Guide v1.0 2023.08 available at https://dl.djicdn.com/downloads/DJI_Mavic_3_Enterprise/20230829/Mavic_3M_Image_Processing_Guide_EN.pdf
    
    nir_img - image array with vignetting correction applied
    red_img - image array with vignetting correction applied and aligned with nir band
    filename_nir_corrected - path to file with vignetting correction applied"""
    #---------------------------------------------------------------
    # Red band:
    xmp_info,tiff_tags_info = get_tags_info(filename_nir_corrected.replace('_NIR_','_R_'))
    red_img = np.where(red_img==0., np.nan, red_img)
    i_red = red_img / (2**tiff_tags_info['bits_per_sample'])
    # Black Level (BlackCurrent) 3200 for 16 bits or 12 for 8bits.
    i_blacklevel = float(xmp_info['xmpmeta']['RDF']['Description']['BlackCurrent']) / (2**tiff_tags_info['bits_per_sample'])
    red_gain = float(xmp_info['xmpmeta']['RDF']['Description']['SensorGain'])
    red_etime = float(xmp_info['xmpmeta']['RDF']['Description']['ExposureTime'])

    red_camera = (i_red - i_blacklevel)/(red_gain * (red_etime/10**6))
    pCam_red = float(xmp_info['xmpmeta']['RDF']['Description']['SensorGainAdjustment'])

    # Then, we need to obtain signal values relevant to the sunlight sensor, Red𝐿𝑆 and 𝑝𝐿𝑆red, and calculate
    # their product Red𝐿𝑆 ×  𝑝𝐿𝑆red. The product of Red𝐿𝑆 ×  𝑝𝐿𝑆red is saved as [Irradiance] in [XMP: drone-dji] in the metadata
    Redls_pLSred = float(xmp_info['xmpmeta']['RDF']['Description']['Irradiance'][1])

    #---------------------------------------------------------
    # NIR band:
    xmp_info,tiff_tags_info = get_tags_info(filename_nir_corrected)
    nir_img[np.isnan(red_img)] = np.nan
    i_nir = nir_img / (2**tiff_tags_info['bits_per_sample'])
    # Black Level (BlackCurrent) 3200 for 16 bits or 12 for 8bits.
    i_blacklevel = float(xmp_info['xmpmeta']['RDF']['Description']['BlackCurrent']) / (2**tiff_tags_info['bits_per_sample'])
    nir_gain = float(xmp_info['xmpmeta']['RDF']['Description']['SensorGain'])
    nir_etime = float(xmp_info['xmpmeta']['RDF']['Description']['ExposureTime'])

    nir_camera = (i_nir - i_blacklevel)/(nir_gain * (nir_etime/10**6))
    pCam_nir = float(xmp_info['xmpmeta']['RDF']['Description']['SensorGainAdjustment'])

    # Then, we need to obtain signal values relevant to the sunlight sensor, 𝑁𝐼𝑅𝐿𝑆 and 𝑝𝐿𝑆𝑁𝐼𝑅, and calculate
    # their product 𝑁𝐼𝑅𝐿𝑆 × 𝑝𝐿𝑆𝑁𝐼𝑅. The product of 𝑁𝐼𝑅𝐿𝑆 × 𝑝𝐿𝑆𝑁𝐼𝑅 is saved as [Irradiance] in [XMP: drone-dji] in the metadata
    NIRls_pLSnir = float(xmp_info['xmpmeta']['RDF']['Description']['Irradiance'][1])

    NIR_ref = (nir_camera * pCam_nir / NIRls_pLSnir)
    Red_ref = (red_camera * pCam_red / Redls_pLSred)
    
    ndvi = (NIR_ref - Red_ref)/(NIR_ref + Red_ref)
    ndvi = np.where((ndvi<-1.)|(ndvi>1.),np.nan,ndvi) #remove outliers
    
    # Store result:
    sourceimg = Image.open(filename_nir_corrected)

    # Get the TIFF tags from the source image
    tiffinfo = sourceimg.tag_v2

    # Tag number 270 is the ImageDescription tag
    tiffinfo[270] = "NDVI values scaled by {}".format(default_scale)

    # Save the target image with the correct tags
    ndvi = ndvi * default_scale
    ndvi[np.isnan(ndvi)] = bands_nodata['NDVI'] # define nodata
    im = Image.fromarray(np.round(ndvi).astype('int16'))
    im.save(filename_nir_corrected.replace('_NIR_','_NDVI_'), tiffinfo=tiffinfo)


def correction_images(filename, warp_mode):
    """Function to apply Vignetting correction, realize band align and calculate NDVI. Please refer to Mavic 3M Image Processing 
    Guide v1.0 2023.08 available at https://dl.djicdn.com/downloads/DJI_Mavic_3_Enterprise/20230829/Mavic_3M_Image_Processing_Guide_EN.pdf
    
    filename - path to multispectral raw image
    warp_mode - define the motion model (Translation, Euclidean, Affine or Homography)

    Translation (MOTION_TRANSLATION): The first image can be shifted (translated) by (x , y) to obtain the second image. There are only two parameters x and y that we need to estimate.
    Euclidean (MOTION_EUCLIDEAN): The first image is a rotated and shifted version of the second image. So there are three parameters x, y and angle. Euclidean transformation, the size does
                                  not change, parallel lines remain parallel, and right angles remain unchanged after transformation.
    Affine (MOTION_AFFINE): An affine transform is a combination of rotation, translation (shift), scale, and shear. This transform has six parameters. When a square undergoes an Affine 
                            transformation, parallel lines remain parallel, but lines meeting at right angles no longer remain orthogonal.
    Homography (MOTION_HOMOGRAPHY): All the transforms described above are 2D transforms. They do not account for 3D effects. A homography transform on the other hand can account for 
                                    some 3D effects. This transform has 8 parameters. A square when transformed using a Homography can change to any quadrilateral.
    Source: https://learnopencv.com/image-alignment-ecc-in-opencv-c-python
    """

    prefix,ext = os.path.splitext(filename)
    template_band = prefix.split('_')[-1]    
    suffix = 'corrected'
    filename_template_corrected = prefix + '_' +suffix + ext    

    if os.path.exists(filename_template_corrected) != True:
        template_img_vig_corrected = vignetting_correction(filename)
        save_with_metadata(template_img_vig_corrected,'uint32',filename,filename_template_corrected,note="The image has the vignetting correction.")
        #calc_reflectance(template_img_vig_corrected,filename,prefix + '_reflectance' + ext)
    else:
       template_img_vig_corrected = np.array(Image.open(filename_template_corrected), dtype='float')

    if template_band == 'NIR':
        nir_img = template_img_vig_corrected.copy()
        filename_nir_corrected = filename_template_corrected
    elif template_band == 'R':
        r_img = template_img_vig_corrected.copy()

    # Alignment of the difference caused by different exposure times:
    #----------------------------------------------------------------
    prefix = '_'.join(prefix.split('_')[:-1])    
    
    # Smoothing image using GaussianFilter:
    template_blurred = cv2.GaussianBlur(template_img_vig_corrected, (3, 3), 0)

    # Edge detection using Canny:
    template_edge = auto_canny(template_blurred)
    
    other_bands = list(bands_definition.keys())
    other_bands.remove(template_band)
    other_bands.remove('NDVI')

    for band in other_bands:
        filename_corrected = prefix+'_'+band+'_' + suffix + ext
        if os.path.exists(filename_corrected) != True:
            img_vig_corrected = vignetting_correction(prefix+'_'+band+ext)

            # Check if already exists a warp matrix for this scene
            filename_template_warp = prefix + '_'+template_band+'_'+band+'_warp-matrix.json'
            if os.path.exists(filename_template_warp) == True:
                # Deserializing JSON array into Python object and coverting to NumPy array:
                with open(filename_template_warp,'r') as f_json:
                    warp_matrix = np.array(json.load(f_json))
            else:
                img_blurred = cv2.GaussianBlur(img_vig_corrected, (3, 3), 0)
                img_edge = auto_canny(img_blurred)

                # Image Registration using Enhanced Correlation Coefficient (ECC) Maximization - adapted from https://learnopencv.com/image-alignment-ecc-in-opencv-c-python       
                
                # Specify the number of iterations.
                number_of_iterations = 5000;
                
                # Specify the threshold of the increment in the correlation coefficient between two iterations
                termination_eps = 1e-10;
                
                # Define termination criteria
                criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations,  termination_eps)

                # Define 2x3 or 3x3 matrices and initialize the matrix to identity
                if warp_mode == cv2.MOTION_HOMOGRAPHY:
                    warp_matrix = np.eye(3, 3, dtype=np.float32)
                else:
                    warp_matrix = np.eye(2, 3, dtype=np.float32)

                # The results are stored in warp_matrix
                # It returns the final enhanced correlation coefficient, that is the correlation coefficient between the template image and the
                # final warped input image.
                print('Finding warp matrix to alignment between '+template_band+' band and '+band+' band using Enhanced Correlation Coefficient Maximization...')
                logging.info('Finding warp matrix to alignment between '+template_band+' band and '+band+' band using Enhanced Correlation Coefficient Maximization...')
                t0 = pc()    
                (cc, warp_matrix) = cv2.findTransformECC(template_edge,img_edge,warp_matrix, warp_mode, criteria);
                print('Time slapsed (s):',pc()-t0)
                logging.info('Time slapsed (s):'+str(pc()-t0))
                print('Correlation Coefficient:',cc)
                logging.info('Correlation Coefficient:'+str(cc))        

                # Converting 2D NumPy array to JSON array:
                with open(filename_template_warp, 'w') as outfile:
                    outfile.write(json.dumps(warp_matrix.tolist()))
            
            # Find size of image
            sz = template_img_vig_corrected.shape

            if warp_mode == cv2.MOTION_HOMOGRAPHY:
                # Use warpPerspective for Homography
                img_aligned = cv2.warpPerspective(img_vig_corrected, warp_matrix, (sz[1],sz[0]), flags=cv2.INTER_AREA + cv2.WARP_INVERSE_MAP);
            else:
                # Use warpAffine for Translation, Euclidean and Affine
                """The function warpAffine transforms the source image using the specified matrix:
                              dst(x,y) = src(M11 * x + M12 * y + M13,M21 * x + M22 * y + M23)
                   when the flag WARP_INVERSE_MAP is set. Otherwise, the transformation is first inverted with invertAffineTransform and 
                   then put in the formula above instead of M. The function cannot operate in-place.
                   flags - combination of interpolation methods (see InterpolationFlags) and the optional flag WARP_INVERSE_MAP that means 
                   that M is the inverse transformation ( dst → src )."""
                img_aligned = cv2.warpAffine(img_vig_corrected, warp_matrix, (sz[1],sz[0]), flags=cv2.INTER_AREA + cv2.WARP_INVERSE_MAP);

            # Save image corrected and alignment:
            save_with_metadata(img_aligned,'uint32',prefix+'_'+band+ext,prefix + '_' +band+ '_' + suffix + ext,note="The image has the vignetting correction and aligned with correlation of {}.".format(cc))

            del warp_matrix

            if band == 'NIR':
                nir_img = img_aligned.copy()
                filename_nir_corrected = prefix + '_' +band+ '_' + suffix + ext
            elif band == 'R':
                r_img = img_aligned.copy()        
        elif band == 'NIR':
            filename_nir_corrected = prefix + '_' +band+ '_' + suffix + ext
            nir_img = np.array(Image.open(filename_nir_corrected), dtype='float')
        elif band == 'R':
            r_img = np.array(Image.open(prefix + '_' +band+ '_' + suffix + ext), dtype='float')
        
    # Calc NDVI:
    """NDVI can be calculated after correcting and aligning the NIR and RED images."""
    calc_ndvi(nir_img,r_img,filename_nir_corrected)


# Adapted from https://gitlab.com/Yario/image_registration_dji_mavic_3m
def load_image(filename):
    """Load a single image with the metadata"""
    sourceimg = Image.open(filename)
    image = np.asarray(sourceimg)
    
    # Get the TIFF tags from the source image
    tiffinfo = sourceimg.tag_v2
    
    return image, tiffinfo

def save_image(filename, image, tiffinfo, note=""):
    """ Save the image with the original metadata """
    image_arr = Image.fromarray(image)

    # Tag number 270 is the ImageDescription tag
    tiffinfo[270] = " ".join([tiffinfo[270].replace('default',''),note]).lstrip()

    image_arr.save(filename, tiffinfo=tiffinfo)


def align_images(filename_image1, filename_image2):
    """Image registration via MOTION_HOMOGRAPHY"""
    image1,_ = load_image(filename_image1)
    image2 ,tiffinfo2 = load_image(filename_image2)

    prefix,ext = os.path.splitext(filename_image2)
    suffix = 'aligned'
    img_save_name = prefix + '_' +suffix + ext

    # Check if already exists a warp matrix for this scene
    prefix_template_band = os.path.splitext(filename_image1)[0]
    template_band = os.path.basename(prefix_template_band).split('_')[-1]
    band = os.path.splitext(os.path.basename(filename_image2))[0].split('_')[-1] 
    filename_template_warp = prefix_template_band+'_'+band+'_warp-matrix.json'
    filename_correlation = filename_template_warp.replace('warp-matrix','ecc-correlation')

    if os.path.exists(filename_template_warp) == True:
        # Deserializing JSON array into Python object and coverting to NumPy array:
        with open(filename_template_warp,'r') as f_json:
            warp_matrix = np.array(json.load(f_json))        

        sz = image1.shape
        print('Align images {} <--> {} using warp-matrix already generated!'.format(os.path.basename(filename_image1),os.path.basename(filename_image2)))
        logging.info('Align images {} <--> {} using warp-matrix already generated!:'.format(os.path.basename(filename_image1),os.path.basename(filename_image2)))
        # Align the final image using the homography matrix
        image2_aligned = cv2.warpPerspective(image2, warp_matrix, (sz[1], sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)

        ecc_correlation = {'correlation':None}
        if os.path.exists(filename_correlation) == True:        
            # Deserializing JSON into Python object:
            with open(filename_correlation,'r') as f_json:
                ecc_correlation = json.load(f_json)

        save_image(img_save_name, image2_aligned, tiffinfo2,note="The image aligned with a correlation of {} between {} and {} bands.".format(ecc_correlation['correlation'],template_band,band))
    else:
        warp_mode = cv2.MOTION_HOMOGRAPHY    
        # Define termination criteria
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations, termination_eps)

        print('Finding warp_matrix...')
        cc,image2_aligned,warp_matrix,status = find_warp_matrix_by_downscale_pyramids(image1,image2,warp_mode,criteria)

        if status == True and cc > 0.5:
            # Converting 2D NumPy array to JSON array:
            with open(filename_template_warp, 'w') as outfile:
                outfile.write(json.dumps(warp_matrix.tolist()))

            with open(filename_correlation, 'w') as outfile:
                outfile.write(json.dumps(dict(correlation=cc)))
            
            print('Correlation Coefficient {} <--> {}:'.format(os.path.basename(filename_image1),os.path.basename(filename_image2)),cc)
            logging.info('Correlation Coefficient {} <--> {}:'.format(os.path.basename(filename_image1),os.path.basename(filename_image2))+str(cc))
            save_image(img_save_name, image2_aligned, tiffinfo2,note="The image aligned with a correlation of {} between {} and {} bands.".format(cc,template_band,band))
        else:
            cc,image2_aligned,warp_matrix,status = find_warp_matrix_by_histogram_equalization(image1,image2,warp_mode,criteria)

            if status == True and cc > 0.5:
                # Converting 2D NumPy array to JSON array:
                with open(filename_template_warp, 'w') as outfile:
                    outfile.write(json.dumps(warp_matrix.tolist()))

                with open(filename_correlation, 'w') as outfile:
                    outfile.write(json.dumps(dict(correlation=cc)))

                print('Correlation Coefficient {} <--> {}:'.format(os.path.basename(filename_image1),os.path.basename(filename_image2)),cc)
                logging.info('Correlation Coefficient {} <--> {}:'.format(os.path.basename(filename_image1),os.path.basename(filename_image2))+str(cc))
                save_image(img_save_name, image2_aligned, tiffinfo2,note="The image aligned with a correlation of {} between {} and {} bands.".format(cc,template_band,band))
            else:
                cc,image2_aligned,warp_matrix,status = find_warp_matrix_by_edge_detection(image1,image2,warp_mode,criteria)

                if status == True:
                    # Converting 2D NumPy array to JSON array:
                    with open(filename_template_warp, 'w') as outfile:
                        outfile.write(json.dumps(warp_matrix.tolist()))

                    with open(filename_correlation, 'w') as outfile:
                        outfile.write(json.dumps(dict(correlation=cc)))

                    print('Correlation Coefficient {} <--> {}:'.format(os.path.basename(filename_image1),os.path.basename(filename_image2)),cc)
                    logging.info('Correlation Coefficient {} <--> {}:'.format(os.path.basename(filename_image1),os.path.basename(filename_image2))+str(cc))
                    save_image(img_save_name, image2_aligned, tiffinfo2,note="The image aligned with a correlation of {} between {} and {} bands.".format(cc,template_band,band))
                else:
                     logging.exception("Fail ECC Transform:\n"+str(filename_image1)+"<-->"+os.path.basename(filename_image2))
                     raise  Exception("Fail ECC Transform:\n"+str(filename_image1)+"<-->"+os.path.basename(filename_image2))          
    

def process_multispec_set(template_image_path):
    """Process one set of multispectral images (G, R, RE, NIR); using a channel as reference for the other channels"""
    prefix,ext = os.path.splitext(template_image_path)
    template_band = prefix.split('_')[-1]    
    suffix = 'aligned'
    filename_template_aligned = prefix + '_' +suffix + ext
    shutil.copy(template_image_path,filename_template_aligned) # just copy the template band image       
    
    # Process each spectral band
    other_bands = list(bands_definition.keys())
    other_bands.remove(template_band)
    other_bands.remove('NDVI')
    list_of_files = [template_image_path.replace(template_band+'.TIF',other_band+'.TIF') for other_band in other_bands]

    print("Starting multi-threading to align multispectral images.")
    t0 = pc()                
    with Pool(num_workers) as pool:
            #starmap - permits multiple arguments to the target task function
            pool.starmap(align_images, zip(repeat(template_image_path),list_of_files))        
            pool.close()
            pool.join() # wait for worker processes to exit
    print('Time slapsed (s):',pc()-t0)
    logging.info('Time slapsed (s):'+str(pc()-t0))
         


def is_decimal(s):
    try:
        Decimal(s)
        return True
    except InvalidOperation:
        return False
    

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


def prepare_thumbnail_v3(filename_out,files_in,composition,flight_yaw_degree):    
    """
    Creates thumbnail from multispectral raw images (TIF) of Drones

       :param filename_out: filename output with mission and data identification.
       :type filename: String

       :param files_in: list of multispectral raw images (TIF) with vignetting correction.
       :type file_in: List

       :param composition: list of band names to create a composition.
       :type composition: List

       :param flight_yaw_degree: angle in degrees related to North from North-East-Down (NED) coordinates, counterclockwise for negative or clockwise for positive values.
       :type arr: Float
    """
    
    tmp = np.array(Image.open(files_in[0]))
    # Find size of image
    sz = tmp.shape

    rgb = np.zeros((sz[0],sz[1],3),dtype='uint8')    
    if os.path.exists(filename_out) == False:
        cont=0
        for i,band in enumerate(composition):
            img = next((str(s) for s in files_in if "_"+band+"_corrected.TIF" in str(s)), None)
            if img:
                tmp = np.array(Image.open(img), dtype='float')
                
                # Normalize image to between 0 and 255
                tmp *= (255.0/tmp.max())
                tmp = np.round(tmp).astype('uint8')
                rgb[...,i] = tmp
                cont += 1

        if cont < 3:
            print("\n\nWARNING: fail to create thumbnail, the bands for composition ({}) not found!".format(composition))
            logging.warning("fail to create thumbnail, the bands for composition ({}) not found!".format(composition))
            raise SystemExit
            
        input_image = Image.fromarray(rgb,"RGB").convert("RGBA")
        w,h = input_image.size    
        input_image.thumbnail((int(w*0.1),int(h*0.1))) #scale image keeping aspect ratio

        #rotate image
        rot = input_image.rotate((-1.0) * flight_yaw_degree, resample=Image.NEAREST, expand=True, fillcolor=(255,255,255))
        
        #change white background to transparent
        img = np.array(rot)
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


def get_midpoint(list_files):
    """This function get the mean from center images coordinates
    """

    drone_points = []
    for file in list_files:
         _,tiff_tags_info = get_tags_info(file)
         drone_points.append([tiff_tags_info['center_coords'][1],tiff_tags_info['center_coords'][0]]) #x, y : float Easting, northing

    drone_points = np.array(drone_points)
    lon_midpoint ,lat_midpoint =  (drone_points.max(axis=0) + drone_points.min(axis=0)) / 2.0  #midpoint

    return lon_midpoint,lat_midpoint



def main(argv):
    logging.info('Started')
    log = logging.getLogger()

    template_band = os.path.splitext(os.path.basename(argv.drone_image))[0].split('_')[-1]

    if template_band not in argv.raster_output:
        print("\n\nWARNING: the raster output filename must have the same band of raw image!")           
        logging.warning("the raster output filename must have the same band of raw image!")
        raise SystemExit
       
    flight_info = {'flight_height_m':argv.flight_height,'sensor_width_mm':argv.sensor_width}
    fname_json = os.path.join(os.path.dirname(argv.drone_image),'info_ms.json')
    if (argv.flight_height == None) or (argv.sensor_width == None):        
        if os.path.exists(fname_json):
            with open(fname_json,'r') as f_json:
                flight_info = json.load(f_json)
        else:
            print("\n\nWARNING: Flight height (meters) and sensor width (millimeters) were parameters\nneeded for projection. Generally, this information" \
                  " is present in file info_ms.json on the same path as the images!\n" \
                  "Please, use command line inputs '--flight_height' and '--sensor_width' to processing image and create json file with this information.\n" \
                    "For example:\n"\
                    "python drone_correction_projection_warp.py --drone_image DJI_20231107174953_0628_MS_NIR.TIF --flight_height 120\n"\
                         "--sensor_width 5.2 --raster_output ./DJI_20231107174953_0628_MS.tif --view R NIR G")           
            logging.warning("Flight height (meters) and sensor width (millimeters) were parameters\nneeded for projection. Generally, this information" \
                  " is present in file info_ms.json on the same path as the images!\n" \
                  "Please, use command line inputs '--flight_height' and '--sensor_width' to processing image and create json file with this information.\n" 
                    "For example:\n"\
                    "python drone_correction_projection_warp.py --drone_image DJI_20231107174953_0628_MS_NIR.TIF --flight_height 120\n"\
                         "--sensor_width 5.2 --raster_output ./DJI_20231107174953_0628_MS.tif --view R NIR G")
            raise SystemExit
    elif os.path.exists(fname_json) == False:
         if is_decimal(flight_info['flight_height_m']) and is_decimal(flight_info['sensor_width_mm']):
                    print('\n',flight_info)
                    print('Path to save auxiliary information file:\n',os.path.dirname(fname_json))
                    
                    ch = input("\nDo you want to save this auxiliary information (flight height and sensor width) for all images in this folder? (y/n)")
                    if ch.lower() == 'y':
                          with open(fname_json, 'w') as outfile:
                               outfile.write(json.dumps(flight_info, indent=4))
    
    # Correction and alignment of bands
    """First, the multispectral images from the Mavic 3M need to be corrected and aligned due to vignetting, lens distortion, slight difference in position, 
    optical accuracy and exposure time between different bands."""
    #correction_images(argv.drone_image, warp_mode=cv2.MOTION_HOMOGRAPHY)

    # List bands to correct align  
    prefix = '_'.join(os.path.splitext(os.path.basename(argv.drone_image))[0].split('_')[:-1])
    _,suffix = os.path.splitext(argv.drone_image) 
    drone_images = [file for file in Path(os.path.dirname(argv.drone_image)).rglob(prefix+'*_aligned'+suffix)]
    if len(drone_images) < 4:
        # Using Homography motion, pyramid of image resolutions and multiprocessing to align between bands
        process_multispec_set(str(argv.drone_image))

    # List bands to correct vignetting  
    prefix = '_'.join(os.path.splitext(os.path.basename(argv.drone_image))[0].split('_')[:-1])
    _,suffix = os.path.splitext(argv.drone_image) 
    drone_images = [file for file in Path(os.path.dirname(argv.drone_image)).rglob(prefix+'*_corrected'+suffix)]
    if len(drone_images) < 5:        
        print('Correcting vignetting...')
        drone_images = [file for file in Path(os.path.dirname(argv.drone_image)).rglob(prefix+'*_aligned'+suffix)]
        lon_midpoint, lat_midpoint = get_midpoint(drone_images)

        for aligned_file in drone_images:
            img_vig_corrected = vignetting_correction(aligned_file)
            band = os.path.splitext(os.path.basename(aligned_file))[0].split('_')[-2]
            filename_corrected = str(aligned_file).replace('aligned','corrected')
            save_with_metadata(img_vig_corrected,'uint32',aligned_file,filename_corrected,note="The image has the vignetting correction.")

            # Remove temporary file
            os.remove(aligned_file)

            if band == 'NIR':
                nir_img = img_vig_corrected.copy()
                filename_nir_corrected = filename_corrected
            elif band == 'R':
                r_img = img_vig_corrected.copy()        
            
        # Calc NDVI:
        """NDVI can be calculated after correcting and aligning the NIR and RED images."""
        calc_ndvi(nir_img,r_img,filename_nir_corrected)
    else:
        lon_midpoint, lat_midpoint = get_midpoint(drone_images)
    
    """EPSG:3395 - WGS 84/World Mercator is global coordinate system with unit in meters. Source: https://epsg.io/3395"""
    # Set up transformers, EPSG:3395 is metric
    crs_dst = 'EPSG:3395'
    
    # List bands to project
    prefix = '_'.join(os.path.splitext(os.path.basename(argv.drone_image))[0].split('_')[:-1])
    _,suffix = os.path.splitext(argv.drone_image) 
    drone_images = [file for file in Path(os.path.dirname(argv.drone_image)).rglob(prefix+'*_corrected'+suffix)]
    drone_images.sort()

    os.makedirs(os.path.dirname(argv.raster_output), exist_ok=True)
    f_thumb_out = (argv.raster_output).replace('_'+template_band+os.path.splitext(os.path.basename(argv.raster_output))[1],'')+'.png'
    _,tiff_tags_info_template = get_tags_info(argv.drone_image)

    # # Get RGB center coordinates:
    # prefix_rgb = '_'.join(prefix.split('_')[0:-1])
    # drone_image_rgb = [file for file in Path(os.path.dirname(argv.drone_image)).rglob(prefix_rgb+'*.JPG')]
    # exif_info = get_exif_info(str(drone_image_rgb[0]))
    

                
    # Create a thumbnail:
    prepare_thumbnail_v3(f_thumb_out, drone_images, argv.view, tiff_tags_info_template['flight_yaw_degree'])

    block_size_output = 256 #Sets the tile width and height in pixels. Must be divisible by 16. https://gdal.org/drivers/raster/cog.html#general-creation-options
    for drone_image in drone_images:
        band_name = os.path.splitext(os.path.basename(drone_image))[0].split('_')[-2]
        _,tiff_tags_info = get_tags_info(drone_image)
        tiff_tags_info['center_coords'] = (tiff_tags_info_template['center_coords'][0],tiff_tags_info_template['center_coords'][1]) #replace coordinates for template band
        tiff_tags_info['center_coords'] = (lat_midpoint,lon_midpoint) #replace coordinates for midpoint of bands
        #tiff_tags_info['center_coords'] = (exif_info['center_coords'][0], exif_info['center_coords'][1]) #replace coordinates for RGB image center coordinates
        
        if tiff_tags_info != None:    
            #Ground Sample Distance (cm) based on flying height above ground level, sensor width size (mm), focal lenght (mm), image width (pixels)
            GSD = (flight_info['flight_height_m']  * flight_info['sensor_width_mm']) / (tiff_tags_info['img_dim_x'] * tiff_tags_info['focal_lenght']) * 100.
            
            # Get corner coordinates of image based on center coordinates, spatial resolution and dimensions of image:    
            gdf_cardinal_points = create_cardinal_points(tiff_tags_info['center_coords'][0], tiff_tags_info['center_coords'][1], 
                                                    tiff_tags_info['img_dim_x'], tiff_tags_info['img_dim_y'], GSD,
                                                    crs_src='EPSG:4326', #coordinate reference system of lat/lon
                                                    crs_dst=crs_dst)

            # Create a GeoTIFF file projected using Global Mercator Coordinate System and Flight Yaw Degree:
            arr = np.array(Image.open(drone_image))

            driver = gdal.GetDriverByName('MEM') #To avoid error of overview creation

            dst_filename = (argv.raster_output).replace('_'+template_band+os.path.splitext(os.path.basename(argv.raster_output))[1], \
                                                        '_'+band_name+os.path.splitext(os.path.basename(argv.raster_output))[1])

            dst_ds = driver.Create('', xsize=arr.shape[1], ysize=arr.shape[0],
                                bands=1, eType=bands_gdal_type[band_name])

            ul_x,_,_,ul_y = gdf_cardinal_points.total_bounds
            p_size_meters = GSD / 100.

            #In case of north up images, the GT(2) and GT(4) coefficients are zero,
            #and the GT(1) is pixel width, and GT(5) is pixel height. 
            #The (GT(0),GT(3)) position is the top left corner of the top left pixel of the raster.

            dst_ds.SetGeoTransform([ul_x, p_size_meters, 0, ul_y, 0, -p_size_meters])

            srs = osr.SpatialReference()
            srs.ImportFromEPSG(int(crs_dst.split(':')[1]))
            dst_ds.SetProjection(srs.ExportToWkt())

            band = dst_ds.GetRasterBand(1)
            band.WriteArray(arr)
            band.SetDescription(bands_definition[band_name]) # This sets the band name!
            band.SetColorInterpretation(bands_colour_interpretation[band_name])
            band.SetNoDataValue(bands_nodata[band_name])
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
            dst_ds.SetGeoTransform(rotate_gt(gt_affine, tiff_tags_info['flight_yaw_degree'], center))

            # Create temporary file
            fd, path = tempfile.mkstemp(suffix='.tif')
            os.close(fd)

            # Create GeoTIFF with North Up reference for each band:
            # https://gdal.org/drivers/raster/cog.html#raster-cog
            # https://erouault.blogspot.com/2014/10/warping-overviews-and-warped-overviews.html
            # Resampling using one of "AVERAGE", "AVERAGE_MAGPHASE", "RMS", "BILINEAR", "CUBIC", "CUBICSPLINE", "GAUSS", 
            # "LANCZOS", "MODE", "NEAREST", or "NONE" method applied
            dst_output = gdal.Warp(path,  dst_ds, options="-of COG -r NEAREST -oo OVERVIEW_LEVEL=5 -co BLOCKSIZE={}" \
                            " -co COMPRESS=NONE -co NUM_THREADS={}".format(str(block_size_output),str(num_workers),))

            dst_output = gdal.Translate(dst_filename,  path, options="-stats -mo comment={} -of COG -r NEAREST -oo OVERVIEW_LEVEL=5 -co BLOCKSIZE={}" \
                            " -co COMPRESS=DEFLATE -co NUM_THREADS={}".format(tiff_tags_info['img_description'].replace(' ','_'),str(block_size_output),str(num_workers)))
            os.remove(path) #remove temporary file
            
            if 'raster_info' not in locals():
                raster_info = get_raster_info(dst_output,block_size_output)
    
            # Once we're done, close properly the dataset
            dst_ds = None
            dst_output = None

            # Remove temporary files
            os.remove(drone_image)
        
            logging.info('Projected file saved as:\n'+dst_filename)        
            if __name__ == "__main__":
                print('Projected file saved as:\n',dst_filename)
    
    logging.info('Finished')
    if __name__ != "__main__":
        return raster_info



if __name__ == "__main__":
    from drone_projection_warp import get_exif_info

    # Process the arguments
    from argparse import ArgumentParser, SUPPRESS
    import arghelper

    # Disable default help
    parser = ArgumentParser(description='Creates a COG file with a composition of multispectral images from drone and NDVI, using TiFF and XPM metadata tags and auxiliary \
                            information such as flight height and sensor parameters (width and focal distance). \
                            Generally, these parameters are defined in the auxiliary file info_ms.json present in the path of the scene.',
                            add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    # Add back help
    optional.add_argument('-h','--help',action='help',default=SUPPRESS,help='show this help message and exit')   
    required.add_argument('--drone_image', type=lambda x: arghelper.is_valid_file(parser, x),
                       help='[Obs.: This image is used as a template to align other bands] Path to raw multispectral drone image in TIF format',
                        metavar='path_to_file', required=True)
    required.add_argument('--raster_output', type=lambda x: arghelper.is_valid_namefile(parser, x), help='COG filename output (including path).', required=True)
    #required.add_argument('--template_band', help='Band used to align other multispectral drone images.', choices=list(band for band in bands_definition.keys() if band != 'NDVI'), required=True)

    optional.add_argument('--flight_height',
                       help='Flight height in meters, this information is important to define the spatial resolution of the image (Ground Sample Distance - GSD).',
                       metavar='120', type=int, required=False)    
    optional.add_argument('--sensor_width',
                       help='Camera sensor width size (TSX) in millimeters. For example 6.48 (DJI Phantom 3 Advanced)',
                        metavar='6.48', type=float, required=False)
    optional.add_argument('--view', help='List of bands to visualization. For example R NIR G.', nargs=3, default=['R','NIR','G'], choices=list(bands_definition.keys()))  
    
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    sys.exit(main(parser.parse_args()))


