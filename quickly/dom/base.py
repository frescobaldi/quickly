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






27 mei
======


Whitespace handling...

and indenting...

where is what whitespace determined?....

a4-5

Note
  Pitch
  Duration
  Direction
    Fingering

no whitespace.


{ c d e }
Simultaneous
  Note
    Pitch
  Note
    Pitch
  Note

whitespace around the notes
We could do:
  Simultaneous draws a space between the children


a full document: how many newlines between stuff?
- at minimum one
- certainly a newline after a single line comment
- in most cases two.


Maybe we should invent a Newline item, also capture Newline tokens?

Or should we make the automatic formatting so robust that it is never
needed to insert line breaks automatically?


It becomes clear that we want to know what whitespace to put
*after* what node.

A node can say that itself.

But is a node's last child is a singleline comment, that newline should
be honoured. So a newline wins over a regular space.

And, a node itself can specify what to put between the children
and before its tail. This should still consult wat each node wants.

Maybe:

    Item.after

    attribute containing the whitespace to draw after this item.
    (either '', ' ', or '\n')

    By default, this consults the last child and its own class-level preference.

SO:

an item itself has a preference for whitespace between its children
an item can have a preference for whitespace to draw after a certain Item type
an item has a preference for whitespace drawn after it


item.whitespace_after(childitem)

Document will return '\n\n' for most types but '\n' for comment


Item.after  (whitespace to draw after this item)
Item.between (whitespace to draw between child items)

Item.whitespace(item):



after       # minimum wsp to draw after
before      # minimum wsp to draw before item
between     # minimum wsp to draw between child items

def concat(self, item, next_item):
    return max_spacing(item.after, next_item.before, self.between)


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


    before = ""         #: minimum whitespace to draw before this item
    between = ""        #: minimum whitespace to draw between child items
    after = ""          #: minimum whitespace to draw after this item

    after_head = ""     #: minimum whitespace to draw after the head
    before_tail = ""    #: minimum whitespace to draw before the tail


    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, reprlib.repr(self.head))

    def value_space(self, whitespace):
        """Return a tuple useable as sorting key to value whitespace.

        Newlines are preferred over normal spaces, and those are preferred
        over no space (empty string).

        """
        return whitespace.count('\n'), whitespace.count(' ')

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
        """Return a three-tuple (before, text, after).

        The ``text`` is the string output of this node. The ``before`` and
        ``after`` values are strings as well, indicating the minimal whitespace
        that should be applied before and after this node.

        """
        result = []
        result_before = self.before
        result_after = self.after
        head = self.write_head()
        tail = self.write_tail()
        if head:
            result.append(head)
        if len(self):
            n = self[0]
            before, text, after = n.write()
            if head:
                result.append(max(self.after_head, before, key=self.value_space))
            else:
                result_before = before
            result.append(text)
            for m in self[1:]:
                before, text, nafter = m.write()
                if text:
                    result.append(max(self.concat(n, m), after, before, key=self.value_space))
                    result.append(text)
                after = nafter
                n = m
            if not tail:
                result_after = max(self.after, after, key=self.value_space)
        if tail:
            if len(self):
                result.append(max(self.before_tail, after, key=self.value_space))
            elif head:
                result.append(max(self.after_head, self.before_tail, key=self.value_space))
        return result_before, ''.join(result), result_after

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
    between = " "
    __slots__ = ('_tail_origin',)



