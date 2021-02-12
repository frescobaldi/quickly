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
        if len(args) == 1:
            return func(args[0])
        return func(lily.MarkupList(*args))
    return decorator

def _autotext(func):
    """Decorator that automatically creates the correct node for text """
    @functools.wraps(func)
    def decorator(*args):
        args = [create_word(arg) for arg in args]
        return func(*args)
    return decorator


@_autotext
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

def from_property(name):
    return _c('from-property', _s(scm.Quote("'", scm.Identifier(name))))




def is_markup(text):
    """Return True if the text can be written as LilyPond markup without quotes."""
    return bool(RE_MATCH_MARKUP(text))

def create_word(arg):
    """If arg is a str, return String or MarkupWord. Otherwise, return unchanged."""
    if isinstance(arg, str):
        return lily.MarkupWord(arg) if is_markup(arg) else lily.String(arg)
    return arg


def main():
    no_arg = lambda n: lambda: _c(n)
    one_arg = lambda n: _autotext(_autolist(lambda arg: _c(n, arg)))

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
