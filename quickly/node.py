# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2020 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
This module defines the Node class, to build simple tree structures based on
Python lists.

"""

import weakref


DUMP_STYLES = {
    "ascii":   (" | ", "   ", " |-", " `-"),
    "round":   (" │ ", "   ", " ├╴", " ╰╴"),
    "square":  (" │ ", "   ", " ├╴", " └╴"),
    "double":  (" ║ ", "   ", " ╠═", " ╚═"),
    "thick":   (" ┃ ", "   ", " ┣╸", " ┗╸"),
    "flat":    ("│", " ", "├", "╰"),
}

DUMP_STYLE_DEFAULT = "round"



class Node(list):
    """Node implements a simple tree type, based on Python list.

    Adding nodes to the list sets the parent of the nodes; and removing nodes
    sets the parent of the nodes to None; but adding nodes does not
    automatically remove them from the previous parent; you should take care of
    that yourself (e.g. by using the :meth:`take` method).

    """

    __slots__ = ('__weakref__', '_parent')

    def dump(self, file=None, style=None, depth=0):
        """Display a graphical representation of the node and its contents.

        The file object defaults to stdout, and the style to "round". You can
        choose any style that's in the ``DUMP_STYLES`` dictionary.

        """
        i = 2
        d = DUMP_STYLES[style or DUMP_STYLE_DEFAULT]
        prefix = []
        node = self
        for _ in range(depth):
            prefix.append(d[i + int(node.is_last())])
            node = node.parent
            i = 0
        print(''.join(reversed(prefix)) + repr(self), file=file)
        for n in self:
            n.dump(file, style, depth + 1)

    def __bool__(self):
        """Always return True."""
        return True

    def __init__(self, *children):
        """Constructor.

        If children are given they are appended to the list, and their
        parent is set to this node.

        """
        if children:
            list.extend(self, children)
            parent = weakref.ref(self)
            for node in self:
                node._parent = parent

    @property
    def parent(self):
        """Return the parent Node or None; uses a weak reference."""
        return self._parent()

    @parent.setter
    def parent(self, node):
        """Set the parent to Node node or None."""
        self._parent = weakref.ref(node) if node else lambda: None

    @parent.deleter
    def parent(self):
        """Set the parent to None."""
        self._parent = lambda: None

    def append(self, node):
        """Append node to this node; the parent is set to this node."""
        node._parent = weakref.ref(self)
        list.append(self, node)

    def extend(self, nodes):
        """Append nodes to this node; the parent is set to this node."""
        nodes = list(nodes)
        parent = weakref.ref(self)
        for node in nodes:
            node._parent = parent
        list.extend(self, nodes)

    def insert(self, index, node):
        """Insert node in this node; the parent is set to this node."""
        node._parent = weakref.ref(self)
        list.insert(self, index, node)

    def remove(self, node):
        """Remove node from this node, the parent is set to None."""
        index = list.index(self, node)
        del self[index]

    def pop(self, index=-1):
        """Pop node from this node; the parent is set to None."""
        node = list.pop(self, index)
        node._parent = lambda: None
        return node

    def take(self, start=0, end=None):
        """Like pop, but takes out and returns a slice(start, end).

        The parent of the returned nodes is set to None.

        """
        k = slice(start, end)
        nodes = self[k]
        for node in nodes:
            node._parent = lambda: None
        list.__delitem__(self, k)
        return nodes

    def __setitem__(self, k, new):
        """Set self[k] to the node(s) in ``new``; the parent is set to this Node."""
        old = self[k]
        parent = weakref.ref(self)
        if isinstance(k, slice):
            new = tuple(new)
            for node in old:
                node._parent = lambda: None
            for node in new:
                node._parent = parent
        else:
            old._parent = lambda: None
            new._parent = parent
        list.__setitem__(self, k, new)

    def __delitem__(self, k):
        """Delete self[k]; the parent of the deleted nodes is set to None."""
        old = self[k]
        if isinstance(k, slice):
            for node in old:
                node._parent = lambda: None
        else:
            old._parent = None
        list.__delitem__(self, k)

    def equals(self, other):
        """Return True if we and other are equivalent.

        This is the case when we and the other have the same class,
        both lists of children have the same length and compare equal.

        Before it calls :meth:`equals` on all the children this method calls
        meth:`_equals`; implement that method if you want to add more tests,
        e.g. for certain instance attributes.

        """
        return type(self) is type(other) and len(self) == len(other) and \
            self._equals(other) and \
            all(a.equals(b) for a, b in zip(self, other))

    def _equals(self, other):
        """Implement this to add more `equals` tests, before all the children are compared."""
        return True

    def __eq__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is other

    def __ne__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is not other

    def __truediv__(self, other):
        """Iterate over children of the specified class."""
        for i in self:
            if type(i) is other:
                yield i

    def __floordiv__(self, other):
        """Iterate over descendants of the specified class, in document order."""
        stack = []
        gen = iter(self)
        while True:
            for i in gen:
                if type(i) is other:
                    yield i
                if len(i):
                    stack.append(gen)
                    gen = iter(i)
                    break
            else:
                if stack:
                    gen = stack.pop()
                else:
                    break

    def __repr__(self):
        return '<{} ({} children)>'.format(type(self).__name__, len(self))

    def is_last(self):
        """Return True if this is the last node. Fails if no parent."""
        return self.parent[-1] is self

    def is_first(self):
        """Return True if this is the first node. Fails if no parent."""
        return self.parent[0] is self


