# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2022 by Wilbert Berendsen <info@wilbertberendsen.nl>
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

### find quickly
import sys
sys.path.insert(0, '.')


from fractions import Fraction

import parce
import quickly
from quickly.time import Time
from quickly.dom import lily, read



def test_main():
    """Main test function."""
    d = parce.Document(quickly.find('lilypond'), r'''
music = { c4 d e f }

{ c2 \music g a b8 g f d }
''', transformer=True)

    m = d.get_transform(True)
    t = Time()
    assert t.duration(m[1][0], m[1][2]).time == 2       # length of "c2 \music g" part (g has duration 2)

    c = parce.Cursor(d, 44, 47)
    assert t.cursor_position(c).time == Fraction(11, 4) # length or music before the cursor
    assert t.cursor_duration(c).time == Fraction(1, 4)  # duration of the selected music

    m = read.lily(r"\tuplet 3/2 { c8 d e }")
    assert t.length(m) == Fraction(1, 4)
    assert t.length(m[1][1]) == Fraction(1, 12)         # one note in tuplet

    m = read.lily(r"\shiftDurations #1 #1 { c4 d e f }")
    assert t.length(m) == Fraction(3, 4)        # note value halved and dot added, so should be 3/4
    assert t.length(m[2][2]) == Fraction(3, 16) # autodiscovers the current duration transform



if __name__ == "__main__" and 'test_main' in globals():
    test_main()
