# inbuilt libraries
import os
import zipfile
import subprocess
from datetime import datetime
from typing import (
    List,
    Optional
)

# third-party libraries
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
from dateutil.relativedelta import relativedelta

# custom functions
from src.cube4health.edpu.utils import _check_existence_dirs


# Root path of the project
ROOT_PATH = '/'.join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1])

SPATIAL_AGG_LIS = {
    'mun_res': 'municipality',
    'regsaude_449_res': 'health_region', 
    'uf_res': 'state'
}


def __format_lis_boundaries_shapefile(gdf: gpd.GeoDataFrame, 
                                      file_path: str, 
                                      agg: str) -> gpd.GeoDataFrame:
    """
        Format the boundaries shapefile.

    Parameters
    ----------
        gdf : gpd.GeoDataFrame,
            The GeoDataFrame that contains the boundaries.
        file_path : str,
            The path of the boundaries shapefile.
        agg : str,
            The aggregation of the boundaries.

    Returns
    ----------
        A GeoDataFrame that contains the formatted boundaries.
    """
    agg = agg.lower()
    aggs_allowed = SPATIAL_AGG_LIS.values()

    if agg not in aggs_allowed:
        raise ValueError(f'The agg parameters must be one of {aggs_allowed}')

    if agg == 'municipality':
        if '.shp' not in file_path:
            file_path = glob.glob(os.path.join(file_path, '2010*.shp'))[0]
        old_gdf = gpd.read_file(file_path, encoding='utf-8')
        for _, row in gdf.iterrows():
            condition = old_gdf['CD_GEOCODM'] == row['CD_MUN']
            for idx in old_gdf.index[condition]:
                old_gdf.at[idx, 'NM_MUNICIP'] = row['NM_MUN']
                old_gdf.at[idx, 'geometry'] = row['geometry']
        old_gdf = old_gdf.rename(columns={"cod6": "GEOCODE", 
                                          "NM_MUNICIP": "NAME", 
                                          "CD_GEOCODM": "CD_MUN"})
        gdf = old_gdf.copy()

    elif agg == 'state':
        gdf = gdf.rename(columns={"CD_GEOCODU": "GEOCODE", "NM_ESTADO": "NAME"})
    else:
        if '.csv' not in file_path:
            file_path = glob.glob(os.path.join(file_path, '*.csv'))[0]
        df_sus = pd.read_csv(file_path)
        gdf_columns = gdf.columns
        if 'codigo_reg' in gdf_columns and 'nome_regia' in gdf_columns:
            gdf = gdf.rename(columns={"codigo_reg": "GEOCODE", "nome_regia": "NAME"})
    return gdf[['GEOCODE', 'NAME', 'geometry', 'CD_MUN']]


def create_LIS_boundaries_shp(agg: str, 
                              input_path: Optional[str]= None) -> str:
    """
        Create/update the boundaries of the shape files used for the spatial aggregation
        of LIS datasets.

    Parameters
    ----------
        agg : str,
            Spatial aggregation value.
        input_path : Optional[str], default value is None.
            Path of the shapefile to update.

    Returns
    -------
        A string that contains the path of the shapefile created.
    """
    AGG_VALUES = SPATIAL_AGG_LIS.values()
    agg = agg.lower()

    if not agg in AGG_VALUES:
        raise Exception(f"Insert a valid value for agg parameter: {(', ').join(AGG_VALUES)}!")
    if not input_path:
        input_path = os.path.join(ROOT_PATH,'shp_malhas/default_grid', agg)
    temp_path = os.path.join(input_path, 'temp')

    _check_existence_dirs(paths=[input_path, temp_path])

    if agg != 'health_region':
        gpds = []
        ufs = ['ac', 'al', 'am', 'ap', 'ba', 'ce', 'df', 
               'es', 'go', 'ma', 'mg', 'ms', 'mt', 'pa', 
               'pb', 'pe', 'pi', 'pr', 'rj', 'rn', 'ro', 
               'rr', 'rs', 'sc', 'se', 'sp', 'to']

        if agg == 'municipality':
            print("\nSHAPEFILE OF THE MUNICIPALITY")
        else:
            print("\nSHAPEFILE OF THE STATE")

        files_folder = os.listdir(temp_path)
        if files_folder:
            for file in files_folder:
                files_to_remove = os.path.join(temp_path, file)
                if os.path.isfile(files_to_remove):
                    os.remove(files_to_remove)

        agg_ibge = '_unidades_da_federacao' if agg.lower() == 'state' else '_municipios'

        # FUNCTION TO CREATE MUNICIPALITY GRID FROM 2022
        exception = True
        zip_file = f"BR_Municipios_2022.zip"
        ibge_ftp = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/" \
                   f"malhas_municipais/municipio_2022/Brasil/BR/{zip_file}"
        zip_path = os.path.join(temp_path, zip_file)

        while exception:
            try:
                print()
                print(f"PROGRESS BAR OF {zip_path}")
                subprocess.run(["curl", "--insecure", "--progress-bar", "-o", zip_path, ibge_ftp], 
                                check=True, stdout=False)
                print()
                exception = False
            except Exception as exc:
                print(f"Download falhou: {str(exc)}. Tentando novamente...")
                exception = True

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_path)
        files = glob.glob(os.path.join(temp_path, '*.shp'))

        for file in files:
            gpds.append(gpd.read_file(file))
        br_gdf = gpd.GeoDataFrame(pd.concat(gpds))

        for file in os.listdir(temp_path):
            os.remove(os.path.join(temp_path, file))
        # FUNCTION TO CREATE MUNICIPALITY GRID FROM 2010
        #filename = f'BR_{agg}_2010.shp'
        # FUNCTION TO CREATE MUNICIPALITY GRID FROM 2022
        filename = f'BR_{agg}_2022.shp'
        if filename in os.listdir(input_path):
            os.remove(os.path.join(input_path, filename))
        br_gdf = __format_lis_boundaries_shapefile(gdf=br_gdf, file_path=input_path, agg=agg)
    else:
        print("\nSHAPEFILE OF THE HEALTH REGION")
        br_gdf = gpd.read_file(glob.glob(os.path.join(input_path, '*.shp'))[0])
        br_gdf = __format_lis_boundaries_shapefile(gdf=br_gdf, file_path=input_path, agg=agg)
        filename = f'BR_{agg}.shp'
        print("...DONE")

    output_file = os.path.join(input_path, filename)
    br_gdf.to_file(output_file, driver='ESRI Shapefile')
    return output_file

