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
This module defines a :class:`Node` class, to build simple tree structures
based on Python lists.

There is also a :class:`Range` class, that defines a fragment of a node tree
from one Node upto and including another (or from/to the beginning or end), and
allows iterating over the tree fragment.

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


class Common:
    """Mixin class implementing the methods shared by :class:`Node` and :class:`Range`."""

    __slots__ = ()

    def _get_predicate_iterator(self, other, source_iterator, invert=False):
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

    def __lshift__(self, cls):
        """Iterate over the ancestors that inherit the specified class(es)."""
        return self._get_predicate_iterator(cls, self.ancestors())

    def __gt__(self, cls):
        """Iterate over the following nodes (see :meth:`forward`) that inherit the specified class(es)."""
        return self._get_predicate_iterator(cls, self.forward())

    def __lt__(self, cls):
        """Iterate over the preceding nodes (see :meth:`backward`) that inherit the specified class(es)."""
        return self._get_predicate_iterator(cls, self.backward())

    def __truediv__(self, cls):
        """Iterate over children that inherit the specified class(es)."""
        return self._get_predicate_iterator(cls, self)

    def __floordiv__(self, cls):
        """Iterate over descendants inheriting the specified class(es), in document order."""
        return self._get_predicate_iterator(cls, self.descendants())

    def __xor__(self, cls):
        """Iterate over children that do not inherit the specified class(es)."""
        return self._get_predicate_iterator(cls, self, True)

    @staticmethod
    def filter_descendants(predicate, generator):
        """Call predicate on all nodes returned by generator.

        Yield the node if the predicate returns True, and send False to the
        generator, causing it to not yield descendant nodes for that node.

        This can be used with :meth:`Node.descendants`, :meth:`Node.forward`,
        :meth:`Node.backward`, :meth:`Range.descendants`,
        :meth:`Range.forward`, :meth:`Range.backward` and :meth:`Range.nodes`.

        """
        try:
            while True:
                node = next(generator)
                while predicate(node):
                    yield node
                    node = generator.send(False)
        except StopIteration:
            pass

    def filter(self, predicate):
        """Call predicate on all descendants.

        If the predicate returns True for a node, that node is yielded and its
        descendants are skipped.

        """
        return self.filter_descendants(predicate, self.descendants())

    def instances_of(self, cls):
        """Iterate over the descendants of the current node and yield
        all nodes that are an instance of ``cls``.

        When a node is yielded, its descendants are not searched anymore.

        The ``cls`` parameter may also be a tuple of more classes, just like the
        standard Python :func:`isinstance`.

        """
        return self.filter(lambda node: isinstance(node, cls))


class Node(Common, list):
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
            # an instance of MyClass

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

    def __repr__(self):
        c = "child" if len(self) == 1 else "children"
        return '<{} ({} {})>'.format(type(self).__name__, len(self), c)

    def __bool__(self):
        """Always True."""
        return True

    def __init__(self, *children):
        """Constructor.

        If children are given they are appended to the list, and their parent
        is set to this node.

        """
        self._parent = _NO_PARENT
        if children:
            list.extend(self, children)
            for node in self:
                node._parent = weakref.ref(self)

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

    def root(self):
        """Return the root node."""
        root = self
        for root in self.ancestors():
            pass
        return root

    def trail(self):
        """Return the list of indices of the node and its ancestors in their
        parents.

        The node's own index is at the end. Using trails you can determine
        arbitrary ranges in a DOM document, and you can compare trails to see
        which node comes first in the document order.

        Given the following hypothetical tree structure (all classes are
        subclasses of Node)::

            A(
                B(
                    C(),
                    D()),
                E(
                    F(),
                    G(
                        H())))

        the trail of the F instance would be ``[1, 0]``, because its parent E
        has index 1 in A, while F has index 0 in E.

        If you have two nodes, e.g. the D and H instance, in resp. ``d`` and
        ``h``, you can quickly see which one is earlier in the tree:
        ``d.trail() < h.trail()``, which would evaluate to True in this case.

        """
        trail = [i for p, i in self.ancestors_with_index()]
        return trail[::-1]

    __hash__ = object.__hash__

    def __eq__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is other

    def __ne__(self, other):
        """Identity compare to make Node.index robust and "faster"."""
        return self is not other

    def copy(self, with_children=True):
        """Return a copy of this Node.

        If ``with_children`` is True (the default), child nodes are also
        copied.

        """
        children = (n.copy() for n in self) if with_children else ()
        return type(self)(*children)

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

    def replace_with(self, node):
        """Replace this node in its parent with another node.

        Fails if called on the root node.

        """
        node._parent = weakref.ref(self)
        index = self.parent.index(self)
        self.parent[index] = node

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

    def is_last(self):
        """Return True if this is the last node. Fails if no parent."""
        return self.parent[-1] is self

    def is_first(self):
        """Return True if this is the first node. Fails if no parent."""
        return self.parent[0] is self

    def is_root(self):
        """Return True if this node has no parent."""
        return self.parent is None

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
        """Return a three-tuple(``ancestor``, ``trail_self``, ``trail_other``) or None.

        The ``ancestor`` node is the common ancestor such as returned by
        :meth:`common_ancestor`. The ``trail_self`` is a list of indices from
        the common ancestor upto self, and ``trail_other`` is a list of indices
        from the same ancestor upto the other Node.

        If one of the trails is empty, the corresponding node is an ancestor of
        the other.

        If there is no common ancestor, (None, None, None) is returned. But
        normally, all nodes share the root node, so that will normally be the
        upmost common ancestor.

        """
        if other is self:
            return self, [], []

        ancestors = []
        trail_self = []
        for n, i in self.ancestors_with_index():
            trail_self.append(i)
            if n is other:
                return n, trail_self[::-1], []
            ancestors.append(n)

        trail_other = []
        for n, i in other.ancestors_with_index():
            trail_other.append(i)
            if n is self:
                return n, [], trail_other[::-1]
            try:
                i = ancestors.index(n)
            except ValueError:
                pass
            else:
                return n, trail_self[i::-1], trail_other[::-1]
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

        When you :meth:`~generator.send` False to this generator, child nodes
        of the just yielded node will not be yielded.

        """
        iterate = reversed if reverse else iter
        stack = []
        gen = iterate(self)
        while True:
            for n in gen:
                if (yield n) is not False and len(n):
                    stack.append(gen)
                    gen = iterate(n)
                    break
            else:
                if stack:
                    gen = stack.pop()
                else:
                    break

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

        When you :meth:`~generator.send` False to this generator, child nodes
        of the just yielded node will not be yielded.

        """
        node = self
        while node.parent and node is not upto:
            for n in node.right_siblings():
                if (yield n) is not False and len(n):
                    yield from n.descendants()
            node = node.parent

    def backward(self, upto=None):
        """Iterate backward from this Node, starting with the left sibling.

        If you specify an ancestor node ``upto``, will not go outside that
        node.

        When you :meth:`~generator.send` False to this generator, child nodes
        of the just yielded node will not be yielded.

        """
        node = self
        while node.parent and node is not upto:
            for n in node.left_siblings():
                if (yield n) is not False and len(n):
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

    def range(self, other, from_root=False):
        """Return a :class:`Range` from self to the other node."""
        return Range.from_nodes(self, other, from_root)

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
        _pwd(nodes)


class Range(Common):
    """Defines a range within a node tree.

    A range is defined by a starting node (the ancestor), and optional start
    and end trails. A :attr:`~Node.trail` is a list of indices defining the
    path to the first and/or last node of the range. If both trails are None,
    the range encompasses the full node.

    A Range can be constructed directly, specifying the ancestor node and the
    trails, or using the :meth:`from_nodes` method, specifying the start and/or
    end node. This method is also used when you call the :meth:`Node.range`
    method. The range includes both the start node and the end node (if
    specified).

    A Range is empty when the end node is before the start node, or when the
    ancestor node itself is empty. An empty Range evaluates to False.

    Having created a Range object, you can do a lot:

     * Use the ``node in range`` syntax to see whether a Node is inside a Range.
       A node is in a range when all its children are also in the range.
       (Only the end node can have children outside the range.)

     * Use the ``range & node`` syntax to see whether a Node intersects with
       a Range. A node intersects with a Range when it has child nodes in the
       Range, but it can also have childnodes outside the range.

     * Use :meth:`extract_tree` to get a copy of the node tree from the
       ancestor, including only the range.

     * Iterate over the Range to get the nodes at the current iteration
       level. Iterating starts at the bottom node of the range, and walks over
       the children of the node that are within the range. If you want to
       iterate over the children of a node that are in the range (and possibly
       further down), you can use :meth:`enter`, and, after iterating the
       children, :meth:`leave`. Or use :meth:`children`, which fits more in a
       recursive approach.

    When iterating, the Range object keeps track of the position in the tree
    range. The current node is accessible via the :attr:`node` attribute.

    Range support the same search operators as :class:`Node`: ``/``, ``//``,
    ``<<``, ``>``, ``<`` and ``^``. Note that they set the current node, so it
    you don't exhaust them fully, restarted or other searches may start from a
    different node than you expect. Use with care! :-)

    Of course you can modify the tree directly, but if you change the number of
    children of the parent of the current node, use the item methods (like
    ``range[index] = value``) of the iterator, so that it adjust the range
    boundaries and its iteraton to the changes.

    There is a subtle difference between how the start trail is handled and how
    the end trail is handled. The children of the start node are considered to
    be in the range, but the children of the end node not. If you want those to
    be in the range, be sure you specify the last child node you want to be in
    the range.

    If you replace a node (using the item methods of Range) that's on a range
    boundary, the boundary trail can be modified. For example, if you replace a
    node that lies on the start trail, the start trail is truncated to that
    node, so that all its children are within the range (because the old end of
    the start trail can be invalid for the new node contents). Also the end
    trail is truncated when a node on the end boundary is replaced, causing the
    children of the new node to fall outside of the range. Inserting nodes in
    another node that crosses the end boundary causes the end trail to be
    adjusted, so that the range boundary is still valid.

    """
    def ancestor(self):
        """The bottom node of this range."""
        return self._stack[0].node

    def __init__(self, ancestor, start_trail=None, end_trail=None):
        #: The start trail (path to first node), can be None.
        #: (Do not modify from the outside.)
        self.start_trail = start_trail
        #: The end trail (path to the last node), can be None.
        #: (Do not modify from the outside.)
        self.end_trail = end_trail
        self._stack = [self._Level(ancestor, start_trail, end_trail)]

    def __repr__(self):
        def fields():
            yield type(self).__name__
            yield "@{}".format(self.node)
            if self.start_trail is not None:
                yield "start_node={}".format(self.start_node())
            if self.end_trail is not None:
                yield "end_node={}".format(self.end_node())
        return "<{}>".format(" ".join(fields()))

    @classmethod
    def from_nodes(cls, start_node=None, end_node=None, from_root=False):
        """Create a Range object from a start node to an end node.

        One of them (but not both) may be None. If the ``start_node`` is None,
        the range starts at the very beginning; if the ``end_node`` is None,
        the range starts at the start node and walks to the very end.

        If ``from_root`` is True, the ancestor of the range will always be the
        root node; even if the trails to start and end node are partially the
        same. If False, the ancestor will be the youngest common ancestor.

        Raises a ValueError if both nodes are None, or when the nodes do not
        belong to the same tree.

        """
        if not from_root and start_node and end_node:
            ancestor, start_trail, end_trail = start_node.common_ancestor_with_trail(end_node)
            ok = ancestor is not None
        elif start_node:
            ancestor = start_node.root()
            start_trail = start_node.trail()
            end_trail = end_node.trail() if end_node else None
            ok = (end_node.root() is ancestor) if end_node else True
        elif end_node:
            ancestor = end_node.root()
            start_trail = None
            end_trail = end_node.trail()
            ok = True
        else:
            raise ValueError("must specify at least one node")
        if not ok:
            raise ValueError("start_node and end_node should have the same root")
        return cls(ancestor, start_trail, end_trail)

    def start_node(self):
        """The start node, if specified."""
        if self.start_trail is not None:
            n = self.ancestor()
            for i in self.start_trail:
                n = n[i]
            return n

    def end_node(self):
        """The end node, if specified."""
        if self.end_trail is not None:
            n = self.ancestor()
            for i in self.end_trail:
                n = n[i]
            return n

    def copy(self):
        """Return a clean copy of this Range, initialized at the same ancestor."""
        return type(self)(self.ancestor(), self.start_trail, self.end_trail)

    def from_here(self):
        """Return a new Range, starting at the current :attr:`node`.

        This is easier to use if you prefer a recursive approach.

        """
        level = self._stack[-1]
        if level.index > -1:
            level = level.child()
        start_trail = (level.start_trail[level.depth:] or None) if level.start_trail else None
        end_trail = level.end_trail[level.depth:] if level.end_trail is not None else None
        return type(self)(level.node, start_trail, end_trail)

    def __bool__(self):
        """False if the range is empty."""
        level = self._stack[0]
        return level.start <= level.end

    def __contains__(self, node):
        """Return True if the node is completely within this range.

        Returns False if a node (or any of its descendants) is partially
        outside of the range. (The ancestor itself is completely in the range
        if there is no start_trail and no end_trail.)

        """
        trail = self._get_trail(node)
        return trail is not None and self._trail_in_range(trail)

    def _get_trail(self, node):
        """(Internal) Return the trail of the node from our ancestor.

        Returns None if the node does not belong to our tree. Returns an empty
        list if the node *is* the ancestor.

        """
        ancestor = self.ancestor()
        trail = []
        if node is ancestor:
            return trail
        for p, i in node.ancestors_with_index():
            trail.append(i)
            if p is ancestor:
                trail.reverse()
                return trail

    def _trail_in_range(self, trail):
        """Return True if the trail is completely in our range.

        The trail is assumed to start at our ancestor (like the return value
        of :meth:`_get_trail`).

        """
        if not trail:   # empty list. Ancestor itself? ok if in_range()
            return self._stack[0].start_in_range() and self._stack[0].end_in_range()
        elif self.start_trail and trail < self.start_trail:
            return False
        elif self.end_trail is not None and trail > self.end_trail:
            return False
        return True

    def _trail_intersects(self, trail):
        """Return True if the trail intersects with our range.

        The trail is assumed to start at our ancestor (like the return value
        of :meth:`_get_trail`).

        """
        return (not self.start_trail or trail >= self.start_trail[:len(trail)]) \
           and (not self.end_trail or trail <= self.end_trail[:len(trail)])

    def intersects(self, node):
        """Return True if the node is partially or completely in our range.

        A node is partially in the range if it has descendant nodes in the
        range and other descendants outside.

        A shorthand for this method is ``range & node``.

        Use ``node in range`` to know whether a node is completely in the
        range.

        """
        trail = self._get_trail(node)
        return trail is not None and self._trail_intersects(trail)

    __and__ = intersects

    def is_full(self):
        """True if there is no start and end boundary, i.e. all descendants of the
        ancestor are in the range."""
        level = self._stack[0]
        return level.start_in_range() and level.end_in_range()

    def __iter__(self):
        return self._stack[-1]

    def __next__(self):
        return self._stack[-1].__next__()

    def reversed(self):
        """Iterate the current iteration level in reverse order."""
        return self._stack[-1].reversed()

    def __getitem__(self, i):
        """Get Node(s) at index or slice."""
        return self._stack[-1].node[i]

    def __setitem__(self, i, value):
        """Set Node(s) at index or slice. Slice step must be None or 1."""
        level = self._stack[-1]
        adjust_start = level.start_trail and len(level.start_trail) > level.depth
        adjust_end = level.end_trail and len(level.end_trail) > level.depth

        if isinstance(i, slice):
            if i.step not in (1, None):
                raise ValueError("can't use step other than 1 in slice")
            value = tuple(value)
            index, end, _ = i.indices(len(level.node))
            removed = end - index
            added = len(value)
            length = len(level.node) + added - removed

            if length == 0:
                # node has become empty
                level.start = 0
                level.index = -1
                level.end = -1
                if level.start_trail:
                    level.start_trail[level.depth:] = [0]
                if level.end_trail:
                    del level.end_trail[level.depth:]
            else:
                # adjust start boundary if needed
                if index <= level.start:
                    if index + removed > level.start:
                        level.start = index + added
                        if adjust_start:
                            # deleted node was on the start trail, truncate
                            del level.start_trail[level.depth:]
                            if 0 < level.start < length:
                                level.start_trail.append(level.start)
                    else:
                        level.start += added - removed
                        if adjust_start:
                            level.start_trail[level.depth] = level.start

                # adjust end boundary
                if index <= level.end:
                    if index + removed > level.end:
                        level.end = index + added
                        if adjust_end:
                            # deleted node was on the end trail, truncate
                            del level.end_trail[level.depth:]
                            if level.end < length:
                                level.end_trail.append(level.end)
                    else:
                        level.end += added - removed
                        if adjust_end:
                            level.end_trail[level.depth] = level.end
                elif length and level.end == -1 and level.end_trail is None:
                    # end can be -1 if node was empty or because of empty end trail,
                    # in this case it was because the node was empty, just move the end
                    level.end = length - 1

                # adjust level index
                if index <= level.index:
                    if index + removed > level.index:
                        level.index = index + added
                    else:
                        level.index += added - removed
        else:
            # just replace node at i
            if adjust_start and i == level.start:
                del level.start_trail[level.depth+1:]
            if adjust_end and i == level.end:
                del level.end_trail[level.depth+1:]

        level.node[i] = value

    def __delitem__(self, i):
        """Delete Node(s) at index or slice. Slice step must be None or 1."""
        if not isinstance(i, slice):
            i = slice(i, i+1)
        self[i] = ()

    @property
    def node(self):
        """The current node.

        This is the last yielded Node when iterating. *Setting* the property
        modifies the tree: it replaces the node in its parent with the
        specified node, or raises a ValueError when you try to replace the
        ancestor (i.e. not yet iterated over the range, or the range is empty).

        """
        # If iterating, the current node a child of the younghest iteration
        # level's node, pointed to by the index attribute.
        # If not iterating, the index is -1, and the current node is the level's
        # node itself. Most methods have special handling for both cases.
        level = self._stack[-1]
        return level.node if level.index == -1 else level.node[level.index]

    @node.setter
    def node(self, node):
        index = self._stack[-1].index
        if index == -1:
            if len(self._stack) == 1:
                raise ValueError("can't replace ancestor")
            self._stack.pop()
            index = self._stack[-1].index
        self[index] = node

    @property
    def index(self):
        """The index of the current (last yielded) node in its parent.

        Returns -1 if the ancestor is the current node or the range is empty.

        *Setting* the property selects the child node of the node at the
        current iteration level. Raises a ValueError when the index you specify
        is outside the range.

        .. note::

           The allowed range for the current iteration level is the range from
           :meth:`start` upto and including :meth:`end`. Note that, when you
           already :meth:`enter`-ed a node but not yet iterated over it, the
           displayed :attr:`index` value still relates to the current node,
           while the values returned by the :meth:`start` and :meth:`end`
           methods, and setting the property, already relate to the current
           (newly entered) iteration level.

        """
        index = self._stack[-1].index
        if index == -1 and len(self._stack) > 1:
            index = self._stack[-2].index
        return index

    @index.setter
    def index(self, index):
        level = self._stack[-1]
        if index < level.start or index > level.end:
            raise ValueError("index not in range")
        level.index = index

    def start(self):
        """The start index of the range in the current interation level's node."""
        return self._stack[-1].start

    def end(self):
        """The end index of the range in the current interation level's node."""
        return self._stack[-1].end

    def trail(self):
        """Trail to the current (last yielded) node."""
        trail = [level.index for level in self._stack]
        if trail[-1] == -1:
            trail.pop()
        return trail

    def depth(self):
        """The current iteration depth (0 or higher)."""
        return len(self._stack) - 1

    def in_range(self):
        """True if the current :attr:`node` and its descendants completely fall
        within the range."""
        level = self._stack[-1]
        if level.start < level.index < level.end:
            return True
        elif level.index > -1:
            level = level.child()
        return level.start_in_range() and level.end_in_range()

    def _goto_trail(self, trail):
        """(Internal) Go to the specified trail, which must be in our range.

        Equivalent to :meth:`reset` if trail is None or empty.

        """
        self.reset()
        if trail:
            for i in trail[:-1]:
                self._stack[-1].index = i
                self._stack.append(self._stack[-1].child())
            self._stack[-1].index = trail[-1]

    def goto(self, node):
        """Navigate to another node, returns True if that succeeded.

        Returns False if the node is not in our tree, or completely outside our
        range. The specified node may be partially outside the tree, which is
        the case when it crosses a range boundary.

        """
        trail = self._get_trail(node)
        if trail is None or not self._trail_intersects(trail):
            return False
        self._goto_trail(trail)
        return True

    def reset(self):
        """Reset iteration to the ancestor node, as if we are just instantiated."""
        del self._stack[1:]
        self._stack[-1].index = -1

    def enter(self):
        """Start iterating the current child node.

        Returns the depth *after entering* (which is always 1 or higher). If
        you store this value, and compare with the value returned by
        :meth:`leave`, you are back where you started when both values are the
        same.

        """
        level = self._stack[-1]
        if level.index != -1:
            self._stack.append(level.child())
        return len(self._stack) - 1

    def leave(self):
        """Stop iterating the current child node and pop back to the parent.

        Returns the depth *before leaving*, i.e. the same depth as the
        corresponding call to :meth:`enter`. Returns 0 if you try to leave the
        outermost node.

        """
        if len(self._stack) == 1:
            self._stack[-1].index = -1
            return 0
        self._stack.pop()
        return len(self._stack)

    def extract_tree(self):
        """Return a copy of the node tree, starting at the current
        :attr:`node`, including only the range.

        """
        r = self.from_here()
        tree = node = r.ancestor().copy(False)
        while True:
            for n in r:
                c = n.copy(False)
                node.append(c)
                if len(n):
                    node = c
                    r.enter()
                    break
            else:
                node = node.parent
                if not r.leave():
                    break
        return tree

    def nodes(self):
        """Yield all nodes from start node upto and including the end node.

        If there is no start boundary, the result is the same as
        :meth:`descendants`.

        When you :meth:`~generator.send` False to this generator, child nodes
        of the just yielded node will not be yielded.

        """
        self._goto_trail(self.start_trail)
        if self.start_trail:
            node = self.node
            if (yield node) is not False and len(node):
                yield from self.descendants()
        yield from self.forward()

    def __truediv__(self, cls):
        """Iterate over children that inherit the specified class(es)."""
        return self._get_predicate_iterator(cls, self.children())

    def __xor__(self, cls):
        """Iterate over children that do not inherit the specified class(es)."""
        return self._get_predicate_iterator(cls, self.children(), True)

    def forward(self, upto=None):
        """Iterate forward from the current :attr:`node`, starting with the
        right sibling.

        If you specify an ancestor node ``upto``, will not go outside that
        node.

        When you :meth:`~generator.send` False to this generator, child nodes
        of the just yielded node will not be yielded.

        """
        while True:
            for n in self:
                if (yield n) is not False and len(n):
                    self.enter()
                    break
            else:
                if not self.leave() or self.node is upto:
                    break

    def backward(self, upto=None):
        """Iterate backward from the current :attr:`node`, starting with the
        left sibling.

        If you specify an ancestor node ``upto``, will not go outside that
        node.

        When you :meth:`~generator.send` False to this generator, child nodes
        of the just yielded node will not be yielded.

        """
        while True:
            for n in self.reversed():
                if (yield n) is not False and len(n):
                    self.enter()
                    break
            else:
                if not self.leave() or self.node is upto:
                    break

    def ancestors(self):
        """Iterate over the ancestors of the current :attr:`node` that are in
        the range.

        Ends with the :meth:`ancestor`.

        """
        while self.depth():
            self.leave()
            yield self.node

        if self._stack[-1].index != -1:
            self._stack[-1].index = -1
            yield self.node

    def children(self, reverse=False):
        """Iterate over the children of the current :attr:`node` that are in
        the range.

        If ``reverse`` is set to True, yields the children in backward
        direction.

        """
        self.enter()
        yield from (self.reversed() if reverse else self)
        self.leave()

    def descendants(self, reverse=False):
        """Iterate over all descendants of the current :attr:`node` that are in
        the range.

        If ``reverse`` is set to True, yields all descendants in backward
        direction.

        When you :meth:`~generator.send` False to this generator, child nodes
        of the just yielded node will not be yielded.

        """
        iterate = (lambda n: n.reversed()) if reverse else iter
        depth = self.enter()
        while True:
            for n in iterate(self):
                if (yield n) is not False and len(n):
                    self.enter()
                    break
            else:
                if self.leave() == depth:
                    break

    @property
    def ls(self):
        """List the nodes of the current iteration level that are within the
        range, for debugging purposes.

        The first column shows the index of the nodes in their parent. If
        iteration is active, the current node is highlighted with an arrow.

        Colons are displayed if start and/or end boundaries of the range cross
        any descendants of this node, i.e. the node is not fully
        :meth:`in_range`.

        """
        level = self._stack[-1]
        print(repr(level.node))
        if not level.start_in_range():
            print("  : -- start boundary --")
        if level.end >= level.start:
            for i in range(level.start, level.end+1):
                text = "{:>3} {}".format(i, repr(level.node[i]))
                child = level.child(i)  # make a level child but do not store it
                if not child.start_in_range() or not child.end_in_range():
                    text += " (partly)"
                if i == level.index:
                    text += "  <----"
                print(text)
        elif len(level.node) == 0:
            print("  (empty node)")
        else:
            if level.start_in_range():
                boundaries = "no boundary" if level.end_in_range() else "end boundary"
            else:
                boundaries = "start boundary" if level.end_in_range() else "both boundaries"
            print("  (empty range; {} at {})".format(boundaries, level.start))
        if not level.end_in_range():
            if level.end < len(level.node) - 1:
                print("  : -- end boundary, {} more nodes --".format(len(level.node) - level.end - 1))
            else:
                print("  : -- end boundary --")

    @property
    def pwd(self):
        """Show the ancestry of the current node within the range, for
        debugging purposes.

        """
        nodes = [self.node]
        for n in self.node.ancestors():
            nodes.append(n)
            if n is self.ancestor():
                break
        nodes.reverse()
        _pwd(nodes)

    class _Level:
        """Manages iteration within the range over a Node."""
        def __init__(self, node, start_trail, end_trail, depth=0):
            self.node = node
            self.depth = depth
            self.start_trail = start_trail
            self.end_trail = end_trail
            # for convenience, store start and end indices for the range
            self.start = start_trail[depth] if start_trail else 0
            self.end = len(node) - 1 if end_trail is None else end_trail[depth] if len(end_trail) > depth else -1
            self.index = -1 # so that iteration will start correctly

        def __iter__(self):
            return self

        def __next__(self):
            index = self.start if self.index == -1 else self.index + 1
            if index > self.end:
                raise StopIteration
            self.index = index
            return self.node[index]

        def reversed(self):
            """Iterate in backward direction."""
            index = self.end if self.index == -1 else self.index - 1
            while index >= self.start:
                self.index = index
                yield self.node[index]
                index -= 1

        def child(self, index=None):
            """Return a "child" _Level for the current node.

            If ``index`` is None, use our own index.

            """
            if index is None:
                index = self.index
            # link to the boundary trails if we are on a boundary
            depth = self.depth + 1
            start_trail = self.start_trail if self.start_trail and index == self.start \
                and len(self.start_trail) > depth else None
            end_trail = self.end_trail if self.end_trail is not None and index == self.end else None
            return type(self)(self.node[index], start_trail, end_trail, depth)

        def start_in_range(self):
            """Return True if this node and its descendants completely fall within the range start boundary."""
            return not (self.start_trail and any(self.start_trail[self.depth:]))

        def end_in_range(self):
            """Return True if this node and its descendants completely fall within the range end boundary."""
            if self.end_trail is None:
                return True
            n = self.node
            for i in self.end_trail[self.depth:]:
                if i < len(n) - 1:
                    return False    # this descendant is sliced from the end
                n = n[i]
            return len(n) == 0      # not complete if the end node has children


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


def _pwd(nodes, file=None, style=None):
    """Helper function akin the unix ``pwd`` command.

    Prints nodes as a tree with single branches, first node first.

    """
    d = DUMP_STYLES[style or DUMP_STYLE_DEFAULT]
    for n, node in enumerate(nodes):
        print(''.join((d[1] * max(0, n-1), d[3] if n else '', repr(node))), file=file)


