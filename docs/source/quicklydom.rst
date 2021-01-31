The quickly DOM
===============

.. py:currentmodule:: quickly.dom

A central part of the *quickly* package is the DOM (Document Object Model) it
provides. Targeted mainly at LilyPond, it can build a tree structure of almost
any structured textual language.

The object model is simple and builds on a tree structure of
:class:`~element.Element` nodes (which in turns base on :class:`~quickly.node.Node`
and :class:`list`).

Every syntactical element is represented by an Element node. There are four base
Element types:

* :class:`~element.Element`: which has no text itself but can have child elements

* :class:`~element.HeadElement`: which has a fixed "head" value which is
  displayed before the children's contents

* :class:`~element.BlockElement`: which has a fixed "head" and "tail" value,
  which are displayed before and after the children, respectively.

* :class:`~element.TextElement`: which has a writable "head" value, so its
  contents can be modified.


