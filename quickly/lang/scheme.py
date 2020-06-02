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

    def common(self, items):
        """Yield dom nodes from tokens."""
        number = []
        quotes = []
        def nodes():
            for i in items:
                node = None
                if i.is_token:
                    if i.action in a.Number:
                        number.append(i)
                        if i.action != a.Number.Prefix:
                            yield self.factory({
                                a.Number.Int: dom.SchemeInt,
                                a.Number.Binary: dom.SchemeBinary,
                                a.Number.Octal: dom.SchemeOctal,
                                a.Number.Hexadecimal: dom.SchemeHexadecimal,
                                a.Number.Float: dom.SchemeFloat,
                                a.Number.Infinity: dom.SchemeFloat,
                                a.Number.NaN: dom.SchemeFloat,
                                a.Number.Boolean: dom.SchemeBoolean,
                            }[i.action], number)
                            number.clear()
                    elif i.action == a.Delimiter.Scheme.Quote:
                        quotes.append(i)
                    else:
                        yield self.factory({
                            a.Character: dom.SchemeChar,
                            a.Delimiter.Dot: dom.SchemeDot,
                            a.Keyword: dom.SchemeIdentifier,
                            a.Name: dom.SchemeIdentifier,
                        }[i.action], (i,))
                elif isinstance(i.obj, dom.Item):
                    yield i.obj
        for node in nodes():
            for q in reversed(quotes):
                node = self.factory(dom.SchemeQuote, (q,), (), node)
            quotes.clear()
            yield node

    ### transforming methods
    def root(self, items):
        return dom.SchemeDocument(*self.common(items))

    def list(self, items):
        head = items[:1]
        tail = (items.pop(),) if items[-1] == ')' else ()
        return self.factory(dom.SchemeList, head, tail, *self.common(items[1:]))

    def vector(self, items):
        head = items[:1]
        tail = (items.pop(),) if items[-1] == ')' else ()
        return self.factory(dom.SchemeVector, head, tail, *self.common(items[1:]))

    def string(self, items):
        """Create a String node."""
        return self.factory(dom.SchemeString, items)

    def multiline_comment(self, items):
        """Create a MultilineComment node."""
        return self.factory(dom.SchemeMultilineComment, items)

    def singleline_comment(self, items):
        """Create a SinglelineComment node."""
        return self.factory(dom.SchemeSinglelineComment, items)

    def scheme(self, items):
        """Create a Scheme node in LilyPond."""
        head = items[:1]    # $ or # token introducing scheme mode
        scheme = self.factory(dom.SchemeExpression, head)
        for i in self.common(items[1:]):
            scheme.append(i)
            break
        return scheme

    def argument(self, items):
        for i in self.common(items):
            return i


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

