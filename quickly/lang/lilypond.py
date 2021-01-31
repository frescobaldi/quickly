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



class LilyPond(parce.lang.lilypond.LilyPond):
    """LilyPond language definition."""
    @classmethod
    def get_scheme_target(cls):
        """Get *our* Scheme."""
        from .scheme import Scheme
        return Scheme.scheme


class LilyPondTransform(Transform):
    """Transform LilyPond to Music."""

    ## mappings from action to element
    #: this mapping is used in the identifier method
    _identifier_mapping = {
        a.Number: lily.Number,
        a.Separator: lily.Separator,
    }

    #: mapping for actions in LilyPond.pitch
    _pitch_mapping = {
        a.Text.Music.Pitch.Octave: lily.Octave,
        a.Text.Music.Pitch.Octave.OctaveCheck: lily.OctaveCheck,
        a.Text.Music.Pitch.Accidental: lily.Accidental,
    }

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
        """Find comment, string, scheme and markup.

        Yields Element objects.

        """
        items = iter(items)
        for i in items:
            if i.is_token:
                if i.action == a.Operator.Assignment:
                    yield self.factory(lily.EqualSign, (i,))
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

        The items are the contents of a block like \book { }.
        The ``head_origin`` are the first two tokens, the ``tail_origin`` the
        last token, if that is a '``}``'.

        """
        tail_origin = (items.pop(),) if items[-1] == '}' else ()
        head_origin = items[:2]
        return self.factory(element_class, head_origin, tail_origin,
            *self.handle_assignments(self.common(items[2:])))

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
                    nargs = LilyPond.get_markup_argument_count(i.text[1:])
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

    def create_music(self, items):
        """Read music from items and yield Element nodes."""
        yield from MusicBuilder(self, items)

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
        element_class = lily.With if items[1] == r'\with' else lily.LayoutContext
        return self.create_block(element_class, items)

    def musiclist(self, items):
        """Create a SequentialMusic (``{`` ... ``}``) or SimultaneousMusic
        (``<<`` ... ``>>``) node.

        """
        head = items[:1]
        tail = (items.pop(),) if items[-1] in ('}', '>>') else ()
        element_class = lily.SequentialMusic if items[0] == '{' else lily.SimultaneousMusic
        return self.factory(element_class, head, tail, *self.create_music(items[1:]))

    def chord(self, items):
        """Create a Chord node (``<`` ... ``>``)."""
        head = items[:1]
        tail = (items.pop(),) if items[-1] == '>' else ()
        return self.factory(lily.Chord, head, tail, *self.create_music(items[1:]))

    def tempo(self, items):
        return items

    def context(self, items):
        return items

    def set_unset(self, items):
        return items

    def override(self, items):
        return items

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
                    yield self.factory(self._pitch_mapping[i.action], (i,))
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
        return items

    def lyricsto(self, items):
        return items

    def notemode(self, items):
        return items

    def drummode(self, items):
        return items

    def drummode(self, items):
        return items

    def chordmode(self, items):
        return items

    def chord_modifier(self, items):
        return items

    def identifier(self, items):
        """Return an Identifier item."""
        def nodes():
            for i in items:
                if i.is_token:
                    yield self.factory(
                        self._identifier_mapping.get(i.action, lily.Symbol), (i,))
                else:
                    yield i.obj # can be a SchemeExpression or String
        return lily.Identifier(*nodes())

    def unit(self, items):
        """A numerical value with possible unit in a paper block."""
        number = self.factory(lily.Number, items[:1])
        if len(items) > 1:
            number.append(self.factory(lily.Unit, items[1:]))
        return number

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
    #: articulations that are spanners:
    _articulations_mapping = {
        r'\startTextSpan': lily.TextSpanner,
        r'\stopTextSpan': lily.TextSpanner,
        r'\startTrillSpan': lily.TrillSpanner,
        r'\stopTrillSpan': lily.TrillSpanner,
    }

    #: mapping for spanners in LilyPond.create_music
    _music_mapping = {
        a.Name.Symbol.Spanner.Slur: lily.Slur,
        a.Name.Symbol.Spanner.Slur.Phrasing: lily.PhrasingSlur,
        a.Name.Symbol.Spanner.Tie: lily.Tie,
        a.Name.Symbol.Spanner.Beam: lily.Beam,
        a.Name.Symbol.Spanner.Ligature: lily.Ligature,
        a.Name.Symbol.Spanner.PesOrFlexa: lily.PesOrFlexa,
    }

    _token = Dispatcher()
    _action = Dispatcher()
    _object = Dispatcher()

    def __init__(self, transform, items):
        self.transform = transform
        self.factory = transform.factory
        self.items = iter(items)

        self._music = None
        self._duration = None
        self._scaling = None
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
            if self._articulations:
                if self._comments:
                    if music.tail:
                        music = lily.Music(music)
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
        if self._events:
            self._events[-1].append(art)
            art = e = self._events[0]
            for f in self._events[1:]:
                e.append(f)
                e = f
            self._events.clear()
        self._articulations.append(art)

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
                meth = self._object.get(i.name)
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

    @_action(a.Text.Music)
    def music_action(self, token):
        r"""Called for ``Text.Music``."""
        yield from self.pending_music()
        if token.action is a.Text.Music.Pitch:
            cls = lily.Q if token == 'q' else lily.Note
        else: # i.action is Music.Rest:
            cls = lily.Space if token == 's' else lily.Rest
        self._music = self.factory(cls, (token,))

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

    @_action(a.Name.Script.Articulation)
    def articulation_action(self, token):
        r"""Called for ``Name.Script.Articulation``."""
        cls = self._articulations_mapping.get(token.text, lily.Articulation)
        self.add_articulation(self.factory(cls, (token,)))

    @_action(a.Name.Builtin.Dynamic)
    def dynamic_action(self, token):
        r"""Called for ``Name.Builtin.Dynamic``."""
        self.add_articulation(self.factory(lily.Dynamic, (token,)))

    @_action(a.Name.Symbol.Spanner)
    def spanner_action(self, token):
        r"""Called for ``Name.Symbol.Spanner.*``."""
        if token.action is a.Name.Symbol.Spanner.Id:
            self._events.append(self.factory(lily.SpannerId, (token,)))
        else:
            self.add_articulation(self.factory(self._music_mapping[token.action], (token,)))

    @_action(a.Delimiter.Tremolo)
    def tremolo_action(self, token):
        r"""Called for ``Delimiter.Tremolo``."""
        tremolo = self.factory(lily.Tremolo, (token,))
        if token.group == 0:
            # next item is the duration
            tremolo.append(self.factory(lily.Duration, (next(self.items),)))
        self.add_articulation(tremolo)

    @_action(a.Delimiter.Separator.PipeSymbol)
    def separator_action(self, token):
        r"""Called for ``Delimiter.Separator.PipeSymbol``."""
        yield from self.pending_music()
        yield self.factory(lily.PipeSymbol, (token,))

    @_action(a.Delimiter.Separator.VoiceSeparator)
    def separator_action(self, token):
        r"""Called for ``Delimiter.Separator.VoiceSeparator``."""
        yield from self.pending_music()
        yield self.factory(lily.VoiceSeparator, (token,))

    @_action(a.Number)
    def number_action(self, token):
        r"""Called for ``Number``."""
        elem = self.factory(lily.Number, (token,))
        if not self.add_spanner_id(elem) and not self.add_tweak(elem):
            pass # there was no spanner id, something else?

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

    @_object("pitch")
    def pitch(self, obj):
        """Called for ``pitch`` context: octave, accidental, octavecheck."""
        self._music.extend(obj)

    @_object("duration")
    def duration(self, obj):
        """Called for ``duration`` context: dots, scaling."""
        dots, self._scaling = obj
        self._duration.extend(dots)

    @_object("chord")
    def chord(self, obj):
        """Called for ``chord`` context: a chord."""
        yield from self.pending_music()
        self._music = obj

    @_object("script")
    def script(self, obj):
        """Called for ``script`` context: an articulation."""
        self.add_articulation(obj)

    @_object("string", "scheme")
    def string_scheme(self, obj):
        """Called for ``string`` or ``scheme`` context."""
        if self._events:
            # after a direction: an articulation
            if not self.add_spanner_id(obj) and not self.add_tweak(obj):
                self.add_articulation(obj)
        else:
            # toplevel expression
            yield from self.pending_music()
            yield obj

    @_object("markup")
    def markup(self, obj):
        """Called for ``markup`` context: read arguments from items."""
        for node in self.transform.create_markup(obj, self.items):
            if self._events:
                # after a direction: add to the note
                self.add_articulation(node)
            else:
                # toplevel markup item
                yield from self.pending_music()
                yield node

    @_object("singleline_comment", "multiline_comment")
    def comment(self, obj):
        """Called for ``singleline_comment`` and ``multiline_comment`` context.

        Comments are preserved as good as possible.

        """
        if self._events:
            self._events[-1].append(obj)
        elif self._articulations:
            self._articulations.append(obj)
        elif not self._music and not self._duration:
            # no pending music
            yield obj
        else:
            self._comments.append(obj)  # will be added after the duration

