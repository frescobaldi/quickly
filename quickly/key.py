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

from . import pitch

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


def alterations(offset, scale=None):
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
    scale = scale or pitch.MAJOR_SCALE
    l = len(scale)
    offset %= l
    alter = scale[offset] - scale[0]
    return [_int(scale[step % l] + step // l * 6 - scale[orig] - alter)
                for step, orig in enumerate(range(l), offset)]


def accidentals(note, alter=0, mode=None, scale=None):
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
        >>> accidentals(0, 0, freygish)
        [0, -0.5, 0, 0, 0, -0.5, -0.5]
        >>> tatooinish = [0.5, 0 -0.5, 0.5, 0, 0, -0.5]
        >>> accidentals(3, 0.5, tatooinish)           # F-sharp tatooinish
        [0, 0.5, 0, 1, 0, 1]                        # (one sharp and two double sharps)

    """
    scale = scale or pitch.MAJOR_SCALE
    if mode is None:
        mode = alterations(0, scale)
    note %= len(scale)
    steps = alterations(note, scale)
    accs = [_int(m - s + alter) for m, s in zip(mode, steps)]
    return accs[-note:] + accs[:-note]  # rotate so C is always at start


def chromatic_scale(note=0, alter=0, scale=None, flats=None):
    """Return a default chromatic scale, based on the ``scale``.

    Every item in the scale is a tuple(note, alter).
    Uses sharps for altered notes, unless a pitch value is in the ``flats``
    list. By default, step 1.5 and 5 are in the flats list, resulting in an
    e-flat instead of d-sharp, and b-flat instead of a-sharp.

    If ``note`` and/or ``alter`` are given, the scale is transposed and rotated
    as if it where in that key.

    """
    scale = scale or pitch.MAJOR_SCALE
    flats = pitch.MAJOR_FLATS if flats is None else flats

    def chrom_scale():
        """Yield a chromatic scale."""
        note = 0
        for step in range(12):
            pitch = step / 2
            if note < len(scale)-1 and (pitch in flats or pitch == scale[note+1]):
                note += 1
            yield note, pitch - scale[note]

    def transpose(notes):
        """Transpose a chromatic scale."""
        l = len(scale)
        for n, a in notes:
            doct, new_note = divmod(n + note, l)
            new_alter = a + alter - doct * 6 - scale[new_note] + scale[n]
            yield new_note, _int(new_alter)

    alter += scale[note] - scale[0]
    notes = list(transpose(chrom_scale()))
    semitones = int(alter * 2)
    return notes[-semitones:] + notes[:-semitones]  # rotate so C-based pitch is at start


def tonic(sf, scale=None):
    """Return the tuple(note, alter) which is the musical tonic for the major
    scale with the given number of sharps or flats ``sf``.

    If ``sf`` is negative, it is the number of flats, otherwise it is the
    number of sharps. This function is useful when you only know the number of
    sharps or flats, which is common in e.g. MIDI key signature meta messages.

    If you want the tonic and alteration of a minor key signature, just add 3
    sharps. So if you have the information that the key signature has 4 flats
    and is minor, you get the tonic with ``tonic(-4 + 3)``, which results in
    ``(3, 0.0)``, which in the default scale is F.

    """
    scale = scale or pitch.MAJOR_SCALE
    l = len(scale)
    note, alter = 0, 0
    d = 1 if sf > 0 else -1 if sf < 0 else 0
    for _ in range(d * sf):
        doct, new_note = divmod(note + d * 4, l)
        alter += d * 3.5 - doct * 6 - scale[new_note] + scale[note]
        note = new_note
    return note, alter


class KeySignature:
    r"""Represents a key signature.

    This object can represent the information contained in a LilyPond ``\key``
    command.

    The ``note`` and ``alter`` attributes represent the pitch, and the ``mode``
    the mode. Just as with LilyPond, the mode can be a standard name or a
    custom list of alterations.

    Additionally, it stores the accidentals such as returned by the
    :func:`accidentals` function, and provides conversion of MIDI key numbers
    to sensible pitches.

    """
    def __init__(self, note, alter=0, mode="major", scale=None):
        scale = scale or pitch.MAJOR_SCALE
        self.note = note        #: The note (0..6).
        self.alter = alter      #: The alteration in whole tones (0 by default).
        self.mode = mode        #: The mode (a standard LilyPond mode name like "major" or a custom alterations list).
        self.scale = scale      #: The default scale.
        if isinstance(mode, str):
            mode = alterations(mode_offset[mode])
        self.accidentals = accidentals(note, alter, mode, scale)    #: The accidentals for this key signature.
        #: The tuple of pitch values in the default scale to give a flat instead
        #: of a sharp when converting a MIDI key number to a pitch. The default
        #: value is set in the :py:data:`MAJOR_FLATS` module constant.
        self.flats = pitch.MAJOR_FLATS

    def __repr__(self):
        p = pitch.Pitch(self.note, self.alter)
        return "<{} note,alter={},{} ({}) mode={}>".format(type(self).__name__,
            self.note, self.alter, p, self.mode)

    def pitch(self, key, flats=None):
        """Return a :class:`~.pitch.Pitch` representing the MIDI ``key`` number.

        The pitch's note and alteration are chosen so that they logically fit
        in the key signature.

        The optional ``flats`` parameter is a list of pitch values that get
        flats instead of sharps (if they are not base steps of the current key
        signature). By default, the :attr:`flats` attribute is read, which
        contains by default step 1.5 and 5, resulting (in a C key) in an e-flat
        instead of a d-sharp, and a b-flat instead of an a-sharp.

        An example, A major::

            >>> from quickly.key import KeySignature
            >>> sig = KeySignature(5)
            >>> for key in range(60, 72):
            ...     print(sig.pitch(key, (1.5, 4, 5)))
            ...
            <Pitch note=0, alter=0, octave=1 (c')>
            <Pitch note=0, alter=0.5, octave=1 (cis')>
            <Pitch note=1, alter=0, octave=1 (d')>
            <Pitch note=1, alter=0.5, octave=1 (dis')>
            <Pitch note=2, alter=0, octave=1 (e')>
            <Pitch note=3, alter=0, octave=1 (f')>
            <Pitch note=3, alter=0.5, octave=1 (fis')>
            <Pitch note=4, alter=0, octave=1 (g')>
            <Pitch note=4, alter=0.5, octave=1 (gis')>
            <Pitch note=5, alter=0, octave=1 (a')>
            <Pitch note=5, alter=0.5, octave=1 (ais')>
            <Pitch note=6, alter=0, octave=1 (b')>

        The same MIDI keys in B-flat minor::

            >>> sig = KeySignature(6, -0.5, "minor")
            >>> for key in range(60, 72):
            ...     print(sig.pitch(key))
            ...
            <Pitch note=0, alter=0, octave=1 (c')>
            <Pitch note=1, alter=-0.5, octave=1 (des')>
            <Pitch note=1, alter=0, octave=1 (d')>
            <Pitch note=2, alter=-0.5, octave=1 (ees')>
            <Pitch note=2, alter=0, octave=1 (e')>
            <Pitch note=3, alter=0, octave=1 (f')>
            <Pitch note=4, alter=-0.5, octave=1 (ges')>
            <Pitch note=4, alter=0, octave=1 (g')>
            <Pitch note=5, alter=-0.5, octave=1 (aes')>
            <Pitch note=5, alter=0, octave=1 (a')>
            <Pitch note=6, alter=-0.5, octave=1 (bes')>
            <Pitch note=6, alter=0, octave=1 (b')>

        Or G-sharp major::

            >>> sig = KeySignature(4, 0.5, "major")
            >>> for key in range(60, 72):
            ...     print(sig.pitch(key))
            ...
            <Pitch note=6, alter=0.5, octave=0 (bis)>
            <Pitch note=0, alter=0.5, octave=1 (cis')>
            <Pitch note=0, alter=1, octave=1 (cisis')>
            <Pitch note=1, alter=0.5, octave=1 (dis')>
            <Pitch note=1, alter=1, octave=1 (disis')>
            <Pitch note=2, alter=0.5, octave=1 (eis')>
            <Pitch note=3, alter=0.5, octave=1 (fis')>
            <Pitch note=3, alter=1, octave=1 (fisis')>
            <Pitch note=4, alter=0.5, octave=1 (gis')>
            <Pitch note=4, alter=1, octave=1 (gisis')>
            <Pitch note=5, alter=0.5, octave=1 (ais')>
            <Pitch note=6, alter=0, octave=1 (b')>

        You may alter the :attr:`flats` attribute beforehand to influence the
        returned MIDI pitches. This incantation makes all altered notes flats::

            >>> sig = KeySignature(0)   # C-major
            >>> sig.flats = (.5, 1.5, 3, 4, 5)
            >>> for key in range(60, 72): print(sig.pitch(key))
            ...
            <Pitch note=0, alter=0, octave=1 (c')>
            <Pitch note=1, alter=-0.5, octave=1 (des')>
            <Pitch note=1, alter=0, octave=1 (d')>
            <Pitch note=2, alter=-0.5, octave=1 (ees')>
            <Pitch note=2, alter=0, octave=1 (e')>
            <Pitch note=3, alter=0, octave=1 (f')>
            <Pitch note=4, alter=-0.5, octave=1 (ges')>
            <Pitch note=4, alter=0, octave=1 (g')>
            <Pitch note=5, alter=-0.5, octave=1 (aes')>
            <Pitch note=5, alter=0, octave=1 (a')>
            <Pitch note=6, alter=-0.5, octave=1 (bes')>
            <Pitch note=6, alter=0, octave=1 (b')>

        """
        if flats is None:
            flats = self.flats
        return self._midi_reader(flats)(key)

    @cached_method
    def _midi_reader(self, flats):
        """Return a callable that converts a MIDI key number to a sensible
        :class:`~.pitch.Pitch` for this key signature."""
        # cache for 12 semitones, get a default chromatic scale
        steps = list(chromatic_scale(self.note, self.alter, self.scale, flats))
        # fill in the base tones from the scale (note, alter)
        for note, (base, alter) in enumerate(zip(self.scale, self.accidentals)):
            step = int((base + alter) * 2) % 12
            steps[step] = (note, alter)
        # add octave
        octave = lambda p: -1 if p > 6 else 1 if p < 0 else 0
        steps = [(octave(note + alter) - 5, note, alter) for note, alter in steps]

        def from_midi(key):
            """Return a Pitch from the MIDI key number."""
            octave, step = divmod(key, 12)
            base_octave, note, alter = steps[step]
            return pitch.Pitch(octave + base_octave, note, alter)

        return from_midi

