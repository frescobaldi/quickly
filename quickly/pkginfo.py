# This file is part of python-ly, https://pypi.python.org/pypi/python-ly
#
# Copyright (c) 2014 - 2015 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Meta-information about the quickly package.

This information is used by the install script.

The :attr:`version` and :attr:`version_string` are also available
in the global :mod:`quickly` module space.

"""

import collections
Version = collections.namedtuple("Version", "major minor patch")


#: name of the package
name = "quickly"

#: the current version
version = Version(0, 0, 3)
version_suffix = ""
version_string = "{}.{}.{}".format(*version) + version_suffix

#: short description
description = "Tool and library for manipulating LilyPond files"

#: long description
long_description = \
    "The quickly package provides a Python library and a commandline tool " \
    "that can be used to parse and manipulate LilyPond source files."

#: maintainer name
maintainer = "Wilbert Berendsen"

#: maintainer email
maintainer_email = "info@frescobaldi.org"

#: homepage
url = "https://github.com/frescobaldi/quickly"

#: license
license = "GPL v3"

#: copyright year
copyright_year = "2020-2021"

