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

    You can inherit of Node and add your own attributes and methods.

    A node can have child nodes and a :attr:`parent`. The parent is referred to
    with a weak reference, so a node tree does not contain circular references.
    (This also means that you need to keep a reference to a tree's root node,
    otherwise it will be garbage collected.)

    Adding nodes to a node sets the parent of the nodes; but removing nodes
    *doesn't* unset the parent of the removed nodes; and adding nodes does not
    automatically remove them from their previous parent; you should take care
    of that yourself. Unset the parent of a node by setting the :attr:`parent`
    attribute to ``None``.

    Iterating over a node yields the child nodes, just like the underlying
    Python list. Unlike Python's list, a node always evaluates to True, even if
    there are no children.

    To find the index of a node in its parent, use::

        >>> index = node.parent.index(node)

    This is safe, because it uses the nodes' identity, but potentially slow
    because it uses a linear search, so don't use it for every node in an
    iterative operation.

    Besides the usual methods, Node defines six special query operators: ``/``,
    ``//``, ``<<``, ``>``, ``<`` and ``^``. All these expect a Node (sub)class
    (or instance) as argument, and iterate in different ways over selected
    Nodes:

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

    * The ``>`` operator iterates :meth:`forward` from the node, starting
      with the right sibling::

        for n in node > MyClass:
            # do something on the MyClass instance that comes after the node
            # (and is not a child)

    * The ``<`` operator iterates :meth:`backward` from the node, starting
      with the left sibling::

        for n in node < MyClass:
            # do something on the MyClass instance that precedes the node
            # (and is not a child)

    * The ``^`` operator iterates over the children that are *not* an instance
      of the specified class(es)::

        node[:] = (node ^ MyClass)
        # deletes all children that are an instance of MyClass

    Instead of a subclass, a class instance or a tuple of more than one class
    may also be given. If a class instance is given, :meth:`body_equals` must
    return true for the compared nodes. (Child nodes are not compared when using
    a class instance to compare with.)

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
        using the ``/`` or ``^`` operator::

            >>> node.ls / Class

        Only the children of node that are an (or are not) instance of Class
        are shown.

        """
        return _NodeLister(self)

    @property
    def pwd(self):
        """Show the ancestry, for debugging purposes."""
        nodes = [self]
        nodes.extend(self.ancestors())
        nodes.reverse()
        d = DUMP_STYLES[DUMP_STYLE_DEFAULT]
        for n, node in enumerate(nodes):
            print(''.join((d[1] * max(0, n-1), d[3] if n else '', repr(node))))

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
                node._parent = weakref.ref(self)

    def copy(self):
        """Return a copy of this Node, with copied children."""
        return type(self)(*(n.copy() for n in self))

    @property
    def parent(self):
        """The parent Node or None; uses a weak reference."""
        return self._parent()

    @parent.setter
    def parent(self, node):
        self._parent = _NO_PARENT if node is None else weakref.ref(node)

    @parent.deleter
    def parent(self):
        self._parent = _NO_PARENT

    def append(self, node):
        """Append node to this node; the parent is set to this node."""
        node._parent = weakref.ref(self)
        list.append(self, node)

    def extend(self, nodes):
        """Append nodes to this node; the parent is set to this node."""
        index = len(self)
        list.extend(self, nodes)
        for node in self[index:]:
            node._parent = weakref.ref(self)

    def insert(self, index, node):
        """Insert node in this node; the parent is set to this node."""
        node._parent = weakref.ref(self)
        list.insert(self, index, node)

    def take(self, start=0, end=None):
        """Like :meth:`list.pop`, but takes out and returns a slice(start, end)."""
        k = slice(start, end)
        nodes = self[k]
        del self[k]
        return nodes

    def __setitem__(self, k, new):
        """Set self[k] to the node(s) in ``new``; the parent is set to this Node."""
        if isinstance(k, slice):
            new = tuple(new)
            for node in new:
                node._parent = weakref.ref(self)
        else:
            new._parent = weakref.ref(self)
        list.__setitem__(self, k, new)

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

    def get_predicate_iterator(self, other, source_iterator, invert=False):
        """Return an iterator or NotImplemented.

        This is used by the ``/``, ``//``, ``<<``, ``^``, ``>``, and ``<``
        operators.

        If the argument ``other`` is a :class:`Node` instance, the type must
        match and :meth:`body_equals` must return True. The argument may also
        be a :class:`type` or a :class:`tuple`, in which case it is used as
        argument for the :func:`isinstance` builtin function.

        For other types of argument, NotImplemented is returned.

        If ``invert`` is True, the condition is inverted, i.e. if the source
        object does not match the ``other``, it is yielded.

        """
        if isinstance(other, Node):
            predicate = lambda node: type(node) is type(other) and node.body_equals(other)
        elif isinstance(other, (tuple, type)):
            predicate = lambda node: isinstance(node, other)
        else:
            return NotImplemented
        return (itertools.filterfalse if invert else filter)(predicate, source_iterator)

    def __eq__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is other

    def __ne__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is not other

    def __lshift__(self, cls):
        """Iterate over the ancestors that inherit the specified class(es)."""
        return self.get_predicate_iterator(cls, self.ancestors())

    def __gt__(self, cls):
        """Iterate over the following nodes (see :meth:`forward`) that inherit the specified class(es)."""
        return self.get_predicate_iterator(cls, self.forward())

    def __lt__(self, cls):
        """Iterate over the preceding nodes (see :meth:`backward`) that inherit the specified class(es)."""
        return self.get_predicate_iterator(cls, self.backward())

    def __truediv__(self, cls):
        """Iterate over children that inherit the specified class(es)."""
        return self.get_predicate_iterator(cls, self)

    def __floordiv__(self, cls):
        """Iterate over descendants inheriting the specified class(es), in document order."""
        return self.get_predicate_iterator(cls, self.descendants())

    def __xor__(self, cls):
        """Iterate over children that do not inherit the specified class(es)."""
        return self.get_predicate_iterator(cls, self, True)

    def __repr__(self):
        c = "child" if len(self) == 1 else "children"
        return '<{} ({} {})>'.format(type(self).__name__, len(self), c)

    def is_last(self):
        """Return True if this is the last node. Fails if no parent."""
        return self.parent[-1] is self

    def is_first(self):
        """Return True if this is the first node. Fails if no parent."""
        return self.parent[0] is self

    def common_ancestor(self, other):
        """Return the common ancestor, if any.

        When one node appears to be an ancestor of the other, that node is
        returned.

        """
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

    def common_ancestor_with_trail(self, other):
        """Return a three-tuple(ancestor_node, trail_self, trail_other).

        The ancestor node is the common ancestor such as returned by
        :meth:`common_ancestor`. The trail_self is a list of indices from
        the common ancestor upto self, and trail_other is a list of indices
        from the same ancestor upto the other Node.

        If one of the trails is empty, the corresponding node is then an
        ancestor or the other.

        If there is no common ancestor, (None, None, None) is returned. But
        normally, all nodes share the root node, so that will normally be the
        upmost common ancestor.

        """
        if other is self:
            return self, [], []
        ancestors = [self]
        trail_self = []
        n = self
        for p, i in self.ancestors_with_index():
            trail_self.append(i)
            if p is other:
                return p, trail_self[::-1], []
            ancestors.append(p)
            n = p
        trail_other = []
        for n, i in other.ancestors_with_index():
            trail_other.append(i)
            try:
                i = ancestors.index(n)
                return n, trail_self[i::-1], trail_other[::-1]
            except ValueError:
                pass
        return None, None, None

    def ancestors(self):
        """Yield the parent, then the parent's parent, etcetera."""
        n = self.parent
        while n:
            yield n
            n = n.parent

    def ancestors_with_index(self):
        """Yield the ancestors and the index of each node in the parent."""
        n = self
        for p in self.ancestors():
            yield p, p.index(n)
            n = p

    def descendants(self, reverse=False):
        """Iterate over all the descendants of this node.

        If ``reverse`` is set to True, yields all descendants in backward
        direction.

        """
        iterate = reversed if reverse else iter
        stack = []
        gen = iterate(self)
        while True:
            for node in gen:
                yield node
                if len(node):
                    stack.append(gen)
                    gen = iterate(node)
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

    def trail(self):
        """Return the list of indices of all ancestors in their parents.

        The node's own index is at the end. Using trails you can determine
        arbitrary ranges in a DOM document, and you can compare trails to see
        which node comes first in the document order.

        """
        trail = [i for p, i in self.ancestors_with_index()]
        return trail[::-1]

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

    def right_sibling(self):
        """The right sibling, if any."""
        p = self.parent
        if p and p[-1] is not self:
            i = p.index(self)
            return p[i+1]

    def left_sibling(self):
        """The left sibling, if any."""
        p = self.parent
        if p and p[0] is not self:
            i = p.index(self)
            return p[i-1]

    def forward(self, upto=None):
        """Iterate forward from this Node, starting with the right sibling.

        If you specify an ancestor node ``upto``, will not go outside that
        node.

        """
        node = self
        while node.parent and node is not upto:
            for n in node.right_siblings():
                yield n
                if len(n):
                    yield from n.descendants()
            node = node.parent

    def backward(self, upto=None):
        """Iterate backward from this Node, starting with the left sibling.

        If you specify an ancestor node ``upto``, will not go outside that
        node.

        """
        node = self
        while node.parent and node is not upto:
            for n in node.left_siblings():
                yield n
                if len(n):
                    yield from n.descendants(reverse=True)
            node = node.parent

    def depth(self):
        """Return the number of ancestors."""
        return sum(1 for n in self.ancestors())

    def height(self):
        """Return the height of the tree (the longest distance to a descendant)."""
        stack = []
        height = 0
        gen = iter((self,))
        while True:
            for node in gen:
                if len(node):
                    stack.append(gen)
                    height = max(height, len(stack))
                    gen = iter(node)
                    break
            else:
                if stack:
                    gen = stack.pop()
                else:
                    return height

    def filter(self, predicate):
        """Call predicate on all descendants.

        If the predicate returns True for a node, that node is yielded and its
        descendants are skipped.

        """
        stack = []
        gen = iter(self)
        while True:
            for node in gen:
                if predicate(node):
                    yield node
                elif len(node):
                    stack.append(gen)
                    gen = iter(node)
                    break
            else:
                if stack:
                    gen = stack.pop()
                else:
                    break

    def instances_of(self, cls):
        """Yield all descendants that are an instance of ``cls``.

        The difference with the ``//`` operator is that when a node is yielded,
        its children are not searched anymore.

        The ``cls`` parameter may also be a tuple of more classes, just like the
        standard Python :func:`isinstance`.

        """
        return self.filter(lambda node: isinstance(node, cls))


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

    def __xor__(self, other):
        """Iterate over children that do not inherit the specified class."""
        for n, node in enumerate(self.node):
            if not isinstance(node, other):
                print(self.format(n, repr(node)))

    def __getitem__(self, key):
        """Print specified items."""
        if isinstance(key, slice):
            indices = itertools.islice(range(len(self.node)), key.start, key.stop, key.step)
        else:
            indices = [key]
        for n in indices:
            print(self.format(n, repr(self.node[n])))


