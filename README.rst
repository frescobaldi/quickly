Welcome to quickly!
===================

`Homepage       <https://quick-ly.info/>`_                      •
`Development    <https://github.com/frescobaldi/quickly>`_      •
`Download       <https://pypi.org/project/quickly/>`_           •
`Documentation  <https://quick-ly.info/>`_                      •
`License        <https://www.gnu.org/licenses/gpl-3.0>`_

The quickly python package is slated to become the successor of python-ly.

It is currently in a very early development stage.

Like python-ly, it will provide tools to manipulate `LilyPond`_ music
documents, but instead of using the lexer in python-ly, which is very difficult
to maintain, it will use the new `parce`_ package for parsing LilyPond files.

.. _LilyPond: http://lilypond.org/
.. _parce: https://parce.info/

``ly.dom`` and ``ly.music`` will be superseded by ``quickly.dom`` which
provides a way to both build a LilyPond source file from scratch (like
``ly.dom``) and manipulate an existing document (like ``ly.music``). It is also
expected that much of the functionality that is currently implemented at the
token level, like transposing and rhythm manipulations, can be rewritten to
work on the musical representation provided by ``quickly.dom``, which will look
a lot like ``ly.music``.

This module is written and maintained by Wilbert Berendsen, and will, as it
grows, also contain (adapted) code from python-ly that was contributed by
others. Python 3.6 and higher is supported. Besides Python itself the most
recent version of the *parce* module is needed. Testing is done by running
``pytest-3`` in the root directory.

