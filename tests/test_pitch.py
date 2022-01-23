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
Test pitch related functions (pitch, transpose, relative, ...)
"""

import pytest

### find quickly
import sys
sys.path.insert(0, '.')

import parce

import quickly
from quickly.pitch import (
    Pitch, PitchProcessor, octave_to_string, octave_from_string, determine_language)
from quickly.transpose import Transposer, Transpose
from quickly.relative import Abs2rel, Rel2abs, abs2rel, rel2abs
from quickly.dom import read, lily
from quickly.registry import find


def lydoc(text):
    """Return a parce LilyPond doc with text."""
    return parce.Document(find('lilypond'), text, transformer=True)


def check_pitch():
    """Test pitch manipulations."""
    p = PitchProcessor()
    c = Pitch(-1, 0, 0)
    cis = Pitch(-1, 0, 0.5)
    d = Pitch(-1, 1, 0)
    dis = Pitch(-1, 1, 0.5)
    disis = Pitch(-1, 1, 1)

    assert 'c' == p.to_string(c)
    assert 'cis' == p.to_string(cis)

    p.language = 'english'
    assert 'cs' == p.to_string(cis)
    p.prefer_long = True
    assert 'c-sharp' == p.to_string(cis)

    p.language = 'français'
    p.prefer_accented = True
    assert 'ré' == p.to_string(d)

    p.prefer_x = True
    assert 'réx' == p.to_string(disis)
    p.prefer_x = False
    assert 'rédd' == p.to_string(disis)
    p.prefer_accented = False
    p.prefer_x = True
    assert 'rex' == p.to_string(disis)
    p.prefer_x = False
    assert 'redd' == p.to_string(disis)

    with pytest.raises(KeyError):
        p.language = "does_not_exist"

    p.language = "english"
    assert 'c-sharp' == p.to_string(cis)

    del p.language
    assert p.language == "nederlands"
    assert p.pitch('dis') == dis

    p.language = 'français'
    assert p.pitch('réx') == disis
    assert p.pitch('rex') == disis
    assert p.pitch('rédd') == disis
    assert p.pitch('redd') == disis

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
    p = PitchProcessor("français")
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
    with pp.process(n) as p:
        p.note += 2
        p.octave = 0
    assert n.head == 'e'
    assert n.octave == 1

    # Pitch class
    assert Pitch(0, 0, 0) < Pitch(0, 0, 1)
    assert Pitch(0, 0, 0) > Pitch(-1, 1, 0)
    assert Pitch(0, 1, .25) == Pitch(0, 1, .25)


    # other functions
    assert octave_to_string(3) == "'''"
    assert octave_to_string(-3) == ",,,"
    assert octave_from_string(",") == -1
    assert octave_from_string("''") == 2
    assert octave_from_string("',") == 0

    assert list(determine_language(['c', 'd', 'e', 'f', 'g'])) == \
        ['nederlands', 'english', 'deutsch', 'norsk', 'suomi', 'svenska', 'arabic', 'bagpipe']
    assert list(determine_language(['c', 'd', 'es', 'f', 'g'])) == \
        ['nederlands', 'english', 'deutsch', 'norsk', 'suomi']
    assert list(determine_language(['c', 'd', 'es', 'fis', 'g', 'bis'])) == \
        ['nederlands']
    assert list(determine_language(['c', 'do'])) == [] # ambiguous
    assert list(determine_language(['do', 'ré', 'r'])) == \
        ['français']    # r is ignored, ré with accent is français


def check_transpose():
    """Test Transposer."""
    t = Transposer(Pitch(0, 0, 0), Pitch(0, 2, 0))
    p = Pitch(0, 0, 0)
    t.transpose(p)
    assert p == Pitch(0, 2, 0)

    p = Pitch(0, 6, 0)
    t.transpose(p)
    assert p == Pitch(1, 1, 0.5)

    t = Transposer(Pitch(0, 0, 0), Pitch(0, 2, 0))
    music = read.lily_document("{ c d e f g }")
    Transpose(t).edit_node(music)
    assert music.write() == "{ e fis gis a b }"
    Transpose(t).edit_node(music)
    assert music.write() == "{ gis ais bis cis' dis' }"

    t = Transposer(Pitch(0, 0, 0), Pitch(1, 0, 0))
    music = read.lily_document(r"\relative { c' d e f g }")
    Transpose(t).edit_node(music)
    assert music.write() == r"\relative { c'' d e f g }"

    t = Transposer(Pitch(0, 0, 0), Pitch(0, 4, 0))
    music = read.lily_document(r"\relative c' { c d e f g }")
    Transpose(t).edit_node(music)
    assert music.write() == r"\relative g' { g a b c d }"

    t = Transposer(Pitch(0, 0, 0), Pitch(0, 1, 0))
    music = read.lily_document(r"\relative { c' d' e, f g }")
    Transpose(t).edit_node(music)
    assert music.write() == r"\relative { d' e' fis, g a }"

    t = Transposer(Pitch(0, 0, 0), Pitch(-1, 6, .5))
    music = read.lily_document(r"\relative { c' d' e, f g }")
    Transpose(t, relative_first_pitch_absolute=True).edit_node(music)
    assert music.write() == r"\relative { bis cisis' disis, eis fisis }"

    t = Transposer(Pitch(0, 0, 0), Pitch(-1, 6, .5))
    music = read.lily_document(r"\relative c' { c d' e, f g }")
    Transpose(t, relative_first_pitch_absolute=True).edit_node(music)
    assert music.write() == r"\relative bis { bis cisis' disis, eis fisis }"

    t = Transposer(Pitch(0, 0, 0), Pitch(-1, 6, -.5))
    music = read.lily_document(r"\relative { g a b c d }")
    Transpose(t, relative_first_pitch_absolute=False).edit_node(music)
    assert music.write() == r"\relative { f, g a bes c }"

    music = read.lily_document(r"\relative { g a b c d }")
    Transpose(t, relative_first_pitch_absolute=True).edit_node(music)
    assert music.write() == r"\relative { f g a bes c }"

    music = read.lily_document("""\\version "2.12.0"\n\\relative { g a b c d }\n""")
    Transpose(t).edit_node(music)
    assert music[1].write() == r"\relative { f, g a bes c }"

    music = read.lily_document("""\\version "2.22.0"\n\\relative { g a b c d }\n""")
    Transpose(t).edit_node(music)
    assert music[1].write() == r"\relative { f g a bes c }"

    doc = lydoc("{ c d e f g }")
    cur = parce.Cursor(doc).select(4, 7)
    t = Transposer(Pitch(0, 0, 0), Pitch(0, 2, 0))
    Transpose(t).edit_cursor(cur)
    assert doc.text() == "{ c fis gis f g }"    # only two notes changed


def check_relative():
    """Test functions in the relative module."""
    doc = lydoc("{ c' d' e' f' g' }")
    abs2rel(doc)
    assert doc.text() == r"\relative c' { c d e f g }"

    doc = lydoc("{ c' d' e' f' g' }")
    Abs2rel(start_pitch=False).edit(doc)
    assert doc.text() == r"\relative { c d e f g }"

    doc = lydoc("{ c' d' e' f' g' }")
    Abs2rel(start_pitch=False, first_pitch_absolute=True).edit(doc)
    assert doc.text() == r"\relative { c' d e f g }"

    doc = lydoc("{ { c' d' e' f' g' } { d' e' fis' g' a' } }")
    Abs2rel(start_pitch=False, first_pitch_absolute=True).edit(doc)
    assert doc.text() == r"{ \relative { c' d e f g } \relative { d' e fis g a } }"

    doc = lydoc("{ c { c' d' e' f' g' } { d' e' fis' g' a' } }")
    cur = parce.Cursor(doc)
    Abs2rel(start_pitch=False, first_pitch_absolute=True).edit(cur)
    assert doc.text() == r"\relative { c { c' d e f g } { d e fis g a } }"

    doc = lydoc("{ c { c' d e' f g' } { d' e'' fis' g a' } }")
    cur = parce.Cursor(doc)
    Abs2rel(start_pitch=False, first_pitch_absolute=True).edit(cur)
    assert doc.text() == r"\relative { c { c' d, e' f, g' } { d e' fis, g, a' } }"


def test_main():
    """Main test function."""
    check_pitch()
    check_transpose()
    check_relative()


if __name__ == "__main__" and 'test_main' in globals():
    test_main()
