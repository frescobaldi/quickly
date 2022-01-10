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
Tests for rhythm module.
"""

### find quickly
import sys
sys.path.insert(0, '.')

from fractions import Fraction

import parce

import quickly
from quickly.rhythm import *
from quickly.dom import read


def test_main():
    """Main test function."""

    m = read.lily_document(r"{ c4 d e f g }")
    assert copy(m) == [(Fraction(1, 4), 1), None, None, None, None]

    paste(m, [(Fraction(1, 2), 1/2), None, None])
    assert m.write() == r"{ c2*1/2 d e f2*1/2 g }"

    # \skip does not change "previous" duration
    m = read.lily_document(r"{ c4 d e \skip 2 f g }")
    explicit(m)
    assert m.write() == r"{ c4 d4 e4 \skip 2 f4 g4 }"

    # \skip duration may not be removed
    remove(m)
    assert m.write() == r"{ c d e \skip 2 f g }"

    # duration may not be removed when immediate next is an Unpitched
    m = read.lily_document(r"{ c4 d8 8 8 g }")
    remove(m)
    assert m.write() == r"{ c d8 8 8 g }"

    # but when there is an articulation it is no problem:
    m = read.lily_document(r"{ c4 d8-- 8 8 g }")
    remove(m)
    assert m.write() == r"{ c d-- 8 8 g }"

    # both with paste None, result should be same
    m = read.lily_document(r"{ c4 d8 8 8 g }")
    paste(m, [None])
    assert m.write() == r"{ c d8 8 8 g }"
    m = read.lily_document(r"{ c4 d8-- 8 8 g }")
    paste(m, [None])
    assert m.write() == r"{ c d-- 8 8 g }"

    # lyrics
    m = read.lily_document(r"""\lyricmode { hoi4 \markup hoi "wil" -- bert }""")
    explicit(m)
    assert m.write() == r"""\lyricmode { hoi4 \markup hoi 4 "wil"4 -- bert4 }"""

    # implicit per line
    d = parce.Document(quickly.find('lilypond'), r'''
music = {
  c4 d8 e8 f8 g8 a4
  g f e4 d
  c d4 e2
}
''', transformer=True)
    implicit(d, True)
    assert d.text() == r'''
music = {
  c4 d8 e f g a4
  g4 f e d
  c4 d e2
}
'''

    # implicit per line, with unpitched that may not be removed
    d = parce.Document(quickly.find('lilypond'), r'''
music = {
  c4 d8 e8 f8 g8 a4
  g f e4 d
  c d4 4 4
}
''', transformer=True)
    implicit(d, True)
    assert d.text() == r'''
music = {
  c4 d8 e f g a4
  g4 f e d
  c4 d4 4 4
}
'''



if __name__ == "__main__" and 'test_main' in globals():
    test_main()
