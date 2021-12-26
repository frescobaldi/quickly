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

from .dom import lily, util
from .pitch import Pitch, PitchProcessor


def rel2abs(node, processor=None, writable=None, first_pitch_absolute=None):
    r"""Convert ``\relative`` music in node to absolute.

    Removes the ``\relative`` command and makes all pitches absolute.

    The ``processor`` is a :class:`~.pitch.PitchProcessor`; a default one is
    used if none is specified.

    The ``writable`` function is a callable that is called with a node, and
    should return True if the node may be modified. If None, all nodes may be
    modified.

    If ``first_pitch_absolute`` is True, the first pitch in a ``\relative``
    expression is considered to be absolute, when a startpitch is not given.
    This is LilyPond >= 2.18 behaviour. If False, the first pitch in a
    ``\relative`` expression is considered to be relative to c', if no
    startpitch is given. This is LilyPond < 2.18 behaviour. If not specified,
    the function looks at the LilyPond version from the document. If the
    version can't be determined, defaults to False, the old behaviour.

    """
    if processor is None:
        processor = PitchProcessor()

    if first_pitch_absolute is None:
        first_pitch_absolute = util.lilypond_version(node) >= (2, 18)

    if not node.is_root():
        processor.find_language(node)

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
            last_pitch = Pitch(3)
        else:
            last_pitch = Pitch(0, 0, 1)

        parent[index:index+1] = nodes   # remove \relative node but keep its child(ren)

        for n in notes(nodes):
            if isinstance(n, lily.Pitchable):
                # note (or positioned rest)
                with processor.pitch(n) as p:
                    p.make_absolute(last_pitch)
                    last_pitch = p
            elif isinstance(n, lily.Chord):
                # chord
                stack = [last_pitch]
                for note in notes(n):
                    with processor.pitch(note) as p:
                        p.make_absolute(stack[-1])
                        stack.append(p)
                last_pitch = stack[:2][-1]  # first note of chord, or the old if chord was empty
            elif isinstance(n, lily.OctaveCheck):
                # OctaveCheck, read last_pitch but remove
                for note in notes(n):
                    last_pitch = processor.read_node(note)
                n.parent.remove(n)
    # Do it!
    for n in processor.follow_language(node.instances_of((lily.Language, lily.Include, lily.Relative))):
        if isinstance(n, lily.Relative) and (not writable or writable(n)):
            make_absolute(n)


def rel2abs_doc(cursor, processor=None, first_pitch_absolute=None):
    """Convert relative music to absolute in the selected range of the
    :class:`~parce.Cursor`'s document.

    If there is no selection, then all relative music is converted.

    For the other arguments see :func:`rel2abs_node`.

    """
    with util.edit(cursor) as (node, writable):
        rel2abs(node, processor, writable, first_pitch_absolute)


def abs2rel(node, processor=None, writable=None, start_pitch=True,
            first_pitch_absolute=None):
    r"""Convert music in absolute notation to ``\relative`` notation.

    The topmost MusicList (``{`` ... ``}`` or ``<<`` ... ``>>``) that has child
    notes gets a Relative parent node.

    The ``processor`` is a :class:`~.pitch.PitchProcessor`; a default one is
    used if none is specified.

    The ``writable`` function is a callable that is called with a node, and
    should return True if the node may be modified. If None, all nodes may be
    modified.

    If ``start_pitch`` is True, a starting pitch is written after the ``\relative``
    command.

    If ``start_pitch`` is False, the ``first_pitch_absolute`` parameter determines
    the meaning of the first pitch in the new Relative expression.
    If ``first_pitch_absolute`` is True, the first pitch in the ``\relative``
    expression is considered to be absolute, when a startpitch is not given.
    This is LilyPond >= 2.18 behaviour. If False, the first pitch in a
    ``\relative`` expression is considered to be relative to c', if no
    startpitch is given. This is LilyPond < 2.18 behaviour. If not specified,
    the function looks at the LilyPond version from the document. If the
    version can't be determined, defaults to False, the old behaviour.

    """
    if processor is None:
        processor = PitchProcessor()

    if not start_pitch and first_pitch_absolute is None:
        first_pitch_absolute = util.lilypond_version(node) >= (2, 18)

    if not node.is_root():
        processor.find_language(node)

    def abs2rel(node):
        """Find MusicList nodes, and if they contain notes, make relative."""
        for n in node.instances_of(lily.MusicList):
            if any(n / lily.Pitchable):
                if not writable or writable(n):
                    make_relative(n)
            else:
                abs2rel(n)

    def make_relative(node):
        """Replace the MusicList node with a Relative node."""
        rel = lily.Relative()

        def get_first_pitch(p):
            if start_pitch:
                last_pitch = Pitch(0, 0, p.octave)
                if p.note > 3:
                    last_pitch.octave += 1
                rel.append(lily.Note('c'))
                processor.write_node(rel[-1], last_pitch)
            elif first_pitch_absolute:
                last_pitch = Pitch(3)
            else:
                last_pitch = Pitch(0, 0, 1)
            return last_pitch

        def relative_note(node, last_pitch):
            with processor.pitch(node) as p:
                if last_pitch is None:
                    last_pitch = get_first_pitch(p)
                lp = p.copy()
                p.make_relative(last_pitch)
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
        node.replace_with(rel)
        rel.append(node)

    # Do it!
    abs2rel(node)


def abs2rel_doc(cursor, processor=None, start_pitch=True, first_pitch_absolute=None):
    r"""Convert music in absolute notation in the selected range of the
    :class:`~parce.Cursor`'s document to ``\relative``.

    If there is no selection, then all music expressions that contain notes are
    converted.

    For the other arguments see :func:`abs2rel_node`.

    """
    with util.edit(cursor) as (node, writable):
        abs2rel(node, processor, writable, start_pitch, first_pitch_absolute)


