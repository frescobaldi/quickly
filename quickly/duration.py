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

A duration is a :class:`~fractions.Fraction` or an integer, where a whole note
is 1. A duration can be split in two values, log and dot-count, where the log
value is 0 for a whole note, 1 for a half note, 2 for a crotchet, -1 for a
``\\breve``, etc. This is the same way LilyPond handles durations.

Durations can be scaled using multiplying, e.g. with a Fraction.

"""

import fractions
import math


NAMED_DURATIONS = ('breve', 'longa', 'maxima')


class Transform:
    """Combine modifications of a duration (shift and/or scale).

    Use it to calculate the real length of musical items. Transforms can be
    added. A Transform that doesn't modify anything evaluates to False.

    """
    def __init__(self, log=0, dotcount=0, scale=1):
        self.log = log              #: the log to shift
        self.dotcount = dotcount    #: the dots to shift
        self.scale = scale          #: the scaling

    def __bool__(self):
        return bool(self.log or self.dotcount or self.scale != 1)

    def __repr__(self):
        return "<{} log={} dotcount={} scale={}>".format(
            type(self).__name__, self.log, self.dotcount, self.scale)

    def __add__(self, other):
        log = self.log + other.log
        dotcount = self.dotcount + other.dotcount
        scale = self.scale * other.scale
        return type(self)(log, dotcount, scale)

    def length(self, duration, scaling=1):
        """Return the actual musical length of the duration and scaling values."""
        duration, scaling = self.transform(duration, scaling)
        return duration * scaling

    def transform(self, duration, scaling=1):
        """Return a transformed two-tuple (duration, scaling)."""
        if self.log or self.dotcount:
            duration = shift_duration(duration, self.log, self.dotcount)
        return duration, scaling * self.scale


def log_dotcount(value):
    r"""Return the integer two-tuple (log, dotcount) for the duration value.

    The ``value`` may be a Fraction, integer or floating point value.

    The returned log is 0 for a whole note, 1 for a half note, 2 for a
    crotchet, -1 for a ``\\breve``, etc. This is the same way LilyPond handles
    durations. For example::

        >>> from quickly.duration import log_dotcount
        >>> log_dotcount(1)
        (0, 0)
        >>> log_dotcount(1/2)
        (1, 0)
        >>> log_dotcount(4)
        (-2, 0)
        >>> log_dotcount(1/4)
        (2, 0)
        >>> log_dotcount(3/4)
        (1, 1)
        >>> log_dotcount(7/16)
        (2, 2)
        >>> to_string(duration(*log_dotcount(Fraction(3, 4))))
        '2.'

    The value is truncated to a duration that can be expressed by a note length
    and a number of dots. For example::

        >>> to_string(duration(*log_dotcount(1)))
        '1'
        >>> to_string(duration(*log_dotcount(1.4)))
        '1'
        >>> to_string(duration(*log_dotcount(1.5)))
        '1.'
        >>> to_string(duration(*log_dotcount(0.9999)))
        '2............'

    """
    mantisse, exponent = math.frexp(value)
    log = 1 - exponent
    m, e = math.frexp(1 - mantisse)
    dotcount = -e - (m > 0.5)
    return log, dotcount


def duration(log, dotcount=0):
    r"""Return the duration as a Fraction.

    See for an explanation of the ``log`` and ``dotcount`` values
    :func:`log_dotcount`.

    """
    numer = ((2 << dotcount) - 1) << 3
    denom = 1 << (dotcount + log + 3)
    return fractions.Fraction(numer, denom)


def shift_duration(value, log, dotcount=0):
    r"""Shift the duration.

    This function is analogous to LilyPond's ``\shiftDurations`` command. It
    modifies a duration by shifting the log and the number of dots. Adding 1 to
    the log halves the note length, and adding a dot mutiplies the note length
    with ``(1 + 1/2**<dots>)``. Subtracting 1 from the log doubles the note
    length.

    The ``value`` should be a duration that is expressable by a note length and
    a number of dots. A Fraction is returned. ``log`` is the scaling as a power
    of 2; and ``dotcount`` the number of dots to be added (or removed, by
    specifying a negative value).

    For example::

        >>> shift_duration(Fraction(1, 8), -1)
        Fraction(1, 4)
        >>> shift_duration(Fraction(1, 8), -2)
        Fraction(1, 2)
        >>> shift_duration(Fraction(1, 4), 1, 1)
        Fraction(3, 16)
        >>> to_string(shift_duration(Fraction(1,4), 1, 1))
        '8.'
        >>> to_string(shift_duration(from_string('2'), 1, 1))
        '4.'
        >>> shift_duration(Fraction(7, 8), 0, -2)
        Fraction(1, 2)
        >>> shift_duration(Fraction(7, 8), 0, -1)
        Fraction(3, 4)

    The number of dots in a duration will never drop below zero::

        >>> shift_duration(1/4, 0, -1)
        Fraction(1, 4)

    """
    old_log, old_dotcount = log_dotcount(value)
    return duration(old_log + log, max(0, old_dotcount + dotcount))


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
    log, dotcount = log_dotcount(value)
    if log < 0:
        dur = '\\' + NAMED_DURATIONS[-1-log]
    else:
        dur = 1 << log
    return '{}{}'.format(dur, '.' * dotcount)


def from_string(text, dotcount=None):
    r"""Convert a LilyPond duration string (e.g. ``'4.'``) to a Fraction.

    The durations ``\breve``, ``\longa`` and ``\maxima`` may be used with or
    without backslash. If ``dotcount`` is None, the dots are expected to be in
    the ``text``.

    For example::

        >>> from quickly.duration import from_string
        >>> from_string('8')
        Fraction(1, 8)
        >>> from_string('8..')
        Fraction(7, 32)
        >>> from_string('8', dotcount=2)
        Fraction(7, 32)

    Raises a ValueError if an invalid duration is specified.

    """
    if dotcount is None:
        dotcount = text.count('.')
    text = text.strip(' \t.')
    try:
        log = int(text).bit_length() - 1
    except ValueError:
        log = -1 - NAMED_DURATIONS.index(text.lstrip('\\'))
    return duration(log, dotcount)


def is_valid(value):
    """Return True if the value can be exactly expressed in a log and dotcount
    value, without loss.

    The value should be >= 1/1024 and < 16, because LilyPond can't display more
    than 8 flags and ``\\maxima`` is the longest available duration name.

    """
    mantisse, exponent = math.frexp(value)
    return -10 < exponent < 5 and math.frexp(1 - mantisse)[0] == 0.5

