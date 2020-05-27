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
(Abstract) base classes for the quickly.dom items.

The Item classes you can choose from are in the items module.

TODO
====

- distinguish between Items that originate from tokens from a document
  and Items that originate from ad-hoc created tokens,

  e.g. transform_text(LilyPond.root, "<c' d e>")

  Ad hoc tokens must not have the origin set, while tokens from a document
  have.


24 mei
======
thinkin....

an Item:

- has some value
- that can originate from tokens origin (read)
- that can be set manually
- that must also be output (write)

how do we know if the value was altered manually?
- a "modified" flag
- compute the value each time from the origin?

When writing a new document:
- write out from the value

When writing back to an existing document:
- if the value has changed, replace the origins's slice with the new output
- if the value has not changed, do nothing


"""

import reprlib

from parce.tree import Token

from ..node import Node


HEAD_MODIFIED = 1
TAIL_MODIFIED = 2


class Item(Node):
    """Abstract base class for all item types."""
    __slots__ = ('_head_origin',)
    _head = None
    _tail = None
    _modified = 0

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, reprlib.repr(self.head))

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

    def write(self):
        """Write out the combined output of the Item and its children.

        Writes a space character in between every node's output. Does not yet
        differentiate spacing, and does not yet insert newlines (e.g. after
        a singleline comment a newline is mandatory :-) but this is not yet
        handled.)

        """
        def output():
            yield self.write_head()
            yield from (item.write() for item in self)
            yield self.write_tail()
        return ' '.join(text for text in output() if text)

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

    def edit_head(self):
        """Return a three-tuple(start, end, text) denoting how to modify an
        existing document.

        If start and end are None: this is a new node, with text to be added.
        If start and end are not None, but text is None: the node is unchanged
        and the text does not need to be altered. If text is not None: the
        range from start to end needs to be replaced with text.

        """
        try:
            origin = self._head_origin
        except AttributeError:
            return None, None, self.write_head()
        pos = origin[0].pos
        end = origin[-1].end
        return pos, end, self.write() if self._modified & HEAD_MODIFIED else None

    def edit_tail(self):
        """Return a three-tuple(start, end, text) denoting how to modify an
        existing document.

        If start and end are None: this is a new node, with text to be added.
        If start and end are not None, but text is None: the node is unchanged
        and the text does not need to be altered. If text is not None: the
        range from start to end needs to be replaced with text.

        """
        try:
            origin = self._tail_origin
        except AttributeError:
            return None, None, self.write_tail()
        pos = origin[0].pos
        end = origin[-1].end
        return pos, end, self.write() if self._modified & TAIL_MODIFIED else None

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children):
        return cls(*children)

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children):
        node = cls.from_origin(head_origin, tail_origin, *children)
        if head_origin:
            node._head_origin = head_origin
        if tail_origin:
            node._tail_origin = tail_origin
        return node


class HeadItem(Item):
    """Item that has a variable head value."""
    __slots__ = ('_head', '_modified')

    def __init__(self, head, *children):
        self._head = head
        self._modified = 0
        super().__init__(*children)

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children):
        head = cls.read_head(head_origin)
        return cls(head, *children)


class EnclosedItem(Item):
    """Item that has a tail value as well."""
    __slots__ = ('_tail_origin',)

