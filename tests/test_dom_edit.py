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

import pytest

### find quickly
import sys
sys.path.insert(0, '.')



import parce

import quickly
from quickly.registry import find
from quickly.dom import lily, util



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

    ### the new Unknown element....
    # Now we test the quickly transformer, which handles unknown pieces of text.
    d = parce.Document(find('html'),
        r'<p style="color:red;"><lilypond> { c d e f g } </lilypond></p>', transformer=True)
    music = d.get_transform(True)
    for note in music // lily.Note('e'):
        note.head = 'fis'
    assert music.edit(d) == 1
    # NOTE we don't loose any text!!
    assert d.text() == r'<p style="color:red;"><lilypond> { c d fis f g } </lilypond></p>'

    # Again test a document with two music pieces in it:
    d = parce.Document(find('html'),
        '<p style="color:red;"><lilypond> { c d e f g } </lilypond></p>\n'
        '<p style="color:red;"><lilypond> { a b c d e } </lilypond></p>\n',
        transformer=True)
    music = d.get_transform(True)

    # Now we do not store positions. Bluntly perform the manipulations!
    for note in music // lily.Note('e'):
        note.head = 'fis'

    # And then bluntly edit the full document. "Unknown" elements will simply be
    # skipped, as they are never modified.
    assert music.edit(d) == 2
    assert d.text() == '<p style="color:red;"><lilypond> { c d fis f g } </lilypond></p>\n' \
                     + '<p style="color:red;"><lilypond> { a b c d fis } </lilypond></p>\n'

    # writing out should raise a RuntimeError, as Unknown elements do not know
    # the text they should print
    with pytest.raises(RuntimeError):
        music.write()

    # but after replacing the Unknown elements, it should work:
    music = d.get_transform(True)
    util.replace_unknown(music, d.text())
    assert music.write() == '<p style="color:red;"><lilypond>{ c d fis f g }</lilypond></p>\n' \
                          + '<p style="color:red;"><lilypond>{ a b c d fis }</lilypond></p>\n'







if __name__ == "__main__" and 'test_main' in globals():
    test_main()
