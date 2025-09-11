#!/bin/bash
# NOTE: convert NetCDF file to COG – Cloud Optimized GeoTIFF and to PNG.
# Edit the directory with .nc files, then execute "/[path_script]/gdal_script_convert_NetCDF_to_TIFF.sh"
# Daily Product from http://ftp.cptec.inpe.br/modelos/tempo/SAMeT/DAILY/
# SAMeT - CPTEC/INPE
# https://www.cogeo.org/developers-guide.html
# https://trac.osgeo.org/gdal/wiki/CloudOptimizedGeoTIFF
# color  - https://grasswiki.osgeo.org/wiki/Color_tables
# https://grass.osgeo.org/grass82/manuals/r.colors.html
# https://queimadas.dgi.inpe.br/queimadas/portal/risco-de-fogo-meteorologia

echo
echo "----- Start processing -----"

mydir=$(pwd)

#exec > ${mydir}/output_mosaic_TIFF_COG_color.log 2>&1
#echo "Inicio: `date +%d-%m-%y_%H:%M:%S`"

##path_TIFF_files=$(pwd)
#path_TIFF_files="/home/adeline/Dropbox/github_projects/BDC_Harmonize/scripts_climate/fiocruz_studies/data_era5_prec_temp/temperature/max/Nordeste/indi_max" # <---- CHANGE ME
#path_color_file="/home/adeline/Dropbox/github_projects/BDC_Harmonize/scripts_climate/Shell/color_temperature_fire_era5.txt" # <---- CHANGE ME

path_TIFF_files="$1"
path_color_file="$2"

echo "Name directory: $1"
echo "Color range: $2"

printf $path_TIFF_files $path_color_file

echo
echo "----- COG to PNG Color  -----"
echo
dir=thumbnail
mkdir -p $path_TIFF_files/$dir

files_tif=$(find ${path_TIFF_files} -maxdepth 1 -name '*.tif' | wc -l)
echo $files_tif " files with .tif here!"

if [ "$files_tif" != "0" ]
then
  echo
  for file1 in ${path_TIFF_files}/*.tif; do
    echo $file1
    output1=$(echo $(basename -a "$file1" | cut -f 1 -d '.'))
    echo $output1
    # time gdaldem color-relief "$file1" $path_color_file ${path_TIFF_files}/${dir}/${output1}".tif" -alpha
    time gdaldem color-relief -nearest_color_entry -b 1 "$file1" $path_color_file ${path_TIFF_files}/${dir}/${output1}".png"
    echo
  done


  echo "Script has been executed successfully"

else
echo
echo "No files with that extension in the directory!"
echo
fi

echo "Script has been executed successfully"
echo
echo "Fim: `date +%d-%m-%y_%H:%M:%S`"
