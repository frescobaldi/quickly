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
Classes and convenience functions to manipulate the rhythm of music.

For all convenience functions: the ``music`` argument may be a
:class:`parce.Document`, a parce :class:`~parce.document.Cursor` (optionally
only selecting a range of the document to edit), a node :class:`~.node.Range`
or any :class:`~.dom.element.Element` node (DOM tree).

"""


import itertools


from .dom import edit, lily, util
from .duration import duration


class EditRhythm(edit.Edit):
    """Base class for rhythm editing operations.
    """
    def durables(self, r):
        """Yield all Durable instances in range."""
        for n in r.nodes():
            if isinstance(n, lily.Durable):
                yield n

    def edit_range(self, r):
        """Perform our operations on all Durables in the range."""
        prev = None
        for n in self.durables(r):
            prev = self.process(n, prev)

    def previous_duration(self, node):
        """Return the Duration of node.previous_durable() or a default Duration."""
        prev = node.previous_durable()
        if prev:
            return next(prev / lily.Duration)
        else:
            return lily.Duration.from_string('4')

    def process(self, node, prev):
        """Implement to perform an operation on the ``node``.

        The ``prev`` parameter is the value the previous call to this method
        returned, it is None on the first call.

        """
        raise NotImplementedError


class Remove(EditRhythm):
    """Remove duration from Durable nodes, if allowed."""
    def process(self, node, prev):
        """Remove duration from ``node``; ``prev`` is unused."""
        if not node.duration_required:
            del node.duration


class RemoveScaling(EditRhythm):
    """Remove scaling from Durable nodes."""
    def process(self, node, prev):
        """Remove scaling from ``node``; ``prev`` is unused."""
        del node.scaling


class RemoveFractionScaling(EditRhythm):
    """Remove scaling if it contains a fraction."""
    def process(self, node, prev):
        """Remove scaling if it contains a fraction from ``node``; ``prev`` is unused."""
        s = node.scaling
        if s is not None and int(s) != s:
            del node.scaling


class RhythmExplicit(EditRhythm):
    """Add the current duration to all nodes that don't have one."""
    def process(self, node, prev):
        """Add duration to ``node`` if absent; ``prev`` is the previous Duration node."""
        if node.duration is None:
            if prev is None:
                prev = self.previous_duration(node)
            node.add(prev.copy())
        elif node.duration_sets_previous:
            prev = next(node / lily.Duration)
        return prev


class RhythmImplicit(EditRhythm):
    """Remove reoccurring durations."""
    def process(self, node, prev):
        """Remove duration from ``node`` if same as (duration, scaling) tuple in ``prev``."""
        dur, scaling = node.duration, node.scaling
        if dur:
            if (dur, scaling) == prev and not node.duration_required:
                del node.duration
            elif node.duration_sets_previous:
                prev = (dur, scaling)
        return prev


class RhythmImplicitPerLine(EditRhythm):
    """Remove reoccurring durations within the same line, but always add a
    duration to the first Durable on a line.

    This only works when editing from a parce Document, otherwise we don't know
    the newlines in the original text. If there is no parce Document, the
    behaviour is the same as :class:`RhythmImplicit`.

    """
    def process(self, node, prev):
        """Remove duration from ``node`` if duration and text block are the
        same as [duration, scaling, block] list in ``prev``.

        """
        dur, scaling = node.duration, node.scaling
        block = self.find_block(node)
        if dur:
            if [dur, scaling, block] == prev and not node.duration_required:
                del node.duration
            elif node.duration_sets_previous:
                prev = [dur, scaling, block]
        elif block and prev and prev[2] != block:
            node.duration, node.scaling = prev[:2]
            prev[2] = block
        return prev


class RhythmTransform(EditRhythm):
    """Transform durations using a :class:`~.duration.Transform`.

    This can be used for all types of shift and scale operations. For example,
    to add a dot to all durations::

        >>> from quickly.rhythm import RhythmTransform
        >>> from quickly.duration import Transform
        >>> from quickly.dom import read
        >>> music = read.lily_document(r"{ c4 d8 e16 f g2 }")
        >>> t = Transform(dotcount=1) # add a dot
        >>> RhythmTransform(t).edit(music)
        >>> music.write()
        '{ c4. d8. e16. f g2. }'

    Remove a dot::

        >>> t = Transform(dotcount=-1)
        >>> RhythmTransform(t).edit(music)
        >>> music.write()
        '{ c4 d8 e16 f g2 }'

    Double durations::

        >>> t = Transform(log=-1)
        >>> RhythmTransform(t).edit(music)
        >>> music.write()
        '{ c2 d4 e8 f g1 }'

    Add a scaling factor::

        >>> t = Transform(scale=1/3)
        >>> RhythmTransform(t).edit(music)
        >>> music.write()
        '{ c2*1/3 d4*1/3 e8*1/3 f g1*1/3 }'

    Or modify all in one go::

        >>> t = Transform(1, 1, 3)
        >>> RhythmTransform(t).edit(music)
        >>> music.write()
        '{ c4. d8. e16. f g2. }'

    """
    def __init__(self, transform):
        self._transform = transform.transform   # store the transform method

    def process(self, node, prev):
        """Apply Transform to ``node`` if it has a duration; ``prev`` is unused."""
        dur = node.duration
        if dur is not None:
            node.duration, node.scaling = self._transform(dur, node.scaling)


class CopyRhythm(EditRhythm):
    """Extract durations from a range in the form of (duration, scaling) tuples.

    The durations are returned by :meth:`edit_range` and thus also all other
    edit methods. Durables without duration yield a None. Example::

        >>> from quickly.dom import read
        >>> music = read.lily_document(r"{ c4 d8 e16 f g2 }")
        >>> from quickly.rhythm import CopyRhythm
        >>> durations = CopyRhythm().edit(music)
        >>> durations
        [(Fraction(1, 4), 1.0), (Fraction(1, 8), 1.0), (Fraction(1, 16), 1.0),
        None, (Fraction(1, 2), 1.0)]

    """
    readonly = True

    def edit_range(self, r):
        """Return the list of extracted durations."""
        def rhythm():
            for n in self.durables(r):
                dur = n.duration
                yield (dur, n.scaling) if dur else None
        return list(rhythm())


class PasteRhythm(EditRhythm):
    """Paste durations such as returned by :class:`CopyRhythm` into music.

    The durations are an iterable of either the two-tuple (duration, scaling)
    or None. If ``cycle`` is True, the pasted durations are endlessly repeated
    in the selected range. Example::

        >>> from fractions import Fraction
        >>> durations = [(Fraction(1, 4), 1), (Fraction(3, 16), 0.5), None]
        >>> from quickly.dom import read
        >>> music = read.lily_document(r"{ c4 d8 e16 f g2 }")
        >>> from quickly.rhythm import PasteRhythm
        >>> PasteRhythm(durations).edit(music)
        >>> music.write()
        '{ c4 d8.*1/2 e f4 g8.*1/2 }'

    """
    def __init__(self, durations, cycle=True):
        self._durations = durations
        self.cycle = cycle

    def edit_range(self, r):
        """Paste the durations."""
        durs = (itertools.cycle if self.cycle else iter)(self._durations)
        for node, duration in zip(self.durables(r), durs):
            if duration:
                node.duration, node.scaling = duration
            elif not node.duration_required:
                del node.duration


def remove(music):
    """Remove all durations from music."""
    return Remove().edit(music)


def remove_scaling(music):
    """Remove all scalings from the durations in music."""
    return RemoveScaling().edit(music)


def remove_fraction_scaling(music):
    """Convenience function to remove all scalings that contain a fraction
    (like ``1/3``) from the durations in music."""
    return RemoveFractionScaling().edit(music)


def explicit(music):
    """Add the current duration to all notes, chords, rests etc in the music."""
    return RhythmExplicit().edit(music)


def implicit(music, per_line=False):
    """Remove all reoccuring durations from the music.

    If ``per_line`` is True, the first duration in a text line is not removed,
    but rather added if absent. (This only works when editing a parce document
    or cursor, otherwise we can't know the newlines in the original text.)

    An example::

        >>> import parce
        >>> import quickly.rhythm
        >>> d=parce.Document(quickly.find('lilypond'), r'''music = {
        ...   c4 d8 e8 f8 g8 a4
        ...   g f e4 d
        ...   c d4 e2
        ... }
        ... ''', transformer=True)
        >>> quickly.rhythm.implicit(d, True)
        >>> print(d.text())
        music = {
          c4 d8 e f g a4
          g4 f e d
          c4 d e2
        }

    """
    cls = RhythmImplicitPerLine if per_line else RhythmImplicit
    return cls().edit(music)


def transform(music, log=0, dotcount=0, scale=1):
    """Transform durations in music by modifying log, dot count and/or scaling.

    Increasing the log by 1 halves the durations, decreasing the log doubles
    them. (See also the :mod:`.duration` module.) An example, where the
    duration is halved and one dot is added::

        >>> from quickly.dom import read
        >>> from quickly import rhythm
        >>> m = read.lily_document("{ c4 d8 e16 f g2 }")
        >>> rhythm.transform(m, 1, 1)
        >>> m.write()
        '{ c8. d16. e32. f g4. }'

    """
    from .duration import Transform
    return RhythmTransform(Transform(log, dotcount, scale)).edit(music)


def copy(music):
    """Extract durations from music.

    Every duration is a two-tuple of integers or fractions (duration, scaling),
    or None for Durables without duration.

    """
    return CopyRhythm().edit(music)


def paste(music, durations, cycle=True):
    """Replace durations in the music with the specified durations.

    Every duration is a two-tuple of integers or fractions (duration, scaling),
    or None for Durables without duration.

    """
    return PasteRhythm(durations, cycle).edit(music)

