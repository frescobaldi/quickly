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
import itertools
import re

from .. import duration, pitch
from . import base, element, scm


class Music(element.Element):
    """Base class for all elements that contain music."""
    def is_sequential(self):
        """Return True if child music nodes should be played sequentially.

        This is used to compute the time position of a child: if this returns
        False, every child starts at the same position; if True, preceding
        nodes must be traversed in order to get the time position.

        """
        return False

    def transform(self):
        """Can return a :class:`~.duration.Transform` that adjusts the duration
        of child nodes.

        By default, None is returned.

        """
        pass

    def properties(self):
        """Can return a :class:`~.datatypes.Properties` object with values to
        keep in the context of this node.

        By default, None is returned.

        Inside the :meth:`Music.time_length` method you can access and modify
        the accumulated properties of the current Music node via the
        :attr:`~.time.TimeContext.properties` attribute of a
        :class:`~.time.TimeContext` object

        """

    def time_length(self, context, end=None):
        """Return the length of this expression, using a
        :class:`~.time.TimeContext` handler.

        If ``end`` is given it is the index to stop just before.

        """
        if self.is_sequential():
            return sum(context.length(n) for n in self[:end])
        elif end is None:
            return max((context.length(n) for n in self), default=0)
        return 0


class Durable(Music):
    """Base class for a single musical object that takes time and can have a
    Duration child.

    The :attr:`duration` and :attr:`scaling` properties make it easy to
    manipulate the respective child and grandchild nodes. Floating point values
    are automatically converted to Fractions, with a limit on the denominator,
    so a lazy ``note.scaling = 1/3`` works properly.

    Inherited by: :class:`Note`, :class:`Rest`, :class:`Chord`, :class:`Space`,
    :class:`Skip`, :class:`LyricText` etc.

    """
    duration_required = False     #: Whether the Duration child is required (e.g. \skip)
    duration_sets_previous = True #: Whether this Duration is stored as the previous duration for Durables without Duration

    def time_length(self, context, end=None):
        """Return the length of this Durable, using a
        :class:`~.time.TimeContext` handler.

        For Durable, ``end`` is ignored.

        """
        return context.durable_length(self)

    @property
    def duration(self):
        """Read or set the duration.

        The duration is the head value of the Duration child. The value is None
        if there is no Duration child. Delete or set to None to remove the
        child. (In that case the scaling also disappears.)

        """
        for n in self / Duration:
            return n.head

    @duration.setter
    def duration(self, value):
        for n in self / Duration:
            if value is None:
                self.remove(n)
            elif not isinstance(value, fractions.Fraction):
                n.head = fractions.Fraction(value).limit_denominator()
            else:
                n.head = value
            return
        if value is not None:
            self.add(Duration(value))

    @duration.deleter
    def duration(self):
        for n in self / Duration:
            self.remove(n)
            break

    @property
    def scaling(self):
        """Read or set the scaling.

        The scaling is the value of the DurationScaling child of the Duration
        child. The value is None if there is no Duration child and 1 if there
        is no DurationScaling grand child. Delete or set to None to remove the
        DurationScaling grand child.

        Setting the property while there is no duration child raises a
        ValueError. Setting it to None or 1 removes the DurationScaling grand
        child.

        """
        for d in self / Duration:
            scaling = 1
            for s in d / DurationScaling:
                scaling *= s.head
            return scaling
        return None

    @scaling.setter
    def scaling(self, value):
        for d in self / Duration:
            scaling = d / DurationScaling
            for s in scaling:
                if value in (1, None):
                    d.remove(s)
                elif not isinstance(value, fractions.Fraction):
                    s.head = fractions.Fraction(value).limit_denominator()
                else:
                    s.head = value
                for s in scaling:
                    d.remove(s)
                return
            if value not in (1, None):
                d.insert(0, DurationScaling(value))
            return
        if value not in (1, None):
            raise ValueError("can't set scaling if no duration is set")

    @scaling.deleter
    def scaling(self):
        self.scaling = None

    @property
    def duration_scaling(self):
        """Access duration and scaling in one go.

        This value is either a two-tuple (duration, scaling) or None.

        """
        for d in self / Duration:
            return d.duration()

    @duration_scaling.setter
    def duration_scaling(self, value):
        if value:
            self.duration, self.scaling = value
        else:
            del self.duration

    @duration_scaling.deleter
    def duration_scaling(self):
        del self.duration


class Pitchable(element.TextElement, Music):
    """Base class for a note or pitched rest.

    The head value is the pitch name. To read, write and understand the pitch
    name, use a :class:`~.pitch.PitchProcessor`.

    This class provides convenient properties to manipulate the
    :class:`Octave`, :class:`Accidental` and/or :class:`OctCheck` child nodes.

    Inherited by: :class:`Note`, :class:`Pitch` (a pitch that is no durable
    music), :class:`PitchedRest`.

    """
    @property
    def octave(self):
        """Read or set the octave.

        The octave is an integer value, indicating how many ``'``-s or ``,``-s
        are displayed after the pitch name. Automatically creates an
        :class:`Octave` child if needed. Delete this attribute or set it to 0
        to remove the octave.

        """
        for n in self / Octave:
            return n.head
        return 0

    @octave.setter
    def octave(self, num):
        for n in self / Octave:
            n.head = num
            return
        if num != 0:
            self.add(Octave(num))

    @octave.deleter
    def octave(self):
        self[:] = self ^ Octave

    @property
    def accidental(self):
        """Read or set the accidental.

        The accidental is ``None``, ``"cautionary"`` or ``"forced"``.
        Automatically creates an :class:`Accidental` child if needed.
        Delete this attribute or set it to None to remove the accidental.

        """
        for n in self / Accidental:
            return n.head

    @accidental.setter
    def accidental(self, value):
        for n in self / Accidental:
            if not value:
                self.remove(n)
            else:
                n.head = value
            return
        if value:
            self.add(Accidental(value))

    @accidental.deleter
    def accidental(self):
        self[:] = self ^ Accidental

    @property
    def oct_check(self):
        """Read or set the octave check.

        The octave check is an integer value, or None, when no octave check is
        there. Automatically creates an :class:`OctCheck` child if set. Delete
        this attribute or set it tot ``None`` to remove the octave check.

        """
        for n in self / OctCheck:
            return n.head

    @oct_check.setter
    def oct_check(self, num):
        for n in self / OctCheck:
            if num is None:
                self.remove(n)
            else:
                n.head = num
            return
        if num is not None:
            self.add(OctCheck(num))

    @oct_check.deleter
    def oct_check(self):
        self[:] = self ^ OctCheck


class Reference(element.Element):
    r"""Base class for an Element that (potentially) refers to another node,
    possibly in another DOM tree.

    This is used te get the value of a variable, e.g. for the IdentifierRef and
    the MarkupCommand element types. The :meth:`get_value` method returns the
    value. Here is an example of how it works::

        >>> from quickly.dom import read
        >>> m = read.lily_document(r'''
        ... titled = "blurk"
        ...
        ... \header {
        ...   title = "Wilbert"
        ...   composer = \title
        ... }
        ... ''', True)
        >>> m.dump()
        <lily.Document (2 children)>
         ├╴<lily.Assignment titled (3 children)>
         │  ├╴<lily.Identifier (1 child)>
         │  │  ╰╴<lily.Symbol 'titled' [1:7]>
         │  ├╴<lily.EqualSign [8:9]>
         │  ╰╴<lily.String 'blurk' [10:17]>
         ╰╴<lily.Header (2 children) [19:70]>
            ├╴<lily.Assignment title (3 children)>
            │  ├╴<lily.Identifier (1 child)>
            │  │  ╰╴<lily.Symbol 'title' [31:36]>
            │  ├╴<lily.EqualSign [37:38]>
            │  ╰╴<lily.String 'Wilbert' [39:48]>
            ╰╴<lily.Assignment composer (3 children)>
               ├╴<lily.Identifier (1 child)>
               │  ╰╴<lily.Symbol 'composer' [51:59]>
               ├╴<lily.EqualSign [60:61]>
               ╰╴<lily.IdentifierRef 'title' [62:68]>
        >>> n = m[1].composer
        >>> n
        <lily.IdentifierRef 'title' [62:68]>
        >>> n.get_value()
        <lily.String 'Wilbert' [39:48]>
        >>> n.head = "titled"
        >>> n.get_value()
        <lily.String 'blurk' [10:17]>

    The ``composer`` field in the header is set to the value of the title
    field. When requesting the value, the value of the title assignment is
    returned. When we change the name of the variable reference to ``titled``,
    it finds the "blurk" value in the toplevel document.

    A reference can also point to another file. A :class:`~.scope.Scope` is used
    to define the context of a file and the desired path to look for ``\include``
    files. Here is an example. First we create two LilyPond files::

        >>> with open('file_a.ly', 'w') as f:
        ...     f.write("music = { c d e f g }\n")
        ...
        22
        >>> with open('file_b.ly', 'w') as f:
        ...     f.write('\\include "file_a.ly"\n\n{ \\music }\n')
        ...
        33

    Then we load ``file_b.ly`` into a parce document, and we try to find the
    value of the ``\music`` variable::

        >>> import quickly
        >>> d = quickly.load('file_b.ly')
        >>> print(d.text())
        \include "file_a.ly"

        { \music }

        >>> m = d.get_transform(True)
        >>> m.dump()
        <lily.Document (2 children)>
         ├╴<lily.Include 'file_a.ly' (1 child) [0:8]>
         │  ╰╴<lily.String 'file_a.ly' [9:20]>
         ╰╴<lily.MusicList (1 child) [22:32]>
            ╰╴<lily.IdentifierRef 'music' [24:30]>
        >>> m[1][0]
        <lily.IdentifierRef 'music' [24:30]>
        >>> print(m[1][0].get_value())
        None

    We see that the returned value is None, meaning that the definition of
    ``music`` was not found in ``file_b.ly``. Now, we create a
    :class:`~.scope.Scope` to find included files, and try it again::

        >>> from quickly.dom.scope import Scope
        >>> s = Scope(d)
        >>> m[1][0].get_value(s)
        <lily.MusicList (5 children) [8:21]>
        >>> m[1][0].get_value(s).dump()
        <lily.MusicList (5 children) [8:21]>
         ├╴<lily.Note 'c' [10:11]>
         ├╴<lily.Note 'd' [12:13]>
         ├╴<lily.Note 'e' [14:15]>
         ├╴<lily.Note 'f' [16:17]>
         ╰╴<lily.Note 'g' [18:19]>
        >>> m[1][0].get_value_with_scope(s)
        (<lily.MusicList (5 children) [8:21]>, <Scope 'file_a.ly'>)

    The ``music`` in ``file_a.ly`` is found. The :meth:`get_value_with_scope`
    method also returns the scope the definition was found in, which can be
    used to recursively resolve Reference nodes in the returned node.

    """
    def get_value(self, scope=None, wait=True):
        """Find the value this variable refers to.

        Returns the value if found, and None otherwise. For the arguments, see
        :meth:`get_value_with_scope`.

        """
        result = self.get_value_with_scope(scope)
        if result:
            return result[0]

    def get_value_with_scope(self, scope=None, wait=True):
        """Find the value this variable refers to.

        Searches for Assignments. If found, returns a two-tuple (value, scope).
        Otherwise None. The scope is the scope the value was found in.

        The ``scope``, if given, is used to resolve include files. If no scope
        is given, only searches the current DOM document; the returned scope is
        then always None.

        If a scope is given, include commands are followed and ``wait``
        determines whether to wait for ongoing transformations of external DOM
        documents. If wait is False, and a transformation is not yet finished,
        a value found in an included document will not be returned.

        """
        return Lookup(self, scope, wait).find_assignment(self.get_name())

    def get_name(self):
        """Implement to return the name the ``get_value()`` methods search for."""
        raise NotImplementedError


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


class _ConvertUnpitchedToDuration(element.Element):
    """Mixin class to convert Unpitched arguments to their Duration."""
    def add_argument(self, node):
        """Reimplemented to pick the Duration of an Unpitched node."""
        if isinstance(node, Unpitched):
            for node in node:
                node = node.copy_with_origin()
                break
        super().add_argument(node)


class _ConvertUnpitchedToInt(element.Element):
    """Mixin class to convert Unpitched arguments to an Int."""
    def add_argument(self, node):
        """Reimplemented to read the Duration of an Unpitched node as a Int."""
        if isinstance(node, Unpitched):
            for dur in node / Duration:
                node = convert_duration_to_int(dur) or node
                break
        super().add_argument(node)


class HandleAssignments(element.Element):
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
            node = assignment.get_value()
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
            assignment[-1] = node
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
        """The LilyPond version number, as a tuple of ints (may be empty)."""
        for v in self//Version:
            return v.version
        return ()

    @version.setter
    def version(self, version):
        for v in self//Version:
            v.version = version
            return
        self.insert(0, Version(version=version))


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
    def fraction(self):
        """Return the head value as a :class:`fractions.Fraction`."""
        return fractions.Fraction(*self.head)

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
    space_before = space_after = " "

    @classmethod
    def check_head(cls, head):
        return head in ('$', '#', '$@', '#@')


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

    def find_parallel(self, limit=0):
        r"""Try to find the other end of this spanner. May return None.

        Does not look outside of the current New or Assignment node. The
        ``limit`` can be used to further restrict the number of nodes searched,
        e.g. to prevent slowness in text editors that do not need to highlight
        items far offscreen.

        For example::

            >>> from quickly.dom import lily, read
            >>> n = read.lily(r"{ c\=1( d e f g\=2) a\=1) }", True)
            >>> n.dump()
            <lily.MusicList (6 children) [0:27]>
             ├╴<lily.Note 'c' (1 child) [2:3]>
             │  ╰╴<lily.Articulations (1 child)>
             │     ╰╴<lily.SpannerId (2 children) [3:5]>
             │        ├╴<lily.Int 1 [5:6]>
             │        ╰╴<lily.Slur 'start' [6:7]>
             ├╴<lily.Note 'd' [8:9]>
             ├╴<lily.Note 'e' [10:11]>
             ├╴<lily.Note 'f' [12:13]>
             ├╴<lily.Note 'g' (1 child) [14:15]>
             │  ╰╴<lily.Articulations (1 child)>
             │     ╰╴<lily.SpannerId (2 children) [15:17]>
             │        ├╴<lily.Int 2 [17:18]>
             │        ╰╴<lily.Slur 'stop' [18:19]>
             ╰╴<lily.Note 'a' (1 child) [20:21]>
                ╰╴<lily.Articulations (1 child)>
                   ╰╴<lily.SpannerId (2 children) [21:23]>
                      ├╴<lily.Int 1 [23:24]>
                      ╰╴<lily.Slur 'stop' [24:25]>
            >>> slur = n.find_descendant(6)
            >>> slur
            <lily.Slur 'start' [6:7]>
            >>> slur.find_parallel()
            <lily.Slur 'stop' [24:25]>

        """
        upto = next(self << (Assignment, New, Document, Score), None)
        nodes = self.forward(upto) if self.head == "start" else self.backward(upto)
        if limit:
            nodes = itertools.islice(nodes, limit)
        cls, head = type(self), self.head
        parallel = lambda n: type(n) is cls and n.head != head

        spanner_id = self.left_sibling() if isinstance(self.parent, SpannerId) else None
        if spanner_id:
            spanner_ok = lambda n: isinstance(n.parent, SpannerId) and spanner_id.equals(n.left_sibling())
        else:
            spanner_ok = lambda n: not isinstance(n.parent, SpannerId)

        for n in filter(lambda n: parallel(n) and spanner_ok(n), nodes):
            return n


class Block(HandleAssignments, element.BlockElement):
    """Base class for a block, e.g. score, paper, etc.

    Newlines are placed by default between all child nodes. There are
    convenience methods to access variables inside a block.

    """
    space_before = space_after = space_after_head = space_before_tail = space_between = '\n'
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
        >>> h.tagline = False
        >>> print(h.write_indented())
        \header {
          title = "My title"
          composer = "Wilbert Berendsen"
          tagline = ##f
        }

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
    space_before = space_after = " "


class LayoutContext(Block):
    r"""A \context { } block within \layout or \midi."""
    head = r"\context {"


class EqualSign(element.HeadElement):
    r"""An equal sign (``=``)."""
    head = "="
    space_before = space_after = " "


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
        nodes = filter_map(make_list_node, iterable)
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
    space_before = space_after = '\n'

    @classmethod
    def with_name(cls, name, node):
        """Convenience constructor to create a complete Assignment.

        Automatically creates a Identifier child node for the ``name``, an
        EqualSign node, and appends the specified ``node`` as the value of the
        assignment. For the ``name``, see :meth:`Identifier.set_name`.

        """
        return cls(Identifier.with_name(name), EqualSign(), node)

    def repr_head(self):
        """If available, show the name of our identifier."""
        for child in self / Identifier:
            return child.write()

    def get_name(self):
        """Return the name of our identifier as a string or tuple."""
        for child in self / Identifier:
            return child.get_name()

    def get_value(self):
        """Return the value after the equalsign."""
        for child in self / EqualSign:
            return child.right_sibling()


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


class IdentifierRef(base.BackslashCommand, Reference):
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
        nodes = filter_map(make_list_node, name)
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


class MusicFunction(base.BackslashCommand, Music):
    r"""A generic music function with a backslash, like ``\stemUp``

    To be used if there is no special Element type for the music function.
    When manually constructing this element, the initial backslash need not
    to be given. Example::

        >>> from quickly.dom.lily import MusicFunction
        >>> MusicFunction('stemUp').write()
        '\\stemUp'

    """
    space_between = space_after_head = " "

    def signatures(self):
        if self.head == "defineBarLine":
            yield String, Scheme


class Context(element.HeadElement, Music):
    r"""``\context ...``."""
    space_between = space_after_head = " "
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
    space_between = space_after_head = " "
    head = r'\change'

    def signatures(self):
        yield Symbol, EqualSign, (String, Symbol)


class AddQuote(element.HeadElement):
    r"""An ``\addQuote`` command, at toplevel."""
    space_between = space_after_head = " "
    head = r'\addQuote'

    def signatures(self):
        yield (Identifier, String, Symbol), MUSIC


class QuoteDuring(element.HeadElement, Music):
    r"""A ``\quoteDuring`` command."""
    space_between = space_after_head = " "
    head = r'\quoteDuring'

    def signatures(self):
        yield (List, String, Symbol), MUSIC


class ApplyContext(element.HeadElement):
    r"""The ``\applyContext`` command."""
    space_between = space_after_head = " "
    head = r'\applyContext'

    def signatures(self):
        yield Scheme,


class ApplyMusic(element.HeadElement):
    r"""The ``\applyMusic`` function."""
    space_between = space_after_head = " "
    head = r'\applyMusic'

    def signatures(self):
        yield Scheme, MUSIC


class ApplyOutput(element.HeadElement):
    r"""The ``\applyOutput`` command."""
    space_between = space_after_head = " "
    head = r'\applyOutput'

    def signatures(self):
        yield SYMBOL, Scheme


class Relative(element.HeadElement, Music):
    """Relative music."""
    head = r'\relative'
    space_between = space_after_head = " "

    def signatures(self):
        yield Pitchable, MUSIC
        yield MUSIC,

    def add_argument(self, node):
        """Reimplemented to turn an added Note argument into a Pitch."""
        if isinstance(node, Note) and sum(1 for n in self / Pitchable) < 1:
            node = node.to_pitch()
        return super().add_argument(node)


class Absolute(element.HeadElement, Music):
    """Absolute music."""
    head = r'\absolute'
    space_between = space_after_head = " "

    def signatures(self):
        yield MUSIC,


class Fixed(element.HeadElement, Music):
    """Fixed music."""
    head = r'\fixed'
    space_between = space_after_head = " "

    def signatures(self):
        yield Pitchable, MUSIC

    def add_argument(self, node):
        """Reimplemented to turn an added Note argument into a Pitch."""
        if isinstance(node, Note) and sum(1 for n in self / Pitchable) < 1:
            node = node.to_pitch()
        return super().add_argument(node)


class Transpose(element.HeadElement, Music):
    """Transposed music."""
    head = r'\transpose'
    space_between = space_after_head = " "

    def signatures(self):
        yield Pitchable, Pitchable, MUSIC

    def add_argument(self, node):
        """Reimplemented to turn 2 added Note arguments into Pitch arguments."""
        if isinstance(node, Note) and sum(1 for n in self / Pitchable) < 2:
            node = node.to_pitch()
        return super().add_argument(node)


class Repeat(element.HeadElement, Music):
    """Repeated music."""
    head = r'\repeat'
    space_between = space_after_head = " "

    def signatures(self):
        yield Symbol, INT, MUSIC
        yield Symbol, INT, MUSIC, Alternative


class Alternative(element.HeadElement, Music):
    """Alternative music for repeats."""
    head = r'\alternative'
    space_between = space_after_head = " "

    def signatures(self):
        yield MusicList,


class UnfoldRepeats(element.HeadElement, Music):
    r"""The ``\unfoldRepeats`` command."""
    space_between = space_after_head = " "
    head = r'\unfoldRepeats'

    def signatures(self):
        yield MUSIC,


class Unfolded(element.HeadElement, Music):
    r"""The ``\unfolded`` command."""
    head = r'\unfolded'
    space_between = space_after_head = " "

    def signatures(self):
        yield MUSIC,


class Volta(element.HeadElement, Music):
    r"""The ``\volta`` command."""
    head = r'\volta'
    space_between = space_after_head = " "

    def signatures(self):
        yield (List, Scheme), MUSIC


class Transposition(element.HeadElement, Music):
    r"""A ``\tranposition`` command."""
    head = r'\transposition'
    space_between = space_after_head = " "

    def signatures(self):
        yield Pitchable,

    def add_argument(self, node):
        """Reimplemented to turn an added Note argument into a Pitch."""
        if isinstance(node, Note) and sum(1 for n in self / Pitchable) < 1:
            node = node.to_pitch()
        return super().add_argument(node)


class Ottava(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""An ``\ottava`` command."""
    space_between = space_after_head = " "
    head = r'\ottava'

    def signatures(self):
        yield NUMBER,


class MusicList(element.BlockElement, Music):
    """A list of music items between ``{`` ... ``}``."""
    space_after_head = space_before_tail = space_between = " "
    head = "{"
    tail = "}"

    def is_sequential(self):
        """Return False when the parent is a Simultaneous command, True otherwise."""
        return not isinstance(self.parent, Simultaneous)

    def indent_align_indices(self):
        """How to align child nodes if on the same line as an indenting char."""
        yield 0


class SimultaneousMusicList(MusicList):
    """A list of music items between ``<<`` ... ``>>``."""
    head = "<<"
    tail = ">>"

    def is_sequential(self):
        """Return always False."""
        return False


class Sequential(element.HeadElement, Music):
    r"""The ``\sequential`` command, has one MusicList child."""
    head = r'\sequential'
    space_between = space_after_head = " "

    def signatures(self):
        yield MusicList,


class Simultaneous(element.HeadElement, Music):
    r"""The ``\simultaneous`` command, has one MusicList child."""
    head = r'\simultaneous'
    space_between = space_after_head = " "

    def signatures(self):
        yield MusicList,


class InputMode(Music):
    r"""Base class for any input mode, such as ``\figures`` or ``\lyricmode``.

    The head value is the command without backslash prepended.

    """
    space_between = space_after_head = " "

    def signatures(self):
        yield MUSIC,


class LyricMode(base.BackslashCommand, InputMode):
    r"""``\lyricmode``, ``\lyrics`` or ``\lyricsto``."""

    def signatures(self):
        if self.head == r'lyricsto':
            yield (String, Symbol), MUSIC
        else:
            yield MUSIC,


class ChordMode(base.BackslashCommand, InputMode):
    r"""``\chordmode`` or ``\chords``."""


class DrumMode(base.BackslashCommand, InputMode):
    r"""``\drummode`` or ``\drums``."""


class NoteMode(element.HeadElement, InputMode):
    r"""``\notemode``."""
    head = r'\notemode'


class FigureMode(base.BackslashCommand, InputMode):
    r"""``\figuremode`` or ``\figures``."""


class Chord(Durable):
    """A chord. Must have a ChordBody element."""

    def time_length(self, context, end=None):
        """Return the length of this Durable, using a
        :class:`~.time.TimeContext` handler.

        For Chord, ``end`` is ignored; returns 0 if the chord is empty,
        in accordance with LilyPond's behaviour.

        """
        for body in self:
            if any(body / Note):
                return super().time_length(context, end)
        return 0

    def child_order(self):
        yield ChordBody, Duration, Articulations, base.Comment


class ChordBody(element.BlockElement):
    """The body of a chord ``<`` ... ``>``.

    Always the child of a Chord, which can have a duration and articulations.
    Contains Note elements.

    """
    space_between = " "
    head = "<"
    tail = ">"

    def indent_align_indices(self):
        """How to align child nodes if on the same line as an indenting char."""
        yield 0


class Note(Pitchable, Durable):
    """A musical note."""

    def child_order(self):
        yield Octave, Accidental, OctCheck, Duration, Articulations, base.Comment

    def to_pitch(self):
        r"""Convenience function to create a :class:`Pitch` from this note.

        This is used when this Note is added to a command where the note has
        not a musical meaning, but just a pitch is intended, e.g. ``\key`` or
        ``\transpose``, etc.

        """
        p = Pitch(self.head, *self)
        p.copy_origin_from(self)
        return p


class Pitch(Pitchable):
    r"""A pitch name.

    This is used as pitch argument for ``\transpose``, ``\tranposition``,
    ``\fixed``, ``\relative``, ``\key`` etc. The difference with :class:`Note`
    is that a Pitch is not a Durable and can't have a duration or
    articulations.

    """

    def child_order(self):
        yield Octave, Accidental, OctCheck, base.Comment


class Unpitched(Durable):
    """An unpitched note, always has a Duration child."""
    duration_required = True    #: always needs a duration

    def child_order(self):
        yield Duration, Articulations, base.Comment


class RestType(Durable):
    """Base class for Rest, PitchedRest and MultiMeasureRest."""
    def child_order(self):
        yield Duration, Articulations, base.Comment


class Rest(element.HeadElement, RestType):
    head = "r"
    """A normal rest (``r``)."""


class MultiMeasureRest(Rest):
    head = "R"
    """A multi-measure rest (``R``)."""


class PitchedRest(Pitchable, RestType):
    r"""A pitched rest.

    This rest has a pitchname but also a RestModifier child, e.g. ``c\rest``.
    It is a normal rest, but vertically positioned using a pitch name, which is
    the head value. This element can also have an Octave or OctCheck.

    """
    def child_order(self):
        yield Octave, Accidental, OctCheck, Duration, RestModifier, Articulations, base.Comment


class Space(element.HeadElement, Durable):
    """A space (``s``)."""
    head = "s"

    def child_order(self):
        yield Duration, Articulations, base.Comment


class Skip(element.HeadElement, Durable):
    r"""A ``\skip``. Must have a Duration child."""
    head = r'\skip'
    space_after_head = " "
    duration_required = True        #: always needs a duration
    duration_sets_previous = False  #: the "previous" duration is not changed by \skip

    def child_order(self):
        yield Duration, base.Comment


class After(element.HeadElement, Music):
    r"""An ``\after``. Must have a Duration child and an event."""
    head = r'\after'


class Q(element.HeadElement, Durable):
    """A ``q``, repeating the previous chord.

    The repeated chord always has the same absolute pitch, Octave childs are
    not possible. LilyPond signals a warning if there is no previous chord in
    the current music expression, and the q becomes a skip.

    Articulations attached to the repeated chord or to its individual notes are
    not copied, but internal tweaks to the noteheads are.

    """
    head = 'q'

    def child_order(self):
        yield Duration, Articulations, base.Comment


class Drum(element.TextElement, Durable):
    """A drum note."""
    def child_order(self):
        yield Duration, Articulations, base.Comment


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

    The head value is the number of ``'`` (if positive) or the number of ``,``,
    if negative.

    """
    @classmethod
    def read_head(cls, origin):
        """Read the octave from the token."""
        return pitch.octave_from_string(origin[0].text)

    def write_head(self):
        """Write the octave, an empty string for octave 0."""
        return pitch.octave_to_string(self.head)


class OctCheck(element.TextElement):
    """The octavecheck after a note, e.g. like ``=,``.

    The head value is the number of ``'`` (if positive) or the number of ``,``,
    if negative.

    """
    @classmethod
    def read_head(cls, origin):
        """Read the octave from the token."""
        return pitch.octave_from_string(origin[0].text[1:])

    def write_head(self):
        """Write the octave, an empty string for octave 0."""
        return '=' + pitch.octave_to_string(self.head)


class OctaveCheck(element.HeadElement):
    r"""The ``\octaveCheck`` command."""
    space_after_head = space_between = " "
    head = r'\octaveCheck'

    def signatures(self):
        yield Pitchable,

    def add_argument(self, node):
        """Reimplemented to turn an added Note argument into a Pitch."""
        if isinstance(node, Note) and sum(1 for n in self / Pitchable) < 1:
            node = node.to_pitch()
        return super().add_argument(node)


class Duration(element.TextElement):
    """A duration after a note.

    To the constructor the duration is specified using a numerical value, which
    can be a :class:`~fractions.Fraction`. A whole note is 1, a breve 2, etc; a
    quarter note or crotchet 1/4, etc.

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
    def __init__(self, head, *children, **attrs):
        if not isinstance(head, fractions.Fraction):
            head = fractions.Fraction(head).limit_denominator()
        super().__init__(head, *children, **attrs)

    @classmethod
    def from_string(cls, text):
        """Convenience constructor to make a Duration from a string.

        Examples::

            >>> lily.Duration.from_string('4')
            <lily.Duration Fraction(1, 4)>
            >>> lily.Duration.from_string('2.')
            <lily.Duration Fraction(3, 4)>
            >>> d = lily.Duration.from_string('1*1/3')
            >>> d.dump()
            <lily.Duration Fraction(1, 1) (1 child)>
             ╰╴<lily.DurationScaling Fraction(1, 3)>
            >>> d.duration()
            Fraction(1, 3)

        """
        dur, *scalings = text.split('*')
        scaling = 1
        for t in scalings:
            scaling *= fractions.Fraction(t)
        return cls.from_duration(duration.from_string(dur), scaling)

    @classmethod
    def from_duration(cls, duration, scaling=1):
        """Convenience constructor to make a Duration from a duration and scaling value.

        An example::

            >>> from quickly.dom.lily import Duration
            >>> d = Duration.from_duration(1/4)
            >>> d.write()
            '4'
            >>> d = Duration.from_duration(1/4, 1/3)
            >>> d.write()
            '4*1/3'

        """
        n = cls(duration)
        if scaling != 1:
            n.append(DurationScaling(scaling))
        return n

    def duration(self):
        """Return the two-tuple(duration, scaling).

        The duration is simply our head value, the scaling is computed
        from a :class:`DurationScaling` child if present, or 1.

        """
        scaling = 1
        for s in self / DurationScaling:
            scaling *= s.head
        return self.head, scaling

    @classmethod
    def read_head(cls, origin):
        """Read the duration value from the origin tokens."""
        dur, *dots = origin
        return duration.from_string(dur.text, len(dots))

    def write_head(self):
        """Write back the duration fraction to a string like ``4.``"""
        return duration.to_string(self.head)


class DurationScaling(element.TextElement):
    """An optional scaling after a :class:`Duration`.

    E.g. ``*1/2``. May be read from multiple ``*n/m`` parts, but always outputs
    a single ``*n/d`` value, or ``*n`` when the denominator is 1. To the
    constructor any numerical value may be given, but the value is always
    represented as a fraction (omitting the denominator if 1).

    """
    def __init__(self, head, *children, **attrs):
        if not isinstance(head, fractions.Fraction):
            head = fractions.Fraction(head).limit_denominator()
        super().__init__(head, *children, **attrs)

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


class LyricItem(Durable):
    r"""Wrap a Scheme, String, Symbol or Markup in lyricmode.

    If it has no Scherm, String, Symbol or Markup child, a duration is
    required.

    """
    def child_order(self):
        yield (Scheme, String, Symbol, Markup), Duration, base.Comment

    @property
    def duration_required(self):
        """Duration is required if no visible child."""
        return not any(self / (Scheme, String, Symbol, Markup))


class LyricText(element.TextElement, Durable):
    r"""A word in lyric mode."""
    def child_order(self):
        yield Duration, base.Comment


class LyricExtender(element.HeadElement):
    r"""A lyric extender ``__``."""
    head = "__"
    # note: LilyPond >=2.20 allows a duration after a -- and __,
    # but it doesn't make much sense, so  we don't inherit Durable


class LyricHyphen(element.HeadElement):
    r"""A lyric hyphen ``--``."""
    head = "--"
    # note: LilyPond >=2.20 allows a duration after a -- and __
    # but it doesn't make much sense, so  we don't inherit Durable


class LyricSkip(element.HeadElement, Durable):
    r"""A lyric skip ``_``."""
    head = "_"
    def child_order(self):
        yield Duration, base.Comment


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


class Modifier(base.BackslashCommand):
    r"""A generic modifier that is not an articulation but added to
    the Articulations after a note.

    For example ``\noBeam``.

    The backslash is not in the head value.

    """

class RestModifier(element.HeadElement):
    r"""A ``\rest`` command after a note.

    Is a child of a Rest element that has a pitch name and possibly
    octave information instead of plain "r".

    """
    head = r'\rest'


class Fingering(element.TextElement):
    r"""A FingeringEvent."""


class Dynamic(base.BackslashCommand):
    r"""A dynamic symbol, like ``pp``."""


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
    space_after_head = " "
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
        r'\pageTurn':   'yes',
        r'\noPageTurn': 'no',
        r'\allowPageTurn': 'allow',
    }


class InStaffSegno(element.HeadElement, Music):
    r"""An ``\inStaffSegno`` command."""
    head = r'\inStaffSegno'


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
    space_after_head = space_between = " "
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
    space_after_head = space_between = space_after = " "
    head = r'\tweak'


class Tremolo(element.HeadElement):
    r"""A Tremolo (``:``) with an optional Duration child."""
    head = ":"


class Mode(base.BackslashCommand):
    r"""The mode subcommand of the ``\key`` statement."""


class Key(element.HeadElement, Music):
    r"""A \key statement.

    Must have a Pitch and a (Mode, IdentifierRef or Scheme) child.

    """
    space_after_head = space_between = ' '
    head = r"\key"

    def key_signature(self, processor, scope=None, wait=True):
        """Return a :class:`~.key.KeySignature` object for this key signature.

        The processor is a :class:`~.pitch.PitchProcessor`, which interprets
        the pitch language. ``scope`` and ``wait`` help (when the mode argument
        is a variable) finding its value in another file.

        """
        pitch = mode = None
        for n in self:
            while True:
                if isinstance(n, Pitchable):
                    pitch = processor.read_node(n)
                elif isinstance(n, Mode):
                    mode = n.head
                elif isinstance(n, IdentifierRef):
                    scope, n = n.get_value_with_scope(scope, wait)
                    continue
                elif isinstance(n, Scheme):
                    for n in n // scm.List:
                        mode = [n.head for n in n / scm.Number]
                break
        if pitch and mode:
            from ..key import KeySignature
            return KeySignature(pitch.note, pitch.alter, mode)

    def signatures(self):
        yield Pitchable, (Mode, IdentifierRef, Scheme)

    def add_argument(self, node):
        """Reimplemented to turn an added Note argument into a Pitch."""
        if isinstance(node, Note) and sum(1 for n in self / Pitchable) < 1:
            node = node.to_pitch()
        return super().add_argument(node)


class Clef(element.HeadElement, Music):
    r"""A ``\clef`` statement.

    Must have a Symbol or String child indicating the clef type.

    """
    space_after_head = " "
    head = r"\clef"

    def signatures(self):
        yield (Symbol, String),


class Time(element.HeadElement, Music):
    r"""A ``\time`` statement.

    Has an optional List child and a Fraction child.

    """
    space_after_head = " "
    head = r"\time"

    def signatures(self):
        yield List, Fraction
        yield Fraction,


class Partial(_ConvertUnpitchedToDuration, element.HeadElement, Music):
    r"""A ``\partial`` statement.

    Has a Duration child.

    """
    space_after_head = " "
    head = r"\partial"

    def signatures(self):
        yield Duration,
        yield Unpitched,


class Times(element.HeadElement, Music):
    r"""A ``\times`` statement.

    Has a Fraction child and a Music child.
    The ``\times`` command is not documented anymore in LilyPond, but also
    not deprecated. Using ``\tuplet`` is recommended.

    """
    space_after_head = space_between = " "
    head = r"\times"

    def transform(self):
        """Return a transform to scale durations of child nodes."""
        for n in self / Fraction:
            return duration.Transform(scale=n.fraction())

    def signatures(self):
        yield Fraction, MUSIC


class Tuplet(_ConvertUnpitchedToDuration, element.HeadElement, Music):
    r"""A ``\tuplet`` statement.

    Has a Fraction child, an optional Duration child and a Music child.

    """
    space_after_head = space_between = " "
    head = r"\tuplet"

    def transform(self):
        """Return a transform to scale durations of child nodes."""
        for n in self / Fraction:
            return duration.Transform(scale=1/n.fraction())

    def signatures(self):
        yield Fraction, Duration, MUSIC
        yield Fraction, Unpitched, MUSIC
        yield Fraction, MUSIC


class ScaleDurations(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""A ``\scaleDurations`` command.

    Has a Fraction child and a Music child.

    """
    space_after_head = space_between = " "
    head = r"\scaleDurations"

    def transform(self):
        """Return a transform to scale durations of child nodes."""
        for value in filter_map(get_num_value, self):
            return duration.Transform(scale=value)

    def signatures(self):
        yield (Fraction, Int, Unpitched, Scheme), MUSIC


class ShiftDurations(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""A ``\shiftDurations`` command.

    Has two Scheme children and a Music child.

    """
    space_after_head = space_between = " "
    head = r"\shiftDurations"

    def transform(self):
        """Return a transform to scale durations of child nodes."""
        nums = filter_map(get_int_value, self)
        for log in nums:
            for dotcount in nums:
                return duration.Transform(log, dotcount)

    def signatures(self):
        yield NUMBER, NUMBER, MUSIC


class Grace(element.HeadElement, Music):
    r"""A ``\grace`` command.

    Has a Music child.

    """
    space_after_head = " "
    head = r"\grace"

    def transform(self):
        """Return a transform to scale durations of child nodes to 0."""
        return duration.Transform(scale=0)

    def signatures(self):
        yield MUSIC,


class Acciaccatura(Grace):
    r"""An ``\acciaccatura`` command.

    Has a Music child.

    """
    head = r"\acciaccatura"


class Appoggiatura(Grace):
    r"""An ``\appoggiatura`` command.

    Has a Music child.

    """
    head = r"\appoggiatura"


class SlashedGrace(Grace):
    r"""A ``\slashedGrace`` command.

    Has a Music child.

    """
    head = r"\slashedGrace"


class AfterGrace(element.HeadElement, Music):
    r"""An ``\afterGrace`` command.

    Has an optional Fraction and two Music children. The second music
    expression is the grace music and has length 0, the fraction is multiplied
    with the duration of the first music expression and determines the moment
    the grace music is displayed.

    The default fraction (if not specified) is in the toplevel
    ``afterGraceFraction`` variable or 3/4.

    """
    space_after_head = space_between = " "
    head = r"\afterGrace"

    def time_length(self, context, end=None):
        """Return the length of this expression, using a :class:`~.time.TimeContext`
        handler.

        Reimplemented to skip the second child music expression.

        """
        for n in self[:end]:
            if isinstance(n, Music):
                return context.length(n)
        return 0

    def signatures(self):
        yield Fraction, MUSIC, MUSIC
        yield MUSIC, MUSIC


class PartCombine(element.HeadElement, Music):
    r"""The ``\partcombine`` command, with two Music arguments."""
    space_after_head = space_between = " "
    head = r"\partcombine"

    def signatures(self):
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
    space_after = '\n'

    @classmethod
    def read_head(cls, origin):
        return ''.join(t.text for t in origin[1:])

    def write_head(self):
        return '%{}'.format(self.head)


class Markup(base.BackslashCommand):
    r"""A ``\markup``, ``\markuplines`` or ``\markuplist`` expression.

    When manually constructing a Markup, the backslash is not needed.

    """
    space_before = ""
    space_after = " "
    space_between = space_after_head = " "


class MarkupWord(element.TextElement):
    """A word in markup mode."""
    space_before = space_after = " "


class MarkupList(element.BlockElement):
    """A bracketed markup expression, like ``{`` ... ``}``."""
    space_after_head = space_before_tail = space_between = " "
    head = "{"
    tail = "}"

    def indent_align_indices(self):
        """How to align child nodes if on the same line as an indenting char."""
        yield 0


class MarkupCommand(base.BackslashCommand, Reference):
    r"""A markup command, like ``\bold <arg>``.

    When manually constructing a MarkupCommand, the backslash is not needed.

    """
    space_after_head = space_before_tail = space_between = " "

    def get_name(self):
        """The name of the markup command. This is used when looking up
        the definition of a custom markup command.

        """
        return self.head


class MarkupScore(Score):
    r"""A ``\score`` in Markup."""
    space_after_head = space_before_tail = space_between = " "


class MarkupScoreLines(MarkupScore):
    r"""A ``\score-lines`` in Markup."""
    head = r"\score-lines {"


class Figure(Music):
    """A bass figure in figure mode.

    Always has one FigureBody child, which contains the numbers etc.
    Can also have a duration child.

    """


class FigureBody(element.BlockElement):
    r"""One ``<`` ... ``>`` figure "chord" in figuremode.

    Always the child of a Figure element, which can have a duration.

    """
    space_between = " "
    head = '<'
    tail = '>'


class FigureBracket(element.BlockElement):
    r"""One ``[`` ... ``]`` bracketed set of figures in figuremode."""
    space_between = " "
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
    space_after_head = space_between = " "
    head = r'\accepts'

    def signatures(self):
        yield (String, Symbol),


class Denies(element.HeadElement):
    r"""The ``\denies`` command."""
    space_after_head = space_between = " "
    head = r'\denies'

    def signatures(self):
        yield (String, Symbol),


class Name(element.HeadElement):
    r"""The ``\name`` command."""
    space_after_head = space_between = " "
    head = r'\name'

    def signatures(self):
        yield (String, Symbol),


class Alias(element.HeadElement):
    r"""The ``\alias`` command."""
    space_after_head = space_between = " "
    head = r'\alias'

    def signatures(self):
        yield (String, Symbol),


class Consists(element.HeadElement):
    r"""The ``\consists`` command."""
    space_after_head = space_between = " "
    head = r'\consists'

    def signatures(self):
        yield (String, Symbol, Scheme),


class Remove(element.HeadElement):
    r"""The ``\remove`` command."""
    space_after_head = space_between = " "
    head = r'\remove'

    def signatures(self):
        yield (String, Symbol, Scheme),


class DefaultChild(element.HeadElement):
    r"""The ``\defaultchild`` command."""
    space_after_head = space_between = " "
    head = r'\defaultchild'

    def signatures(self):
        yield (String, Symbol),


class Omit(element.HeadElement, Music):
    r"""The ``\omit`` command."""
    space_after_head = space_between = " "
    head = r'\omit'

    def signatures(self):
        yield SYMBOL,


class Hide(element.HeadElement, Music):
    r"""The ``\hide`` command."""
    space_after_head = space_between = " "
    head = r'\hide'

    def signatures(self):
        yield SYMBOL,


class Undo(element.HeadElement, Music):
    r"""The ``\undo`` command."""
    space_after_head = space_between = " "
    head = r'\undo'

    def signatures(self):
        yield MUSIC,


class Once(element.HeadElement, Music):
    r"""The ``\once`` command."""
    space_after_head = space_between = " "
    head = r'\once'

    def signatures(self):
        yield MUSIC,


class Temporary(element.HeadElement, Music):
    r"""The ``\temporary`` command."""
    space_after_head = space_between = " "
    head = r'\temporary'

    def signatures(self):
        yield MUSIC,


class Override(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""The ``\override`` command."""
    space_after_head = space_between = " "
    head = r'\override'

    def signatures(self):
        yield SYMBOL, EqualSign, VALUE
        yield SYMBOL, Scheme, EqualSign, VALUE
        yield SYMBOL, Scheme, Scheme, EqualSign, VALUE
        yield SYMBOL, Scheme, Scheme, Scheme, EqualSign, VALUE
        yield SYMBOL, Scheme, Scheme, Scheme, Scheme, EqualSign, VALUE


class Revert(element.HeadElement, Music):
    r"""The ``\revert`` command."""
    space_after_head = space_between = " "
    head = r'\revert'

    def signatures(self):
        yield SYMBOL,
        yield SYMBOL, Scheme
        yield SYMBOL, Scheme, Scheme
        yield SYMBOL, Scheme, Scheme, Scheme
        yield SYMBOL, Scheme, Scheme, Scheme, Scheme


class Set(_ConvertUnpitchedToInt, element.HeadElement, Music):
    r"""The ``\set`` command."""
    space_after_head = space_between = " "
    head = r'\set'

    def signatures(self):
        yield SYMBOL, EqualSign, VALUE


class Unset(element.HeadElement, Music):
    r"""The ``\unset`` command."""
    space_after_head = space_between = " "
    head = r'\unset'

    def signatures(self):
        yield SYMBOL,


class Version(element.HeadElement, Music):
    r"""The ``\version`` command."""
    space_after_head = space_between = " "
    head = r'\version'

    @property
    def version(self):
        """The version number, as a tuple of ints (may be empty)."""
        for s in self/String:
            return tuple(map(int, re.findall(r'\d+', s.head)))
        return ()

    @version.setter
    def version(self, version):
        version = '.'.join(map(str, version))
        for s in self/String:
            s.head = version
            break
        else:
            self.insert(0, String(version))

    def signatures(self):
        yield String,


class Language(element.HeadElement):
    r"""The ``\language`` command.

    Has a :class:`String` child with the language name, which can be
    conveniently edited via the :attr:`language` attribute.

    """
    space_after_head = space_between = " "
    head = r'\language'

    def signatures(self):
        yield String,

    def repr_head(self):
        return repr(self.language)

    @property
    def language(self):
        """The language."""
        for n in self / String:
            return n.head

    @language.setter
    def language(self, language):
        for n in self / String:
            n.head = language
            return
        self.insert(0, String(language))


class Include(element.HeadElement):
    r"""The ``\include`` command.

    You can use the :attr:``language`` attribute, assuming that the included
    file is a language definition file. If the :attr:`filename` is not
    recognized as a language definition file, the property will return None.

    """
    space_after_head = space_between = " "
    head = r'\include'

    def signatures(self):
        yield String,

    def repr_head(self):
        return repr(self.filename)

    @property
    def filename(self):
        """The filename."""
        for n in self / String:
            return n.head

    @filename.setter
    def filename(self, value):
        for n in self / String:
            n.head = value
            return
        self.insert(0, String(value))

    @property
    def language(self):
        """The language, if the filename refers to a known language definition.

        Setting the attribute appends the ``".ly"`` automatically.

        """
        from .. import pitch
        filename = self.filename
        if filename.endswith(".ly"):
            language = filename[:-3]
            if language in pitch.pitch_names:
                return language

    @language.setter
    def language(self, language):
        self.filename = language + ".ly"


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
    space_after_head = space_between = " "
    head = r'\shape'

    def signatures(self):
        yield Scheme, SYMBOL


class VShape(Shape):
    r"""The ``\vshape`` command.

    Like ``\shape`` but draws the control points.

    """
    head = r'\vshape'


class StringTuning(element.HeadElement):
    r"""The ``\stringTuning`` command, with one Chord argument."""
    space_after_head = space_between = " "
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



### Helper classes and functions

class Lookup:
    """Helper class to find definitions and other stuff in a lily.Document from
    the viewpoint of a ``node``.

    A :class:`~.scope.Scope`, if given using the ``scope`` parameter, is used
    to resolve include files. If no scope is given, only searches the current
    DOM document; the yielded scope is then always None.

    If a scope is given, include commands are followed and ``wait`` determines
    whether to wait for ongoing transformations of external DOM documents. If
    wait is False, and a transformation is not yet finished the included
    document's toplevel nodes will not be yielded.

    """
    def __init__(self, node, scope=None, wait=True):
        self.node = node
        self.scope = scope
        self.wait = wait

    def __repr__(self):
        return "<{} node={} scope={} wait={}>".format(
            type(self).__name__, self.node, self.scope, self.wait)

    def ancestors(self):
        """Yield the ancestors with index of node that should be searched for
        possible definitions.

        The default implementation yields ancestors that inherit
        HandleAssignments and stops at the Document node.

        """
        for node, index in self.node.ancestors_with_index():
            if isinstance(node, HandleAssignments):
                yield node, index
            if isinstance(node, Document):
                break

    def preceding_nodes(self):
        r"""Yield preceding nodes in ancestors and toplevel, in backward
        direction, as two-tuples (node, scope).

        If a scope was given on instantiation, included files are followed.

        When the beginning of the current scope (document) is reached,
        continues the search in parent scopes (if a scope was given), and if
        that parent scope has a node pointer, continues the search from there.
        This is useful when an included file refers to a variable that was set
        in the parent document before the ``\include`` command.

        So when ``file_a.ly`` reads::

            music = { c }
            \include "file_b.ly"

        And ``file_b.ly`` only contains::

            \new Score { \music }

        When traversing the musical contents of file a, the value of the
        ``\music`` Reference in file b is correctly found in file a.

        """
        scope = self.scope
        if scope:
            lookup = self
            while True:
                for p, i in lookup.ancestors():
                    stack = []
                    gen = reversed(p[:i])
                    while True:
                        for n in gen:
                            if isinstance(n, Include):
                                new_scope = scope.include_scope(n.filename, n)
                                if new_scope:
                                    dom = new_scope.document().get_transform(lookup.wait)
                                    if isinstance(dom, Document):
                                        stack.append((scope, gen))
                                        scope = new_scope
                                        gen = reversed(dom)
                                        break
                            yield n, scope
                        else:
                            if stack:
                                scope, gen = stack.pop()
                            else:
                                break
                if scope.parent and scope.node:
                    lookup = type(self)(scope.node, scope.parent, self.wait)
                    scope = scope.parent
                else:
                    break
        else:
            for p, i in self.ancestors():
                for n in reversed(p[:i]):
                    yield n, None

    def find_assignment(self, name):
        """Find an Assignment from here, with name ``name``.

        If found, return its value and the scope.

        """
        for node, scope in self.preceding_nodes():
            if isinstance(node, Assignment) and node.get_name() == name:
                return node.get_value(), scope


def is_music(node):
    """Return True if the node is an instance of Music."""
    return isinstance(node, Music)


def is_symbol(text):
    """Return True if text is a valid LilyPond symbol."""
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


def duration_getter():
    """Return a callable that returns the (duration, scaling) tuple of a
    :class:`Durable`.

    If the durable does not have a Duration child, the callable searches
    backwards until a Durable is found that has a duration that LilyPond would
    use for the current durable. All found durables without duration are
    cached, so the next request only needs at most to search back one durable.
    If no durable with a value is found, ``(Fraction(1, 4), 1)`` is returned.

    Use this getter if you are not sure you really iterate over all the
    durables in a node and cannot keep track of the previous durable yourself.

    Get a new getter if you also modify durations.

    """
    durables = set()
    duration = None

    def get_duration(durable):
        """Return the tuple (duration, scaling) of the Durable."""
        nonlocal durables, duration

        dur = durable.duration_scaling
        if dur:
            return dur
        elif durable in durables:
            return duration

        new = {durable}
        for prev in durable < Durable:
            if prev.duration_sets_previous:
                dur = prev.duration_scaling
                if dur:
                    durables = new
                    duration = dur
                    return dur
                elif prev in durables:
                    durables.update(new)
                    return duration
                new.add(prev)
        durables = new
        duration = (fractions.Fraction(1, 4), 1)
        return duration

    return get_duration


def previous_duration(node):
    """Return a two-tuple(duration, scaling) of the closest preceding Durable
    that has a duration that LilyPond would use if the current node had no
    duration.

    If no such node was found, returns ``(Fraction(1, 4), 1)``.

    This function is potentially slow, as it searches backwards for a Durable
    node. Don't use it if you have the opportunity to keep track of the
    previous duration yourself (from a :class:`Durable` that has the
    :attr:`~Durable.duration_sets_previous` attribute set to True).

    You can also use a :func:`duration_getter`, which optimizes for adjacent
    notes without duration.

    """
    for n in node < Durable:
        if n.duration_sets_previous:
            for d in n / Duration:
                return d.duration()
    return fractions.Fraction(1, 4), 1


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
    """Get the Python value from an Element node.

    Returns:

    * bool, int, float etc for a Scheme('#', scm.Bool(value) or scm.Number(value)) node
    * int for an Int node
    * float for a Float node
    * Fraction for a Fraction node
    * str for a String, Symbol or scm.String node
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
    elif isinstance(node, Fraction):
        return node.fraction()
    elif isinstance(node, Scheme):
        if len(node) == 1:
            node = node[0]
            if isinstance(node, (scm.Bool, scm.Number, scm.String)):
                return node.value


def get_num_value(node):
    """Get a numerical value from a node, if possible, else None."""
    if isinstance(node, (Int, Float)):
        return node.head
    elif isinstance(node, Fraction):
        return node.fraction()
    elif isinstance(node, Scheme):
        if len(node) == 1:
            if isinstance(node[0], scm.Number):
                return node[0].head


def get_int_value(node):
    """Get a integer value from a node, if possible, else None."""
    if isinstance(node, Int):
        return node.head
    elif isinstance(node, Float) and node.head.is_integer():
        return int(node.head)
    elif isinstance(node, Scheme):
        if len(node) == 1:
            if isinstance(node[0], scm.Number):
                v = node[0].head
                if isinstance(v, int):
                    return v
                if isinstance(v, float) and v.is_integer():
                    return int(v)


def filter_map(func, iterable):
    """Call func on every item in iterable and yield the result value if not
    None.

    Equivalent to::

        filter(lambda r: r is not None, map(func, iterable))

    """
    return filter(lambda r: r is not None, map(func, iterable))



# often used signatures:
MUSIC = (Music, IdentifierRef, Etc)
VALUE = (List, String, Scheme, Number, Markup, IdentifierRef, Etc, Unpitched)
SYMBOL = (List, Symbol, String)
TEXT = (List, Symbol, String, Markup, IdentifierRef, Etc)
NUMBER = (Scheme, Number, Unpitched)
INT = (Int, IdentifierRef, Scheme)
