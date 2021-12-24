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
    >>> from quickly.transpose import transpose_doc, Transposer
    >>> p1 = Pitch(0)     # -> c
    >>> p2 = Pitch(3)     # -> f
    >>> t = Transposer(p1, p2)

Now transpose the music from ``c`` to ``f`` and view the result::

    >>> transpose_doc(parce.Cursor(doc), t)
    >>> doc.text()
    "music = { f g a bes c' }"

Using the cursor, we can also operate on a fragment of the document::

    >>> cur = parce.Cursor(doc, 12, 15)     # only the second and third note
    >>> transpose_doc(cur, t)
    >>> doc.text()
    "music = { f c' d' bes c' }"

Only the second and third note are transposed. The function :func:`transpose`
operates directly on a DOM node, while :func:`transpose_doc` operates on a
:class:`parce.Document`.


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
    >>> cursor = parce.Cursor(doc)
    >>> from quickly.relative import rel2abs_doc
    >>> rel2abs_doc(cursor)
    >>> doc.text()
    "music = { c' d' e' f' g' }"

And convert back to relative::

    >>> from quickly.relative import abs2rel_doc
    >>> abs2rel_doc(cursor)
    >>> doc.text()
    "music = \\relative c' { c d e f g }"

The function :func:`abs2rel` and :func:`rel2abs` operate directly on a DOM
node, while :func:`abs2rel_doc` and :func:`rel2abs_doc` operate on a *parce*
Document.
