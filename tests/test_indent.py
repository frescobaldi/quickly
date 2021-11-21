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
Test the indenting features
"""

### find quickly
import sys
sys.path.insert(0, '.')

from quickly.dom import lily, scm, read, indent





def test_main():

    d = read.lily_document("{ { c d e f g } }")
    assert d.write_indented() == '{ { c d e f g } }\n'

    next(d // lily.Note('d')).space_after = '\n'
    assert d.write_indented() == '''\
{ { c d
    e f g } }
'''

    d = read.scm_document("(if a b c)")
    next(d // scm.Identifier('a')).space_after = '\n'
    assert d.write_indented() == '''\
(if a
    b c)
'''

    d = read.scm_document("((if a b c))")
    next(d // scm.Identifier('a')).space_after = '\n'
    assert d.write_indented() == '''\
((if a
     b c))
'''

    d = read.scm_document('((string-append "een" "twee" "drie"))')
    for n in d[0][0][2:]:
        n.space_before = '\n'   # twee and drie on new line
    assert d.write_indented() == '''\
((string-append "een"
                "twee"
                "drie"))
'''

    d = read.scm_document('((blaat) (string-append "een" "twee" "drie"))')
    for n in d[0][1][2:]:
        n.space_before = '\n'   # twee and drie on new line
    assert d.write_indented() == '''\
((blaat) (string-append "een"
   "twee"
   "drie"))
'''

    assert d.write_indented(max_align_indent=24) == '''\
((blaat) (string-append "een"
                        "twee"
                        "drie"))
'''



if __name__ == "__main__" and 'test_main' in globals():
    test_main()
