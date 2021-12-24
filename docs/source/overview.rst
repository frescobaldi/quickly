Overview
========

The *quickly* module provides ready-to-use functions to create, manipulate and
convert `LilyPond`_ music text documents, and the building blocks to create new
functionality.

Besides Python and its standard library, *quickly* only depends on `parce`_.
LilyPond documents are plain text documents; using *parce*, the text is
tokenized into a tree structure of parce tokens and contexts, and then
transformed into a "Document Object Model", a more semantical tree structure of
:mod:`~quickly.dom` nodes.

.. _parce: https://parce.info/
.. _LilyPond: http://lilypond.org/

When a document is modified (e.g. by the user, typing in a text editor), the
tokens and the DOM document are automatically updated.

The two cornerstones of *quickly* are the :class:`parce.Document` (or any class
following this interface), and the *quickly* DOM. Lexing the text in the
document is done by *parce*, using a root lexicon, which belongs to a language
definition. Transforming the lexed text into a DOM document is also done by
*parce*, using a :class:`~parce.transform.Transform` that's coupled to the
language definition.

Most music manipulation functions operate on the *quickly* DOM, which
afterwards can update the text document it originated from, if desired.

To create a parce Document, with LilyPond contents::

    >>> import parce
    >>> from quickly.registry import find
    >>> doc = parce.Document(find("lilypond"), transformer=True)
    >>> doc.set_text(r"music = { c d e f g }")

To target only specific regions in a text document, often a
:class:`parce.Cursor` is used.

To get the transformed DOM document:

    >>> music = doc.get_transform(True)
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.Assignment music (3 children)>
        ├╴<lily.Identifier (1 child)>
        │  ╰╴<lily.Symbol 'music' [0:5]>
        ├╴<lily.EqualSign [6:7]>
        ╰╴<lily.MusicList (5 children) [8:21]>
           ├╴<lily.Note 'c' [10:11]>
           ├╴<lily.Note 'd' [12:13]>
           ├╴<lily.Note 'e' [14:15]>
           ├╴<lily.Note 'f' [16:17]>
           ╰╴<lily.Note 'g' [18:19]>

See :doc:`quicklydom` for more information about the DOM used by *quickly*.

