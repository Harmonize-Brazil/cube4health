# inbuilt libraries
import os
import re
import sys
import glob
import shutil
import getpass
import textwrap
import pkg_resources
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import (
    List, 
    Optional, 
    Union
)
from pathlib import Path
from requests.auth import HTTPBasicAuth

# third-party libraries
import requests
import geopandas as gpd
from tqdm import tqdm
from contextlib import closing
from geoserver.store import CoverageStore
from geoserver.catalog import (
    Catalog, 
    FailedRequestError, 
    ConflictingDataError
)
from geo.Geoserver import (
    Geoserver, 
    GeoserverException
)

# custom functions
from .utils import (
    files_ssh,
    connect_ssh, 
    get_time_list_from_data,
    check_existence_remote_path,
    get_round_value, 
    get_ip_container_db, 
    clean_raster_directory,
    _check_database_existence 
)

from .. import config #cube4health global variables



ROOT_PATH = '/'.join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1])


class GeoServer:
    """
    Attributes
    ----------
        service_url : str
            The URL for the GeoServer instance.
        workspace : str
            Workspace name to group similar layers.
        hostname : str
            Hostname for server with collections files. Default values is localhost.
        username : str
            Login name for session.
        store : str
            Store name to connects to a data source that contains raster or vector data.
        db_settings: Optional[dict] = None
            Database settings (name, user, schema and port)
    """

    def __init__(
        self, 
        service_url: str,
        workspace: str,
        hostname: str = "localhost",  # ip for server with collections files, default localhost
        username: str = "admin",  # default username during geoserver installation
        store: str = 'public', # default Store
        db_settings: Optional[dict] = None
    ):

        self.hostname = hostname if hostname != 'localhost' else get_ip_container_db()
        self._username = username
        self.service_url = service_url

        if hostname != 'localhost':

            print()
            print('-'*120)
            print('To publish layers available at the remote host, we need to enable an SSH '\
                   'connection to copy Geoserver configuration files.\nPlease enter with your '\
                   'private information:\n')


            for try_connect in range(1, 4): 
                # If the hostname is not localhost, it will ask for the username and password
                if config.ssh_username == None:
                    self._hostusername = input('Enter host username: ')
                    self._hostpassword = getpass.getpass('Enter host password: ')
                else:
                    self._hostusername = config.ssh_username
                    self._hostpassword = config.ssh_passwd

                connected, connection = connect_ssh(hostname=self.hostname, 
                                                    username=self._hostusername, 
                                                    password=self._hostpassword)

                if connected:
                    self.connection = connection
                    if config.ssh_username == None:
                        config.ssh_username = self._hostusername
                        config.ssh_passwd = self._hostpassword
                    break
                print(f'{connection}, \ntry {try_connect}/3\n')
            else:
                print('-'*120)
                print(f'As you have reached the maximum number of login attempts,'\
                      ' you need to run the script again.')
                print('-'*120)
                print()
                sys.exit() 

        for try_connect in range(1, 4):            
            if config.geoserver_passwd == None:
                self._password = getpass.getpass(f'\nEnter geoserver password: ')
            else:
                self._password = config.geoserver_passwd           

            try:
                self.geoserver = Geoserver(service_url, 
                                           username=username, 
                                           password=self._password)

                self.cat = Catalog(service_url=f'{os.path.join(service_url, "rest")}', 
                                   username=username,
                                   password=self._password)

                # Verifies if the geoserver password informed is correct
                status_geoserver = self.geoserver.get_status()                
                if status_geoserver:
                    if config.geoserver_passwd == None:
                        config.geoserver_passwd = self._password
                    break
            except Exception as e:
                print(e)
                print(f'\ntry {try_connect}/3\n')
        else:
                print('-'*120)
                print(f'As you have reached the maximum number of geoserver login attempts, '\
                      'you need to run the script again.')
                print('-'*120)
                print()
                sys.exit() 

        for try_connect in range(1, 4):
            
            self.db = db_settings.get('db', 'public')
            self.db_user = db_settings.get('user', 'postgres')
            self.db_port = db_settings.get('port', 5432)
            self.db_schema = db_settings.get('schema', 'postgres')

            if config.db_passwd == None:
                self.db_password = getpass.getpass(f'Enter password for database user ('+ self.db_user +'): ')
            else:
                self.db_password = config.db_passwd           

            status_db = _check_database_existence(self.db, self.db_user, self.db_password, self.hostname, self.db_port)
            if status_db:
                if config.db_passwd == None:
                    config.db_passwd = self.db_password
                break
            else:
                print(f'\ntry {try_connect}/3\n')
        else:
            print('-'*120)
            print(f'As you have reached the maximum number of database login attempts, '\
                    'you need to run the script again.')
            print('-'*120)
            print()
            sys.exit()
        
        self.store = store

        try:
            _ = self.geoserver.get_workspace(workspace=workspace) # Here verifies if the workspace 
                                                                  # exists in geoserver. If not, 
                                                                  # it will raise GeoserverException
                                                                  # and will be created. Because it, 
                                                                  # the return value 
                                                                  # of get_workspace isn't used.
        except GeoserverException:
            _ = self.create_workspace(workspace=workspace)

        self.workspace = workspace

    def get_username(self) -> str:
        """
            Get the GeoServer username

        Returns
        -------
            A string that contains the GeoServer username
        """
        return self._username


    def get_password(self) -> str:
        """
            Get the Geoserver password

        Returns
        -------
            A string that contains the Geoserver password
        """
        return self._password


    def create_workspace(self, workspace: str=None) -> bool:
        """
            Create a new workspace in geoserver. The geoserver workspace url will be same as 
            the name of the workspace.

        Parameters
        ----------
            workspace : str, default value is None.
                The name of workspace.

        Returns
        -------
            Booleand value that indicates if the workspace was created.
        """
        if not workspace:
            workspace = self.workspace

        max_request = 0
        ws_exists = False

        # Create workspace
        while not ws_exists:
            try:
                if self.geoserver.get_workspace(workspace=workspace):
                    ws_exists = True
            except Exception as e:
                try:
                    response = self.geoserver.create_workspace(workspace=workspace)
                    if response == 200:
                        if self.geoserver.get_workspace(workspace=workspace):
                            ws_exists = True
                except Exception as e:
                    max_request += 1
                    response = e
            if max_request == 5:
                raise ConnectionError(f"Error {response}")
        return ws_exists


    def create_feature_store(self,
                             workspace: Optional[str]=None, 
                             store: Optional[str]=None) -> bool:
        """
            Create a new feature store in geoserver.

        Parameters
        ----------
            workspace : str, default value is None.
                The name of workspace.
            store : str, default value is None.
                The name of Store.

        Returns
        -------
            Boolean value of existance of store.
        """
        if not workspace:
            workspace = self.workspace
        if not store:
            store = self.store

        max_request = 0

        db = self.db
        pg_schema = self.db_schema
        pg_username = self.db_user
        pg_password = self.db_password
        pg_port = self.db_port

        # Create workspace
        try:
            if self.geoserver.get_workspace(workspace=workspace):
                ws_exists = True 
        except GeoserverException:
            ws_exists = self.create_workspace()

        # Create feature store
        if ws_exists:
            store_exists = False

            while not store_exists:
                try:
                    # Verify if the feature store exists
                    if self.geoserver.get_datastore(store_name=store,
                                                    workspace=workspace):
                        store_exists = True
                except Exception as e:
                    # Create feature store
                    try:
                        # Host parameter varies depending on the execution mode (local or remote)
                        response = self.geoserver.create_featurestore(store_name=store, 
                                                                      workspace=workspace, 
                                                                      pg_password=pg_password, 
                                                                      pg_user=pg_username, 
                                                                      schema=pg_schema, 
                                                                      db=db,
                                                                      port=pg_port, 
                                                                      host=self.hostname)

                        # Verify if the feature store exists
                        if self.geoserver.get_datastore(store_name=store, 
                                                        workspace=workspace):
                            store_exists = True
                    except Exception as e:
                        # Try again to create feature store in case of error
                        max_request += 1
                        response = e
                # Raise error if maximum number of requests is reached
                if max_request == 5:
                    raise ConnectionError(f"Error {response}")

        return store_exists


    def publish_feature_data(self, 
                             layers: List[dict], 
                             time_regex: str,
                             attribute: str = "date", 
                             workspace: Optional[str]=None, 
                             store: Optional[str]=None,
                             dynamic_style: bool=False,
                             add_tile_cache: Optional[bool]=True) -> None:
        """
            Publish features in geoserver.

        Parameters
        ----------
            layers : list with dicts,
                A list that contains dicts with layers informations,  
                keys = (name, title, style, dates, bbox, path)
            time_regex : str
                The regex that matches the time of features.
            workspace : str, default value is None.
                The name of workspace.
            store : str, default value is None.
                The name of Store.
            dynamic_style : bool, default value is False
                Whether to use style that are created dynamically or not.
            add_tile_cache : bool, default value is True
                Whether to add a tile cache or not to the layer.

        Returns
        -------
            None
        """

        if not workspace:
            workspace = self.workspace
        if not store:
            store = self.store
        # if not schema:
        #     schema = self.schema

        create_style, create_store, store_exists = False, False, False
        pg_schema = self.db_schema

        # Create feature store
        try:
            if self.geoserver.get_datastore(store_name=store, 
                                            workspace=workspace):
                store_exists = True

        except GeoserverException as e:
            store_exists = self.create_feature_store(schema=pg_schema)

        # Publish feature layers
        if store_exists:
            # For each layer in the list of layers publish it
            for layer in layers:

                layer_name = layer['name']
                layer_title = layer['title']
                layer_style = layer['style']
                layer_folder = layer['path']

                # Publish layer
                try:
                    response = self.geoserver.publish_featurestore(workspace=workspace, 
                                                                   store_name=store,
                                                                   pg_table=layer_name, 
                                                                   title=layer_title)
                    # Publish style to layer
                    if response == 201:

                        # If style already exists, delete it and upload a new one. Otherwise 
                        # upload a new one.
                        try:
                            response = self.geoserver.get_style(style_name=layer_name, 
                                                                workspace=workspace)
                            if response:
                                response = self.geoserver.delete_style(style_name=layer_name, 
                                                                       workspace=workspace)
                                if response:
                                    create_style = True
                        except GeoserverException as e:
                            create_style = True

                        # Upload style
                        if create_style:
                            # print(layer_style)
                            response = self.geoserver.upload_style(path=layer_style, 
                                                                   workspace=workspace, 
                                                                   name=layer_name)

                            if response == 200:
                                response = self.geoserver.publish_style(layer_name=layer_name, 
                                                                        style_name=layer_name, 
                                                                        workspace=workspace)

                                # Publish time dimension to feature layer with style
                                if response == 200:
                                    print(f"Style {layer_name} uploaded with success!")
                                    response = self.geoserver.publish_time_dimension_to_layers(layer_name=layer_name, 
                                                                                               store_name=store, 
                                                                                               workspace=workspace,
                                                                                               attribute=attribute)

                                    # Add tile cache if add_tile_cache is True
                                    if response == 200 and add_tile_cache:
                                        response = self._add_tile_cache(name=layer_name, 
                                                                        path=layer_folder, 
                                                                        time_regex=time_regex, 
                                                                        is_vector=True)
                                        print(f"Layer {layer_name} uploaded with success!")

                                    # Delete style if dynamic style is True
                                    if dynamic_style:
                                        os.remove(layer_style)

                except Exception as e:
                    print('Error:', e)


    @staticmethod
    def create_health_feature_style(layer_name: str, 
                                    column_name: str, 
                                    gdf: gpd.GeoDataFrame,
                                    template_name: Optional[str]=None) -> str:
        """
            Create style for layer in geoserver.

        Parameters
        ----------
            layer_name : str,
                Name of the layer to which the style will be associated.
            column_name : str,
                Name of the data column that will be used to create ranges.
            gdf : gpd.GeoDataFrame,
                Layer GeoDataFrame.

        Returns
        -------
            The path of the style.
        """
        base_path = Path(__file__).parent
        template_name = template_name or 'health'

        # Caminho do template
        template = base_path / 'templates' / 'styles' / 'vector' / f'{template_name}.sld'

        if not template.exists():
            return "Error: Template not found!"
        
        # Definindo o caminho do arquivo de saída
        output = template.with_name(f'{layer_name}.sld')
        # print('output: ', output)

        # Caso especial para 'alert_level'
        if template_name == 'alert_level':
            shutil.copyfile(template, output)  # Copia o arquivo
            return str(output)  # Retorna o caminho do arquivo copiado como string

        # Caso geral: ler e processar como XML
        tree = ET.parse(template)  # Passar diretamente o Path sem conversão para string
        root = tree.getroot()

        try:
            column_name, min_value, interval, round_value = get_round_value(gdf=gdf, 
                                                                            column_name=column_name)
        except (KeyError, IndexError):
            return "Error: Some column name in the grid or tabular data is wrong!"

        for rule in root.iter("{http://www.opengis.net/sld}Rule"):
            name = rule.find("{http://www.opengis.net/sld}Name")
            title = rule.find("{http://www.opengis.net/sld}Title")

            number = int(name.text.split(" ")[-1])
            first_value = str(round(min_value + interval * (number - 1), round_value))
            second_value = str(round(min_value + interval * number, round_value))

            if number == 1 or number == 5:
                literal_element = rule.find(
                    ".//{http://www.opengis.net/ogc}Filter").find(".//{http://www.opengis.net/ogc}Literal")
                prop_name = rule.find(".//{http://www.opengis.net/ogc}Filter").find(
                    ".//{http://www.opengis.net/ogc}PropertyName")
                if number == 1:
                    new_title = f"{(' ').join(title.text.split(' ')[:-1])} {second_value}"
                    literal_element.text = second_value
                else:
                    new_title = f"{(' ').join(title.text.split(' ')[:-1])} {first_value}"
                    literal_element.text = first_value
                prop_name.text = column_name
            else:
                pieces = title.text.split()
                new_title = f"{pieces[0]} {first_value} {pieces[2]} {second_value}"
                literal_f_element = rule.find(".//{http://www.opengis.net/ogc}Filter").find(
                    ".//{http://www.opengis.net/ogc}PropertyIsGreaterThanOrEqualTo").findall("*")
                for child in literal_f_element:
                    if 'PropertyName' in child.tag:
                        child.text = column_name
                    else:
                        child.text = first_value

                literal_s_element = rule.find(".//{http://www.opengis.net/ogc}Filter").find(
                    ".//{http://www.opengis.net/ogc}PropertyIsLessThan").findall("*")

                for child in literal_s_element:
                    if 'PropertyName' in child.tag:
                        child.text = column_name
                    else:
                        child.text = second_value
            title.text = new_title
        
        # Cria diretório caso não exista
        output.parent.mkdir(parents=True, exist_ok=True)

        # Grava o arquivo de saída
        tree.write(output, encoding="utf-8", xml_declaration=True)
        return str(output)


    def make_thumbnail(self, 
                       url: str, 
                       layers: List[dict], 
                       time_regex: Optional[str]='regex=[0-9]{8}',
                       workspace: Optional[str]=None) -> None:
        """
            Make thumbnail from Layer.

        Parameters
        ----------
            url : str,
                The URL for the GeoServer instance.
            layers : list with dicts,
                A list that contains dicts with layers informations,  
                keys = (name, title, style, bbox, path)
            time_regex : str, default value is 'regex=[0-9]{8}'
                The time regex.
            workspace : str, default value is None.
                The name of workspace.
            store : str, default value is None.
                The name of Store.
        """
        if not workspace:
            workspace = self.workspace

        filepath = ''
        print('\nCREATING THUMBNAILS FROM INDICATORS...')
        for layer in tqdm(layers):
            for path in glob.glob(layer['path']):
                pattern = re.compile(r'(' + time_regex.split('=')[1]  + ')')
                try:
                    date_from_file = pattern.search([file for file in os.listdir(path) 
                                                     if pattern.search(file)][0]).group(0)
                except IndexError:
                    return "No files found with time regex informed"

                if '_' in date_from_file:
                    date = datetime.strptime(date_from_file.split('_')[0], '%Y%m%d')
                    end_date = datetime.strptime(date_from_file.split('_')[1], '%Y%m%d')
                else:
                    date = end_date = datetime.strptime(date_from_file, '%Y%m%d')

                datetime_format = '%Y-%m-%d %H:%M:%S'
                thumb_url = f"{url}/{workspace}/wms?service=WMS&version=1.1.0&time="\
                            f"{date.strftime(datetime_format).replace(' ', 'T')}.000Z" \
                            f"&request=GetMap&layers={workspace}%3A{layer['name']}&bbox={layer['bbox']}" \
                            "&width=1000&height=800&srs=EPSG%3A4326&styles=&format=image%2Fpng"

                if isinstance(date, datetime):
                    date = date.strftime('%Y%m%d')
                if isinstance(end_date, datetime):
                    end_date = end_date.strftime('%Y%m%d')

                filepath = os.path.join(path, f"{layer['name']}_{date}_{end_date}.png")

                response = requests.get(thumb_url)
                path = filepath.split(os.path.basename(filepath))[0]
                if not os.path.exists(path):
                    os.makedirs(path)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)


    def create_coverage_store(self, 
                              data: str, 
                              workspace: Optional[str]=None, 
                              file_type: Optional[str]='GeoTIFF', 
                              content_type: Optional[str]='image/tiff') -> None:
        """
            Create coverage store.

        Parameters
        ----------
            data : str,
                The path to the data.
            workspace : str, default value is None
                The name of workspace.
            file_type : str, default value is 'GeoTIFF'.
                The type of file.
            content_type : str, default value is 'image/tiff'
                The content type.

        Returns
        -------
            None
        """
        if not workspace:
            workspace=self.workspace

        files = [f for f in glob.iglob(f"{data}/**/*",
                                       recursive=True) if os.path.isfile(f) and f.endswith('.tif')]
        try:
            for file in files:
                layer_name = os.path.basename(file).split(".")[0]
                response = self.geoserver.create_coveragestore(path=file, 
                                                               layer_name=layer_name, 
                                                               workspace=workspace, 
                                                               file_type=file_type, 
                                                               content_type=content_type)
                print(f"Coveragestore {layer_name} successfully created!")
        except Exception as e:
            print(f"Coveragestore {layer_name} not created!")


    def _create_indexer_properties(self, 
                                   layer_name: str, 
                                   path: str) -> bool:
        """
            Create indexer properties for layer.

        Parameters
        ----------
            layer_name : str,
                Layer name.
            path : str,
                Path where the file will be created.

        Returns
        -------
            Boolean value indicating if the file was created.
        """

        data_xml = 'Caching=false\n\
        NoData=0\n\
        TimeAttribute=ingestion\n\
        Schema=*the_geom:Polygon,location:String,ingestion:java.util.Date\n\
        PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion)\n\
        Wildcard=*.tif'
        lines = data_xml.splitlines()
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        data_xml = textwrap.dedent('\n'.join(non_empty_lines))

        filename = 'indexer.properties'
        filepath = os.path.join(os.getcwd()) if all(hasattr(self, atributo) for atributo in 
                                                    ['hostusername', '_hostpassword']) else path
        file = os.path.join(filepath, filename)
        try:
            with open(file, 'w') as f:
                f.write(data_xml)

            if all(hasattr(self, atributo) for atributo in ['hostusername', '_hostpassword']):
                return files_ssh(ssh=self.connection,
                                 local_path=filepath,
                                 remote_path=path,
                                 filename=filename,
                                 method='put')
            else:
                return True
        except FileNotFoundError:
            return False


    def _create_timeregex_properties(self, 
                                     layer_name: str, 
                                     time_regex: str, 
                                     path: str) -> bool:
        """
            Create timeregex properties for layer.

        Parameters
        ----------
            layer_name : str,
                Layer name.
            time_regex : str,
                Time regex.
            path : str,
                Path where the file will be created.

        Returns
        -------
            Boolean value indicating if the file was created.
        """
        filename = 'timeregex.properties'
        filepath = os.path.join(os.getcwd()) if all(hasattr(self, atributo) for atributo in 
                                                    ['hostusername', '_hostpassword'])else path
        file = os.path.join(filepath, filename)
        try:
            with open(file, 'w') as f:
                f.write(time_regex)
            if all(hasattr(self, atributo) for atributo in ['hostusername', '_hostpassword']):
                return files_ssh(ssh=self.connection,
                                 local_path=filepath,
                                 remote_path=path,
                                 filename=filename,
                                 method='put')
            else:
                return True
        except FileNotFoundError:
            return False


    def _create_datastore_properties(self, path: str) -> bool:
        """
            Create indexer properties for layer.

        Parameters
        ----------
            path : str,
                Path where the file will be created.

        Returns
        -------
            Boolean value indicating if the file was created.
        """

        db = self.db
        pg_schema = self.db_schema
        pg_user = self.db_user
        pg_password = self.db_password
        pg_port = self.db_port

        data_xml = f'SPI=org.geotools.data.postgis.PostgisNGDataStoreFactory\n\
        host={self.hostname}\n\
        port={pg_port}\n\
        database={db}\n\
        schema={pg_schema}\n\
        user={pg_user}\n\
        passwd={pg_password}'
        lines = data_xml.splitlines()
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        data_xml = textwrap.dedent('\n'.join(non_empty_lines))

        filename = 'datastore.properties'
        filepath = os.path.join(os.getcwd()) if all(hasattr(self, atributo) for atributo in 
                                                    ['hostusername', '_hostpassword']) else path
        file = os.path.join(filepath, filename)

        try:
            with open(file, 'w') as f:
                f.write(data_xml)

            if all(hasattr(self, atributo) for atributo in ['hostusername', '_hostpassword']):
                return files_ssh(ssh=self.connection,
                                 local_path=filepath,
                                 remote_path=path,
                                 filename=filename,
                                 method='put')
            else:
                # Remove old properties and sample_image.dat
                for file in os.listdir(path):
                    if file.endswith((f'{os.path.basename(path)}.properties', '.dat')):
                        os.remove(os.path.join(path, file))
                return True
        except FileNotFoundError:
            return False


    def _add_tile_cache(self, 
                        name: str, 
                        time_regex: str, 
                        path: str, 
                        workspace: Optional[str]=None, 
                        is_vector: Optional[bool]=False) -> int:
        """
            Add tile cache.

        Parameters
        ----------
            name : str,
                Layer name.
            path : str,
                Path where the file will be created.
            workspace : str, default value is None
                The name of workspace.
            time_regex : str, default value is 'regex=[0-9]{8}'
                The time regex.
            list_dates : List[str], default value is None
                The list of dates.
            is_vector : bool, default value is False
                The type of layer.

        Returns
        -------
            The status code.
        """
        if not workspace:
            workspace = self.workspace
        layer_name = f"{workspace}:{name}"
        url = f'{self.service_url}/gwc/rest/layers/{layer_name}.xml'

        headers = {"Content-type": "application/xml"}
        auth = HTTPBasicAuth(self.get_username(), self.get_password())

        args = {}
        if hasattr(self, 'connection'):
            args['conn'] = self.connection
        # print(path)
        list_dates = get_time_list_from_data(path=path,
                                             time_regex=time_regex,
                                             is_vector=is_vector, **args)

        response = requests.get(url, 
                                headers=headers, 
                                auth=auth, 
                                verify=False)
        current_xml = response.text
        root = ET.fromstring(current_xml)

        new_string_parameter_filter = ET.Element('stringParameterFilter')
        key = ET.SubElement(new_string_parameter_filter, 'key')
        key.text = 'TIME'
        default_value = ET.SubElement(new_string_parameter_filter, 'defaultValue')
        default_value.text = list_dates[0]
        normalize = ET.SubElement(new_string_parameter_filter, 'normalize')
        locale = ET.SubElement(normalize, 'locale')
        values = ET.SubElement(new_string_parameter_filter, 'values')
        for date in list_dates:
            new_date = ET.SubElement(values, 'string')
            new_date.text = date
        parameter_filters = root.find('.//parameterFilters')
        parameter_filters.append(new_string_parameter_filter)
        data = ET.tostring(root, encoding='utf-8').decode()

        response = requests.put(url, 
                                data=data, 
                                headers=headers, 
                                auth=auth, 
                                verify=False)
        return response.status_code


    def _update_coverage_title(self,
                               name: str,
                               title: str,
                               workspace: Optional[str]=None) -> int:
        """
            Update coverage title.

        Parameters
        ----------
            name : str
                Layer name.
            title : str
                Title of layer.
            workspace : str, default value is None
                The name of workspace.

        Returns
        -------
            The status code.
        """
        if not workspace:
            workspace=self.workspace

        url = f"{self.service_url}/rest/workspaces/{workspace}/coveragestores"\
              f"/{name}/coverages/{name}"
        data = {
            "coverage": {
                "title": title,
            }
        }
        headers = {"Content-type": "application/json"}
        auth = HTTPBasicAuth(self.get_username(), self.get_password())
        response = requests.put(url, 
                                json=data, 
                                headers=headers, 
                                auth=auth, 
                                verify=False)

        return response.status_code


    def create_imagemosaic_store(self,
                                 data: str,
                                 layer_name: str,
                                 store_name: Optional[str]=None,
                                 workspace: Optional[str]=None,
                                 title: Optional[str] = None,
                                 time_regex: Optional[str]='regex=[0-9]{8}',
                                 style: Optional[str]=None,
                                 is_root_path: Optional[bool]=True) -> Union[bool, str]:
                                #  db_settings: Optional[dict]=None) -> Union[bool, str]:
        """
            Create a new coverage store in geoserver.

        Parameters
        ----------
            data : str
                Path where the raster are stored.
            layer_name : str
                Layer name.
            store_name : Optional[str], default = None,
                Store name.
            workspace : Optional[str], default = None,
                Workspace name.
            time_regex : Optional[str], default = 'regex=[0-9]{8}',
                Time regex.
            style : Optional[str], default = None,
                Style path.
            is_root_path : Optional[bool], default = False
                If false, the data is not stored in the root path. Otherwise, the data is 
                stored in the root path.

        Return
        ------
            True if the coveragestore was created successfully, False otherwise.
            And a message that indicates the status of the operation.

        Example
        -------
            data_path = '/home/yuri/Docker-Compose/geoserver/data/Phantom3Adv_120m_RGB'
            name = 'Phantom3Adv_120m_RGB'
            time_regex = 'regex=[0-9]{8}T[0-9]{6}'

            created, message = geo.create_imagemosaic_store(data=data_path, 
                                                            layer_name=name, 
                                                            store_name=name,
                                                            time_regex=time_regex)
        """
        response_style = 0
        created = False

        if not workspace:
            workspace=self.workspace
        if not store_name:
            store_name = self.store
        if not title:
            title = layer_name

        # Uploading style
        if style:

            # Create style path if the user did not specify it. 
            # It takes the default path in edpu/templates/styles/raster
            if not '.sld' in os.path.basename(style):
                style_path = os.path.join(ROOT_PATH, 'edpu', 'templates', 'styles', 'raster')
                style_list = [os.path.basename(style) for style in glob.glob(os.path.join(style_path, 
                                                                                          '*.sld'))]
                if f'{style}.sld' in style_list:
                    style = os.path.join(style_path, f'{style}.sld')
            #style_name = os.path.basename(style).split(".")[0]
            style_name = layer_name

            # Verify if the style already exists. If not, upload it.
            try:
                response_style = self.geoserver.get_style(style_name=style_name, workspace=workspace)
                if response_style:
                    response_style = self.geoserver.delete_style(style_name=style_name, 
                                                                 workspace=workspace)
                    if response_style:
                        raise GeoserverException(200, 'Style deleted successfully')
            except GeoserverException as e:
                response_style = self.geoserver.upload_style(path=style, 
                                                             workspace=workspace, 
                                                             name=style_name)

        # Cleaning raster directory if is running in local mode
        if is_root_path:
            args = {}
            if hasattr(self, 'connection'):
                args['conn'] = self.connection
            response = clean_raster_directory(path=data, **args)

        # Creating index properties
        response = self._create_indexer_properties(layer_name=layer_name, path=data)

        # Creating timeregex properties
        if response:
            response = self._create_timeregex_properties(layer_name=layer_name, 
                                                         time_regex=time_regex,
                                                         path=data)
            if response:
                db = self.db
                pg_schema = self.db_schema
                pg_user = self.db_user

                response = self._create_datastore_properties(path=data)
                # Creating imagemosaic store
                if response:
                    print("\nCreating Imagemosaic store...")

                    try:
                        cat_obj = self.cat.create_imagemosaic(name=store_name,
                                                              data=data,
                                                              workspace=workspace,
                                                              coverageName=layer_name)

                        # Publishing time dimension to coveragestore
                        if cat_obj:
                            response = self.geoserver.publish_time_dimension_to_coveragestore(layer_name=layer_name, 
                                                                                              store_name=store_name, 
                                                                                              workspace=workspace)

                            # Updating coverage title
                            response_title = self._update_coverage_title(name=store_name, title=title)

                            # Publishing style
                            if response_style == 200:
                                response_style = self.geoserver.publish_style(layer_name=layer_name, 
                                                                              style_name=style_name, 
                                                                              workspace=workspace)

                                # Printing response if the coveragestore style is created or not
                                if response_style in [200, 201, 202] and response_title == 200: 
                                    print("Coveragestore style successfully created!")
                                else:
                                    print("Coveragestore style not created!")

                            # Adding tile caching to coveragestore
                            if response in [200, 201, 202]:
                                response = self._add_tile_cache(path=data,
                                                                name=layer_name,
                                                                time_regex=time_regex)

                                # Printing response if the coveragestore is created or not
                                if response == 200:
                                    print("...Done")
                                    created = True
                                    message = "Coveragestore with time dimension and tile caching "\
                                            "successfully created!"
                                else:
                                    message = "Coveragestore with time dimension and tile caching not "\
                                            "created!"
                        else:
                            message = "Coveragestore not created!"

                    except ConflictingDataError as ce:
                        message = str(ce)

                else:
                    message = "Datastore.properties not created!"
            else:
                message = "Timeregex.properties not created!"
        else:
            message = "Indexer.properties not created!"

        # Closing connection to remote server
        if hasattr(self, 'connection'):
            self.connection.close()

        return created, message

    def update_imagemosaic_store(self, 
                                 data: str, 
                                 root_path: str, 
                                 layer_name: str, 
                                 store_name: Optional[str]=None,
                                 workspace: Optional[str]=None,
                                 title: Optional[str] = None,
                                 time_regex: Optional[str]='regex=[0-9]{8}') -> Union[bool, str]:
        """
            Update Imagemosaic store

        Parameters
        ----------
            data : str
                The path where the data is stored.
            root_path : str
                The root path where the data is stored.
            layer_name : str
                The name of the layer.
            store_name : str, default value is None
                The name of the store.
            workspace : str, default value is None
                The name of the workspace.
            title : str, default value is None
                The title of the layer.
            time_regex : str, default value is 'regex=[0-9]{8}'
                The time regex.
           
        Return
        ------
            A boolean value indicating if the store was updated and a string
            with the message.

        Example
        --------

            new_data = '/home/yuri/Docker-Compose/geoserver/data/Phantom3Adv_120m_RGB/2022/11'
            root_data = '/home/yuri/Docker-Compose/geoserver/data/Phantom3Adv_120m_RGB'
            name = 'Phantom3Adv_120m_RGB'
            time_regex = 'regex=[0-9]{8}T[0-9]{6}'

            created, message = geo.update_imagemosaic_store(data=new_data,
                                                            root_path=root_data,
                                                            layer_name=name, 
                                                            store_name=name,
                                                            time_regex=time_regex)

        """
        response = False
        updated = False
        message = ""
        
        missing_prop_files = False

        if not workspace:
            workspace=self.workspace
        if not store_name:
            store_name = self.store
        if not title:
            title = layer_name

        # Checking if the data and root_path directories exist in both in local or remote server
        if all(hasattr(self, atributo) for atributo in ['hostusername', '_hostpassword']):
            if not check_existence_remote_path(ssh=self.connection, remote_path=data):
                return False, "The data does not exist in the remote server."
        else:
            if not os.path.exists(data) or not os.path.exists(root_path):
                return False, "The data or root_path does not exist in the local server."

        db = self.db
        pg_schema = self.db_schema
        pg_user = self.db_user

        root_files = set(os.listdir(root_path))  # usar set para busca mais rápida
        root_folder_name = os.path.basename(os.path.normpath(root_path))

        required_properties = {
            f"{root_folder_name}.properties",
            "datastore.properties",
            "indexer.properties",
            "timeregex.properties"
        }

        missing_files = required_properties - root_files  # encontra os arquivos que faltam

        if missing_files:
            missing_prop_files = True
            message = (
                f"The following required .properties file(s) are missing: "
                f"{', '.join(sorted(missing_files))}"
            )
        else:
            response = self._create_datastore_properties(path=data)
            
        # Updating imagemosaic store
        if response:
            print("\nUpdating Imagemosaic store...")

            try:
                cat_obj = self.cat.add_granule(data=data,
                                            store=store_name,
                                            workspace=workspace)

                # Updating coverage granule. The condition is checking if cat_obj is None
                # because the return from the add_granule function if the coverage is
                # updated is None
                if cat_obj is None:
                    message = "Coveragestore updated!"

                    # Updating time dimension to coveragestore
                    response = self._add_tile_cache(name=layer_name,
                                                    time_regex=time_regex,
                                                    path=root_path)
                    if response == 200:
                        print("...Done")
                        updated = True
                        message = "Coveragestore with time dimension and tile caching "\
                                "successfully updated!"
                    else:
                        message = "Coveragestore with time dimension and tile caching not "\
                                "updated!"
                else:
                    message = "Coveragestore not updated!"
            except FailedRequestError as fe:
                message = "Error: To update coveragestore it is necessary to create the "\
                        "store first."
        elif not response and not missing_prop_files:
            message = "Datastore properties not updated! Some parameters are missing."
        else:
            pass

        # Closing connection to remote server
        if hasattr(self, 'connection'):
            self.connection.close()

        return updated, message
    