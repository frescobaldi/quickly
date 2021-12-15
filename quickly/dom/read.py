# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Simple helper functions to easily build DOM elements reading from text.

By default the generated DOM nodes do not know their position in the
originating text, because the origin tokens are not preserved. This is the best
when building DOM snippets using this module and inserting them in existing
documents.

If you set the ``with_origin`` argument in the reader functions to True, the
origin tokens are preserved, so the DOM nodes know their position in the
originating text. Do not insert these nodes in a DOM document originating from
another text source if you want to edit that text via the DOM document later,
because the positions of the nodes can't be trusted then, and that may lead to
errors. (Of course this is no problem when you are writing a document from
scratch.)

"""


from parce.transform import Transformer

from ..lang import (
#    docbook,
    latex,
    lilypond,
    html,
    scheme,
#    texinfo,
)


# init two transformers, accessible by 0 (False) and 1 (True) :-)
_transformer = [Transformer(), Transformer()]
_transformer[0].transform_name_template = "{}AdHocTransform"


def htm_document(text, with_origin=False):
    """Return a :class:`.htm.Document` from the text.

    Example::

        >>> from quickly.dom import read
        >>> node = read.htm_document('<html><h1>Title</h1><p>Text...</p></html>')
        >>> node.dump()
        <htm.Document (1 child)>
         ╰╴<htm.Element (4 children)>
            ├╴<htm.OpenTag (1 child)>
            │  ╰╴<htm.TagName 'html'>
            ├╴<htm.Element (3 children)>
            │  ├╴<htm.OpenTag (1 child)>
            │  │  ╰╴<htm.TagName 'h1'>
            │  ├╴<htm.Text 'Title'>
            │  ╰╴<htm.CloseTag (1 child)>
            │     ╰╴<htm.TagName 'h1'>
            ├╴<htm.Element (3 children)>
            │  ├╴<htm.OpenTag (1 child)>
            │  │  ╰╴<htm.TagName 'p'>
            │  ├╴<htm.Text 'Text...'>
            │  ╰╴<htm.CloseTag (1 child)>
            │     ╰╴<htm.TagName 'p'>
            ╰╴<htm.CloseTag (1 child)>
               ╰╴<htm.TagName 'html'>
        >>> node.write()
        '<html><h1>Title</h1><p>Text...</p></html>'

    If you want the generated nodes to know the position in the original text,
    you should keep the origin tokens and set ``with_origin`` to True:

        >>> node = read.htm_document('<html><h1>Title</h1><p>Text...</p></html>', True)
        >>> node.dump()
        <htm.Document (1 child)>
         ╰╴<htm.Element (4 children)>
            ├╴<htm.OpenTag (1 child) [0:6]>
            │  ╰╴<htm.TagName 'html' [1:5]>
            ├╴<htm.Element (3 children)>
            │  ├╴<htm.OpenTag (1 child) [6:10]>
            │  │  ╰╴<htm.TagName 'h1' [7:9]>
            │  ├╴<htm.Text 'Title' [10:15]>
            │  ╰╴<htm.CloseTag (1 child) [15:20]>
            │     ╰╴<htm.TagName 'h1' [17:19]>
            ├╴<htm.Element (3 children)>
            │  ├╴<htm.OpenTag (1 child) [20:23]>
            │  │  ╰╴<htm.TagName 'p' [21:22]>
            │  ├╴<htm.Text 'Text...' [23:30]>
            │  ╰╴<htm.CloseTag (1 child) [30:34]>
            │     ╰╴<htm.TagName 'p' [32:33]>
            ╰╴<htm.CloseTag (1 child) [34:41]>
               ╰╴<htm.TagName 'html' [36:40]>

    """
    return _transformer[with_origin].transform_text(html.Html.root, text)


def htm(text, with_origin=False):
    """Return one element from the text, read in Html.root."""
    for node in htm_document(text, with_origin):
        return node


def lily_document(text, with_origin=False):
    """Return a :class:`.lily.Document` from the text.

    Example::

        >>> from quickly.dom import read
        >>> node = read.lily_document("music = { c d e f g }")
        >>> node.write()
        'music = { c d e f g }'
        >>> node.dump()
        <lily.Document (1 child)>        <lily.Document (1 child)>
         ╰╴<lily.Assignment music (3 children)>
            ├╴<lily.Identifier (1 child)>
            │  ╰╴<lily.Symbol 'music'>
            ├╴<lily.EqualSign>
            ╰╴<lily.MusicList (5 children)>
               ├╴<lily.Note 'c'>
               ├╴<lily.Note 'd'>
               ├╴<lily.Note 'e'>
               ├╴<lily.Note 'f'>
               ╰╴<lily.Note 'g'>

    This way you can get a DOM document from a full source text. This can also
    help you to create DOM element nodes that would otherwise be tedious to
    construct and type.

    """
    return _transformer[with_origin].transform_text(lilypond.LilyPond.root, text)


def lily(text, with_origin=False):
    """Return one element from the text, read in LilyPond.root.

    Examples::

        >>> from quickly.dom import read
        >>> read.lily("a")
        <lily.Note 'a'>

        >>> color = read.lily("#(x11-color 'DarkSlateBlue4)")
        >>> color.dump()
        <lily.Scheme '#' (1 child)>
         ╰╴<scm.List (2 children)>
            ├╴<scm.Identifier 'x11-color'>
            ╰╴<scm.Quote "'" (1 child)>
               ╰╴<scm.Identifier 'DarkSlateBlue4'>

        >>> read.lily("##f").dump()
        <lily.Scheme '#' (1 child)>
         ╰╴<scm.Bool False>

        >>> read.lily("1/2")
        <lily.Fraction 1/2>

        >>> read.lily("##xa/b").dump()
        <lily.Scheme '#' (1 child)>
         ╰╴<scm.Hex Fraction(10, 11)>

    This can help you to create DOM element nodes that would otherwise be
    tedious to construct and type.

    """
    for node in lily_document(text, with_origin):
        return node


def scm_document(text, with_origin=False):
    """Return a :class:`.scm.Document` from the text."""
    return _transformer[with_origin].transform_text(scheme.Scheme.root, text)


def scm(text, with_origin=False):
    """Return one element from the text, read in Scheme.root."""
    for node in scm_document(text, with_origin):
        return node


def tex_document(text, with_origin=False):
    """Return a :class:`.tex.Document` from the text."""
    return _transformer[with_origin].transform_text(latex.Latex.root, text)


def tex(text, with_origin=False):
    """Return one :mod:`.tex` node from the text."""
    for node in tex_document(text, with_origin):
        return node


