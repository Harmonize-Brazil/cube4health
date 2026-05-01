Changelog
=========

(unreleased)
------------

* Fix RasterIO error in get_raster_info function.
* Remove extra dependencies from pyproject.toml. Starting from version 6, timezonefinder no longer provides optional extras, including the pytz extra.
* Fix invalid value encountered in division ndvi = (NIR - Red)/(NIR + Red) in EDDPR module.
* Migrate project versioning to setuptools-git-versioning.
* Changed the EDDPR module to save the mosaics COG with embedded statistics to improve the Geoserver rendering

0.3.0 (2025-11-15)
------------------

* ECLIMPR module added data publication workflow, improved anomaly coloring logic, fixed GeoServer style configuration used by EDPU. 
* EHIPR module implemented epidemiological week generation using the *epiweeks* package
* EDDPR module changed the folder name for mosaic products
* EHIPR module updated internal imports to reference cube4health packages correctly


0.2.0 (2025-10-14)
------------------

* ECLIMPR module improved PostgreSQL insertion using MULTIPOLYGON geometries, and fixed Zenodo data download function.
* EHIPR module optimized PostgreSQL batch insertion and enabled post-spatialization health data publication.
* EDDPR module adopted STAC extension *renders* to RGB composition from multispectral and True Color Image (TCI) drone data
* Add dynamic version using Git scm
* Fix the documentation generation using Sphinx.

0.1.0 (2025-09-19)
------------------

* Add ECLIMPR module and included major refactoring for climate indicators processing, implemented epidemiological week generation using the *epiweeks* package, and integrated Sphinx documentation generation. 
* Add EDDPR module.
* Add EDPU module.
* Add EHIPR module and validate InfoDengue flow.

0.0.1 (2025-04-24)
------------------

* Initial version.
