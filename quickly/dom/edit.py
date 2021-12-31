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
The Edit base class, to perform operations on a DOM document in different ways.
"""

import parce.document

from ..node import Range
from .element import Element


class Edit:
    """Base class to perform operations on a DOM document via a
    :class:`~quickly.node.Range`, an :class:`.element.Element` node, a
    :class:`parce.Document` or a selection of a parce document in a
    :class:`parce.Cursor`.

    You must implement at least :meth:`Edit.edit_range` to make it work. You
    can choose to reimplement other methods to alter behaviour or
    functionality.

    Then you create an instance, and you can call one of the ``edit_xxx()``
    methods.

    """

    #: If True, when there is a selection, a Range is created from the root
    #: node, otherwise from the younghest common ancestor.
    range_from_root = False

    #: If True, a Range is created from the cursor's position to the end,
    #: instead of the full document in case there is no selection.
    range_from_cursor = False

    def edit(self, music):
        """Convenience method calling one of the other edit_xxx methods depending on the type."""
        meth = (self.edit_cursor   if isinstance(music, parce.Cursor)
           else self.edit_document if isinstance(music, parce.document.AbstractDocument)
           else self.edit_range    if isinstance(music, Range)
           else self.edit_node     if isinstance(music, Element)
           else None)
        if meth:
            return meth(music)
        raise TypeError('unknown music type')

    def edit_cursor(self, cursor):
        """Edit the range pointed to by the :class:`parce.Cursor`.

        If the cursor has no selection, by default the whole document is used.

        """
        d = cursor.document().get_transform(True)
        r = start = end = None
        if cursor.has_selection():
            start_node = d.find_descendant_right(cursor.pos)
            end_node = d.find_descendant_left(cursor.end)
            if end_node or start_node:
                r = Range.from_nodes(start_node, end_node, self.range_from_root)
                if start_node:
                    start = start_node.pos
                if end_node:
                    end = end_node.end
        elif self.range_from_cursor:
            start_node = d.find_descendant_right(cursor.pos)
            if start_node:
                r = Range.from_nodes(start_node)
        if r is None:
            r = Range(d)
        result = self.edit_range(r)
        r.ancestor().edit(cursor.document(), start=start, end=end)
        return result

    def edit_document(self, document):
        """Edit the full :class:`parce.Document`.

        The default implementation calls :meth:`edit_cursor` with a
        :class:`parce.Cursor` pointing to the beginning of the document,
        without selection.

        """
        return self.edit_cursor(parce.Cursor(document))

    def edit_node(self, node):
        """Edit the full :class:`.element.Element` node.

        The default implementation calls :meth:`edit_range` with a Range
        encompassing the full element node.

        """
        return self.edit_range(Range(node))

    def edit_range(self, r):
        """Edit the specified :class:`~quickly.node.Range`.

        At least this method needs to be implemented to actually perform the
        operation.

        """
        raise NotImplementedError



