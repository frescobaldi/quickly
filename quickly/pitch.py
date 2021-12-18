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


class PitchNameProcessor:
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
        """The language to use if none is specified (default: ``"nederlands"``).

        Deleting this attribute sets it back to ``"nederlands"``.

        Raises a :obj:`KeyError` if the language you try to set does not exist.
        Valid languages are: {langs}.

        """.format(langs = ", ".join('``"{}"``'.format(name)
            for name in sorted(pitch_names)))

    def read(self, name, language=None):
        """Returns ``(note, alter)`` for the specified note name.

        The default ``language`` is used if you don't specify one.

        Raises a :obj:`KeyError` if the language does not know the pitch name,
        or when the language name is unknown.

        For example::

            >>> from quickly.pitch import PitchNameProcessor
            >>> p=PitchNameProcessor()
            >>> p.read('cis')
            (0, 0.5)

        """
        return pitch_names[language or self._language][name]

    def write(self, note, alter=0, language=None):
        """Return a pitch name for the specified note and alter.

        The ``note`` is a value in the range 0..6, and ``alter`` a value
        between -1 and 1. Most used alterations are -1, -0.5, 0, 0.5 and 1, but
        some languages also support quarter tones, like 0.25.

        The default ``language`` is used if you don't specify one.

        Raises a :obj:`KeyError` if the language does not contain a pitch name,
        or when the language name is unknown.

        For example::

            >>> from quickly.pitch import PitchNameProcessor
            >>> p=PitchNameProcessor()
            >>> p.write(0)
            'c'
            >>> p.write(4, 1)
            'gisis'
            >>> p.write(4, 1, 'english')
            'gss'
            >>> p.prefer_long = True
            >>> p.write(4, 1, 'english')
            'g-sharpsharp'

        """
        names = pitch_names_reversed[language or self._language][note, alter]
        if len(names) == 1:
            return names[0]
        return self._suitable(language, names) or names[-1]

    def distill_preferences(self, pitchnames, language=None):
        """Iterate over the ``pitchnames`` and try to distill the preferred style.

        Adjust the preferences based on the encountered pitches.
        The default ``language`` is used if you don't specify one.

        If the pitchnames iterable contains a language name, that language is
        followed to test following pitchnames. (The default language is not
        changed.)

        """
        if not language:
            language = self._language

        pitchnames = iter(pitchnames)

        prefer_accented = None
        prefer_classic = None
        prefer_double_s = None
        prefer_long = None
        prefer_x = None
        prefer_deprecated = None

        while True:
            names = pitch_names[language]
            for name in pitchnames:
                if name in names:
                    if language in ("francais", "français"):
                        if 'é' in name:
                            prefer_accented = True
                        elif not prefer_accented and 'e' in name:
                            prefer_accented = False
                    elif language == "english":
                        if '-' in name:
                            prefer_long = True
                        elif not prefer_long and names[name][1] in {-1, -0.5, 0.5, 1}:
                            prefer_long = False
                    elif language == "norsk":
                        if 'ss' in name:
                            prefer_double_s = True
                        elif not prefer_double_s and 's' in name:
                            prefer_double_s = False
                    elif language == "nederlands":
                        if name in {'es', 'eses', 'as', 'ases'}:
                            prefer_classic = True
                        elif not prefer_classic and name in {'ees', 'eeses', 'aes', 'aeses'}:
                            prefer_classic = False
                    elif language == "deutsch":
                        if name in {'eeh', 'ases', 'aseh', 'aeh'}:
                            prefer_deprecated = True
                        elif not prefer_deprecated and name in {'eh', 'asas', 'asah', 'ah'}:
                            prefer_deprecated = False
                    if name.endswith('x'):
                        prefer_x = True
                    elif not prefer_x and (
                               (name.endswith('ss') and language in ("english", "espanol", "español"))
                            or (name.endswith('dd') and language in ("francais", "français"))):
                        prefer_x = False
                elif name in pitch_names:
                    language = name
                    break
            else:
                break   # all names checked

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


