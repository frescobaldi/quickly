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
Elements needed for Html or Xml text.

This module is called ``htm`` to keep its name short and to avoid confusion
with the language modules ``parce.lang.html`` and ``quickly.lang.html``.

Because entities can be resolved both in generic text and within attribute
strings, strings are block elements with childnodes containing the text or
entities, instead of TextElement such a LilyPond or Scheme strings.

TODO: add Element types for DTD, Style, Script etc, or at least some way
to catch the contents without traversing the full parce tree....

"""

from . import base, element


class Document(base.Document):
    """An Html document, normally has one Element child,
    but could contain more elements or text.

    """
    _space_between = ''


class Text(element.TextElement):
    """Html/Xml text contents (Text or Whitespace)."""
    def write_head(self):
        return escape(self.head)


class Comment(base.MultilineComment):
    """A Html/Xml comment node."""


class EntityRef(element.TextElement):
    r"""An entity reference like ``&euml;``, ``&#123;`` or ``&#xed;``.

    The ``head`` value is the part between the ``&`` and the ``;``.

    """
    @classmethod
    def read_head(cls, origin):
        return origin[0].text[1:-1]  # strip & and ;

    def write_head(self):
        return "&{};".format(self.head)


class CData(element.TextElement):
    r"""A CDATA section.

    The head value is the contents.

    """
    @classmethod
    def read_head(cls, origin):
        return origin[1]

    def write_head(self):
        # handle the unlikely case literal ']]>' is in text
        text = self.head.replace(']]>', ']]>]]&gt;<[CDATA[')
        return "<[CDATA[{}]]>".format(text)


class String(element.BlockElement):
    """Base class for strings."""
    def indent_children(self):
        return False


class SqString(String):
    """A single-quoted string.

    Inside are Text or EntityRef elements.

    """
    head = tail = "'"


class DqString(String):
    """A double-quoted string.

    Inside are Text or EntityRef elements.

    """
    head = tail = '"'


class Number(element.TextElement):
    """An integer or floating-point value.

    Only used in the attributes of LilyPond tags.

    """
    @classmethod
    def read_head(cls, origin):
        return (float if '.' in origin[0] else int)(origin[0])

    def write_head(self):
        return str(self.head)


class Unit(element.TextElement):
    """A short unit string like ``"mm"``, used in lilypond book options."""


class ProcessingInstruction(element.BlockElement):
    """A processing instruction.

    Inside are Text, String or EntityRef elements.

    """
    head = '<?'
    tail = '?>'


class Tag(element.BlockElement):
    """Base class for tags."""
    _space_between = ' '


class OpenTag(Tag):
    """An Html open tag: ``< >``.

    Has a TagName child, then zero or more Attribute children.

    """
    head = '<'
    tail = '>'


class CloseTag(Tag):
    """An Html close tag: ``</ >``."""
    head = '</'
    tail = '>'


class SingleTag(Tag):
    """An Html single (self closing) tag: ``< />``."""
    head = '<'
    tail = '/>'


class TagName(element.TextElement):
    """The name of a tag, a child of a Tag element."""


class Element(element.Element):
    """An Xml or Html element.

    Has an OpenTag child, then contents (Text or Element), and then a CloseTag
    child. Or alternatively, has only a SingleTag child.

    """

class Attribute(element.Element):
    """An Xml or Html attribute within an OpenTag or SingleTag.

    Has normally three children: AttrName, EqualSign, [DS]qString.
    In some cases it has only an AttrName child.

    """


class AttrName(element.TextElement):
    """The name of the attribute."""


class EqualSign(element.HeadElement):
    """The ``=`` in an attribute definition."""
    head = '='


class Colon(element.HeadElement):
    """The ``:`` in a short-form LilyPond html tag."""
    head = ':'


def escape(text):
    r"""Escape &, < and > to use text in HTML."""
    return text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")


def attrescape(text):
    r"""Escape &, <, > and ", to use text in HTML."""
    return escape(text).replace('"', "&quot;")


