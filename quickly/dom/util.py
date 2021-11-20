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


def add_newlines(node, text, block_separator='\n', max_blank_lines=10):
    """Set whitespace properties of all nodes according to the original text.

    Only nodes with an origin are affected. When a node appears on a new line,
    the ``space_before`` property is set; when the tail part of a node appears
    on a new line, the ``space_before_tail`` property is set.

    It is possible to set the ``block_separator`` (by default a single
    newline); and the maximum amount of consecutive blank lines, using
    ``max_blank_lines``.

    This can be useful before re-indenting or reformatting a document
    completely, to retain some aspects of the original formatting.

    """
    def next_block():
        nonlocal current_block
        if current_block < len(text):
            current_block = text.find(block_separator, current_block + 1)
            if current_block == -1:
                current_block = len(text)
            return True
        return False

    def get_newlines(pos):
        count = 0
        while pos > current_block:
            if not next_block():
                break
            count += 1
        count = max(count, max_blank_lines)
        return '\n' * count

    def handle_node(node):
        try:
            head_origin = node.head_origin
        except AttributeError:
            pass
        else:
            s = get_newlines(head_origin[0].pos)
            if s:
                node.space_before = s

        if len(node):
            for n in node:
                handle_node(n)

        try:
            tail_origin = node.tail_origin
        except AttributeError:
            pass
        else:
            s = get_newlines(tail_origin[0].pos)
            if s:
                node.space_before_tail = s

    current_block = -1
    next_block()
    handle_node(node)


