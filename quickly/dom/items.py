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
    _after = '\n'

    def __init__(self, **attrs):
        super().__init__(**attrs)


class BlankLine(Newline):
    """A blank line.

    Not created from existing documents, but you can insert this node
    anywhere you want a blank line in manually crafted documents.

    """
    _after = '\n\n'

    def __init__(self, **attrs):
        super().__init__(**attrs)


class Line(base.Item):
    """Container that prints the child nodes on one line with a space in between.

    Not created from existing documents, but you can insert this node in a
    Document when you want some nodes to be on the same line, for example when
    you want to write a comment at the end of the preceding line instead of on
    a line of its own.

    """
    __slots__ = ()

    _before = _after = '\n'
    _between = ' '


class Document(base.Item):
    """A LilyPond source document."""
    __slots__ = ()

    _between = '\n\n'

    def concat(self, n, m):
        if isinstance(n, (SinglelineComment, Newline)):
            return '\n'
        return self.between


class Block(base.TailItem):
    """Base class for a block that wants newlines everywhere."""
    __slots__ = ()

    _before = _after = _after_head = _before_tail = '\n'
    head = '<fill in> {'
    tail = '}'


class Book(Block):
    r"""A \book { } block."""
    __slots__ = ()

    head = r"\book {"


class BookPart(Block):
    r"""A \bookpart { } block."""
    __slots__ = ()

    head = r"\bookpart {"


class Score(Block):
    r"""A \score { } block."""
    __slots__ = ()

    head = r"\score {"


class Header(Block):
    r"""A \header { } block."""
    __slots__ = ()

    head = r"\header {"


class Paper(Block):
    r"""A \paper { } block."""
    __slots__ = ()

    head = r"\paper {"


class Layout(Block):
    r"""A \layout { } block."""
    __slots__ = ()

    head = r"\layout {"


class Midi(Block):
    r"""A \midi { } block."""
    __slots__ = ()

    head = r"\midi {"


class With(Block):
    r"""A \with { } block."""
    __slots__ = ()

    head = r"\with {"
    _before = _after = " "


class LayoutContext(Block):
    r"""A \context { } block within \layout or \midi."""
    __slots__ = ()

    head = r"\context {"


class Pitch(base.VarHeadItem):
    """A pitch note name."""
    __slots__ = ()


class Mode(base.VarHeadItem):
    r"""The mode subcommand of the \key statement."""
    __slots__ = ()


class Key(base.HeadItem):
    r"""A \key statement.

    Must have a Pitch and a Mode child.

    """
    __slots__ = ()

    head = r"\key"


class Clef(base.HeadItem):
    r"""A \clef statement.

    Must have a Symbol or String child indicating the clef type.

    """
    __slots__ = ()

    head = r"\clef"


class String(base.VarHeadItem):
    r"""A quoted string."""
    __slots__ = ()

    def __init__(self, text, **attrs):
        super().__init__(text, **attrs)

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text[1:] if t.action is a.String.Escape else t.text
            for t in origin[1:-1])

    def write_head(self):
        return '"{}"'.format(re.sub(r'([\\"])', r'\\\1', self.head))


class Comment(base.VarHeadItem):
    r"""Base class for comment items."""
    __slots__ = ()

    def __init__(self, text, **attrs):
        super().__init__(text, **attrs)


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
    _after = '\n'

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write_head(self):
        return '%{}'.format(self.head)


class Markup(base.VarHeadItem):
    r"""A \markup, \markuplines or \markuplist expression."""
    __slots__ = ()
    _before = _after = _between = _after_head = " "


class MarkupWord(base.VarHeadItem):
    """A word in markup mode."""
    __slots__ = ()
    _before = _after = " "

    def __init__(self, text, **attrs):
        super().__init__(text, **attrs)


class MarkupList(base.TailItem):
    """A bracketed markup expression, like { ... }."""
    __slots__ = ()
    _after_head = _before_tail = _between = " "
    head = "{"
    tail = "}"


class MarkupCommand(base.VarHeadItem):
    r"""A markup command, like ``\bold <arg>``."""
    __slots__ = ()
    _before = _after = _between = " "


### Scheme

class SchemeSinglelineComment(Comment):
    r"""A singleline comment in Scheme after ``;``."""
    __slots__ = ()
    _after = '\n'

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write_head(self):
        return ';{}'.format(self.head)


class SchemeMultilineComment(Comment):
    r"""A multiline comment in Scheme after ``#!``."""
    __slots__ = ()

    @classmethod
    def read_head(cls, origin):
        end = -1 if origin[-1] == "#!" else None
        return ''.join(t.text for t in origin[1:end])

    def write_head(self):
        return '#!{}#!'.format(self.head)


class SchemeString(base.VarHeadItem):
    r"""A quoted string."""
    __slots__ = ()

    def __init__(self, text, **attrs):
        super().__init__(text, **attrs)

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text[1:] if t.action is a.String.Escape else t.text
            for t in origin[1:-1])

    def write_head(self):
        return '"{}"'.format(re.sub(r'([\\"])', r'\\\1', self.head))


class SchemeList(base.TailItem):
    r"""A Scheme pair or list ( ... )."""
    __slots__ = ()
    _between = " "
    head = "("
    tail = ")"


class SchemeVector(base.TailItem):
    r"""A Scheme vector #( ... )."""
    __slots__ = ()
    _between = " "
    head = "#("
    tail = ")"


class SchemeQuote(base.VarHeadItem):
    r"""A Scheme quote ``'``, ``\``` or ``,``."""
    __slots__ = ()


