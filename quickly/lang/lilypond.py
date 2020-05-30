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
LilyPond language and transform definition
"""

import itertools

from parce.transform import Transform
import parce.lang.lilypond
import parce.action as a

from quickly import dom



class LilyPond(parce.lang.lilypond.LilyPond):
    """LilyPond language definition."""
    @classmethod
    def get_scheme_target(cls):
        """Get *our* Scheme."""
        from .scheme import Scheme
        return Scheme.one_arg




class LilyPondTransform(Transform):
    """Transform LilyPond to Music."""
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
        """Find comment, string, scheme and markup.

        Yields dom.Item objects.

        """
        items = iter(items)
        for i in items:
            if not i.is_token:
                if isinstance(i.obj, dom.Item):
                    yield i.obj
                elif i.name == "markup":
                    origin = i.obj[:1]
                    markup = next(self.create_markup(itertools.chain(i.obj[1:], items)), None)
                    if markup:
                        yield self.factory(dom.Markup, origin, (), markup)


    def create_block(self, item_class, items):
        r"""Return a tree tuple(head_origin, nodes, tail_origin) for the items.

        The items are the contents of a block like \book { }.
        The ``head_origin`` are the first two tokens, the ``tail_origin`` the
        last token, if that is a '``}``'.

        """
        tail_origin = (items.pop(),) if items[-1] == '}' else ()
        head_origin = items[:2]
        nodes = items[2:].objects(dom.Item)
        return self.factory(item_class, head_origin, tail_origin, *nodes)

    def create_markup(self, items):
        """Read from items and yield nodes that can occur in markup."""
        items = iter(items)
        for i in items:
            if i.is_token:
                if i.action is a.Text:
                    yield self.factory(dom.MarkupWord, (i,))
                elif i.action in a.Name.Function:
                    nargs = LilyPond.get_markup_argument_count(i.text[1:])
                    args = []
                    if nargs:
                        for arg in self.create_markup(items):
                            args.append(arg)
                            if not isinstance(arg, dom.Comment):
                                nargs -= 1
                            if nargs == 0:
                                break
                    yield self.factory(dom.MarkupCommand, (i,), (), *args)
            elif isinstance(i.obj, dom.Item):
                yield i.obj

    ## transforming methods
    def root(self, items):
        """Concatenate all nodes in a Document object."""
        return dom.Document(*self.common(items))

    def book(self, items):
        """Create a Book or BookPart node."""
        item_class = dom.BookPart if items[1] == r'\bookpart' else dom.Book
        return self.create_block(item_class, items)

    def score(self, items):
        """Create a Score node (can also appear inside Markup and MarkupList)."""
        return self.create_block(dom.Score, items)

    def header(self, items):
        """Create a Header node."""
        return self.create_block(dom.Header, items)

    def paper(self, items):
        """Create a Paper node."""
        return self.create_block(dom.Paper, items)

    def layout(self, items):
        """Create a Layout node."""
        return self.create_block(dom.Layout, items)

    def midi(self, items):
        """Create a Midi node."""
        return self.create_block(dom.Midi, items)

    def layout_context(self, items):
        """Create a With or LayoutContext node."""
        item_class = dom.With if items[1] == r'\with' else dom.LayoutContext
        return self.create_block(item_class, items)

    def musiclist(self, items):
        return items

    def chord(self, items):
        return items

    def tempo(self, items):
        return items

    def context(self, items):
        return items

    def set_unset(self, items):
        return items

    def override(self, items):
        return items

    def script(self, items):
        return items

    def pitch(self, items):
        return items

    def duration(self, items):
        return items

    def duration_dots(self, items):
        return items

    def duration_scaling(self, items):
        return items

    def lyricmode(self, items):
        return items

    def lyricsto(self, items):
        return items

    def notemode(self, items):
        return items

    def drummode(self, items):
        return items

    def drummode(self, items):
        return items

    def chordmode(self, items):
        return items

    def chord_modifier(self, items):
        return items

    def varname(self, items):
        return items

    def markup(self, items):
        """Simply return the flattened contents, the markup will be constructed later."""
        result = []
        for i in items:
            if i.is_token or i.name != "markup":
                result.append(i)
            else:
                result.extend(i.obj)
        return result

    def markuplist(self, items):
        """Create a MarkupList node."""
        head = items[:1]
        tail = (items.pop(),) if items[-1] == '}' else ()
        return self.factory(dom.MarkupList, head, tail, *self.create_markup(items[1:]))

    def schemelily(self, items):
        return items

    def string(self, items):
        """Create a String node."""
        return self.factory(dom.String, items)

    def multiline_comment(self, items):
        """Create a MultilineComment node."""
        return self.factory(dom.MultilineComment, items)

    def singleline_comment(self, items):
        """Create a SinglelineComment node."""
        return self.factory(dom.SinglelineComment, items)


class LilyPondAdHocTransform(LilyPondTransform):
    """LilyPondTransform that does not keep the origin tokens.

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

