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
The quickly.music module.

This module will provide a music object model that can be used for two things:

* building a LilyPond document (or expressions) from scratch
* representing a parsed LilyPond source document

*First* use case: Construct a music document or expression, optionally
manipulate it and then output it as a LilyPond source document (e.g. for
composition algorithms or import from other formats). It should be simple,
extensible and flexible.

The *second* use case is the most challenging: A LilyPond source document is
lexed by parce.lang.lilypond, and then transformed into a music Document
expression.

This expression is then used to manipulate and query the source document.
It should be possible to write modifications back to the source document, not
by bluntly replacing the full source document, but by accurately replacing
the modified parts.




"""


