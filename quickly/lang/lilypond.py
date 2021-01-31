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
    identifier_mapping = {
        a.Number: lily.Number,
        a.Separator: lily.Separator,
    }

    #: mapping for actions in LilyPond.pitch
    pitch_mapping = {
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
                    yield self.factory(self.pitch_mapping[i.action], (i,))
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
                        self.identifier_mapping.get(i.action, lily.Symbol), (i,))
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
    """Helper class that reads and builds music."""
    #: articulations that are spanners:
    articulations_mapping = {
        r'\startTextSpan': lily.TextSpanner,
        r'\stopTextSpan': lily.TextSpanner,
        r'\startTrillSpan': lily.TrillSpanner,
        r'\stopTrillSpan': lily.TrillSpanner,
    }

    #: mapping for spanners in LilyPond.create_music
    music_mapping = {
        a.Name.Symbol.Spanner.Slur: lily.Slur,
        a.Name.Symbol.Spanner.Slur.Phrasing: lily.PhrasingSlur,
        a.Name.Symbol.Spanner.Tie: lily.Tie,
        a.Name.Symbol.Spanner.Beam: lily.Beam,
        a.Name.Symbol.Spanner.Ligature: lily.Ligature,
        a.Name.Symbol.Spanner.PesOrFlexa: lily.PesOrFlexa,
    }

    #: mapping for separators in LilyPond.create_music
    separator_mapping = {
        a.Delimiter.Separator.PipeSymbol: lily.PipeSymbol,
        a.Delimiter.Separator.VoiceSeparator: lily.VoiceSeparator,
    }

    def __init__(self, transform, items):
        self.transform = transform
        self.factory = transform.factory
        self.items = iter(items)

        self.music = None
        self.duration = None
        self.scaling = None
        self.events = []         # for direction and spanner-id
        self.articulations = []
        self.comments = []       # for comments between pitch and duration...

    def pending_music(self):
        """Yield pending music."""
        music = self.music
        if self.duration:
            dur = self.factory(lily.Duration, self.duration)
            if self.scaling:
                dur.append(self.scaling)
            if music:
                if music.tail:
                    music = lily.Music(music)
                music.append(dur)
            else:
                music = lily.Unpitched(dur)
        if music:
            if self.articulations:
                if self.comments:
                    if music.tail:
                        music = lily.Music(music)
                    music.extend(self.comments)
                    self.comments.clear()
                music.append(lily.Articulations(*self.articulations))
                self.articulations.clear()
                # move comments at end of articulations back to toplevel
                while isinstance(music[-1][-1], base.Comment):
                    self.comments.append(music[-1].pop())

            yield music

            yield from self.comments
            self.comments.clear()

            # if there are tweaks but no articulations, the tweak
            # is meant for the next note. Output it now.
            yield from (e for e in self.events if isinstance(e, lily.Tweak))
            self.events.clear()

        self.music = self.duration = self.scaling = None

    def add_articulation(self, art):
        """Add an articulation or script."""
        if self.events:
            self.events[-1].append(art)
            art = e = self.events[0]
            for f in self.events[1:]:
                e.append(f)
                e = f
            self.events.clear()
        self.articulations.append(art)

    def add_spanner_id(self, node):
        """Return True if the node could be added to a spanner id that's being built."""
        if self.events and isinstance(self.events[-1], lily.SpannerId) and len(self.events[-1]) == 0:
            self.events[-1].append(node)
            return True
        return False

    def add_tweak(self, node):
        """Return True if the node could be added to a Tweak that's being built."""
        if self.events and isinstance(self.events[-1], lily.Tweak) and len(self.events[-1]) < 2:
            self.events[-1].append(node)
            return True
        return False

    def __iter__(self):
        """Yield all the music from the items given at construction."""
        for i in self.items:
            if i.is_token:
                if i.action in a.Text.Music:
                    yield from self.pending_music()
                    if i.action is a.Text.Music.Pitch:
                        cls = lily.Q if i == 'q' else lily.Note
                    else: # i.action is Music.Rest:
                        cls = lily.Space if i == 's' else lily.Rest
                    self.music = self.factory(cls, (i,))
                elif i.action is a.Number.Duration:
                    if self.duration or self.articulations:
                        yield from self.pending_music()
                    self.duration = [i]
                elif i == r'\skip':
                    yield from self.pending_music()
                    self.music = self.factory(lily.Skip, (i,))
                elif i == r'\rest':
                    if isinstance(self.music, lily.Note):
                        # make it a positioned rest, reuse old pitch token if possible
                        try:
                            origin = self.music.head_origin
                        except AttributeError:
                            self.music = lily.Rest(self.music.head, *music)
                        else:
                            self.music = self.factory(lily.Rest, origin, (), *self.music)
                        self.music.append(self.factory(lily.RestModifier, (i,)))
                elif i == r'\tweak':
                    self.events.append(self.factory(lily.Tweak, (i,)))
                elif i == r'\noBeam':
                    self.add_articulation(self.factory(lily.Modifier, (i,)))
                elif i.action is a.Delimiter.Direction:
                    self.events.append(self.factory(lily.Direction, (i,)))
                elif i.action is a.Name.Script.Articulation:
                    cls = self.articulations_mapping.get(i.text, lily.Articulation)
                    self.add_articulation(self.factory(cls, (i,)))
                elif i.action is a.Name.Builtin.Dynamic:
                    self.add_articulation(self.factory(lily.Dynamic, (i,)))
                elif i.action in a.Name.Symbol.Spanner:
                    if i.action is a.Name.Symbol.Spanner.Id:
                        self.events.append(self.factory(lily.SpannerId, (i,)))
                    else:
                        self.add_articulation(self.factory(self.music_mapping[i.action], (i,)))
                elif i.action is a.Delimiter.Tremolo:
                    tremolo = self.factory(lily.Tremolo, (i,))
                    if i.group == 0:
                        # next item is the duration
                        tremolo.append(self.factory(lily.Duration, (next(self.items),)))
                    self.add_articulation(tremolo)
                elif i.action in a.Delimiter.Separator:
                    yield from self.pending_music()
                    yield self.factory(self.separator_mapping[i.action], (i,))
                elif i.action is a.Number:
                    elem = self.factory(lily.Number, (i,))
                    if not self.add_spanner_id(elem) and not self.add_tweak(elem):
                        pass # there was no spanner id, something else?
                elif i.action in a.Name.Symbol:
                    elem = self.factory(lily.Symbol, (i,))
                    if not self.add_spanner_id(elem) and not self.add_tweak(elem):
                        pass # there was no spanner id, something else?
                elif i.action == a.Operator.Assignment:
                    if not self.events:
                        # '=' has no meaning inside music, but let it through at toplevel
                        yield from self.pending_music()
                        yield self.factory(lily.EqualSign, (i,))
                else:
                    # TEMP
                    print("Unknown token:", i)
            else:
                # dispatch on object name
                meth = getattr(self, i.name, None)
                if meth:
                    yield from meth(i.obj)
                elif isinstance(i.obj, element.Element):
                    yield from self.pending_music()
                    yield i.obj
                else:
                    # TEMP
                    print("Unknown item:", i)

        # pending stuff
        yield from self.pending_music()

    def pitch(self, obj):
        # pitch context: octave, accidental, octavecheck
        self.music.extend(obj)
        return
        yield

    def duration(self, obj):
        dots, self.scaling = obj
        self.duration.extend(dots)
        return
        yield

    def chord(self, obj):
        yield from self.pending_music()
        self.music = obj

    def script(self, obj):
        self.add_articulation(obj)
        return
        yield

    def string(self, obj):
        if self.events:
            # after a direction: an articulation
            if not self.add_spanner_id(obj) and not self.add_tweak(obj):
                self.add_articulation(obj)
        else:
            # toplevel expression
            yield from self.pending_music()
            yield obj

    scheme = string

    def markup(self, obj):
        for node in self.transform.create_markup(obj, self.items):
            if self.events:
                # after a direction: add to the note
                self.add_articulation(node)
            else:
                # toplevel markup item
                yield from self.pending_music()
                yield node

    def singleline_comment(self, obj):
        if self.events:
            self.events[-1].append(obj)
        elif self.articulations:
            self.articulations.append(obj)
        elif not self.music and not self.duration:
            # no pending music
            yield obj
        else:
            self.comments.append(obj)  # will be added after the duration

    multiline_comment = singleline_comment

