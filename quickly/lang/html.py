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
    ARG, MATCH, TEXT, bygroup, dselect, findmember, ifeq, pattern)
from parce.lang import html, lilypond_words
from parce.util import Dispatcher
from parce.transform import add_untransformed

from quickly.dom import base, element, htm
from . import lilypond


class Html(base.XmlLike, html.Html):
    """Html language definition, with support for the lilypond-book tags.

    Those are: ``<lilypond ... />`` for short code, ``<lilypond> ...
    </lilypond>`` for longer code, ``<lilypondfile>filename</lilypondfile>``
    for a LilyPond file, and ``<musicxmlfile>filename</musicxmlfile>`` for a
    MusicXml file.

    These tags also support the attribute notation that's outlined in the
    `LilyPond documentation <https://lilypond.org/doc/latest/Documentation/usage/html>`_.

    """
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield r'(<)(lilypond(?:file)?|musicxmlfile)\b(>|/\s*>)?', bygroup(a.Delimiter, a.Name.Tag, a.Delimiter), \
            dselect(MATCH[2], {
                "lilypond": dselect(MATCH[3],
                    {'>': lilypond.LilyPond.html_lilypond_tag, None: cls.lilypond_book_options('lilypond')}),
                "lilypondfile": dselect(MATCH[3],
                    {'>': cls.tag, None: cls.lilypond_book_options("lilypondfile")}),
                "musicxmlfile": dselect(MATCH[3],
                    {'>': cls.tag, None: cls.lilypond_book_options("musicxmlfile")}),
            })  # by default a close tag, stay in the context.
        yield from super().root

    @lexicon
    def lilypond_book_options(cls):
        """Options within the attribute space of a lilypond book tag."""
        yield r'>', a.Delimiter, -1, ifeq(ARG, "lilypond", lilypond.LilyPond.html_lilypond_tag, cls.tag)
        yield pattern(ifeq(ARG, "lilypond", ":", None)), a.Delimiter, -1, lilypond.LilyPond.html_lilypond_tag("short form")
        yield r'\d+(?:\.\d+)?', a.Number
        yield r'[^\W\d]\w*(?:-\w+)*', findmember(TEXT, (
            (lilypond_words.lilypond_book_options, a.Name.Attribute),
            (lilypond_words.lilypond_book_units, a.Name.Builtin.Unit)), a.Name)
        yield r'=', a.Operator
        yield from cls.find_strings()
        yield r'/\s*>', a.Delimiter, -1   # self-closing tag, no LilyPond input here


class HtmlTransform(base.Transform):
    """Transform Html (for lilypond-book) to :mod:`quickly.dom.htm` elements.

    Note that this transform currently ignores the following lexicons:
    ``css_style_attribute``, ``css_style_tag``, ``doctype``, ``internal_dtd``
    and ``script_tag``.

    This means the constructed :class:`htm.Document <quickly.dom.htm.Document>`
    cannot write back the full document. You should only rely on the
    lilypond-tags and their content.

    The alternative would be to disable css and javascript in the inherited
    parce language definition, but then we loose the nice highlighting of CSS
    and JS parts.

    """

    ## helper methods and factory
    def factory(self, element_class, head_origin, tail_origin=(), *children):
        """Create a node, keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All items should be created using this method, so that
        it can be overridden for the case you don't want to remember the
        origin.

        """
        return element_class.with_origin(tuple(head_origin), tuple(tail_origin), *children)

    ## unimplemented transform contexts
    css_style_attribute = None
    css_style_tag = None
    doctype = None
    internal_dtd = None
    script_tag = None

    ## transform methods
    @add_untransformed
    def root(self, items):
        """Process the ``root`` context."""
        return htm.Document(*self.tag(items))

    @add_untransformed
    def attrs(self, items):
        """Process the ``attrs`` context.

        Returns a list of :class:`htm.Attribute` elements and a ``tail_origin``
        tuple.

        """
        return self.lilypond_book_options(items)

    def cdata(self, items):
        """Process the ``cdata`` context."""
        return self.factory(htm.CData, items)

    def comment(self, items):
        """Process the ``comment`` context."""
        return self.factory(htm.Comment, items)

    def dqstring(self, items):
        """Process the ``dqstring`` context."""
        head_origin = items[0],
        tail_origin = (items.pop(),) if items[-1] == '"' else ()
        children = (self._action(t.action, t) for t in items[1:])
        return self.factory(htm.DqString, head_origin, tail_origin, *children)

    def sqstring(self, items):
        """Process the ``sqstring`` context."""
        head_origin = items[0],
        tail_origin = (items.pop(),) if items[-1] == "'" else ()
        children = (self._action(t.action, t) for t in items[1:])
        return self.factory(htm.SqString, head_origin, tail_origin, *children)

    def processing_instruction(self, items):
        """Process the ``processing_instruction`` context."""
        head_origin = items[0],
        tail_origin = (items.pop(),) if items[-1] == '?>' else ()
        # combine multiple text tokens into Text elements, and keep [SD]qString
        # and EntityRef elements
        def children():
            origin = []
            for i in items[1:]:
                obj = self._action(i.action, i) if i.is_token else i.obj
                if obj:
                    if origin:
                        yield self.factory(htm.Text, origin)
                        origin.clear()
                    yield obj
                else:
                    origin.append(i)
            if origin:
                yield self.factory(htm.Text, origin)
        return self.factory(htm.ProcessingInstruction, head_origin, tail_origin, *children())

    @add_untransformed
    def tag(self, items):
        """Process the ``tag`` context.

        Returns a list of nodes representing the contents.

        """
        nodes = []
        z = len(items)
        i = 0
        while i < z:
            if items[i].is_token:
                if items[i].action in (a.Text, a.Whitespace):
                    nodes.append(self.factory(htm.Text, (items[i],)))
                elif items[i].action is a.Escape:
                    nodes.append(self.factory(htm.EntityRef, (items[i],)))
                elif items[i].action is a.Delimiter:
                    if items.peek(i+1, a.Name.Tag, "attrs", "<untransformed>") or \
                       items.peek(i+1, a.Name.Tag, a.Delimiter, "<untransformed>") or \
                       items.peek(i+1, a.Keyword, a.Name.Tag.Definition, "<untransformed>"):
                        # untransformed css style, script tag or doctype declaration
                        nodes.append(self.factory(base.Unknown, (items[i], items[i+3].obj.last_token())))
                        i += 1
                    elif i < z - 2:
                        head_origin = items[i:i+1]
                        tagname = self.factory(htm.TagName, items[i+1:i+2])
                        if '/' in items[i].text: # and z - i < 2: (will always be the case)
                            # closing tag, will also be the end of this context
                            tail_origin = items[i+2:i+3]
                            nodes.append(self.factory(htm.CloseTag, head_origin, tail_origin, tagname))
                        else:
                            cls = None
                            attrs = ()
                            if items[i+2].is_token:
                                if items[i+2].group == -2:
                                    tail_origin = items[i+2:i+3]
                                    if '/' in items[i+2].text:
                                        # self closing tag without attributes
                                        cls = htm.SingleTag
                                    else:
                                        # opening tag without attributes, new tag ctxt will follow
                                        cls = htm.OpenTag
                            elif items[i+2].name == 'attrs':
                                attrs, tail_origin = items[i+2].obj
                                # opening or self-closing tag with attributes that follow
                                cls = htm.SingleTag if tail_origin and '/' in tail_origin[0].text else htm.OpenTag
                            elif items[i+2].name == 'lilypond_book_options':
                                # short form of LilyPond input within (self-closing) lilypond tag?
                                attrs, tail_origin = items[i+2].obj
                                if tail_origin and tail_origin[0] == ':' and items.peek(i + 3, "html_lilypond_tag"):
                                    # yes, add the music to the attrs
                                    attrs = list(attrs)
                                    attrs.append(self.factory(htm.Colon, tail_origin))
                                    objs, tail_origin = items[i+3].obj
                                    attrs.extend(objs)
                                    cls = htm.SingleTag
                                    i += 1
                                else:
                                    # no, just handle the attrs
                                    cls = htm.SingleTag if tail_origin and '/' in tail_origin[0].text else htm.OpenTag
                            if cls:
                                nodes.append(htm.Element(self.factory(cls, head_origin, tail_origin, tagname, *attrs)))
                    i += 2
            elif items[i].name == "tag":
                nodes[-1].extend(items[i].obj) # add contents and CloseTag
            elif items[i].name == "html_lilypond_tag":
                nodes[-1].extend(items[i].obj[0]) # add contents and CloseTag
            i += 1
        return nodes

    @add_untransformed
    def lilypond_book_options(self, items):
        """Process the ``lilypond_book_options`` context.

        Returns a list of Attribute elements and a tuple with the ending
        delimiter (``:`` or ``>`` or ``/>``).

        """
        attrs = []
        tail_origin = ()
        z = len(items)
        i = 0
        while i < z:
            t = items[i]
            if t.is_token:
                if t.action is a.Name.Attribute:
                    attrs.append(htm.Attribute(self.factory(htm.AttrName, (t,))))
                elif t == '=':
                    if attrs and len(attrs[-1]) == 1:
                        attrs[-1].append(self.factory(htm.EqualSign, (t,)))
                elif t.action is a.Delimiter:
                    tail_origin = (t,)
                    break
                elif t == '"' and items.peek(i, a.String, "<untransformed>"):
                    # this happens with a css style attribute; create Unknown
                    if attrs and len(attrs[-1]) > 1:
                        attrs[-1].append(self.factory(base.Unknown, (t, items[i+1].obj.last_token())))
                    i += 1
                # only appear in lilypond_book_options
                elif t.action is a.Number:
                    if attrs and len(attrs[-1]) > 1:
                        attrs[-1].append(self.factory(htm.Number, (t,)))
                elif t.action is a.Name.Builtin.Unit:
                    if attrs and len(attrs[-1]) > 2:
                        attrs[-1].append(self.factory(htm.Unit, (t,)))
                elif t.action is a.Name:
                    # unknown LilyPond book attribute...
                    attrs.append(htm.Attribute(self.factory(htm.AttrName, (t,))))
            elif attrs and len(attrs[-1]) == 2:
                attrs[-1].append(t.obj) # a string value
            i += 1
        return attrs, tail_origin

    _action = Dispatcher()

    @_action(a.Escape)
    @_action(a.String.Escape)
    def entityref_action(self, token):
        return self.factory(htm.EntityRef, (token,))

    @_action(a.String.Single)
    @_action(a.String.Double)
    def string_action(self, token):
        return self.factory(htm.Text, (token,))


class HtmlAdHocTransform(base.AdHocTransform, HtmlTransform):
    """Html Transform that does not keep the originating tokens."""
    pass


