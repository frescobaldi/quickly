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
LilyPond language and transform definition
"""

from parce.transform import Transform
import parce.lang.lilypond


from quickly import dom



class LilyPond(parce.lang.lilypond.LilyPond):
    """LilyPond language definition."""




class LilyPondTransform(Transform):
    """Transform LilyPond to Music."""
    ## helper methods and factory
    def factory(self, item_class, origin, children=()):
        """Create an Item, keeping its origin.

        ``origin`` is an iterable of Token instances.

        """
        return item_class.with_origin(tuple(origin), *children)

    def common(self, items):
        """Find comment, string, scheme and markup."""
        for i in items:
            if not i.is_token:
                if i.name in (
                    "string", "multiline_comment", "singleline_comment"
                ):
                    yield i.obj


    ## transforming methods
    def root(self, items):
        return list(self.common(items))

    def book(self, items):
        return items

    def score(self, items):
        return items

    def header(self, items):
        return items

    def paper(self, items):
        return items

    def layout(self, items):
        return items

    def midi(self, items):
        return items

    def layout_context(self, items):
        return items

    def sequential(self, items):
        return items

    def simultaneous(self, items):
        return items

    def chord(self, items):
        return items

    def tempo(self, items):
        return items

    def context(self, items):
        return items

    def set_unset(self, items):
        return items

    def override(self, items):
        return items

    def script(self, items):
        return items

    def pitch(self, items):
        return items

    def duration(self, items):
        return items

    def duration_dots(self, items):
        return items

    def duration_scaling(self, items):
        return items

    def lyricmode(self, items):
        return items

    def lyricsto(self, items):
        return items

    def notemode(self, items):
        return items

    def drummode(self, items):
        return items

    def drummode_sequential(self, items):
        return items

    def drummode_simultaneous(self, items):
        return items

    def chordmode(self, items):
        return items

    def chord_modifier(self, items):
        return items

    def varname(self, items):
        return items

    def markup(self, items):
        return items

    def markuplist(self, items):
        return items

    def schemelily(self, items):
        return items

    def string(self, items):
        return self.factory(dom.String, items)

    def multiline_comment(self, items):
        return self.factory(dom.MultilineComment, items)

    def singleline_comment(self, items):
        return self.factory(dom.SinglelineComment, items)


