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
A Transformer that inherits :class:`parce.transform.Transformer`.

Our transformer adds a method that's called on unknown parce contexts.

"""


import parce.transform


class Transformer(parce.transform.Transformer):
    """A Transformer that yields the origin for unknown parce contexts.

    This creates the transform :class:`~parce.transform.Item` with name
    ``<unknown>`` (including the angle brackets) which pops up whereever a
    lexicon is encountered no transform method could be found for.

    """
    def missing(self, context):
        """Returns the origin for untransformed parce contexts."""
        first = context.first_token()
        last = context.last_token()
        origin = (first,) if first is last else (first, last)
        return origin


