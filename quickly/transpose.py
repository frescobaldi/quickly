# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2021-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Transpose pitches.
"""

from fractions import Fraction

from .dom import lily


class AbstractTransposer:
    """Base class for a Transposer."""
    def transpose(self, pitch):
        """Transpose the :class:`~.pitch.Pitch`, by modifying its ``note``,
        ``alter`` and possibly ``octave`` attribute."""


class Transposer(AbstractTransposer):
    """Transpose pitches.

    Instantiate with a from- and to-Pitch. The ``scale`` attribute is a list
    with the pitch height of the unaltered step (0 .. 6). The default scale is
    the normal scale: C, D, E, F, G, A, B.

    """

    scale = (0, 1, 2, Fraction(5, 2), Fraction(7, 2), Fraction(9, 2), Fraction(11, 2))

    def __init__(self, from_pitch, to_pitch):
        # the number of octaves we need to transpose
        self.octave = to_pitch.octave - from_pitch.octave

        # the number of base note steps (c->d == 1, e->f == 1, etc.)
        self.steps = to_pitch.note - from_pitch.note

        # the number (fraction) of real whole steps
        self.alter = (self.scale[to_pitch.note] + to_pitch.alter -
                      self.scale[from_pitch.note] - from_pitch.alter)

    def transpose(self, pitch):
        doct, note = divmod(pitch.note + self.steps, 7)
        pitch.alter += self.alter - doct * 6 - self.scale[note] + self.scale[pitch.note]
        pitch.octave += self.octave + doct
        pitch.note = note
        # change the step if alterations fall outside -1 .. 1
        while pitch.alter > 1:
            doct, note = divmod(pitch.note + 1, 7)
            pitch.alter -= doct * 6 + self.scale[note] - self.scale[pitch.note]
            pitch.octave += doct
            pitch.note = note
        while pitch.alter < -1:
            doct, note = divmod(pitch.note - 1, 7)
            pitch.alter += doct * -6 + self.scale[pitch.note] - self.scale[note]
            pitch.octave += doct
            pitch.note = note


def transpose_node(
        node,
        transposer,
        pitch_processor = None,
        writable = None,
        relative_first_pitch_absolute = False,
    ):
    """Transpose pitches using the specified transposer.

    If ``relative_first_pitch_absolute`` is True, the first pitch in a
    ``\\relative`` expression is considered to be absolute, when a startpitch
    is not given. This is LilyPond >= 2.18 behaviour.

    If relative_first_pitch_absolute is False, the first pitch in a
    ``\\relative`` expression is considered to be relative to c', is no
    startpitch is given. This is LilyPond < 2.18 behaviour.

    Currently, relative_first_pitch_absolute defaults to False.

    """
