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
This module defines a Node class, to build simple tree structures based on
Python lists.

"""

import itertools
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


_NO_PARENT = lambda: None


class Node(list):
    """Node implements a simple tree type, based on Python :class:`list`.

    Adding nodes to the list sets the parent of the nodes; and removing nodes
    sets the parent of the nodes to None; but adding nodes does not
    automatically remove them from the previous parent; you should take care of
    that yourself (e.g. by using the :meth:`take` method).

    Besides the usual methods, Node defines three special query operators:
    ``/``, ``//`` and ``<<``. All these expect a Node (sub)class as argument,
    and iterate in different ways over selected Nodes:

    * The ``/`` operator iterates over the children that are instances of the
      specified class::

        for n in node / MyClass:
            # do_something with n, which is a child of node and
            # an an instance of MyClass

    * The ``//`` operator iterates over all descendants in document order::

        for n in node // MyClass:
            # n is a descendant of node and an instance of MyClass

    * The ``<<`` operator iterates over the ancestors::

        for n in node << Header:
            n.blabla    # n is the youngest ancestor that is a Header instance

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

    @property
    def ls(self):
        """List the children, for debugging purposes.

        You can also narrow down the list of children to certain types,
        using the ``/`` operator::

            >>> node.ls / Class

        Only the children of node that are an instance of Class are shown.

        """
        return _NodeLister(self)

    def __bool__(self):
        """Always return True."""
        return True

    def __init__(self, *children):
        """Constructor.

        If children are given they are appended to the list, and their
        parent is set to this node.

        """
        self._parent = _NO_PARENT
        if children:
            list.extend(self, children)
            for node in self:
                node.parent = self

    def copy(self):
        """Return a copy of this Node, with copied children."""
        return type(self)(*(n.copy() for n in self))

    @property
    def parent(self):
        """Return the parent Node or None; uses a weak reference."""
        return self._parent()

    @parent.setter
    def parent(self, node):
        """Set the parent to Node node or None."""
        self._parent = weakref.ref(node) if node else _NO_PARENT

    @parent.deleter
    def parent(self):
        """Set the parent to None."""
        self.parent = None

    def append(self, node):
        """Append node to this node; the parent is set to this node."""
        node.parent = self
        list.append(self, node)

    def extend(self, nodes):
        """Append nodes to this node; the parent is set to this node."""
        nodes = list(nodes)
        for node in nodes:
            node.parent = self
        list.extend(self, nodes)

    def insert(self, index, node):
        """Insert node in this node; the parent is set to this node."""
        node.parent = self
        list.insert(self, index, node)

    def remove(self, node):
        """Remove node from this node, the parent is set to None."""
        index = list.index(self, node)
        del self[index]

    def pop(self, index=-1):
        """Pop node from this node; the parent is set to None."""
        node = list.pop(self, index)
        node.parent = None
        return node

    def take(self, start=0, end=None):
        """Like pop, but takes out and returns a slice(start, end).

        The parent of the returned nodes is set to None.

        """
        k = slice(start, end)
        nodes = self[k]
        for node in nodes:
            node.parent = None
        list.__delitem__(self, k)
        return nodes

    def __setitem__(self, k, new):
        """Set self[k] to the node(s) in ``new``; the parent is set to this Node."""
        old = self[k]
        if isinstance(k, slice):
            new = tuple(new)
            for node in old:
                node.parent = None
            for node in new:
                node.parent = self
        else:
            old.parent = None
            new.parent = self
        list.__setitem__(self, k, new)

    def __delitem__(self, k):
        """Delete self[k]; the parent of the deleted nodes is set to None."""
        old = self[k]
        if isinstance(k, slice):
            for node in old:
                node.parent = None
        else:
            old.parent = None
        list.__delitem__(self, k)

    def clear(self):
        """Remove all child nodes."""
        for node in self:
            node.parent = None
        list.clear(self)

    def equals(self, other):
        """Return True if we and other are equivalent.

        This is the case when we and the other have the same class, the same
        amount of children, :meth:`body_equals` returns True, and finally for
        all the children this method returns True.

        Before this method is called on all the children, this method calls
        :meth:`body_equals`; implement that method if you want to add more
        tests, e.g. for certain instance attributes.

        """
        return type(self) is type(other) and len(self) == len(other) and \
            self.body_equals(other) and \
            all(a.equals(b) for a, b in zip(self, other))

    def body_equals(self, other):
        """Implement this to add more :meth:`equals` tests, before all the
        children are compared.

        The default implementation returns True.

        """
        return True

    def __eq__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is other

    def __ne__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is not other

    def __lshift__(self, other):
        """Iterate over the ancestors that inherit the specified class."""
        for i in self.ancestors():
            if isinstance(i, other):
                yield i

    def __truediv__(self, other):
        """Iterate over children that inherit the specified class."""
        for i in self:
            if isinstance(i, other):
                yield i

    def __floordiv__(self, other):
        """Iterate over descendants inheriting the specified class, in document order."""
        for i in self.descendants():
            if isinstance(i, other):
                yield i

    def __repr__(self):
        return '<{} ({} children)>'.format(type(self).__name__, len(self))

    def is_last(self):
        """Return True if this is the last node. Fails if no parent."""
        return self.parent[-1] is self

    def is_first(self):
        """Return True if this is the first node. Fails if no parent."""
        return self.parent[0] is self

    def common_ancestor(self, other):
        """Return the common ancestor, if any."""
        if other is self:
            return self
        ancestors = [self]
        for n in self.ancestors():
            if n is other:
                return n
            ancestors.append(n)
        for n in other.ancestors():
            if n in ancestors:
                return n

    def ancestors(self):
        """Climb up the tree over the parents."""
        n = self.parent
        while n:
            yield n
            n = n.parent

    def descendants(self):
        """Iterate over all the descendants of this node."""
        stack = []
        gen = iter(self)
        while True:
            for i in gen:
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

    def descendants_backward(self):
        """Iterate over all the descendants of this node in backward direction."""
        stack = []
        gen = reversed(self)
        while True:
            for i in gen:
                yield i
                if len(i):
                    stack.append(gen)
                    gen = reversed(i)
                    break
            else:
                if stack:
                    gen = stack.pop()
                else:
                    break

    def root(self):
        """Return the root node."""
        root = self
        for root in self.ancestors():
            pass
        return root

    def right_siblings(self):
        """Iterate over the right siblings of this node."""
        p = self.parent
        if p:
            i = p.index(self)
            yield from p[i+1:]

    def left_siblings(self):
        """Iterate backwards over the left siblings of this node."""
        p = self.parent
        if p:
            i = p.index(self)
            yield from reversed(p[:i])

    @property
    def right_sibling(self):
        """The right sibling, if any."""
        p = self.parent
        if p and p[-1] is not self:
            i = p.index(self)
            return p[i+1]

    @property
    def left_sibling(self):
        """The left sibling, if any."""
        p = self.parent
        if p and p[0] is not self:
            i = p.index(self)
            return p[i-1]

    def forward(self):
        """Iterate forward from this Node, starting with the right sibling."""
        node = self
        while node.parent:
            for n in node.right_siblings():
                yield n
                if len(n):
                    yield from n.descendants()
            node = node.parent

    def backward(self, other=None):
        """Iterate backward from this Node, starting with the left sibling."""
        node = self
        while node.parent:
            for n in node.left_siblings():
                yield n
                if len(n):
                    yield from n.descendants_backward()
            node = node.parent


class _NodeLister:
    """Displays a node for debugging purposes."""
    def __init__(self, node):
        self.node = node
        self.format = "{{:{}}} {{}}".format(len(str(len(node)))).format

    def __repr__(self):
        return '\n'.join(self.format(n, repr(node)) for n, node in enumerate(self.node))

    def __truediv__(self, other):
        """Iterate over children that inherit the specified class."""
        for n, node in enumerate(self.node):
            if isinstance(node, other):
                print(self.format(n, repr(node)))

    def __getitem__(self, key):
        """Print specified items."""
        if isinstance(key, slice):
            indices = itertools.islice(range(len(self.node)), key.start, key.stop, key.step)
        else:
            indices = [key]
        for n in indices:
            print(self.format(n, repr(self.node[n])))


