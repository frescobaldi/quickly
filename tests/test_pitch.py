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
Template for test files that test quickly.
"""

import pytest

### find quickly
import sys
sys.path.insert(0, '.')

import parce

import quickly
from quickly.pitch import (
    Pitch, PitchProcessor, num_to_octave, octave_to_num, determine_language)
from quickly.transpose import Transposer, transpose_node, transpose
from quickly.dom import read, lily
from quickly.registry import find


def check_pitch():
    """Test pitch manipulations."""
    p = PitchProcessor()
    assert 'c' == p.write(0)
    assert 'cis' == p.write(0, 0.5)

    p.language = 'english'
    assert 'cs' == p.write(0, 0.5)
    p.prefer_long = True
    assert 'c-sharp' == p.write(0, 0.5)

    for language in 'francais', 'français':
        p.language = language
        p.prefer_accented = True
        assert 'ré' == p.write(1, 0)

        p.prefer_x = True
        assert 'réx' == p.write(1, 1)
        p.prefer_x = False
        assert 'rédd' == p.write(1, 1)
        p.prefer_accented = False
        p.prefer_x = True
        assert 'rex' == p.write(1, 1)
        p.prefer_x = False
        assert 'redd' == p.write(1, 1)

    with pytest.raises(KeyError):
        p.language = "does_not_exist"

    p.language = "english"
    assert 'c-sharp' == p.write(0, 0.5)

    del p.language
    assert p.language == "nederlands"
    assert p.read('dis') == (1, 0.5)

    p.language = 'francais'
    assert p.read('réx') == (1, 1)
    assert p.read('rex') == (1, 1)
    assert p.read('rédd') == (1, 1)
    assert p.read('redd') == (1, 1)

    # distill prefs
    p = PitchProcessor()
    p.distill_preferences(['es', 'g'])
    assert p.prefer_classic == True
    p.distill_preferences(['ees', 'g'])
    assert p.prefer_classic == False

    # a non-specific note does not change the pref
    p.distill_preferences(['fis', 'g'])
    assert p.prefer_classic == False
    p.prefer_classic = True
    p.distill_preferences(['fis', 'g'])
    assert p.prefer_classic == True

    # one note changes two prefs
    p = PitchProcessor("francais")
    p.prefer_x = False
    p.prefer_accented = False
    p.distill_preferences(['réx'])
    assert p.prefer_x == True
    assert p.prefer_accented == True

    # unaccented pref set back
    p.distill_preferences(['red'])
    assert p.prefer_x == True
    assert p.prefer_accented == False

    # x pref set back
    p.distill_preferences(['redd'])
    assert p.prefer_x == False
    assert p.prefer_accented == False

    # node editing
    pp = PitchProcessor()
    n = lily.Note('c', octave=2)
    with pp.pitch(n) as p:
        p.note += 2
        p.octave = 1
    assert n.head == 'e'
    assert n.octave == 1

    # Pitch class
    assert Pitch(0, 0, 0) < Pitch(1, 0, 0)
    assert Pitch(0, 0, 0) > Pitch(1, 0, -1)
    assert Pitch(1, .25, 0) == Pitch(1, .25, 0)


    # other functions
    assert num_to_octave(3) == "'''"
    assert num_to_octave(-3) == ",,,"
    assert octave_to_num(",") == -1
    assert octave_to_num("''") == 2
    assert octave_to_num("',") == 0

    assert list(determine_language(['c', 'd', 'e', 'f', 'g'])) == \
        ['nederlands', 'english', 'deutsch', 'norsk', 'suomi', 'svenska']
    assert list(determine_language(['c', 'd', 'es', 'f', 'g'])) == \
        ['nederlands', 'english', 'deutsch', 'norsk', 'suomi']
    assert list(determine_language(['c', 'd', 'es', 'fis', 'g', 'bis'])) == \
        ['nederlands']
    assert list(determine_language(['c', 'do'])) == [] # ambiguous
    assert list(determine_language(['do', 'ré', 'r'])) == \
        ['francais']    # r is ignored, ré with accent is francais


def check_transpose():
    """Test Transposer."""
    t = Transposer(Pitch(0, 0, 0), Pitch(2, 0, 0))
    p = Pitch(0, 0, 0)
    t.transpose(p)
    assert p == Pitch(2, 0, 0)

    p = Pitch(6, 0, 0)
    t.transpose(p)
    assert p == Pitch(1, 0.5, 1)

    t = Transposer(Pitch(0, 0, 0), Pitch(2, 0, 0))
    music = read.lily_document("{ c d e f g }")
    transpose_node(music, t)
    assert music.write() == "{ e fis gis a b }"
    transpose_node(music, t)
    assert music.write() == "{ gis ais bis cis' dis' }"

    t = Transposer(Pitch(0, 0, 0), Pitch(0, 0, 1))
    music = read.lily_document(r"\relative { c' d e f g }")
    transpose_node(music, t)
    assert music.write() == r"\relative { c'' d e f g }"

    t = Transposer(Pitch(0, 0, 0), Pitch(4, 0, 0))
    music = read.lily_document(r"\relative c' { c d e f g }")
    transpose_node(music, t)
    assert music.write() == r"\relative g' { g a b c d }"

    t = Transposer(Pitch(0, 0, 0), Pitch(6, -.5, -1))
    music = read.lily_document(r"\relative { g a b c d }")
    transpose_node(music, t, relative_first_pitch_absolute=False)
    assert music.write() == r"\relative { f, g a bes c }"

    music = read.lily_document(r"\relative { g a b c d }")
    transpose_node(music, t, relative_first_pitch_absolute=True)
    assert music.write() == r"\relative { f g a bes c }"

    music = read.lily_document("""\\version "2.12.0"\n\\relative { g a b c d }\n""")
    transpose_node(music, t)
    assert music[1].write() == r"\relative { f, g a bes c }"

    music = read.lily_document("""\\version "2.22.0"\n\\relative { g a b c d }\n""")
    transpose_node(music, t)
    assert music[1].write() == r"\relative { f g a bes c }"

    doc = parce.Document(find('lilypond'), "{ c d e f g }", transformer=True)
    cur = parce.Cursor(doc).select(4, 7)
    t = Transposer(Pitch(0, 0, 0), Pitch(2, 0, 0))
    transpose(cur, t)
    assert doc.text() == "{ c fis gis f g }"    # only two notes changed



def test_main():
    """Main test function."""
    check_pitch()
    check_transpose()


if __name__ == "__main__" and 'test_main' in globals():
    test_main()
