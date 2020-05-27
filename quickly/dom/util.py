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
Some utility functions.
"""


def max_space(*whitespace):
    r"""Return the "most important" whitespace of the specified strings.

    This is used to combine whitespace requirements. For example, newlines
    are preferred over single spaces, and a single space is preferred over
    an empty string. For example::

        >>> max_space('\n', ' ')
        '\n'
        >>> max_space(' ', '')
        ' '

    """
    return max(whitespace, key=lambda s: (s.count('\n'), s.count(' ')))




