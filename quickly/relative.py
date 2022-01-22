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
Utilities and functions to manipulate music written in relative pitches.
"""

from .dom import edit, lily, util
from .pitch import Pitch, PitchProcessor


class Rel2abs(edit.Edit):
    r"""Convert ``\relative`` music to absolute.

    Removes the ``\relative`` command and makes all pitches absolute.

    :attr:`processor`: a :class:`~.pitch.PitchProcessor`; a default one is used
    if none is specified.

    :attr:`first_pitch_absolute`: if True, the first pitch in a ``\relative``
    expression is considered to be absolute, when a startpitch is not given.
    This is LilyPond >= 2.18 behaviour. If False, the first pitch in a
    ``\relative`` expression is considered to be relative to c', if no
    startpitch is given. This is LilyPond < 2.18 behaviour. If not specified,
    the function looks at the LilyPond version from the document. If the
    version can't be determined, defaults to False, the old behaviour.

    You may change these attributes after instantiation.

    """
    def __init__(self, processor=None, first_pitch_absolute=None):
        #: The :class:`~.pitch.PitchProcessor`; a default one is used if None is specified.
        self.processor = processor
        #: Whether to consider the first pitch in a ``\relative`` expression absolute
        #: if a start pitch is not used (by default dependent on LilyPond version).
        self.first_pitch_absolute = first_pitch_absolute

    def edit_range(self, r):
        """Do the pitch conversion."""
        node = r.ancestor()
        processor = self.processor or PitchProcessor()

        if not node.is_root():
            processor.find_language(node)

        first_pitch_absolute = self.first_pitch_absolute
        if first_pitch_absolute is None:
            first_pitch_absolute = util.lilypond_version(node) >= (2, 18)

        def notes(nodes):
            """Yield note/rest, chord and octavecheck; follow pitch language."""
            for n in processor.follow_language(nodes):
                if isinstance(n, lily.Pitchable):
                    yield n
                    # music in markup expressions?
                    for n in node.instances_of(lily.Relative):
                        make_absolute(n)
                elif isinstance(n, (lily.Chord, lily.OctaveCheck)):
                    yield n
                elif isinstance(n, lily.Relative):
                    make_absolute(n)
                elif isinstance(n, (
                        lily.ChordMode, lily.Key, lily.Absolute, lily.Fixed,
                        lily.Transpose, lily.Transposition, lily.StringTuning,
                    )):
                    pass
                else:
                    yield from notes(n)

        def make_absolute(node):
            """Convert this relative music to absolute music."""
            parent = node.parent
            index = parent.index(node)

            nodes = list(util.skip_comments(node))
            if len(nodes) > 1 and isinstance(nodes[0], lily.Note):
                start_note, *nodes = nodes
                last_pitch = processor.read_node(start_note)
            elif first_pitch_absolute:
                last_pitch = Pitch(-1, 3, 0)
            else:
                last_pitch = Pitch(0, 0, 0)

            parent[index:index+1] = nodes   # remove \relative node but keep its child(ren)

            for n in notes(nodes):
                if isinstance(n, lily.Pitchable):
                    # note (or positioned rest)
                    with processor.process(n) as p:
                        p.make_absolute(last_pitch)
                        last_pitch = p
                elif isinstance(n, lily.Chord):
                    # chord
                    stack = [last_pitch]
                    for note in notes(n):
                        with processor.process(note) as p:
                            p.make_absolute(stack[-1])
                            stack.append(p)
                    last_pitch = stack[:2][-1]  # first note of chord, or the old if chord was empty
                elif isinstance(n, lily.OctaveCheck):
                    # OctaveCheck, read last_pitch but remove
                    for note in notes(n):
                        last_pitch = processor.read_node(note)
                    n.parent.remove(n)
        # Do it!
        nodes = r.instances_of((lily.Language, lily.Include, lily.Relative))
        for n in processor.follow_language(nodes):
            if isinstance(n, lily.Relative) and r.in_range():
                make_absolute(n)


def rel2abs(music):
    """Convenience function to convert relative music to absolute in music.

    The ``music`` may be a parce document or cursor, a node range or an element
    node.

    """
    return Rel2abs().edit(music)


class Abs2rel(edit.Edit):
    r"""Convert music in absolute notation to ``\relative`` notation.

    The topmost :class:`~quickly.dom.lily.MusicList` (``{`` ... ``}`` or ``<<``
    ... ``>>``) that has child notes gets a :class:`~quickly.dom.lily.Relative`
    parent node.

    :attr:`processor`: a :class:`~.pitch.PitchProcessor`; a default one is used
    if none is specified.

    :attr:`start_pitch`: if True, a starting pitch is written after the
    ``\relative`` command.

    :attr:`start_pitch`: if False, the :attr:`first_pitch_absolute` attribute
    determines the meaning of the first pitch in the new Relative expression.
    If :attr:`first_pitch_absolute` is True, the first pitch in the
    ``\relative`` expression is considered to be absolute, when a startpitch is
    not given. This is LilyPond >= 2.18 behaviour. If False, the first pitch in
    a ``\relative`` expression is considered to be relative to c', if no
    start pitch is given. This is LilyPond < 2.18 behaviour. If not specified,
    the function looks at the LilyPond version from the document. If the
    version can't be determined, defaults to False, the old behaviour.

    You may change these attributes after instantiation.

    """
    def __init__(self, processor=None, start_pitch=True, first_pitch_absolute=None):
        #: The :class:`~.pitch.PitchProcessor`; a default one is used if None is specified.
        self.processor = processor
        #: Whether to write a starting pitch after the ``\relative`` command.
        self.start_pitch = start_pitch
        #: Whether to consider the first pitch in a ``\relative`` expression absolute
        #: if a start pitch is not used (by default dependent on LilyPond version).
        self.first_pitch_absolute = first_pitch_absolute

    def _get_settings(self, node):
        """Get preferences for node."""
        first_pitch_absolute = self.first_pitch_absolute
        if not self.start_pitch and first_pitch_absolute is None:
            first_pitch_absolute = util.lilypond_version(node) >= (2, 18)

        processor = self.processor or PitchProcessor()

        if not node.is_root():
            processor.find_language(node)

        return processor, first_pitch_absolute

    def edit_range(self, r):
        """Do the pitch conversion."""
        processor, first_pitch_absolute = self._get_settings(r.ancestor())

        def abs2rel():
            """Find MusicList nodes, and if they contain notes, make relative."""
            for n in r.instances_of((lily.MusicList, lily.Relative, lily.ChordMode)):
                if isinstance(n, lily.MusicList):
                    if any(n / lily.Pitchable) and r.in_range():
                        r.node = self._make_relative_internal(r.node, processor, first_pitch_absolute)
                    else:
                        abs2rel()
        # Do it!
        abs2rel()

    def make_relative(self, node):
        """Make al notes and pitched rests in the specified :class:`~quickly.dom.lily.MusicList` or
        :class:`~quickly.dom.lily.SimultaneousMusicList` node relative.

        Returns a :class:`~quickly.dom.lily.Relative` node with the modified
        music list appended.

        Replace the node in its parent with the returned node if desired.

        """
        processor, first_pitch_absolute = self._get_settings(node)
        return self._make_relative_internal(node, processor, first_pitch_absolute)

    def _make_relative_internal(self, node, processor, first_pitch_absolute):
        """Implementation of make_relative() with settings."""
        rel = lily.Relative()

        def get_first_pitch(p):
            if self.start_pitch:
                last_pitch = Pitch(p.octave, 0, 0)
                if p.note > 3:
                    last_pitch.octave += 1
                rel.append(processor.pitchable(last_pitch, lily.Pitch))
            elif first_pitch_absolute:
                last_pitch = Pitch(-1, 3, 0)
            else:
                last_pitch = Pitch(0, 0, 0)
            return last_pitch

        def relative_note(node, last_pitch):
            with processor.process(node) as p:
                default_octave = p.octave - node.octave
                if last_pitch is None:
                    last_pitch = get_first_pitch(p)
                lp = p.copy()
                p.make_relative(last_pitch)
                p.octave += default_octave
            return lp

        def relative_notes(node, last_pitch=None):
            for n in processor.follow_language(node):
                if isinstance(n, lily.Pitchable):
                    last_pitch = relative_note(n, last_pitch)
                elif isinstance(n, lily.Chord):
                    stack = [last_pitch]
                    for note in n / lily.Pitchable:
                        stack.append(relative_note(note, last_pitch))
                    last_pitch = stack[:2][-1]  # first of chord or old if empty
                elif isinstance(n, (
                    lily.ChordMode, lily.Key, lily.Absolute, lily.Fixed,
                    lily.Transpose, lily.Transposition, lily.StringTuning,
                )):
                    pass
                else:
                    last_pitch = relative_notes(n, last_pitch)
            return last_pitch

        relative_notes(node)
        rel.append(node)
        return rel


def abs2rel(music):
    """Convenience function to convert absolute music to relative.

    The ``music`` may be a parce document or cursor, a node range or an element
    node.

    """
    return Abs2rel().edit(music)


