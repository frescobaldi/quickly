# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2022 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Classes and functions to deal with key signatures.
"""

import collections

from parce.util import cached_method

from .pitch import Pitch, MAJOR_SCALE

#: The offset of the standard key modes to the default major scale in LilyPond.
mode_offset = {
    'major': 0,
    'minor': 5,
    'ionian': 0,
    'dorian': 1,
    'phrygian': 2,
    'lydian': 3,
    'mixolydian': 4,
    'aeolian': 5,
    'locrian': 6,
}


def _int(value):
    """Return int if val is integer."""
    i = int(value)
    return i if value == i else value


def alterations(offset, scale=MAJOR_SCALE):
    """Return the list of alterations for the specified offset.

    The list has the same length as the :py:data:`scale <.pitch.MAJOR_SCALE>`
    (which has the pitch of the "white keys" starting at C, and probably almost
    never will have to be specified).

    The ``offset`` is an integer that specifies the number of notes to shift
    the scale to the left or right. The pitches in the scale from that offset
    are compared with the pitches from the beginning, and the returned
    alteration for that step is the difference from the default step in the
    scale. For example::

        >>> from quickly.key import alterations
        >>> alterations(0)
        [0, 0, 0, 0, 0, 0, 0]
        >>> alterations(1)
        [0, 0, -0.5, 0, 0, 0, -0.5]

    The first call lists the accidentals for C major. The second call lists the
    accidentals that would be needed when transposing the scale starting at
    step 1 in the scale (that would be a dorian scale for the default major
    scale) to step 0 in the same scale, so this would be the accidentals that
    would be needed for C dorian.

    """
    l = len(scale)
    offset %= l
    diff = scale[offset] - scale[0]
    return [_int(scale[step % l] + step // l * 6 - scale[orig] - diff)
                for step, orig in enumerate(range(l), offset)]


def accidentals(note, alter=0, mode=None, scale=MAJOR_SCALE):
    """Return the list of 7 alterations for the specified key signature.

    The ``note`` is a note from 0..6; the ``alter`` is the alteration of that
    note in whole tones, and the ``mode``, if given, is a list of 7 alterations
    describing the mode. By default the major mode is used. Examples::

        >>> major = alterations(0)
        >>> minor = alterations(5)
        >>> phrygian = alterations(2)
        >>> accidentals(0, 0, major)                  # C major
        [0, 0, 0, 0, 0, 0, 0]
        >>> accidentals(1, 0, major)                  # D major, accs for cs and fs
        [0.5, 0, 0, 0.5, 0, 0, 0]
        >>> accidentals(1, 0, minor)                  # D minor, just a b-flat
        [0, 0, 0, 0, 0, 0, -0.5]
        >>> accidentals(2, 0, phrygian)               # E phrygian, no accidentals
        [0, 0, 0, 0, 0, 0, 0]
        >>> accidentals(3, .5, phrygian)              # F-sharp phrygian, 2 accs
        [0.5, 0, 0, 0.5, 0, 0, 0]
        >>> accidentals(5, 0, major)                  # A major
        [0.5, 0, 0, 0.5, 0.5, 0, 0]
        >>> accidentals(5, 0, minor)                  # A minor
        [0, 0, 0, 0, 0, 0, 0]
        >>> accidentals(5, -0.5, major)               # A-flat major
        [0, -0.5, -0.5, 0, 0, -0.5, -0.5]
        >>> accidentals(2, -0.5, minor)               # E-flat minor
        [-0.5, -0.5, -0.5, 0, -0.5, -0.5, -0.5]
        >>> accidentals(4, 0.5, major)                # G-sharp major
        [0.5, 0.5, 0.5, 1, 0.5, 0.5, 0.5]

    You can compose your own mode (inspired by the LilyPond manual)::

        >>> freygish = [0, -0.5, 0, 0, 0, -0.5, -0.5]
        >>> signature(0, 0, freygish)
        [0, -0.5, 0, 0, 0, -0.5, -0.5]
        >>> tatooinish = [0.5, 0 -0.5, 0.5, 0, 0, -0.5]
        >>> signature(3, 0.5, tatooinish)           # F-sharp tatooinish
        [0, 0.5, 0, 1, 0, 1]                        # (one sharp and two double sharps)

    """
    if mode is None:
        mode = alterations(0, scale)
    note %= len(scale)
    steps = alterations(note, scale)
    accs = [_int(m - s + alter) for m, s in zip(mode, steps)]
    return accs[-note:] + accs[:-note]  # rotate so C is always at start


class KeySignature:
    """Represents a key signature."""
    def __init__(self, note, alter=0, mode=None, scale=MAJOR_SCALE):
        self.note = note        #: The note (0..6).
        self.alter = alter      #: The alteration in whole tones (0 by default).
        self.mode = mode        #: The mode (None, standard LilyPond mode name like "major" or alterations list).
        self.scale = scale      #: The scale.
        if isinstance(mode, str):
            mode = alterations(mode_offset[mode])
        self.accidentals = accidentals(note, alter, mode, scale)


    # Preferred base notes for every MIDI key number (0..11). MIDI tones are
    # semitones, this list specifies the base note to pick. So, for MIDI key 3,
    # (e-flat) a third is preferred, which in C will be an e-flat, but
    _preferred_intervals = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 6, 6]

    def from_midi(self, key):
        """Convert a MIDI key number to a sensible Pitch."""
        # cache for 12 semitones
        steps = [None] * 12
        # fill in the tones from the scale (note, alter, octave)
        for note, (base, alter) in enumerate(zip(self.scale, self.accidentals)):
            octave, step = divmod(int((base + alter) * 2), 12)
            steps[step] = (note, alter, octave)

        print(steps)
        tonic = self.scale[self.note]
        alter = self.alter
        midi_tonic = int((tonic + alter) * 2) % 12
        print("MIDI tonic:", midi_tonic)
        # find suitable base pitches for the missing semitones
        for key, base in enumerate(self._preferred_intervals):
            midi_step = (midi_tonic + key) % 12
            if steps[midi_step] is None:
                pass # TODO impl


