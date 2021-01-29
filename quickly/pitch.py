# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Functions to deal with LilyPond pitches.
"""


def num_to_octave(n):
    """Convert a numeric value to an octave notation.

    The octave notation consists of zero or more ``'`` or ``,``. The octave
    ``0`` returns the empty string. Note that this differs from LilyPond, which
    uses -1 for the octave without a ``'`` or ``,``.

    """
    if n < 0:
        return "," * -n
    return "'" * n


def octave_to_num(octave):
    """Convert an octave string to a numeric value.

    ``''`` is converted to 2, ``,`` to -1. The empty string gives 0.

    """
    return octave.count("'") - octave.count(",")


