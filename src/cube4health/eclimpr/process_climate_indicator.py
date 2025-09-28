""" This module provides a single public function to deal with indicators processing """

from typing import Literal

from cube4health.eclimpr import (
    process_era5land_temp,
    process_era5land_precip,
    process_era5land_anomaly,
    process_era5land_rhumidity,
    process_cptec_temp,
    process_cptec_precip,
)

def process_climate_indicator(main_dir, output_dir, folder_name, shapefile_path, variable_name, years, color_png_file=None, aggregation_type: Literal["max", "min", "mean", "all"] = "max", interval_file_path= None, provide_interval = False, type_indicator = "temp_era5land", spatial_aggregation: Literal ["epiweek", "month"] = "epiweek", **kwargs,):
    """
    Process climate indicators from ERA5-Land or CPTEC/INPE, by epidemiological week or by month.

    This is a facade that dispatches to the appropriate specialized function, keeping a single, user-friendly entry point.

    Parameters
    ----------
    main_dir : str
        Directory path where the source NetCDF/GRIB files are stored (input root).
        For most indicators, this should be a single folder containing the relevant files.
        For ``humidity_era5land``, however, two subfolders are required inside ``main_dir``:
            - ``temperature``: must contain data with ``2m_temperature_day_mean``.
            - ``dewpoint``: must contain data with ``2m_dewpoint_temperature_day_mean``.
    output_dir : str
        Directory path where outputs (rasters/vector files/PNGs) will be written.
    folder_name : str
        Name of the output subfolder (e.g., regional scope like ``"northeast"``).
    shapefile_path : str
        Path to the study-area Shapefile used for clipping/aggregation.
    variable_name : str
        Name of the variable in the data files (e.g., ``"2m_temperature"``, ``"temp"``).
    years : iterable of int or str
        Year or list of years to process (e.g., ``[2019, 2020]`` or ``"2020"``).
    color_png_file : str, optional
        Path to a color table used when exporting PNGs. If ``None``, a package default is used
        (e.g., templates under ``eclimpr/templates``).
    aggregation_type : {"max", "min", "mean", "all"}, optional
        Statistical aggregation(s) to compute over the selected temporal unit.
        If ``"all"``, every supported aggregation for that indicator is computed.
        Default is ``"max"``. (Some indicators may ignore this parameter.)
    interval_file_path : str, optional
        Path to a custom interval definition file for epidemiological weeks. Used only when
        ``provide_interval=True``.
    provide_interval : bool, optional
        If ``True``, enables the use of a custom epidemiological weeks calendar provided via ``interval_file_path``.
        If ``False``, the standard epidemiological weeks calendar is used. Default is ``False``.
    type_indicator : {"temp_era5land", "precip_era5land", "anomaly_era5land", "humidity_era5land",
                    "temp_cptec", "precip_cptec"}, optional
        Indicator family to process. Default is ``"temp_era5land"``.
    spatial_aggregation : {"epiweek", "month"}, optional
        Temporal aggregation unit. Default is ``"epiweek"``.
    **kwargs
        Extra keyword arguments forwarded to the specialized processing functions (e.g., resampling parameters, nodata handling, compression options, etc.).
    
    Returns
    -------
    None
        The function performs side effects only (writes files to ``output_dir``) and returns nothing.

    Raises
    ------
    ValueError
        If an invalid combination of "type_indicator" and "spatial_aggregation" is given.

    Notes
    -----
    - **Facade pattern**: this function does not implement processing logic; it routes to the correct specialized routine based on ``type_indicator`` and ``spatial_aggregation``.
    - **Color tables**: when ``color_png_file`` is not provided, a default color table shipped with the package is used automatically.
    - **Custom epiweeks**: when ``provide_interval=True``, the interval file must conform to the expected epiweek format of the specialized routines.
    - **Outputs**: specialized functions typically export (i) aggregated rasters, (ii) vector summaries (Shapefile/GeoJSON) per administrative unit, and (iii) preview PNGs using the chosen color table.

    See Also
    --------
    process_era5land_temp.process_era5land_temp_epiweek
    process_era5land_temp.process_era5land_temp_month
    process_era5land_precip.process_era5land_precip_epiweek
    process_era5land_precip.process_era5land_precip_month
    process_era5land_anomaly.process_era5land_anomaly_epiweek
    process_era5land_anomaly.process_era5land_anomaly_month
    process_era5land_rhumidity.process_era5land_rhumidity_epiweek
    process_era5land_rhumidity.process_era5land_rhumidity_month
    process_cptec_temp.process_cptec_temp_epiweek
    process_cptec_temp.process_cptec_temp_month
    process_cptec_precip.process_cptec_precip_epiweek
    process_cptec_precip.process_cptec_precip_month
    
    Examples
    --------

    >>> import importlib.resources as pkg_resources
    ... from cube4health.eclimpr.process_climate_indicator import process_climate_indicator

    >>> roi = pkg_resources.files('cube4health.eclimpr.shp_malhas.northeast').joinpath('northeast.shp')

    ERA5-Land temperature by epiweek (max only):

    >>> process_climate_indicator(
    ...     type_indicator="temp_era5land",
    ...     spatial_aggregation="epiweek",
    ...     main_dir="/path/to/data/era5land/temp all NetCDF files",
    ...     output_dir="/outputs/indicators",
    ...     folder_name="northeast",
    ...     shapefile_path=roi,
    ...     variable_name="2m_temperature",
    ...     years=[2010, 2011],
    ...     aggregation_type="max"
    ... )
    
    ERA5-Land precipitation by month (all aggregations):

    >>> process_climate_indicator(
    ...     type_indicator="precip_era5land",
    ...     spatial_aggregation="month",
    ...     main_dir="/path/to/data/era5land/precip all NetCDF files",
    ...     output_dir="/outputs/indicators",
    ...     folder_name="northeast",
    ...     shapefile_path=roi,
    ...     variable_name="tp",
    ...     years=[2020, 2021],
    ...     aggregation_type="all"
    ... )

    CPTEC temperature by epiweek with custom epiweek calendar:

    >>> process_climate_indicator(
    ...     type_indicator="temp_cptec",
    ...     spatial_aggregation="epiweek",
    ...     main_dir="/path/to/data/cptec/TMAX all NetCDF files",
    ...     output_dir="/outputs/indicators",
    ...     folder_name="north",
    ...     shapefile_path="/path/to/shapes/NO_municipios.shp",
    ...     variable_name="temp",
    ...     years=[2022],
    ...     provide_interval=True,
    ...     interval_file_path="/configs/epiweek_intervals.csv",
    ...     aggregation_type="mean"
    ... )

    """

    # Normalize/validate indicators
    valid_indicators = {
        "temp_era5land",
        "precip_era5land",
        "anomaly_era5land",
        "humidity_era5land",
        "temp_cptec",
        "precip_cptec",
    }
    valid_aggs = {"epiweek", "month"}

    if type_indicator not in valid_indicators:
        raise ValueError(f"Invalid type_indicator: {{type_indicator}}. Must be one of {{sorted(valid_indicators)}}")
    if spatial_aggregation not in valid_aggs:
        raise ValueError(f"Invalid spatial_aggregation: {{spatial_aggregation}}. Must be one of {{sorted(valid_aggs)}}")

    # Common args (without aggregation_type; add only where needed)
    def _epiweek_args_common():
        return dict(
            main_dir = main_dir,
            output_dir = output_dir,
            folder_name = folder_name,
            shapefile_path = shapefile_path,
            variable_name = variable_name,
            years = years,
            color_png_file = color_png_file,
            interval_file_path = interval_file_path,
            provide_interval = provide_interval,
        )

    def _month_args_common():
        return dict(
            main_dir = main_dir,
            output_dir = output_dir,
            folder_name = folder_name,
            shapefile_path = shapefile_path,
            variable_name = variable_name,
            years = years,
            color_png_file = color_png_file,
        )

    # Route using if/else to temperature, precipitation, anomaly and humidity era5land
    # ERA5-Land temperature
    if type_indicator == "temp_era5land" and spatial_aggregation == "epiweek":
        return process_era5land_temp.process_era5land_temp_epiweek(
            **_epiweek_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
            )
    if type_indicator == "temp_era5land" and spatial_aggregation == "month":
        return process_era5land_temp.process_era5land_temp_month(
            **_month_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
            )

    # ERA5-Land precipitation
    if type_indicator == "precip_era5land" and spatial_aggregation == "epiweek":
        return process_era5land_precip.process_era5land_precip_epiweek(
            **_epiweek_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
            )
    if type_indicator == "precip_era5land" and spatial_aggregation == "month":
        return process_era5land_precip.process_era5land_precip_month(
            **_month_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
            )

    # ERA5-Land anomaly
    if type_indicator == "anomaly_era5land" and spatial_aggregation == "epiweek":
        return process_era5land_anomaly.process_era5land_anomaly_epiweek(
            **_epiweek_args_common(), 
            **kwargs,
            )
    if type_indicator == "anomaly_era5land" and spatial_aggregation == "month":
        return process_era5land_anomaly.process_era5land_anomaly_month(
            **_month_args_common(), 
            **kwargs,
            )

    # ERA5-Land relative humidity
    if type_indicator == "humidity_era5land" and spatial_aggregation == "epiweek":
        return process_era5land_rhumidity.process_era5land_rhumidity_epiweek(
            **_epiweek_args_common(), 
            **kwargs,
            )
    if type_indicator == "humidity_era5land" and spatial_aggregation == "month":
        return process_era5land_rhumidity.process_era5land_rhumidity_month(
            **_month_args_common(), 
            **kwargs,
            )

    # Route using if/else to temperature and precipitation cptec
    # CPTEC temperature
    if type_indicator == "temp_cptec" and spatial_aggregation == "epiweek":
        return process_cptec_temp.process_cptec_temp_epiweek(
             **_epiweek_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
        )
    if type_indicator == "temp_cptec" and spatial_aggregation == "month":
        return process_cptec_temp.process_cptec_temp_month(
            **_month_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
        )

    # CPTEC precipitation
    if type_indicator == "precip_cptec" and spatial_aggregation == "epiweek":
        return process_cptec_precip.process_cptec_precip_epiweek(
            **_epiweek_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
        )
    if type_indicator == "precip_cptec" and spatial_aggregation == "month":
        return process_cptec_precip.process_cptec_precip_month(
            **_month_args_common(),
            aggregation_type=aggregation_type,
            **kwargs,
        )

    # Unsupported combination
    raise ValueError(f"Unsupported combination: type_indicator={type_indicator}, spatial_aggregation={spatial_aggregation}")


