# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2020 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
This module defines the :class:`Element` class.

An Element describes an object and can have child objects. An Element can
display a ``head`` and optionally a ``tail``. The head is text that is printed
before the children (if any). The tail is displayed after the children, and
will in most cases be used as a closing delimiter.

An Element can be constructed in two ways: either using the
:meth:`~Element.from_origin` class method from tokens (this is done by the
LilyPondTransform class), or manually using the normal constructor.

You can specify all child elements in the constructor, so theoretically you can
build a whole document in one expression.

To get the textual output of an element and all its child elements, use the
:meth:`~Element.write` method. Indented output is created by the
:meth:`~Element.write_indented` method.

Whitespace is handled in a smart way: Element subclasses can specify the
preferred whitespace before, after and between elements, and elements that have
head and tail texts can also specify the preperred whitespace after the head
and before the tail. When outputting the text, the whitespace between elements
is combined to fulfil all requirements but to prevent double spaces.

When an Element is constructed from tokens using the
:meth:`~Element.with_origin` constructor, it is able to write ifself back in
the document if modified, using the :meth:`~Element.edit` method.

:class:`Element` inherits from  :class:`~quickly.node.Node`, and thus from
:class:`list`, to build a reliable and easy to navigate tree structure.

"""

import collections
import reprlib

from parce.util import caching_dict

from ..node import Node
from .util import collapse_whitespace, combine_text


#: A Point describes a piece of text at a certain position.
#: See :meth:`Element.points`.
Point = collections.namedtuple("Point", "pos end text modified space_before space_after")
Point.pos.__doc__ = "The position in the original text. None for newly added nodes."
Point.end.__doc__ = "The end position in the original text. None for newly added nodes."
Point.text.__doc__ = ("A callable returning the text (the :attr:`~Element.write_head` or "
                      ":attr:`~Element.write_tail` method of the respective element).")
Point.modified.__doc__ = "True if the text has been modified."
Point.space_before.__doc__ = "The desired whitespace before this text fragment."
Point.space_after.__doc__ = "The desired whitespace after this text fragment."

HEAD_MODIFIED = 1
TAIL_MODIFIED = 2


class _SpaceProperty:
    """A property that denotes spacing.

    If it does not deviate from the default (set in the Element class
    definition prefixed with an underscore), it takes up no memory. Only when a
    value is different from the default value, a dict is created to hold the
    values.

    """
    __slots__ = ('name', 'default')

    def __init__(self, name, default):
        self.name = name
        self.default = default

    def __get__(self, obj, cls):
        try:
            return obj._space[self.name]
        except (AttributeError, KeyError):
            pass
        return self.default

    def __set__(self, obj, value):
        is_default = value == self.default
        try:
            d = obj._space
        except AttributeError:
            if is_default:
                return
            d = obj._space = {}
        else:
            if is_default:
                try:
                    del d[self.name]
                except KeyError:
                    pass
                else:
                    if not d:
                        del obj._space
                return
        d[self.name] = value

    def __delete__(self, obj):
        try:
            del obj._space[self.name]
        except (AttributeError, KeyError):
            return
        if not obj._space:
            del obj._space


class ElementType(type):
    """Metaclass for Element.

    This meta class automatically adds an empty ``__slots__`` attribute if it
    is not defined in the class body, and replaces space defaults with dynamic
    properties that are settable on a per-instance basis.

    """
    _props = caching_dict(_SpaceProperty, True)

    def __new__(cls, name, bases, namespace):
        for n in ('before', 'after_head', 'between', 'before_tail', 'after'):
            attr = 'space_' + n
            if attr in namespace:
                namespace[attr] = cls._props[n, namespace[attr]]
        if '__slots__' not in namespace:
            namespace['__slots__'] = ()
        return type.__new__(cls, name, bases, namespace)


class Element(Node, metaclass=ElementType):
    """Base class for all element types.

    The Element has no head or tail value.

    Child elements can be specified directly as arguments to the constructor.
    Using keyword arguments you can give other spacing preferences than the
    default values for ``space_before``, ``space_after``, ``space_between``,
    ``space_after_head`` and ``space_before_tail``.

    """
    __slots__ = ("_space",)

    _head = None
    _tail = None
    _modified = 0

    space_before = ""       #: whitespace before this element
    space_after_head = ""   #: whitespace before first child
    space_between = ""      #: whitespace between children
    space_before_tail = ""  #: whitespace before tail
    space_after = ""        #: whitespace after this element

    def __init__(self, *children, **attrs):
        super().__init__(*children)
        for attribute, value in attrs.items():
            setattr(self, attribute, value)

    def copy(self, with_children=True):
        """Copy the node, without the origin.

        If ``with_children`` is True (the default), child nodes are also
        copied.

        """
        children = (n.copy() for n in self) if with_children else ()
        return type(self)(*children, **getattr(self, '_spacing', {}))

    def copy_with_origin(self, with_children=True):
        """Copy the node, with origin if available.

        If ``with_children`` is True (the default), child nodes are also
        copied.

        """
        children = (n.copy_with_origin() for n in self) if with_children else ()
        copy = type(self)(*children, **getattr(self, '_spacing', {}))
        copy.copy_origin_from(self)
        return copy

    def copy_origin_from(self, other, modified=None):
        """Copy the origin from another element node to ourself.

        If ``modified`` is True, sets ourself as "modified", i.e. we will write
        back changes when requested via :meth:`edits`. If ``modified`` is
        False, our "modified" flag will be set to to unmodified state. If
        ``modified`` is None (the default); the modified flag will be copied
        from the other.

        .. note::

           The modified flag makes only sense for :class:`TextElement` types,
           that have a writable head value. Using this method on other node
           types can lead to changes going unnoticed.

        """
        modified_flag = 0
        try:
            self.head_origin = other.head_origin
            modified_flag = HEAD_MODIFIED
            self.tail_origin = other.tail_origin
            modified_flag |= TAIL_MODIFIED
        except AttributeError:
            pass
        try:
            if modified:
                self._modified = modified_flag
            elif modified is None:
                self._modified = other._modified
            else:
                self._modified = 0
        except AttributeError:
            pass

    def __repr__(self):
        def result():
            # class name with last part module prepended
            cls = self.__class__
            mod = cls.__module__.split('.')[-1]
            yield "{}.{}".format(mod, cls.__name__)
            # head and tail
            head = self.repr_head()
            if head is not None:
                yield head
            tail = self.repr_tail()
            if tail is not None:
                yield '...'
                yield tail
            # child count
            if len(self):
                yield "({} child{})".format(len(self), '' if len(self) == 1 else 'ren')
            # position
            pos = end = None
            p = self.head_point()
            if p:
                pos, end = p.pos, p.end
                if pos is not None:
                    p = self.tail_point()
                    if p and p.end is not None:
                        end = p.end
                    yield '[{}:{}]'.format(pos, end)
        return "<{}>".format(" ".join(result()))

    def py_dump(self, file=None, indent_width=4):
        r"""Print out the node to the console in Python syntax.

        This can be used to speed up developing code that creates DOM
        documents. If the head value of every :class:`TextElement` has a proper
        :func:`repr` value, the code can be directly executed in Python.

        For example::

            >>> from quickly.lang.latex import Latex
            >>> from parce.transform import transform_text
            >>> transform_text(Latex.root, r"\begin[opts]{lilypond}music = { c }\end{lilypond}").py_dump()
            tex.Document(
                tex.Environment(
                    tex.Command('begin',
                        tex.Option(
                            tex.Text('opts')),
                        tex.EnvironmentName('lilypond')),
                    lily.Document(
                        lily.Assignment(
                            lily.Identifier(
                                lily.Symbol('music')),
                            lily.EqualSign(),
                            lily.MusicList(
                                lily.Note('c')))),
                    tex.Command('end',
                        tex.EnvironmentName('lilypond'))))

        """
        def generate_text():
            stack = []
            gen = iter((self,))
            while True:
                for node in gen:
                    cls = node.__class__
                    mod = cls.__module__.split('.')[-1]
                    yield ' ' * len(stack) * indent_width
                    yield "{}.{}(".format(mod, cls.__name__)
                    if isinstance(node, TextElement):
                        yield repr(node.head)
                        if len(node):
                            yield ','
                    text = '),\n' if node.parent and not node.is_last() else ')'
                    if len(node):
                        yield '\n'
                        stack.append((gen, text))
                        gen = iter(node)
                        break
                    else:
                        yield text
                else:
                    if stack:
                        gen, text = stack.pop()
                        yield text
                    else:
                        break
        print(''.join(generate_text()), file=file)

    @property
    def pos(self):
        """Return the position of this element.

        Only makes sense for elements that have an origin, or one of the
        descendants has an origin. Possibly an expensive call, when a node tree
        has been heavily modified already. Returns None if this node and no
        single descendant of it has an origin.

        """
        try:
            return self.head_origin[0].pos
        except (AttributeError, IndexError):
            for n in self.descendants():
                try:
                    return n.head_origin[0].pos
                except (AttributeError, IndexError):
                    pass

    @property
    def end(self):
        """Return the end position of this element.

        Only makes sense for elements that have an origin, or one of the
        descendants has an origin. Possibly an expensive call, when a node tree
        has been heavily modified already. Returns None if this node and no
        single descendant of it has an origin.

        """
        try:
            return self.tail_origin[-1].end
        except (AttributeError, IndexError):
            for n in reversed(self):
                end = n.end
                if end is not None:
                    return end
            try:
                return self.head_origin[-1].end
            except (AttributeError, IndexError):
                pass

    def find_child(self, position):
        """Return the child node touching the position.

        If two child nodes touch the position, the one to the right is chosen.
        Only returns a node that has a ``pos`` attribute, i.e. at least one of
        its descendants has an origin.

        """
        # we do not bisect because we need to loop anyway to skip position-less
        # nodes
        prev = None
        for n in self:
            pos = n.pos
            if pos is not None:
                if pos == position:
                    return n
                elif pos > position:
                    return prev
                end = n.end
                if end > position:
                    return n
                prev = n if end == position else None
        return prev

    def find_descendant(self, position, end=None):
        """Return the youngest descendant node that contains position.

        If two descendant nodes touch the position, the one to the right is
        chosen. Only returns a node that has a ``pos`` attribute, i.e. at least
        one of its descendants has an origin. If ``end`` is specified, stops
        with the last node that contains the range ``position`` ... ``end``.
        Returns None if there is no such node that contains this position.

        """
        n = None
        for n in self.find_descendants(position, end):
            pass
        return n

    def find_descendants(self, position, end=None):
        """Yield the child at position, then the grandchild, etc.

        Stops with the last node that really contains the position. Only yields
        nodes that have a ``pos`` attribute, i.e. at least one of its
        descendants has an origin. If ``end`` is specified, stops with the last
        node that contains the range ``position`` ... ``end``.

        """
        if end is None or end < position:
            end = position
        n = self.find_child(position)
        while n and n.pos <= position and end <= n.end:
            yield n
            n = n.find_child(position)

    def find_descendant_right(self, position):
        """Return the first descendant that starts at or to the right of position.

        Only returns a node that has a ``pos`` attribute, i.e. at least one of
        its descendants has an origin. Returns None if no node with a ``pos``
        value is found at or to the right of the position.

        """
        # we do not bisect because we need to loop anyway to skip position-less
        # nodes
        stack = []
        gen = iter(self)
        while True:
            for n in gen:
                end = n.end
                if end is not None and end > position:
                    if n.pos >= position:
                        return n
                    # enter this node
                    stack.append(gen)
                    gen = iter(n)
                    break
            else:
                if stack:
                    gen = stack.pop()
                else:
                    break

    def find_descendant_left(self, position):
        """Return the last descendant that ends at or to the left of position.

        Only returns a node that has a ``pos`` attribute, i.e. at least one of
        its descendants has an origin. Returns None if no node with a ``pos``
        value is found at or to the left of the position.

        """
        # we do not bisect because we need to loop anyway to skip position-less
        # nodes
        stack = []
        gen = reversed(self)
        while True:
            for n in gen:
                pos = n.pos
                if pos is not None and pos < position:
                    if n.end <= position:
                        return n
                    # enter this node
                    stack.append(gen)
                    gen = reversed(n)
                    break
            else:
                if stack:
                    gen = stack.pop()
                else:
                    break

    @property
    def head(self):
        """The head contents."""
        return self._head

    @head.setter
    def head(self, head):
        if head != self._head:
            self._head = head
            self._modified |= HEAD_MODIFIED

    @property
    def tail(self):
        """The tail contents."""
        return self._tail

    @tail.setter
    def tail(self, tail):
        if tail != self._tail:
            self._tail = tail
            self._modified |= TAIL_MODIFIED

    @classmethod
    def read_head(cls, head_origin):
        """Return the value as computed from the specified origin Tokens.

        The default implementation concatenates the text from all tokens.

        """
        return ''.join(t.text for t in head_origin)

    @classmethod
    def read_tail(cls, tail_origin):
        """Return the value as computed from the specified origin Tokens.

        The default implementation concatenates the text from all tokens.

        """
        return ''.join(t.text for t in tail_origin)

    def write_head(self):
        """Return the textual output that represents our ``head`` value.

        The default implementation just returns the ``head`` attribute,
        assuming it is text.

        """
        return self.head

    def write_tail(self):
        """Return the textual output that represents our ``tail`` value.

        The default implementation just returns the ``tail`` attribute,
        assuming it is text.

        """
        return self.tail

    def repr_head(self):
        """Return a representation for the head.

        The default implementation returns None.

        """
        return None

    def repr_tail(self):
        """Return a representation for the tail.

        The default implementation returns None.

        """
        return None

    def head_point(self):
        """Return the :class:`Point` describing the head text.

        Returns None for elements that don't have a head text.

        """

    def tail_point(self):
        """Return the :class:`Point` describing the tail text.

        Returns None for elements that can't have a tail text.

        """

    def points(self):
        """Yield Points for this element and all its descendants.

        Each point is a :class:`Point` describing a text piece and the desired
        whitespace before and after it.

        """
        head_point = self.head_point()
        tail_point = self.tail_point()

        def collapse_last(points, last):
            """Yield all points, but with the last one, add last spacing wish"""
            for p in points:
                for q in points:
                    yield p
                    p = q
                # last point, add last space to space wishes
                space_after = collapse_whitespace((p.space_after, last))
                yield p._replace(space_after=space_after)

        if head_point:
            yield head_point
        children = iter(self)
        for n in children:
            # collapse the whitespace after each child (except the last) with
            # the return value of self.concat() (by default space_between)
            for m in children:
                yield from collapse_last(n.points(), self.concat(n, m))
                n = m
            # collapse own space_after with last child point?
            yield from collapse_last(n.points(), self.space_after) if not tail_point else n.points()
        if tail_point:
            yield tail_point

    def concat(self, node, next_node):
        """Return the minimum whitespace to apply between these child nodes.

        This method is called in the :meth:`points` method, when calculating
        whitespace between two adjacent child nodes. By default, the value of
        the ``space_between`` attribute is returned. Reimplement this method to
        differentiate whitespacing based on the (type or contents of the)
        nodes.

        """
        return self.space_between

    def write(self):
        """Return the combined output of this node and its children.

        To get indented output, use :meth:`write_indented` and/or the
        :mod:`~quickly.dom.indent` module.

        """
        return combine_text(
            (p.space_before, p.text(), p.space_after) for p in self.points())[1]

    def edits(self, context, start=None, end=None):
        """Yield three-tuples (pos, end, text) denoting text changes.

        The ``context`` is a parce Context. If ``start`` and/or ``end`` are not
        specified, the edits encompass the full context's range. All added or
        modified text fragments will still be written to the document, but no
        text outside the specified range will be deleted.

        """
        pos = context.pos if start is None else start
        end = context.end if end is None else end
        tokens = context.tokens()
        insert_after = ''
        for point in self.points():
            space = collapse_whitespace((insert_after, point.space_before))
            if point.pos is None:
                # new element
                text = point.text()
                if text:
                    yield pos, pos, space + text
                    insert_after = point.space_after
            else:
                # existing element
                if point.pos > pos:
                    # see if old content needs to be deleted between pos and point.pos
                    del_pos = del_end = pos
                    for t in tokens:
                        if t.pos >= point.pos:
                            pos = t.pos
                            break
                        del_end = t.end
                    if del_end > del_pos:
                        if space and del_end < pos:
                            del_end = pos   # unparsed space can be ditched
                        yield del_pos, del_end, space
                elif space:
                    yield point.pos, point.pos, space
                # modified?
                if point.modified:
                    yield point.pos, point.end, point.text()
                pos = point.end
                insert_after = point.space_after
        if pos < end:
            yield pos, end, ''

    def edit(self, document, context=None, start=None, end=None,):
        """Write back the modifications to the original parce document.

        Returns the number of changes that are made. If you don't specify the
        parce Context ``context``, the document's root context will be used.

        If ``start`` and/or ``end`` are not specified, the edits encompass the
        full context's range. All added or modified text fragments will still
        be written to the document, but no text outside the specified range
        will be deleted.

        After writing back the modifications to the original document, you
        should transform a new dom.Document, because some parts need to be
        rebuilt.

        """
        if context is None:
            context = document.builder().root
        n = 0
        with document:
            for pos, end, text in self.edits(context, start, end):
                document[pos:end] = text
                n += 1
        return n

    def signatures(self):
        """Return an iterable of signature tuples.

        A signature is a tuple. Every item in the tuple is an Element type, or
        a tuple of Element types; and is used with :func:`build_tree` to see
        whether an element can be a child of this element.

        By default an empty iterable is returned.

        """
        return ()

    def add_argument(self, node):
        """Called by :func:`build_tree` to add a child node as argument.

        ``node`` is the node to be appended. You can reimplement this method to
        perform some manipulation before appending it.

        """
        self.append(node)

    def child_order(self):
        """Return an iterable of tuples with element types.

        This is almost the same as :meth:`signatures` but used when a child
        node is inserted using :meth:`add`.

        By default an empty iterable is returned.

        """
        return ()

    def add(self, node):
        """Add a node, calling :meth:`child_order` to get the proper place to
        insert it.

        When the node type matches with one of the types in a child order
        tuple, it is inserted in that position between the other children. Not
        all node types need to be present, but at least the order is always
        respected.

        If the proper place can't be found, the node is appended at the end.

        """
        for order in self.child_order():
            for index, cls in enumerate(order):
                if isinstance(node, cls):
                    skip = order[:index]
                    for n in self ^ skip:
                        i = self.index(n)
                        self.insert(i, node)
                        return
        self.append(node)

    def indent_children(self):
        """Return True if the children should indent a level, if they appear on
        a new line.

        """
        return False

    def indent_align_indices(self):
        """Yield zero or more child indices that new lines could align with.

        This only makes sense for nodes that trigger a new indent level when
        pretty-printing their contents, in most cases this will be a
        :class:`BlockElement` node type.

        When, within a BlockElement node, a new line is started, it will by
        default be indented with, say, two spaces. But when there are already
        child nodes on the current line, the next line's indent could be
        aligned to one of them. This method yields the indices of the nodes, in
        priority, that may be used to align the indent with. The first one that
        matches will be used.

        """
        return
        yield

    def indent_override(self):
        """Return an indent position that could be used if this node is the first
        on a new line.

        By default None is returned, causing the normal indenting rules to
        apply.

        """
        return None

    def write_indented(self,
            indent_width = 2,
            start_indent = 0,
            max_align_indent = 16,
        ):
        """Return the output of this node and its children with indentation
        added.

        See for all the arguments the :class:`~quickly.dom.indent.Indenter`
        class from the :mod:`~quickly.dom.indent` module.

        """
        from . import indent
        return indent.Indenter(
            indent_width,
            start_indent,
            max_align_indent,
        ).write(self)


class HeadElement(Element):
    """Element that has a fixed head value."""
    __slots__ = ('head_origin',)

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        """Instantiate an Element from the origin tokens, but don't keep the tokens."""
        return cls(*children, **attrs)

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        """Instantiate an Element from the origin tokens, and keep the tokens.

        This way, this element knows its position in the text source, even if
        the parce tree changes, or this element changes.

        """
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node.head_origin = head_origin  #: tuple of parce Tokens the head value is read from
        return node

    def head_point(self):
        """Return the :class:`Point` describing the head text."""
        try:
            origin = self.head_origin
        except AttributeError:
            pos = end = None
        else:
            pos = origin[0].pos
            end = origin[-1].end
        modified = bool(self._modified & HEAD_MODIFIED)
        space_after = self.space_after_head if len(self) else self.space_after
        return Point(pos, end, self.write_head, modified, self.space_before, space_after)


class BlockElement(HeadElement):
    """Element that has a fixed head and tail value."""
    __slots__ = ('tail_origin',)

    @classmethod
    def with_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        node = cls.from_origin(head_origin, tail_origin, *children, **attrs)
        node.head_origin = head_origin
        node.tail_origin = tail_origin  #: tuple of parce Tokens the tail value is read from
        return node

    def indent_children(self):
        """Reimplemented to indent children of a BlockElement type by default."""
        return True

    def tail_point(self):
        """Return the :class:`Point` describing the tail text."""
        try:
            origin = self.tail_origin
        except AttributeError:
            pos = end = None
        else:
            try:
                pos = origin[0].pos
                end = origin[-1].end
            except IndexError:      # can happen when tail was missing
                pos = end = None
        modified = bool(self._modified & TAIL_MODIFIED)
        return Point(pos, end, self.write_tail, modified, self.space_before_tail, self.space_after)


class TextElement(HeadElement):
    """Element that has a variable/writable head value.

    This value must be given to the constructor, and can be modified later.

    If you want to, you can implement the :meth:`check_head` method, which by
    default returns True, to perform some checking on the ``head`` value of
    this element. This prevents forgetting to set the ``head`` value on manual
    construction, which can lead to unexpected and difficult to debug bugs.
    This method is not called when an element is copied, constructed from or
    with an origin, or when the ``head`` attribute is modified manually later.

    """
    __slots__ = ('_head', '_modified')

    def __new__(cls, head, *children, **attrs):
        if not cls.check_head(head):
            raise TypeError("invalid head value for {}: {}".format(cls.__name__, repr(head)))
        return super().__new__(cls)

    @classmethod
    def _factory(cls, head, *children, **attrs):
        """Factory bypassing the ``check_head`` check."""
        instance = super().__new__(cls)
        instance.__init__(head, *children, **attrs)
        return instance

    def __init__(self, head, *children, **attrs):
        self._head = head
        self._modified = 0
        super().__init__(*children, **attrs)

    def repr_head(self):
        """Return a repr value for our head value."""
        h = self.head
        if h is not None:
            return reprlib.repr(h)

    @classmethod
    def check_head(cls, head):
        """Returns whether the proposed head value is valid."""
        ### Raise error when forgetting the head value, and abusively using the first child
        return not isinstance(head, Element)

    def body_equals(self, other):
        """Compares the head values, called by :meth:`Node.equals() <quickly.node.Node.equals>`."""
        return self.head == other.head

    @classmethod
    def from_origin(cls, head_origin=(), tail_origin=(), *children, **attrs):
        head = cls.read_head(head_origin)
        return cls._factory(head, *children, **attrs)

    def copy(self, with_children=True):
        """Copy the node, without the origin.

        If ``with_children`` is True (the default), child nodes are also
        copied.

        """
        children = (n.copy() for n in self) if with_children else ()
        return self._factory(self.head, *children, **getattr(self, '_spacing', {}))

    def copy_with_origin(self, with_children=True):
        children = (n.copy_with_origin() for n in self) if with_children else ()
        copy = self._factory(self.head, *children, **getattr(self, '_spacing', {}))
        copy.copy_origin_from(self)
        return copy


class MappingElement(TextElement):
    r"""A TextElement with a fixed set of possible head values."""

    #: The ``mapping`` class attribute is a dictionay mapping unique head
    #: values to unique output values.  Other head values can't be used, they
    #: result in a TypeError.
    mapping = {}

    def __init_subclass__(cls, **kwargs):
        # auto-create the reversed mapping for writing output
        cls._inverted_mapping = {v: k for k, v in cls.mapping.items()}
        super().__init_subclass__(**kwargs)

    @classmethod
    def check_head(cls, head):
        return head in cls._inverted_mapping

    @classmethod
    def from_mapping(cls, text, *children, **attrs):
        """Convenience constructor to create this element from a text key
        that's available in the ``mapping``.

        """
        return cls(cls.mapping[text], *children, **attrs)

    @classmethod
    def read_head(cls, origin):
        """Get the head value from our mapping."""
        return cls.mapping[origin[0].text]

    def write_head(self):
        """Return the text value."""
        return self._inverted_mapping[self.head]


class ToggleElement(MappingElement):
    r"""A TextElement for a toggled item that has two possible values.

    E.g. ``\break`` or ``\noBreak``, or ``\sustainOn`` and ``\sustainOff``.

    The on-value is represented by head value True, the off value by False.

    """
    toggle_on = "<on>"
    toggle_off = "<off>"

    def __init_subclass__(cls, **kwargs):
        cls.mapping = {cls.toggle_on: True, cls.toggle_off: False}
        super().__init_subclass__(**kwargs)


def build_tree(nodes, ignore_type=None):
    """Build a tree of a stream of elements, based on their
    :meth:`Element.signatures`.

    ``nodes`` is an iterable of nodes. Consumes all nodes, and make some nodes
    a child of a preceding node. Yields the resulting nodes. When a node
    specifies what child element types it can have, and those element types
    follow indeed, they are added as child element.

    If ``ignore_type`` is given, it should be an Element type, or a tuple of
    Element types that are ignored, and added anyway as argument. This can be
    used to interperse Comment nodes.

    Existing children are taken into account.

    """
    stack = []

    if ignore_type:
        child_nodes = lambda n: n ^ ignore_type
    else:
        child_nodes = lambda n: n

    def add(node):
        """Add a node and yield finished nodes."""
        pending = [node]
        while stack and pending:
            # see if this node fits on top of the stack
            node = pending.pop()
            parent, signatures = stack[-1]
            if ignore_type and isinstance(node, ignore_type):
                parent.add_argument(node)
                continue
            signatures = [s[1:] for s in signatures if isinstance(node, s[0])]
            if signatures:
                # this fits
                parent.add_argument(node)
                signatures = [s for s in signatures if s]
                if signatures:
                    # wait for more arguments
                    stack[-1] = parent, signatures
                    continue
                # the parent is complete!
            else:
                # this does not fit, finish this parent and try again
                pending.append(node)
            pending.append(stack.pop()[0])
        yield from reversed(pending)

    for node in nodes:
        signatures = node.signatures()
        if signatures:
            for c in child_nodes(node):
                signatures = [s[1:] for s in signatures if isinstance(c, s[0])
                                       and len(s) > 1]
                if not signatures:
                    break
            else:
                stack.append((node, signatures))
                continue
        yield from add(node)

    # yield pending (unfinished) stuff
    while stack:
        yield from add(stack.pop()[0])


def head_mapping(*element_types):
    """Return a dictionary mapping (written out) head text to element type.

    Makes only sense for HeadElement or MappingElement descendants.

    """
    d = {}
    for cls in element_types:
        # we could delegate this to private methods of Element, but I didn't
        # want to pollute the classes with unimportant logic :-)
        if issubclass(cls, MappingElement):
            d.update(dict.fromkeys(cls.mapping, cls))
        elif issubclass(cls, HeadElement):
            d[cls.head] = cls
    return d


