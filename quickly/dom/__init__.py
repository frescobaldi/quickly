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
This module defines a DOM (Document Object Model) for LilyPond source files.

This LilyPond DOM is a simple tree structure where a command or environment
is represented by a node with possible child nodes.

Some LilyPond commands have their own node type, and the arguments are
represented by child nodes, while other commands use a generic Command node.

This DOM is used in two ways:

1. Building a LilyPond source document from scratch. This helps to create
   a LilyPond document, although it in no way forces the output to be a valid
   LilyPond file.

2. Transform a *parce* tree of an existing LilyPond source document. All
   tokens are stored in the nodes (in the ``origin`` attributes), so it is
   possible to write back modifications to the original document without
   touching other parts of the document.


"""


