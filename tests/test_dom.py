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
from quickly.dom import htm, lily, scm, tex, read


def check_output(root_lexicon, text, tree):
    """Tests whether text->dom and dom->text works properly.

    Transforms text with root_lexicon, then returns True if the created tree
    compares equal with the given tree, and a tree transformed from the written
    output of the specified tree also compares equal.

    """
    tree2 = transform_text(root_lexicon, text)
    return tree.equals(tree2) and tree.equals(transform_text(root_lexicon, tree.write()))


def check_spanners():
    """Test various spanner features."""
    # find slur end with spanner id 1
    n = read.lily(r"{ c\=1( d e f g\=2) a\=1) }", True)
    slur = n.find_descendant(6)
    assert slur.find_parallel().pos == 24

    # find slur end with no spanner id
    n = read.lily(r"{ c( d e f g\=2) a) }", True)
    slur = n.find_descendant(3)
    assert slur.find_parallel().pos == 18

    # does not look outside music assignment
    n = read.lily_document(r"music = { c\=1( d e f } bmusic= { g\=2) a\=1) }", True)
    slur = n.find_descendant(15)
    assert slur.find_parallel() is None




def test_main():

    check_spanners()

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
        tex.Document(tex.MathInlineDollar(tex.Text('x+2')))
    )

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
            tex.Text('text.'))
    )

    assert check_output(
        latex.Latex.root, r"\begin[opts]{lilypond}music = { c }\end{lilypond}",
        tex.Document(
            tex.Environment(
                tex.Command('begin',
                    tex.Option(tex.Text('opts')),
                    tex.EnvironmentName('lilypond')),
                lily.Document(
                    lily.Assignment(
                        lily.Identifier(lily.Symbol('music')),
                        lily.EqualSign(),
                        lily.MusicList(
                            lily.Note('c')))),
                tex.Command('end',
                    tex.EnvironmentName('lilypond'))))
    )

    assert check_output(
        latex.Latex.root, r"\begin{lilypond}[opts]music = { c }\end{lilypond}",
        tex.Document(
            tex.Environment(
                tex.Command('begin',
                    tex.EnvironmentName('lilypond'),
                    tex.Option(tex.Text('opts'))),
                lily.Document(
                    lily.Assignment(
                        lily.Identifier(lily.Symbol('music')),
                        lily.EqualSign(),
                        lily.MusicList(
                            lily.Note('c')))),
                tex.Command('end',
                    tex.EnvironmentName('lilypond'))))
    )


if __name__ == "__main__" and 'test_main' in globals():
    test_main()
