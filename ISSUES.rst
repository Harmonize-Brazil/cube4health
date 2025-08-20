============================
Related issues and solutions
============================

GDAL import problem:
====================

ImportError: /home/user/miniconda3/envs/py310/bin/../lib/libstdc++.so.6: version `GLIBCXX_3.4.30' not found (required by /lib/libgdal.so.30)


Tip

Find version required and link to current environment:

strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBCXX_3.4.30
mv /home/user/miniconda3/envs/py310/lib/libstdc++.so.6 /home/user/miniconda3/envs/py310/lib/libstdc++.so.6_old
ln -s /usr/lib/x86_64-linux-gnu/libstdc++.so.6 /home/user/miniconda3/envs/py310/lib/libstdc++.so.6


Test GDAL import:
=================

.. code-block:: shell

        python -c "from osgeo import gdal, gdal_array ; print(gdal.__version__)"


If this command raises an ImportError, numpy-based raster support has not been properly installed. This is most often due to pip reusing a cached GDAL installation. 
Verify that the necessary dependencies have been installed and then run the following to force a clean build:

.. code-block:: shell

        pip3 install --no-cache --force-reinstall gdal[numpy]=="$(gdal-config --version).*"

Check again:

.. code-block:: shell

        python -c "from osgeo import gdal, gdal_array ; print(gdal.__version__)"

