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
Some general element types and some base classes for the quickly.dom elements.
"""


### NOTE: if adding classes/functions here, update docs/source/dom/base.rst!


import re

import parce.action as a
from parce import lexicon, transform

from . import element


## Base classes:

class Document(element.Element):
    """Base class for a full source document."""

    _space_between = '\n\n'

    def concat(self, n, m):
        if isinstance(n, (SinglelineComment, Newline)):
            return '\n'
        return self.space_between


class String(element.TextElement):
    """Base class for a string element."""

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text[1:] if t.action is a.String.Escape else t.text
            for t in origin[1:-1])

    def write_head(self):
        return '"{}"'.format(re.sub(r'([\\"])', r'\\\1', self.head))


class Comment(element.TextElement):
    """Base class for a comment element."""


class SinglelineComment(Comment):
    """Base class for a multiline comment element."""
    def indent_override(self):
        """Returns 0 if this comment has at least three comment characters
        at the beginning.

        If it is on a line on its own, the current indent will then be ignored.

        """
        head = self.write_head()[:3]
        if len(head) == 3 and len(set(head)) == 1:
            return 0


class MultilineComment(Comment):
    """Base class for a multiline comment element."""


class BackslashCommand(element.TextElement):
    r"""A command that starts with a backslash, like in LaTeX and LilyPond.

    The backslash (``\``) is not in the head value.

    """
    @classmethod
    def check_head(cls, head):
        r"""Return False if the head value starts with a backslash (``\``)."""
        return not head.startswith('\\')

    @classmethod
    def read_head(cls, origin):
        """Strip the backslash of the origin token."""
        text = ''.join(t.text for t in origin)[1:]
        return text

    def write_head(self):
        """Add the backslash on write-out."""
        return '\\' + self.head


## Generic elements:

class Newline(element.Element):
    """A Newline.

    Not created from existing documents, but you can insert this node
    anywhere you want a newline in manually crafted documents.

    """
    head = ''
    _space_after = '\n'


class BlankLine(element.Element):
    """A blank line.

    Not created from existing documents, but you can insert this node
    anywhere you want a blank line in manually crafted documents.

    """
    head = ''
    _space_after = '\n\n'


class Line(element.Element):
    """Container that prints the child nodes on one line with a space in between.

    Not created from existing documents, but you can insert this node in a
    Document when you want some nodes to be on the same line, for example when
    you want to write a comment at the end of the preceding line instead of on
    a line of its own.

    """
    _space_before = _space_after = '\n'
    _space_between = ' '


class Column(element.Element):
    """Container that prints every child node on a new line.

    Not created from existing documents, but you can insert this node in a
    Document when you want some nodes to be stacked vertically.

    """
    _space_before = _space_after =  _space_between = '\n'


class Text(element.TextElement):
    """Generic text that is printed unmodified."""


## Special element:

class Unknown(element.HeadElement):
    """Represents a document region that is not transformed.

    This element can only occur in documents transformed from source. It is
    used to denote reqions that are not transformed, such as CSS style tags or
    attributes, or script tags, in Html documents containing LilyPond music.

    *Parce* has fancy highlighting for those text fragments, but it makes no
    sense to try to transform those also to useful DOM nodes. So instead, we
    simply record the positions in the source document of these fragments using
    the first and the last token of such contexts that are not transformed.

    Calling :meth:`write_head` on this element results in an exception, because
    it does not know how it looks. But it knows the position in the document,
    because the first and the last untransformed tokens are in the origin.

    Before you can write out a document containing :class:`Unknown` elements
    fully out (e.g. using :meth:`~.element.Element.write` or
    :meth:`~.element.Element.write_indented`), you should replace those
    elements with e.g. :class:`Text` elements that have the text such as it
    appears in the source document. This can be done using
    :func:`.util.replace_unknown`.

    You *can* :meth:`~.element.Element.edit` documents with this element however,
    it will simply leave the unknown parts of the document as they are.

    """
    def write_head(self):
        """Raise RuntimeError."""
        raise RuntimeError(
            "can't write head value of Unknown element.\n"
            "Hint: replace Unknown with Text elements.")


## Language and Transform base/helper classes

class XmlLike:
    """Mixin class for a language definition that bases on parce.lang.Xml.

    Adds the comsume attribute to some lexicons, like comment and string, which
    makes transforming easier.

    """
    @lexicon(consume=True)
    def comment(cls):
        yield from super().comment

    @lexicon(consume=True)
    def sqstring(cls):
        yield from super().sqstring

    @lexicon(consume=True)
    def dqstring(cls):
        yield from super().dqstring

    @lexicon(consume=True)
    def cdata(cls):
        yield from super().cdata

    @lexicon(consume=True)
    def processing_instruction(cls):
        yield from super().processing_instruction


class Transform(transform.Transform):
    """Transform base class that keeps the origin tokens.

    Provides the :meth:`factory` method that creates the DOM node.

    """
    def factory(self, element_class, head_origin, tail_origin=(), *children):
        """Create an Element, keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All elements should be created using this method, so
        that it can be overridden for the case you don't want to remember the
        origin.

        """
        return element_class.with_origin(tuple(head_origin), tuple(tail_origin), *children)


class AdHocTransform:
    """Transform mixin class that does *not* keep the origin tokens.

    This is used to create pieces (nodes) of a LilyPond document from text, and
    then use that pieces to compose a larger Document or to edit an existing
    document. It is undesirable that origin tokens then would mistakenly be
    used as if they originated from the document that's being edited.

    """
    def factory(self, element_class, head_origin, tail_origin=(), *children):
        """Create an Item *without* keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All items should be created using this method, so that
        it can be overridden for the case you don't want to remember the
        origin.

        """
        return element_class.from_origin(tuple(head_origin), tuple(tail_origin), *children)


