# inbuilt libraries
import os
import re
import json
import glob
import sys
import getpass
import subprocess
from datetime import datetime
from typing import (
    Dict,
    List,
    Union,
    Optional
)

# third-party libraries
import geopandas as gpd
from tqdm import tqdm
from flask import Flask
from pathlib import Path
from itertools import groupby
from geoalchemy2.shape import from_shape
from bdc_catalog import BDCCatalog
from bdc_catalog.cli import load_data
from shapely.geometry import (
    MultiPolygon,
    Polygon
)
from bdc_catalog.models import (
    db,
    Item,
    Collection,
    MimeType
)

# custom functions
from .utils import (
    raster_convexhull,
    modify_json,
    _check_database_existence,
    files_ssh,
    connect_ssh,
    execute_command,
    get_ip_container_db
)


ROOT_PATH = '/'.join(os.path.dirname(os.path.abspath(__file__)).split('/'))
KEYWORDS = [
    'health',
    'climate',
    'drone'
]

GEOSERVER_FILES = [
    'timeregex.properties',
    'sample_image.dat',
    'indexer.properties'
]

POSSIBLE_DATE_PATTERNS = [
    '(\d{8}T\d{6}_\d{8}T\d{6})', 
    '(\d{8}T\d{6})', 
    '(\d{8}_\d{8})', 
    '(\d{8})',
]

DEFAULT_MIME_TYPES = [
     'image/png',
     'image/tiff',
     'image/tiff; application=geotiff',
     'image/tiff; application=geotiff; profile=cloud-optimized',
     'text/plain',
     'text/html',
     'application/json',
     'application/xml',
     'application/x-tar',
     'application/zip',
     'application/gzip',
     'image/jp2; profile=cloud-optimized',
     'image/jp2'
]


class STAC:

    def __init__(
        self,
        service_url: str,
        hostname: str = "localhost", # ip for server with collections files, default localhost
        db_name: str = 'bdc', # default name of database
        port: int = 5432, # default port
        pg_username: str = 'postgres', # default username
        pg_password: str = 'postgres' # default password
    ):
        self.service_url = service_url
        self.hostname = hostname #if hostname != 'localhost' else get_ip_container_db(name='bdc-stac')
        self._pg_username = pg_username
        #self._pg_password = getpass.getpass('\nEnter database password: ')
        self._pg_password = pg_password

        if hostname != 'localhost':
            print()
            print('-'*120)
            print('To publish the data metadata available on the remote host, we need to enable an SSH '\
                   'connection o list the items in the STAC collections.\nPlease enter with your '\
                   'private information:\n')

            for try_connect in range(1, 4): 
                # If the hostname is not localhost, it will ask for the username and password
                self._hostusername = input('Enter host username: ')
                self._hostpassword = getpass.getpass('Enter host password: ')

                connected, connection = connect_ssh(hostname=self.hostname, username=self._hostusername, 
                                                    password=self._hostpassword)

                if connected:
                    self.connection = connection
                    break
                print(f'{connection}, \ntry {try_connect}/3\n')
            else:
                print('-'*120)
                print(f'As you have reached the maximum number of login attempts, you need to run the script again.')
                print('-'*120)
                print()
                sys.exit() 

        self.db_uri = f'postgresql://{self._pg_username}:{self._pg_password}@{hostname}:{port}/{db_name}'

        if not _check_database_existence(db_name):
            try:
                execute_command(f'export SQLALCHEMY_DATABASE_URI="{self.db_uri}"')
                execute_command('bdc-db db init')
                execute_command('bdc-db db create-namespaces')
                execute_command('bdc-db db create-extension-postgis')
                execute_command('bdc-db db create-schema')
                execute_command('bdc-db db create-triggers')
            except Exception as e:
                pass

        # Try to run the Flask app. If it fails, it means that there is alerady a Flask app running and
        # the script uses that app context.
        try: 
            self.app = Flask(__name__)
            self.app.config['SQLALCHEMY_DATABASE_URI'] = self.db_uri
            self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            BDCCatalog(self.app)
        except:
            with self.app.app_context():
                pass


    @staticmethod
    def format_date(date: str) -> str:
        """
            Format the date

            Parameters
            ----------
                date : str,
                    The date to be formatted

            Returns
            -------
                The formatted date
        """
        try:
            d = datetime.strftime(datetime.strptime(date, '%Y%m%dT%H%M%S'), '%Y-%m-%dT%H:%M:%S')
        except:
            d = datetime.strftime(datetime.strptime(date, '%Y%m%d'), '%Y-%m-%d') + 'T00:00:00'
        return d


    def close_connection(self) -> str:
        """
        Close the connection

        Returns
        -------
            The message that the connection was closed
        """
        self.connection.close()
        return 'Connection closed'


    def publish_collection(self, 
                           data: dict, 
                           workspace: str,
                           template: str, 
                           items_path: str, 
                           asset_names: Dict[str, str], 
                           root_data_path: Optional[str]=None, 
                           additional_path: Optional[str] = None,
                           footprint: Union[List[int], Dict[str, List[int]]] = None, 
                           output_file: Optional[str] = None, 
                           del_output_file: Optional[bool] = True) -> Union[int, str]:
        """
            Update the the collection's metadata JSON file template

            Parameters
            -----------
                data : dict,
                    The collection's metadata JSON file
                template : str,
                    The collection's template
                output_file : str,
                    The path where the collection's metadata JSON file will be created.
                del_output_file : bool, default value is True,
                    If True, delete the output_file.
                workspace : Optional[str], default = 'bdc_lcc',
                    The name of geoserver workspace.
                items_path: str,
                    The directory path where the items are.
                asset_names: Dict[str, str],
                    The asset names. The key of the dictionary is the asset name and the value is the asset extension.
                root_data_path: str,
                    The data path where nginx is running.
                footprint: Union[List[int], Dict[str, List[int]]], default value is None,
                    The footprint of the items. The user can inform the footprint in a list or in a dictionary with footprints.
                    If the footprint is in a dictionary, the key of the dictionary is the item name and the value is the footprint.
                    If the footprint is in a list, the footprint is a list of coordinates and it will be used to all items.

            Returns
            -------
                The collection id or a string with the error.
        """
        if not all(key in data.keys() for key in ['name', 'version']):
            return "Collection name and version must be informed!"
        try:
            with self.app.app_context():
                mimetypes = [mime.name for mime in MimeType.query().all()]
            if 'bands' in data.keys():
                data_mimetypes = [band['mime_type'] for band in data['bands']]
                data_mimetypes.extend(DEFAULT_MIME_TYPES)
                data_mimetypes = list(set(data_mimetypes))
                for mimetype_name in data_mimetypes:
                    if not mimetype_name in mimetypes:
                        with self.app.app_context():
                            with db.session.begin_nested():
                                resolution = MimeType(name=mimetype_name)
                                db.session.add(resolution)
                            db.session.commit()
        except Exception as e:
            print(e)
            return "Error insert or query MimeType"
        try:
            with self.app.app_context():
                collection_id = Collection.get_by_id(f"{data['name']}-{data['version']}").id

                if collection_id:
                    print("The collection provided already exists!")
                    return collection_id
        except Exception as e:
            if '.json' not in os.path.basename(template) and template.lower() in KEYWORDS:
                template = os.path.join(ROOT_PATH, f'templates/jsons/{template.lower()}.json')
            try:
                template = json.load(open(template))
            except FileNotFoundError as e:
                return "File not found"
        
            if data is not None:
                print("\nUpdating the collection's metadata JSON file...")
                new_collection = modify_json(data=data, 
                                             template=template, 
                                             stac_url=self.service_url,
                                             workspace=workspace)
                print("...Done")
            else:
                return "The 'data' parameter is required!", False

            if not del_output_file:
                if not output_file:
                    output_file = os.path.join(ROOT_PATH, f'templates/jsons/{data["name"]}.json')
            else:
                output_file = os.path.join(ROOT_PATH, 'templates/jsons/temporary_collection.json')

            items = self.browse_items(path=items_path, root_data_path=root_data_path, 
                                      asset_names=asset_names, additional_path=additional_path)
            new_collection.update(
                {'items': items}
            )

            with open(output_file, 'w') as json_file:
                json.dump(obj=template, fp=json_file, indent=4)
            cmd = f'export SQLALCHEMY_DATABASE_URI={self.db_uri} '\
                  '&& bdc-catalog load-data --ifile ' + output_file
            subprocess.run(cmd, shell=True)

        try:
            with self.app.app_context():
                collection_id = Collection.get_by_id(f"{data['name']}-{data['version']}").id
                if collection_id:
                    if del_output_file:
                        os.remove(output_file)
                    if hasattr(self, 'connection'):
                        self.connection.close()
                    return collection_id
        except Exception as e:
            return f"Error getting collection by id {str(e)}"


    def browse_items(self, path: str, asset_names: Dict[str, str], 
                     root_data_path: Optional[str]=None,
                     footprint: Union[List[int], Dict[str, List[int]]]=None, **kwargs) -> Union[List[dict], str]:
        """
        Browse the items directory.

        Parameters
        ----------
        path : str
            The directory path.
        asset_names : Dict[str, str]
            The asset names. The key of the dictionary is the asset name, and the value is the asset extension.
        root_data_path : str
            The data path where nginx is running.
        footprint : Union[List[int], Dict[str, List[int]]], optional
            The footprint of the items. The user can provide the footprint as a list or as a dictionary. If a dictionary, the key is the item name, and the value is the footprint. If a list, it represents coordinates and will be used for all items.

        Returns
        -------
        Union[List[dict], str]
            A list of items. Each item is a dictionary with the following keys:

            - `name` (str): The name of the item.
            - `collection_id` (int): The collection ID.
            - `start_date` (datetime): The start date of the item.
            - `end_date` (datetime): The end date of the item.
            - `footprint` (Polygon): The footprint of the item.
            - `assets` (dict): A dictionary with the assets of the item.
            - `cloud_cover` (int): The cloud cover of the item.
            - `srid` (int): The SRID of the item.

            If the return value is a string, it indicates an error.
        """

        items = []

        additional_path = kwargs.get('additional_path') if 'additional_path' in kwargs.keys() else None

        # GETTING ALL ASSETS PATHS
        if hasattr(self, 'connection'):
            stdin, stdout, stderr = self.connection.exec_command('find {0} -type f'.format(path))
            assets_paths = stdout.read().decode().splitlines()
        else:
            if '*' in path:
                matching_files = glob.glob(os.path.join(path))
                assets_paths = [os.path.join(root, file) for path in matching_files for root, dirs, files 
                                in os.walk(path) for file in files 
                                if os.path.isfile(os.path.join(root, file))]
            else:
                assets_paths = [os.path.join(root, file) for root, dirs, files in os.walk(path) for file in files 
                                if os.path.isfile(os.path.join(root, file))]
        base_folder = os.path.basename(path)
        assets_paths = [asset for asset in assets_paths if not base_folder == os.path.basename(asset).split('.')[0]
                                                                and os.path.basename(asset) not in GEOSERVER_FILES]

        item_name = lambda x: os.path.splitext(os.path.basename(x))[0]
        items_assets = groupby(sorted(assets_paths), key=item_name) # items_assets is a TUPLE (ITEM NAME, LIST OF ASSETS PATHS
                                                            # -> itertools.groupby)
        items_assets_ex = [
            (name, list(group))
            for name, group in groupby(sorted(assets_paths, key=item_name), key=item_name)
        ]

        # with open('items_assets.json', 'w', encoding='utf-8') as arq:
        #     json.dump({'items_assets': items_assets_ex}, arq, indent=4, ensure_ascii=False)

        for name, paths in tqdm(items_assets, desc="Getting items..."):
            assets = {}
            paths = list(paths)

            # GETTING START_DATE/END_DATE
            for date_pattern in POSSIBLE_DATE_PATTERNS:
                pattern = re.compile(r'{pattern}'.format(pattern=date_pattern))
                date = pattern.search(name)
                if date:
                    break
            else:
                return "The format of the item name is not valid. The date is missing or is not in acceptable format."
            dates = [self.format_date(d) for d in date.group(1).split('_')]

            if len(dates) == 1:
                end_date = start_date = dates[0]
            else:
                start_date, end_date = dates

            if not footprint:
                all_conditions = any(path.endswith(('.tif', '.jp2', '.geojson')) for path in paths)
            else:
                all_conditions = True

            if all_conditions:
                # GETTING ASSETS OF EACH ITEM
                for asset in paths:
                    ref = None
                    href = Path(asset).relative_to(root_data_path)
                    suffix = href.suffix.lower()
                    is_raster = suffix in ('.tif', '.jp2')
                    is_geojson = suffix in ('.geojson',)

                    # GETTING BBOX AND FOOTPRINT FROM ITEM
                    if is_raster or is_geojson:
                        ref = asset
                        if not footprint:
                            if hasattr(self, 'connection'):
                                ref = os.getcwd()
                                files_ssh(ssh=self.connection, local_path=ref, 
                                        remote_path=asset.split(os.path.basename(asset))[0], 
                                        method='get', filename=href.name)
                                ref = os.path.join(ref, href.name)
                                href = Path(asset).relative_to(root_data_path)

                            if is_raster:
                                footprint_to_db = raster_convexhull(ref)
                            else:
                                gdf = gpd.read_file(ref)
                                footprint_to_db = MultiPolygon([gdf.unary_union.envelope]).convex_hull
                                gdf = None
                                if hasattr(self, 'connection'):
                                    os.remove(ref)
                        else:
                            if isinstance(footprint, list):
                                footprint_to_db = footprint
                            else:
                                footprint_to_db = footprint.get(name)
                            footprint_to_db = [MultiPolygon([Polygon(footprint_to_db)]).convex_hull]
                        bbox_to_db = footprint_to_db = [[list(coord) for coord in list(footprint_to_db.exterior.coords)]]

                    # GETTING ASSET VALUES
                    if suffix not in ['.shp', '.cpg', '.dbf', '.prj', '.shx']:
                        asset_name = asset_names.get(suffix)
                        asset_type = '' # SEARCH mime_type into DB
                        with self.app.app_context():
                            mimetypes = [mime.name.lower() for mime in MimeType.query().all()]
                        for mime in mimetypes:
                            suffix = href.suffix.lower()[1:]
                            if suffix in mime:
                                asset_type = mime
                                break
                            else:
                                if suffix == 'parquet':
                                    asset_type = 'application/octet-stream'
                                    break
                                if suffix == 'geojson':
                                    asset_type = 'application/geo+json'
                                    break

                        assets.update({
                            asset_name: {
                            'href': str(href) if not additional_path and root_data_path 
                                            else f'{additional_path}{str(asset)}',
                            'type': asset_type,
                            'roles': ["thumbnail"] if asset_name in ["thumbnail", "preview", "png", ".png"] else ["data"],
                            'created': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            'updated': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            }
                        })

                item = {
                    'name': name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'srid': kwargs.get('srid', 4326),
                    'is_available': kwargs.get('is_available', True),
                    'cloud_cover': kwargs.get('cloud_cover', 0),
                    'bbox': {
                        'type': 'Polygon',
                        'coordinates': bbox_to_db
                    },
                    'footprint': {
                        'type': 'Polygon',
                        'coordinates': footprint_to_db
                    }, 
                    'assets': assets
                }

                for key, value in kwargs.items():
                    if item.get(key) is None:
                        item.update({key: value})
                items.append(item)

                if hasattr(self, 'connection') and ref:
                    try:
                        os.remove(ref)
                    except Exception as e:
                        pass

        return items

