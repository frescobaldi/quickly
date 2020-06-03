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

An Item can be constructed in two ways: either using the
:meth:`~HeadItem.from_origin` class method from tokens (this is done by the
LilyPondTransform class), or manually using the normal constructor.

You can specify all child items in the constructor, so theoretically you
can build a whole document in one expression.

To get the textual output of an item and all its child items, use the
:meth:`~Item.write` method. TODO: indenting.

Whitespace is handled in a smart way: Item subclasses can specify the preferred
whitespace ``before``, ``after`` and ``between`` elements, and items that have
head and tail texts can also specify the preperred whitespace after the head
and before the tail. When outputting the text, the whitespace between items is
combined to fulfil all requirements but to prevent double spaces.

When an Item is constructed from tokens using the :meth:`~HeadItem.with_origin`
constructor, it is able to write ifself back in the document if modified, using
the :meth:`~Item.edit` method.


"""

import collections
import reprlib

from parce.tree import Token

from ..node import Node
from .util import collapse_whitespace, combine_text


#: describes a piece of text at a certain position
Point = collections.namedtuple("Point", "pos end text modified")


HEAD_MODIFIED = 1
TAIL_MODIFIED = 2


class _SpacingProperty:
    """A property that denotes spacing.

    If it does not deviate from the default (set in the Item class definition
    prefixed with an underscore), it takes up no memory. Only when a value is
    changed, a dict is created to hold the values.

    """
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        d = getattr(obj, "_spacing", None)
        if d:
            value = d.get(self.name)
            if value is not None:
                return value
        return getattr(cls, '_' + self.name)

    def __set__(self, obj, value):
        d = getattr(obj, "_spacing", None)
        if not d:
            if value == getattr(obj, '_' + self.name):
                return # don't set if same as default
            d = obj._spacing = {}
        d[self.name] = value

    def __delete__(self, obj):
        d = getattr(obj, "_spacing", None)
        if d and self.name in d:
            del d[self.name]
            if not d:
                delattr(obj, "_spacing")


class Item(Node):
    """Abstract base class for all item types.

    Most Item types support children. Using keyword arguments you can give
    other spacing preferences than the default values for ``before``,
    ``after``, ``between``, ``after_head`` and ``before_tail``.

    """
    __slots__ = ("_spacing",)

    _head = None
    _tail = None
    _modified = 0

    _before = ""         #: minimum default whitespace to draw before this item
    _between = ""        #: minimum default whitespace to draw between child items
    _after = ""          #: minimum default whitespace to draw after this item

    _after_head = ""     #: minimum default whitespace to draw after the head
    _before_tail = ""    #: minimum default whitespace to draw before the tail

    def __init__(self, *children, **attrs):
        super().__init__(*children)
        if attrs:
            self._spacing = attrs

    def copy(self):
        """Copy the node, without the origin."""
        children = (n.copy() for n in self)
        return type(self)(*children, **getattr(self, '_spacing', {}))

    def __repr__(self):
        def result():
            yield self.__class__.__name__
            if self.head:
                yield self.repr_head()
            if len(self):
                yield "({} child{})".format(len(self), '' if len(self) == 1 else 'ren')
            pos = end = None
            p = self.head_point()
            if p:
                pos, end = p.pos, p.end
                if pos is not None:
                    p = self.tail_point()
                    if p and p.end is not None:
                        end = p.end
                    yield '[{}:{}]'.format(pos, end)
        return "<{}>".format(" ".join(result()))

    before = _SpacingProperty('before')          #: whitespace before this item
    between = _SpacingProperty('between')        #: whitespace between children
    after = _SpacingProperty('after')            #: whitespace after this item
    after_head = _SpacingProperty('after_head')  #: whitespace before first child
    before_tail = _SpacingProperty('before_tail')#: whitespace before tail

    @property
    def pos(self):
        """Return the position of this item.

        Only makes sense for items that have an origin, or one of the
        descendants has an origin. Possibly an expensive call, when a node tree
        has been heavily modified already. Returns None if this node and no
        single descendant of it has an origin.

        """
        try:
            return self._head_origin[0].pos
        except (AttributeError, IndexError):
            for n in self.descendants():
                try:
                    return n._head_origin[0].pos
                except (AttributeError, IndexError):
                    pass

    @property
    def end(self):
        """Return the end position of this item.

        Only makes sense for items that have an origin, or one of the
        descendants has an origin. Possibly an expensive call, when a node tree
        has been heavily modified already. Returns None if this node and no
        single descendant of it has an origin.

        """
        try:
            return self._tail_origin[-1].end
        except (AttributeError, IndexError):
            for n in reversed(self):
                end = n.end
                if end is not None:
                    return end
            try:
                return self._head_origin[-1].end
            except (AttributeError, IndexError):
                pass

    def find_child(self, position):
        """Return the child node at or to the right of position.

        Only returns a node that has an origin; ignores nodes without origin.

        """
        hi = len(self)
        if hi:
            nodes = list(self)
            i = 0
            while i < hi:
                mid = (i + hi) // 2
                n = nodes[mid]
                pos = n.pos
                while pos is None:
                    del nodes[mid]
                    if not nodes:
                        return
                    hi -= 1
                    if mid == hi:
                        mid -= 1
                    n = nodes[mid]
                    pos = n.pos
                if pos >= position:
                    hi = mid
                elif n.end <= position:
                    i = mid + 1
                else:
                    hi = mid
            i = min(i, len(nodes) - 1)
            return nodes[i]

    def find_descendant(self, position):
        """Return the youngest descendant node at or at the right of position.

        Only returns a node that has an origin; ignores nodes without origin.

        """
        n = self.find_child(position)
        while n is not None and len(n):
            n = n.find_child(position)
        return n

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

    def repr_head(self):
        """Return a repr value for our head value."""
        return reprlib.repr(self.head)

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
        """Return the Point describing the head text.

        Returns None for items that can't have a head text.

        """
        return None

    def tail_point(self):
        """Return the Point describing the tail text.

        Returns None for items that can't have a tail text.

        """
        return None

    def points(self, _last=''):
        """Yield three-tuples (before, point, after).

        Each ``point`` is a Point describing a text piece, ``before`` and
        ``after`` are the desired whitespace before and after the piece. For
        adjacent pieces, you may collapse whitespace. You don't have to supply
        a value for the ``_last`` argument, it is used by recursive calls to
        this method.

        """
        head_point = self.head_point()
        tail_point = self.tail_point()
        after = collapse_whitespace((self.after, _last))
        last_space = self.before_tail if tail_point else after
        if len(self):
            if head_point:
                yield self.before, head_point, self.after_head
            n = self[0]
            for m in self[1:]:
                yield from n.points(self.concat(n, m))
                n = m
            yield from n.points(last_space)
        elif head_point:
            yield self.before, head_point, last_space
        if tail_point:
            yield self.before_tail, tail_point, after

    def concat(self, node, next_node):
        """Return the minimum whitespace to apply between these child nodes.

        This method is called in the :meth:`points` method, when calculating
        whitespace between child nodes. By default, the value of the
        ``between`` attribute is returned. Reimplement this method to
        differentiate whitespacing based on the (type of the) nodes.

        """
        return self.between

    def write(self):
        """Return the combined (not yet indented) output of this node and its
        children.

        """
        return combine_text((b, p.text, a) for b, p, a in self.points())[1]

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

    def edits(self, tree):
        """Yield three-tuples (pos, end, text) denoting text changes.

        Changes to whitespace attributes are not registered as text changes.

        """
        tokens = tree.tokens()
        pos = tree.pos
        insert_after = None
        for before, point, after in self.points():
            b = '' if insert_after is None else collapse_whitespace((insert_after, before))
            if point.pos is None:
                # new item
                if point.text:
                    yield pos, pos, b + point.text
                    insert_after = after
            else:
                # existing item
                if point.pos > pos:
                    # see if old content needs to be deleted between pos and point.pos
                    del_pos = del_end = pos
                    for t in tokens:
                        if t.pos >= point.pos:
                            break
                        if t.pos >= pos:
                            del_end = t.end
                    if del_end > del_pos:
                        yield del_pos, del_end, b
                elif b:
                    yield point.pos, point.pos, b
                # modified?
                if point.modified:
                    yield point.pos, point.end, point.text
                pos = point.end
                insert_after = after
        if pos < tree.end:
            yield pos, tree.end, ''

    def edit(self, document, root=None):
        """Write back the modifications to the original parce document.

        Returns the number of changes that are made. If you don't specify the
        root Context, it will be requested from the document's tree builder.

        After writing back the modifications to the original document, you
        should transform a new dom.Document, because some parts need to be
        rebuilt.

        """
        root = root or document.builder().root
        n = 0
        with document:
            for pos, end, text in self.edits(root):
                document[pos:end] = text
                n += 1
        return n

    def replace(self, index, node):
        """Replace the node at index with the specified node.

        The origin of the old node is copied to the new, so that when
        writing out the node, its output exactly comes on the same spot in the
        document. For nodes without origin, this method does nothing more than
        ``self[index] = node``.

        """
        old = self[index]
        self[index] = node
        try:
            node._head_origin = old._head_origin
        except AttributeError:
            pass
        try:
            node._tail_origin = old._tail_origin
        except AttributeError:
            pass


class HeadItem(Item):
    """Item that has a fixed head value."""
    __slots__ = ('_head_origin', '_modified')

    def __init__(self, *children, **attrs):
        self._modified = 0
        super().__init__(*children, **attrs)

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

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        return cls(*children, **attrs)

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node._head_origin = head_origin
        return node


class TailItem(HeadItem):
    """Item that has a fixed head and tail value."""
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

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node._head_origin = head_origin
        node._tail_origin = tail_origin
        return node


class VarHeadItem(HeadItem):
    """Item that has a variable/writable head value."""
    __slots__ = ('_head', '_modified')

    def __init__(self, head, *children, **attrs):
        self._head = head
        self._modified = 0
        super().__init__(*children, **attrs)

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        head = cls.read_head(head_origin)
        return cls(head, *children, **attrs)

    def copy(self):
        """Copy the node, without the origin."""
        children = (n.copy() for n in self)
        return type(self)(self.head, *children, **getattr(self, '_spacing', {}))

