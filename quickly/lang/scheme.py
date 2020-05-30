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
Scheme language and transformation definition.
"""

import itertools

from parce.transform import Transform
import parce.lang.scheme
import parce.action as a

from quickly import dom


class Scheme(parce.lang.scheme.SchemeLily):
    """Scheme language definition."""
    @classmethod
    def common(cls, pop=0):
        from . import lilypond
        yield r"#{", a.Bracket.LilyPond.Start, pop, lilypond.LilyPond.schemelily
        yield from super(parce.lang.scheme.SchemeLily, cls).common(pop)


class SchemeTransform(Transform):
    """Transform Scheme quickly.dom."""
    ## helper methods and factory
    def factory(self, item_class, head_origin, tail_origin=(), *children):
        """Create an Item, keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All items should be created using this method, so that
        it can be overridden for the case you don't want to remember the
        origin.

        """
        return item_class.with_origin(tuple(head_origin), tuple(tail_origin), *children)

    def common(self):
        pass

    ### transforming methods
    def root(self, items):
        return items

    def list(self, items):
        return items

    def vector(self, items):
        return items

    def string(self, items):
        return items

    def multiline_comment(self, items):
        return items

    def singleline_comment(self, items):
        return items

    def one_arg(self, items):
        return items


class SchemeAdHocTransform(SchemeTransform):
    """SchemeTransform that does not keep the origin tokens.

    This is used to create pieces (nodes) of a LilyPond document from text, and
    then use that pieces to compose a larger Document or to edit an existing
    document. It is undesirable that origin tokens then would mistakenly be
    used as if they originated from the document that's being edited.

    """
    def factory(self, item_class, head_origin, tail_origin=(), *children):
        """Create an Item *without* keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All items should be created using this method, so that
        it can be overridden for the case you don't want to remember the
        origin.

        """
        return item_class.from_origin(tuple(head_origin), tuple(tail_origin), *children)

