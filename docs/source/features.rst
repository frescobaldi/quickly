Features of quickly
===================

Supported document types
------------------------

*quickly* supports LilyPond, Html, LaTeX and Scheme documents. DocBook and
TexInfo are in the works.

Html, LaTeX, DocBook and TexInfo are used to edit documents for
``lilypond-book``, a script provided by the `LilyPond`_ project that can extract
fragments of LilyPond music and run other document processors to produce output
of the texts with the musical fragments properly inserted. *quickly* is able to
recognize LilyPond music inside these document formats and allows the user to
manipulate the music.

.. _LilyPond: http://lilypond.org/

Music manipulations
-------------------

Most of *quickly*'s features manipulate music on the DOM document level,
writing back the modifications to the originating text, without interfering
with other parts of the source text.

There are four "levels" at which documents can be manipulated: a DOM node tree,
a :class:`~quickly.node.Range` of a DOM tree, a *parce* :class:`~parce.Document`, or a
selection of a parce document, specified by a *parce* :class:`~parce.Cursor`.

All manipulation functions can handle all four levels of operation, because
they inherit :class:`~quickly.dom.edit.Edit`. Typically only the
:meth:`~quickly.dom.edit.Edit.edit_range` method needs to be implemented for
the others to work equally well. Most modules have convenience functions that
can be called with all four types.


Transpose
^^^^^^^^^

.. currentmodule:: quickly.transpose

Transposing music is done using the :mod:`~quickly.transpose` module. A
Transposer is created that can actually transpose pitches according to the
user's wish, and optionally a PitchProcessor that reads and writes LilyPond
pitch names in all languages.

An example; create a document::

    >>> import parce
    >>> from quickly.registry import find
    >>> doc = parce.Document(find("lilypond"), r"music = { c d e f g }", transformer=True)

Create a transposer::

    >>> from quickly.pitch import Pitch
    >>> from quickly.transpose import transpose, Transposer
    >>> p1 = Pitch(0)     # -> c
    >>> p2 = Pitch(3)     # -> f
    >>> t = Transposer(p1, p2)

Now transpose the music from ``c`` to ``f`` and view the result::

    >>> transpose(doc, t)
    >>> doc.text()
    "music = { f g a bes c' }"

Using the cursor, we can also operate on a fragment of the document::

    >>> cur = parce.Cursor(doc, 12, 15)     # only the second and third note
    >>> transpose(cur, t)
    >>> doc.text()
    "music = { f c' d' bes c' }"

Only the second and third note are transposed. The function :func:`transpose`
is a convenience function that creates a :class:`Transpose` object and calls
its :meth:`~quickly.dom.edit.Edit.edit` method.


Convert pitches to and from relative notation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. currentmodule:: quickly.relative

The :mod:`~quickly.relative` module contains functions to convert music to and
from relative notation. These functions also use the PitchProcessor to read and
write pitch names in all languages, and automatically adapt to the pitch
language used in a document.

To convert all music from relative to absolute notation::

    >>> import parce
    >>> from quickly.registry import find
    >>> doc = parce.Document(find("lilypond"), r"music = \relative c' { c d e f g }", transformer=True)
    >>> from quickly.relative import rel2abs
    >>> rel2abs(doc)
    >>> doc.text()
    "music = { c' d' e' f' g' }"

And convert back to relative::

    >>> from quickly.relative import abs2rel
    >>> abs2rel(doc)
    >>> doc.text()
    "music = \\relative c' { c d e f g }"

The function :func:`abs2rel` and :func:`rel2abs` are convenience functions that
create respectively a :class:`Abs2rel` or :class:`Rel2abs` object and call
their :meth:`~quickly.dom.edit.Edit.edit` method.

