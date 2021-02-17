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
Helper module to manually construct markup elements.

Usage example::

    >>> import quickly.dom.markup as m
    >>> mkup = m.markup(m.bold("text", "text2"))
    >>> mkup.write()
    '\\markup \\bold { text text2 }'
    >>> mkup.dump()
    <lily.Markup '\\markup' (1 child)>
     ╰╴<lily.MarkupCommand 'bold' (1 child)>
        ╰╴<lily.MarkupList (2 children)>
           ├╴<lily.MarkupWord 'text'>
           ╰╴<lily.MarkupWord 'text2'>

"""

import functools
import keyword
import re

import parce.lang.lilypond
import parce.lang.lilypond_words as w

from . import base, element, lily, scm


# helpers
_c = lily.MarkupCommand
_s = lambda n: lily.Scheme('#', n)
_a = lambda v: lily.Scheme('#', scm.create_element_from_value(v))
_q = lambda n: lily.Scheme('#', scm.Quote("'", n))
_sym = lambda s: lily.Scheme('#', scm.Quote("'", scm.Identifier(s)))
_pair = lambda x, y: lily.Scheme('#', scm.Quote("'", scm.p(x, y)))


_RE_MATCH_MARKUP = re.compile(parce.lang.lilypond.RE_LILYPOND_MARKUP_TEXT).fullmatch


def is_markup(text):
    """Return True if the text can be written as LilyPond markup without quotes."""
    return bool(_RE_MATCH_MARKUP(text))


def _create_list(args):
    """Create a MarkupList when number of arguments is not 1.

    Also calls :func:`_auto_arg` on every argument.

    """
    if len(args) == 1:
        return _auto_arg(args[0])
    return lily.MarkupList(*map(_auto_arg, args))


def _auto_arg(arg):
    """Create MarkupWord or Scheme if not already an Element.

    If arg is an element, it is returned unchanged. If arg is a :class:`str`, a
    :class:`~lily.MarkupWord` is created (or a :class:`~lily.String`, if there
    are non-printable characters). Otherwise, a Scheme expression is created of
    the corresponding type.

    """
    if isinstance(arg, element.Element):
        return arg
    elif isinstance(arg, str):
        return lily.MarkupWord(arg) if is_markup(arg) else lily.String(arg)
    return lily.Scheme('#', scm.create_element_from_value(arg))


def markup(*args):
    r"""Return `\markup`; automatically wraps arguments in brackets."""
    return lily.Markup(r'\markup', _create_list(args))


def markuplist(*args):
    r"""Return `\markuplist`; automatically wraps arguments in brackets."""
    return lily.Markup(r'\markuplist', lily.MarkupList(*map(_auto_arg, args)))


### markup commands with special agument handling

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


def fromproperty(name):
    return _c('fromproperty', _sym(name))


def harp_pedal(s):
    return _c('harp-pedal', lily.String(s))


def justify_field(name):
    return _c('justify-field', _sym(name))


def justify_string(s):
    return _c('justify-string', _s(scm.String(s)))


def lookup(s):
    return _c('lookup', _s(scm.String(s)))


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


def verbatim_file(filename):
    return _c('verbatim-file', _s(scm.String(filename)))


def wordwrap_field(name):
    return _c('wordwrap-field', _sym(name))


def wordwrap_string(s):
    return _c('wordwrap-string', _s(scm.String(s)))


def note(duration, direction):
    r"""The ``\note`` command.

    The ``duration`` can be a markup object containing a word that is a
    duration, e.g. ``4..`` (for LilyPond >= 2.22) or a Scheme string like
    ``#"4.."`` (for LilyPond < 2.22).

    The ``direction`` is a floating point value; the sign is the stem
    direction, the value the stem length.

    """
    return _c('note', duration, _s(scm.Float(direction)))


def override(prop, value, *args):
    r"""The ``\override`` command.

    The ``prop`` should be a string, the ``value`` a Scheme value (Python bool,
    int or float are handled automatically).

    """
    value = scm.create_element_from_value(value)
    return _c('override', _pair(scm.Identifier(prop), value), _create_list(args))


def override_lines(prop, value, *args):
    r"""The ``\override-lines`` command.

    The ``prop`` should be a string, the ``value`` a Scheme value (Python bool,
    int or float are handled automatically).

    """
    value = scm.create_element_from_value(value)
    return _c('override-lines', _pair(scm.Identifier(prop), value), _create_list(args))


def translate(x, y, *args):
    return _c('translate', _pair(x, y), _create_list(args))


def translate_scaled(x, y, *args):
    return _c('translate-scaled', _pair(x, y), _create_list(args))


def with_link(label, *args):
    return _c('with-color', _sym(label), _create_list(args))


def with_url(url, *args):
    return _c('with-url', _s(scm.String(url)), _create_list(args))


def woodwind_diagram(instrument, scheme_commands):
    return _c('woodwind-diagram', _sym(label), scheme_commands)


def draw_squiggle_line(sqlength, x, y, eqend):
    return _c('draw-squiggle-line', _a(sqlength), _pair(x, y), _a(eqend))


def epsfile(axis, size, filename):
    return _c('epsfile', _a(axis), _a(size), _a(filename))


def filled_box(x1, y1, x2, y2, blot):
    return _c('filled-box', _pair(x1, x2), _pair(y1, y2), _a(blot))


def note_by_number(log, dotcount, direction):
    return _c('note-by-number', _s(scm.Number(log)), _s(scm.Number(dotcount)), _a(direction))


def pad_to_box(x1, y1, x2, y2, *args):
    return _c('pad-to-box', _pair(x1, x2), _pair(y1, y2), _create_list(args))


def page_ref(label, gauge, *mkup):
    return _c('page-ref', _sym(label), _auto_arg(gauge), _create_list(mkup))


def with_dimensions(x1, y1, x2, y2, *args):
    return _c('with-dimensions', _pair(x1, x2), _pair(y1, y2), _create_list(args))


def fill_with_pattern(space, direction, pattern, left, right):
    return _c('fill-with-pattern',
        _a(space), _a(direction),
        _auto_arg(pattern), _auto_arg(left), _auto_arg(right))





def _main():
    """Auto-create markup factory functions."""
    factories = (
        (lambda n: lambda: _c(n)),
        (lambda n: lambda *text: _c(n, _create_list(text))),
        (lambda n: lambda arg, *text: _c(n, _auto_arg(arg), _create_list(text))),
        (lambda n: lambda arg1, arg2, *text: _c(n, *map(_auto_arg, (arg1, arg2)), _create_list(text))),
        (lambda n: lambda arg1, arg2, arg3, *text: _c(n, *map(_auto_arg, (arg1, arg2, arg3)), _create_list(text))),
        None,
    )

    for argcount, factory in enumerate(factories):
        for cmd in w.markup_commands_nargs[argcount]:
            name = cmd.replace('-', '_')
            if keyword.iskeyword(name):
                name += '_'
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



_main()
del _main
