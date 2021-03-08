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
Test quickly.numbering
"""

### find quickly
import sys
sys.path.insert(0, '.')

import quickly





def test_main():

    from quickly.numbering import (
        int2roman, int2text, int2letter, letter2int, roman2int, text2int)

    assert int2roman(2021) == "MMXXI"
    assert int2roman(1967) == "MCMLXVII"

    for val in range(1, 9999):
        assert roman2int(int2roman(val)) == val

    assert int2text(12345) == "TwelveThousandThreeHundredFortyFive"
    assert text2int("ThousandTwoHundred") == 1200

    for val in range(9999):
        assert text2int(int2text(val)) == val

    assert int2letter(27) == "AA"
    assert letter2int("AB") == 28

    for val in range(9999):
        assert letter2int(int2letter(val)) == val



if __name__ == "__main__" and 'test_main' in globals():
    test_main()
