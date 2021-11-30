# This file is part of python-ly, https://pypi.python.org/pypi/python-ly
#
# Copyright (c) 2021 - 2021 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Registry of the language definitions bundled with :mod:`quickly`.

When adding languages to :mod:`quickly.lang` please also add a registration
here.

"""

__all__ = ['find', 'register']


import itertools

import parce.registry


registry = parce.registry.Registry()


def find(name=None, *, filename=None, mimetype=None, contents=None):
    """Get the root lexicon for a language with name.

    See for all the arguments :func:`parce.find`. If no root lexicon can be
    found in quickly's bundled languages, falls back to :mod:`parce`.

    """
    if name:
        lexicon_name = registry.find(name)
    else:
        for lexicon_name in registry.suggest(filename, mimetype, contents):
            break
        else:
            lexicon_name = None
    if lexicon_name:
        return parce.registry.root_lexicon(lexicon_name)
    return parce.find(name, filename=filename, mimetype=mimetype, contents=contents)


def register(lexicon_name, parce_lexicon_name=None, *,
    name = None,
    desc = None,
    aliases = (),
    filenames = (),
    mimetypes = (),
    guesses = (),
):
    """Register a root lexicon name with specified properties.

    See for an explanation of all the arguments
    :meth:`parce.registry.Registry.register`.

    If a ``parce_lexicon_name`` is given, inherits properties from that
    language definition. The "list-properties" ``aliases``, ``filenames``,
    ``mimetypes`` and ``guesses`` are combined with the properties already
    present in *parce*.

    """
    if parce_lexicon_name:
        template = parce.registry.registry.get(parce_lexicon_name)
        if name is None:
            name = template.name
        if desc is None:
            desc = template.desc
        aliases = list(itertools.chain(template.aliases, aliases))
        filenames = list(itertools.chain(template.filenames, filenames))
        mimetypes = list(itertools.chain(template.mimetypes, mimetypes))
        guesses = list(itertools.chain(template.guesses, guesses))
    registry.register(
        lexicon_name, name = name, desc = desc, aliases = aliases,
        filenames = filenames, mimetypes = mimetypes, guesses = guesses)



## register bundled languages here
register("quickly.lang.html.Html.root", "parce.lang.html.Html.root",
    name = "HTML",
    desc = "HTML with embedded LilyPond",
)

register("quickly.lang.latex.Latex.root", "parce.lang.tex.Latex.root",
    name = "LaTeX",
    desc = "LaTeX with embedded LilyPond",
    filenames = [("*.lytex", 1)],
)

register("quickly.lang.lilypond.LilyPond.root", "parce.lang.lilypond.LilyPond.root")

register("quickly.lang.scheme.Scheme.root", "parce.lang.scheme.Scheme.root")

#TODO: texinfo and docbook
