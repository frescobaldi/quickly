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

"""

from parce.tree import Token

from ..node import Node


class Item(Node):
    """The base node type for all LilyPond dom nodes.

    Al LilyPond DOM nodes have the tuple of tokens they originate from in the
    :attr:`origin` attribute. The attribute is None for manually created DOM
    nodes. The tokens must be adjacent.

    """
    __slots__ = ('origin', 'output')

    def __init__(self, *children, origin=None):
        super().__init__(*children)
        self.origin = origin

    def text(self):
        """Return our representation as in a LilyPond document."""
        try:
            return self.output
        except AttributeError:
            return ''.join(t.text for t in self.origin)

    def edit(self):
        """Return the edit that would be made to the document.

        This is a three-tuple (start, end, text).
        If we have no origin, start and end are None.
        If we have an origin but it is unchanged, text is None.

        """
        pos, end = self.pos, self.end
        return pos, end, getattr(self, 'output', None)

    @property
    def pos(self):
        if self.origin:
            return self.origin[0].pos

    @property
    def end(self):
        if self.origin:
            return self.origin[-1].end


class TokenItem(Item):
    """The base node type for Items that originate from one single token.

    It is specified as the first argument, and may also be a generic string.
    If a Token, it is set as the origin.

    """
    def __init__(self, token, *children):
        super().__init__(*children)
        if isinstance(token, Token):
            self.origin = token,
        else:
            self.output = token

