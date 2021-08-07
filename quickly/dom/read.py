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
Build DOM elements reading from text.

This module provides helper infrastructure to create DOM element nodes and
documents from text or *parce* trees, using parce's :mod:`~parce.transform`
module and the Transform classes in the :mod:`quickly.lang` modules.

The :class:`Reader` is the base of this infrastructure. In its default
instantiation, it uses the language definitions from the ``quickly`` module,
with their default Transforms. On instantiation, you can specify other language
definitions, for example to add specific features or parse specific versions of
the language. Also you can specify other than the default Transform classes.

By default, a parce :class:`~parce.transform.Transformer` is set; but you can
set another. The language definitions of the Reader are added to the
Transformer so they get used when transforming text or a *parce* tree.

Using the :meth:`Reader.adhoc` constructor, you can create a Reader that uses
Transforms that do *not* retain the origin tokens in the DOM element nodes.
This way, you can create DOM elements that are intended to be used in another
DOM document that has origin tokens. So the newly added content will not have
tokens that interfere with the tokens that are already in the document.

There is a global default Reader, which is returned by :func:`reader`; and a
global adhoc Reader is returned by :func:`adhoc_reader`.

Finally, all Reader methods are also conveniently available as global
functions, that operate with the global *adhoc* Reader.

"""


import parce.transform
from parce.util import cached_func


#import quickly.lang.docbook
#import quickly.lang.latex
import quickly.lang.lilypond
#import quickly.lang.html
import quickly.lang.scheme
#import quickly.lang.texinfo


class Reader:
    """A Reader contains the Language definitions to use and their associated
    Transforms.

    Those can be specified on instantiation, and have sensible defaults. The
    language definitions are accessible in the attributes of an instance of
    this class.

    For example, the :attr:`lilypond` attribute points to the LilyPond language
    definition. By default this is :class:`quickly.lang.lilypond.LilyPond`, but
    you can specify another. The :attr:`lilypond_transform` attribute points to
    the Transform to use for the lilypond language, if None the default
    transform is chosen.

    Using the :meth:`adhoc` constructor, a Reader is instantiated
    with so-called "ad hoc" Transforms. These Transform classes throw away
    the parce tokens when creating DOM element nodes, instead of storing them
    in the origin attributes of the elements.

    Using an "ad hoc" Reader you can construct element nodes that will be
    injected into DOM documents that have their own origin tokens, so the newly
    inserted nodes will not point to the text the rest of the document
    originated from.

    TODO: Add basic docbook, latex, html, texinfo transforms, to support
    LilyPond Book.

    """
    def __init__(self, *,
            lilypond = quickly.lang.lilypond.LilyPond,
            lilypond_transform = None,
            scheme = quickly.lang.scheme.Scheme,
            scheme_transform = None,
            # TODO add docbook, latex, html, texinfo, may be MUP?
            ):

        self.docbook = None                          #: the DocBook language definition (NYI)
        self.docbook_transform = None                #: the DocBook transform to use (None⇒default)
        self.html = None                             #: the HTML language definition (NYI)
        self.html_transform = None                   #: the HTML transform to use (None⇒default)
        self.latex = None                            #: the Latex language definition (NYI)
        self.latex_transform = None                  #: the Latex transform to use (None⇒default)
        self.lilypond = lilypond                     #: the LilyPond language definition
        self.lilypond_transform = lilypond_transform #: the LilyPond Transform to use (None⇒default)
        self.scheme = scheme                         #: the Scheme language definition
        self.scheme_transform = scheme_transform     #: the Scheme Transform to use (None⇒default)
        self.texinfo = None                          #: the Texinfo language definition (NYI)
        self.texinfo_transform = None                #: the Texinfo transform to use (None⇒default)

        self.set_transformer(parce.transform.Transformer())

    def set_transformer(self, transformer):
        """Set the Transformer to use.

        The languages and transforms that were specified on Reader
        instantiation are added to the transformer.

        On Reader instantiation a default :class:`~parce.transform.Transformer`
        is already set, so only if you want to use another Transformer you need
        this method.

        """
        self._transformer = transformer

        if self.lilypond_transform:
            transformer.add_transform(self.lilypond, self.lilypond_transform)
        if self.scheme_transform:
            transformer.add_transform(self.scheme, self.scheme_transform)

    def transformer(self):
        """Get the current Transformer."""
        return self._transformer

    @classmethod
    def adhoc(cls):
        """Return a :class:`Reader` with default languages and ad hoc
        transforms.

        These transforms do not keep the origin in the element nodes, so
        element nodes created with this Reader can be used in other documents
        that have origin tokens.

        """
        return cls(
            lilypond_transform = quickly.lang.lilypond.LilyPondAdHocTransform(),
            scheme_transform = quickly.lang.scheme.SchemeAdHocTransform(),
        )


    def tree(self, tree):
        """Transform a full *parce* tree."""
        return self.transformer().transform_tree(tree)

    def lily_document(self, text):
        """Return a full :class:`.lily.Document` from the text.

        You can use this to get a one-shot full document, but also to create
        fragments of a document that can be used in other documents.

        """
        return self.transformer().transform_text(self.lilypond.root, text)

    def lily(self, text):
        """Return one element from the text, read in LilyPond.root."""
        for node in self.lily_document(text):
            return node

    def scm_document(self, text):
        """Return a :class:`.scm.Document` from the text."""
        return self.transformer().transform_text(self.scheme.root, text)

    def scm(self, text):
        """Return one element from the text, read in Scheme.root."""
        for node in self.scm_document(text):
            return node


@cached_func
def adhoc_reader():
    """Return a global adhoc Reader."""
    return Reader.adhoc()


@cached_func
def reader():
    """Return a global Reader."""
    return Reader()


def lily_document(text):
    """Return a :class:`.lily.Document` from the text, using the global adhoc
    :class:`Reader`.

    Example::

        >>> from quickly.dom import read
        >>> node = read.lily_document("music = { c d e f g }")
        >>> node.write()
        'music = { c d e f g }'
        >>> node.dump()
        <lily.Document (1 child)>
         ╰╴<lily.Assignment music (3 children)>
            ├╴<lily.Identifier (1 child)>
            │  ╰╴<lily.Symbol 'music'>
            ├╴<lily.EqualSign>
            ╰╴<lily.MusicList (5 children)>
               ├╴<lily.Note 'c'>
               ├╴<lily.Note 'd'>
               ├╴<lily.Note 'e'>
               ├╴<lily.Note 'f'>
               ╰╴<lily.Note 'g'>

    This way you can get a DOM document from a full source text. This can also
    help you to create DOM element nodes that would otherwise be tedious to
    construct and type.

    """
    return adhoc_reader().lily_document(text)


def lily(text):
    """Return one element from the text, read in LilyPond.root, using the
    global adhoc :class:`Reader`.

    Examples::

        >>> from quickly.dom import read
        >>> read.lily("a")
        <lily.Note 'a'>

        >>> color = read.lily("#(x11-color 'DarkSlateBlue4)")
        >>> color.dump()
        <lily.Scheme '#' (1 child)>
         ╰╴<scm.List (2 children)>
            ├╴<scm.Identifier 'x11-color'>
            ╰╴<scm.Quote "'" (1 child)>
               ╰╴<scm.Identifier 'DarkSlateBlue4'>

        >>> read.lily("##f").dump()
        <lily.Scheme '#' (1 child)>
         ╰╴<scm.Bool False>

        >>> read.lily("1/2")
        <lily.Fraction 1/2>

        >>> read.lily("##xa/b").dump()
        <lily.Scheme '#' (1 child)>
         ╰╴<scm.Hex Fraction(10, 11)>

    This can help you to create DOM element nodes that would otherwise be
    tedious to construct and type.

    """
    return adhoc_reader().lily(text)


def scm_document(text):
    """Return a :class:`.scm.Document` from the text, using the global adhoc
    :class:`Reader`."""
    return adhoc_reader().scm_document(text)


def scm(text):
    """Return one element from the text, read in Scheme.root, using the global
    adhoc :class:`Reader`."""
    return adhoc_reader().scm(text)


