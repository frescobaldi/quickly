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
Classes and functions to deal with LilyPond pitches.

A pitch consists of a step (note, the index in the global default scale) and an
alteration, which is a rational value (fraction or floating point) in whole
tones. The notes 0..6 correspond with the usual "white keys" C, D, E, F, G, A,
B; a sharp is represented by a +0.5 alteration value, and a flat by a -0.5
value.

The octave of a pitch is 0 for the octave starting at middle C, just like
LilyPond handles the octave.

All functions and classes in this module, and also in the :mod:`.key` module,
allow specifying a different global default scale (set in the
:py:data:`MAJOR_SCALE` module constant), to theoretically support other tone
systems, but that will probably almost never be necessary.

"""

import bisect
import collections
import contextlib

import parce.util
from parce.lang.lilypond_words import pitch_names


#: Major scale: C D E F G A B, with the default pitch offset from the starting
#: C in whole tones.
MAJOR_SCALE = (0, 1, 2, 2.5, 3.5, 4.5, 5.5)

#: Which pitch values get a flat by default instead of a sharp when converting
#: a MIDI key number to a pitch.
MAJOR_FLATS = (1.5, 5)


# reverse pitch names
def _make_reverse_pitch_table():
    for language, pitches in pitch_names.items():
        notes = collections.defaultdict(lambda: collections.defaultdict(list))
        for name, (octave, note, alter) in pitches.items():
            notes[note, alter][octave].append(name)
        yield language, {note_alter:
            {octave: tuple(names) for octave, names in d.items()}
                for note_alter, d in notes.items()}

pitch_names_reversed = dict(_make_reverse_pitch_table())
del _make_reverse_pitch_table


class Pitch:
    """A pitch with ``octave``, ``note``, and ``alter`` attributes.

    The attributes may be manipulated directly, and have the same contents and
    meaning as the three values in LilyPond's ``(ly:make-pitch octave note
    alter)`` construct.

    The ``octave`` is an integer where 0 stands for the octave containing
    "middle C" (with one apostrophe in LilyPond's format). The ``note`` is an
    integer in the 0..6 range, where 0 stands for C; the ``alter`` is an
    integer, float or fraction denoting the alteration in whole tones, where
    all pitch languages support the values -1, -0.5, 0, 0.5, 1, and some
    languages also support semi, three-quarter alterations like 0.25 (i.e.
    ``Fraction(1, 4)``), or even other alterations.

    Pitches compare equal when their attributes are the same, and also support
    the ``>``, ``<``, ``>=`` and ``<=`` operators. These operators compare on
    octave first, then note, then alter.

    ``format(pitch)`` returns always the dutch notation (or a question mark if
    there's no known name for the note, alter combination), but you can use
    :class:`PitchProcessor` to read/write pitch names in all LilyPond
    languages.

    """
    def __init__(self, octave, note, alter):
        self.octave = octave
        self.note = note
        self.alter = alter

    def __format__(self, format_spec):
        p = PitchProcessor()
        try:
            s = p.to_string(self)
        except KeyError:
            s = '?'
        return format(s, format_spec)

    def __repr__(self):
        return "<{} octave={}, note={}, alter={} ({})>".format(
            self.__class__.__name__, self.octave, self.note, self.alter, self)

    def _as_tuple(self):
        """Return our attributes as a sortable tuple."""
        return (self.octave, self.note, self.alter)

    def __eq__(self, other):
        return isinstance(other, Pitch) and self._as_tuple() == other._as_tuple()

    def __ne__(self, other):
        return not isinstance(other, Pitch) or self._as_tuple() != other._as_tuple()

    def __gt__(self, other):
        if isinstance(other, Pitch):
            return self._as_tuple() > other._as_tuple()
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Pitch):
            return self._as_tuple() < other._as_tuple()
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Pitch):
            return self._as_tuple() >= other._as_tuple()
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Pitch):
            return self._as_tuple() <= other._as_tuple()
        return NotImplemented

    def copy(self):
        """Return a new Pitch with our attributes."""
        return type(self)(self.octave, self.note, self.alter)

    def to_midi(self, scale=None):
        """Return the MIDI key number for this pitch."""
        scale = scale or MAJOR_SCALE
        return int((self.octave + 5) * 12 + (scale[self.note] + self.alter) * 2)

    @classmethod
    def from_midi(cls, key, scale=None, flats=None):
        """Return a :class:`Pitch` from the MIDI key value.

        All altered notes get a sharp, unless a pitch value is listed in the
        ``flats`` parameter. By default, the pitch values 1.5 and 5 get a flat,
        resulting in an e-flat instead of d-sharp and a b-flat instead of an
        a-sharp.

        An example::

            >>> from quickly.pitch import Pitch
            >>> Pitch.from_midi(60)
            <Pitch note=0, alter=0, octave=1 (c')>
            >>> Pitch.from_midi(61)
            <Pitch note=0, alter=0.5, octave=1 (cis')>
            >>> Pitch.from_midi(70)
            <Pitch note=6, alter=-0.5, octave=1 (bes')>
            >>> Pitch.from_midi(70, flats=())
            <Pitch note=5, alter=0.5, octave=1 (ais')>

        A more powerful way to convert MIDI key numbers to pitches is in the
        :class:`~.key.KeySignature` class.

        """
        scale = scale or MAJOR_SCALE
        flats = MAJOR_FLATS if flats is None else flats
        octave, step = divmod(key, 12)
        pitch = step / 2
        if pitch in flats:
            note = bisect.bisect_left(scale, pitch)
        else:
            note = bisect.bisect_right(scale, pitch) - 1
        alter = pitch - scale[note]
        a = int(alter)
        if a == alter:
            alter = a
        return cls(octave - 5, note, alter)

    def make_absolute(self, prev_pitch, scale=None):
        """Make ourselves absolute, i.e. set our octave from ``prev_pitch``."""
        l = len(scale or MAJOR_SCALE)
        self.octave += prev_pitch.octave - (self.note - prev_pitch.note + 3) // l

    def make_relative(self, prev_pitch, scale=None):
        """Make ourselves relative, i.e. change our octave from ``prev_pitch``."""
        l = len(scale or MAJOR_SCALE)
        self.octave -= prev_pitch.octave - (self.note - prev_pitch.note + 3) // l


class PitchProcessor:
    """Read and write pitch names in all LilyPond languages.

    The language to use by default can be given on instantiation or set in the
    ``language`` attribute. Some languages have multiple pitch names for the
    same note; using the ``prefer_`` attributes you can control which style is
    chosen when writing the pitch name.

    """
    #: Prefer long names in english, e.g. ``c-sharpsharp`` above ``css``
    prefer_long = False

    #: Prefer ``ré`` above ``re`` (in francais)
    prefer_accented = False

    #: Prefer ``dox`` above ``doss``, ``cx`` above ``css``, etc in enspanol, english, francais
    prefer_x = False

    #: Prefer ``ss`` above ``s`` inside note names in norsk
    prefer_double_s = False

    #: Prefer ``es`` above ``ees`` and ``as`` above ``aes`` (in nederlands, norsk)
    prefer_classic = True

    #: Prefer names marked as deprecated
    prefer_deprecated = False

    _language = "nederlands"

    def __init__(self, language=None):
        if language:
            self.language = language

    def __repr__(self):
        return "<{} ({})>".format(type(self).__name__, self._language)

    @property
    def language(self):
        return self._language

    @language.setter
    def language(self, language):
        if language not in pitch_names:
            raise KeyError("unknown language name")
        self._language = language

    @language.deleter
    def language(self):
        self._language = "nederlands"

    language.__doc__ = \
        """The language to use (default: ``"nederlands"``).

        Deleting this attribute sets it back to ``"nederlands"``.

        Raises a :obj:`KeyError` if the language you try to set does not exist.
        Valid languages are: {langs}.

        Do not modify the language between a :meth:`read_node` and
        :meth:`write_node` operation on the same node. For translation of pitch
        names, use two PitchProcessors.

        """.format(langs = ", ".join('``"{}"``'.format(name)
            for name in sorted(pitch_names)))

    def pitch(self, name):
        """Return a :class:`Pitch` for the specified note name.

        Raises a :obj:`KeyError` if the language does not know the pitch name,
        or when the language name is unknown.

        For example::

            >>> from quickly.pitch import PitchProcessor
            >>> p = PitchProcessor()
            >>> p.read('cis')
            <Pitch octave=-1, note=0, alter=0.5 (cis)>

        """
        return Pitch(*pitch_names[self._language][name])

    def name_octave(self, pitch):
        """Return a two-tuple (name, octave) for the :class:`Pitch`.

        The name is the note name, the octave is the number of ``,`` (if
        negative) or ``'`` that still need to be added.

        Raises a :obj:`KeyError` if the language does not contain a pitch name.

        """
        octave_dict = pitch_names_reversed[self._language][pitch.note, pitch.alter]
        for octave in sorted(octave_dict, key=lambda o: abs(o - pitch.octave)):
            names = octave_dict[octave]
            octave = pitch.octave - octave
            if len(names) == 1:
                name = names[0]
            else:
                name = self._suitable(self._language, names) or names[-1]
            return name, octave

    def to_string(self, pitch):
        """Return a string representing the pitch.

        Raises a :obj:`KeyError` if the language does not contain a pitch name.

        For example::

            >>> from quickly.pitch import PitchProcessor
            >>> p = PitchProcessor()
            >>> p.write(Pitch(-1, 0, 0))
            'c'
            >>> p.write(Pitch(0, 4, 1))
            "gisis'"
            >>> p.language = 'english'
            >>> p.write(Pitch(0, 4, 1))
            "gss'"
            >>> p.prefer_long = True
            >>> p.write(Pitch(0, 4, 1))
            "g-sharpsharp'"

        """
        name, octave = self.name_octave(pitch)
        return name + octave_to_string(octave)

    def read_node(self, node):
        """Return a Pitch, initialized from the node.

        The ``node`` is a :class:`~.dom.lily.Note`, positioned
        :class:`~.dom.lily.PitchedRest` or any other
        :class:`~.dom.lily.Pitchable` For example::

            >>> from quickly.pitch import PitchProcessor
            >>> from quickly.dom import lily
            >>> n = lily.Note('re')
            >>> p = PitchProcessor('français')
            >>> p.read_node(n)
            <Pitch octave=-1, note=1, alter=0 (d)>

        The octave handling might be a little confusing at first sight: A Note
        node without octave characters has octave 0, while the pitch has octave
        -1. This is because, just like in LilyPond, the pitch name itself
        carries the octave -1, and the octave count of the node is added to it
        to get the resulting octave of the actual pitch::

            >>> n.octave                    # number of ' or ,
            0
            >>> p.read_node(n).octave       # actual octave
            -1

        """
        p = self.pitch(node.head)
        p.octave += node.octave
        return p

    def write_node(self, node, pitch):
        """Write the Pitch's note, alter and octave to the node.

        The ``node`` is a :class:`~.dom.lily.Note` or
        :class:`~.dom.lily.PitchedRest`. Example::

            >>> from quickly.pitch import Pitch, PitchProcessor
            >>> from quickly.dom import lily
            >>> n = lily.Note('c')
            >>> p = PitchProcessor()
            >>> p.write_node(n, Pitch(2, 1, 0.5))
            >>> n.dump()
            <lily.Note 'dis' (1 child)>
             ╰╴<lily.Octave 3>

        """
        p = self.pitch(node.head)
        if (p.note, p.alter) == (pitch.note, pitch.alter):
            # keep the head value, even if there are multiple pitch names
            # in the current language (that can differ in octave)
            node.octave = pitch.octave - p.octave
        else:
            node.head, node.octave = self.name_octave(pitch)

    @contextlib.contextmanager
    def process(self, node, write=True):
        """Return a context manager that yields a :class:`Pitch` when entered.

        The ``node`` is a :class:`~.dom.lily.Note` or
        :class:`~.dom.lily.PitchedRest`. You can manipulate the Pitch, and when
        done, the node will be updated if the pitch was changed. An example::

            >>> from quickly.pitch import PitchProcessor
            >>> from quickly.dom import lily
            >>> n = lily.Note('c')
            >>> p = PitchProcessor()
            >>> with p.process(n) as pitch:
            ...     pitch.note += 2
            ...     pitch.alter = 0.5
            ...     pitch.octave += 1
            ...
            >>> n.write()
            "eis'"
            >>> n.dump()
            <lily.Note 'eis' (1 child)>
             ╰╴<lily.Octave 1>

        If you set the ``write`` parameter to False on invocation, the pitch
        changes will not be written back to the DOM node, this enables you to
        e.g. apply changes only within a certain range.

        """
        p = self.read_node(node)
        yield p
        if write:
            self.write_node(node, p)

    def pitchable(self, pitch, cls=None):
        """Return a new Pitchable element for the pitch.

        By default, a Note is returned, but you may specify any Pitchable
        subclass.

            >>> from quickly.pitch import *
            >>> p = PitchProcessor('nederlands')
            >>> n = p.pitchable(Pitch(2, 3, -.25))
            >>> n.dump()
            <lily.Note 'feh' (1 child)>
             ╰╴<lily.Octave 3>
            >>> n.write()
            "feh'''"

        """
        name, octave = self.name_octave(pitch)
        from .dom import lily
        if cls is None:
            cls = lily.Note
        return cls(name, octave=octave)

    def find_language(self, node):
        r"""Search backwards from node to find the last set language.

        If an ``\include`` command is found that names a language file, or a
        ``\language`` command with a valid language, that language is set.

        """
        from .dom import lily
        for n in node < (lily.Language, lily.Include):
            lang = n.language
            if lang:
                self.language = lang
                break

    def follow_language(self, nodes):
        r"""Iterate over the DOM nodes and follow language changes.

        .. currentmodule:: quickly.dom

        Yield every node, except for :class:`lily.Language` or
        :class:`lily.Include` if a language name is included. Sets the language
        attribute according to the ``\language`` or ``\include`` command.

        """
        from .dom import lily
        for n in nodes:
            if isinstance(n, (lily.Language, lily.Include)):
                lang = n.language
                if lang:
                    self.language = lang
                    continue
            yield n

    def distill_preferences(self, names):
        """Iterate over the ``names`` and try to distill the preferred style.

        Adjust the preferences based on the encountered pitch names.

        This can be used to analyze existing music and use the same pitch name
        preferences for newly entered music.

        The ``names`` iterable may be a set but also an ordered sequence or
        generator. If a name is encountered that is a language name, that
        language is followed to test following pitch names. (The ``language``
        attribute is not changed.)

        """
        language = self._language

        prefer_accented = None
        prefer_classic = None
        prefer_double_s = None
        prefer_long = None
        prefer_x = None
        prefer_deprecated = None

        pnames = pitch_names[language]
        for name in names:
            if name in pnames:
                if language in ("nederlands", "norsk"):
                    if name[:2] in {'es', 'as'}:
                        prefer_classic = True
                    elif not prefer_classic and name[:2] in {'ee', 'ae'}:
                        prefer_classic = False
                    if language == "norsk":
                        if 'ss' in name:
                            prefer_double_s = True
                        elif not prefer_double_s and 's' in name:
                            prefer_double_s = False
                elif language == "english":
                    if '-' in name:
                        prefer_long = True
                    elif not prefer_long and pnames[name][1] in {-1, -0.5, 0.5, 1}:
                        prefer_long = False
                elif language == "français":
                    if 'é' in name:
                        prefer_accented = True
                    elif not prefer_accented and 'e' in name:
                        prefer_accented = False
                elif language == "deutsch":
                    if name in {'eeh', 'ases', 'aseh', 'aeh'}:
                        prefer_deprecated = True
                    elif not prefer_deprecated and name in {'eh', 'asas', 'asah', 'ah'}:
                        prefer_deprecated = False
                elif language == "suomi":
                    if name in {'ases', 'bb', 'heses'}:
                        prefer_deprecated = True
                    elif not prefer_deprecated and name in {'asas', 'bes'}:
                        prefer_deprecated = False
                if name.endswith('x'):
                    prefer_x = True
                elif not prefer_x and (
                           (name.endswith('ss') and language in ("english", "espanol", "español"))
                        or (name.endswith('dd') and language == "français")):
                    prefer_x = False
            elif name in pitch_names:
                language = name
                pnames = pitch_names[language]

        if prefer_accented is not None:
            self.prefer_accented = prefer_accented
        if prefer_classic is not None:
            self.prefer_classic =prefer_classic
        if prefer_double_s is not None:
            self.prefer_double_s = prefer_double_s
        if prefer_long is not None:
            self.prefer_long = prefer_long
        if prefer_x is not None:
            self.prefer_x = prefer_x
        if prefer_deprecated is not None:
            self.prefer_deprecated = prefer_deprecated

    _suitable = parce.util.Dispatcher()

    @_suitable("nederlands")
    def _nederlands(self, names):
        for name in names:
            if self.prefer_classic == (name in {'es', 'eses', 'as', 'ases'}):
                return name

    @_suitable("catalan")
    def _catalan(self, names):
        for name in names:
            if self.prefer_deprecated == name.endswith('s'):
                return name

    @_suitable("deutsch")
    def _deutsch(self, names):
        for name in names:
            if self.prefer_deprecated == (name in {'eeh', 'ases', 'aseh', 'aeh'}):
                return name

    @_suitable("english")
    def _english(self, names):
        if self.prefer_long:
            for name in names:
                if "-" in name:
                    return name
        for name in names:
            if "-" not in name and self.prefer_x == name.endswith('x'):
                return name

    @_suitable("espanol")
    @_suitable("español")
    def _espanol(self, names):
        for name in names:
            if self.prefer_x == name.endswith('x'):
                return name

    @_suitable("français")
    def _francais(self, names):
        subset = [name for name in names if self.prefer_accented == ('é' in name)]
        if subset:
            if len(subset) == 1:
                return subset[0]
            names = subset
        for name in names:
            if self.prefer_x == (name.endswith('x')):
                return name

    @_suitable("norsk")
    def _norsk(self, names):
        subset = [name for name in names if self.prefer_double_s ==  ('ss' in name)]
        if subset:
            if len(subset) == 1:
                return subset[0]
            names = subset
        for name in names:
            if self.prefer_classic == ('ee' in name or 'ae' in name):
                return name

    @_suitable("suomi")
    def _suomi(self, names):
        for name in names:
            if self.prefer_deprecated == (name in {'ases', 'bb', 'heses'}):
                return name


def octave_to_string(n):
    """Convert a numeric value to an octave notation.

    The octave notation consists of zero or more ``'`` or ``,``. The octave
    ``0`` returns the empty string.

    """
    return "," * -n if n < 0 else "'" * n


def octave_from_string(octave):
    """Convert an octave string to a numeric value.

    ``''`` is converted to 2, ``,`` to -1. The empty string gives 0.

    """
    return octave.count("'") - octave.count(",")


def determine_language(names):
    """Yield the language names that have all the specified pitch names.

    This can be used to auto-determine the language of music if the language
    name somehow is not set in a file. Just harvest all the pitch names and
    call this function. The pitch names ``"r"``, ``"R"``, ``"s"`` and ``"q"``
    are ignored. For example::

        >>> from quickly.pitch import determine_language
        >>> list(determine_language(['c', 'd', 'es', 'fis', 'bis']))
        ['nederlands']
        >>> list(determine_language(['c', 'do']))
        []  # ambiguous

    """
    def langs():
        # prefer often used languages
        ubiquitous = ["nederlands", "english", "deutsch", "français", "italiano"]
        exotic = ["arabic", "bagpipe"]

        def others():
            # remove synonyms
            seen = set(id(pitch_names[name]) for name in ubiquitous + exotic)
            for name, value in pitch_names.items():
                if id(value) not in seen:
                    seen.add(id(value))
                    yield name

        yield from ubiquitous
        yield from sorted(others())
        yield from exotic

    names = set(names) - set('rRsq') # remove language-agnostic names ;-)
    for language in langs():
        if not names - set(pitch_names[language]):
            yield language


