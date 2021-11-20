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
Functionality to pretty-print a DOM document, with good default indentation.

"""

from . import util


class _IndentLevel:
    """Holds the information for a new indent level."""
    def __init__(self, node):
        self.align_indices = tuple(node.indent_align_indices())
        self.align_positions = {}

    def align_child(self, child_index, pos):
        """Store a position value for the child at the specified index."""
        self.align_positions[child_index] = pos

    def get_align_pos(self):
        """Get a stored align value if the node supports it.

        Otherwise, None is returned.

        """
        for index in self.align_indices:
            try:
                return self.align_positions[index]
            except KeyError:
                pass


class Indenter:
    """Encapsulates the process of printing the indented output of a node.

    """
    def __init__(self, indent_width=2, start_indent=""):
        """Initialize ourselves.

        The default ``indent_width`` can be given (in nr of spaces), and the
        additional ``start_indent`` which is prepended to every output line,
        defaulting to the empty string.

        """
        self.indent_width = indent_width
        self.start_indent = start_indent

        # working variables
        self._result = []               # the list in which the result output is built up
        self._indent_stack = []         # the list of indenting history
        self._indenters = []            # the list of indenters created in the current line
        self._dedenters = 0             # the negative count of indent levels to end
        self._whitespace = []           # collects the minimal amount of whitespace between nodes
        self._can_dedent = False        # can the current line be dedented

    def write_indented(self, node):
        """Get the indented output of the node.

        Called by :meth:`Element.write_indented() <quickly.dom.element.Element.write_indented>`.

        """
        self._result[:] = [[0, []]]
        self._indent_stack.clear()
        self._indenters.clear()
        self._dedenters = 0
        self._whitespace.clear()
        self._can_dedent = False

        self.output_node(node)

        # strip preceding space
        while self._result:
            if self._result[0][1]:
                if self._result[0][1][0].isspace():
                    del self._result[0][1][0]
                else:
                    break
            else:
                del self._result[0]

        result = ''.join(
            "{}{}{}\n".format(self.start_indent, " " * indent, ''.join(line))
            for indent, line in self._result)
        return result

    def output_node(self, node, index=-1):
        """Output one node and its children.

        The index, if given, is the index of this node in its parent. This is
        used to get additional indenting hints for the node.

        """
        head = node.write_head()
        tail = node.write_tail()
        children = len(node) > 0
        indent = node.indent_children()

        self.add_whitespace(node.space_before)

        if head:
            self.output_head(head, index, node.indent_override())
            if tail or children:
                self.add_whitespace(node.space_after_head)

        if indent:
            self.enter_indent(node)

        if children:
            n = node[0]
            self.output_node(n, 0)
            for i, m in enumerate(node[1:], 1):
                self.add_whitespace(node.concat(n, m), m.space_before)
                self.output_node(m, i)
                n = m

        if indent:
            self.leave_indent()

        if tail:
            self.add_whitespace(node.space_before_tail)
            self.output_tail(tail)

        self.add_whitespace(node.space_after)

    def add_whitespace(self, *whitespace):
        """Adds whitespace, which is combined as soon as text is printed out."""
        self._whitespace.extend(whitespace)

    def enter_indent(self, node):
        """Enter a new indent level for the ``node``."""
        self._indenters.append(_IndentLevel(node))  # TODO get from node?

    def leave_indent(self):
        """Leave the younghest indent level."""
        if self._indenters:
            self._indenters.pop()
        else:
            self._dedenters -= 1

    def current_indent(self):
        """Get the current indent (not looking at ``self.start_indent``) in nr
        of spaces.

        """
        return self._indent_stack[-1] if self._indent_stack else 0

    def create_new_block(self):
        """Go to a new line."""
        if self._indenters:
            # add new indent levels
            current_indent = self.current_indent()
            for i in self._indenters:
                pos = i.get_align_pos()
                if pos is None:
                    indent = self.indent_width
                else:
                    indent = sum(map(len, self._result[-1][1][:pos]))
                current_indent += indent
                self._indent_stack.append(current_indent)
            self._indenters.clear()
        else:
            if self._dedenters:
                # remove some levels
                del self._indent_stack[self._dedenters:]
                self._dedenters = 0
            current_indent = self.current_indent()

        self._can_dedent = bool(self._indent_stack)
        self._result.append([current_indent, []])

    def output_space(self):
        """Output whitespace. Newlines start a new output line."""
        for c in util.collapse_whitespace(self._whitespace):
            if c == '\n':
                self.create_new_block()
            else:
                self._result[-1][1].append(c)
        self._whitespace.clear()

    def output_head(self, text, index=-1, override=None):
        """Output head text.

        The ``index``, if given, is the index of the node in its parent. This
        is used to get additional indenting hints for the node.

        If ``override`` is not None, and this head text happens to be the first
        on a new line, this value is used as the indent depth for this line,
        in stead of the current indent.

        """
        self.output_space()
        self._can_dedent = False
        last_line = self._result[-1][1]
        if not last_line and override is not None:
            self._result[-1][0] = override
        if self._indenters and index in self._indenters[-1].align_indices:
            # store the position of the node on the current output line
            position = len(last_line)
            self._indenters[-1].align_child(index, position)
        last_line.append(text)

    def output_tail(self, text):
        """Output the tail text."""
        self.output_space()
        if self._can_dedent and self._dedenters:
            del self._indent_stack[self._dedenters]
            self._dedenters = 0
            self._result[-1][0] = self.current_indent()
        self._result[-1][1].append(text)

