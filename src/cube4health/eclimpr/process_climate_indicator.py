""" This module provides a single public function to deal with indicators processing """

from typing import Literal

from . import (
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
        Directory path where the NetCDF or GRIB files are stored.
    output_dir : str
        Directory path where the indicators generated will be stored.
    folder_name : str
        Name of the folder to be created for output files.
    shapefile_path : str
        Path to the Shapefile of the study area.
    variable_name : str
        Variable name in the NetCDF file (e.g., '2m_temperature', 'temp').
    years : iterable of int or str
        List of years or a single year to process (e.g., [2020, 2021]).
    color_png_file : str
        Path to the file with color ranges for PNG output. Default is provided by package
    aggregation_type : str or iterable of str, optional
        Aggregations to compute (e.g., 'max', 'min', 'mean', or 'all'). Default is 'all'. Ignored by some indicators that do not support it.
    interval_file_path : str, optional
        Path to a custom interval file (used when "provide_interval=True" for epidemiological week flows).
    provide_interval : bool, optional
        If True, allows the user to provide a custom interval file. Default is False (use standard epidemiological weeks).
    type_indicator : {{"temp_era5land", "precip_era5land", "anomaly_era5land", "humidity_era5land", "temp_cptec", "precip_cptec"}}, required
        Which indicator family to process. Default is "temp_era5land".
    spatial_aggregation : {{"epiweek", "month"}}, required
        Temporal aggregation unit. Default is "epiweek".
    
    Returns
    -------
    None
        The specialized functions perform their processing and side effects (file outputs). No value is returned.

    Raises
    ------
    ValueError
        If an invalid combination of "type_indicator" and "spatial_aggregation" is given.
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


