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
Test DOM document editing features.
"""

### find quickly
import sys
sys.path.insert(0, '.')



import parce

import quickly
from quickly.registry import find
from quickly.dom import lily



def test_main():
    """Main test function."""

    d = parce.Document(find('lilypond'), "{ c d e f g }", transformer=True)
    music = d.get_transform(True)
    for note in music // lily.Note('e'):
        note.head = 'fis'
    assert music.edit(d) == 1
    assert d.text() == "{ c d fis f g }"



if __name__ == "__main__" and 'test_main' in globals():
    test_main()
