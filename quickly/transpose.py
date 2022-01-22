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

from .dom import edit, lily, util
from .pitch import MAJOR_SCALE, Pitch, PitchProcessor


class AbstractTransposer:
    """Base class for a Transposer."""

    #: a Transposer at least has an ``octave`` attribute, specifying how many
    #: octaves a pitch will be transposed.
    octave = 0

    def transpose(self, pitch):
        """Transpose the :class:`~.pitch.Pitch`, by modifying its ``note``,
        ``alter`` and possibly ``octave`` attribute."""


class Transposer(AbstractTransposer):
    """Transpose pitches.

    Instantiate with a from- and to-Pitch. The ``scale`` attribute is a list
    with the pitch height of the unaltered step (0 .. 6). The default scale is
    the normal scale: C, D, E, F, G, A, B.

    Adding a Transposer to a Transposer creates a new Transposer, adding up
    both transpositions. Subtracting a Transposer from a Transposer creates a
    new one, reverting the last transposition.

    """

    def __init__(self, from_pitch, to_pitch, scale=MAJOR_SCALE):
        self.scale = scale

        # the number of octaves we need to transpose
        self.octave = to_pitch.octave - from_pitch.octave

        # the number of base note steps (c->d == 1, e->f == 1, etc.)
        self.steps = to_pitch.note - from_pitch.note

        # the number (fraction) of real whole steps
        self.alter = (self.scale[to_pitch.note] + to_pitch.alter -
                      self.scale[from_pitch.note] - from_pitch.alter)

    def __repr__(self):
        return "<{} octave={} steps={} alter={}>".format(type(self).__name__,
            self.octave, self.steps, self.alter)

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

    def __add__(self, other):
        t = type(self).__new__(type(self))
        doct, t.steps = divmod(self.steps + other.steps, 7)
        t.octave = self.octave + other.octave + doct
        t.alter = self.alter + other.alter - doct * 6
        return t

    def __sub__(self, other):
        t = type(self).__new__(type(self))
        doct, t.steps = divmod(self.steps - other.steps, 7)
        t.octave = self.octave - other.octave + doct
        t.alter = self.alter - other.alter + doct * 6
        return t


class Transpose(edit.Edit):
    r"""Transpose pitches using the specified transposer. Arguments:

    :attr:`transposer`: a :class:`Transposer` instance that does the actual work.

    :attr:`processor`: a :class:`~.pitch.PitchProcessor`; a default one is used
    if none is specified.

    :attr:`relative_first_pitch_absolute`: if True, the first pitch in a
    ``\relative`` expression is considered to be absolute, when a startpitch is
    not given. This is LilyPond >= 2.18 behaviour. If False, the first pitch in
    a ``\relative`` expression is considered to be relative to c', if no
    startpitch is given. This is LilyPond < 2.18 behaviour. If not specified,
    the function looks at the LilyPond version from the document. If the
    version can't be determined, defaults to False, the old behaviour.

    You may change these attributes after instantiation.

    """
    def __init__(self, transposer, processor=None, relative_first_pitch_absolute=None):
        #: The :class:`Transposer` that can transpose pitches.
        self.transposer = transposer
        #: The :class:`~.pitch.PitchProcessor`; a default one is used if None is specified.
        self.processor = processor
        #: Whether to consider the first pitch in a ``\relative`` expression absolute
        #: (by default dependent on LilyPond version)
        self.relative_first_pitch_absolute = relative_first_pitch_absolute

    def edit_range(self, r):
        """Perform the transposing on the specified range."""
        node = r.ancestor()
        processor = self.processor or PitchProcessor()

        if not node.is_root():
            processor.find_language(node)

        relative_first_pitch_absolute = self.relative_first_pitch_absolute
        if relative_first_pitch_absolute is None:
            relative_first_pitch_absolute = util.lilypond_version(node) >= (2, 18)

        writable = (lambda n: True) if r.is_full() else (lambda n: n in r)

        def notes(nodes, relative_mode=False):
            """Yield notes (lily.Pitchable) to be transposed.

            If relative_mode is True, also Chord and OctaveCheck nodes are yielded.

            """
            for n in processor.follow_language(nodes):
                if isinstance(n, lily.Pitchable):
                    yield n
                    transpose_absolute(n)   # e.g. notes in markup scores
                elif isinstance(n, (lily.ChordMode, lily.Key)):
                    transpose_no_octave(n)
                elif isinstance(n, lily.Absolute):
                    transpose_absolute(n)
                elif isinstance(n, lily.Relative):
                    transpose_relative(n)
                elif isinstance(n, lily.Fixed):
                    transpose_fixed(n)
                elif isinstance(n, lily.Transpose):
                    pitches, rest = n[:2], n[2:]
                    for p in transpose_pitches(pitches):
                        p.octave -= self.transposer.octave
                    yield from notes(rest)
                elif isinstance(n, (lily.Transposition, lily.StringTuning)):
                    pass    # don't change child nodes
                elif relative_mode and isinstance(n, (lily.Chord, lily.OctaveCheck)):
                    yield n # transpose_relative is interested in those
                else:
                    yield from notes(n, relative_mode)

        def transpose_pitches(nodes):
            """Transpose the notes, and yield their pitches for extra changes."""
            for n in notes(nodes):
                with processor.process(n, writable(n)) as p:
                    self.transposer.transpose(p)
                    yield p

        def transpose_no_octave(nodes):
            r"""Transpose without modifying octave, e.g. for \key or \chordmode."""
            for p in transpose_pitches(nodes):
                p.octave = 0

        def transpose_absolute(nodes):
            """Transpose absolute pitches."""
            for p in transpose_pitches(nodes):
                pass

        def transpose_fixed(node):
            r"""Transpose \fixed pitches: handle octave nicely."""
            nodes = util.skip_comments(node)
            for note in nodes:
                if isinstance(note, lily.Pitchable) and writable(note):
                    # we may change this note, modify the octave
                    offset = self.transposer.octave
                    with processor.process(note) as p:
                        self.transposer.transpose(p)
                else:
                    offset = 0
                for p in transpose_pitches(nodes):
                    p.octave -= offset

        def transpose_relative(node):
            r"""Transpose \relative music."""

            def transpose(note, last_pitch):
                """Transpose one note, return its pitch in absolute form for the next."""
                p = processor.read_node(note)
                default_octave = p.octave - note.octave # the octave of the pitch name itself
                # absolute pitch determined from untransposed pitch of last_pitch
                p.make_absolute(last_pitch)
                if not writable(note):
                    return p
                # we may change this pitch. Make it relative against the
                # transposed last_pitch.
                try:
                    last = last_pitch.transposed
                except AttributeError:
                    last = last_pitch
                # transpose a copy and store that in the transposed attribute of
                # last_pitch. Next time that is used for making the next pitch
                # relative correctly.
                last_pitch = p.copy()
                self.transposer.transpose(p)
                last_pitch.transposed = p.copy()
                if note.oct_check is not None:
                    note.oct_check = p.octave - default_octave
                p.make_relative(last)
                processor.write_node(note, p)
                return last_pitch

            # handle the start pitch
            nodes = list(util.skip_comments(node))
            if len(nodes) > 1 and isinstance(nodes[0], lily.Pitchable):
                start_note, *nodes = nodes
                last_pitch = processor.read_node(start_note)    # untransposed
                if writable(start_note):
                    with processor.process(start_note) as p:
                        self.transposer.transpose(p)
                    last_pitch.transposed = p
                    last_pitch.octave -= self.transposer.octave
                    last_pitch.transposed.octave -= self.transposer.octave
            else:
                last_pitch = Pitch(-1, 3, 0) if relative_first_pitch_absolute else Pitch(0, 0, 0)

            # transpose the notes in the relative expression
            for n in notes(nodes, True):
                if isinstance(n, lily.Pitchable):
                    # note (or positioned rest)
                    last_pitch = transpose(n, last_pitch)
                elif isinstance(n, lily.Chord):
                    # chord
                    stack = [last_pitch]
                    for note in notes(n):
                        stack.append(transpose(note, stack[-1]))
                    last_pitch = stack[:2][-1]  # first note of chord, or the old if chord was empty
                elif isinstance(n, lily.OctaveCheck):
                    # OctaveCheck, also transpose and keep as new last_pitch
                    for note in notes(n):
                        p = processor.read_node(note)
                        last_pitch = p.copy()
                        if writable(note):
                            self.transposer.transpose(p)
                            last_pitch.transposed = p
                            processor.write_node(note, p)
        # Do it!
        transpose_absolute((node,))


def transpose(music, transposer):
    """Convenience function to transpose all notes in music using transposer.

    The ``music`` may be a parce document or cursor, a node range or an element
    node.

    """
    Transpose(transposer).edit(music)

