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
Elements needed for Html text.

This module is called ``htm`` to keep its name short and to avoid confusion
with the language modules ``parce.lang.html`` and ``quickly.lang.html``.

"""

from . import base, element

class Text(element.TextElement):
    """Html/Xml text contents (Text or Whitespace)."""
    def write_head(self):
        return escape(self.head)


class Comment(base.MultilineComment):
    """A Html/Xml comment node."""


class EntityRef(element.TextElement):
    r"""An entity reference like ``&euml;``, ``&#123;`` or ``&#xed;``.

    The ``head`` value is the part between the ``&`` and the ``;``.

    """
    @classmethod
    def read_head(cls, origin):
        return origin[0].text[1:-1]  # strip & and ;

    def write_head(self):
        return "&{};".format(self.head)


class String(element.BlockElement):
    """Base class for strings."""
    def indent_children(self):
        return False


class SqString(String):
    """A single-quoted string.

    Inside are Text or EntityRef elements.

    """
    head = tail = "'"


class DqString(String):
    """A double-quoted string.

    Inside are Text or EntityRef elements.

    """
    head = tail = '"'




def escape(text):
    r"""Escape &, < and > to use text in HTML."""
    return text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")


def attrescape(text):
    r"""Escape &, <, > and ", to use text in HTML."""
    return escape(text).replace('"', "&quot;")


