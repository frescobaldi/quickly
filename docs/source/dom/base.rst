The dom.base module
===================

.. automodule:: quickly.dom.base


Base classes
------------

The following are base element classes for different languages.

.. autoclass:: Document
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: String
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: Comment
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: SinglelineComment
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: MultilineComment
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: BackslashCommand
    :members:
    :undoc-members:
    :show-inheritance:


Generic elements
----------------

These are generic elements, which are never created from transforming a
sourcce, but may be used to alter the output of a DOM tree/document.

.. autoclass:: Newline
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: BlankLine
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: Line
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: Column
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: Text
    :members:
    :undoc-members:
    :show-inheritance:


Special element
---------------

There is one "special" element.

.. autoclass:: Unknown
    :members:
    :undoc-members:
    :show-inheritance:


Language and Transform base/helper classes
------------------------------------------

.. autoclass:: XmlLike
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: Transform
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: AdHocTransform
    :members:
    :undoc-members:
    :show-inheritance:

