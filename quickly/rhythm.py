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
Utilities and functions to manipulate the rhythm of music.
"""

from .dom import edit, lily, util



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
        if not node.duration_required:
            del node.duration


class RemoveScaling(EditRhythm):
    """Remove scaling from Durable nodes."""
    def process(self, node, prev):
        del node.scaling


class RemoveFractionScaling(EditRhythm):
    """Remove scaling if it contains a fraction."""
    def process(self, node, prev):
        s = node.scaling
        if s is not None and int(s) != s:
            del node.scaling


class RhythmExplicit(EditRhythm):
    """Add the current duration to all nodes that don't have one."""
    def process(self, node, prev):
        if node.duration is None:
            if prev is None:
                prev = self.previous_duration(node)
            node.insert_duration(prev.copy())
        elif node.duration_sets_previous:
            prev = next(node / lily.Duration)
        return prev


class RhythmImplicit(EditRhythm):
    """Remove reoccurring durations."""
    def process(self, node, prev):
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
    behaviour is the same as class:`RhythmImplicit`.

    """
    def process(self, node, prev):
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


