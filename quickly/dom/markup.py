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
_a = lambda v: _s(scm.create_element_from_value(v))
_q = lambda n: _s(scm.Quote("'", n))
_sym = lambda s: _q(scm.Identifier(s))
_pair = lambda x, y: _q(scm.List(
    scm.create_element_from_value(x), scm.Dot(), scm.create_element_from_value(y)))


_RE_MATCH_MARKUP = re.compile(parce.lang.lilypond.RE_LILYPOND_MARKUP_TEXT).fullmatch


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


@_autotext
def markup(*args):
    r"""Return `\markup`; automatically wraps arguments in brackets."""
    return lily.Markup(r'\markup', lily.MarkupList(*args))

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
    return _c('from-property', _sym(name))

def harp_pedal(s):
    return _c('harp-pedal', lily.String(s))

def hspace(n):
    return _c('hspace', _s(scm.Int(n)))

def justify_field(name):
    return _c('justify-field', _sym(name))

def justify_string(s):
    return _c('justify-string', _s(scm.String(s)))

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

def wordwrap_field(name):
    return _c('wordwrap-field', _sym(name))

def wordwrap_string(s):
    return _c('wordwrap-string', _s(scm.String(s)))


#### two arguments
#### (those that are not mentioned here are created automatically)

def abs_fontsize(n, *args):
    return _c('abs-fontsize', _s(scm.Float(n)), create_list(args))

def customTabClef(num_strings, staff_space):
    r"""The ``\customTabClef`` command (int, float)."""
    return _c('customTabClef', _s(scm.Int(num_strings)), _s(scm.Float(staff_space)))

def fontsize(n, *args):
    return _c('fontsize', _s(scm.Float(n)), create_list(args))

def hcenter_in(n, *args):
    return _c('hcenter-in', _s(scm.Float(n)), create_list(args))

def lower(n, *args):
    return _c('lower', _s(scm.Float(n)), create_list(args))

def magnify(n, *args):
    return _c('magnify', _s(scm.Float(n)), create_list(args))

def map_markup_commands(procedure, *args):
    r"""The ``\map-markup-commands`` command (Scheme procedure, markups)."""
    return _c('map-markup-commands', procedure, create_list(args))

def note(duration, direction):
    r"""The ``\note`` command.

    The ``duration`` can be a markup object containing a word that is a duration, e.g.
    ``4..`` (for LilyPond >= 2.22) or a Scheme string like ``#"4.."`` (for
    LilyPond < 2.22).

    The ``direction is a floating point value; the sign is the stem direction,
    the value the stem length.

    """
    return _c('note', duration, _s(scm.Float(direction)))

def on_the_fly(procedure, *args):
    r"""The ``\on-the-fly`` command (Scheme procedure, markups)."""
    return _c('on-the-fly', procedure, create_list(args))

def override(prop, value, *args):
    r"""The ``\override`` command.

    The ``prop`` should be a string, the ``value`` a Scheme value (Python bool, int
    or float are handled automatically).

    """
    value = scm.create_element_from_value(value)
    return _c('override', _pair(scm.Identifier(prop), value), create_list(args))

def override_lines(prop, value, *args):
    r"""The ``\override-lines`` command.

    The ``prop`` should be a string, the ``value`` a Scheme value (Python bool, int
    or float are handled automatically).

    """
    value = scm.create_element_from_value(value)
    return _c('override-lines', _pair(scm.Identifier(prop), value), create_list(args))

def pad_around(n, *args):
    return _c('pad-around', _s(scm.Float(n)), create_list(args))

def pad_markup(n, *args):
    return _c('pad-markup', _s(scm.Float(n)), create_list(args))

def pad_x(n, *args):
    return _c('pad-x', _s(scm.Float(n)), create_list(args))

def page_link(n, *args):
    return _c('page-link', _s(scm.Int(n)), create_list(args))

def path(thickness, commands):
    r"""The ``\path`` command (thickness is float, commands is SchemeExpression)."""
    return _c('path', _s(scm.Float(thickness)), commands)

def raise_(n, *args):
    return _c('raise', _s(scm.Float(n)), create_list(args))

def replace(scheme, *args):
    return _c('replace', scheme, create_list(args))

def rest_by_number(log, dotcount):
    r"""The ``\rest-by-number`` command (int log, int dotcount)."""
    return _c('rest-by-number', _s(scm.Int(log)), _s(scm.Int(dotcount)))

def rotate_(angle, *args):
    return _c('raise', _s(scm.Float(angle)), create_list(args))

def scale(x, y, *args):
    return _c('scale', _pair(x, y), create_list(args))

def table(column_align, *args):
    r"""The ``\table`` command (scheme column_align, markups args)."""
    return _c('table', column_align, create_list(args))

def translate(x, y, *args):
    return _c('translate', _pair(x, y), create_list(args))

def translate_scaled(x, y, *args):
    return _c('translate-scaled', _pair(x, y), create_list(args))

def with_color(scheme, *args):
    return _c('with-color', scheme, create_list(args))

def with_link(label, *args):
    return _c('with-color', _sym(label), create_list(args))

def with_url(url, *args):
    return _c('with-url', _s(scm.String(url)), create_list(args))

def woodwind_diagram(instrument, scheme_commands):
    return _c('woodwind-diagram', _sym(label), scheme_commands)


#### three arguments

def arrow_head(axis, direction, filled):
    r"""The ``\arrow-head`` command.

    Axis, direction are numbers, filled is True/False.

    """
    return _c('arrow-head',
        _s(scm.create_element_from_value(axis)),
        _s(scm.create_element_from_value(direcion)),
        _s(scm.create_element_from_value(filled)))

def beam(width, slope, thickness):
    return _c('beam', _a(width), _a(slope), _a(thickness))

def draw_circle(radius, thickness, filled):
    r"""The ``\draw-circle`` command.

    Radius, thickness are numbers, filled is True/False.

    """
    return _c('draw-circle', _a(radius), _a(thickness), _a(filled))

def draw_squiggle_line(sqlength, x, y, eqend):
    return _c('draw-squiggle-line', _a(sqlength), _pair(x, y), _a(eqend))

def epsfile(axis, size, filename):
    return _c('epsfile', _a(axis), _a(size), _a(filename))

def filled_box(x1, y1, x2, y2, blot):
    return _c('filled-box', _pair(x1, x2), _pair(y1, y2), _a(blot))

def general_align(axis, direction, *args):
    return _c('general-align', _a(axis), _a(direction), create_list(args))

def note_by_number(log, dotcount, direction):
    return _c('note-by-number', _s(scm.Int(log)), _s(scm.Int(dotcount)), _a(direction))

def pad_to_box(x1, y1, x2, y2, *args):
    return _c('pad-to-box', _pair(x1, x2), _pair(y1, y2), create_list(args))

def page_ref(label, gauge, *mkup):
    return _c('page-ref', _sym(label), create_word(gauge), create_list(mkup))

def with_dimensions(x1, y1, x2, y2, *args):
    return _c('with-dimensions', _pair(x1, x2), _pair(y1, y2), create_list(args))


#### four arguments

def pattern(count, axis, space, *args):
    return _c('pattern', _s(scm.Int(count)), _s(scm.Int(axis)), _a(space),
        create_list(args))

def put_adjacent(axis, direction, arg1, *arg2):
    return _c('put-adjacent', _s(scm.Int(axis)), _a(direction),
        create_word(arg1), create_list(arg2))


#### five arguments

def fill_with_pattern(space, direction, pattern, left, right):
    return _c('fill-with-pattern',
        _a(space), _a(direction),
        create_word(pattern), create_word(left), create_word(right))




# helper functions

def is_markup(text):
    """Return True if the text can be written as LilyPond markup without quotes."""
    return bool(_RE_MATCH_MARKUP(text))


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
    factories = (
        (lambda n: lambda: _c(n)),
        (lambda n: lambda *text: _c(n, create_list(text))),
        (lambda n: lambda arg, *text: _c(n, create_word(arg), create_list(text))),
        None,
        None,
    )

    for argcount, factory in enumerate(factories):
        for cmd in w.markup_commands_nargs[argcount]:
            name = cmd.replace('-', '_')
            doc = r"The ``\{}`` markup command.".format(cmd)
            try:
                f = globals()[name]
            except KeyError:
                if factory:
                    func = factory(cmd)
                    func.__name__ = name
                    func.__doc__ = doc
                    globals()[name] = func
            else:
                if not f.__doc__:
                    f.__doc__ = doc



main()
del main
