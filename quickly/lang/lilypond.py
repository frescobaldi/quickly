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

    #: articulations that are spanners:
    articulations_mapping = {
        r'\startTextSpan': lily.TextSpanner,
        r'\stopTextSpan': lily.TextSpanner,
        r'\startTrillSpan': lily.TrillSpanner,
        r'\stopTrillSpan': lily.TrillSpanner,
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
        music = duration = scaling = None
        events = []         # for direction and spanner-id
        Music = a.Text.Music
        articulations = []
        comments = []       # for comments between pitch and duration...

        def pending_music():
            """Yield pending music."""
            nonlocal music, duration, scaling

            if duration:
                dur = self.factory(lily.Duration, duration)
                if scaling:
                    dur.append(scaling)
                if music:
                    if music.tail:
                        music = lily.Music(music)
                    music.append(dur)
                else:
                    music = lily.Unpitched(dur)
            if music:
                if comments:
                    if music.tail:
                        music = lily.Music(music)
                    music.extend(comments)
                comments.clear()
                if articulations:
                    music.append(lily.Articulations(*articulations))
                    articulations.clear()

                yield music

                # if there are tweaks but no articulations, the tweak
                # is meant for the next note. Output it now.
                yield from (e for e in events if isinstance(e, lily.Tweak))
                events.clear()

            music = duration = scaling = None

        def add_articulation(art):
            """Add an articulation or script."""
            if events:
                events[-1].append(art)
                art = e = events[0]
                for f in events[1:]:
                    e.append(f)
                    e = f
                events.clear()
            articulations.append(art)

        def add_spanner_id(node):
            """Return True if the node could be added to a spanner id that's being built."""
            if events and isinstance(events[-1], lily.SpannerId) and len(events[-1]) == 0:
                events[-1].append(node)
                return True
            return False

        def add_tweak(node):
            """Return True if the node could be added to a Tweak that's being built."""
            if events and isinstance(events[-1], lily.Tweak) and len(events[-1]) < 2:
                events[-1].append(node)
                return True
            return False

        items = iter(items)
        for i in items:
            if i.is_token:
                if i.action in Music:
                    yield from pending_music()
                    if i.action is Music.Pitch:
                        cls = lily.Q if i == 'q' else lily.Note
                    elif i.action is Music.Rest:
                        cls = lily.Space if i == 's' else lily.Rest
                    music = self.factory(cls, (i,))
                elif i.action is a.Number.Duration:
                    if duration or articulations:
                        yield from pending_music()
                    duration = [i]
                elif i == r'\skip':
                    yield from pending_music()
                    music = self.factory(lily.Skip, (i,))
                elif i == r'\rest':
                    if isinstance(music, lily.Note):
                        # make it a positioned rest, reuse old pitch token if possible
                        try:
                            origin = music.head_origin
                        except AttributeError:
                            music = lily.Rest(music.head, *music)
                        else:
                            music = self.factory(lily.Rest, origin, (), *music)
                        music.append(self.factory(lily.RestModifier, (i,)))
                elif i == r'\tweak':
                    events.append(self.factory(lily.Tweak, (i,)))
                elif i == r'\noBeam':
                    add_articulation(self.factory(lily.Modifier, (i,)))
                elif i.action is a.Delimiter.Direction:
                    events.append(self.factory(lily.Direction, (i,)))
                elif i.action is a.Name.Script.Articulation:
                    cls = self.articulations_mapping.get(i.text, lily.Articulation)
                    add_articulation(self.factory(cls, (i,)))
                elif i.action is a.Name.Builtin.Dynamic:
                    add_articulation(self.factory(lily.Dynamic, (i,)))
                elif i.action in a.Name.Symbol.Spanner:
                    if i.action is a.Name.Symbol.Spanner.Id:
                        events.append(self.factory(lily.SpannerId, (i,)))
                    else:
                        add_articulation(self.factory(self.music_mapping[i.action], (i,)))
                elif i.action in a.Delimiter.Separator:
                    yield from pending_music()
                    yield self.factory(self.separator_mapping[i.action], (i,))
                elif i.action is a.Number:
                    elem = self.factory(lily.Number, (i,))
                    if not add_spanner_id(elem) and not add_tweak(elem):
                        pass # there was no spanner id, something else?
                elif i.action in a.Name.Symbol:
                    elem = self.factory(lily.Symbol, (i,))
                    if not add_spanner_id(elem) and not add_tweak(elem):
                        pass # there was no spanner id, something else?
                elif i.action == a.Operator.Assignment:
                    if not events:
                        # '=' has no meaning inside music, but let it through at toplevel
                        yield from pending_music()
                        yield self.factory(lily.EqualSign, (i,))
                else:
                    # TEMP
                    print("Unknown token:", i)
            elif i.name == "pitch":
                # pitch context: octave, accidental, octavecheck
                music.extend(i.obj)
            elif i.name == "duration":
                dots, scaling = i.obj
                duration.extend(dots)
            elif i.name == "chord":
                yield from pending_music()
                music = i.obj
            elif i.name == "script":
                add_articulation(i.obj)
            elif i.name in ("string", "scheme"):
                if events:
                    # after a direction: an articulation
                    if not add_spanner_id(i.obj) and not add_tweak(i.obj):
                        add_articulation(i.obj)
                else:
                    # toplevel expression
                    yield from pending_music()
                    yield i.obj
            elif i.name == "markup":
                for node in self.create_markup(i.obj, items):
                    if events:
                        # after a direction: add to the note
                        add_articulation(node)
                    else:
                        # toplevel markup item
                        yield from pending_music()
                        yield node
            elif i.name in ("singleline_comment", "multiline_comment"):
                if events:
                    events[-1].append(i.obj)
                elif articulations:
                    articulations.append(i.obj)
                elif not music and not duration:
                    # no pending music
                    yield i.obj
                else:
                    comments.append(i.obj)  # will be added after the duration
            elif isinstance(i.obj, element.Element):
                yield from pending_music()
                yield i.obj
            else:
                # TEMP
                print("Unknown item:", i)

        # pending stuff
        yield from pending_music()

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
        return self.create_block(lily.Midi, items)

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



