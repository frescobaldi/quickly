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
from quickly.pitch import PitchNameProcessor, num_to_octave, octave_to_num



def test_main():
    """Main test function."""

    p = PitchNameProcessor()
    assert 'c' == p.write(0)
    assert 'cis' == p.write(0, 0.5)

    assert 'cs' == p.write(0, 0.5, 'english')
    p.prefer_long = True
    assert 'c-sharp' == p.write(0, 0.5, 'english')

    p.prefer_accented = True
    assert 'ré' == p.write(1, 0, 'francais')
    assert 'ré' == p.write(1, 0, 'français')

    p.prefer_x = True
    assert 'réx' == p.write(1, 1, 'francais')
    p.prefer_x = False
    assert 'rédd' == p.write(1, 1, 'francais')
    p.prefer_accented = False
    p.prefer_x = True
    assert 'rex' == p.write(1, 1, 'francais')
    p.prefer_x = False
    assert 'redd' == p.write(1, 1, 'francais')

    with pytest.raises(KeyError):
        p.language = "does_not_exist"

    p.language = "english"
    assert 'c-sharp' == p.write(0, 0.5)

    del p.language
    assert p.language == "nederlands"
    assert p.read('dis') == (1, 0.5)

    assert p.read('réx', 'francais') == (1, 1)
    assert p.read('rex', 'francais') == (1, 1)
    assert p.read('rédd', 'francais') == (1, 1)
    assert p.read('redd', 'francais') == (1, 1)

    # distill prefs
    w = PitchNameProcessor()
    w.distill_preferences(['es', 'g'])
    assert w.prefer_classic == True
    w.distill_preferences(['ees', 'g'])
    assert w.prefer_classic == False

    # a non-specific note does not change the pref
    w.distill_preferences(['fis', 'g'])
    assert w.prefer_classic == False
    w.prefer_classic = True
    w.distill_preferences(['fis', 'g'])
    assert w.prefer_classic == True

    # one note changes two prefs
    w = PitchNameProcessor()
    w.language = "francais"
    w.prefer_x = False
    w.prefer_accented = False
    w.distill_preferences(['réx'])
    assert w.prefer_x == True
    assert w.prefer_accented == True

    # unaccented pref set back
    w.distill_preferences(['red'])
    assert w.prefer_x == True
    assert w.prefer_accented == False

    # x pref set back
    w.distill_preferences(['redd'])
    assert w.prefer_x == False
    assert w.prefer_accented == False


    # other functions
    assert num_to_octave(3) == "'''"
    assert num_to_octave(-3) == ",,,"
    assert octave_to_num(",") == -1
    assert octave_to_num("''") == 2
    assert octave_to_num("',") == 0


if __name__ == "__main__" and 'test_main' in globals():
    test_main()
