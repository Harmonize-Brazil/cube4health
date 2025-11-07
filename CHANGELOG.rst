Changelog
=========

(unreleased)
------------

* eclimpr module added data publication workflow, improved anomaly coloring logic, fixed GeoServer style configuration used by edpu. 
* ehipr module implemented epidemiological week generation using the *epiweeks* package
* eddpr module changed the folder name for mosaic products
* ehipr module updated internal imports to reference cube4health packages correctly


0.2.0 (2025-10-14)
------------------

* eclimpr module improved PostgreSQL insertion using MULTIPOLYGON geometries, and fixed Zenodo data download function.
* ehipr module optimized PostgreSQL batch insertion and enabled post-spatialization health data publication.
* eddpr module adopted STAC extension *renders* to RGB composition from multispectral and True Color Image (TCI) drone data
* Add dynamic version using Git scm
* Fix the documentation generation using Sphinx.

0.1.0 (2025-09-19)
------------------

* Add eclimpr module and included major refactoring for climate indicators processing, implemented epidemiological week generation using the *epiweeks* package, and integrated Sphinx documentation generation. 
* Add eddpr module.
* Add edpu module.
* Add ehipr module and validate InfoDengue flow.

0.0.1 (2025-04-24)
------------------

* Initial version.
