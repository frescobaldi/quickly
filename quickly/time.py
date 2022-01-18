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
import itertools

from . import datatypes, duration
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

    .. note::

       As a :class:`Time` instance uses some caching for the duration of
       individual notes, don't rely on its computations while also modifying
       durations of music notes, rests etc.

    """
    def __init__(self, scope=None, wait=False):
        self.scope = scope  #: Our :class:`~.scope.Scope`.
        self.wait = wait    #: If True, parce transformations are waited for.
        self.get_duration = lily.duration_getter()

    def __repr__(self):
        return "<{} scope={} wait={}>".format(
            type(self).__name__, self.scope, self.wait)

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

    def length(self, node):
        """Return the musical length of this node."""
        context = TimeContext(self)
        if isinstance(node, (lily.Music, lily.Reference)):
            ancestors = list(itertools.takewhile(lily.is_music, node.ancestors()))
            for p in reversed(ancestors):
                context = context.enter(p)
        return context.length(node)

    def position(self, node, include=False):
        """Return a :class:`Result` two-tuple(node, time).

        The ``node`` argument must be (a child of) a :class:`~.dom.lily.Music`
        instance.

        The returned ``node`` is the topmost Music element, and the ``time`` is
        the computed length of all preceding music nodes. If ``include`` is
        True, the node's length itself is also added.

        """
        music, trail = self._preceding_music(node)
        context = TimeContext(self)
        context, node, length = context._follow_trail(music, trail)
        if include:
            length += context.length(node)
        return Result(music, length)

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
        context = TimeContext(self)

        # common part, just follow transform
        index = -1
        for index, (pos, end) in enumerate(zip(start_trail, end_trail)):
            context = context.enter(node)
            if pos != end:
                break
            node = node[pos]
        else:
            index += 1

        # compute time only for differing part of the trails
        start_time = context._follow_trail(node, start_trail[index:])[2]
        context, node, end_time = context._follow_trail(node, end_trail[index:])
        end_time += context.length(node)
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


class TimeContext:
    """Encapsulates the transform and properties during time calculations.

    The transform (:class:`~.duration.Transform`) determines the actual length
    of Durable objects, and the properties (:class:`~.datatypes.Properties`)
    are forwarded to child contexts, where inside the
    :meth:`~.dom.lily.Music.time_length` of Music nodes values can be read and
    also modified.

    """
    def __init__(self, time, transform=None, properties=None):
        self.time = time    #: The :class:`Time` object we originate from.
        self.transform = transform or duration.Transform()      #: The current Transform.
        self.properties = properties or datatypes.Properties()  #: The current Properties.

    def __repr__(self):
        return "<{} time={} transform={} properties={}>".format(
            type(self).__name__, self.time, self.transform, self.properties)

    def _follow_trail(self, node, trail):
        """Compute length; return context, node and length at end of trail."""
        context = self
        length = 0
        for index in trail:
            context = context.enter(node)
            if index and node.is_sequential():
                length += node.time_length(context, index)
            node = node[index]
        return context, node, length

    def enter(self, node, time=None):
        """Return a new TimeContext.

        The returned TimeContext uses the new :class:`Time` (if given,
        otherwise the same as ours) and adds the :class:`~.duration.Transform`
        and the :class:`~.datatypes.Properties` of the specified ``node`` to
        the current ones.

        """
        t = self.transform
        transform = node.transform()
        if transform:
            t += transform
        p = self.properties
        properties = node.properties()
        if properties:
            p += properties
        return type(self)(time or self.time, t, p)

    def length(self, node, end=None):
        """Return the length of any node.

        Follows variable references using the scope (if given to the
        :class:`Time` instance) and calls :meth:`~.dom.lily.Music.time_length`
        for Music nodes. Returns 0 for any other, non-musical, node.

        """
        if isinstance(node, lily.Reference):
            return self.remote_length(node)
        elif isinstance(node, lily.Music):
            context = self.enter(node)
            return node.time_length(context, end)
        return 0

    def durable_length(self, node):
        """Return the length of a Durable node."""
        return self.transform.length(*self.time.get_duration(node))

    def remote_length(self, node):
        """Return the length of the value of an IdentifierRef node.

        Returns 0 if the node can't be found or is no music.

        """
        node, scope = node.get_value_with_scope(self.time.scope, self.time.wait)
        while isinstance(node, lily.Reference):
            node, scope = node.get_value_with_scope(scope, self.time.wait)
        if isinstance(node, lily.Music):
            time = type(self.time)(scope, self.time.wait)
            return node.time_length(self.enter(node, time), None)
        return 0

