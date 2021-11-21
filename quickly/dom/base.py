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

import re

import parce.action as a
from parce import lexicon

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


