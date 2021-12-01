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
Test the functions in dom.util
"""

### find quickly
import sys
sys.path.insert(0, '.')

from quickly.dom import util, read



def test_main():
    assert util.whitespace_key('\n\n  ') == (2, 2)
    assert util.whitespace_key('') == (0, 0)
    assert util.whitespace_key(' ') == (0, 1)
    assert util.whitespace_key('\n\n') == (2, 0)
    assert util.whitespace_key('  ') == (0, 2)

    assert util.combine_text((
        ('\n', 'hallo', ' '),
        ('\n', 'hallo', ' '),
        (' ', 'hallo', ''),
        (' ', 'hallo', ''),
        ('', 'hallo', '\n'),
    )) == ('\n', 'hallo\nhallo hallo hallohallo', '\n')


    s = r"""(define (attribute-escape s)
  (string-substitute "\n" "&#10;"
    (string-substitute "\"" "&quot;"
      (string-substitute "&" "&amp;"
        s))))
"""
    d = read.scm(s, True)
    util.add_newlines(d, s)
    assert d.write_indented() == \
r"""(define (attribute-escape s)
  (string-substitute "n" "&#10;"
    (string-substitute "\"" "&quot;"
      (string-substitute "&" "&amp;"
        s))))
"""
    assert d.write_indented(max_align_indent=20) == \
r"""(define (attribute-escape s)
  (string-substitute "n" "&#10;"
                     (string-substitute "\"" "&quot;"
                                        (string-substitute "&" "&amp;"
                                                           s))))
"""




if __name__ == "__main__" and 'test_main' in globals():
    test_main()
