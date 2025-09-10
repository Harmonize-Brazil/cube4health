..
    This file is part of Python cube4health package.
    Copyright (C) 2025 HARMONIZE/INPE.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.


Usage
=====

Running cube4health package in the Command Line
-----------------------------------------------

The ``cube4health`` package installs a command line tool with the same name ``cube4health`` that allows processing and publishing health, climate, and drone data produced in the 
context of the Earth Observation Data Cube tuned for Health Response Systems (EODCtHRS) component of the HARMONIZE project. Important to know that the publishing process is based on 
predefined protocols and additional services such as BDC-STAC, Geoserver, and Titiler. Please see the documentation available on the `Cube4Health GitHub page <https://harmonize-brazil.github.io/cube4health/index.html>`_.


If you want to know the cube4health version, use the option ``--version`` as in::

    cube4health --version


Each type of data has your specific module (subpackage) for processing and publishing, try (``eddpr`` - drone, ``ehipr`` - health, and ``eclimpr`` - climate) to see parameter requirements::

    cube4health run --module eddpr -h

    
    usage: run --module eddpr [-h] --server_type {localhost,remote} --root_path ROOT_PATH --data_path_output
                          DATA_PATH_OUTPUT --publish_data {True,False}

    Convert raw images and mosaics to Cloud Optimized GeoTIFF (COG) and create JSON files to build catalogs using
    SpatioTemporal Asset Catalog (STAC) specification

    required arguments:
    --server_type {localhost,remote}
                            Required server target type localhost or remote
    --root_path ROOT_PATH
                            Required path to raw and mosaic images from drone. Example /home/user/Desktop/HARMONIZE-
                            Br_Project/src/FieldWorkCampaigns
    --data_path_output DATA_PATH_OUTPUT
                            Required path to save Cloud Optimized GeoTIFF (COG) files. Example /home/user/Docker-
                            Compose/geoserver/data
    --publish_data {True,False}
                            Required parameter to specify a supplementary processing step for automatically publishing
                            data via the BDC STAC service and Geoserver. Note: Additional parameters will be requested
                            after data processing.

    optional arguments:
    -h                    show this help message and exit


This is an example of using the ``eddpr`` module to process and publish data at localhost::

    cube4health run --module eddpr  --server_type localhost --root_path /home/user/Desktop/HARMONIZE-Br_Project/src/FieldWorkCampaigns --data_path_output /home/user/Docker-Compose/geoserver/data  --publish_data True

**Obs.:** the of processing drone data is based on the `Harmonize protocol <https://docs.google.com/document/d/1pZ_yBBRXJBnyq6wTk4bMXDYmdHe-aP1BHejxg4-wc4U/edit?usp=sharing>`_  that shows how to provide images and auxiliary information from fieldwork campaigns available in the folder especified through the  ``--root_path`` option. The creation of images or mosaics collections depends on templates files in JSON format for each device (e.g. Phantom 3 Advanced, Mavic 3M, Mavic 3 Enterprise), type (scene, mosaic or thermal) and flight height. 