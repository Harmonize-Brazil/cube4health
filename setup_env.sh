#!/bin/bash

export GDAL_VERSION=$(gdal-config --version)
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal

echo "Using GDAL version: $GDAL_VERSION"

# Upgrade pip and install Python dependencies and build numpy-based raster support
pip3 install --upgrade "pip<=25.2" wheel
pip3 install numpy
pip3 install --use-pep517 --no-build-isolation --no-cache-dir --force-reinstall gdal[numpy]==`gdal-config --version`
pip install -e .
