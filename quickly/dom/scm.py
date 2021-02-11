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
Elements needed for Scheme expressions.
"""

import fractions

import parce.action as a

from . import base, element


class LilyPond(element.BlockElement):
    """A LilyPond block inside Scheme, between ``#{`` and ``#}``."""
    head = "#{"
    tail = "#}"


class Document(base.Document):
    """A full Scheme document."""


class SinglelineComment(base.SinglelineComment):
    """A singleline comment in Scheme after ``;``."""
    _space_after = '\n'

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write_head(self):
        return ';{}'.format(self.head)


class MultilineComment(base.MultilineComment):
    """A multiline comment in Scheme after ``#!``."""
    @classmethod
    def read_head(cls, origin):
        end = -1 if origin[-1] == "#!" else None
        return ''.join(t.text for t in origin[1:end])

    def write_head(self):
        return '#!{}#!'.format(self.head)


class Char(element.TextElement):
    """A Scheme character."""
    @classmethod
    def read_head(cls, origin):
        return origin[0].text[2:]    # leave out the '#\' prefix

    def write_head(self):
        return r'#\{}'.format(self.head)


class String(base.String):
    """A quoted string."""


class Identifier(element.TextElement):
    """A Scheme identifier (keyword, variable, symbol)."""


class List(element.BlockElement):
    """A Scheme pair or list ( ... )."""
    _space_between = " "
    head = "("
    tail = ")"


class Vector(element.BlockElement):
    """A Scheme vector #( ... )."""
    _space_between = " "
    head = "#("
    tail = ")"


class Quote(element.TextElement):
    r"""A Scheme quote ``'``, ``\```, ``,`` or ``,@``."""


class Number(element.TextElement):
    """Base class for a numerical value.

    You can set and read the numerical value using the ``value`` attribute. The
    optional prefix can be ``#e`` or ``#i``, optionally followed by ``#d``.

    """
    def __init__(self, value, *children, prefix='', **attrs):
        super().__init__((value, prefix), *children, **attrs)

    def repr_head(self):
        """Show a better repr."""
        return self.write_head()

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

    def copy(self):
        """Reimplemented to handle the prefix on copying."""
        children = (n.copy() for n in self)
        spacing = getattr(self, '_spacing', {})
        return type(self)(self.value, *children, prefix=self.prefix, **spacing)


class Int(Number):
    """A Scheme decimal integer."""
    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t)

    def write_value(self):
        return format(self.value)


class Bin(Number):
    """A Scheme binary integer value."""
    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t[2:], 2)

    def write_value(self):
        return '#b{:b}'.format(self.value)


class Oct(Number):
    """A Scheme octal integer value."""
    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t[2:], 8)

    def write_value(self):
        return '#o{:o}'.format(self.value)


class Hex(Number):
    """A Scheme hexadecimal integer value."""
    @classmethod
    def read_value(cls, origin):
        t = origin[0].text
        return int(t[2:], 16)

    def write_value(self):
        return '#x{:x}'.format(self.value)


class Float(Number):
    """A Scheme floating point value."""
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


class Fraction(Number):
    """A Scheme fractional value."""
    @classmethod
    def read_value(cls, origin):
        s = "".join(t.text for t in origin)
        return fractions.Fraction(s)

    def write_value(self):
        return format(self.value)


class Bool(Number):
    """A Scheme boolean value."""
    @classmethod
    def read_value(cls, origin):
        return origin[0].text[1] in 'tT'

    def write_value(self):
        return '#t'if self.value else '#f'


class Dot(element.HeadElement):
    """A dot, e.g. in a Scheme pair."""
    head = '.'

