# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2020 by Wilbert Berendsen <info@wilbertberendsen.nl>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""
The quickly module.
"""

import os.path

import parce

from .pkginfo import version, version_string
from .registry import find


__all__ = ('find', 'load', 'version', 'version_string')


def load(filename, lexicon=True, encoding=None, errors=None, newline=None):
    """Convenience function to read text from ``filename`` and return a
    :class:`parce.Document`.

    If ``lexicon`` is True, the lexicon will be guessed based on filename and
    contents. If it is a string name, its name is looked up in the registry;
    otherwise the lexicon is used directly.

    The ``encoding``, if specified, is used to read the file; otherwise the
    encoding is autodetected. The ``errors`` and ``newline`` arguments will be
    passed to Python's :func:`open` function. Raises :class:`OSError` if the
    file can't be read.

    """
    from .registry import registry
    return parce.Document.load(os.path.abspath(filename), lexicon, encoding, errors, newline, registry=registry, transformer=True)

