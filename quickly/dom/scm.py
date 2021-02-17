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

Besides the elements a few functions are provided to make it easier to
manually construct scheme expressions. For example::

    >>> from quickly.dom.scm import q, qq, uq, i, p, s
    >>> s(True)
    <scm.Bool #t>
    >>> s(100)
    <scm.Number 100>
    >>> s(100.123)
    <scm.Number 100.123>
    >>> s(('text', -2)).dump()
    <scm.List (3 children)>
     ├╴<scm.String 'text'>
     ├╴<scm.Dot>
     ╰╴<scm.Number -2>
    >>> s(('text', -2)).write()
    '("text" . -2)'
    >>> q(s((i('text'), -2))).write()
    "'(text . -2)"
    >>> n = s([i('if'), [i('<'), i('a'), 100], "smaller", "larger"])
    >>> n.dump()
    <scm.List (4 children)>
     ├╴<scm.Identifier 'if'>
     ├╴<scm.List (3 children)>
     │  ├╴<scm.Identifier '<'>
     │  ├╴<scm.Identifier 'a'>
     │  ╰╴<scm.Number 100>
     ├╴<scm.String 'smaller'>
     ╰╴<scm.String 'larger'>
    >>> n.write()
    '(if (< a 100) "smaller" "larger")'

"""

import fractions
import math

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
    @classmethod
    def check_head(cls, head):
        return head in ("'", "`", ",", ",@")


class Number(element.TextElement):
    """A decimal numerical value, and the base class for Hex, Bin, Oct.

    All features of Scheme numerical values are supported: exact/inexactness,
    polar coordinates, complex numbers, fractions, infinity, nan and unknown
    digits (#).

    """
    radix = 10
    _prefix = {2: "#b", 8: "#o", 10: "", 16: "#x" }
    _fmt = {2: "b", 8: "o", 10: "d", 16: "x" }
    @classmethod
    def read_head(cls, origin):
        from parce.lang.scheme import scheme_number
        return scheme_number(origin)

    def write_head(self):
        v = self.head
        if v == math.inf:
            s = '+inf.0'
        elif v == -math.inf:
            s = '-inf.0'
        elif v is math.nan:
            s = '+nan.0'
        elif isinstance(v, fractions.Fraction):
            fmt = self._fmt[self.radix]
            f = lambda n: format(n, fmt)
            s = f(v.numerator)
            if v.denominator != 1:
                s = '{}/{}'.format(s, f(v.denominator))
        elif isinstance(v, float) and self.radix == 10:
            s = str(v)
        elif isinstance(v, complex):
            s = '{}{:+}i'.format(v.real, v.imag)
        else:
            s = format(int(v), self._fmt[self.radix])
        return self._prefix[self.radix] + s


class Bin(Number):
    """A Scheme binary integer value."""
    radix = 2


class Oct(Number):
    """A Scheme octal integer value."""
    radix = 8


class Hex(Number):
    """A Scheme hexadecimal integer value."""
    radix = 16


class Bool(Number):
    """A Scheme boolean value."""
    @classmethod
    def read_head(cls, origin):
        return origin[0].text[1] in 'tT'

    def write_head(self):
        return '#t' if self.head else '#f'


class NaN(Number):
    """Not a Number, created when a ``number`` context has invalid tokens."""
    @classmethod
    def read_head(cls, origin):
        return math.nan


class Dot(element.HeadElement):
    """A dot, e.g. in a Scheme pair."""
    head = '.'


def create_element_from_value(value):
    """Convert a regular Python value to a scheme Element node.

    Python bool, int, float or str values are converted into Bool, Number, or
    String objects respectively. A list is converted into a List element, and a
    tuple (of length > 1)  in a pair, with a dot inserted before the last node.
    Element objects are returned unchanged.

    A KeyError is raised when there is no conversion for the value's type.

    """
    if isinstance(value, element.Element):
        return value
    return _element_mapping[type(value)](value)


def q(arg):
    """Quote arg. Automatically converts arguments if needed."""
    return Quote("'", create_element_from_value(arg))


def qq(arg):
    """Quasi-quote arg. Automatically converts arguments if needed."""
    return Quote("`", create_element_from_value(arg))


def uq(arg):
    """Un-quote arg. Automatically converts arguments if needed."""
    return Quote(",", create_element_from_value(arg))


def i(arg):
    """Make an identifier of str arg."""
    return Identifier(arg)


def p(arg1, arg2, *args):
    """Return a pair (two-or-more element List with dot before last element)."""
    return create_element_from_value((arg1, arg2, *args))


def s(arg):
    """Same as :func:`create_element_from_value`."""
    return create_element_from_value(arg)


# used in the create_element_from_value function
_element_mapping = {
    bool: Bool,
    int: Number,
    float: Number,
    fractions.Fraction: Number,
    str: String,
    list: (lambda value: List(*map(s, value))),
    tuple: (lambda value: List(*map(s, value[:-1]), Dot(), *map(s, value[-1:]))),
}

