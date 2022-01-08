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


def load(filename, lexicon=True, encoding=None):
    """Read text from ``filename`` and return a :class:`parce.Document`.

    If ``lexicon`` is True, the lexicon will be guessed based on filename and
    contents, otherwise the lexicon is used directly. The ``encoding`` is
    passed directly to Python's :func:`open` function. Raises :class:`OSError`
    if the file can't be read.

    """
    text = open(filename, encoding=encoding).read()
    if lexicon is True:
        lexicon = find(filename=filename, contents=text)
    doc = parce.Document(lexicon, text, transformer=True)
    doc.url = os.path.abspath(filename)
    return doc

