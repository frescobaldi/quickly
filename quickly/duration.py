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
Functions to deal with LilyPond's musical durations.
"""

import fractions
import math


def to_string(value):
    r"""Convert the value (most times a Fraction) to a LilyPond string notation.

    The value is truncated to a duration that can be expressed by a note length
    and a number of dots. For example::

        >>> from fractions import Fraction
        >>> from quickly.duration import to_string
        >>> to_string(Fraction(3, 2))
        '1.'
        >>> to_string(4)
        '\\longa'
        >>> to_string(7.75)
        '\\longa....'

    Raises an IndexError if the base duration is too long (longer than
    ``\maxima``).

    """
    mantisse, exponent = math.frexp(value)
    dotcount = int(-1 - math.log2(1 - mantisse))
    if exponent >= 2:
        dur = (r'\breve', r'\longa', r'\maxima')[exponent-2]
    else:
        dur = 1 << 1 - exponent
    return '{}{}'.format(dur, '.' * dotcount)


def to_fraction(text, dotcount=None):
    r"""Convert a LilyPond duration string (e.g. ``'4.'``) to a Fraction.

    The durations ``\breve``, ``\longa`` and ``\maxima`` may be used with or
    without backslash. If ``dotcount`` is None, the dots are expected to be in
    the ``text``.

    For example::

        >>> from quickly.duration import to_fraction
        >>> to_fraction('8')
        Fraction(1, 8)
        >>> to_fraction('8..')
        Fraction(7, 32)
        >>> to_fraction('8', dotcount=2)
        Fraction(7, 32)

    Raises a ValueError if an invalid duration is specified.

    """
    if dotcount is None:
        dotcount = text.count('.')
        text = text.strip(' \t.')
    # maxima, longa, breve, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048
    # i: 0    1      2      3  4  5  6  7   8   9   10   11   12   13    14
    try:
        i = int(text).bit_length() + 2
    except ValueError:
        i = ('maxima', 'longa', 'breve').index(text.lstrip('\\'))
    return fractions.Fraction(8 * ((2 << dotcount) - 1), 1 << dotcount + i)


def shift_duration(value, log, dotcount):
    r"""Shift the duration.

    The ``value`` should be a normalized Fraction, a new Fraction is returned.
    ``log`` is the scaling as a power of 2; and ``dotcount`` the number of dots
    to be added (or removed, by specifying a negative value). The value should
    be expressable by a note length and a number of dots.

    When removing too much dots, a ValueError is raised.

    """
    offset = max(0, -log - dotcount)
    dots1 = value.numerator.bit_length() + dotcount # (actually #dots+1)
    if dots1 <= 0:
        raise ValueError("cannot remove more dots")
    numer = 2 ** dots1 - 1 << offset
    denom = value.denominator * 2 ** (log + dotcount + offset)
    return fractions.Fraction(numer, denom)

