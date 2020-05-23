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


r"""
The quickly.music module.

This module will provide a music object model that can be used for two things:

* building a LilyPond document (or expressions) from scratch
* representing a parsed LilyPond source document

*First* use case: Construct a music document or expression, optionally
manipulate it and then output it as a LilyPond source document (e.g. for
composition algorithms, a Score Wizard or import from other formats). It should
be simple, extensible and flexible.

The *second* use case is the most challenging: A LilyPond source document is
lexed by parce.lang.lilypond, and then transformed into a music Document
expression.

This expression is then used to manipulate and query the source document.
It should be possible to write modifications back to the source document, not
by bluntly replacing the full source document, but by accurately replacing
the modified parts.

This means that every item should know the tokens it originates from, to be
able to see if anything changes. At least each item should know its start
and end position in the text. Implicit items (such as a left-out duration)
still should know their spot.

When performing larger changes (i.e. large-scale reordering) we can't modify
individual items but should fall back to just rewriting.

For example: when transposing music we can write back every note name on its
old place.

So we should find a way to tell a container when it's internal ordering really
changes.

When music items are deleted how do we mark them for deletion?

When music items are inserted, how do we know where actually to insert them?

Imagine a Music document tree, read from a source text. Now we perform a large
amount of modifications on it, and then want to write it back.

may 20th
==============

- as few as possible different tree items
- as much as possible shared behaviour
- origin attribute containing original token

it should be possible to
- mark an item to be deleted
- mark an item to be modified
- indicate whether whitespace around items is desired
- insert a container inbetween an item and its parent without loosing the origin of the kids

after modifying a tree it should be possible to:
- output a full new document
- output the modifications relating to the origin that were done

An item with origin:
- can be modified. It determines itself whether its output would change.


IDEA.
-----

Two base music tree node types:
- container
- leaf

A container only contains leafs and prints nothing itself.
A leaf corresponds to a single token

Leaf
----

- has original Token in origin attribute
- when asked to modify, puts new output in output attribute

When asked for modifications: yields nothing if output is same as origin


Container
---------

- has children which may be leaf or container

If a child is cut out of a tree, or injected somewhere else, all origins are reset.

Only when a container is created encompassing a list of other nodes, the origins
are not reset.

For example:

{ c d e f g } becomes { c d { e f } g }; in this case we can still reuse the
existing e and f.

Inserting nodes
---------------

Newly created nodes never have an origin attribute.

A container decides together with the child nodes what kind of whitespace
is recommended between the items.

Every node, container or leaf can tell its preference.


Outputting
----------

When requesting output, an object is given as argument which can contain
certain preferences or additional information. ("Printer" in python-ly.)

A container can't simply concatenate the output of its children.

Because there could be newlyinserted items, while other are still in place.

The outputter could collect output until an item with an origin is encountered.

The output is then injected between the items that have an origin.


Only the leafs generate output.

The output is thus a list of leafs. Adjacent leafs with origin
ignore the text between them
For leafs without origin they decide together with the container about
the whitespace between them.

Comments
---------

We should also remember comments. They are desirable in new output, for example
by a score wizard.


Manipulating
------------

It should be possible to manipulate and query the tree structure.


GOAL
====

* Easily write LilyPond text from scratch. (Also: music21 and abjad can do this!)
  Like ly.dom in Python-ly.

* Parse LilyPond and/or even Scheme, query/convert (like ly.music in Python-ly)

* manipulate rhythm, pitch, pitch language etc all interacting with quickly.Music

Data Format
===========

container → List, and attributes.
leaf→ object with attributes.

one of the attributes of a container and leaf is the TYPE.
i.e. Comment, Newline, Note, Musiclist, Chord, Markup ...

DO WE USE:
-- class (like ly.dom and ly.music)   ??
-- an Action-like attribute like the standardactions in parce ??
-- an XML tag name?

use XML????
===========

We could use lxml.etree to store the Music structure so that it is basically
an XML document.

The tagname is the type of the object. The attributes are the attributes.
Child elements are the list of children.

There is a little "problem": A container such as a chord has a prefix and
suffix: the "<" and the ">". They are a item in themselves.

Do we include them in the list of child objects?

I.e.:

\relative {
  c d e f g
}

Then maps to:

<relative>
  <musiclist type="sequential">
    <prefix>{</prefix>
    <note><pitch>c</pitch></note>
    <note><pitch>d</pitch></note>
    <note><pitch>e</pitch></note>
    <note><pitch>f</pitch></note>
    <note><pitch>g</pitch></note>
    <suffix>}</suffix>
  </musiclist>
</relative>

It makes sense, because we can't avoid other items in containers, like comments

Xml and origin????
------------------

We want to store the original Token, because its ``pos`` attribute is kept
up-to-date by the tree builder. lxml.etree can't store a non-string attribute.


Custom Python tree node object
==============================

Store prefix and suffix leafs in attributes of a container?

A prefix Leaf would be a '{' and a suffix Leaf a '}'


When building a music list in a Transform
-----------------------------------------

A transform method does not get the opening '{' for many data types.

The encompassing context needs to add it! Could there be a danger that this is
done more than once, when a transform is partly updated? The encompassing
context might be transformed again. But if we only set an attribute (NOT APPEND
some child!) it would not be a problem.

So we could go for a:

Leaf type (1 or more adjacent tokens)

Container type (multiple children)

Container can have children and a prefix and suffix leaf.



Note:
c?'=,4.*1/2

Note:
 Pitch
 Accidental
 Octave
 OctaveCheck
 Duration
  Dots
  Scaling

21 mei
========

origin will have a tuple of all responsible tokens


Note
Rest


further musings on container/leaf

    Node
   /    \
Leaf    Container

Leaf:
* represents something that prints output
* can be asked to print output
* can have origin attribute with a tuple of all responsible tokens

{ c d e f g }

Musiclist
  prefix        -> Node (Leaf {)
  elements      -> Nodes
  suffix        -> Node (Leaf })


Deletion of nodes
-----------------

Manipulating the music tree can also delete nodes.
No problem when creating a new document.
But how to know what to do when writing back to an existing document.

Node deletion simply deletes a node, loosing the origin tokens.

When writing back, we could check all room inbetween all origins that are there.
* if that room is only whitespace, don't change it.
* If it is not whitespace, stuff has been deleted.

This presumes all tokens are kept music elements.

We could then as well check the tokens. If the origin tokens skip tokens in the
tokenized tree, it means stuff has been deleted.


BECAUSE transformation is not applied when token ancestry not changes, we dont
know the current PITCH LANGUAGE. It could be changed without the transformation
being run again.

So the Music tree cannot know the pitches, it should iterated over them knowing
the language, and the previous pitch etc.

OTOH: the root is always composed again, we could let the current language
"bubble up" automatically????

The goal of the music tree is make this process as fast and simple as possible.



Pitch language
--------------


\language "nederlands"

music = { c d e f g }

when transforming the notes we don;t know the lang. We set "unset".

when transforming the root we see the language. We set an attribute to all
following nodes?

Then this:

music = {
  c d e f g
  \language "français"
  ré mi fa sol

}

musicA = {
  do re mi
}

When reading music, we dont know the lang. we set unset. Then we see \language
francais, we set attr to following nodes (notes). We could return the language
with the item as the item's "last lang".

BUT is is cleaner to not do that. Nodes should not carry information that's
defined outside them.

SO for knowing the pitch language we should search backwards for the language
command.

22 mei
======


Converting LilyPond.root tree to Music or DOM.
==============================================

To understand the music, we need to know the current pitch language
and the last duration. (See ly.music.read.Reader.__init__().)

A \language command changes the current language in the parsing stage already.

Possible methods to find those when we don't know them during transforming
a music expression::

- when composing the Document, fill in all missing information


PITCH LANGUAGE
==============

What if we simply do not store the pitch language but try to find it when
reading music.

We should look backwards in document order to find it.
Look in left siblings, then the parent etc.

How to speed up this?

We could store in the music expression whether it has a language command.
When it hasn't, we can immediately try the parent, without searching backwards.

PREVIOUS DURATION
=================

same problem.


....



We could also iterate once over the full DOM tree, to fill in previous durations
and interprete pitch names.

OR we do nothing, and defer this to the moment we iterate over the music.

22 mei
DECIDE:
- we only read the pitches when iterating over the music
- same for the durations

So the transformed tree structure is side-effect free :-)

Let's go on decide on the tree infrastructure.

DOM TREE STRUCTURE
==================

* As generic and simple as possible
* Fast iteration over children
* Class of Nodes determines functionality

* quickly address a subnode by its type

questions:
- separate Leaf/Node ??
-

say a = Music()

iterate over a children of type List:

for node in a/List:
    ...

pick the first:

a.pick(List)
a.find(List)


what to do with:
{ c d e f g }

Simultaneous
  OpenBrace "{"
  List
    Note
      PitchName "c"
    Note
      PitchName "d"
    Note
      PitchName "e"
    ...
  CloseBrace "}"



\override Staff.KeySignature.dotted.path = #'(scheme . expression)

Override
  Command "\override"
  List
    Context "Staff"
    Dot '.'
    Grob "KeySignature"
    Dot '.'
    Symbol 'dotted'
    Dot '.'
    Symbol 'path'
  Assignment
    EqualSign '='
    SchemeExpression
      SchemeQuote
        SchemePair
          OpenParen '('
          List
            Symbol 'scheme'
            Dot '.'
            Symbol 'expression'
          CloseParen ')'

We could simply keep the Tokens.....
But that can't be done when building from scratch.

There are lots of simple items that just can represent a token.

23 mei
======

DECISIONS
=========


- Items can have output AND children

- The own output is prepended
  Eg: Clef('treble') yields:
  Clef → has output/origin '\clef'
    Symbol 'treble'
  Key(Pitch('c'), 'major') yields
    Key → '\key'
      Pitch 'c'
      Mode '\major'

- for { ... } we use small leaf nodes:
  Enclosed
    Prefix
    List
    Suffix
  (Enclosed may choose to delete the Prefix/Suffix nodes if List has length 1)

- Child nodes can be added on init:
  Simultanous(Sequential(Note(), Note(), Note(),...), Sequential(Note(), Chord(),...))
  so a document can be constructed in one expression

- ``from_token`` class method constructs items from Tokens, used in Transform
  OR ``origin=`` keyword args?

- Add a simple way to construct items from LilyPond syntax!

  e.g. items(LilyPond.root, "{ c d e f g }")
  basically calls transform_text  :-)

- Friendly constructors, allowing things like:

  Key('c', 'major') which is then converted to
  Key(Pitch('c'), Mode('\major'))

- Pay attention to variable names, in ly.dom we have Reference objects for
  named variables that can be changed in one place in the case of name clashes.
  That should be possible too using quickly.Music

- USE THE NAME ``quickly.dom`` for the module? It is more than music, also
  markup and scheme...



"""



class Node:
    def append(self, child):
        child.parent = self
        self._children.append(child)


class Item(Node):
    __slots__ = ('origin', 'output')
    def __init__(self, origin=None):
        if origin:
            self.origin = origin


class _TokenItem(Item):
    """Base class for simple items that originate from one token or text piece."""
    def __init__(self, text, **kw):
        super().__init__(**kw)
        if isinstance(text, Token):
            self.origin = text
        else:
            self.output = text

    def text(self):
        """Get the output text."""
        try:
            return self.output
        except AttributeError:
            return self.origin.text


class Key(Item):
    r"""A \key pitch \mode statement. Pitch and mode may be Tokens.

    when creating from a token::

    # key, pitch, mode are tokens
    Key(pitch, mode, origin=key)


    """
    def __init__(self, pitch, mode, **kw):
        super().__init__(**kw)
        if not isinstance(pitch, Pitch):
            pitch = Pitch(pitch)
        if not isinstance(mode, Mode):
            mode = Mode(mode)
        self.append(pitch)
        self.append(mode)


class Pitch(_TokenItem):
    """A pitch name (token or plain text)."""


class Mode(_TokenItem):
    r"""The mode in a \key statement, e.g. "\major", token or plain text."""
