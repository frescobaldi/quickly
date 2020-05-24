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


class Pitch(base.ValueItem):
    """A pitch note name."""


class Mode(base.ValueItem):
    r"""The mode subcommand of the \key statement."""


class Key(base.Item):
    r"""A \key statement.

    Must have a Pitch and a Mode child.

    """
    value = r"\key"


class Clef(base.Item):
    r"""A \clef statement.

    Must have a Symbol or String child indicating the clef type.

    """
    value = r"\clef"


class String(base.ValueItem):
    r"""A quoted string."""
    @classmethod
    def read(cls, origin):
        return ''.join(t.text[1:] if t.action is a.String.Escape else t.text
            for t in origin[1:-1])

    def write(self):
        return '"{}"'.format(re.sub(r'([\\"])', r'\\\1', self.value))


class Comment(base.ValueItem):
    r"""Base class for comment items."""


class MultilineComment(Comment):
    r"""A multiline comment between %{ and %}."""
    @classmethod
    def read(cls, origin):
        end = -1 if origin[-1] == "%}" else None
        return ''.join(t.text for t in origin[1:end])

    def write(self):
        return '%{{{}%}}'.format(self.value)


class SinglelineComment(Comment):
    r"""A singleline comment after %."""
    @classmethod
    def read(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write(self):
        multiline, text = self.value
        return '%{}'.format(text)

