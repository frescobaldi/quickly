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
Functions to deal with LilyPond pitches.
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
        yield language, dict(notes)

pitch_names_reversed = dict(_make_reverse_pitch_table())
del _make_reverse_pitch_table


class PitchNameWriter:
    """Write pitch names in all LilyPond languages.

    Some languages have multiple pitch names for the same note; using the
    ``prefer_`` attributes you can control which style is chosen.

    """
    prefer_long = False         #: prefer long names in english, e.g. c-sharpsharp above css
    prefer_accented = False     #: prefer ré above re (in francais)
    prefer_x = False            #: prefer dox above doss, cx above css, etc in enspanol, english, francais
    prefer_double_s = False     #: prefer ss above s in norsk
    prefer_classic = True       #: prefer es above ees and as above aes (in nederlands, norsk)
    prefer_deprecated = False   #: prefer names marked as deprecated

    def write(self, note, alter=0, language="nederlands"):
        """Return a pitch name for the specified note and alter.

        The ``note`` is a value in the range 0..6, and ``alter`` a value
        between -1 and 1. Most used alterations are -1, -0.5, 0, 0.5 and 1, but
        some languages also support quarter tones, like 0.25.

        Raises a KeyError if the language does not contain a pitch name, or
        when the language name is unknown.

        For example::

            >>> from quickly.pitch import PitchNameWriter
            >>> w=PitchNameWriter()
            >>> w.write(0)
            'c'
            >>> w.write(4, 1)
            'gisis'
            >>> w.write(4, 1, 'english')
            'gss'
            >>> w.prefer_long = True
            >>> w.write(4, 1, 'english')
            'g-sharpsharp'

        """
        names = pitch_names_reversed[language][note, alter]
        if len(names) == 1:
            return names[0]
        return self._suitable(language, names) or names[-1]

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
            if self.prefer_deprecated != (name in {'eh', 'asas', 'asah', 'ah'}):
                return name

    @_suitable("english")
    def _english(self, names):
        if self.prefer_long:
            for name in names:
                if "-" in name:
                    return name
        for name in names:
            if "-" not in name and self.prefer_x == (name.endswith('x')):
                return name

    @_suitable("espanol")
    @_suitable("español")
    def _espanol(self, names):
        for name in names:
            if self.prefer_x == (name.endswith('x')):
                return name

    @_suitable("francais")
    @_suitable("français")
    def _francais(self, names):
        if self.prefer_accented:
            accented = [name for name in names if 'é' in name]
            if accented:
                if len(accented) == 1:
                    return accented[0]
                names = accented
        for name in names:
            if self.prefer_x == (name.endswith('x')):
                return name

    @_suitable("norsk")
    def _norsk(self, names):
        if self.prefer_double_s:
            double_s = [name for name in names if 'ss' in name]
            if double_s:
                if len(double_s) == 1:
                    return double_s[0]
                names = double_s
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
    if n < 0:
        return "," * -n
    return "'" * n


def octave_to_num(octave):
    """Convert an octave string to a numeric value.

    ``''`` is converted to 2, ``,`` to -1. The empty string gives 0.

    """
    return octave.count("'") - octave.count(",")


