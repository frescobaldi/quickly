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
"""


import collections
import contextlib

import parce.util
from parce.lang.lilypond_words import pitch_names


# reverse pitch names
def _make_reverse_pitch_table():
    for language, pitches in pitch_names.items():
        notes = collections.defaultdict(list)
        for name, note_alter in pitches.items():
            notes[note_alter].append(name)
        yield language, {note_alter: tuple(names)
                for note_alter, names in notes.items()}

pitch_names_reversed = dict(_make_reverse_pitch_table())
del _make_reverse_pitch_table


class Pitch:
    """A pitch with ``note``, ``alter`` and ``octave`` attributes.

    The attributes may be manipulated directly.

    The ``note`` is an integer in the 0..6 range, where 0 stands for C; the
    ``alter`` is a float in the range -1..1, where all pitch languages support
    the values -1, -0.5, 0, 0.5, 1, and some languages also support semi and
    three-quarter alterations like 0.25; and ``octave`` is an integer where 0
    stands for the octave below "middle C" (with no comma or apostrophe in
    LilyPond's format).

    Pitches compare equal when their attributes are the same, and also support
    the ``>``, ``<``, ``>=`` and ``<=`` operators.

    """
    def __init__(self, note=0, alter=0, octave=0):
        self.note = note
        self.alter = alter
        self.octave = octave

    @classmethod
    def c1(cls):
        """Return a pitch ``c'``."""
        return cls(octave=1)

    @classmethod
    def c0(cls):
        """Return a pitch ``c``."""
        return cls()

    @classmethod
    def f0(cls):
        """Return a pitch ``f``."""
        return cls(3)

    def __repr__(self):
        try:
            name = pitch_names_reversed['nederlands'][(self.note, self.alter)][0] + num_to_octave(self.octave)
        except KeyError:
            name = '?'
        return "<{} note={}, alter={}, octave={} ({})>".format(
            self.__class__.__name__, self.note, self.alter, self.octave, name)

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
        return type(self)(self.note, self.alter, self.octave)

    def make_absolute(self, prev_pitch):
        """Make ourselves absolute, i.e. set our octave from ``prev_pitch``."""
        self.octave += prev_pitch.octave - (self.note - prev_pitch.note + 3) // 7

    def make_relative(self, prev_pitch):
        """Make ourselves relative, i.e. change our octave from ``prev_pitch``."""
        self.octave -= prev_pitch.octave - (self.note - prev_pitch.note + 3) // 7


class PitchProcessor:
    """Read and write pitch names in all LilyPond languages.

    The language to use by default can be set in the ``language`` attribute;
    you can also specify the language on every call to the :meth:`read` or
    :meth:`write` method.

    Some languages have multiple pitch names for the same note; using the
    ``prefer_`` attributes you can control which style is chosen on
    :meth:`write`.

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

        """.format(langs = ", ".join('``"{}"``'.format(name)
            for name in sorted(pitch_names)))

    def read(self, name):
        """Returns ``(note, alter)`` for the specified note name.

        Raises a :obj:`KeyError` if the language does not know the pitch name,
        or when the language name is unknown.

        For example::

            >>> from quickly.pitch import PitchProcessor
            >>> p=PitchProcessor()
            >>> p.read('cis')
            (0, 0.5)

        """
        return pitch_names[self._language][name]

    def write(self, note, alter=0):
        """Return a pitch name for the specified note and alter.

        The ``note`` is a value in the range 0..6, and ``alter`` a value
        between -1 and 1. Most used alterations are -1, -0.5, 0, 0.5 and 1, but
        some languages also support quarter tones, like 0.25.

        Raises a :obj:`KeyError` if the language does not contain a pitch name.

        For example::

            >>> from quickly.pitch import PitchProcessor
            >>> p=PitchProcessor()
            >>> p.write(0)
            'c'
            >>> p.write(4, 1)
            'gisis'
            >>> p.language = 'english'
            >>> p.write(4, 1)
            'gss'
            >>> p.prefer_long = True
            >>> p.write(4, 1)
            'g-sharpsharp'

        """
        names = pitch_names_reversed[self._language][note, alter]
        if len(names) == 1:
            return names[0]
        return self._suitable(self._language, names) or names[-1]

    def read_node(self, node):
        """Return a Pitch, initialized from the node.

        The ``node`` is a :class:`~.dom.lily.Note` (or positioned
        :class:`~.dom.lily.Rest`). For example::

            >>> from quickly.pitch import PitchProcessor
            >>> from quickly.dom import lily
            >>> n = lily.Note('re')
            >>> p = PitchProcessor('français')
            >>> p.read_node(n)
            <Pitch note=1, alter=0, octave=0 (d)>

        """
        note, alter = self.read(node.head)
        return Pitch(note, alter, node.octave)

    def write_node(self, node, pitch):
        """Write the Pitch's note, alter and octave to the node.

        The ``node`` is a :class:`~.dom.lily.Note` (or positioned
        :class:`~.dom.lily.Rest`). Example::

            >>> from quickly.pitch import Pitch, PitchProcessor
            >>> from quickly.dom import lily
            >>> n = lily.Note('c')
            >>> p = PitchProcessor()
            >>> p.write_node(n, Pitch(1, 0.5, 2))
            >>> n.dump()
            <lily.Note 'dis' (1 child)>
             ╰╴<lily.Octave 2>

        """
        node.head = self.write(pitch.note, pitch.alter)
        node.octave = pitch.octave

    @contextlib.contextmanager
    def pitch(self, node, write=True):
        """Return a context manager that yields a :class:`Pitch` when entered.

        The ``node`` is a :class:`~.dom.lily.Note` (or positioned
        :class:`~.dom.lily.Rest`). You can manipulate the Pitch, and when done,
        the node will be updated. An example::

            >>> from quickly.pitch import PitchProcessor
            >>> from quickly.dom import lily
            >>> n = lily.Note('c')
            >>> p = PitchProcessor()
            >>> with p.pitch(n) as pitch:
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
                elif language in ("francais", "français"):
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
                        or (name.endswith('dd') and language in ("francais", "français"))):
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

    @_suitable("francais")
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


def num_to_octave(n):
    """Convert a numeric value to an octave notation.

    The octave notation consists of zero or more ``'`` or ``,``. The octave
    ``0`` returns the empty string. Note that this differs from LilyPond, which
    uses -1 for the octave without a ``'`` or ``,``.

    """
    return "," * -n if n < 0 else "'" * n


def octave_to_num(octave):
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
    langs = ["nederlands", "english", "deutsch", "francais", "italiano"]
    langs.extend(sorted(set(pitch_names) - set(langs) - {'français', 'español'}))
    names = set(names) - set('rRsq') # remove language-agnostic names ;-)
    for language in langs:
        if not names - set(pitch_names[language]):
            yield language


