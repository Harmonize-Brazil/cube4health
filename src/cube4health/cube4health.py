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

"""Main module."""
# --------------------------
#        Imports
# --------------------------
import click
from .eddpr import eddpr


class Cube4Health:
    """Define an interface for cube4health modules."""

    def __init__(self, **request_kwargs):
        """Create an object with method to run subpackages of cube4health
           """
        # Get click context with parameters:
        ctx = click.get_current_context()
        click_msg = [ctx.info_name]
        for key,value in ctx.params.items():
            click_msg.append("--"+str(key))
            click_msg.append(value)
        
        self.args = click_msg
        
        
    def run(self,module=None):
        if not module:
            raise ValueError('Module name is required!')
        elif module == 'eddpr':
            eddpr.main(self.args)
        else:
            raise ValueError('CLI entry point not implemented yet for {}!'.format(module))
