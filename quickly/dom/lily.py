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


import collections
import fractions
import re

from .. import duration, pitch
from . import base, element, scm


class _Variable:
    """A property that makes setting an Assignment easier.

    This can only be used for simple variable names. An underscore in the name
    is converted to a hyphen. Use this in classes that mix in
    lily.HandleAssignments::

        class Header(HandleAssignments):
            title = _Variable("The title of the document.")

    When setting a variable, only ``int`` and ``str`` are allowed, or an
    Element node of course. When getting a value, for an Int or String node the
    head value is returned, for other element types the node itself.

    """
    def __init__(self, docstring=None):
        self.__doc__ = docstring

    def __set_name__(self, owner, name):
        self.name = name.replace('_', '-')

    def __get__(self, instance, owner=None):
        if instance:
            return instance.get_variable(self.name)
        return self

    def __set__(self, instance, value):
        if value is None:
            instance.unset_variable(self.name)
        else:
            instance.set_variable(self.name, value)

    def __delete__(self, instance):
        instance.unset_variable(self.name)


class _ConvertUnpitchedToDuration:
    """Mixin class to convert Unpitched arguments to their Duration."""
    def add_argument(self, node):
        """Reimplemented to pick the Duration of an Unpitched node."""
        if isinstance(node, Unpitched):
            for node in node:
                node = node.copy_with_origin()
                break
        super().add_argument(node)


class _ConvertUnpitchedToInt:
    """Mixin class to convert Unpitched arguments to an Int."""
    def add_argument(self, node):
        """Reimplemented to read the Duration of an Unpitched node as a Int."""
        if isinstance(node, Unpitched):
            for dur in node / Duration:
                node = convert_duration_to_int(dur) or node
                break
        super().add_argument(node)


class HandleAssignments:
    __slots__ = ()

    """Mixin class to handle Assignment children in a convenient way."""
    def find_assignment(self, name):
        """Find the Assignment with the specified name."""
        for n in self/Assignment:
            for v in n/Identifier:
                if v.get_name() == name:
                    return n

    def get_variable(self, name):
        """Convenience method to find the value of the named variable.

        Finds an Assignment child that assigns a value to a Identifier with the
        specified ``name``.  Returns the Element node representing the value,
        or None if no assignment with that name exists.

        When the node is a String or an Int, its head value is returned.
        If no assignment with the name can be found, None is returned.

        For the ``name``, see :meth:`Identifier.set_name`.

        """
        assignment = self.find_assignment(name)
        if assignment:
            node = assignment[-1]
            value = create_value_from_element(node)
            if value is not None:
                return value
            return node

    def set_variable(self, name, value):
        """Convenience method to add or replace a variable assignment.

        If an Assignment exists with the named variable, replaces its node
        value; otherwise appends a new Assignment.

        If the value is an Element node, it is used directly. If it is an
        integer, an Int element is created; if it is a string, a String element
        is created. (If such element was already in use, only the head value
        is changed.)

        """
        node = create_element_from_value(value)
        assignment = self.find_assignment(name)
        if assignment:
            assignment.replace(-1, node)
        else:
            self.append(Assignment.with_name(name, node))

    def unset_variable(self, name):
        """Convenience method to delete a variable assignment.

        If an Assignment exists with the named variable, it is removed from its
        parent.

        """
        assignment = self.find_assignment(name)
        if assignment:
            self.remove(assignment)

    def variables(self):
        """Convenience method to return a list of the available variable names."""
        return list(v.get_name()
            for n in self/Assignment
                for v in n/Identifier)


class Document(HandleAssignments, base.Document):
    """A full LilyPond source document."""

    @property
    def version(self):
        """The LilyPond version number, as a tuple of ints."""
        for v in self//Version:
            for s in v/String:
                return tuple(map(int, re.findall(r'\d+', s.head)))

    @version.setter
    def version(self, version):
        """Set the version, as a tuple of ints."""
        version = '.'.join(map(str, version))
        for v in self//Version:
            for s in v/String:
                s.head = version
                break
            else:
                v.clear()
                v.append(String(version))
            return
        self.insert(0, Version(String(version)))


class Number(element.TextElement):
    """Base class for numeric values."""
    def write_head(self):
        return str(self.head)

    @classmethod
    def read_head(cls, origin):
        raise NotImplementedError


class Int(Number):
    """An integer number."""

    @classmethod
    def check_head(cls, head):
        return type(head) is int

    @classmethod
    def read_head(cls, origin):
        return int(origin[0].text)

    def signatures(self):
        yield Unit,


class Fraction(Number):
    """A fraction, like ``1/2``.

    The head value is a two-tuple of ints (numerator, denominator).

    """
    @classmethod
    def check_head(cls, head):
        return isinstance(head, tuple) and len(head) == 2 and \
            all(isinstance(v, int) for v in head)

    def repr_head(self):
        return self.write_head()

    @classmethod
    def read_head(cls, origin):
        return tuple(map(int, origin[0].text.split('/')))

    def write_head(self):
        return '/'.join(map(str, self.head))


class Float(Number):
    """A floating point number."""
    @classmethod
    def read_head(cls, origin):
        return float(origin[0].text)

    @classmethod
    def check_head(cls, head):
        return isinstance(head, (int, float))

    def signatures(self):
        yield Unit,


class Symbol(element.TextElement):
    """A symbol (unquoted text piece)."""


class String(base.String):
    r"""A quoted string."""


class Scheme(element.TextElement):
    """A Scheme expression in LilyPond.

    A Scheme expression can start with ``$``, ``#``, ``$@`` or ``#@``.
    The latter two are rarely used; they unroll a list in the surrounding
    expression.

    A Scheme expression starting with a dollar sign is directly executed by
    LilyPond when encountered in a source file, it is then ignored when it is
    no valid expression; an expression starting with a hash sign is evaluated
    later, when evalating the music expression.

    """
    _space_before = _space_after = " "

    @classmethod
    def check_head(cls, head):
        return head in ('$', '#', '$@', '#@')


class Music(element.Element):
    """A basic music element.

    This is also the base class for other elements that contain music.

    """


class Spanner(element.MappingElement):
    r"""Base class for spanner elements, that start or stop.

    Specify ``"start"`` or ``"stop"`` to the constructor, and put the texts
    that are displayed for either in the ``spanner_start`` and ``spanner_stop``
    attribute.

    """
    spanner_start = "<start>"
    spanner_stop = "<stop>"

    def __init_subclass__(cls, **kwargs):
        cls.mapping = {cls.spanner_start: "start", cls.spanner_stop: "stop"}
        super().__init_subclass__(**kwargs)


class Block(HandleAssignments, element.BlockElement):
    """Base class for a block, e.g. score, paper, etc.

    Newlines are placed by default between all child nodes. There are
    convenience methods to access variables inside a block.

    """
    _space_before = _space_after = _space_after_head = _space_before_tail = _space_between = '\n'
    head = '<fill in> {'
    tail = '}'


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
    r"""A \header { } block.

    The standard LilyPond header variables are accessible as attributes. When
    setting a value to a simple string, a String element is created
    automatically. When reading a value that is a single String element, the
    string contents is returned.

    For example::

        >>> from quickly.dom import lily
        >>> h = lily.Header()
        >>> h.title = "My title"
        >>> h.composer = "Wilbert Berendsen"
        >>> h.write()
        '\\header {\ntitle = "My title"\ncomposer = "Wilbert Berendsen"\n}'
        >>> h.dump()
        <lily.Header (2 children)>
         ├╴<lily.Assignment title (3 children)>
         │  ├╴<lily.Identifier (1 child)>
         │  │  ╰╴<lily.Symbol 'title'>
         │  ├╴<lily.EqualSign>
         │  ╰╴<lily.String 'My title'>
         ╰╴<lily.Assignment composer (3 children)>
            ├╴<lily.Identifier (1 child)>
            │  ╰╴<lily.Symbol 'composer'>
            ├╴<lily.EqualSign>
            ╰╴<lily.String 'Wilbert Berendsen'>

    Header variables can also be specified as keyword arguments on construction
    (just like any attribute)::

        >>> h = lily.Header(composer="Johann Sebastian Bach")

    When a variable is not present, None is returned. Other variable names can
    be set using :meth:`~HandleAssignments.set_variable` and read using
    :meth:`~HandleAssignments.get_variable`. The method
    :meth:`~HandleAssignments.variables` returns a list with the names of all
    assignments.

    Deleting a variable can be done in two ways::

        >>> h.title = None
        >>> del h.title         # same as setting to None

    """
    head = r"\header {"

    dedication = _Variable("The dedication.")
    title = _Variable("The title.")
    subtitle = _Variable("The subtitle.")
    subsubtitle = _Variable("The subsubtitle.")
    instrument = _Variable("The instrument (shown on all pages).")
    poet = _Variable("The poet.")
    composer = _Variable("The composer.")
    meter = _Variable("The meter (shown left).")
    arranger = _Variable("The arranger (shown right).")
    tagline = _Variable("The tagline (at the bottom of the last page).")
    copyright = _Variable("The copyright (at the bottom of the first page).")


class Paper(Block):
    r"""A \paper { } block.

    The most used paper variables can be set using properties, which
    auto-convert string, int and boolean values. Where LilyPond uses hyphens in
    paper variables, these properties use underscores.

    """
    head = r"\paper {"

    paper_height = _Variable("Paper height.")
    top_margin = _Variable("Top margin.")
    bottom_margin = _Variable("Bottom margin.")
    ragged_bottom = _Variable("Whether to have a ragged bottom (bool).")
    ragged_last_bottom = _Variable("Whether to have a ragged bottom on the last page (bool).")
    markup_system_spacing = _Variable("Spacing between markup and first system.")
    score_markup_spacing = _Variable("Spacing between score and markup.")
    score_system_spacing = _Variable("Spacing between two adjacent scores.")
    system_system_spacing = _Variable("Spacing between systems of one score.")
    markup_markup_spacing = _Variable("Spacing between two markups.")
    last_bottom_spacing = _Variable("Spacing between the last system or markup and the page bottom.")
    top_system_spacing = _Variable("Spacing between page top and first system.")
    top_markup_spacing = _Variable("Spacing between page top and first markup.")
    paper_width = _Variable("Paper width.")
    line_width = _Variable("Line witdh.")
    left_margin = _Variable("Left margin.")
    right_margin = _Variable("Right margin.")
    check_consistency = _Variable("Check whether all width settings fit.")
    ragged_right = _Variable("Whether to fill out the systems to the right (bool).")
    ragged_last = _Variable("Whether to fill out the last system to the right (bool).")
    two_sided = _Variable("Whether to have mirrored margins for left and right pages.")
    inner_margin = _Variable("Margin at binding side.")
    outer_margin = _Variable("Margin at outer side.")
    binding_offset = _Variable("Extra offset for inner-margin.")
    horizontal_shift = _Variable("Amount al systems and markups are shifted to the right.")
    indent = _Variable("Indent distance for the first system.")
    short_indent = _Variable("Indent distance for all other systems.")
    max_systems_per_page = _Variable("The maximum number of systems on a page.")
    min_systems_per_page = _Variable("The minimum number of systems on a page.")
    systems_per_page = _Variable("How many systems to put on a page.")
    system_count = _Variable("The number of systems to create.")
    page_breaking = _Variable("Page-breaking algorithm to use.")
    page_breaking_system_system_spacing = _Variable("Specially adjust spacing for page breaker.")
    page_count = _Variable("The number of pages to be used.")
    blank_page_penalty = _Variable("Penalty for having a blank page.")
    blank_last_page_penalty = _Variable("Penalty for ending on a left page.")
    blank_after_score_page_penalty = _Variable("Penalty for having a blank page before a score.")
    auto_first_page_number = _Variable("Automatically choose whether to start with even or odd page number.")
    first_page_number = _Variable("The page number for the first page.")
    print_first_page_number = _Variable("Print the page number on the first page (bool).")
    print_page_number = _Variable("Print page numbers anyway (bool).")
    page_spacing_weight = _Variable("Relative importance of page and line spacing.")
    print_all_headers = _Variable("Whether to print all headers in each score (bool).")
    system_separator_markup = _Variable("Markup to use between systems.")


class Layout(Block):
    r"""A \layout { } block.

    The most used layout variables can be set using properties, which
    auto-convert string, int and boolean values. Where LilyPond uses hyphens in
    paper variables, these properties use underscores.

    """
    head = r"\layout {"

    line_width = _Variable("Line witdh.")
    ragged_right = _Variable("Whether to fill out the systems to the right (bool).")
    ragged_last = _Variable("Whether to fill out the last system to the right (bool).")
    indent = _Variable("Indent distance for the first system.")
    short_indent = _Variable("Indent distance for all other systems.")
    system_count = _Variable("The number of systems to create.")


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


class List(element.Element):
    """A list consisting of String, Scheme, Int or Symbol elements.

    Separated by Separator elements; may also contain Comment nodes.

    """
    def get_list(self):
        """Convenience method to get a tuples with the contents of the list.

        Comment and Scheme nodes are ignored; for Symbol and String elements
        Python strings are returned, and for Int elements integer values.

        """
        return tuple(node.head for node in self / (Symbol, String, Int))

    def set_list(self, iterable):
        """Replaces the contents of this List with nodes converted
        from the iterable.

        Strings are converted to Symbol if possible, else String, and integers
        to Int nodes.

        """
        self.clear()
        nodes = make_list_nodes(iterable)
        for n in nodes:
            self.append(n)
            for n in nodes:
                self.append(Separator(',' if isinstance(n, Int) else '.'))
                self.append(n)


class Assignment(element.Element):
    """A variable = value construct.

    The first node is a Identifier element, then an EqualSign, and then the
    value.

    """
    _space_before = _space_after = '\n'

    @classmethod
    def with_name(cls, name, node):
        """Convenience constructor to create a complete Assignment.

        Automatically creates a Identifier child node for the ``name``, an
        EqualSign node, and appends the specified ``node`` as the value of the
        assignment. For the ``name``, see :meth:`Identifier.set_name`.

        """
        return cls(Identifier.with_name(name), EqualSign(), node)

    def repr_head(self):
        """If available, show the name of our first identifier."""
        for child in self / Identifier:
            return child.write()


class Identifier(List):
    """A variable name, the first node is always a Symbol or String.

    Further contains Symbol, String, Separator, Int or Scheme. This
    element is created when a List is encountered in an assignment by the
    transformer (see
    :meth:`~quickly.lang.lilypond.LilyPondTransform.handle_assignments`).

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
        heads = self.get_list()
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
        :class:`String` element, and an integer value into a :class:`Int`
        element.

        """
        if type(name) is str:
            name = name,
        self.set_list(name)


class IdentifierRef(element.TextElement):
    r"""A ``\variable`` name.

    The first symbol part is in the head of this element. Additional nodes can
    be Symbol, String, Separator, Int or Scheme.

    For the ``\"name"``, construct, head is the empty string, and the first
    child is a String. Otherwise, if there are child nodes, the first child is
    a Separator.

    For the constructor, the backslash is not needed::

        >>> from quickly.dom.lily import *
        >>> var = IdentifierRef('music')
        >>> var.write()
        '\\music'
        >>> var = IdentifierRef.with_name(('music', 1))
        >>> var.write()
        '\\music.1'

    """
    @classmethod
    def read_head(cls, origin):
        return origin[0].text.lstrip('\\')

    def write_head(self):
        return '\\' + self.head

    @classmethod
    def with_name(cls, name):
        """Convenience method to create a IdentifierRef with specified name.

        This is especially useful with complicated names that are not a
        simple symbol.

        """
        v = cls()
        v.set_name(name)
        return v

    def get_name(self):
        """Convenience method to get the name of this variable.

        The backslash is not returned. The name can be a plain string or a
        tuple. It is a tuple when the variable name consists of multiple parts,
        separated by dots. The first item in the tuple is always a string, but
        the other items might also be numbers.

        """
        names = []
        if self.head:
            names.append(self.head)
        for n in self / (Symbol, String, Int):
            names.append(n.head)
        if len(names) == 1:
            return names[0]
        return tuple(names)

    def set_name(self, name):
        """Convenience method to set the name of this variable.

        In most cases the name is an alphanumeric identifier, but it can be any
        string (in that case it is automatically quoted) or a tuple of names,
        strings and even numbers. The first item in the tuple always must be a
        name or string. An alphanumeric string is turned into a :class:`Symbol`
        element, a string containing "illegal" characters into a
        :class:`String` element, and an integer value into a :class:`Int`
        element.

        A backslash need not to be prepended.

        """
        if type(name) is str:
            name = name,
        nodes = make_list_nodes(name)
        self.clear()
        for n in nodes:
            if isinstance(n, Symbol):
                self.head = n.head
            else:
                self.head = ''
                self.append(n)
            for n in nodes:
                self.append(Separator('.'))
                self.append(n)


class MusicFunction(element.TextElement, Music):
    r"""A generic music function with a backslash, like ``\stemUp``

    To be used is there is no special Element type for the music function.
    When manually constructing this element, the initial backslash need not
    to be given. Example::

        >>> from quickly.dom.lily import MusicFunction
        >>> MusicFunction('stemUp').write()
        '\\stemUp'

    """
    _space_between = _space_after_head = " "

    @classmethod
    def read_head(cls, origin):
        return origin[0].text[1:]

    def write_head(self):
        return '\\' + self.head


class Context(element.HeadElement, Music):
    r"""``\context ...``."""
    _space_between = _space_after_head = " "
    head = r'\context'

    def signatures(self):
        yield Symbol, MUSIC
        yield Symbol, With, MUSIC
        yield Symbol, EqualSign, (String, Symbol), MUSIC
        yield Symbol, EqualSign, (String, Symbol), With, MUSIC


class New(Context):
    r"""``\new ...``."""
    head = r'\new'


class Change(element.HeadElement, Music):
    r"""``\change ...``."""
    _space_between = _space_after_head = " "
    head = r'\change'

    def signatures(self):
        yield Symbol, EqualSign, (String, Symbol)


class AddQuote(element.HeadElement):
    r"""An ``\addQuote`` command, at toplevel."""
    _space_between = _space_after_head = " "
    head = r'\addQuote'

    def signatures(self):
        yield (Identifier, String, Symbol), MUSIC


class QuoteDuring(element.HeadElement, Music):
    r"""A ``\quoteDuring`` command."""
    _space_between = _space_after_head = " "
    head = r'\quoteDuring'

    def signatures(self):
        yield (List, String, Symbol), MUSIC


class ApplyContext(element.HeadElement):
    r"""The ``\applyContext`` command."""
    _space_between = _space_after_head = " "
    head = r'\applyContext'

    def signatures(self):
        yield Scheme,


class ApplyMusic(element.HeadElement):
    r"""The ``\applyMusic`` function."""
    _space_between = _space_after_head = " "
    head = r'\applyMusic'

    def signatures(self):
        yield Scheme, MUSIC


class ApplyOutput(element.HeadElement):
    r"""The ``\applyOutput`` command."""
    _space_between = _space_after_head = " "
    head = r'\applyOutput'

    def signatures(self):
        yield SYMBOL, Scheme


class Relative(element.HeadElement, Music):
    """Relative music."""
    head = r'\relative'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield Note, MUSIC
        yield MUSIC,


class Absolute(element.HeadElement, Music):
    """Absolute music."""
    head = r'\absolute'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield MUSIC,


class Fixed(element.HeadElement, Music):
    """Fixed music."""
    head = r'\fixed'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield Note, MUSIC


class Transpose(element.HeadElement, Music):
    """Transposed music."""
    head = r'\transpose'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield Note, Note, MUSIC


class Repeat(element.HeadElement, Music):
    """Repeated music."""
    head = r'\repeat'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield Symbol, Int, MUSIC
        yield Symbol, Int, MUSIC, Alternative


class Alternative(element.HeadElement, Music):
    """Alternative music for repeats."""
    head = r'\alternative'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield MusicList,


class UnfoldRepeats(element.HeadElement, Music):
    r"""The ``\unfoldRepeats`` command."""
    _space_between = _space_after_head = " "
    head = r'\unfoldRepeats'

    def signatures(self):
        yield MUSIC,


class Transposition(element.HeadElement, Music):
    r"""A ``\tranposition`` command."""
    head = r'\transposition'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield Note,


class Ottava(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""An ``\ottava`` command."""
    _space_between = _space_after_head = " "
    head = r'\ottava'

    def signatures(self):
        yield NUMBER,


class MusicList(element.BlockElement, Music):
    """A list of music items between ``{`` ... ``}``."""
    _space_after_head = _space_before_tail = _space_between = " "
    head = "{"
    tail = "}"


class SimultaneousMusicList(MusicList):
    """A list of music items between ``<<`` ... ``>>``."""
    head = "<<"
    tail = ">>"


class Sequential(element.HeadElement, Music):
    r"""Music after ``\sequential``."""
    head = r'\sequential'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield MUSIC,


class Simultaneous(element.HeadElement, Music):
    r"""Music after ``\simultaneous``."""
    head = r'\simultaneous'
    _space_between = _space_after_head = " "

    def signatures(self):
        yield MUSIC,


class LyricMode(element.TextElement, Music):
    r"""``\lyricmode``, ``\lyrics`` or ``\lyricsto``."""

    def signatures(self):
        if self.head == r'\lyricsto':
            yield (String, Symbol), MUSIC
        else:
            yield MUSIC,


class ChordMode(element.TextElement, Music):
    r"""``\chordmode`` or ``\chords``."""

    def signatures(self):
        yield MUSIC,


class DrumMode(element.TextElement, Music):
    r"""``\drummode`` or ``\drums``."""

    def signatures(self):
        yield MUSIC,


class NoteMode(element.HeadElement, Music):
    r"""``\notemode``."""
    head = r'\notemode'

    def signatures(self):
        yield MUSIC,


class FigureMode(element.TextElement, Music):
    r"""``\figuremode`` or ``\figures``."""

    def signatures(self):
        yield MUSIC,


class Chord(element.BlockElement, Music):
    """A chord ``<`` ... ``>``."""
    _space_between = " "
    head = "<"
    tail = ">"


class Note(element.TextElement, Music):
    """A pitch note name."""


class Unpitched(Music):
    """An unpitched note, always has a Duration child."""


class Rest(element.TextElement, Music):
    r"""A rest (``r`` or ``R``).

    The Rest element has normally a ``r`` or ``R`` value. In the latter case
    it is a multi measure rest.

    But the head value can also be a pitch name, and there can be an Octave or
    OctCheck child in this case; this means that is is a positioned rest (e.g.
    ``c\rest``).

    """


class Space(element.HeadElement, Music):
    """A space (``s``)."""
    head = "s"


class Skip(element.HeadElement, Music):
    r"""A ``\skip``. Must have a Duration child."""
    head = r'\skip'


class Q(element.HeadElement, Music):
    """A ``q``, repeating the previous chord."""
    head = 'q'


class Drum(element.TextElement, Music):
    """A drum note."""


class RestModifier(element.HeadElement):
    r"""A ``\rest`` command after a note.

    Is a child of a Rest element that has a pitch name and possibly
    octave information instead of plain "r".

    """
    head = r'\rest'


class Accidental(element.MappingElement):
    """The accidental after a note.

    Can be ``cautionary`` or ``forced``.

    """
    mapping = {
        '?': 'cautionary',
        '!': 'forced',
    }


class Octave(element.TextElement):
    """The octave after a note.

    The default octave is 0; each ``'`` increases the octave by one; each ``,``
    decreases the octave by one. Note that this differs from LilyPond, which
    uses 0 to denote the ``'`` octave.

    """
    @classmethod
    def read_head(cls, origin):
        """Read the octave from the token."""
        return pitch.octave_to_num(origin[0].text)

    def write_head(self):
        """Write the octave, an empty string for octave 0."""
        return pitch.num_to_octave(self.head)


class OctCheck(element.TextElement):
    """The octavecheck after a note, e.g. like ``=,``.

    The default octave is 0; each ``'`` increases the octave by one;
    each ``,`` decreases the octave by one. Note that differs from LilyPond,
    which uses 0 to denote the ``'`` octave.

    """
    @classmethod
    def read_head(cls, origin):
        """Read the octave from the token."""
        return pitch.octave_to_num(origin[0].text[1:])

    def write_head(self):
        """Write the octave, an empty string for octave 0."""
        return '=' + pitch.num_to_octave(self.head)


class OctaveCheck(element.HeadElement):
    r"""The ``\octaveCheck`` command."""
    _space_after_head = _space_between = " "
    head = r'\octaveCheck'

    def signatures(self):
        yield Note,


class Duration(element.TextElement):
    """A duration after a note.

    To the constructor the duration is specified using a numerical value, which
    can be a Fraction. A whole note is 1, a breve 2, etc; a quarter note or
    crotchet 1/4, etc.

    The value must be expressable (is that English?:-) in a length value
    and zero or more dots. Examples::

        >>> from quickly.dom.lily import Duration
        >>> Duration(2).write()
        '\\breve'
        >>> Duration(3/2).write()
        '1.'
        >>> Duration(7/4).write()
        '1..'
        >>> Duration(7/16).write()
        '4..'

    """
    def duration(self):
        """Return our duration value, including scaling if a DurationScaling
        child is present. """
        duration = self.head
        for e in self / DurationScaling:
            duration *= e.head
        return duration

    @classmethod
    def read_head(cls, origin):
        """Read the duration value from the origin tokens."""
        dur, *dots = origin
        return duration.to_fraction(dur.text, len(dots))

    def write_head(self):
        """Write back the duration fraction to a string like ``4.``"""
        return duration.to_string(self.head)


class DurationScaling(element.TextElement):
    """An optional scaling after a Duration.

    E.g. ``*1/2``. May be read from multiple ``*n/m`` parts, but always outputs
    a single ``*n/d`` value, or ``*n`` when the denominator is 1. To the
    constructor any numerical value may be given, but the value is always
    represented as a fraction (omitting the denominator if 1).

    """
    @classmethod
    def read_head(cls, origin):
        """Read the scaling from the origin tokens."""
        scaling = 1
        for t in origin:
            if t != "*":
                scaling *= fractions.Fraction(t.text)
        return scaling

    def write_head(self):
        """Write back the scaling to a string like ``*1/2``."""
        if self.head != 1:
            return "*{}".format(fractions.Fraction(self.head))
        return ""


class LyricText(element.TextElement, Music):
    r"""A word in lyric mode."""


class LyricExtender(element.HeadElement):
    r"""A lyric extender ``__``."""
    head = "__"


class LyricHyphen(element.HeadElement):
    r"""A lyric hyphen ``--``."""
    head = "--"


class LyricSkip(element.HeadElement, Music):
    r"""A lyric skip ``_``."""
    head = "_"


class ChordModifiers(element.Element):
    r"""A list of elements attachted to a note in chord mode."""


class AddSteps(element.HeadElement):
    r"""Contains the steps to be added in chordmode."""
    head = ":"


class RemoveSteps(element.HeadElement):
    r"""Contains the steps to be added in chordmode."""
    head = "^"


class Qualifier(element.TextElement):
    """A qualifier like ``maj`` in chord mode."""


class Inversion(element.HeadElement):
    r"""Inversion (``/``) in chordmode."""
    head = '/'


class AddInversion(element.HeadElement):
    r"""Inversion  adding the bass note (``/+``) in chordmode."""
    head = '/+'


class Step(Int):
    r"""Contains the steps to be added in chordmode."""


class Alteration(element.TextElement):
    r"""The alteration of a step (``+`` or ``-``)."""


class Articulations(element.Element):
    r"""A list of elements that are attached to a note or chord."""


class Direction(element.MappingElement):
    r"""A ``-``, ``_`` or ``^``.

    The value is -1 for ``_``, 0 for ``-`` or 1 for ``^``

    """
    mapping = {
        '_': -1,
        '-': 0,
        '^': 1,
    }


class Articulation(element.TextElement):
    r"""An ArticulationEvent."""


class Modifier(element.TextElement):
    r"""A generic modifier that is not an articulation but added to
    the Articulations after a note.

    For example ``\noBeam``.

    """


class Fingering(element.TextElement):
    r"""A FingeringEvent."""


class Dynamic(element.TextElement):
    r"""A dynamic symbol, like ``pp``."""
    @classmethod
    def read_head(cls, origin):
        return origin[0].text[1:]    # remove the backslash

    def write_head(self):
        return r'\{}'.format(self.head)


class Slur(Spanner):
    r"""A slur ``(`` or ``)``."""
    spanner_start = "("
    spanner_stop = ")"


class PhrasingSlur(Spanner):
    r"""A phrasing slur ``\(`` or ``\)``."""
    spanner_start = r"\("
    spanner_stop = r"\)"


class Tie(element.HeadElement):
    r"""A tie."""
    head = '~'


class LaissezVibrer(Tie):
    r"""A ``\laissezVibrer`` tie."""
    head = '\\laissezVibrer'


class RepeatTie(Tie):
    r"""A ``\repeatTie`` tie."""
    head = '\\repeatTie'


class Beam(Spanner):
    r"""A beam ``[`` or ``]``."""
    spanner_start = "["
    spanner_stop = "]"


class Ligature(Spanner):
    r"""A ligature ``\[`` or ``\]``."""
    spanner_start = r"\["
    spanner_stop = r"\]"


class TextSpanner(Spanner):
    r"""A text spanner."""
    spanner_start = r'\startTextSpan'
    spanner_stop = r'\stopTextSpan'


class TrillSpanner(Spanner):
    r"""A trill spanner."""
    spanner_start = r'\startTrillSpan'
    spanner_stop = r'\stopTrillSpan'


class Melisma(Spanner):
    r"""A melisma spanner."""
    spanner_start = r'\melisma'
    spanner_stop = r'\melismaEnd'


class Arpeggio(element.HeadElement, Music):
    r"""An ``\arpeggio``."""
    head = r'\arpeggio'


class Glissando(element.HeadElement, Music):
    r"""A ``\glissando``."""
    head = r'\glissando'


class Bar(element.HeadElement, Music):
    r"""A ``\bar``. Has a String child."""
    head = r'\bar'

    def signatures(self):
        yield String,


class Breathe(element.HeadElement, Music):
    r"""A ``\breathe``."""
    head = r'\breathe'


class Break(element.ToggleElement):
    r"""A ``\break`` or ``\noBreak``. """
    toggle_on = r'\break'
    toggle_off = r'\noBreak'


class PageBreak(element.ToggleElement):
    r"""A ``\pageBreak`` or ``\noPageBreak``."""
    toggle_on = r'\pageBreak'
    toggle_off = r'\noPageBreak'


class PageTurn(element.MappingElement):
    r"""A ``\pageTurn``, ``\allowPageTurn`` or ``\noPageTurn``."""
    mapping = {
        r'\pageTurn':   '',
        r'\noPageTurn': 'no',
        r'\allowPageTurn': 'allow',
    }


class PipeSymbol(element.HeadElement):
    r"""A PipeSymbol, most times used as bar check."""
    head = "|"


class VoiceSeparator(element.HeadElement):
    r"""A voice separator."""
    head = r"\\"


class Label(element.HeadElement, Music):
    r"""A ``\label`` command. Has one scheme expression child."""
    head = r'\label'

    def signatures(self):
        yield Scheme,


class Mark(element.HeadElement, Music):
    r"""A ``\mark`` command. Has one child."""
    head = r'\mark'

    def signatures(self):
        yield Default,
        yield VALUE,


class Default(element.HeadElement):
    r"""The ``\default`` mark argument."""
    head = r'\default'


class Tempo(_ConvertUnpitchedToDuration, element.HeadElement, Music):
    r"""A ``\tempo`` command.

    Can have text (symbol, string, markup) child and/or duration, EqualSign and
    numeric value childs.

    """
    _space_after_head = _space_between = " "
    head = r"\tempo"

    def signatures(self):
        yield TEXT,
        yield TEXT, Unpitched, EqualSign, Int
        yield Unpitched, EqualSign, Int


class SpannerId(element.HeadElement):
    r"""A spanner id (``\=``).

    The first child is the id (Int, Symbol, String or Scheme). The second
    child the attached slur, phrasing slur or other object. (LilyPond only
    supports slurs).

    """
    head = r"\="


class PesOrFlexa(element.HeadElement):
    r"""A pes-or-flexa event (``\~``)."""
    head = r"\~"


class Tweak(element.HeadElement):
    r"""A ``\tweak`` command.

    On the music level, this node has two children, a Symbol and an argument.
    As an event after a note, this node has three children, the symbol,
    the argument and the object to tweak.

    """
    _space_after_head = _space_between = _space_after = " "
    head = r'\tweak'


class Tremolo(element.HeadElement):
    r"""A Tremolo (``:``) with an optional Duration child."""
    head = ":"


class Mode(element.TextElement):
    r"""The mode subcommand of the ``\key`` statement."""


class Key(element.HeadElement, Music):
    r"""A \key statement.

    Must have a Pitch and a Mode child.

    """
    _space_after_head = _space_between = ' '
    head = r"\key"

    def signatures(self):
        yield Note, Mode


class Clef(element.HeadElement, Music):
    r"""A ``\clef`` statement.

    Must have a Symbol or String child indicating the clef type.

    """
    _space_after_head = " "
    head = r"\clef"

    def signatures(self):
        yield (Symbol, String),


class Time(element.HeadElement, Music):
    r"""A ``\time`` statement.

    Has an optional List child and a Fraction child.

    """
    _space_after_head = " "
    head = r"\time"

    def signatures(self):
        yield List, Fraction
        yield Fraction,


class Times(element.HeadElement, Music):
    r"""A ``\times`` statement.

    Has a Fraction child and a Music child.
    The ``\times`` command is not documented anymore in LilyPond, but also
    not deprecated. Using ``\tuplet`` is recommended.

    """
    _space_after_head = _space_between = " "
    head = r"\times"

    def signatures(self):
        yield Fraction, MUSIC


class Tuplet(_ConvertUnpitchedToDuration, element.HeadElement, Music):
    r"""A ``\tuplet`` statement.

    Has a Fraction child, an optional Duration child and a Music child.

    """
    _space_after_head = _space_between = " "
    head = r"\tuplet"

    def signatures(self):
        yield Fraction, Duration, MUSIC
        yield Fraction, Unpitched, MUSIC
        yield Fraction, MUSIC


class ScaleDurations(element.HeadElement, Music):
    r"""A ``\scaleDurations`` command.

    Has a Fraction child and a Music child.

    """
    _space_after_head = _space_between = " "
    head = r"\scaleDurations"

    def signatures(self):
        yield Fraction, MUSIC


class ShiftDurations(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""A ``\shiftDurations`` command.

    Has two Scheme children and a Music child.

    """
    _space_after_head = _space_between = " "
    head = r"\shiftDurations"

    def signatures(self):
        yield NUMBER, NUMBER, MUSIC


class Grace(element.HeadElement, Music):
    r"""A ``\grace`` command.

    Has a Music child.

    """
    _space_after_head = " "
    head = r"\grace"

    def signatures(self):
        yield MUSIC,


class Acciaccatura(element.HeadElement, Music):
    r"""An ``\acciaccatura`` command.

    Has two Music children.

    """
    _space_after_head = " "
    head = r"\acciaccatura"

    def signatures(self):
        yield MUSIC, MUSIC


class Appoggiatura(element.HeadElement, Music):
    r"""An ``\appoggiatura`` command.

    Has two Music children.

    """
    _space_after_head = " "
    head = r"\appoggiatura"

    def signatures(self):
        yield MUSIC, MUSIC


class SlashedGrace(element.HeadElement, Music):
    r"""A ``\slashedGrace`` command.

    Has two Music children.

    """
    _space_after_head = " "
    head = r"\slashedGrace"

    def signatures(self):
        yield MUSIC, MUSIC


class AfterGrace(element.HeadElement, Music):
    r"""An ``\afterGrace`` command.

    Has an optional Fraction and two Music children.

    """
    _space_after_head = " "
    head = r"\afterGrace"

    def signatures(self):
        yield Fraction, MUSIC, MUSIC
        yield MUSIC, MUSIC


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
    _space_before = ""
    _space_after = " "
    _space_between = _space_after_head = " "


class MarkupWord(element.TextElement):
    """A word in markup mode."""
    _space_before = _space_after = " "


class MarkupList(element.BlockElement):
    """A bracketed markup expression, like ``{`` ... ``}``."""
    _space_after_head = _space_before_tail = _space_between = " "
    head = "{"
    tail = "}"


class MarkupCommand(element.TextElement):
    r"""A markup command, like ``\bold <arg>``.

    When manually constructing a MarkupCommand, the backslash is not needed.

    """
    _space_after_head = _space_before_tail = _space_between = " "

    @classmethod
    def read_head(cls, origin):
        return origin[0].text.lstrip('\\')

    def write_head(self):
        return '\\' + self.head


class MarkupScore(Score):
    r"""A ``\score`` in Markup."""
    _space_after_head = _space_before_tail = _space_between = " "


class MarkupScoreLines(MarkupScore):
    r"""A ``\score-lines`` in Markup."""
    head = r"\score-lines {"


class Figure(element.BlockElement):
    r"""One ``<`` ... ``>`` figure "chord" in figuremode."""
    _space_between = " "
    head = '<'
    tail = '>'


class FigureBracket(element.BlockElement):
    r"""One ``[`` ... ``]`` bracketed set of figures in figuremode."""
    _space_between = " "
    head = '['
    tail = ']'


class FigureStep(Int):
    """A step number in figure mode."""


class FigureSkip(element.HeadElement):
    r"""The invisible figure step ``_``."""
    head = '_'


class FigureAccidental(element.MappingElement):
    r"""An accidental in figure mode.

    One of: -1, -0.5, 0, 0.5, 1, corresponding to:
     ``'--'``, ``'-'``, ``''``, ``'+'`` or ``'++'``.

    """
    mapping = {
        '--':  -1,
        '-':   -0.5,
        '':     0,
        '+':    0.5,
        '++':   1,
    }


class FigureAlteration(element.MappingElement):
    r"""An alteration in figure mode.

    One of: "augmented", "diminished", "raised" or "end-of-line", corresponding
    to: `\+`, `/`, `\\` or `\!`.

    """
    mapping = {
        r'\+':  "augmented",
        r'/':   "diminished",
        r'\\':  "raised",
        r'\!':  "end-of-line",
    }


class Tag(element.HeadElement):
    r"""A ``\tag`` command."""
    head = r'\tag'

    def signatures(self):
        yield (Symbol, String, Scheme), MUSIC


class KeepWithTag(element.HeadElement):
    r"""A ``\keepWithTag`` command."""
    head = r'\keepWithTag'

    def signatures(self):
        yield (Symbol, String, Scheme), MUSIC


class RemoveWithTag(element.HeadElement):
    r"""A ``\removeWithTag`` command."""
    head = r'\removeWithTag'

    def signatures(self):
        yield (Symbol, String, Scheme), MUSIC


class TagGroup(element.HeadElement):
    r"""A ``\tagGroup`` command."""
    head = r'\tagGroup'

    def signatures(self):
        yield (Symbol, String, Scheme),


class PushToTag(element.HeadElement):
    r"""A ``\pushToTag`` command."""
    head = r'\pushToTag'

    def signatures(self):
        yield (Symbol, String, Scheme), MUSIC


class AppendToTag(element.HeadElement):
    r"""A ``\appendToTag`` command."""
    head = r'\appendToTag'

    def signatures(self):
        yield (Symbol, String, Scheme), MUSIC


class Etc(element.HeadElement):
    r"""The ``\etc`` placeholder."""
    head = r'\etc'


class Accepts(element.HeadElement):
    r"""The ``\accepts`` command."""
    _space_after_head = _space_between = " "
    head = r'\accepts'

    def signatures(self):
        yield (String, Symbol),


class Denies(element.HeadElement):
    r"""The ``\denies`` command."""
    _space_after_head = _space_between = " "
    head = r'\denies'

    def signatures(self):
        yield (String, Symbol),


class Name(element.HeadElement):
    r"""The ``\name`` command."""
    _space_after_head = _space_between = " "
    head = r'\name'

    def signatures(self):
        yield (String, Symbol),


class Alias(element.HeadElement):
    r"""The ``\alias`` command."""
    _space_after_head = _space_between = " "
    head = r'\alias'

    def signatures(self):
        yield (String, Symbol),


class Consists(element.HeadElement):
    r"""The ``\consists`` command."""
    _space_after_head = _space_between = " "
    head = r'\consists'

    def signatures(self):
        yield (String, Symbol, Scheme),


class Remove(element.HeadElement):
    r"""The ``\remove`` command."""
    _space_after_head = _space_between = " "
    head = r'\remove'

    def signatures(self):
        yield (String, Symbol, Scheme),


class DefaultChild(element.HeadElement):
    r"""The ``\defaultchild`` command."""
    _space_after_head = _space_between = " "
    head = r'\defaultchild'

    def signatures(self):
        yield (String, Symbol),


class Omit(element.HeadElement, Music):
    r"""The ``\omit`` command."""
    _space_after_head = _space_between = " "
    head = r'\omit'

    def signatures(self):
        yield SYMBOL,


class Hide(element.HeadElement, Music):
    r"""The ``\hide`` command."""
    _space_after_head = _space_between = " "
    head = r'\hide'

    def signatures(self):
        yield SYMBOL,


class Undo(element.HeadElement, Music):
    r"""The ``\undo`` command."""
    _space_after_head = _space_between = " "
    head = r'\undo'

    def signatures(self):
        yield MUSIC,


class Once(element.HeadElement, Music):
    r"""The ``\once`` command."""
    _space_after_head = _space_between = " "
    head = r'\once'

    def signatures(self):
        yield MUSIC,


class Temporary(element.HeadElement, Music):
    r"""The ``\temporary`` command."""
    _space_after_head = _space_between = " "
    head = r'\temporary'

    def signatures(self):
        yield MUSIC,


class Override(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""The ``\override`` command."""
    _space_after_head = _space_between = " "
    head = r'\override'

    def signatures(self):
        yield SYMBOL, EqualSign, VALUE
        yield SYMBOL, Scheme, EqualSign, VALUE
        yield SYMBOL, Scheme, Scheme, EqualSign, VALUE
        yield SYMBOL, Scheme, Scheme, Scheme, EqualSign, VALUE
        yield SYMBOL, Scheme, Scheme, Scheme, Scheme, EqualSign, VALUE


class Revert(element.HeadElement, Music):
    r"""The ``\revert`` command."""
    _space_after_head = _space_between = " "
    head = r'\revert'

    def signatures(self):
        yield SYMBOL,
        yield SYMBOL, Scheme
        yield SYMBOL, Scheme, Scheme
        yield SYMBOL, Scheme, Scheme, Scheme
        yield SYMBOL, Scheme, Scheme, Scheme, Scheme


class Set(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""The ``\set`` command."""
    _space_after_head = _space_between = " "
    head = r'\set'

    def signatures(self):
        yield SYMBOL, EqualSign, VALUE


class Unset(element.HeadElement, Music):
    r"""The ``\unset`` command."""
    _space_after_head = _space_between = " "
    head = r'\unset'

    def signatures(self):
        yield SYMBOL,


class Version(element.HeadElement, Music):
    r"""The ``\version`` command."""
    _space_after_head = _space_between = " "
    head = r'\version'

    def signatures(self):
        yield String,


class Language(element.HeadElement):
    r"""The ``\language`` command."""
    _space_after_head = _space_between = " "
    head = r'\language'

    def signatures(self):
        yield String,


class Include(element.HeadElement):
    r"""The ``\include`` command."""
    _space_after_head = _space_between = " "
    head = r'\include'

    def signatures(self):
        yield String,


class VoiceN(element.MappingElement):
    r"""Commands like ``\voiceOne``, ``\voiceTwo``, etc."""
    mapping = {
        r'\voiceOne': 1,
        r'\voiceTwo': 2,
        r'\voiceThree': 3,
        r'\voiceFour': 4,
        r'\voiceFive': 5,
        r'\voiceSix': 6,
    }


class GrobDirection(element.MappingElement):
    r"""A collection of commands concerning direction, like ``\slurUp``.

    To create a ``\slurUp`` command, use::

        >>> node = lily.GrobDirection(("Slur", 1))
        >>> node.write()
        '\\slurUp'

    Or::

        >>> node = lily.GrobDirection.from_mapping(r'\slurUp')

    When reading this node programmatically, the ``grob`` and ``direction``
    attributes can be read and modified::

        >>> node.grob
        'Slur'
        >>> node.direction
        1
        >>> node.write()
        '\\slurUp'
        >>> node.direction = -1
        >>> node.write()
        '\\slurDown'

    The ``grobs`` class attribute is a dictionary mapping each available grob
    to a tuple of the directions it supports. (Technically not all named
    objects are grobs (graphical objects).) Most "grobs" support all three
    directions: Up (1), Neutral (0), Down (-1).

    """
    mapping = {
        r'\arpeggioArrowDown': ('ArpeggioArrow', -1),
        r'\arpeggioArrowUp': ('ArpeggioArrow', 1),
        r'\bassFigureStaffAlignmentDown': ('BassFigureStaffAlignment', -1),
        r'\bassFigureStaffAlignmentNeutral': ('BassFigureStaffAlignment', 0),
        r'\bassFigureStaffAlignmentUp': ('BassFigureStaffAlignment', 1),
        r'\dotsDown': ('Dots', -1),
        r'\dotsNeutral': ('Dots', 0),
        r'\dotsUp': ('Dots', 1),
        r'\dynamicDown': ('Dynamic', -1),
        r'\dynamicNeutral': ('Dynamic', 0),
        r'\dynamicUp': ('Dynamic', 1),
        r'\phrasingSlurDown': ('PhrasingSlur', -1),
        r'\phrasingSlurNeutral': ('PhrasingSlur', 0),
        r'\phrasingSlurUp': ('PhrasingSlur', 1),
        r'\slurDown': ('Slur', -1),
        r'\slurNeutral': ('Slur', 0),
        r'\slurUp': ('Slur', 1),
        r'\stemDown': ('Stem', -1),
        r'\stemNeutral': ('Stem', 0),
        r'\stemUp': ('Stem', 1),
        r'\textSpannerDown': ('TextSpanner', -1),
        r'\textSpannerNeutral': ('TextSpanner', 0),
        r'\textSpannerUp': ('TextSpanner', 1),
        r'\tieDown': ('Tie', -1),
        r'\tieNeutral': ('Tie', 0),
        r'\tieUp': ('Tie', 1),
        r'\tupletDown': ('Tuplet', -1),
        r'\tupletNeutral': ('Tuplet', 0),
        r'\tupletUp': ('Tuplet', 1),
    }

    def grobs(mapping):
        d = collections.defaultdict(list)
        for grob, direction in mapping.values():
            d[grob].append(direction)
        return {grob: tuple(sorted(dirs)) for grob, dirs in d.items()}
    grobs = grobs(mapping)

    @property
    def grob(self):
        """The grob (graphical object), starting with a Capital."""
        return self.head[0]

    @grob.setter
    def grob(self, value):
        self.head = (value, self.head[1])

    @property
    def direction(self):
        """The direction, 1 for up, 0 for neutral, -1 for down."""
        return self.head[1]

    @direction.setter
    def direction(self, value):
        self.head = (self.head[0], value)


class GrobStyle(element.MappingElement):
    r"""A collection of commands concerning direction, like ``\slurDashed``.

    To create a ``\slurDashed`` command, use::

        >>> node = lily.GrobStyle(("Slur", "dashed"))
        >>> node.write()
        '\\slurDashed'

    Or::

        >>> node = lily.GrobStyle.from_mapping(r'\slurDashed')

    When reading this node programmatically, the ``grob`` and ``style``
    attributes can be read and modified::

        >>> node.grob
        'Slur'
        >>> node.style
        'dashed'
        >>> node.write()
        '\\slurDashed'
        >>> node.style = "dotted"
        >>> node.write()
        '\\slurDotted'

    The ``grobs`` class attribute is a dictionary mapping each available grob
    to a tuple of the styles it supports. All grobs support the styles
    ``"solid"``, ``"dashed"``, and ``"dotted"``.

    """
    mapping = {
        r'\phrasingSlurDashed': ('PhrasingSlur', "dashed"),
        r'\phrasingSlurDotted': ('PhrasingSlur', "dotted"),
        r'\phrasingSlurSolid': ('PhrasingSlur', "solid"),
        r'\slurDashed': ('Slur', "dashed"),
        r'\slurDotted': ('Slur', "dotted"),
        r'\slurSolid': ('Slur', "solid"),
        r'\tieDashed': ('Tie', "dashed"),
        r'\tieDotted': ('Tie', "dotted"),
        r'\tieSolid': ('Tie', "solid"),
    }

    def grobs(mapping):
        d = collections.defaultdict(list)
        for grob, direction in mapping.values():
            d[grob].append(direction)
        return {grob: tuple(sorted(dirs)) for grob, dirs in d.items()}
    grobs = grobs(mapping)

    @property
    def grob(self):
        """The grob (graphical object), starting with a Capital."""
        return self.head[0]

    @grob.setter
    def grob(self, value):
        self.head = (value, self.head[1])

    @property
    def style(self):
        """The style: ``"solid"``, ``"dashed"``, or ``"dotted"``."""
        return self.head[1]

    @style.setter
    def style(self, value):
        self.head = (self.head[0], value)


class Toggle(element.MappingElement):
    r"""A collection of commands that can be on/off, like ``\textLengthOn``.

    To create a ``\textLengthOn`` command, use::

        >>> node = lily.Toggle(("textLength", True))
        >>> node.write()
        '\\textLengthOn'

    Or::

        >>> node = lily.Toggle.from_mapping(r'\textLengthOn')

    When reading this node programmatically, the ``prop`` and ``value``
    attributes can be read and modified::

        >>> node.prop
        'textLength'
        >>> node.value
        True
        >>> node.write()
        '\\textLengthOn'
        >>> node.value = False
        >>> node.write()
        '\\textLengthOff'

    The ``props`` class attribute is a tuple with all available prop names. All
    props support the values True and False.

    """
    props = (
        "autoBeam",
        "autoBreaks",                   # since 2.20
        "autoLineBreaks",               # since 2.20
        "autoPageBreaks",               # since 2.20
        "balloonLength",
        "bassFigureExtenders",
        "cadenza",
        "deadNotes",                    # since 2.20
        "easyHeads",
        "improvisation",
        "harmonics",
        "kievan",                       # since 2.20
        "markLength",                   # since 2.18
        "mergeDifferentlyDotted",
        "mergeDifferentlyHeaded",
        "pointAndClick",
        "predefinedFretboards",
        "sostenuto",
        "sustain",
        "textLength",
        "xNotes",
    )

    mapping = {}
    for p in props:
        mapping[r'\{}On'.format(p)] = (p, True)
        mapping[r'\{}Off'.format(p)] = (p, False)
    del p

    @property
    def prop(self):
        """The property that can be on or off."""
        return self.head[0]

    @prop.setter
    def prop(self, value):
        self.head = (value, self.head[1])

    @property
    def value(self):
        """The value (True for ``"On"``, False for ``"Off"``)."""
        return self.head[1]

    @value.setter
    def value(self, value):
        self.head = (self.head[0], value)


class Shape(element.HeadElement):
    r"""The ``\shape`` command.

    Has a Scheme and a SYMBOL child. (As articulation, has only a
    Scheme child.)

    """
    _space_after_head = _space_between = " "
    head = r'\shape'

    def signatures(self):
        yield Scheme, SYMBOL


class StringTuning(element.HeadElement):
    r"""The ``\stringTuning`` command, with one Chord argument."""
    _space_after_head = _space_between = " "
    head = r'\stringTuning'

    def signatures(self):
        yield MUSIC,


class Unit(element.MappingElement):
    r"""A unit: ``\mm``, ``\cm``, ``\pt`` or ``\in``.

    A Unit node can be attached to an Int or Float::

        >>> from quickly.dom import lily
        >>> lily.Int(10, lily.Unit("cm")).write()
        '10\\cm'

    """
    mapping = {
        r'\mm': 'mm',
        r'\cm': 'cm',
        r'\in': 'in',
        r'\pt': 'pt',
    }


def is_symbol(text):
    """Return True is text is a valid LilyPond symbol."""
    from parce.lang import lilypond, lilypond_words
    return (re.fullmatch(lilypond.RE_LILYPOND_SYMBOL, text) and
            text not in lilypond_words.all_pitch_names)


def make_list_node(value):
    """Return an element node corresponding to the value.

    If value is a string, a Symbol is returned if it's valid LilyPond identifier.
    otherwise String. If value is an integer, a Int is returned.

    If no suitable node type could be returned, None is returned.

    """
    if isinstance(value, str):
        return Symbol(value) if is_symbol(value) else String(value)
    elif isinstance(value, int):
        return Int(value)


def make_list_nodes(iterable):
    """Return a generator yielding nodes created by :func:`make_list_node`."""
    for value in iterable:
        node = make_list_node(value)
        if node:
            yield node


def convert_duration_to_int(node):
    """Return an Int element, created from the specified Duration element.

    This can be used if a music function wants an integer number, while the
    origin token was seen as a duration by parce and the music builder.

    """
    try:
        try:
            origin = node.head_origin
        except AttributeError:
            return Int(int(node.write()))
        else:
            return Int.with_origin(origin)
    except ValueError:
        return    # cannot convert


def create_element_from_value(value):
    """Convert a regular Python value to a lilypond Element node.

    This can be used to ease manually building a node structure. Converts:

    * bool to Scheme('#', scm.Bool(value))
    * int to Int(value)
    * float to Float(value)
    * str to String(value)
    * tuple(int, "unit") to Int(value, Unit("unit")) where unit in "mm", "cm", "in", "pt"
    * tuple(float, "unit") to Float(value, Unit("unit")) where unit in "mm", "cm", "in", "pt"
    * an Element node is returned unchanged.

    Raises ValueError when a value can't be converted to an element.

    """
    if isinstance(value, element.Element):
        return value
    if (isinstance(value, tuple) and len(value) == 2
            and isinstance(value[0], (int, float)) and value[1] in ('mm', 'cm', 'in', 'pt')):
        unit = Unit(value[1]),
        value = value[0]
    else:
        unit = ()
    if isinstance(value, bool):
        return Scheme('#', scm.Bool(value))
    elif isinstance(value, int):
        return Int(value, *unit)
    elif isinstance(value, float):
        return Float(value, *unit)
    elif isinstance(value, str):
        return String(value)
    raise ValueError("Can't convert value to Element node: {}".format(repr(value)))


def create_value_from_element(node):
    """Gets the value from en Element node.

    Returns:

    * bool for a Scheme('#', scm.Bool(value)) node
    * int for an Int node
    * float for a Float node
    * str for a String or Symbol node
    * tuple(int, "unit") for a Int(Unit()) node
    * tuple(float, "unit") for a Float(Unit()) node

    Returns None when this function cannot get a simple value from the node.

    """
    if isinstance(node, (Int, Float)):
        value = node.head
        for unit in node/Unit:
            return (value, unit.head)
        return value
    elif isinstance(node, (String, Symbol)):
        return node.head
    elif isinstance(node, Scheme) and len(node) == 1 and isinstance(node[0], scm.Bool):
        return node[0].value


# often used signatures:
MUSIC = (Music, IdentifierRef, Etc)
VALUE = (List, String, Scheme, Number, Markup, IdentifierRef, Etc, Unpitched)
SYMBOL = (List, Symbol, String)
TEXT = (List, Symbol, String, Markup, IdentifierRef, Etc)
NUMBER = (Scheme, Number, Unpitched)
