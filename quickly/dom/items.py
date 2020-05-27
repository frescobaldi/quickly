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
The Node types a LilyPond DOM document can be composed of.
"""

import re

import parce.action as a
from parce.lang import lilypond

from . import base


class Newline(base.Item):
    """A Newline.

    Not created from existing documents, but you can insert this node
    anywhere you want a newline in manually crafted documents.

    """
    __slots__ = ()
    head = ''
    after = '\n'


class BlankLine(Newline):
    """A blank line.

    Not created from existing documents, but you can insert this node
    anywhere you want a blank line in manually crafted documents.

    """
    __slots__ = ()
    after = '\n\n'



class Document(base.Item):
    """A LilyPond source document."""
    __slots__ = ()
    between = '\n\n'

    def concat(self, n, m):
        if isinstance(n, (SinglelineComment, Newline)):
            return '\n'
        return self.between


class _Block(base.EnclosedItem):
    """Base class for a block that wants newlines everywhere."""
    __slots__ = ()
    before = after = after_head = after_tail = '\n'
    head = '<fill in> {'
    tail = '}'


class Book(_Block):
    __slots__ = ()
    head = r"\book {"


class BookPart(_Block):
    __slots__ = ()
    head = r"\bookpart {"


class Score(_Block):
    __slots__ = ()
    head = r"\score {"


class Header(_Block):
    __slots__ = ()
    head = r"\header {"


class Paper(_Block):
    __slots__ = ()
    head = r"\paper {"


class Layout(_Block):
    __slots__ = ()
    head = r"\layout {"


class Midi(_Block):
    __slots__ = ()
    head = r"\midi {"


class Pitch(base.HeadItem):
    """A pitch note name."""
    __slots__ = ()


class Mode(base.HeadItem):
    r"""The mode subcommand of the \key statement."""
    __slots__ = ()


class Key(base.Item):
    r"""A \key statement.

    Must have a Pitch and a Mode child.

    """
    __slots__ = ()
    head = r"\key"


class Clef(base.Item):
    r"""A \clef statement.

    Must have a Symbol or String child indicating the clef type.

    """
    __slots__ = ()
    head = r"\clef"


class String(base.HeadItem):
    r"""A quoted string."""
    __slots__ = ()
    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text[1:] if t.action is a.String.Escape else t.text
            for t in origin[1:-1])

    def write_head(self):
        return '"{}"'.format(re.sub(r'([\\"])', r'\\\1', self.head))


class Comment(base.HeadItem):
    r"""Base class for comment items."""
    __slots__ = ()


class MultilineComment(Comment):
    r"""A multiline comment between %{ and %}."""
    __slots__ = ()
    @classmethod
    def read_head(cls, origin):
        end = -1 if origin[-1] == "%}" else None
        return ''.join(t.text for t in origin[1:end])

    def write_head(self):
        return '%{{{}%}}'.format(self.head)


class SinglelineComment(Comment):
    r"""A singleline comment after %."""
    __slots__ = ()
    after = '\n'
    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write_head(self):
        return '%{}'.format(self.head)


class Markup(base.HeadItem):
    r"""A \markup, \markuplines or \markuplist expression."""
    __slots__ = ()


class MarkupWord(base.HeadItem):
    """A word in markup mode."""
    __slots__ = ()


class MarkupList(base.EnclosedItem):
    """A bracketed markup expression, like { ... }."""
    __slots__ = ()
    after_head = before_tail = between = " "
    head = "{"
    tail = "}"


class MarkupCommand(base.HeadItem):
    r"""A known markup command, like \bold <arg>."""
    __slots__ = ()


class MarkupUserCommand(base.HeadItem):
    r"""An unknown markup command."""
    __slots__ = ()


