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
Some utility functions.
"""


def collapse_whitespace(whitespaces):
    r"""Return the "most important" whitespace of the specified strings.

    This is used to combine whitespace requirements. For example, newlines
    are preferred over single spaces, and a single space is preferred over
    an empty string. For example::

        >>> collapse_whitespace(['\n', ' '])
        '\n'
        >>> collapse_whitespace([' ', ''])
        ' '

    """
    return max(whitespaces, key=lambda s: (s.count('\n'), s.count(' ')), default='')


def combine_text(fragments):
    r"""Concatenate text fragments collapsing whitespace before and after the
    fragments.

    ``fragments`` is an iterable of (``before``, ``text``, ``after``) tuples,
    where ``before`` and ``after`` are whitespace. If a ``text`` is empty, the
    whitespace before and after are collapsed into the other surrounding
    whitespace. Returns a tree-tuple (``before``, ``text``, ``after``)
    containing the first ``before`` value, the combined ``text``, and the last
    ``after`` value.

    """
    result = []
    whitespace = []
    for before, text, after in fragments:
        whitespace.append(before)
        if text:
            result.append(collapse_whitespace(whitespace))
            result.append(text)
            whitespace.clear()
        whitespace.append(after)
    return ''.join(result[:1]), ''.join(result[1:]), collapse_whitespace(whitespace)


def transform(text, lexicon=None):
    """Transform the text.

    This function uses a :class:`~quickly.lang.lilypond.LilyPondAdHocTransform`
    transform object, and uses the LilyPond.root lexicon if no other lexicon
    is specified.

    """
    from parce.transform import Transformer
    from quickly.lang.lilypond import LilyPond, LilyPondAdHocTransform
    from quickly.lang.scheme import Scheme, SchemeAdHocTransform
    t = Transformer()
    t.add_transform(LilyPond, LilyPondAdHocTransform())
    t.add_transform(Scheme, SchemeAdHocTransform())
    return t.transform_text(lexicon or LilyPond.root, text)


def node(text, lexicon=None):
    """Build a Element node from text using lexicon (LilyPond.root if not
    specified).

    """
    from .lily import Document
    n = transform(text, lexicon)
    return n[0] if isinstance(n, Document) and len(n) else n


def document(text):
    """Build a Document from the specified text."""
    return transform(text)


