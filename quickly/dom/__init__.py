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
This module defines a DOM (Document Object Model) for LilyPond source files.
"""


from parce.transform import Transformer

from .base import Item
from .items import *


def node(text, lexicon=None):
    """Build a Item node from text using lexicon (LilyPond.root if not
    specified).

    """
    from quickly.lang.lilypond import LilyPond, LilyPondAdHoc
    t = Transformer()
    t.add_transform(LilyPond, LilyPondAdHoc())
    n = t.transform_text(lexicon or LilyPond.root, text)
    return n[0] if isinstance(n, Document) and len(n) else n


def document(text):
    """Build a Document from the specified text."""
    from quickly.lang.lilypond import LilyPond, LilyPondAdHoc
    t = Transformer()
    t.add_transform(LilyPond, LilyPondAdHoc())
    return t.transform_text(LilyPond.root, text)

