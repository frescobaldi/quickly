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
Html language and transformation definition (for lilypond-book).
"""

import re

import parce.action as a
from parce import lexicon
from parce.rule import (
    ARG, MATCH, TEXT, bygroup, dselect, findmember, ifarg, ifeq, pattern)
from parce.lang import html, lilypond_words
from parce.transform import Transform
from parce.util import Dispatcher


from quickly.dom import base, element, htm
from . import lilypond


class Html(base.XmlLike, html.Html):
    """Html language definition, with support for the lilypond-book tags.

    Those are: ``<lilypond ... />`` for short code, ``<lilypond> ...
    </lilypond>`` for longer code, ``<lilypondfile>filename</lilypondfile>``
    for a LilyPond file, and <musicxmlfile>filename</musicxmlfile> for a
    MusicXml file.

    """
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield r'(<)(lilypond(?:file)?|musicxmlfile)\b(>|/\s*>)?', bygroup(a.Delimiter, a.Name.Tag, a.Delimiter), \
            dselect(MATCH[2], {
                "lilypond": dselect(MATCH[3],
                    {'>': cls.lilypond_tag, None: cls.lilypond_book_options('lilypond')}),
                "lilypondfile": dselect(MATCH[3],
                    {'>': cls.lilypondfile_tag, None: cls.lilypond_book_options("lilypondfile")}),
                "musicxmlfile": dselect(MATCH[3],
                    {'>': cls.musicxmlfile_tag, None: cls.lilypond_book_options("musicxmlfile")}),
            })  # by default a close tag, stay in the context.
        yield from super().root

    @lexicon
    def lilypond_tag(cls):
        """Contents of a <lilypond> </lilypond> tag."""
        yield ifarg(r'/>'), a.Delimiter, -1
        yield r'(<\s*/)\s*(lilypond)\s*(>)', bygroup(a.Delimiter, a.Name.Tag, a.Delimiter), -1
        yield from lilypond.LilyPond.root

    @lexicon
    def lilypondfile_tag(cls):
        """Contents of a <lilypondfile> </lilypondfile> tag."""
        yield r'(<\s*/)\s*(lilypondfile)\s*(>)', bygroup(a.Delimiter, a.Name.Tag, a.Delimiter), -1
        yield r'[^\s<>]+', a.Literal.Url

    @lexicon
    def musicxmlfile_tag(cls):
        """Contents of a <musicxmlfile> </musicxmlfile> tag."""
        yield r'(<\s*/)\s*(musicxmlfile)\s*(>)', bygroup(a.Delimiter, a.Name.Tag, a.Delimiter), -1
        yield r'[^\s<>]+', a.Literal.Url

    @lexicon
    def lilypond_book_options(cls):
        """Options within the attribute space of a lilypond book tag."""
        yield r'>', a.Delimiter, -1, dselect(ARG, {
            "lilypond": cls.lilypond_tag,
            "lilypondfile": cls.lilypondfile_tag,
            "musicxmlfile": cls.musicxmlfile_tag,
            })
        yield pattern(ifeq(ARG, "lilypond", ":", None)), -1, cls.lilypond_tag("short form")
        yield r'\d+(?:\.\d+)?', a.Number
        yield r'[^\W\d]\w*(?:-\w+)*', findmember(TEXT, (
            (lilypond_words.lilypond_book_options, a.Name.Attribute),
            (lilypond_words.lilypond_book_units, a.Name.Builtin.Unit)), a.Name)
        yield r'=', a.Operator
        yield from cls.find_strings()


class HtmlTransform(Transform):
    """Transform Html (for lilypond-book) to quickly.dom.html"""

    ## helper methods and factory
    def factory(self, element_class, head_origin, tail_origin=(), *children):
        """Create a node, keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All items should be created using this method, so that
        it can be overridden for the case you don't want to remember the
        origin.

        """
        return element_class.with_origin(tuple(head_origin), tuple(tail_origin), *children)

    ## transform methods
    def root(self, items):
        """Process the ``root`` context."""
        return items

    def attrs(self, items):
        """Process the ``attrs`` context."""
        return items

    def cdata(self, items):
        """Process the ``cdata`` context."""
        return items

    def comment(self, items):
        """Process the ``comment`` context."""
        return self.factory(htm.Comment, items)

    def css_style_attribute(self, items):
        """Process the ``css_style_attribute`` context."""
        return items

    def css_style_tag(self, items):
        """Process the ``css_style_tag`` context."""
        return items

    def doctype(self, items):
        """Process the ``doctype`` context."""
        return items

    def dqstring(self, items):
        """Process the ``dqstring`` context."""
        head_origin = items[0],
        if items[-1] == '"':
            tail_origin = items.pop(),
        children = (self._action(t.action, t) for t in items[1:])
        return self.factory(htm.DqString, head_origin, tail_origin, *children)

    def sqstring(self, items):
        """Process the ``sqstring`` context."""
        head_origin = items[0],
        if items[-1] == "'":
            tail_origin = items.pop(),
        children = (self._action(t.action, t) for t in items[1:])
        return self.factory(htm.SqString, head_origin, tail_origin, *children)

    def internal_dtd(self, items):
        """Process the ``internal_dtd`` context."""
        return items

    def processing_instruction(self, items):
        """Process the ``processing_instruction`` context."""
        return items

    def script_tag(self, items):
        """Process the ``script_tag`` context."""
        return items

    def tag(self, items):
        """Process the ``tag`` context."""
        return items

    def lilypond_book_options(self, items):
        """Process the ``lilypond_book_options`` context."""
        return items

    def lilypond_tag(self, items):
        """Process the ``lilypond_tag`` context."""
        return items

    def lilypondfile_tag(self, items):
        """Process the ``lilypondfile_tag`` context."""
        return items

    def musicxmlfile_tag(self, items):
        """Process the ``musicxmlfile_tag`` context."""
        return items

    _action = Dispatcher()

    @_action(a.Escape)
    @_action(a.String.Escape)
    def entityref_action(self, token):
        return self.factory(htm.EntityRef, (token,))

    @_action(a.String.Single)
    @_action(a.String.Double)
    def string_action(self, token):
        return self.factory(htm.Text, (token,))

