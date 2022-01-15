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
Functionality to compute the time length of musical expressions.
"""


import collections

from . import duration
from .dom import lily


#: The result value (if not None) of the :meth:`~Time.position` and
#: :meth:`~Time.duration` methods.
Result = collections.namedtuple("Result", "node time")
Result.node.__doc__ = "The topmost Music expression."
Result.time.__doc__ = "The position or duration time value."


class Time:
    r"""Compute the length of musical expressions.

    A :class:`~.scope.Scope`, if given using the ``scope`` parameter, is used
    to resolve include files. If no scope is given, only searches the current
    DOM document for variable assignments.

    If a scope is given, include commands are followed and ``wait`` determines
    whether to wait for ongoing transformations of external DOM documents. If
    wait is False, and a transformation is not yet finished the include is not
    followed.

    An example::

        >>> import parce, quickly.time
        >>> d = parce.Document(quickly.find('lilypond'), r'''
        ... music = { c4 d e f }
        ...
        ... { c2 \music g a b8 g f d }
        ... ''', transformer=True)
        >>> m = d.get_transform(True)
        >>> m.dump()
        <lily.Document (2 children)>
         ├╴<lily.Assignment music (3 children)>
         │  ├╴<lily.Identifier (1 child)>
         │  │  ╰╴<lily.Symbol 'music' [1:6]>
         │  ├╴<lily.EqualSign [7:8]>
         │  ╰╴<lily.MusicList (4 children) [9:21]>
         │     ├╴<lily.Note 'c' (1 child) [11:12]>
         │     │  ╰╴<lily.Duration Fraction(1, 4) [12:13]>
         │     ├╴<lily.Note 'd' [14:15]>
         │     ├╴<lily.Note 'e' [16:17]>
         │     ╰╴<lily.Note 'f' [18:19]>
         ╰╴<lily.MusicList (8 children) [23:49]>
            ├╴<lily.Note 'c' (1 child) [25:26]>
            │  ╰╴<lily.Duration Fraction(1, 2) [26:27]>
            ├╴<lily.IdentifierRef 'music' [28:34]>
            ├╴<lily.Note 'g' [35:36]>
            ├╴<lily.Note 'a' [37:38]>
            ├╴<lily.Note 'b' (1 child) [39:40]>
            │  ╰╴<lily.Duration Fraction(1, 8) [40:41]>
            ├╴<lily.Note 'g' [42:43]>
            ├╴<lily.Note 'f' [44:45]>
            ╰╴<lily.Note 'd' [46:47]>
        >>> t=quickly.time.Time()
        >>> t.position(m[1][0])         # first note in second expression
        Result(node=<lily.MusicList (8 children) [23:49]>, time=0)
        >>> t.position(m[1][1])         # \music identifier ref
        Result(node=<lily.MusicList (8 children) [23:49]>, time=Fraction(1, 2))
        >>> t.position(m[1][2])         # the g after the \music ref
        Result(node=<lily.MusicList (8 children) [23:49]>, time=Fraction(3, 2))
        >>> t.length(m[0][2])           # the \music expression
        Fraction(1, 1)
        >>> t.length(m[1])              # total length of second expression
        Fraction(3, 1)                  # referenced \music correctly counted in :)
        >>> t.duration(m[1][0], m[1][2])# length of "c2 \music g" part (g has duration 2)
        Result(node=<lily.MusicList (8 children) [23:49]>, time=Fraction(2, 1))

    There are convenient methods to get the musical position of a parce
    :class:`~parce.Cursor`::

        >>> c = parce.Cursor(d, 44, 47)
        >>> c.text()                    # two notes
        'f d'
        >>> t.cursor_position(c)        # length or music before the cursor
        Result(node=<lily.MusicList (8 children) [23:49]>, time=Fraction(11, 4))
        >>> t.cursor_duration(c)        # duration of the selected music
        Result(node=<lily.MusicList (8 children) [23:49]>, time=Fraction(1, 4))

    LilyPond music functions that alter durations are recognized, and are
    abstracted in simple transformations that alter log, dotcount and/or
    scaling. An example::

        >>> from quickly.dom import read
        >>> m = read.lily(r"\tuplet 3/2 { c8 d e }")
        >>> t.length(m)
        Fraction(1, 4)
        >>> m[1][1]                     # a single note in the tuplet
        <lily.Note 'd'>
        >>> t.length(m[1][1])
        Fraction(1, 12)
        >>> m = read.lily(r"\shiftDurations #1 #1 { c4 d e f }")
        >>> t.length(m)         # note value halved and dot added, so should be 3/4
        Fraction(3, 4)
        >>> m[2][2]
        <lily.Note 'e'>
        >>> t.length(m[2][2])   # autodiscovers the current duration transform
        Fraction(3, 16)

    """
    def __init__(self, scope=None, wait=False):
        self.scope = scope  #: Our :class:`~.scope.Scope`.
        self.wait = wait    #: If True, parce transformations are waited for.

    def _follow_trail(self, node, trail, transform):
        """Compute length; return length, node, transform at end of trail."""
        time = 0
        for index in trail:
            if index and node.is_sequential():
                time += self.length(node, index, transform)
            node = node[index]
            if isinstance(node, lily.Music):
                transform += node.transform()
        return time, node, transform

    @staticmethod
    def _music_child(node):
        """Return the topmost Music child or None."""
        # avoid picking one note of a chord
        if isinstance(node, lily.Chord):
            return node
        for chord in node << lily.Chord:
            return chord
        while node:
            if isinstance(node, lily.Music) or isinstance(node.parent, lily.Music):
                return node
            node = node.parent

    @staticmethod
    def _preceding_music(node):
        """Return a two-tuple(music, trail).

        The ``node`` must be (a child of) a :class:`~.dom.lily.Music` instance.
        The returned music is the topmost Music ancestor and the trail lists
        the indices of the children upto the node.

        """
        trail = []
        for p, i in node.ancestors_with_index():
            if not isinstance(p, lily.Music):
                break
            trail.append(i)
            node = p
        trail.reverse()
        return node, trail

    @staticmethod
    def transform(node):
        """Return the transform in this node, counted from the topmost Music ancestor."""
        t = node.transform() if isinstance(node, lily.Music) else duration.Transform()
        for p in node.ancestors():
            if not isinstance(p, lily.Music):
                break
            t += p.transform()
        return t

    def length(self, node, end=None, transform=None):
        """Return the total musical length of this node until ``end``.

        If end is None, all child nodes are counted. For Durable and Reference
        nodes, the end value is ignored. The duration is transformed if a
        :class:`~.duration.Transform` is specified.

        """
        prev_dur = None

        def remote_length(refnode, transform):
            """Return the length of the value of a IdentifierRef node."""
            n, s = refnode.get_value_with_scope(self.scope, self.wait)
            while isinstance(n, lily.Reference):
                n, s = n.get_value_with_scope(s, self.wait)
            if isinstance(n, lily.Music):
                return type(self)(s, self.wait).length(n, None, transform)
            return 0

        def durable_length(node, transform):
            """Return the length of the Durable."""
            nonlocal prev_dur
            length = node.length(transform)
            if length == -1:
                if not prev_dur:
                    prev_dur = lily.previous_duration(node)
                length = transform.length(*prev_dur)
            elif node.duration_sets_previous:
                prev_dur = node.duration_scaling
            return length

        def times(nodes, transform):
            """Yield the lengths of the given nodes."""
            for node in nodes:
                if isinstance(node, lily.Durable):
                    yield durable_length(node, transform)
                elif isinstance(node, lily.Music):
                    l = times(node, transform + node.transform())
                    yield sum(l) if node.is_sequential() else max(l, default=0)
                elif isinstance(node, lily.Reference):
                    yield remote_length(node, transform)

        if transform is None:
            transform = self.transform(node)

        if isinstance(node, lily.Durable):
            return durable_length(node, transform)
        elif isinstance(node, lily.Music):
            if node.is_sequential():
                return sum(times(node[:end], transform))
            elif end is None:
                return max(times(node, transform), default=0)
        elif isinstance(node, lily.Reference):
            return remote_length(node, transform)
        return 0

    def position(self, node, include=False):
        """Return a :class:`Result` two-tuple(node, time).

        The ``node`` argument must be (a child of) a :class:`~.dom.lily.Music`
        instance.

        The returned ``node`` is the topmost Music element, and the ``time`` is
        the computed length of all preceding music nodes. If ``include`` is
        True, the node's length itself is also added.

        """
        music, trail = self._preceding_music(node)
        time, node, transform = self._follow_trail(music, trail, music.transform())
        if include:
            time += self.length(node, None, transform)
        return Result(music, time)

    def duration(self, start_node, end_node):
        """Return a :class:`Result` two-tuple(node, time) or None.

        The returned ``node`` is the topmost Music element both nodes must be a
        descendant of. Both nodes must be (children of)
        :class:`~.dom.lily.Music` nodes. If they don't share the same ancestor,
        None is returned. The returned ``time`` value can be negative when the
        end node precedes the start node.

        """
        music, start_trail = self._preceding_music(start_node)
        end_music, end_trail = self._preceding_music(end_node)
        if end_music is not music:
            return

        node = music
        transform = node.transform()

        # common part, just follow transform
        index = -1
        for index, (pos, end) in enumerate(zip(start_trail, end_trail)):
            if pos != end:
                break
            node = node[pos]
            transform += node.transform()
        else:
            index += 1

        # compute time only for differing part of the trails
        start_time = self._follow_trail(node, start_trail[index:], transform)[0]
        end_time, node, transform = self._follow_trail(node, end_trail[index:], transform)
        end_time += self.length(node, None, transform)
        return Result(music, end_time - start_time)

    def cursor_position(self, cursor):
        """Return a :class:`Result` two-tuple(node, time) or None.

        The ``node`` is the music expression the cursor is in, and the ``time``
        is the time offset from the start of that expression to the cursor's
        position.

        Returns None if the cursor is not in music.

        """
        dom = cursor.document().get_transform(self.wait)
        if dom:
            node = dom.find_descendant_right(cursor.pos)
            c = self._music_child(node)
            if c:
                return self.position(c)

    def cursor_duration(self, cursor):
        """Return a :class:`Result` two-tuple(node, time) or None.

        The ``node`` is the music expression the cursor is in, and the ``time``
        is the length of the selected music fragment.

        Returns None if there's no selection or the selection's start and/or
        end are not in music, or in different music expressions.

        """
        if cursor.has_selection():
            pos, end = cursor.selection()
            dom = cursor.document().get_transform(self.wait)
            if dom:
                n = dom.find_descendant_right(pos)
                if n:
                    start_node = self._music_child(n)
                    if start_node:
                        n = dom.find_descendant_left(end)
                        if n:
                            end_node = self._music_child(n)
                            if end_node:
                                result = self.duration(start_node, end_node)
                                if result and result.time >= 0:
                                    return result


