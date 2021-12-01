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
Elements needed for Latex documents.

.. note::

   This module does not create DOM nodes for all Latex content.

   You can build a full Latex document from scratch using the available nodes,
   but parce supports much more syntax than makes sense to build DOM nodes for.

LilyPond music is always in a lily.Document nodes, and can occur in a braced
command or an environment.

"""

from . import base, element


class Document(base.Document):
    """A full LaTeX source document."""
    _space_between = ''


class Option(element.BlockElement):
    """An option block: ``[`` ... ``]``."""
    head = '['
    tail = ']'


class Brace(element.BlockElement):
    """A braced expression: ``{`` ... ``}``."""
    head = '{'
    tail = '}'


class Math(element.BlockElement):
    """Abstract Math block. Subclasses define the start/end delimiters."""


class MathInlineParen(Math):
    r"""Inline math ``\(...\)``."""
    head = r'\('
    tail = r'\)'


class MathInlineDollar(Math):
    r"""Inline math ``$...$``."""
    head = tail = r'$'


class MathDisplayBracket(Math):
    r"""Display math ``\[...\]``."""
    head = r'\['
    tail = r'\]'


class MathDisplayDollar(Math):
    r"""Display math ``$$...$$`` (discouraged)."""
    head = tail = '$$'


class Command(base.BackslashCommand):
    """A backslash-prefixed command.

    The backslash is not in the head value, but added on
    :meth:`~.element.Element.write`.

    Arguments may be appended as children.

    """


class Text(element.TextElement):
    """Common text."""


class Environment(element.Element):
    """A LaTeX environment.

    Starts with a :class:`Command` ``\\begin``, with zero or more
    :class:`Option` nodes, then an :class:`EnvironmentName`; then the contents,
    and finally an ``\\end`` :class:`Command` with and again an
    :meth:`EnvironmentName`.

    """
    _space_before = _space_after = '\n'

    @classmethod
    def with_name(cls, name, *children, **kwargs):
        """Convenience method to create an :class:`Environment`.

        Zero or more child nodes can be specified, and keyboard arguments
        are given to the constructor.

        """
        return cls(
            Command('begin', EnvironmentName(name), space_after='\n'),
            *children,
            Command('end', EnvironmentName(name), space_before='\n'), **kwargs)


class EnvironmentName(element.TextElement):
    """The name of an environment.

    The name is in the head value, the braces are added on :meth:`write`.

    """
    @classmethod
    def read_head(cls, origin):
        for t in origin:
            if t.text not in "{}":
                return t.text

    def write_head(self):
        return '{' + self.head + '}'


class Comment(base.SinglelineComment):
    r"""A singleline comment after ``%``."""
    _space_after = '\n'

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write_head(self):
        return '%{}'.format(self.head)


