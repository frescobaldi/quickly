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

import fractions
import math
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


class LilyPond(base.TailItem):
    """A LilyPond block inside Schem, between #{ and #}."""
    __slots__ = ()

    head = "#{"
    tail = "#}"


class Block(base.TailItem):
    """Base class for a block that wants newlines everywhere."""
    __slots__ = ()

    _before = _after = _after_head = _before_tail = _between = '\n'
    head = '<fill in> {'
    tail = '}'

    def get_variable(self, name):
        """Convenience method to find the value of the named variable.

        Finds an Assignment child that assigns a value to a Variable with the
        specified ``name``.  Returns the Item node representing the value, or
        None if no assignment with that name exists.

        """
        for n in self/Assignment:
            for v in n/Variable:
                if v.get_name() == name:
                    return n[-1]

    def set_variable(self, name, node):
        """Convenience method to add or replace a variable assignment.

        If an Assignment exists with the named variable, replaces its node
        value; otherwise appends a new Assignment.

        """
        for n in self/Assignment:
            for v in n/Variable:
                if v.get_name() == name:
                    n.replace(-1, node)
                    return
        self.append(Assignment.with_name(name, node))

    def variables(self):
        """Convenience method to return a list of the available variable names."""
        def names():
            for n in self/Assignment:
                for v in n/Variable:
                    yield v.get_name()
        return list(names())


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


class EqualSign(base.HeadItem):
    r"""An equal sign (``=``)."""
    __slots__ = ()
    head = "="
    _before = _after = " "


class Separator(base.VarHeadItem):
    """A separator."""
    __slots__ = ()


class Number(base.VarHeadItem):
    """A number."""
    __slots__ = ()

    @classmethod
    def read_head(cls, origin):
        return int(origin[0].text)

    def write_head(self):
        return str(self.head)


class Unit(base.VarHeadItem):
    r"""A unit, like \cm, after a numerical value in a paper block."""
    __slots__ = ()


class Symbol(base.VarHeadItem):
    """A symbol (unquoted text piece)."""
    __slots__ = ()


class Assignment(base.Item):
    """A variable = value construct.

    The first node is a Variable item, then an EqualSign, and then the value.

    """
    __slots__ = ()

    @classmethod
    def with_name(cls, name, node):
        """Convenience class method to create a complete Assignment.

        Automatically creates a Variable child node for the ``name``, an
        EqualSign node, and appends the specified ``node`` as the value of the
        assignment. For the ``name``, see :meth:`Variable.set_name`.

        """
        return cls(Variable.with_name(name), EqualSign(), node)


class Variable(base.Item):
    """A variable name, the first node is always a Symbol or String.

    Further contains Symbol, String, Separator, Number or SchemeExpression.

    """
    __slots__ = ()

    @classmethod
    def with_name(cls, name):
        """Create a Variable with specified name."""
        v = cls()
        v.set_name(name)
        return v

    def get_name(self):
        """Convenience method to get the name of this variable.

        This can be a plain string or a tuple. It is a tuple when the variable
        name consists of multiple parts, separated by dots. The first item in
        the tuple is always a string, but the other items might also be
        numbers.

        """
        heads = tuple(n.head for n in self/(String, Symbol, Number))
        if len(heads) == 1:
            return heads[0]
        return heads

    def set_name(self, name):
        """Convenience method to set the name of this variable.

        In most cases the name is an alphanumeric identifier, but it can be any
        string (in that case it is automatically quoted) or a tuple of names,
        strings and even numbers. The first item in the tuple always must be a
        name or string. An alphanumeric string is turned into a :class:`Symbol`
        item, a string containing "illegal" characters into a :class:`String`
        item, and an integer value into a :class:`Number` item.

        """
        if type(name) is str:
            name = name,
        def nodes():
            for n in name:
                if type(n) is str:
                    yield (Symbol if n.isalpha() else String)(n)
                elif type(n) is int:
                    yield Number(n)
        self.clear()
        nodes = nodes()
        for n in nodes:
            self.append(n)
            for n in nodes:
                self.append(Separator('.'))
                self.append(n)


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

class SchemeDocument(base.Item):
    """A full Scheme document."""
    __slots__ = ()

    _between = '\n\n'

    def concat(self, n, m):
        if isinstance(n, (SinglelineComment, Newline)):
            return '\n'
        return self.between


class SchemeExpression(base.VarHeadItem):
    r"""A Scheme expression in LilyPond."""
    __slots__ = ()


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


class SchemeChar(base.VarHeadItem):
    r"""A Scheme character."""
    __slots__ = ()

    @classmethod
    def read_head(cls, origin):
        return origin[0].text[2:]    # leave out the '#\' prefix

    def write_head(self):
        return r'#\{}'.format(self.head)


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


class SchemeIdentifier(base.VarHeadItem):
    r"""A Scheme identifier (keyword, variable, symbol)."""
    __slots__ = ()


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


class SchemeNumber(base.VarHeadItem):
    r"""Base class from a numerical value.

    You can set and read the numerical value using the ``value`` attribute. The
    optional prefix can be ``#e`` or ``#i``, optionally followed by ``#d``.

    """
    __slots__ = ()

    def __init__(self, value, *children, prefix='', **attrs):
        super().__init__((value, prefix), *children, **attrs)

    def repr_head(self):
        """Show a better repr."""
        value, prefix = self.head
        return "{}, prefix='{}'".format(value, prefix) if prefix else format(value)

    @property
    def value(self):
        return self.head[0]

    @property
    def prefix(self):
        return self.head[1]

    @value.setter
    def value(self, value):
        self.head = (value, self.head[1])

    @prefix.setter
    def prefix(self, prefix):
        self.head = (self.head[0], prefix)

    @classmethod
    def read_prefix(self, origin):
        return ''.join(t.text for t in origin)

    @classmethod
    def read_value(self, origin):
        """Implement this method to read the value from the token."""
        raise NotImplementedError

    def write_head(self):
        """Reimplemented to add the prefix."""
        return ''.join((self.prefix, self.write_value()))

    def write_value(self):
        """Implement this method to write the value as a string."""
        raise NotImplementedError

    @classmethod
    def read_head(cls, head_origin):
        for i, t in enumerate(head_origin):
            if t.action != a.Number.Prefix:
                prefix = cls.read_prefix(head_origin[:i])
                value = cls.read_value(head_origin[i:])
                return prefix, value

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        prefix, value = cls.read_head(head_origin)
        return cls(value, *children, prefix=prefix, **attrs)


class SchemeInt(SchemeNumber):
    r"""A Scheme decimal integer."""
    __slots__ = ()

    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t)

    def write_value(self):
        return format(self.value)


class SchemeBinary(SchemeNumber):
    r"""A Scheme binary integer value."""
    __slots__ = ()

    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t[2:], 2)

    def write_value(self):
        return '#b{:b}'.format(self.value)


class SchemeOctal(SchemeNumber):
    r"""A Scheme octal integer value."""
    __slots__ = ()

    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t[2:], 8)

    def write_value(self):
        return '#o{:o}'.format(self.value)


class SchemeHexadecimal(SchemeNumber):
    r"""A Scheme hexadecimal integer value."""
    __slots__ = ()

    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t[2:], 16)

    def write_value(self):
        return '#x{:x}'.format(self.value)


class SchemeFloat(SchemeNumber):
    r"""A Scheme floating point value."""
    __slots__ = ()

    @classmethod
    def read_value(cls, origin):
        t = origin[0]
        if t.action is a.Number.Infinity:
            return float(t.text.split('.')[0])
        elif t.action is a.Number.NaN:
            return float("nan")
        else:
            return float(t.text)

    def write_value(self):
        text = format(self.value)
        if text == 'inf':
            return '+inf.0'
        elif text == '-inf':
            return '-inf.0'
        elif text == 'nan':
            return '+nan.0'
        else:
            return text


class SchemeFraction(SchemeNumber):
    r"""A Scheme fractional value."""
    __slots__ = ()

    @classmethod
    def read_value(cls, origin):
        s = "".join(t.text for t in origin)
        return fractions.Fraction(s)

    def write_value(self):
        return format(self.value)


class SchemeBoolean(SchemeNumber):
    r"""A Scheme boolean value."""
    __slots__ = ()

    @classmethod
    def read_value(cls, origin):
        return origin[0].text[1] in 'tT'

    def write_value(self):
        return '#t'if self.head else '#f'


class SchemeDot(base.VarHeadItem):
    r"""A dot, e.g. in a scheme pair."""
    __slots__ = ()


