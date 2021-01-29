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
This module defines the :class:`Element` class.

An Element describes an object and can have child objects. An Element can
display a ``head`` and optionally a ``tail``. The head is text that is printed
before the children (if any). The tail is displayed after the children, and
will in most cases be used as a closing delimiter.

An Element can be constructed in two ways: either using the
:meth:`~Element.from_origin` class method from tokens (this is done by the
LilyPondTransform class), or manually using the normal constructor.

You can specify all child elements in the constructor, so theoretically you can
build a whole document in one expression.

To get the textual output of an element and all its child elements, use the
:meth:`~Element.write` method. TODO: indenting.

Whitespace is handled in a smart way: Element subclasses can specify the
preferred whitespace before, after and between elements, and elements that have
head and tail texts can also specify the preperred whitespace after the head
and before the tail. When outputting the text, the whitespace between elements
is combined to fulfil all requirements but to prevent double spaces.

When an Element is constructed from tokens using the
:meth:`~Element.with_origin` constructor, it is able to write ifself back in
the document if modified, using the :meth:`~Element.edit` method.

:class:`Element` inherits from  :class:`~quickly.node.Node`, and thus from
:class:`list`, to build a reliable and easy to navigate tree structure.

"""

import collections
import reprlib

from ..node import Node
from .util import collapse_whitespace, combine_text


#: describes a piece of text at a certain position
Point = collections.namedtuple("Point", "pos end text modified")


HEAD_MODIFIED = 1
TAIL_MODIFIED = 2


class SpacingProperty:
    """A property that denotes spacing.

    If it does not deviate from the default (set in the Element class
    definition prefixed with an underscore), it takes up no memory. Only when a
    value is different from the default value, a dict is created to hold the
    values.

    """
    __slots__ = ('name',)

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, cls):
        try:
            return obj._spacing[self.name]
        except (AttributeError, KeyError):
            pass
        return getattr(cls, '_' + self.name)

    def __set__(self, obj, value):
        is_default = value == getattr(obj, '_' + self.name)
        try:
            d = obj._spacing
        except AttributeError:
            if is_default:
                return
            d = obj._spacing = {}
        else:
            if is_default:
                try:
                    del d[self.name]
                except KeyError:
                    pass
                else:
                    if not d:
                        del obj._spacing
                return
        d[self.name] = value

    def __delete__(self, obj):
        try:
            del obj._spacing[self.name]
        except (AttributeError, KeyError):
            return
        if not obj._spacing:
            del obj._spacing


class ElementType(type):
    """Metaclass for Element.

    This meta class automatically adds an empty ``__slots__`` attribute if it
    is not defined in the class body.

    """
    def __new__(cls, name, bases, namespace):
        if '__slots__' not in namespace:
            namespace['__slots__'] = ()
        return type.__new__(cls, name, bases, namespace)


class Element(Node, metaclass=ElementType):
    """Base class for all element types.

    The Element has no head or tail value.

    Child elements can be specified directly as arguments to the constructor.
    Using keyword arguments you can give other spacing preferences than the
    default values for ``space_before``, ``space_after``, ``space_between``,
    ``space_after_head`` and ``space_before_tail``.

    """
    __slots__ = ("_spacing",)

    _head = None
    _tail = None
    _modified = 0

    _space_before = ""         #: minimum default whitespace to draw before this element
    _space_after_head = ""     #: minimum default whitespace to draw after the head
    _space_between = ""        #: minimum default whitespace to draw between child elements
    _space_before_tail = ""    #: minimum default whitespace to draw before the tail
    _space_after = ""          #: minimum default whitespace to draw after this element

    space_before = SpacingProperty()       #: whitespace before this element
    space_after_head = SpacingProperty()   #: whitespace before first child
    space_between = SpacingProperty()      #: whitespace between children
    space_before_tail = SpacingProperty()  #: whitespace before tail
    space_after = SpacingProperty()        #: whitespace after this element

    def __init__(self, *children, **attrs):
        super().__init__(*children)
        for attribute, value in attrs.items():
            setattr(self, attribute, value)

    def copy(self):
        """Copy the node, without the origin."""
        children = (n.copy() for n in self)
        return type(self)(*children, **getattr(self, '_spacing', {}))

    def __repr__(self):
        def result():
            # class name with last part module prepended
            cls = self.__class__
            mod = cls.__module__.split('.')[-1]
            yield "{}.{}".format(mod, cls.__name__)
            # head and tail
            head = self.repr_head()
            if head is not None:
                yield head
            tail = self.repr_tail()
            if tail is not None:
                yield '...'
                yield tail
            # child count
            if len(self):
                yield "({} child{})".format(len(self), '' if len(self) == 1 else 'ren')
            # position
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

    @property
    def pos(self):
        """Return the position of this element.

        Only makes sense for elements that have an origin, or one of the
        descendants has an origin. Possibly an expensive call, when a node tree
        has been heavily modified already. Returns None if this node and no
        single descendant of it has an origin.

        """
        try:
            return self.head_origin[0].pos
        except (AttributeError, IndexError):
            for n in self.descendants():
                try:
                    return n.head_origin[0].pos
                except (AttributeError, IndexError):
                    pass

    @property
    def end(self):
        """Return the end position of this element.

        Only makes sense for elements that have an origin, or one of the
        descendants has an origin. Possibly an expensive call, when a node tree
        has been heavily modified already. Returns None if this node and no
        single descendant of it has an origin.

        """
        try:
            return self.tail_origin[-1].end
        except (AttributeError, IndexError):
            for n in reversed(self):
                end = n.end
                if end is not None:
                    return end
            try:
                return self.head_origin[-1].end
            except (AttributeError, IndexError):
                pass

    def find_child(self, position):
        """Return the child node at or to the right of position.

        Only returns a node that has a ``pos`` attribute, i.e. at least one
        of its descendants has an origin.

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
                if pos == position:
                    return n
                elif pos > position:
                    hi = mid
                else:
                    end = n.end
                    if end == position:
                        return n
                    elif end < position:
                        i = mid + 1
                    else:
                        hi = mid
            i = min(i, len(nodes) - 1)
            return nodes[i]

    def find_descendant(self, position):
        """Return the youngest descendant node that contains position.

        Only returns a node that has a ``pos`` attribute, i.e. at least one of
        its descendants has an origin. Returns None if there is no such node
        that contains this position.

        """
        m = None
        n = self.find_child(position)
        while n and n.pos <= position <= n.end:
            m = n
            n = n.find_child(position)
        return m

    def find_descendants(self, position):
        """Yield the child at position, then the grandchild, etc.

        Stops with the last node that really contains the position. Only yields
        nodes that have a ``pos`` attribute, i.e. at least one of its
        descendants has an origin.

        """
        n = self.find_child(position)
        while n and n.pos <= position <= n.end:
            yield n
            n = n.find_child(position)

    @property
    def head(self):
        """The head contents."""
        return self._head

    @head.setter
    def head(self, head):
        if head != self._head:
            self._head = head
            self._modified |= HEAD_MODIFIED

    @property
    def tail(self):
        """The tail contents."""
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

    def repr_head(self):
        """Return a representation for the head.

        The default implementation returns None.

        """
        return None

    def repr_tail(self):
        """Return a representation for the tail.

        The default implementation returns None.

        """
        return None

    def head_point(self):
        """Return the Point describing the head text.

        Returns None for elements that don't have a head text.

        """
        head = self.write_head()
        if head is not None:
            try:
                origin = self.head_origin
            except AttributeError:
                pos = end = None
            else:
                pos = origin[0].pos
                end = origin[-1].end
            modified = bool(self._modified & HEAD_MODIFIED)
            return Point(pos, end, head, modified)

    def tail_point(self):
        """Return the Point describing the tail text.

        Returns None for elements that can't have a tail text.

        """
        tail = self.write_tail()
        if tail is not None:
            try:
                origin = self.tail_origin
            except AttributeError:
                pos = end = None
            else:
                try:
                    pos = origin[0].pos
                    end = origin[-1].end
                except IndexError:      # can happen when tail was missing
                    pos = end = None
            modified = bool(self._modified & TAIL_MODIFIED)
            return Point(pos, end, tail, modified)

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
        after = collapse_whitespace((self.space_after, _last))
        last_space = self.space_before_tail if tail_point else after
        if len(self):
            if head_point:
                yield self.space_before, head_point, self.space_after_head
            n = self[0]
            for m in self[1:]:
                yield from n.points(self.concat(n, m))
                n = m
            yield from n.points(last_space)
        elif head_point:
            yield self.space_before, head_point, last_space
        if tail_point:
            yield self.space_before_tail, tail_point, after

    def concat(self, node, next_node):
        """Return the minimum whitespace to apply between these child nodes.

        This method is called in the :meth:`points` method, when calculating
        whitespace between child nodes. By default, the value of the
        ``space_between`` attribute is returned. Reimplement this method to
        differentiate whitespacing based on the (type of the) nodes.

        """
        return self.space_between

    def write(self):
        """Return the combined (not yet indented) output of this node and its
        children.

        """
        return combine_text((b, p.text, a) for b, p, a in self.points())[1]

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
                # new element
                if point.text:
                    yield pos, pos, b + point.text
                    insert_after = after
            else:
                # existing element
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
            node.head_origin = old.head_origin
        except AttributeError:
            pass
        try:
            node.tail_origin = old.tail_origin
        except AttributeError:
            pass


class HeadElement(Element):
    """Element that has a fixed head value."""
    __slots__ = ('head_origin',)

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        return cls(*children, **attrs)

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node.head_origin = head_origin
        return node


class BlockElement(HeadElement):
    """Element that has a fixed head and tail value."""
    __slots__ = ('tail_origin',)

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node.head_origin = head_origin
        node.tail_origin = tail_origin
        return node


class TextElement(HeadElement):
    """Element that has a variable/writable head value.

    This value must be given to the constructor, and can be modified later.

    """
    __slots__ = ('_head', '_modified')

    def __init__(self, head, *children, **attrs):
        self._head = head
        self._modified = 0
        super().__init__(*children, **attrs)

    def repr_head(self):
        """Return a repr value for our head value."""
        h = self.head
        if h is not None:
            return reprlib.repr(h)

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        head = cls.read_head(head_origin)
        return cls(head, *children, **attrs)

    def copy(self):
        """Copy the node, without the origin."""
        children = (n.copy() for n in self)
        return type(self)(self.head, *children, **getattr(self, '_spacing', {}))

