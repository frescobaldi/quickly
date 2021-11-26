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
with the language modules :mod:`parce.lang.html` and :mod:`quickly.lang.html`.

.. note::

   Although :mod:`parce` is perfectly capable of parsing CSS style and JavaScript
   script tags and attributes, this module does not implement node types for that.

   This means that although you can construct full Html documents with
   JavaScript, CSS, (and LilyPond and Scheme of course), it is not possible to
   write such documents back to text from the DOM, because *parce* neatly
   parses the CSS and JavaScript, but the our transformer in
   :mod:`quickly.lang.html` does not transform those to :mod:`~quickly.dom.htm`
   elements, so they get lost when writing back a DOM document that was read
   from text, back to text.

   But you can construct html style and script elements manually of course and
   write them out to text.

Every Html tag maps to an :class:`Element` node, which normally has one or more
chilren: either one :class:`SingleTag` node, or an :class:`OpenTag` node at the
beginning and a :class:`CloseTag` at the end, and in between other Elements,
:class:`Text` or :class:`EntityRef` nodes.

The tag nodes inherit :class:`~quickly.dom.element.BlockElement`, have the
delimiters (``<``, ``</``, ``>`` or ``/>``) in their head and tail, and have a
:class:`TagName` child and possibly one or more :class:`Attribute` children.

An attribute node normally has three children: an :class:`AttrName`, an
:class:`EqualSign` and a :class:`DqString` or :class:`SqString` value.

Because entity references can appear both in generic text and in attribute
strings, those strings nodes are block elements with the quotes in their head
and tail, and childnodes containing the Text or EntityRef elements.

How LilyPond fits in
--------------------

LilyPond nodes (:mod:`lily.Document <quickly.dom.lily.Document>`) can appear as
contents in an :class:`Element` that has a ``lilypond`` open tag (like:
``<lilypond staffsize=2> { c d e f g } </lilypond>``); or within the
:class:`SingleTag` node of an Element that has no further contents (this
happens when the short form like ``<lilypond : { c d e f g } />`` is used).

For the ``<lilypondfile>`` and ``<musicxmlfile>`` tags, the attributes are
handled supporting the specialy LilyPond attributes (with or without value).
The filename is in the Text contents.

Some examples
-------------

Short LilyPond notation, the LilyPond node is a child of the ``lilypond``
:class:`SingleTag` element::

    >>> from quickly.lang.html import Html
    >>> from parce.transform import transform_text
    >>> d = transform_text(Html.root, '<html><h1>Title</h1><p>Some music...</p><lilypond staffsize=2: { c d e f g } /></html>')
    >>> d.dump()
    <htm.Document (1 child)>
     ╰╴<htm.Element (5 children)>
        ├╴<htm.OpenTag (1 child) [0:6]>
        │  ╰╴<htm.TagName 'html' [1:5]>
        ├╴<htm.Element (3 children)>
        │  ├╴<htm.OpenTag (1 child) [6:10]>
        │  │  ╰╴<htm.TagName 'h1' [7:9]>
        │  ├╴<htm.Text 'Title' [10:15]>
        │  ╰╴<htm.CloseTag (1 child) [15:20]>
        │     ╰╴<htm.TagName 'h1' [17:19]>
        ├╴<htm.Element (3 children)>
        │  ├╴<htm.OpenTag (1 child) [20:23]>
        │  │  ╰╴<htm.TagName 'p' [21:22]>
        │  ├╴<htm.Text 'Some music...' [23:36]>
        │  ╰╴<htm.CloseTag (1 child) [36:40]>
        │     ╰╴<htm.TagName 'p' [38:39]>
        ├╴<htm.Element (1 child)>
        │  ╰╴<htm.SingleTag (4 children) [40:79]>
        │     ├╴<htm.TagName 'lilypond' [41:49]>
        │     ├╴<htm.Attribute (3 children)>
        │     │  ├╴<htm.AttrName 'staffsize' [50:59]>
        │     │  ├╴<htm.EqualSign [59:60]>
        │     │  ╰╴<htm.Number 2 [60:61]>
        │     ├╴<htm.Colon [61:62]>
        │     ╰╴<lily.Document (1 child)>
        │        ╰╴<lily.MusicList (5 children) [63:76]>
        │           ├╴<lily.Note 'c' [65:66]>
        │           ├╴<lily.Note 'd' [67:68]>
        │           ├╴<lily.Note 'e' [69:70]>
        │           ├╴<lily.Note 'f' [71:72]>
        │           ╰╴<lily.Note 'g' [73:74]>
        ╰╴<htm.CloseTag (1 child) [79:86]>
           ╰╴<htm.TagName 'html' [81:85]>

LilyPond tag notation, the LilyPond node is a child of the ``lilypond``
element::

    >>> d = transform_text(Html.root, '<html><h1>Title</h1><p>Some music...</p><lilypond staffsize=2> { c d e f g } </lilypond></html>')
    >>> d.dump()
    <htm.Document (1 child)>
     ╰╴<htm.Element (5 children)>
        ├╴<htm.OpenTag (1 child) [0:6]>
        │  ╰╴<htm.TagName 'html' [1:5]>
        ├╴<htm.Element (3 children)>
        │  ├╴<htm.OpenTag (1 child) [6:10]>
        │  │  ╰╴<htm.TagName 'h1' [7:9]>
        │  ├╴<htm.Text 'Title' [10:15]>
        │  ╰╴<htm.CloseTag (1 child) [15:20]>
        │     ╰╴<htm.TagName 'h1' [17:19]>
        ├╴<htm.Element (3 children)>
        │  ├╴<htm.OpenTag (1 child) [20:23]>
        │  │  ╰╴<htm.TagName 'p' [21:22]>
        │  ├╴<htm.Text 'Some music...' [23:36]>
        │  ╰╴<htm.CloseTag (1 child) [36:40]>
        │     ╰╴<htm.TagName 'p' [38:39]>
        ├╴<htm.Element (3 children)>
        │  ├╴<htm.OpenTag (2 children) [40:62]>
        │  │  ├╴<htm.TagName 'lilypond' [41:49]>
        │  │  ╰╴<htm.Attribute (3 children)>
        │  │     ├╴<htm.AttrName 'staffsize' [50:59]>
        │  │     ├╴<htm.EqualSign [59:60]>
        │  │     ╰╴<htm.Number 2 [60:61]>
        │  ├╴<lily.Document (1 child)>
        │  │  ╰╴<lily.MusicList (5 children) [63:76]>
        │  │     ├╴<lily.Note 'c' [65:66]>
        │  │     ├╴<lily.Note 'd' [67:68]>
        │  │     ├╴<lily.Note 'e' [69:70]>
        │  │     ├╴<lily.Note 'f' [71:72]>
        │  │     ╰╴<lily.Note 'g' [73:74]>
        │  ╰╴<htm.CloseTag (1 child) [77:88]>
        │     ╰╴<htm.TagName 'lilypond' [79:87]>
        ╰╴<htm.CloseTag (1 child) [88:95]>
           ╰╴<htm.TagName 'html' [90:94]>



"""

import html.entities

from . import base, element


class Element(element.Element):
    """An Xml or Html element.

    Has an OpenTag child, then contents (Text or Element), and then a CloseTag
    child. Or alternatively, has only a SingleTag child.

    """
    def to_plaintext(self, entity_resolver=None):
        """Return all text contents of all children as a concatenated string.

        The entity resolver, if given, is a callable used to resolve entities
        and may return a string or an Element node tree which is then
        traversed. But by default, :func:`html.unescape` is used.

        """
        if entity_resolver is None:
            def entity_resolver(name):
                return html.unescape('&{};'.format(name))

        def to_text(obj):
            if isinstance(obj, Element):
                return obj.to_plaintext()
            elif isinstance(obj, Text):
                return obj.head
            elif isinstance(obj, EntityRef):
                return to_text(entity_resolver(obj.head))
            elif isinstance(obj, str):
                return obj
            return ''

        return ''.join(map(to_text, self))


class Document(base.Document, Element):
    """An Html document, normally has one Element child,
    but could contain more elements or text.

    """
    _space_between = ''


class Text(element.TextElement):
    """Html/Xml text contents (Text or Whitespace)."""
    def write_head(self):
        return html.escape(self.head)


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
        return (float if '.' in origin[0].text else int)(origin[0].text)

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
    def indent_children(self):
        return False


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


class _ElementConstructor:
    """The ``m`` "element constructor" object can be used to manually make
    :class:`Element` nodes easily. You call any method on it; the name will
    become the tag name. Arguments can be either strings or other quickly.dom
    nodes, they become the child tags. Keyword arguments become attributes of
    the created tag.

    For example::

        >>> from quickly.dom.htm import m
        >>> n = m.div(m.h1('title', style="font-weight: bold;"), m.img(src="bla.png"))
        >>> n.dump()
        <htm.Element (4 children)>
         ├╴<htm.OpenTag (1 child)>
         │  ╰╴<htm.TagName 'div'>
         ├╴<htm.Element (3 children)>
         │  ├╴<htm.OpenTag (2 children)>
         │  │  ├╴<htm.TagName 'h1'>
         │  │  ╰╴<htm.Attribute (3 children)>
         │  │     ├╴<htm.AttrName 'style'>
         │  │     ├╴<htm.EqualSign>
         │  │     ╰╴<htm.DqString (1 child)>
         │  │        ╰╴<htm.Text 'font-weight: bold;'>
         │  ├╴<htm.Text 'title'>
         │  ╰╴<htm.CloseTag (1 child)>
         │     ╰╴<htm.TagName 'h1'>
         ├╴<htm.Element (1 child)>
         │  ╰╴<htm.SingleTag (2 children)>
         │     ├╴<htm.TagName 'img'>
         │     ╰╴<htm.Attribute (3 children)>
         │        ├╴<htm.AttrName 'src'>
         │        ├╴<htm.EqualSign>
         │        ╰╴<htm.DqString (1 child)>
         │           ╰╴<htm.Text 'bla.png'>
         ╰╴<htm.CloseTag (1 child)>
            ╰╴<htm.TagName 'div'>
        >>> n.write()
        '<div><h1 style="font-weight: bold;">title</h1><img src="bla.png"/></div>'

    If an element has no child elements, a :class:`SingleTag` is used
    automatically.

    If you need an attribute name that is not a valid Python identifier name,
    use a dictionary to specify the attributes::

        >>> m.html(**{"xmlns:html": "http://www.w3.org/1999/xhtml"}).write()
        '<html xmlns:html="http://www.w3.org/1999/xhtml"/>'

    If you need a tag name that is not a valid Python member name, call ``m``
    directly, with the tag name as the first argument::

        >>> m('asds:yo', 'title', **{'blurk:ns': "taop"}).write()
        '<asds:yo blurk:ns="taop">title</asds:yo>'

    """
    def __getattr__(self, name):
        def func(*children, **attrs):
            attributes = [
                (Attribute(AttrName(key), EqualSign(), DqString(Text(value))) if value is not None
                 else Attribute(AttrName(key))) for key, value in attrs.items()]
            node = Element()
            if children:
                node.append(OpenTag(TagName(name), *attributes))
                node.extend(Text(c) if isinstance(c, str) else c for c in children)
                node.append(CloseTag(TagName(name)))
            else:
                node.append(SingleTag(TagName(name), *attributes))
            return node
        return func

    def __call__(self, name, *children, **attrs):
        return self.__getattr__(name)(*children, **attrs)


m = _ElementConstructor()
m.__globals__ = {}  # avoid Sphinx error: see e.g. https://github.com/sphinx-doc/sphinx/issues/8917

