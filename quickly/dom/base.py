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


class Item(Node):
    """The base node type for all LilyPond dom nodes.

    Al LilyPond DOM nodes have the tuple of tokens they originate from in the
    :attr:`origin` attribute. The attribute is None for manually created DOM
    nodes. The tokens must be adjacent.

    """
    __slots__ = ('origin',)

    modified = False    #: the value can't be changed
    value = ''          #: set this to the text the item should write

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, reprlib.repr(self.value))

    @classmethod
    def with_origin(cls, origin, *children):
        """Construct this item from the origin and keep the origin."""
        node = cls.from_origin(origin, *children)
        node.origin = origin
        return node

    @classmethod
    def from_origin(cls, origin, *children):
        """Construct this item from the origin but don't keep the origin."""
        return cls(*children)

    def write(self):
        """Return the textual output that represents our value."""
        return self.value

    def edit(self):
        """Return a three-tuple(start, end, text) denoting how to modify an
        existing document.

        If start and end are None: this is a new node, with text to be added.
        If start and end are not None, but text is None: the node is unchanged
        and the text does not need to be altered. If text is not None: the
        range from start to end needs to be replaced with text.

        """
        try:
            origin = self.origin
        except AttributeError:
            return None, None, self.write()
        pos = origin[0].pos
        end = origin[-1].end
        return pos, end, self.write() if self.modified else None


class ValueItem(Item):
    """An Item that has a dynamic value that determines its output.

    You should implement :meth:`read` and :meth:`write`.

    """
    __slots__ = ('_value', '_modified')

    def __init__(self, value, *children):
        self._value = value
        self._modified = False
        super().__init__(*children)

    @property
    def value(self):
        """Return our value."""
        return self._value

    @value.setter
    def value(self, value):
        """Modify our value."""
        if value != self._value:
            self._value = value
            self._modified = True

    @property
    def modified(self):
        """Return true when the Item's value was modified."""
        return self._modified

    @classmethod
    def read(cls, origin):
        """Return the value as computed from the specified origin Tokens."""
        return ''.join(t.text for t in origin)

    @classmethod
    def from_origin(cls, origin, *children):
        """Construct this item from the origin but don't keep the origin."""
        value = cls.read(origin)
        node = cls(value, *children)
        return node


