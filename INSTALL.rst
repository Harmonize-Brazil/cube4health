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


Installation
============

The ``cube4health`` relies primarily on the Geospatial Data Abstraction Library (`GDAL <https://gdal.org/en/stable/>`_) for raster processing. Please read the instructions below to install ``cube4health``.


Development Installation
------------------------

Install the GDAL library and its development header files on your system (Linux systems):

.. code-block:: shell

        sudo apt-get update && sudo apt-get upgrade
        sudo apt-get install -y g++ && sudo apt-get install -y gdal-bin libgdal-dev

Install the Python dependencies and build numpy-based raster support (Linux systems):

.. code-block:: shell

        export GDAL_VERSION=$(gdal-config --version)
        export CPLUS_INCLUDE_PATH=/usr/include/gdal
        export C_INCLUDE_PATH=/usr/include/gdal
        pip3 install --upgrade "pip<=25.2" wheel numpy
        pip3 install --use-pep517 --no-build-isolation --no-cache-dir --force-reinstall gdal[numpy]==`gdal-config --version`

Verify that numpy-based raster support has been installed:

.. code-block:: shell

        python -c "from osgeo import gdal, gdal_array ; print(gdal.__version__)"

**Obs.:** If this command raises an ImportError, numpy-based raster support has not been properly installed. Please see these `related issues and solutions <ISSUES.rst>`_!

Source code from Github:

.. code-block:: shell

        pip install git+https://github.com/Harmonize-Brazil/cube4health.git

Alternative using *Python Virtual Environment*:

1. Clone the software repository:

.. code-block:: shell

        git clone https://github.com/Harmonize-Brazil/cube4health.git

2. Go to the source code folder:

.. code-block:: shell

        cd cube4health

3. Create a new virtual environment linked to Python 3.10:

.. code-block:: shell

        python3.10 -m venv venv

4. Activate the new environment:

.. code-block:: shell

        source venv/bin/activate

5. Install using custom setup for GDAL bindings:

.. code-block:: shell

        ./setup_env.sh
        
**Obs.:** This installs the package in development mode, allowing you to modify the code without having to rebuild the package.

Problems with GDAL import? Please see these `related issues and solutions <ISSUES.rst>`_!
