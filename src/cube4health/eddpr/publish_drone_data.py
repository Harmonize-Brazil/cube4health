#
# This file is part of EODCtHRS Drone Data PRocessing (EDDPR).
# Copyright (C) 2025 HARMONIZE/INPE.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.
#
"""Utility for Drone data publishing

   Creates a STAC Catalog from JSON files of collection from Drone data. The COG files Assets that compose the collections was stored in place indicated as
   a parameters (localhost or remote server). The STAC catalogs and Geoserver layers follow the same idea, created and published local or remote.
   """

import sys
import os
from pathlib import Path
import json
import subprocess
from contextlib import closing
import itertools
import getpass
from tqdm import tqdm
from .. import config #cube4health global variables
if __name__ != "__main__":
    from ..edpu import GeoServer
    from ..edpu.utils import connect_ssh

local_path = os.path.dirname(os.path.abspath(__file__))

# Emulates a Geoserver object instance
class geo_object:
    def __init__(
        self, 
        hostname: str = "localhost"  # ip for server with collections files, default localhost
                ):
        if hostname != 'localhost':
            print()
            print('-'*95)
            print('To publish data at the remote host, we need to enable an SSH connection.\nPlease enter with your '\
                   'private information:\n')
            self.hostname = hostname

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


#Source https://stackoverflow.com/a/53877600
def sftp_mkdir_p(sftp, remote_directory):
    dirs_exist = remote_directory.split('/')
    dirs_make = []
    # find level where dir doesn't exist
    while len(dirs_exist) > 0:
        try:
            sftp.listdir('/'.join(dirs_exist))
            break
        except IOError:
            value = dirs_exist.pop()
            if value == '':
                continue
            dirs_make.append(value)
        else:
            return False
    # ...and create dirs starting from that level
    for mdir in dirs_make[::-1]:
        dirs_exist.append(mdir)
        sftp.mkdir('/'.join(dirs_exist))


def check_remote_data(data_path_input,remote_root_path,geo_instance):
    connected, connection = connect_ssh(hostname=geo_instance.hostname, username=geo_instance._hostusername, password=geo_instance._hostpassword)
    if connected:
        list_of_files = [str(path) for path in Path(data_path_input).rglob('*') if path.suffix in {".png", ".tif"}]
        list_of_files_basename = [os.path.basename(file) for file in list_of_files]
        list_of_files_basename.sort()

        with closing(connection.open_sftp()) as sftp:
            try:
                list_of_remote_files = sftp.listdir(remote_root_path)
                list_of_remote_files.sort()
            except IOError as e:
                sftp_mkdir_p(sftp,remote_root_path)  # Create remote_path
                print('New collection transfering...')
                list_of_remote_files = []

        missing_files = set(list_of_files_basename) - set(list_of_remote_files)
        if len(missing_files) > 0:
            print('Copying {} missing files to remote server before publish the data...'.format(len(missing_files)))
            opc = input('Do you confirm this operation? (y/n): ')
            if opc.lower() == 'y': 
                with closing(connection.open_sftp()) as sftp:
                    for file in tqdm(missing_files):
                        first_idx = len(tuple(itertools.takewhile(lambda x: file not in x, list_of_files)))
                        try:
                            sftp.put(list_of_files[first_idx],os.path.join(remote_root_path,file))
                            stdin, stdout, stderr = connection.exec_command('chmod -R 777 {0}'.format(os.path.join(remote_root_path,file)))
                            
                        except Exception as e:
                            print(f"{e}: {remote_root_path} on remote server!")
            else:
                raise Exception("Publish process stopped, missing files on the remote server!")
    else:
        print()
        print('-'*120)
        print('An error occurred when trying to connect the server {} using user {} and password supplied!\n' \
              'Please, revise these parameters and try again!'.format(geo_instance.hostname,geo_instance._hostusername))
        sys.exit()


def  publish_to_geoserver(service_url, workspace, root_path, layer_name, db_settings, local_path, hostname='localhost'):
    """
    Creates store and layers to publish drone data using Geoserver application

       :param service_url: the URL for the GeoServer instance.
       :type service_url: String

       :param workspace: workspace name to group similar layers.
       :type workspace: String

       :param root_path: root path name containing files processed (COGs) to publish throw Geoserver.
       :type root_path: String

       :param layer_name: name that will identify the layer (same of the folder name where the data are stored).
       :type layer_name: String

       :param db_settings:  is a dictionary with the database settings.
       :type db_settings: Dict

       :param local_path:  local path name of module to access styles files.
       :type local_path: String

       :param hostname:  IP address from the server where the data will be stored (default is localhost).
       :type hostname: String
    """

    style_file = None
    styles = {'Thermal':'thermal_style.sld', 'NDVI':'ndvi_style.sld','MS':'multispectral_style.sld'}
    for style_key in styles.keys():
        if style_key in layer_name:
            style_file=os.path.join(os.path.join(local_path,'templates',styles[style_key]))
            break
     
    time_regex='regex=[0-9]{8}' #daily mosaics
    if workspace != 'mosaics':
        time_regex='regex=[0-9]{8}T[0-9]{6}'

    geo = GeoServer(service_url=service_url, workspace=workspace, hostname=hostname, db_settings=db_settings)

    created, message = geo.update_imagemosaic_store(data=os.path.join(root_path,layer_name), root_path=os.path.join(root_path,layer_name), layer_name=layer_name,
                                                        store_name=layer_name, time_regex=time_regex)    
    print(created,message)
    if not created:
        created, message = geo.create_imagemosaic_store(data=os.path.join(root_path,layer_name), layer_name=layer_name, store_name=layer_name,
                                                    time_regex=time_regex, style=style_file)
        if not created:
            print(message,'\n')

            geo = GeoServer(service_url=service_url, workspace=workspace, hostname=hostname)
            print('Alternative - creating a shapefile with mosaic indexes to publish an ImageMosaic store and coverage!')
            created, message = geo.update_imagemosaic_store(data=os.path.join(root_path,layer_name), root_path=os.path.join(root_path,layer_name), layer_name=layer_name,
                                                        store_name=layer_name, time_regex=time_regex)            
            print(created,message)
            if not created:
                created, message = geo.create_imagemosaic_store(data=os.path.join(root_path,layer_name), layer_name=layer_name, store_name=layer_name,
                                                    time_regex=time_regex, style=style_file)
                print('aqui:\n',created,message)
                if not created:
                    print(message)
                    raise Exception("Impossible to publish the data on Geoserver...")
   

def main(argv):
    prefix_geoserver_data = 'harmonize'
    
    # Reading JSON file with collection of drone data:
    fname_drone_collection = argv.json_catalog_file
    with open(fname_drone_collection, 'r') as f:
        drone_collection = json.load(f)

    workspace = None
    layer_name = drone_collection['name']
    if drone_collection['metadata'].get('wms'):
        service_url = drone_collection['metadata']['wms']['url'].split('geoserver')[0]+'geoserver'
        workspace = drone_collection['metadata']['wms']['url'].split('geoserver')[1].split('/')[1]    
    
    print('Publishing data from',layer_name,'collection...')
    hostname = 'localhost'
    if 'localhost' not in str(drone_collection):
        print('\n','-'*95)
        hostname = input('Please, enter the IP of the remote host that has Geoserver, Titiler, and STAC services available: ')

        for key in drone_collection['items'][0]['assets'].keys():
            remote_root_path_data = os.path.dirname(drone_collection['items'][0]['assets'][key]['href'].replace(prefix_geoserver_data,''))
            
        geo = geo_object(hostname=hostname) 
                
        print('Checking the data availability of this collection on the remote server...')
        check_remote_data(os.path.join(argv.data_path_input,layer_name),remote_root_path_data,geo)
        print('Aqui remote root path data:',remote_root_path_data)
        
    
        # Define environment variable to create STAC catalog at remote server: 
        os.environ['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:postgres@{}:5432/bdc".format(geo.hostname) # visible in this process + all children

    print('Creating STAC catalog for',layer_name,'collection...')
    subprocess.run( ['bdc-catalog','load-data','--ifile', fname_drone_collection,'-v'])    

    if 'service_url' in locals(): # Checking that the data needs to be published at Geoserver
        db_settings={'db':'harmonize','schema':'public','user':'postgres'}
        if 'remote_root_path_data' in locals():
            publish_to_geoserver(service_url, workspace, remote_root_path_data, layer_name, db_settings, local_path, hostname)     #local_path global variable for module path
        else:
            publish_to_geoserver(service_url, workspace, argv.data_path_input, layer_name, db_settings, local_path, hostname)     #local_path global variable for module path


if __name__ == "__main__":
    # Process the arguments
    from argparse import ArgumentParser, SUPPRESS
    import cube4health.eddpr.arghelper as arghelper

    from ..edpu.geoserver import GeoServer
    from ..edpu.utils import connect_ssh

    # Disable default help
    parser = ArgumentParser(description='Publish drone data collections using BDC-STAC service and Geoserver', add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    # Add back help
    optional.add_argument('-h','--help',action='help',default=SUPPRESS,help='show this help message and exit')
    required.add_argument('--data_path_input', type=lambda x: arghelper.is_valid_directory(parser, x),
                        required=True, help='Required path to root folder which Cloud Optimized GeoTIFF (COG) files collections were created before. Example /home/user/Docker-Compose/geoserver/data')
    required.add_argument('--json_catalog_file', type=lambda x: arghelper.is_valid_file(parser, x), help='Required JSON filename (including path) used to create STAC catalog and Geoserver layer.', required=True)
    #optional.add_argument('--optional_arg')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    sys.exit(main(parser.parse_args()))

   