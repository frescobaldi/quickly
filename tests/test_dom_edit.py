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
from quickly.dom import lily, transform



def test_main():
    """Main test function."""

    d = parce.Document(find('lilypond'), "{ c d e f g }", transformer=True)
    music = d.get_transform(True)
    for note in music // lily.Note('e'):
        note.head = 'fis'
    assert music.edit(d) == 1
    assert d.text() == "{ c d fis f g }"

    d = parce.Document(find('latex'), r"\lilypond{ { c d e f g } }", transformer=True)
    music = d.get_transform(True)
    for note in music // lily.Note('e'):
        note.head = 'fis'
    assert music.edit(d) == 1
    assert d.text() == r"\lilypond{ { c d fis f g } }"

    d = parce.Document(find('html'), r"<lilypond> { c d e f g } </lilypond>", transformer=True)
    music = d.get_transform(True)
    for note in music // lily.Note('e'):
        note.head = 'fis'
    assert music.edit(d) == 1
    assert d.text() == r"<lilypond> { c d fis f g } </lilypond>"


    ### below some tests with modifying tree with parce tokens that are
    ### not supported by quickly.dom, e.g. CSS tokens. Those are ignored by
    ### our transforms, so we should not rely on node.write() to produce
    ### complete output. Instead, we should only write in the reqions that
    ### are covered by Element types that are completely supported.
    d = parce.Document(find('html'), r'<p style="color:red;"><lilypond> { c d e f g } </lilypond></p>', transformer=True)
    music = d.get_transform(True)
    for note in music // lily.Note('e'):
        note.head = 'fis'
    assert music.edit(d) == 2
    # NOTE: we loose the contents of the style attribute, quickly cannot transform this
    assert d.text() == r'<p style=><lilypond> { c d fis f g } </lilypond></p>'

    # when modifying LilyPond documents within HTML or LaTeX, we should not
    # bluntly write the whole tree, instead just the LilyPond nodes.
    d = parce.Document(find('html'),
        '<p style="color:red;"><lilypond> { c d e f g } </lilypond></p>\n'
        '<p style="color:red;"><lilypond> { a b c d e } </lilypond></p>\n', transformer=True)
    music = d.get_transform(True)

    # We need to store the regions covered by the nodes we modify. Why?
    # Because deleting e.g. the first node that has an origin moves the ``pos``
    # attribute of the encompassing element node. When writing back, the text
    # of the deleted node would remain in the document.
    lily_documents = [(n, n.pos, n.end) for n in music // lily.Document]

    # now perform the manipulations
    for note in music // lily.Note('e'):
        note.head = 'fis'

    # Edit only the LilyPond dom nodes:
    with d:
        for node, pos, end in lily_documents:
            node.edit(d, start=pos, end=end)
    assert d.text() == '<p style="color:red;"><lilypond> { c d fis f g } </lilypond></p>\n' \
                     + '<p style="color:red;"><lilypond> { a b c d fis } </lilypond></p>\n'


    ### the new Unknown element....
    # Now we test the quickly transformer, which handles unknown pieces of text.
    d = parce.Document(find('html'),
        r'<p style="color:red;"><lilypond> { c d e f g } </lilypond></p>',
        transformer=transform.Transformer())
    music = d.get_transform(True)
    for note in music // lily.Note('e'):
        note.head = 'fis'
    assert music.edit(d) == 1
    # NOTE we don't loose any text!!
    assert d.text() == r'<p style="color:red;"><lilypond> { c d fis f g } </lilypond></p>'




if __name__ == "__main__" and 'test_main' in globals():
    test_main()
