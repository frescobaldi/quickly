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
LilyPond language and transform definition
"""

import itertools

from parce.transform import Transform
import parce.lang.lilypond
import parce.action as a
from parce.util import Dispatcher

from quickly.dom import base, element, lily, scm


def _head_mapping(*element_types):
    """Return a dictionary mapping head text to element type.

    The element types must be HeadElement instances with a fixed head attribute.

    """
    return dict((cls.head, cls) for cls in element_types)


def _spanner_start_stop_mapping(*element_types):
    """Return a dictionary mapping ``spanner_start`` and ``spanner_stop``
    to an element type.

    The element types must inherit TextElement.

    """
    d = {}
    for cls in element_types:
        d[cls.spanner_start] = cls
        d[cls.spanner_stop] = cls
    return d


def _toggle_mapping(*element_types):
    """Return a dictionary mapping ``toggle_on`` and ``toggle_of``
    to an element type.

    The element types must inherit TextElement.

    """
    d = {}
    for cls in element_types:
        d[cls.toggle_on] = cls
        d[cls.toggle_off] = cls
    return d


class LilyPond(parce.lang.lilypond.LilyPond):
    """LilyPond language definition."""
    @classmethod
    def get_scheme_target(cls):
        """Get *our* Scheme."""
        from .scheme import Scheme
        return Scheme.scheme


class LilyPondTransform(Transform):
    """Transform LilyPond to Music."""

    ## transforming methods
    def root(self, items):
        """Concatenate all nodes in a Document object."""
        return lily.Document(*self.handle_assignments(self.create_music(items)))

    def book(self, items):
        """Create a Book or BookPart node."""
        element_class = lily.BookPart if items[1] == r'\bookpart' else lily.Book
        tail = (items.pop(),) if items[-1] == '}' else ()
        head = items[:2]
        return self.factory(element_class, head, tail, *self.create_music(items[2:]))

    def score(self, items):
        """Create a Score node (can also appear inside Markup and MarkupList)."""
        tail = (items.pop(),) if items[-1] == '}' else ()
        head = items[:2]
        return self.factory(lily.Score, head, tail, *self.create_music(items[2:]))

    def header(self, items):
        """Create a Header node."""
        return self.create_block(lily.Header, items)

    def paper(self, items):
        """Create a Paper node."""
        return self.create_block(lily.Paper, items)

    def layout(self, items):
        """Create a Layout node."""
        tail = (items.pop(),) if items[-1] == '}' else ()
        head = items[:2]
        return self.factory(lily.Layout, head, tail,
            *self.handle_assignments(self.create_music(items[2:])))

    def midi(self, items):
        """Create a Midi node."""
        tail = (items.pop(),) if items[-1] == '}' else ()
        head = items[:2]
        return self.factory(lily.Midi, head, tail,
            *self.handle_assignments(self.create_music(items[2:])))

    def layout_context(self, items):
        """Create a With or LayoutContext node."""
        element_class = lily.With if items[0] == r'\with' else lily.LayoutContext
        return self.create_block(element_class, items)

    def musiclist(self, items):
        """Create a SequentialMusic (``{`` ... ``}``) or SimultaneousMusic
        (``<<`` ... ``>>``) node.

        """
        head = items[:1]
        tail = (items.pop(),) if items[-1] in ('}', '>>') else ()
        element_class = lily.MusicList if items[0] == '{' else lily.SimultaneousMusicList
        return self.factory(element_class, head, tail, *self.create_music(items[1:]))

    def chord(self, items):
        """Create a Chord node (``<`` ... ``>``)."""
        head = items[:1]
        tail = (items.pop(),) if items[-1] == '>' else ()
        return self.factory(lily.Chord, head, tail, *self.create_music(items[1:]))

    def repeat(self, items):
        """Contents of ``repeat`` context."""
        return list(self.common(items))

    def script(self, items):
        """Contains one Fingering or Articulation event."""
        if items[0].action is a.Literal.Number.Fingering:
            return self.factory(lily.Fingering, items)
        return self.factory(lily.Articulation, items)

    def pitch(self, items):
        """Octave, Accidental and OctaveCheck after a note name.

        Returns a list of elements.

        """
        def gen():
            for i in items:
                if i.is_token:
                    yield self._pitch(i.action, i)
                else:
                    yield i.obj # can only be a comment
        return list(gen())

    def duration(self, items):
        """Dots after a duration, can include scaling.

        Returns (dots, scaling), where dots is a list of Dot tokens and
        scaling a DurationScaling node.

        """
        dots = []
        scaling = None
        for i in items:
            if i == '.':
                dots.append(i)
            elif not i.is_token and i.name == 'duration_scaling':
                scaling = i.obj
        return dots, scaling

    def duration_scaling(self, items):
        """Scaling after a duration."""
        return self.factory(lily.DurationScaling, items)

    def lyricmode(self, items):
        """Contents of ``lyricmode`` context."""
        return list(self.create_music(items))

    def lyricsto(self, items):
        """Contents of ``lyricsto`` context."""
        return list(self.common(items))

    def lyriclist(self, items):
        """Return a ``{`` ... ``}`` or ``<<`` ... ``>>`` construct in lyricmode."""
        return self.musiclist(items)

    def drummode(self, items):
        """Contents of ``drummode`` context."""
        return list(self.create_music(items))

    def drumlist(self, items):
        """Return a ``{`` ... ``}`` or ``<<`` ... ``>>`` construct in drummode."""
        return self.musiclist(items)

    def chordmode(self, items):
        """Contents of ``chordmode`` context."""
        return list(self.create_music(items))

    def chordlist(self, items):
        """Return a ``{`` ... ``}`` or ``<<`` ... ``>>`` construct in chordmode."""
        return self.musiclist(items)

    def chord_modifier(self, items):
        """Contents of ``chord_modifier`` context."""
        items = iter(items)
        nodes = []
        for i in items:
            if i.is_token:
                if i.action is a.Name.Symbol:
                    # a modifier, such as 'maj'
                    nodes.append(self.factory(lily.Qualifier, (i,)))
                elif i.action is a.Number:
                    step = self.factory(lily.Step, (i,))
                    if i.group == 0:
                        alteration = self.factory(lily.Alteration, (next(items),))
                        step.append(alteration)
                    nodes.append(step)
                elif i.action is a.Separator.Dot:
                    nodes.append(self.factory(lily.Separator, (i,)))
            else:
                nodes.append(i.obj)     # can only be comment
        return nodes

    def notemode(self, items):
        """Contents of ``notemode`` context."""
        return list(self.create_music(items))

    def figuremode(self, items):
        """Contents of ``notemode`` context."""
        return list(self.create_music(items))

    def figurelist(self, items):
        """Return a ``{`` ... ``}`` construct in figuremode."""
        return self.musiclist(items)

    def figure(self, items):
        """Return a Figure element."""
        head = items[:1]
        tail = (items.pop(),) if items[-1] == '>' else ()
        return self.factory(lily.Figure, head, tail, *self.create_figure(items))

    def figurebracket(self, items):
        """Return a FigureBracket element."""
        head = items[:1]
        tail = (items.pop(),) if items[-1] == ']' else ()
        return self.factory(lily.FigureBracket, head, tail, *self.create_figure(items))

    def _list_nodes(self, items):
        """Yield element nodes for List, Identifier or IdentifierRef."""
        for i in items:
            if i.is_token:
                yield self._id(i.action, i) # String, Int, Symbol, Separator
            else:
                yield i.obj # can be a SchemeExpression or String

    def list(self, items):
        """A list of numbers, symbols, strings and scheme expressions.

        Returns a List, String, Int, Symbol, or SchemeExpression element.

        """
        nodes = list(self._list_nodes(items))
        return nodes[0] if len(nodes) == 1 else lily.List(*nodes)

    start_list = None   # lexicon never creates tokens

    def identifier(self, items):
        """Return an Identifier item."""
        return lily.Identifier(*self._list_nodes(items))

    def identifier_ref(self, items):
        """Return an IdentifierRef item."""
        node = self.factory(lily.IdentifierRef, items[:1])
        node.extend(self._list_nodes(items[1:]))
        return node

    def markup(self, items):
        """Simply return the flattened contents, the markup will be constructed later."""
        result = []
        for i in items:
            if i.is_token or i.name != "markup":
                result.append(i)
            else:
                result.extend(i.obj)
        return result

    def markuplist(self, items):
        """Create a MarkupList node."""
        head = items[:1]
        tail = (items.pop(),) if items[-1] == '}' else ()
        return self.factory(lily.MarkupList, head, tail, *self.read_markup_arguments(items[1:]))

    def markupscore(self, items):
        """Create a MarkupScore node."""
        tail = (items.pop(),) if items[-1] == '}' else ()
        head = items[:2]
        cls = lily.MarkupScoreLines if items[0] == r'\score-lines' else lily.MarkupScore
        return self.factory(cls, head, tail, *self.create_music(items[2:]))

    def schemelily(self, items):
        head = items[:1]
        tail = (items.pop(),) if items[-1] == '#}' else ()
        return self.factory(scm.LilyPond, head, tail, *self.common(items[1:]))

    def string(self, items):
        """Create a String node."""
        return self.factory(lily.String, items)

    def multiline_comment(self, items):
        """Create a MultilineComment node."""
        return self.factory(lily.MultilineComment, items)

    def singleline_comment(self, items):
        """Create a SinglelineComment node."""
        return self.factory(lily.SinglelineComment, items)

    ## helper methods and factory
    def factory(self, element_class, head_origin, tail_origin=(), *children):
        """Create an Element, keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All elements should be created using this method, so
        that it can be overridden for the case you don't want to remember the
        origin.

        """
        return element_class.with_origin(tuple(head_origin), tuple(tail_origin), *children)

    def common(self, items):
        """Find comment, string, scheme, markup and common tokens.

        Yields Element objects.

        """
        items = iter(items)
        for i in items:
            if i.is_token:
                result = self._action(i.action, i)
                if result:
                    yield result
            elif isinstance(i.obj, element.Element):
                yield i.obj
            elif i.name == "markup":
                yield from self.create_markup(i.obj, items)

    def handle_assignments(self, nodes):
        """Handle assignments that occur in the Element nodes.

        If a Identifier is encountered and then an EqualSign, it is turned
        into an Assignment.

        Needed at toplevel and in blocks.

        """
        nodes = iter(nodes)
        for n in nodes:
            if isinstance(n, lily.Identifier):
                variable = [n]
                equalsign = False
                for n in nodes:
                    variable.append(n)
                    if not isinstance(n, base.Comment):
                        if equalsign:
                            # gotcha!!
                            yield lily.Assignment(*variable)
                            break
                        elif isinstance(n, lily.EqualSign):
                            equalsign = True
                        else:
                            yield from variable
                            break
                else:
                    yield from variable
            else:
                yield n

    def create_block(self, element_class, items):
        r"""Return a tree tuple(head_origin, nodes, tail_origin) for the items.

        The items are the contents of a block like ``\book { }``.
        The ``head_origin`` are the first two tokens, the ``tail_origin`` the
        last token, if that is a '``}``'.

        """
        tail_origin = (items.pop(),) if items[-1] == '}' else ()
        head_origin = items[:2]
        return self.factory(element_class, head_origin, tail_origin,
            *self.handle_assignments(element.build_tree(self.common(items[2:]))))

    def create_markup(self, markup, items):
        """Yield zero or one Markup element.

        ``markup`` is the result list of :meth:`markup`, and ``items`` is the
        iterable from which more arguments are read. If there is no single
        argument, nothing is yielded.

        """
        origin = markup[:1]     # the \markup or \markuplist command
        for mkup in self.read_markup_arguments(itertools.chain(markup[1:], items)):
            yield self.factory(lily.Markup, origin, (), mkup)
            break

    def read_markup_arguments(self, items):
        """Read from items and yield nodes that can occur in markup."""
        items = iter(items)
        for i in items:
            if i.is_token:
                if i.action is a.Text:
                    yield self.factory(lily.MarkupWord, (i,))
                elif i.action in a.Name.Function:
                    nargs = self.get_markup_argument_count(i.text[1:])
                    args = []
                    if nargs:
                        for arg in self.read_markup_arguments(items):
                            args.append(arg)
                            if not isinstance(arg, base.Comment):
                                nargs -= 1
                            if nargs == 0:
                                break
                    yield self.factory(lily.MarkupCommand, (i,), (), *args)
            elif isinstance(i.obj, element.Element):
                yield i.obj

    def get_markup_argument_count(self, command):
        r"""Return the number of arguments of the markup command (without ``\``).

        Re-implement this method if you want to add your own markup commands.
        The default implementation consults :meth:`LilyPond.get_markup_argument_count`.

        """
        return LilyPond.get_markup_argument_count(command)

    def create_figure(self, items):
        """Yield nodes to be added in a Figure."""
        step = None
        items = iter(items)
        for i in items:
            if i.is_token:
                if i.action is a.Text.Music.Pitch.Figure:
                    if step:
                        yield step
                    cls = lily.FigureSkip if i == '_' else lily.FigureStep
                    step = self.factory(cls, (i,))
                elif i.action is a.Text.Music.Pitch.Accidental:
                    if step:
                        step.append(self.factory(lily.FigureAccidental, (i,)))
                elif i.action is a.Literal.Character.Alteration:
                    if step:
                        step.append(self.factory(lily.FigureAlteration, (i,)))
            elif i.name == "markup":
                if step:
                    yield step
                for step in self.create_markup(i.obj, items):
                    break
                else:
                    step = None
            elif isinstance(i.obj, element.Element):
                if step:
                    yield step
                step = i.obj
        if step:
            yield step

    def create_music(self, items):
        """Read music from items and yield Element nodes."""
        return element.build_tree(iter(MusicBuilder(self, items)), ignore_type=base.Comment)

    # dispatchers for common types
    _pitch = Dispatcher()
    _action = Dispatcher()
    _keyword = Dispatcher()

    @Dispatcher
    def _id(self, action, token):
        """Dispatches for identifiers. By default, return a Symbol."""
        return self.factory(lily.Symbol, (token,))

    @_id(a.Number)
    @_action(a.Number)
    def number_action(self, token):
        r"""Called for ``Number``."""
        return self.factory(lily.Int, (token,))

    @_id(a.Separator)
    def separator_action(self, token):
        r"""Called for ``Delimiter.Separator``."""
        return self.factory(lily.Separator, (token,))

    @_action(a.Number.Float)
    def float_action(self, token):
        r"""Called for ``Number.Float``."""
        return self.factory(lily.Float, (token,))

    @_action(a.Number.Fraction)
    def fraction_action(self, token):
        r"""Called for ``Number.Fraction``."""
        return self.factory(lily.Fraction, (token,))

    @_action(a.Operator.Assignment)
    def assignment_action(self, token):
        r"""Called for ``Operator.Assignment``."""
        return self.factory(lily.EqualSign, (token,))

    @_action(a.Keyword)
    def keyword_action(self, token):
        r"""Called for ``Keyword``."""
        return self._keyword(token.text, token)

    @_action(a.Name.Type)
    def name_type_action(self, token):
        r"""Called for ``Name.Type``(repeat mode)."""
        return self.factory(lily.Symbol, (token,))

    @_pitch(a.Text.Music.Pitch.Octave)
    def pitch_octave_action(self, token):
        r"""Called for ``Text.Music.Pitch.Octave``."""
        return self.factory(lily.Octave, (token,))

    @_pitch(a.Text.Music.Pitch.Octave.OctaveCheck)
    def pitch_octavecheck_action(self, token):
        r"""Called for ``Text.Music.Pitch.Octave.OctaveCheck``."""
        return self.factory(lily.OctaveCheck, (token,))

    @_pitch(a.Text.Music.Pitch.Accidental)
    def pitch_accidental_action(self, token):
        r"""Called for ``Text.Music.Pitch.Accidental``."""
        return self.factory(lily.Accidental, (token,))

    @_keyword(r'\accepts')
    def keyword_accepts(self, token):
        r"""Called for Keyword ``\accepts``."""
        return self.factory(lily.Accepts, (token,))

    @_keyword(r'\denies')
    def keyword_denies(self, token):
        r"""Called for Keyword ``\denies``."""
        return self.factory(lily.Denies, (token,))

    @_keyword(r'\name')
    def keyword_name(self, token):
        r"""Called for Keyword ``\name``."""
        return self.factory(lily.Name, (token,))

    @_keyword(r'\alias')
    def keyword_alias(self, token):
        r"""Called for Keyword ``\alias``."""
        return self.factory(lily.Alias, (token,))

    @_keyword(r'\consists')
    def keyword_consists(self, token):
        r"""Called for Keyword ``\consists``."""
        return self.factory(lily.Consists, (token,))

    @_keyword(r'\remove')
    def keyword_remove(self, token):
        r"""Called for Keyword ``\remove``."""
        return self.factory(lily.Remove, (token,))

    @_keyword(r'\defaultchild')
    def keyword_defaultchild(self, token):
        r"""Called for Keyword ``\defaultchild``."""
        return self.factory(lily.DefaultChild, (token,))


class LilyPondAdHocTransform(LilyPondTransform):
    """LilyPondTransform that does not keep the origin tokens.

    This is used to create pieces (nodes) of a LilyPond document from text, and
    then use that pieces to compose a larger Document or to edit an existing
    document. It is undesirable that origin tokens then would mistakenly be
    used as if they originated from the document that's being edited.

    """
    def factory(self, element_class, head_origin, tail_origin=(), *children):
        """Create an Item *without* keeping its origin.

        The ``head_origin`` and optionally ``tail_origin`` is an iterable of
        Token instances. All items should be created using this method, so that
        it can be overridden for the case you don't want to remember the
        origin.

        """
        return element_class.from_origin(tuple(head_origin), tuple(tail_origin), *children)


class MusicBuilder:
    """Helper class that reads and builds music.

    An instance of MusicBuilder is created and used in
    :meth:`LilyPondTransform.create_music`.

    """

    _token = Dispatcher()
    _action = Dispatcher()
    _keyword = Dispatcher()
    _context = Dispatcher()

    def __init__(self, transform, items):
        self.transform = transform
        self.factory = transform.factory
        self.items = iter(items)

        self._music = None
        self._duration = None
        self._scaling = None
        self._chord_modifiers = []
        self._events = []         # for direction and spanner-id
        self._articulations = []
        self._comments = []       # for comments between pitch and duration...

    def pending_music(self):
        """Yield pending music."""
        music = self._music
        if self._duration:
            dur = self.factory(lily.Duration, self._duration)
            if self._scaling:
                dur.append(self._scaling)
            if music:
                if music.tail:
                    music = lily.Music(music)
                music.append(dur)
            else:
                music = lily.Unpitched(dur)
        if music:
            if self._chord_modifiers:
                if music.tail:
                    music = lily.Music(music)
                music.append(lily.ChordModifiers(*self._chord_modifiers))
                self._chord_modifiers.clear()
                # move comments at end of chord modifiers back to toplevel
                while len(music[-1][-1]) and isinstance(music[-1][-1][-1], base.Comment):
                    self._comments.append(music[-1][-1].pop())
            if self._articulations:
                if music.tail:
                    music = lily.Music(music)
                if self._comments:
                    music.extend(self._comments)
                    self._comments.clear()
                music.append(lily.Articulations(*self._articulations))
                self._articulations.clear()
                # move comments at end of articulations back to toplevel
                while isinstance(music[-1][-1], base.Comment):
                    self._comments.append(music[-1].pop())

            yield music

            yield from self._comments
            self._comments.clear()

            # if there are tweaks but no articulations, the tweak
            # is meant for the next note. Output it now.
            yield from (e for e in self._events if isinstance(e, lily.Tweak))
            self._events.clear()

        self._music = self._duration = self._scaling = None

    def add_articulation(self, art):
        """Add an articulation or script."""
        if self._music:
            if self._events:
                self._events[-1].append(art)
                art = e = self._events[0]
                for f in self._events[1:]:
                    e.append(f)
                    e = f
                self._events.clear()
            self._articulations.append(art)
            return True
        else:
            print("Unbound event:", art) # TEMP
            return False

    def add_spanner_id(self, node):
        """Return True if the node could be added to a spanner id that's being built."""
        if self._events and isinstance(self._events[-1], lily.SpannerId) and len(self._events[-1]) == 0:
            self._events[-1].append(node)
            return True
        return False

    def add_tweak(self, node):
        """Return True if the node could be added to a Tweak that's being built."""
        if self._events and isinstance(self._events[-1], lily.Tweak) and len(self._events[-1]) < 2:
            self._events[-1].append(node)
            return True
        return False

    def add_tag(self, node):
        r"""Return True if the node could be added to a ``\tag`` command that's being built."""
        if self._events and isinstance(self._events[-1], lily.Tag):
            self._events[-1].append(node)
            return True
        return False

    def __iter__(self):
        """Yield all the music from the items given at construction."""
        for i in self.items:
            if i.is_token:
                # dispatch on token (text or action)
                meth = self._token.get(i.text)
                if not meth:
                    for action in i.action:
                        meth = self._action.get(action)
                        if meth:
                            break
                    else:
                        # TEMP
                        print("Unknown token:", i)
                        continue
                result = meth(i)
            else:
                # dispatch on object name
                meth = self._context.get(i.name)
                if not meth:
                    if isinstance(i.obj, element.Element):
                        yield from self.pending_music()
                        yield i.obj
                    else:
                        # TEMP
                        print("Unknown item:", i)
                    continue
                result = meth(i.obj)
            if result:
                yield from result

        # pending stuff
        yield from self.pending_music()

    @_token(r'\skip')
    def skip_token(self, token):
        r"""Called for ``\skip``."""
        yield from self.pending_music()
        self._music = self.factory(lily.Skip, (token,))

    @_token(r'\rest')
    def rest_token(self, token):
        r"""Called for ``\rest``."""
        if isinstance(self._music, lily.Note):
            # make it a positioned rest, reuse old pitch token if possible
            try:
                origin = self._music.head_origin
            except AttributeError:
                self._music = lily.Rest(self._music.head, *self._music)
            else:
                self._music = self.factory(lily.Rest, origin, (), *self._music)
            self._music.append(self.factory(lily.RestModifier, (token,)))

    @_token(r'\tweak')
    def tweak_token(self, token):
        r"""Called for ``\tweak``."""
        self._events.append(self.factory(lily.Tweak, (token,)))

    @_token(r'\noBeam')
    def nobeam_token(self, token):
        r"""Called for ``\noBeam``."""
        self.add_articulation(self.factory(lily.Modifier, (token,)))

    @_token(r'\tag')
    def tag_token(self, token):
        r"""Called for ``\tag``."""
        elem = self.factory(lily.Tag, (token,))
        if self._events and isinstance(self._events[-1], lily.Direction):
            # after a direction it affects the coming articulation
            self._events.append(elem)
        else:
            # otherwise a toplevel tag element
            yield from self.pending_music()
            yield elem

    @_action(a.Text.Music.Pitch, a.Name.Pitch)
    def pitch_action(self, token):
        r"""Called for ``Text.Music.Pitch (or Name.Pitch)``."""
        yield from self.pending_music()
        cls = lily.Q if token == 'q' else lily.Note
        self._music = self.factory(cls, (token,))

    @_action(a.Text.Music.Pitch.Octave)
    def octave_action(self, token):
        r"""Called for ``Text.Music.Pitch.Octave``.

        This happens for \\relative, \\transpose, \\fixed etc.
        The previous item then was a Name.Pitch, which created a note.
        Just append the octave.

        """
        octave = self.factory(lily.Octave, (token,))
        self._music.append(octave)

    @_action(a.Text.Music.Rest)
    def rest_action(self, token):
        r"""Called for ``Text.Music.Rest``."""
        yield from self.pending_music()
        cls = lily.Space if token == 's' else lily.Rest
        self._music = self.factory(cls, (token,))

    @_action(a.Text.Music.Pitch.Drum)
    def drum_action(self, token):
        r"""Called for ``Text.Music.Pitch.Drum``."""
        yield from self.pending_music()
        self._music = self.factory(lily.Drum, (token,))

    @_action(a.Number.Duration)
    def duration_action(self, token):
        r"""Called for ``Number.Duration``."""
        if self._duration or self._articulations:
            yield from self.pending_music()
        self._duration = [token]

    @_action(a.Delimiter.Direction)
    def direction_action(self, token):
        r"""Called for ``Delimiter.Direction``."""
        self._events.append(self.factory(lily.Direction, (token,)))

    @_action(a.Name.Builtin.Dynamic)
    def dynamic_action(self, token):
        r"""Called for ``Name.Builtin.Dynamic``."""
        self.add_articulation(self.factory(lily.Dynamic, (token,)))

    # articulations that are spanners, for articulation_action()
    _articulations_mapping = _spanner_start_stop_mapping(
        lily.TextSpanner, lily.TrillSpanner, lily.Melisma,
    )
    _articulations_mapping.update(_head_mapping(
        lily.LaissezVibrer, lily.RepeatTie, lily.Arpeggio, lily.Glissando,
    ))

    @_action(a.Name.Script.Articulation)
    def articulation_action(self, token):
        r"""Called for ``Name.Script.Articulation``."""
        cls = self._articulations_mapping.get(token.text, lily.Articulation)
        self.add_articulation(self.factory(cls, (token,)))

    # mapping for spanners in spanner_action()
    _spanner_mapping = {
        a.Name.Symbol.Spanner.Slur: lily.Slur,
        a.Name.Symbol.Spanner.Slur.Phrasing: lily.PhrasingSlur,
        a.Name.Symbol.Spanner.Tie: lily.Tie,
        a.Name.Symbol.Spanner.Beam: lily.Beam,
        a.Name.Symbol.Spanner.Ligature: lily.Ligature,
        a.Name.Symbol.Spanner.PesOrFlexa: lily.PesOrFlexa,
    }

    @_action(a.Name.Symbol.Spanner)
    def spanner_action(self, token):
        r"""Called for ``Name.Symbol.Spanner.*``."""
        if token.action is a.Name.Symbol.Spanner.Id:
            self._events.append(self.factory(lily.SpannerId, (token,)))
        else:
            self.add_articulation(self.factory(self._spanner_mapping[token.action], (token,)))

    @_action(a.Name.Type)
    def name_type_action(self, token):
        r"""Called for ``Name.Type``, e.g. a key signature mode."""
        yield from self.pending_music()
        yield self.factory(lily.Mode, (token,))

    @_action(a.Delimiter.Tremolo)
    def tremolo_action(self, token):
        r"""Called for ``Delimiter.Tremolo``."""
        tremolo = self.factory(lily.Tremolo, (token,))
        if token.group == 0:
            # next item is the duration
            tremolo.append(self.factory(lily.Duration, (next(self.items),)))
        self.add_articulation(tremolo)

    @_action(a.Delimiter.Separator.PipeSymbol)
    def pipe_symbol_action(self, token):
        r"""Called for ``Delimiter.Separator.PipeSymbol``."""
        yield from self.pending_music()
        yield self.factory(lily.PipeSymbol, (token,))

    @_action(a.Delimiter.Separator.VoiceSeparator)
    def voice_separator_action(self, token):
        r"""Called for ``Delimiter.Separator.VoiceSeparator``."""
        yield from self.pending_music()
        yield self.factory(lily.VoiceSeparator, (token,))

    _chord_modifier_mapping = _head_mapping(
        lily.AddSteps, lily.RemoveSteps, lily.Inversion, lily.AddInversion)

    @_action(a.Delimiter.Separator.Chord)
    def chord_modifier_action(self, token):
        r"""Called for ``Delimiter.Separator.Chord``, chordmode."""
        elem = self.factory(self._chord_modifier_mapping[token.text], (token,))
        if token.group == 0:
            # next item is the pitch of an inversion
            note = self.factory(lily.Note, (next(self.items),))
            elem.append(note)
        if self._music and not self._articulations:
            self._chord_modifiers.append(elem)

    @_action(a.Number)
    def number_action(self, token):
        r"""Called for ``Number``."""
        elem = self.factory(lily.Int, (token,))
        if not self.add_spanner_id(elem) and not self.add_tweak(elem):
            pass # there was no spanner id, something else?

    @_action(a.Number.Float)
    def float_action(self, token):
        r"""Called for ``Number.Float``."""
        elem = self.factory(lily.Float, (token,))
        if not self.add_tweak(elem):
            yield from self.pending_music()
            yield elem

    @_action(a.Number.Fraction)
    def fraction_action(self, token):
        r"""Called for ``Number.Fraction``."""
        yield from self.pending_music()
        yield self.factory(lily.Fraction, (token,))

    @_action(a.Name.Symbol)
    def symbol_action(self, token):
        r"""Called for ``Name.Symbol.*``."""
        elem = self.factory(lily.Symbol, (token,))
        if not self.add_spanner_id(elem) and not self.add_tweak(elem):
            pass # there was no spanner id, something else?

    @_action(a.Operator.Assignment)
    def assignment_action(self, token):
        r"""Called for ``Operator.Assignment``."""
        if not self._events:
            # '=' has no meaning inside music, but let it through at toplevel
            yield from self.pending_music()
            yield self.factory(lily.EqualSign, (token,))

    @_action(a.Text.Lyric.LyricText)
    def lyric_text_action(self, token):
        r"""Called for ``Text.Lyric.LyricText``."""
        yield from self.pending_music()
        self._music = self.factory(lily.LyricText, (token,))

    @_action(a.Delimiter.Lyric.LyricExtender)
    def lyric_extender_action(self, token):
        r"""Called for ``Delimiter.Lyric.LyricExtender``."""
        yield from self.pending_music()
        yield self.factory(lily.LyricExtender, (token,))

    @_action(a.Delimiter.Lyric.LyricHyphen)
    def lyric_hyphen_action(self, token):
        r"""Called for ``Delimiter.Lyric.LyricHyphen``."""
        yield from self.pending_music()
        yield self.factory(lily.LyricHyphen, (token,))

    @_action(a.Delimiter.Lyric.LyricSkip)
    def lyric_skip_action(self, token):
        r"""Called for ``Delimiter.Lyric.LyricSkip``."""
        yield from self.pending_music()
        yield self.factory(lily.LyricSkip, (token,))

    _builtin_mapping = _head_mapping(
        lily.Key, lily.Clef, lily.Time, lily.Relative, lily.Absolute,
        lily.Fixed, lily.Transpose, lily.Transposition, lily.Ottava,
        lily.Times, lily.Tuplet, lily.ScaleDurations, lily.Tempo, lily.Grace,
        lily.Acciaccatura, lily.Appoggiatura, lily.SlashedGrace,
        lily.AfterGrace, lily.Bar, lily.Breathe, lily.Mark, lily.Default,
        lily.Label, lily.AddQuote, lily.QuoteDuring, lily.UnfoldRepeats,
        lily.Alternative, lily.KeepWithTag, lily.RemoveWithTag, lily.TagGroup,
        lily.PushToTag, lily.AppendToTag,
    )
    _builtin_mapping.update(_toggle_mapping(
        lily.AutoBeam, lily.Break, lily.PageBreak, lily.PageTurn, lily.Cadenza,
        lily.EasyHeads, lily.PointAndClick, lily.Sustain, lily.Sostenuto,
    ))

    @_action(a.Name.Builtin)
    def name_builtin_action(self, token):
        """Called for any Name.Builtin token."""
        yield from self.pending_music()
        cls = self._builtin_mapping.get(token.text, lily.MusicFunction)
        yield self.factory(cls, (token,))

    _keyword_mapping = _head_mapping(
        lily.Omit, lily.Hide, lily.Undo, lily.Once, lily.Temporary,
        lily.Override, lily.Revert, lily.Set, lily.Unset, lily.Version,
        lily.Language, lily.Include, lily.New, lily.Context, lily.Change,
        lily.Sequential, lily.Simultaneous, lily.NoteMode, lily.Repeat,
        lily.Alternative,
    )

    @_action(a.Keyword)
    def keyword_action(self, token):
        """Called for any Keyword token."""
        yield from self.pending_music()
        try:
            cls = self._keyword_mapping[token.text]
        except KeyError:
            yield from self._keyword(token.text, token) or ()
        else:
            yield self.factory(cls, (token,))

    @_keyword(r'\lyricmode', r'\lyrics', r'\lyricsto')
    def keyword_lyricmode(self, token):
        r"""Called for Keyword ``\lyricmode``, ``\lyrics`` and ``\lyricsto``."""
        yield self.factory(lily.LyricMode, (token,))

    @_keyword(r'\addlyrics')
    def keyword_addlyrics(self, token):
        r"""Called for Keyword ``\addlyrics``."""
        yield self.factory(lily.LyricMode, (token,))

    @_keyword(r'\chordmode', r'\chords')
    def keyword_chordmode(self, token):
        r"""Called for Keyword ``\chordmode`` and ``\chords``."""
        yield self.factory(lily.ChordMode, (token,))

    @_keyword(r'\figuremode', r'\figures')
    def keyword_figure(self, token):
        r"""Called for Keyword ``\figuremode`` and ``\figures``."""
        yield self.factory(lily.FigureMode, (token,))

    @_keyword(r'\drummode', r'\drums')
    def keyword_drummode(self, token):
        r"""Called for Keyword ``\drummode`` and ``\drums``."""
        yield self.factory(lily.DrumMode, (token,))

    @_context("chord_modifier")
    def chord_modifier(self, obj):
        """Called with the result of the ``chord_modifier`` context."""
        self._chord_modifiers[-1].extend(obj)

    @_context("repeat", "lyricsto", "lyricmode", "drummode", "notemode",
              "chordmode", "figuremode")
    def flatten_elements(self, obj):
        """Called for context that yield lists of Elements; flatten them."""
        yield from obj

    @_context("pitch")
    def pitch(self, obj):
        """Called for ``pitch`` context: octave, accidental, octavecheck."""
        self._music.extend(obj)

    @_context("duration")
    def duration(self, obj):
        """Called for ``duration`` context: dots, scaling."""
        dots, self._scaling = obj
        self._duration.extend(dots)

    @_context("chord")
    def chord(self, obj):
        """Called for ``chord`` context: a chord."""
        yield from self.pending_music()
        self._music = obj

    @_context("script")
    def script(self, obj):
        """Called for ``script`` context: an articulation."""
        self.add_articulation(obj)

    @_context("figure")
    def figure(self, obj):
        """Called for ``figure`` context: a Figure."""
        yield from self.pending_music()
        self._music = obj

    @_context("string", "scheme", "list")
    def string_scheme(self, obj):
        """Called for ``string``, ``scheme`` or ``list`` context."""
        if self._events:
            # after a direction: an articulation
            if not self.add_spanner_id(obj) and not self.add_tweak(obj) and not self.add_tag(obj):
                self.add_articulation(obj)
        else:
            # toplevel expression
            yield from self.pending_music()
            yield obj

    @_context("markup")
    def markup(self, obj):
        """Called for ``markup`` context: read arguments from items."""
        for node in self.transform.create_markup(obj, self.items):
            if self._events:
                # after a direction: add to the note
                self.add_articulation(node)
            else:
                # toplevel markup item (in lyricmode possible)
                yield from self.pending_music()
                self._music = node

    @_context("identifier_ref")
    def identifier_ref(self, obj):
        """Called for ``identifier_ref`` context: maybe articulation."""
        if self._events:
            # after a direction: add as articulation
            self.add_articulation(obj)
        else:
            # toplevel expression
            yield from self.pending_music()
            yield obj

    @_context("singleline_comment", "multiline_comment")
    def comment(self, obj):
        """Called for ``singleline_comment`` and ``multiline_comment`` context.

        Comments are preserved as good as possible.

        """
        if self._chord_modifiers:
            self._chord_modifiers[-1].append(obj)
        elif self._events:
            self._events[-1].append(obj)
        elif self._articulations:
            self._articulations.append(obj)
        elif not self._music and not self._duration:
            # no pending music
            yield obj
        else:
            self._comments.append(obj)  # will be added after the duration

