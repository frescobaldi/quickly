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
Elements needed for LilyPond expressions.
"""


from . import base, element


class Document(base.Document):
    """A full LilyPond source document."""


class Block(element.BlockElement):
    """Base class for a block, e.g. score, paper, etc.

    Newlines are placed by default between all child nodes. There are
    convenience methods to access variables inside a block.

    """
    _space_before = _space_after = _space_after_head = _space_before_tail = _space_between = '\n'
    head = '<fill in> {'
    tail = '}'

    def get_variable(self, name):
        """Convenience method to find the value of the named variable.

        Finds an Assignment child that assigns a value to a Identifier with the
        specified ``name``.  Returns the Element node representing the value,
        or None if no assignment with that name exists.

        """
        for n in self/Assignment:
            for v in n/Identifier:
                if v.get_name() == name:
                    return n[-1]

    def set_variable(self, name, node):
        """Convenience method to add or replace a variable assignment.

        If an Assignment exists with the named variable, replaces its node
        value; otherwise appends a new Assignment.

        """
        for n in self/Assignment:
            for v in n/Identifier:
                if v.get_name() == name:
                    n.replace(-1, node)
                    return
        self.append(Assignment.with_name(name, node))

    def variables(self):
        """Convenience method to return a list of the available variable names."""
        return list(v.get_name()
            for n in self/Assignment
                for v in n/Identifier)


class Book(Block):
    r"""A \book { } block."""
    head = r"\book {"


class BookPart(Block):
    r"""A \bookpart { } block."""
    head = r"\bookpart {"


class Score(Block):
    r"""A \score { } block."""
    head = r"\score {"


class Header(Block):
    r"""A \header { } block."""
    head = r"\header {"


class Paper(Block):
    r"""A \paper { } block."""
    head = r"\paper {"


class Layout(Block):
    r"""A \layout { } block."""
    head = r"\layout {"


class Midi(Block):
    r"""A \midi { } block."""
    head = r"\midi {"


class With(Block):
    r"""A \with { } block."""
    head = r"\with {"
    _space_before = _space_after = " "


class LayoutContext(Block):
    r"""A \context { } block within \layout or \midi."""
    head = r"\context {"


class EqualSign(element.HeadElement):
    r"""An equal sign (``=``)."""
    head = "="
    _space_before = _space_after = " "


class Separator(element.TextElement):
    """A separator."""


class Number(element.TextElement):
    """A number."""
    @classmethod
    def read_head(cls, origin):
        return int(origin[0].text)

    def write_head(self):
        return str(self.head)


class Unit(element.TextElement):
    r"""A unit, like ``\cm``, after a numerical value in a paper block."""


class Symbol(element.TextElement):
    """A symbol (unquoted text piece)."""


class Assignment(element.Element):
    """A variable = value construct.

    The first node is a Identifier element, then an EqualSign, and then the
    value.

    """
    _space_before = _space_after = '\n'

    @classmethod
    def with_name(cls, name, node):
        """Convenience class method to create a complete Assignment.

        Automatically creates a Identifier child node for the ``name``, an
        EqualSign node, and appends the specified ``node`` as the value of the
        assignment. For the ``name``, see :meth:`Identifier.set_name`.

        """
        return cls(Identifier.with_name(name), EqualSign(), node)


class Identifier(element.Element):
    """A variable name, the first node is always a Symbol or String.

    Further contains Symbol, String, Separator, Number or SchemeExpression.

    """
    @classmethod
    def with_name(cls, name):
        """Create a Identifier with specified name."""
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
        element, a string containing "illegal" characters into a
        :class:`String` element, and an integer value into a :class:`Number`
        element.

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


class Music:
    """Base mixin class for musical elements."""


class MusicList(Music, element.BlockElement):
    """Base class for a music list ``{`` ... ``}`` or ``<<`` ... ``>>``."""
    _space_after_head = _space_before_tail = _space_between = " "
    head = "{"
    tail = "}"


class SequentialMusic(MusicList):
    """Music between ``{`` ... ``}``."""


class SimultaneousMusic(MusicList):
    """Music between ``<<`` ... ``>>``."""
    head = "<<"
    tail = ">>"


class Chord(Music, element.BlockElement):
    """A chord ``<`` ... ``>``."""
    _space_between = " "
    head = "<"
    tail = ">"


class Pitch(element.TextElement):
    """A pitch note name."""


class Mode(element.TextElement):
    r"""The mode subcommand of the ``\key`` statement."""


class Key(element.HeadElement):
    r"""A \key statement.

    Must have a Pitch and a Mode child.

    """
    _space_after_head = _space_between = ' '

    head = r"\key"


class Clef(element.HeadElement):
    r"""A ``\clef`` statement.

    Must have a Symbol or String child indicating the clef type.

    """
    _space_after_head = " "
    head = r"\clef"


class String(base.String):
    r"""A quoted string."""


class MultilineComment(base.MultilineComment):
    r"""A multiline comment between ``%{`` and ``%}``."""
    @classmethod
    def read_head(cls, origin):
        end = -1 if origin[-1] == "%}" else None
        return ''.join(t.text for t in origin[1:end])

    def write_head(self):
        return '%{{{}%}}'.format(self.head)


class SinglelineComment(base.SinglelineComment):
    r"""A singleline comment after ``%``."""
    _space_after = '\n'

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write_head(self):
        return '%{}'.format(self.head)


class Markup(element.TextElement):
    r"""A ``\markup``, ``\markuplines`` or ``\markuplist`` expression."""
    _space_before = _space_after = _space_between = _space_after_head = " "


class MarkupWord(element.TextElement):
    """A word in markup mode."""
    _space_before = _space_after = " "


class MarkupList(element.BlockElement):
    """A bracketed markup expression, like ``{`` ... ``}``."""
    _space_after_head = _space_before_tail = _space_between = " "
    head = "{"
    tail = "}"


class MarkupCommand(element.TextElement):
    r"""A markup command, like ``\bold <arg>``."""
    _space_before = _space_after = _space_between = " "


class SchemeExpression(element.TextElement):
    """A Scheme expression in LilyPond."""

