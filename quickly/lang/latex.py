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
LaTeX language and transformation definition.
"""

import itertools

from parce import skip, lexicon, default_target
from parce.rule import bygroup, ifarg, ifeq, ifgroup
import parce.lang.tex
import parce.action as a

from quickly.dom import base, element, lily, scm
from . import lilypond


class Latex(parce.lang.tex.Latex):
    """Latex language definition."""
    @classmethod
    def get_environment_target(cls, name):
        return ifeq(name, "lilypond",
            (lilypond.LilyPond.latex_lilypond_environment, cls.test_lilypond_option),
            super().get_environment_target(name))

    @classmethod
    def common(cls):
        yield r'(\\lilypond)\s*(?:(\{)|(\[))?', bygroup(a.Name.Builtin, a.Delimiter.Brace, a.Delimiter), \
            ifgroup(2, lilypond.LilyPond.latex_lilypond_environment('short form'),
                ifgroup(3, cls.option("lilypond")))
        yield from super().common()

    @lexicon
    def option(cls):
        yield ifarg(r'(\])\s*(\{)'), bygroup(a.Delimiter, a.Delimiter.Brace), -1, \
                lilypond.LilyPond.latex_lilypond_environment('short form')
        yield from super().option
        yield r'\[', a.Delimiter.Bracket    # this can match if we were here looking for a [

    @lexicon
    def test_lilypond_option(cls):
        """One time check for Latex options at the beginning of a LilyPond environment.

        This lexicon never creates a context.

        """
        yield r'(?=\s*\[)', skip, -1, cls.option
        yield default_target, -1


class LatexTransform(base.Transform):
    """Transform Latex quickly.dom."""



class LatexAdHocTransform(base.AdHocTransform, LatexTransform):
    """LatexTransform that does not keep the origin tokens."""
    pass


