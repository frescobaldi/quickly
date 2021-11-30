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
Test the DOM by comparing manually built tree with parsed trees,
and re-parsing the output of the trees where that makes sense.

"""

### find quickly
import sys
sys.path.insert(0, '.')

import quickly


import fractions

from parce.transform import transform_text
from quickly.lang import html, lilypond, scheme, latex
from quickly.dom import htm, lily, scm, tex


def check_output(root_lexicon, text, tree):
    """Return True when transforming text with root lexicon gives the same tree
    as the one specified.
    """
    tree2 = transform_text(root_lexicon, text)
    return tree.equals(tree2)






def test_main():

    assert check_output(
        lilypond.LilyPond.root, "{c4}",
        lily.Document(
            lily.MusicList(
                lily.Note('c',
                    lily.Duration(
                        fractions.Fraction(1, 4)))))
    )

    assert check_output(
        latex.Latex.root, "$x+2$",
            tex.Document(tex.MathInlineDollar(tex.Text('x+2'))))

    assert check_output(
        latex.Latex.root, r"\lilypond[staffsize=26]{ { c\breve^\markup \italic { YO! } d'4 } }text.",
            tex.Document(
                tex.Command('lilypond',
                    tex.Option(tex.Text('staffsize=26')),
                    tex.Brace(
                        lily.Document(
                            lily.MusicList(
                                lily.Note('c',
                                    lily.Duration(2),
                                    lily.Articulations(
                                        lily.Direction(1,
                                            lily.Markup(r'markup',
                                                lily.MarkupCommand('italic',
                                                    lily.MarkupList(
                                                        lily.MarkupWord("YO!"))))))),
                                lily.Note('d',
                                    lily.Octave(1),
                                    lily.Duration(fractions.Fraction(1, 4))))))),
                tex.Text('text.')))




if __name__ == "__main__" and 'test_main' in globals():
    test_main()
