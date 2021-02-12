# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Helper module for manually constructing markup elements.

Usage example::

    >>> import quickly.dom.markup as m
    >>> mkup = m.markup(m.bold("text", "text2"))
    >>> mkup.write()

"""

import re
import functools

import parce.lang.lilypond
import parce.lang.lilypond_words as w

from . import base, element, lily, scm

_c = lily.MarkupCommand
_s = lambda n: lily.SchemeExpression('#', n)

RE_MATCH_MARKUP = re.compile(parce.lang.lilypond.RE_LILYPOND_MARKUP_TEXT).fullmatch

def _autolist(func):
    """Decorator that automatically wraps arguments in a markup list if not one."""
    @functools.wraps(func)
    def decorator(*args):
        return func(create_list(args))
    return decorator

def _autotext(func):
    """Decorator that automatically creates the correct node for text """
    @functools.wraps(func)
    def decorator(*args):
        args = [create_word(arg) for arg in args]
        return func(*args)
    return decorator


@_autolist
def markup(arg):
    r"""Return `\markup`; automatically wraps more arguments in a brackets."""
    return lily.Markup(r'\markup', arg)


@_autotext
def markuplist(*args):
    r"""Return `\markuplist`; automatically wraps arguments in brackets."""
    return lily.Markup(r'\markuplist', lily.MarkupList(*args))


#### one argument commands
#### (those that are not mentioned here are created automatically)

def backslashed_digit(n):
    return _c('backslashed-digit', _s(scm.Int(n)))

def char(n):
    return _c('char', _s(scm.Hex(n)))

def tied_lyric(text):
    return _c('tied-lyric', _s(scm.String(text)))

def fret_diagram(s):
    return c_('fret-diagram', _s(scm.String(s)))

def fret_diagram_terse(s):
    return c_('fret-diagram-terse', _s(scm.String(s)))

def fret_diagram_verbose(element):
    return c_('fret-diagram-verbose', element)

def from_property(name):
    return _c('from-property', _s(scm.Quote("'", scm.Identifier(name))))

def harp_pedal(s):
    return _c('harp-pedal', lily.String(s))

def hspace(n):
    return _c('hspace', _s(scm.Int(n)))

def lookup(s):
    return _c('lookup', _s(scm.String(s)))

def markalphabet(n):
    return _c('markalphabet', _s(scm.Int(n)))

def markletter(n):
    return _c('markletter', _s(scm.Int(n)))

def musicglyph(name):
    return _c('musicglyph', _s(scm.String(name)))

def postscript(s):
    if isinstance(s, str):
        s = _s(scm.String(s))
    return _c('postscript', s)

def rest(s):
    return _c('rest', lily.String(s))

def score(*elements):
    r"""The ``\score`` command. You may give Header, Layout and general Music nodes."""
    return lily.MarkupScore(*elements)

def score_lines(*elements):
    r"""The ``\score-lines`` command. You may give Header, Layout and general Music nodes."""
    return lily.MarkupScoreLines(*elements)

def slashed_digit(n):
    return _c('slashed-digit', _s(scm.Int(n)))

def triangle(filled):
    return _c('triangle', _s(scm.Bool(filled)))

def vspace(n):
    return _c('vspace', _s(scm.Int(n)))

def verbatim_file(filename):
    return _c('verbatim-file', _s(scm.String(filename)))


#### two arguments

def abs_fontsize(n, *args):
    arg = create_list(map(create_word, args))
    return _c('abs-fontsize', _s(scm.Float(n)), arg)

def auto_footnote(mkup, *text):
    return _c('auto-footnote', create_word(mkup), create_list(text))

def combine(mkup1, mkup2):
    return _c('combine', create_word(mkup1), create_word(mkup2))

def customTabClef(num_strings, staff_space):
    r"""The ``\customTabClef`` command (int, float)."""
    return _c('customTabClef', _s(scm.Int(num_strings)), _s(scm.Float(staff_space)))

def fontsize(n, *args):
    arg = create_list(map(create_word, args))
    return _c('fontsize', _s(scm.Float(n)), arg)

def footnote(mkup, *text):
    return _c('footnote', create_word(mkup), create_list(text))







def is_markup(text):
    """Return True if the text can be written as LilyPond markup without quotes."""
    return bool(RE_MATCH_MARKUP(text))



def create_list(args):
    """Create a MarkupList when number of arguments is not 1.

    Also calls :func:`create_word` on every argument.

    """
    if len(args) == 1:
        return create_word(args[0])
    return lily.MarkupList(*map(create_word, args))


def create_word(arg):
    """If arg is a str, return String or MarkupWord. Otherwise, return unchanged."""
    if isinstance(arg, str):
        return lily.MarkupWord(arg) if is_markup(arg) else lily.String(arg)
    return arg


def main():
    """Auto-create markup factory functions."""
    no_arg = lambda n: lambda: _c(n)
    one_arg = lambda n: _autolist(lambda arg: _c(n, arg))

    for argcount, factory in enumerate((no_arg, one_arg)):
        for cmd in w.markup_commands_nargs[argcount]:
            name = cmd.replace('-', '_')
            doc = r"The ``\{}`` markup command.".format(cmd)
            try:
                f = globals()[name]
            except KeyError:
                func = factory(cmd)
                func.__name__ = name
                func.__doc__ = doc
                globals()[name] = func
            else:
                if not f.__doc__:
                    f.__doc__ = doc



main()
del main
