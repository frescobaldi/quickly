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


from . import duration
from .dom import lily


class Time:
    """Compute the length of musical expressions.

    A :class:`~.scope.Scope`, if given using the ``scope`` parameter, is used
    to resolve include files. If no scope is given, only searches the current
    DOM document; the yielded scope is then always None.

    If a scope is given, include commands are followed and ``wait`` determines
    whether to wait for ongoing transformations of external DOM documents. If
    wait is False, and a transformation is not yet finished the included
    document's toplevel nodes will not be searched for variable assignments.

    An example::

        >>> import parce, quickly
        >>> from quickly import time
        >>> d=parce.Document(quickly.find('lilypond'), r'''
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
        >>> t=time.Time()
        >>> t.position(m[1][0])         # first note in second expression
        (<lily.MusicList (8 children) [23:49]>, 0)
        >>> t.position(m[1][1])         # \music identifier ref
        (<lily.MusicList (8 children) [23:49]>, Fraction(1, 2))
        >>> t.position(m[1][2])         # the g after the \music ref
        (<lily.MusicList (8 children) [23:49]>, Fraction(3, 2))
        >>> t.length(m[0][2])           # the \music expression
        Fraction(1, 1)
        >>> t.length(m[1])              # total length of second expression
        Fraction(3, 1)                  # referenced \music correctly counted in :)
        >>> t.duration(m[1][0], m[1][2])
        Fraction(2, 1)                  # length of "c2 \music g" part (g has duration 2)

    """
    def __init__(self, scope=None, wait=True):
        self.scope = scope
        self.wait = wait

    def preceding_music(self, node):
        """Return a two-tuple(music, trail).

        The ``node`` must be a child of a :class:`~.dom.lily.Music` instance.
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

    def position(self, node, include=False):
        """Return a two-tuple(ancestor, length).

        The ``node`` must be a child of a :class:`~.dom.lily.Music` instance.
        The returned ancestor is the topmost Music element, and the length is
        the computed length of all preceding music nodes. If ``include`` is
        True, the node's length itself is also added.

        """
        music, trail = self.preceding_music(node)
        time, node, transform = self._follow_trail(music, trail, music.transform())
        if include:
            time += self.length(node, None, transform)
        return music, time

    def duration(self, start_node, end_node):
        """Return the time from start upto and including end node.

        Both nodes must be children of :class:`~.dom.lily.Music` nodes. If they
        don't share the same ancestor, -1 is returned. A negative value can
        also be returned when the end node precedes the start node.

        """
        music, start_trail = self.preceding_music(start_node)
        end_music, end_trail = self.preceding_music(end_node)
        if end_music is not music:
            return -1

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
        return end_time - start_time

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
                prev_dur = node.duration, node.scaling
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

        if isinstance(node, lily.Durable):
            return durable_length(node, transform or duration.Transform())
        elif isinstance(node, lily.Music):
            if node.is_sequential():
                return sum(times(node[:end], transform or node.transform()))
            elif end is None:
                return max(times(node, transform or node.transform()), default=0)
        elif isinstance(node, lily.Reference):
            return remote_length(node, transform or duration.Transform())
        return 0


