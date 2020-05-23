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

from ..node import Node


class Item(Node):
    """The base node type for all LilyPond dom nodes.

    Al LilyPond DOM nodes have the tokens they originate from in the
    :attr:`origin` attribute. The attribute is None for manually created DOM
    nodes.

    """
    __slots__ = ('origin',)

    def __init__(self, *children, origin=None):
        super().__init__(*children)
        self.origin = origin

