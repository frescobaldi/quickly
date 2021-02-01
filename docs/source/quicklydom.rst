The quickly DOM
===============

.. py:currentmodule:: quickly.dom

A central part of the *quickly* package is the DOM (Document Object Model) it
provides. Targeted mainly at LilyPond and Scheme, it can build a tree structure
of almost any structured textual language. The object model is simple and
builds on a tree structure of :class:`~element.Element` nodes (which in turns
base on :class:`~quickly.node.Node` and :class:`list`).

Every syntactical element is represented by an Element node. There are four base
Element types:

* :class:`~element.Element`: which has no text itself but can have child elements

* :class:`~element.HeadElement`: which has a fixed "head" value which is
  displayed before the children's contents

* :class:`~element.BlockElement`: which has a fixed "head" and "tail" value,
  which are displayed before and after the children, respectively.

* :class:`~element.TextElement`: which has a writable "head" value, so its
  contents can be modified.

All other element types inherit of one of these four, and may bring other
features.


Building a Document manually
----------------------------

Using the element types in the :mod:`lily` and :mod:`scm` modules, a full
LilyPond source document can be built (theoratically) in one expression.
For example::

    >>> import fractions
    >>> from quickly.dom import lily
    >>> music = lily.Document(lily.SequentialMusic(
    ... lily.Note('c', lily.Duration(fractions.Fraction(1, 4))),
    ... lily.Note('d', lily.Articulations(lily.Direction(1, lily.Articulation
    ... (".")))),
    ... lily.Rest('r', lily.Articulations(lily.Dynamic("pp")))))
    >>> music
    <lily.Document (1 child)>
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.SequentialMusic (3 children)>
        ├╴<lily.Note 'c' (1 child)>
        │  ╰╴<lily.Duration Fraction(1, 4)>
        ├╴<lily.Note 'd' (1 child)>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Direction 1 (1 child)>
        │        ╰╴<lily.Articulation '.'>
        ╰╴<lily.Rest 'r' (1 child)>
           ╰╴<lily.Articulations (1 child)>
              ╰╴<lily.Dynamic 'pp'>
    >>> music.write()
    '{ c4 d^. r\\pp }'

Each element node type knows how to display its "head" value. For example, the
Note element knows the pitch name simply as a letter, but the Direction as a
number (-1, 0 or 1) and Duration as a fraction. Instead of one long expression,
nodes may be combined using usual Python methods::

    >>> music = lily.Document(lily.SequentialMusic())
    >>> music[0].append(lily.Note('c', lily.Duration(fractions.Fraction(1, 8))))
    >>> music[0].append(lily.Note('d'))
    >>> stacc = lily.Direction(1, lily.Articulation('.'))
    >>> music[0][-1].append(stacc)
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.SequentialMusic (2 children)>
        ├╴<lily.Note 'c' (1 child)>
        │  ╰╴<lily.Duration Fraction(1, 8)>
        ╰╴<lily.Note 'd' (1 child)>
           ╰╴<lily.Direction 1 (1 child)>
              ╰╴<lily.Articulation '.'>


