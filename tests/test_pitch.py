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

import quickly
from quickly.pitch import PitchProcessor, num_to_octave, octave_to_num
from quickly.dom import read, lily


def test_main():
    """Main test function."""

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
    p = PitchProcessor()
    p.language = "francais"
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


    # other functions
    assert num_to_octave(3) == "'''"
    assert num_to_octave(-3) == ",,,"
    assert octave_to_num(",") == -1
    assert octave_to_num("''") == 2
    assert octave_to_num("',") == 0


if __name__ == "__main__" and 'test_main' in globals():
    test_main()
