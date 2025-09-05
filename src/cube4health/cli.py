
#
# This file is part of cube4health package.
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


"""Command line interface for the cube4health package."""
import click
from .cube4health import Cube4Health
from . import config #cube4health global variables
from . import __version__

@click.group()
@click.version_option(__version__, prog_name="cube4health CLI Tool")
def cli():
    """A CLI tool for cube4health package."""
    pass

@cli.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option('--module', required=True, type=click.Choice(['eddpr', 'ehipr', 'eclimpr']), help='Choose a module.')
def run(module):
    """Run a module: cube4health run --module eddpr"""
    cube_obj = Cube4Health()
    cube_obj.run(module=module)