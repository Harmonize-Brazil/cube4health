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

"""
Set operations for validate input and output files or directories.
:Contains:
 is_valid_file,
 is_valid_directory

:Notes:
This module enable verify if input and output files and directories passed to ArgParse arguments are valid. The
code was adapted from https://codereview.stackexchange.com posted for Matthew Rankin.
"""

import os
import string


def is_valid_file(parser, arg):
    if not os.path.isfile(arg):
        parser.error('The file {} does not exist!'.format(arg))
    else:
        # File exists so return the filename
        return arg


def is_valid_directory(parser, arg):
    if not os.path.isdir(arg):
        parser.error('The directory {} does not exist!'.format(arg))
    else:
        # Directory exists so return the directory name
        return arg


def is_valid_namefile(parser,arg):
    if '.tif' not in os.path.basename(arg) and '.TIF' not in os.path.basename(arg):
         parser.error('The file {} does not have a valid extension for a COG file!'.format(arg))
    elif os.path.isdir(os.path.dirname(arg)) != True:
        parser.error('Please, include a valid path to save COG file {}!'.format(arg))                       
    else:
        # File have COG valid extension so return the filename
        return arg


