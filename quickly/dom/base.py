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
Base classes for the quickly.dom items.

An :class:`Item` describes an object and can have child objects. An Item can
display a ``head`` and optionally a ``tail``. The head is text that is printed
before the children (if any). The tail is displayed after the children, and
will in most cases be used as a closing delimiter.

An :class:Item can be constructed in two ways: either using the
:meth:from_origin class method from tokens (this is done by the
LilyPondTransform class), or manually using the normal constructor.

You can specify all child items in the constructor, so theoretically you
can build a whole document in one expression.

To get the textual output of an item and all its child items, use the
:meth:`~Item.output` method. TODO: indenting.

Whitespace is handled in a smart way: Item subclasses can specify the preferred
whitespace ``before``, ``after`` and ``between`` elements, and items that draw
head and tail texts can also specify the preperred whitespace after the head
and before the tail. When outputting the text, the whitespace between items is
combined to fulfil all requirements but to prevent double spaces.

When an Item is constructed from tokens using the :meth:`~Item.with_origin`
constructor, it is able to write ifself back in the document if modified, using
the :meth:`~Item.edit_head` and :meth:`~Item.edit_tail` method.


"""

import collections
import reprlib

from parce.tree import Token

from ..node import Node
from .util import collapse_whitespace


#: describes a piece of text at a certain position
Point = collections.namedtuple("Point", "pos end text modified")


HEAD_MODIFIED = 1
TAIL_MODIFIED = 2


class Item(Node):
    """Abstract base class for all item types."""
    __slots__ = ('__dict__', '_head_origin',)
    _head = None
    _tail = None
    _modified = 0

    before = ""         #: minimum whitespace to draw before this item
    between = ""        #: minimum whitespace to draw between child items
    after = ""          #: minimum whitespace to draw after this item

    after_head = ""     #: minimum whitespace to draw after the head
    before_tail = ""    #: minimum whitespace to draw before the tail

    def __init__(self, *children, **attrs):
        super().__init__(*children)
        if attrs:
            self.__dict__.update(attrs)

    def __repr__(self):
        def result():
            yield self.__class__.__name__
            if self.head:
                yield reprlib.repr(self.head)
            if len(self):
                yield "({} child{})".format(len(self), '' if len(self) == 1 else 'ren')
        return "<{}>".format(" ".join(result()))

    @property
    def head(self):
        return self._head

    @head.setter
    def head(self, head):
        if head != self._head:
            self._head = head
            self._modified |= HEAD_MODIFIED

    @property
    def tail(self):
        return self._tail

    @tail.setter
    def tail(self, tail):
        if tail != self._tail:
            self._tail = tail
            self._modified |= TAIL_MODIFIED

    @classmethod
    def read_head(cls, head_origin):
        """Return the value as computed from the specified origin Tokens.

        The default implementation concatenates the text from all tokens.

        """
        return ''.join(t.text for t in head_origin)

    @classmethod
    def read_tail(cls, tail_origin):
        """Return the value as computed from the specified origin Tokens.

        The default implementation concatenates the text from all tokens.

        """
        return ''.join(t.text for t in tail_origin)

    def head_point(self):
        """Return the Point describing the head text."""
        try:
            origin = self._head_origin
        except AttributeError:
            pos = end = None
        else:
            pos = origin[0].pos
            end = origin[-1].end
        head = self.write_head()
        modified = bool(self._modified & HEAD_MODIFIED)
        return Point(pos, end, head, modified)

    def tail_point(self):
        """Return the Point describing the tail text.

        Returns None for items that can't have a tail text.

        """
        return None

    def points(self):
        """Yield three-tuples (before, point, after).

        Each ``point`` is a Point describing a text piece, ``before`` and
        ``after`` are the desired whitespace before and after the piece. For
        adjacent pieces, you may collapse whitespace.

        """
        yield from self._points(self.after)

    def _points(self, last_space):
        """Interally used by points()."""
        if len(self):
            yield self.before, self.head_point(), self.after_head
            n = self[0]
            for m in self[1:]:
                points = n.points()
                p = next(points)
                for q in points:
                    yield p
                    p = q
                yield p[0], p[1], collapse_whitespace((p[2], self.concat(n, m)))
                n = m
            points = n.points()
            p = next(points)
            for q in points:
                yield p
                p = q
            yield p[0], p[1], collapse_whitespace((p[2], last_space))
        else:
            yield self.before, self.head_point(), last_space

    def write(self):
        """Return a three-tuple (before, text, after).

        The ``text`` is the string output of this node. The ``before`` and
        ``after`` values are strings as well, indicating the minimal whitespace
        that should be applied before and after this node.

        """
        result = []
        after = []
        for b, p, a in self.points():
            after.append(b)
            if p.text:
                result.append(collapse_whitespace(after))
                result.append(p.text)
                after.clear()
            after.append(a)
        if result:
            return result[0], ''.join(result[1:]), collapse_whitespace(after)
        return self.before, '', self.after

    def output(self):
        """Return the formatted (not yet indented) output."""
        return ''.join(self.write()[1:])

    def concat(self, node, next_node):
        """Return the minimum whitespace to apply between these child nodes.

        This method is called in the :meth:`write` method, when concatenating
        child nodes. By default, the value of the ``between`` attribute is
        returned. Reimplement this method to differentiate whitespacing based
        on the (type of the) nodes.

        """
        return self.between

    def write_head(self):
        """Return the textual output that represents our ``head`` value.

        The default implementation just returns the ``head`` attribute,
        assuming it is text.

        """
        return self.head

    def write_tail(self):
        """Return the textual output that represents our ``tail`` value.

        The default implementation just returns the ``tail`` attribute,
        assuming it is text.

        """
        return self.tail

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        return cls(*children, **attrs)

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node._head_origin = head_origin
        return node


class HeadItem(Item):
    """Item that has a variable head value."""
    __slots__ = ('_head', '_modified')

    def __init__(self, head, *children, **attrs):
        self._head = head
        self._modified = 0
        super().__init__(*children, **attrs)

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        head = cls.read_head(head_origin)
        return cls(head, *children, **attrs)


class EnclosedItem(Item):
    """Item that has a tail value as well."""
    __slots__ = ('_tail_origin',)

    def tail_point(self):
        try:
            origin = self._tail_origin
        except AttributeError:
            pos = end = None
        else:
            pos = origin[0].pos
            end = origin[-1].end
        tail = self.write_tail()
        modified = bool(self._modified & TAIL_MODIFIED)
        return Point(pos, end, tail, modified)

    def points(self):
        """Reimplemented to add a tail point as well."""
        yield from self._points(self.before_tail)
        yield self.before_tail, self.tail_point(), self.after

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node._head_origin = head_origin
        node._tail_origin = tail_origin
        return node


class CustomItem(EnclosedItem):
    """Item where head and tail are both writable."""
    __slots__ = ('_head', '_tail', '_modified')

    def __init__(self, head, tail, *children, **attrs):
        self._head = head
        self._tail = tail
        self._modified = 0
        super().__init__(*children, **attrs)

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        head = cls.read_head(head_origin)
        tail = cls.read_tail(tail_origin)
        return cls(head, tail, *children, **attrs)

