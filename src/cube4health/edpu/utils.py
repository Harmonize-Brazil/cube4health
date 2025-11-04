# inbuilt libraries
import os
import re
import glob
import json
import shlex
import subprocess
from datetime import datetime
from typing import (
    Dict,
    List,
    Tuple,
    Union,
    Optional
)

# third-party libraries
import stat
import docker
import numpy as np
import geopandas as gpd
import shapely
from tqdm import tqdm
from shapely import geometry
from paramiko import SSHClient
from contextlib import closing
from rasterio import (
    open as rasterio_open,
    features,
    warp
)
from psycopg2 import (
    sql,
    connect
)
from psycopg2.errors import (
    ProgrammingError,
    IntegrityError,
    Error
)
from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor
)
from jsonpath_rw import jsonpath, parse


def connect_ssh(hostname: str, 
                username: str, 
                password: str, 
                port: Optional[int]=22) -> Tuple[bool, Union[str, SSHClient]]:
    """
    Connect to a remote server using SSH.

    Parameters
    ----------
        hostname : str
            Hostname of the remote server.
        username : str
            Username to connect to the remote server.
        password : str
            Password to connect to the remote server.
        port : int
            Port to connect to the remote server. Default value is 22.

    Returns
    -------
        A tuple containing a boolean value indicating if the connection was successful
        and a string or SSHClient object depending on the success of the connection.
    """
    ssh = SSHClient()
    ssh.load_system_host_keys()
    try:
        ssh.connect(hostname, 
                    port=port, 
                    username=username, 
                    password=password)
        return True, ssh
    except:
        return False,  f"\nUnable to connect to {hostname}"


def check_existence_remote_path(ssh: SSHClient,
                                remote_path: str) -> bool:
    """
        Check if a remote path exists.

    Parameters
    ----------
        ssh : SSHClient
            SSH client object.
        remote_path : str
            Remote path to check.

    Returns
    -------
        Boolean value indicating if the remote path exists.
    """
    with closing(ssh.open_sftp()) as sftp:
        sftp.chdir(remote_path)
        stdin, stdout, stderr = ssh.exec_command('ls {0}'.format(remote_path))

        return True if stdout.channel.recv_exit_status() == 0 else False


def files_ssh(ssh: SSHClient, method: str, local_path: str, 
              remote_path: str, filename: str) -> bool:
    """
    Send or retrieve files from local path to remote path, or delete files remotely.

    Parameters
    ----------
    ssh : SSHClient
        SSH client object.
    method : str
        Method to be used: 'get' for download, 'put' for upload, 'delete' for removing a file.
    local_path : str
        Local path where the file is located or where it will be stored.
    remote_path : str
        Remote path where the file will be sent or retrieved from.
    filename : str
        Name of the file to be sent, retrieved, or deleted.

    Returns
    -------
    bool
        Boolean value indicating if the operation was successful.
    """
    with closing(ssh.open_sftp()) as sftp:
        path = ''
        for directory in remote_path.split('/'):
            if directory:
                path = f'{path}/{directory}' if path else f'/{directory}'
                try:
                    sftp.stat(path)
                except FileNotFoundError:
                    sftp.mkdir(path)
        try:
            sftp.chdir(remote_path)
        except FileNotFoundError:
            return False

        try:
            os.chdir(local_path)
        except FileNotFoundError:
            return False

        try:
            if method == "get":
                sftp.get(filename, filename)
            elif method == "put":
                sftp.put(filename, filename)
            elif method == "delete":
                sftp.remove(filename)

            stdin, stdout, stderr = ssh.exec_command(f'chmod -R 777 {os.path.join(remote_path, filename)}')
            stdout.channel.recv_exit_status()
            return True

        except (FileNotFoundError, PermissionError, Exception) as e:
            return False


def send_files_ssh(ssh: SSHClient,
                   paths: List[Dict[str, List[str]]]) -> bool:
    """
        Send files from local path to remote path.

    Parameters
    ----------
        ssh : SSHClient
            SSH client object.
        paths : List[Dict[str, List[str]]]
            List of paths to send to the remote server.

    Returns
    -------
    
        Boolean value indicating if the file was sent.
    """

    def download_file(ssh: SSHClient, 
                      local_file: str, 
                      remote_path: str) -> bool:
        """
            Download file from local path to remote path.

        Parameters
        ----------
            ssh : SSHClient
                SSH client object.
            local_file : str
                Local path where the file will be sent.
            remote_path : str
                Remote path where the file will be sent.

        Returns
        -------
            Boolean value indicating if the file was sent.
        """
        if os.path.isfile(local_file):
            response = files_ssh(
                ssh=ssh,
                method='put',
                local_path=os.path.dirname(local_file),
                remote_path=remote_path,
                filename=os.path.basename(local_file)
            )
            return response

    all_saved = []
    total_files = sum(len(files_in_dir) for path in paths for _, _, files_in_dir in os.walk(path[0]))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        with tqdm(total=total_files, desc="Enviando arquivos", unit="file") as progress_bar:
            for path in paths:
                local, remote = path
                for root, _, files_in_dir in os.walk(local):
                    for file in files_in_dir:
                        local_file = os.path.join(root, file)
                        remote_path = os.path.dirname("/".join([remote, os.path.relpath(local_file, local)]))

                        if os.path.isfile(local_file):
                            future = executor.submit(download_file, ssh, local_file, remote_path)
                            while not future.result():
                                future = executor.submit(download_file, ssh, local_file, remote_path)
                                print(f"Arquivo {local_file} reenviado.")
                            futures.append(future)

            for future in futures:
                try:
                    response = future.result()
                    if response:
                        all_saved.append(response)
                    progress_bar.update(1)
                except Exception as e:
                    print(f"Erro ao enviar arquivo: {e}")

    return all(all_saved)


def _get_container_db(name: str = 'postgis') -> docker.models.containers.Container:
    """
        Get the container where the database is hosted. It searches for the container called 'postgis'.

    Parameters
    ----------
        name : str, default value is 'postgis'
            The name of the container where the database is hosted.

    Returns
    ----------
        A container object.
    """
    client = docker.from_env()
    containers = client.containers.list()
    container = None
    for c in containers:
        if name in c.name:
            container = client.containers.get(c.name)
    client.close()
    return container


def get_ip_container_db(name: str = 'postgis', 
                        platform: str = 'bdc_net') -> str:
    """
        Get the IP address of the container where the database is hosted.

    Parameters
    ----------
        name : str, default value is 'postgis'
            The name of the container where the database is hosted.
        platform : str, default value is 'bdc_net'
            The platform of the container where the database is hosted.

    Returns
    ----------
        A string that contains the IP address of the container where the database is hosted.
    """
    # CONTAINER_DB is a constant value that stores an container object.
    container_db = _get_container_db(name=name)

    # IP_CONTAINER_DB is a constant value that stores an IP from database container.
    ip_container_db = container_db.attrs['NetworkSettings']['Networks'][platform]['Gateway']

    return ip_container_db


def get_ports_container_db(name: str = 'postgis') -> str:
    """
        Get the ports of the container where the database is hosted.

    Parameters
    ----------
        name : str, default value is 'postgis'
            The name of the container where the database is hosted.

    Returns
    ----------
        A string that contains the ports of the container where the database is hosted.
    """
    # CONTAINER_DB is a constant value that stores an container object.
    CONTAINER_DB = _get_container_db(name=name)

    # PORTS_CONTAINER_DB is a constant value that stores the ports of this container
    PORTS_CONTAINER_DB = list(CONTAINER_DB.attrs['NetworkSettings']['Ports'].keys())[0].split('/')[0]

    return PORTS_CONTAINER_DB


def execute_command(command:str) -> None:
    """
        Execute a command in the terminal.

    Parameters
    ----------
        command : str
            Command to execute in the terminal.

    Returns
    -------
        None 
    """
    subprocess.run(command, shell=True, check=True)


def _check_database_existence(db_name: str, 
                              user: Optional[str]='postgres', 
                              password: Optional[str]='postgres', 
                              host: Optional[str]='localhost', 
                              port: Optional[str]='5432',) -> bool:
    """
        Check if a database exists.

    Parameters
    ----------
        db_name : str
            The name of the database.
        user : Optional[str], default value is 'postgres'
            The user of the database.
        password : Optional[str], default value is 'postgres'
            The password of the database.
        host : Optional[str], default value is 'localhost'
            The host of the database.
        port : Optional[str], default value is '5432'
            The port of the database.

    Returns
    -------
        Boolean value indicating if the database exists.
    """
    try:
        connection = connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        connection.autocommit = True
        cursor = connection.cursor()

        query = sql.SQL("SELECT 1 FROM pg_database WHERE datname = {}").format(sql.Literal(db_name))
        cursor.execute(query)

        exists = cursor.fetchone() is not None
        cursor.close()
        connection.close()
        return exists

    except Error as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return False


def get_round_value(gdf: gpd.GeoDataFrame, 
                    column_name: str = 'vl', 
                    only_round: bool = False) -> Union[Tuple[str, float, float, int], int]:
    """
    Rounds a point number of a column from a GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The GeoDataFrame that contains the column to be rounded.
    column_name : str, optional
        The column name to be rounded. Default is 'vl'.
    only_round : bool, optional
        If True, returns only the number of decimal places to round.
        If False, returns a tuple containing the column name, minimum value,
        interval value, and number of decimal places.

    Returns
    -------
    Union[int, Tuple[str, float, float, int]]
        If `only_round` is True:
            - An integer indicating the number of decimal places to round.

        If `only_round` is False:
            - A tuple containing:
                - column_name (str): The name of the column.
                - min_value (float): The minimum value in the column.
                - interval (float): The interval value.
                - decimals (int): Number of decimal places to round.
    """
    try:
        by_columns = gdf.filter(like=column_name, axis=1).astype('float')
        column_name = by_columns.columns[0]
        min_value = by_columns.min().min()
        max_value = by_columns.max().max()
        interval = (max_value - min_value) / 5

        if max_value > 0 and max_value < 1:
            round_value = 4
        else:
            round_value = 2
        if only_round:
            return round_value
        return column_name, min_value, interval, round_value
    except Exception as err:
        return {
            "message": "Error: Verify the column name informed!"
        }


def _check_existence_dirs(paths: List[str]) -> None:
    """
        Check the existence of directories.

    Parameters
    ----------
        paths : List[str]
            The directories path.

    Returns
    -------
            None
    """
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)


def raster_convexhull(imagepath: str, 
                      epsg='EPSG:4326') -> geometry.Polygon:
    """
        Get the convex hull of a raster image footprint.

    Parameters
    ----------
        imagepath : str 
            Path to the image file.
        epsg : str
            Target EPSG code for geometry.

    Returns
    -------
        shapely.geometry.Polygon: Convex hull of the raster footprint.
    """
    with rasterio_open(imagepath) as dataset:
        # Read raster data, masking nodata values
        data = dataset.read(1, masked=True)
        # Create mask, where 1 represents valid data and 0 represents nodata
        mask = np.invert(data.mask).astype(np.uint8)

        geoms = []
        res = {'val': []}
        for geom, val in features.shapes(mask, 
                                         mask=mask, 
                                         transform=dataset.transform):
            geom = warp.transform_geom(dataset.crs, epsg, geom)
            res['val'].append(val)
            # Convert transformed geometry to Shapely object
            geoms.append(shapely.geometry.shape(geom))

        if not geoms:
            # No geometries extracted
            return None

        if len(geoms) == 1:
            # Only one geometry extracted, return it directly
            return geoms[0]

        # Create MultiPolygon from extracted geometries
        multi_polygons = shapely.geometry.MultiPolygon(geoms)
        # Compute convex hull
        convex_hull = multi_polygons.convex_hull

        return convex_hull


def clean_raster_directory(path: str, 
                           conn:Optional[SSHClient]=None) -> bool:
    """
        Clean the raster directory.

    Parameters
    ----------
        path : str
            The directory path.

    Returns
    -------
        True if the directory is empty. False otherwise.
    """
    files_to_remove = []
    files_to_remove.extend(glob.glob(f'{path}/*'))

    if conn:
        extensions = ('.properties', 'sample_image.dat')
        for file in files_to_remove:
            if os.path.isfile(file) and (file.endswith(extensions) or os.path.basename(path) in file):
                os.remove(file)

        stdin, stdout, stderr = conn.exec_command(f'find {path} -type f')
        paths = stdout.read().decode().splitlines()
        if not [file for extension in extensions for file in paths if extension in os.path.basename(file)]:
            return True
    else:
        for file in files_to_remove:
            if os.path.isfile(file) and not file.endswith('.tif') and not file.endswith('.png'):
                os.remove(file)
        if not [arquivo for arquivo in os.listdir(path) if os.path.isfile(os.path.join(path, arquivo))]:
            return True

    return False


def get_time_list_from_data(path: str, 
                            time_regex: str, 
                            is_vector: Optional[bool]=False, 
                            conn:Optional[SSHClient]=None) -> List[str]:
    """
        Get time list from data.

    Parameters
    ----------
        path : str
            The directory path.
        time_regex : str
            The time regex.

    Returns
    -------
        A list with the time.
    """

    def get_dates_from_filenames(paths: List[str], 
                                 time_regex: str, 
                                 is_vector: Optional[bool]=False) -> List[str]:
        """
            Get dates from filenames.

        Parameters
        ----------
            paths : List[str]
                List of paths.
            time_regex : str
                Time regex.
            is_vector : bool, default value is False
                The type of layer.

        Returns
        -------
            A list with the dates.

        """

        pattern = re.compile(r'(' + time_regex.split('=')[1]  + ')')
        date_formats = [
            '%Y%m%d',          # 20100905
            '%Y-%m-%d',        # 2010-09-05
            '%Y%m%dT%H%M%S',   # 20100905T120000
            '%Y-%m-%dT%H:%M:%S',  # 2010-09-05T12:00:00
            '%Y%m%d_%Y%m%d',
            '%Y-%m-%d_%Y-%m-%d',
            '%Y%m%dT%H%M%S_%Y%m%dT%H%M%S',
            '%Y-%m-%dT%H:%M:%S_%Y-%m-%dT%H:%M:%S',
        ]
        time_list = []

        for file in tqdm(paths):
            if '.tif' in file or ('.shp' in file and is_vector):
                matches = pattern.findall(file)
                # print('matches: ', matches)
                if matches:
                    date_str = matches[0].split('_')[0]
                    # print('date_str: ', date_str)

                    # Tenta converter a string usando os formatos disponíveis
                    time = None
                    for fmt in date_formats:
                        try:
                            time = datetime.strptime(date_str, fmt)
                            break  # Para o loop se encontrar um formato válido
                        except ValueError:
                            continue

                    if time:
                        # Formata a saída com o formato padrão
                        final_format = '%Y-%m-%dT%H:%M:%S.000Z' if 'T' in date_str else '%Y-%m-%d'
                        time_str = time.strftime(final_format)

                        if time_str not in time_list:
                            time_list.append(time_str)
                    else:
                        print(f"Aviso: Nenhum formato válido encontrado para '{date_str}' no arquivo {file}")

        '''print('\nGETTING TIME LIST FROM DATA...')
        for file in tqdm(paths):
            if '.tif' in file or ('.shp' in file and is_vector):
                try:
                    final_format = '%Y-%m-%d'
                    print('Date: ', pattern.search(file).group(0))
                    time = datetime.strptime(pattern.search(file).group(0), '%Y%m%d')
                except:
                    final_format = '%Y-%m-%dT%H:%M:%S.000Z'
                    print(pattern.search(file).group(0))
                    time = datetime.strptime(pattern.search(file).group(0), '%Y%m%dT%H%M%S')
                time = time.strftime(final_format)
                if not time in time_list:
                    time_list.append(time)'''

        return sorted(time_list)

    if conn:
        stdin, stdout, stderr = conn.exec_command('find {0} -type f'.format(path))
        paths = stdout.read().decode().splitlines()
    else:
        paths = [os.path.join(root, file) for path in glob.glob(path) for root, dirs, 
                                                                    files in os.walk(path) for file in files]
    return get_dates_from_filenames(paths=paths, time_regex=time_regex, is_vector=is_vector)


def modify_json(data: dict, 
                template: dict, 
                workspace: str,
                stac_url: str)-> dict:
    """
        Modify the json template.

    Parameters
    ----------
        data : dict,
            The json with updated values.
        template : dict,
            The json template.
        stac_url : str, default value is 'http://localhost:8080/'
            The STAC URL.

    Returns
    -------
        The json template with updated values.
    """
    jsonpath_expr = parse('*.$..*')
    data = [(str(match.full_path), match.value) for match in jsonpath_expr.find(data)]
    keys, values = zip(*data)
    keys, values = list(keys), list(values)
    new_keys, duplicated_indexes = [], []

    for index, key in enumerate(keys):
        if key not in new_keys:
            new_keys.append(key)
        else:
            duplicated_indexes.append(index)

    for index in sorted(duplicated_indexes, reverse=True):
        del keys[index]
        del values[index]
    data = dict(zip(keys, values))

    keys = []
    for key, value in data.items():
        if isinstance(value, dict):
            keys.append(key)
    for index in keys:
        del data[index]

    for key, values in data.items():
        keys = key.split('.')
        current = template
        for sub_key in keys[:-1]:
            if sub_key.startswith('[') and sub_key.endswith(']'):
                sub_key = int(sub_key[1:-1])
                current = current[sub_key]
            else:
                current = current.get(sub_key, {})
        current[keys[-1]] = values

    template['metadata']['wms']['layerName'] = f'{workspace}:{template["name"]}'
    template['metadata']['sources'][0]['name'] = f'{template["name"]}'
    template['metadata']['sources'][0]['stacUri'] = os.path.join(stac_url, 
                                                                 f'{template["name"]}-{template["version"]}')
    template['metadata']['datacite']['id'] = f'{template["name"]}'
    template['metadata']['datacite']['titles']['title'] = f'{template["name"]}'
    template['metadata']['datacite']['descriptions'][0]['description'] = f'{template["description"]}'

    return template

