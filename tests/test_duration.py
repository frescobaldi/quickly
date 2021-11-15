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
Test quickly.duration.
"""

from fractions import Fraction

### find quickly
import sys
sys.path.insert(0, '.')


from quickly.duration import *


def test_main():

    assert log_dotcount(7/16) == (2, 2)
    assert log_dotcount(Fraction(3, 4)) == (1, 1)

    assert to_string(1) == "1"
    assert to_string(1/2) == "2"
    assert to_string(1/4) == "4"
    assert to_string(3/8) == "4."
    assert to_string(7/16) == "4.."

    assert to_string(Fraction(1, 2)) == "2"
    assert to_string(Fraction(1, 4)) == "4"
    assert to_string(Fraction(3, 8)) == "4."
    assert to_string(Fraction(7, 16)) == "4.."

    assert from_string("2...") == Fraction(15, 16)
    assert from_string(" \\longa ") == 4
    assert from_string("breve") == 2
    assert from_string("breve.") == 3
    assert from_string("breve..") == Fraction(7, 2)
    assert from_string("breve...") == Fraction(15, 4)
    assert from_string("4") == Fraction(1, 4)
    assert from_string("8") == Fraction(1, 8)
    assert from_string("16") == Fraction(1, 16)
    assert from_string("32") == Fraction(1, 32)
    assert from_string("64") == Fraction(1, 64)
    assert from_string("64.") == Fraction(3, 128)

    assert shift_duration(Fraction(1, 8), -1) == Fraction(1, 4)
    assert to_string(shift_duration(from_string('2'), 1, 1)) == '4.'


if __name__ == "__main__" and 'test_main' in globals():
    test_main()
