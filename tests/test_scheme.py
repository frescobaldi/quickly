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
Test Scheme transform.
"""

### find quickly
import sys
sys.path.insert(0, '.')

from quickly.dom import scm

from quickly.lang.scheme import Scheme
from parce.transform import transform_text


scheme_doc = """
; some constructs
(define var 'symbol)
(define (name args) (body))

; a list
(1 2 3 4 5)

; a partially quoted list
`(a b c ,@(d e f) g)

; a string
("a string")

; a hex value with fraction :-)
#xdead/beef

; same value in decimal
57005/48879
"""

def test_main():
    d = transform_text(Scheme.root, scheme_doc)
    assert len(d) == 13
    assert sum(1 for _ in d//scm.Number) == 7
    assert sum(1 for _ in d//scm.String) == 1
    assert sum(1 for _ in d//scm.Identifier) == 14

    # the two fractions
    assert d[10].head == d[12].head

    # does find_descendant work propery?
    assert d.find_descendant(40).head == "("
    assert d.find_descendant(41).head == "define"
    l = d.find_descendant(59)
    assert isinstance(l, scm.List)
    assert l.pos == 48

    # see if the output is correct, and when transformed again as well...
    output = d.write()
    d1 = transform_text(Scheme.root, output)
    assert d.equals(d1)
    assert output == d1.write()




if __name__ == "__main__" and 'test_main' in globals():
    test_main()
