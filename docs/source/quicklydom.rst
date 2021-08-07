The quickly DOM
===============

.. py:currentmodule:: quickly.dom

A central part of the *quickly* package is the DOM (Document Object Model) it
provides. Targeted mainly at LilyPond and Scheme, it can build a tree structure
of almost any structured textual language. The object model is simple and
builds on a tree structure of :class:`~element.Element` nodes (which in turn
bases on :class:`~quickly.node.Node` and :class:`list`).

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

With the :mod:`quickly.dom` module you can:

* Build a DOM document manually and use it to write out a well-formatted
  LilyPond (template) score

* Create a DOM document from a LilyPond score, to further analyze or convert
  the music

* Create a DOM document from a score, manipulate it and then write the
  changes back to the original text.


Building a Document manually
----------------------------

Using the element types in the :mod:`~quickly.dom.lily` and
:mod:`~quickly.dom.scm` modules, a full LilyPond source document can be built
(theoretically) in one expression.

Child elements are specified as arguments to the constructor of an element. For
elements that inherit of :class:`~element.TextElement` is the first argument
the ``head`` value. Attributes (such as for spacing, but also other attributes
an element might support) can be specified as keyword arguments to the
constructor.

For example::

    >>> import fractions
    >>> from quickly.dom import lily
    >>> music = lily.Document(lily.MusicList(
    ... lily.Note('c', lily.Duration(fractions.Fraction(1, 4))),
    ... lily.Note('d', lily.Articulations(lily.Direction(1, lily.Articulation(".")))),
    ... lily.Rest('r', lily.Articulations(lily.Dynamic("pp")))))
    >>> music
    <lily.Document (1 child)>
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.MusicList (3 children)>
        ├╴<lily.Note 'c' (1 child)>
        │  ╰╴<lily.Duration Fraction(1, 4)>
        ├╴<lily.Note 'd' (1 child)>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Direction 1 (1 child)>
        │        ╰╴<lily.Articulation '.'>
        ╰╴<lily.Rest 'r' (1 child)>
           ╰╴<lily.Articulations (1 child)>
              ╰╴<lily.Dynamic 'pp'>

Call :meth:`~element.Element.write` to get the music in LilyPond format::

    >>> music.write()
    '{ c4 d^. r\\pp }'

Each element node type knows how to display its "head" value. For example, the
Note element knows the pitch name simply as a letter, but the Direction as a
number (-1, 0 or 1) and Duration as a fraction. For example::

    >>> duration = music[0][0][0]
    >>> duration.head
    Fraction(1, 4)
    >>> duration.write_head()
    '4'

So the ``head`` attribute is the interpreted value, while
:meth:`~element.Element.write_head` returns the output in LilyPond syntax.
For elements that inherit of :class:`~element.TextElement`, the head attribute
can be changed::

    >>> duration.head = fractions.Fraction(3, 8)
    >>> duration.write_head()
    '4.'
    >>> music.write()
    '{ c4. d^. r\\pp }'

Note the updated duration in the ``music`` output.

Instead of one long expression, nodes may be combined using usual Python
methods::

    >>> music = lily.Document(lily.MusicList())
    >>> music[0].append(lily.Note('c', lily.Duration(fractions.Fraction(1, 8))))
    >>> music[0].append(lily.Note('d'))
    >>> stacc = lily.Direction(1, lily.Articulation('.'))
    >>> music[0][-1].append(stacc)
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.MusicList (2 children)>
        ├╴<lily.Note 'c' (1 child)>
        │  ╰╴<lily.Duration Fraction(1, 8)>
        ╰╴<lily.Note 'd' (1 child)>
           ╰╴<lily.Direction 1 (1 child)>
              ╰╴<lily.Articulation '.'>

Element nodes are "side-effects free"; i.e. a node knows nothing that's not
defined in itself. That's why we simply show the pitch name letter(s): we don't
know the actual pitch, because the node doesn't know the current pitch
language. But traversing the nodes is simple, to find a point a pitch language
or duration is defined.


Creating a Document from LilyPond source
----------------------------------------

Creating a Document from LilyPond source is a two-stage process. The first
stage is tokenizing the text to a *parce* tree structure. The second stage is
transforming the tree to a ``quickly.dom`` Document (or any node type).

Here is an example, with intermediate results shown. First we create a *parce*
tree::

    >>> import parce.transform
    >>> from quickly.lang.lilypond import LilyPond
    >>> tree = parce.root(LilyPond.root, "{ <c' g'>4( a'2) f:16-. }")
    >>> tree.dump()     # show the parce tree
    <Context LilyPond.root at 0-25 (1 child)>
     ╰╴<Context LilyPond.musiclist* at 0-25 (14 children)>
        ├╴<Token '{' at 0:1 (Delimiter.Bracket.Start)>
        ├╴<Context LilyPond.chord at 2-9 (6 children)>
        │  ├╴<Token '<' at 2:3 (Delimiter.Chord.Start)>
        │  ├╴<Token 'c' at 3:4 (Text.Music.Pitch)>
        │  ├╴<Context LilyPond.pitch at 4-5 (1 child)>
        │  │  ╰╴<Token "'" at 4:5 (Text.Music.Pitch.Octave)>
        │  ├╴<Token 'g' at 6:7 (Text.Music.Pitch)>
        │  ├╴<Context LilyPond.pitch at 7-8 (1 child)>
        │  │  ╰╴<Token "'" at 7:8 (Text.Music.Pitch.Octave)>
        │  ╰╴<Token '>' at 8:9 (Delimiter.Chord.End)>
        ├╴<Token '4' at 9:10 (Literal.Number.Duration)>
        ├╴<Token '(' at 10:11 (Name.Symbol.Spanner.Slur)>
        ├╴<Token 'a' at 12:13 (Text.Music.Pitch)>
        ├╴<Context LilyPond.pitch at 13-14 (1 child)>
        │  ╰╴<Token "'" at 13:14 (Text.Music.Pitch.Octave)>
        ├╴<Token '2' at 14:15 (Literal.Number.Duration)>
        ├╴<Token ')' at 15:16 (Name.Symbol.Spanner.Slur)>
        ├╴<Token 'f' at 17:18 (Text.Music.Pitch)>
        ├╴<Token ':' at 18:19 (Delimiter.Tremolo)>
        ├╴<Token '16' at 19:21 (Literal.Number.Duration.Tremolo)>
        ├╴<Token '-' at 21:22 (Delimiter.Direction)>
        ├╴<Context LilyPond.script at 22-23 (1 child)>
        │  ╰╴<Token '.' at 22:23 (Literal.Character.Script)>
        ╰╴<Token '}' at 24:25 (Delimiter.Bracket.End)>

Then we transform the tree to a DOM document. The transformer automagically
finds :class:`~quickly.lang.lilypond.LilyPondTransform` in the
:mod:`quickly.lang.lilypond` module::

    >>> t = parce.transform.Transformer()
    >>> music = t.transform_tree(tree)
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.MusicList (3 children) [0:25]>
        ├╴<lily.Music (3 children)>
        │  ├╴<lily.Chord (2 children) [2:9]>
        │  │  ├╴<lily.Note 'c' (1 child) [3:4]>
        │  │  │  ╰╴<lily.Octave 1 [4:5]>
        │  │  ╰╴<lily.Note 'g' (1 child) [6:7]>
        │  │     ╰╴<lily.Octave 1 [7:8]>
        │  ├╴<lily.Duration Fraction(1, 4) [9:10]>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Slur 'start' [10:11]>
        ├╴<lily.Note 'a' (3 children) [12:13]>
        │  ├╴<lily.Octave 1 [13:14]>
        │  ├╴<lily.Duration Fraction(1, 2) [14:15]>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Slur 'stop' [15:16]>
        ╰╴<lily.Note 'f' (1 child) [17:18]>
           ╰╴<lily.Articulations (2 children)>
              ├╴<lily.Tremolo (1 child) [18:19]>
              │  ╰╴<lily.Duration Fraction(1, 16) [19:21]>
              ╰╴<lily.Direction 0 (1 child) [21:22]>
                 ╰╴<lily.Articulation '.' [22:23]>

Note that the elements now show their position in the original text. More about
that later. Just to check if the music was interpreted correctly::

    >>> music.write()
    "{ <c' g'>4( a'2) f:16-. }"


Intermezzo: Whitespace handling
-------------------------------

Some elements have whitespace between them, others don't. For example, the
:class:`lily.SequentialMusic` and the :class:`lily.Chord` element put
whitespace between their children, but :class:`lily.Note` doesn't.
SequentialMusic also puts whitespace after the first brace (the "head") and
before the closing brace ("tail"), but Chord doesn't.

This is handled by five properties that have sensible defaults for every
element type, but can be modified for every individual element. These
properties are:
:attr:`~element.Element.space_before`,
:attr:`~element.Element.space_after_head`,
:attr:`~element.Element.space_between`,
:attr:`~element.Element.space_before_tail` and
:attr:`~element.Element.space_after`.

If the whitespace properties have their default value, they don't take any
memory. Then there is a :meth:`~element.Element.concat` method which is called
to return the whitespace to use between two child elements. Most element types
just return the :attr:`~element.Element.space_between` there.

After consulting all the whitespace wishes, the most important whitespace is
chosen by the :meth:`~element.Element.write` method. E.g. ``"\n"`` prevails
over ``" "`` and ``"\n\n"`` prevails over ``"\n"``.

Indenting output has yet to be implemented.


Modifying a DOM document
------------------------

A DOM document can be modified by:

* adding or removing element nodes

* (only for elements that inherit :class:`~element.TextElement`)
  by changing the ``head`` attribute.

Consider these examples (using the same music as above):

Add a note::

    >>> from quickly.dom import lily
    >>> music[0].append(lily.Note('e'))
    >>> music.write()
    "{ <c' g'>4( a'2) f:16-. e }"

Remove all octave marks::

    >>> for node in music // lily.Octave:
    ...     node.parent.remove(node)
    ...
    >>> music.write()
    '{ <c g>4( a2) f:16-. e }'

Using ``//`` you can iterate over all descendant elements of a node
that are an instance of the specified type. See for more information
the :mod:`~quickly.node` module.

Add an octave mark to all notes that don't have one::

    >>> for node in music // lily.Note:
    ...     if not any(node / lily.Octave):
    ...         node.insert(0, lily.Octave(2))
    ...
    >>> music.write()
    "{ <c'' g''>4( a''2) f'':16-. e'' }"

Change the note names::

    >>> for node in music // lily.Note:
    ...     node.head += 'is'
    ...
    >>> music.write()
    "{ <cis'' gis''>4( ais''2) fis'':16-. eis'' }"

TODO: Really understanding the pitches and modifying them in a musical manner
(e.g. transposing) will be implemented using a helper class that holds track of
the current pitch language, and the last duration etc.

Move all slurs up (only where they start)::

    >>> for slur in music // lily.Slur:
    ...     if slur.head == "start":
    ...         if isinstance(slur.parent, lily.Direction):
    ...             slur.parent.head = 1
    ...         else:
    ...             direction = lily.Direction(1)
    ...             slur.parent[slur.parent.index(slur)] = direction
    ...             direction.append(slur)
    ...
    >>> music.write()
    "{ <cis'' gis''>4^( ais''2) fis'':16-. eis'' }"

The above example iterates over all slur events, and selects those that are a
start event (``(``). If they already have a :class:`lily.Direction` parent, its
direction is set to 1 (up). Otherwise, a Direction element is created and the
slur appended to it (and thus reparented).

In the following example we remove durations that are the same as the previous
note::

    >>> tree = parce.root(LilyPond.root, "{ <c' g'>4 e8 e8 g16 g16 8 }")
    >>> music = t.transform_tree(tree)
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.MusicList (6 children) [0:28]>
        ├╴<lily.Music (2 children)>
        │  ├╴<lily.Chord (2 children) [2:9]>
        │  │  ├╴<lily.Note 'c' (1 child) [3:4]>
        │  │  │  ╰╴<lily.Octave 1 [4:5]>
        │  │  ╰╴<lily.Note 'g' (1 child) [6:7]>
        │  │     ╰╴<lily.Octave 1 [7:8]>
        │  ╰╴<lily.Duration Fraction(1, 4) [9:10]>
        ├╴<lily.Note 'e' (1 child) [11:12]>
        │  ╰╴<lily.Duration Fraction(1, 8) [12:13]>
        ├╴<lily.Note 'e' (1 child) [14:15]>
        │  ╰╴<lily.Duration Fraction(1, 8) [15:16]>
        ├╴<lily.Note 'g' (1 child) [17:18]>
        │  ╰╴<lily.Duration Fraction(1, 16) [18:20]>
        ├╴<lily.Note 'g' (1 child) [21:22]>
        │  ╰╴<lily.Duration Fraction(1, 16) [22:24]>
        ╰╴<lily.Unpitched (1 child)>
           ╰╴<lily.Duration Fraction(1, 8) [25:26]>
    >>> prev = None
    >>> for node in music[0] / lily.Music:
    ...     if not isinstance(node, lily.Skip):
    ...         for dur in node / lily.Duration:
    ...             if dur.duration() == prev:
    ...                 if not isinstance(node, lily.Unpitched):
    ...                     node.remove(dur)
    ...             else:
    ...                 prev = dur.duration()
    ...
    >>> music.write()
    "{ <c' g'>4 e8 e g16 g 8 }"

Unpitched and Skip *must* have a duration child. A Skip (``\skip``) does not
change the "current" duration in LilyPond however, while an unpitched note
(indicated by a sole duration) does.


Intermezzo: Validity
--------------------

Note that, when modifying a DOM document, you must take care that you produce a
valid LilyPond document. The ``quickly.dom`` module doesn't enforce validity.
Maybe in the future element types could provide some type hints or checks as
per the child elements they allow, and in what particular order.

The behaviour of all element types is very predictable: they print their head
value, and then the output of the child elements, and then the tail value if
there is one. All output interpersed with whitespace according to well-defined
rules.

But that predictability can lead to unexpected results. For example, adding a
duration to a note is straightforward::

    >>> from quickly.dom import lily
    >>> note = lily.Note('c')
    >>> note.append(lily.Duration(1/2))
    >>> note.write()
    'c2'

But when adding a duration to a chord, care must be taken to put the
duration not before the chord's tail (``>``)::

    >>> chord = lily.Chord(*map(lily.Note, 'cega'))
    >>> chord.write()
    '<c e g a>'
    >>> chord.append(lily.Duration(1/4))
    >>> chord.write()
    '<c e g a 4>'       # erroneous!!

In ``python-ly`` this was tackled by making the duration an attribute instead
of a child; but that made handling of the music tree more difficult and the
class definitions unpredictable and complicated.

What makes ``quickly.dom`` special is that it *both* tries to be a semantical
structure that's easy to create, query and manipulate, *and* on the other hand
still strictly follows the printing order of the original document. Which makes
creating and adapting new element types with new output easy.

Another reason to adopt the very same behaviour everywhere is that all element
nodes can keep references to the parce tokens they were transformed from.
Modifications to a transformed DOM document can be collected and written back
to the original source text. More about that later.

So, how do we correctly add a duration to a chord? By wrapping the chord in a
generic :class:`lily.Music` element, much like LilyPond itself can endlessly
wrap music in ``(make-music ...)`` calls::

    >>> chord = lily.Chord(lily.Note('c'), lily.Note('e'), lily.Note('g'), lily.Note('c', lily.Octave(1)))
    >>> chord.write()
    "<c e g c'>"
    >>> chord = lily.Music(chord)
    >>> chord.append(lily.Duration(1/4))
    >>> chord.write()
    "<c e g c'>4"       # valid :-)

The same holds true for adding articulations to a chord, be sure it is wrapped
in a Music element first.


Using a DOM document to edit an original document
-------------------------------------------------

A DOM document that is transformed from a *parce* tree, keeps references to the
originating tokens in the ``head_origin`` and optionally the ``tail_origin``
attribute. That's why such a DOM document shows the positions in the text when
dumping the contents to the console.

When an element is modified by writing to the ``head`` attribute (for
TextElement), a "modified" flag is set when the new value actually is
different.

There are two element methods dealing with this:

* :meth:`~element.Element.edits`, which yields a list of three-tuples (pos, end, text)
  denoting the changes that are made when comparing to the original tree. Although
  the elements have the originating tokens, the tree is needed as well, to see if
  contents was removed.

* :meth:`~element.Element.edit`, which directly writes back the changes to a
  :class:`parce.Document`.

Let's go back to the initial example, but now create a parce Document with the
LilyPond source, instead of only creating a tree::

    >>> import parce.transform
    >>> from quickly.lang.lilypond import LilyPond
    >>> d = parce.Document(LilyPond.root)

We now create the transformer::

    >>> t = parce.transform.Transformer()

But we connect the source document's treebuilder to the transformer (see
the *parce* documentation)::

    >>> t.connect_treebuilder(d.builder())

Now we set the text, the transformer then automatically builds the resulting
DOM::

    >>> d.set_text("{ <c' g'>4( a'2) f:16-. }")
    >>> music = t.result(d.get_root(True))
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.MusicList (3 children) [0:25]>
        ├╴<lily.Music (3 children)>
        │  ├╴<lily.Chord (2 children) [2:9]>
        │  │  ├╴<lily.Note 'c' (1 child) [3:4]>
        │  │  │  ╰╴<lily.Octave 1 [4:5]>
        │  │  ╰╴<lily.Note 'g' (1 child) [6:7]>
        │  │     ╰╴<lily.Octave 1 [7:8]>
        │  ├╴<lily.Duration Fraction(1, 4) [9:10]>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Slur 'start' [10:11]>
        ├╴<lily.Note 'a' (3 children) [12:13]>
        │  ├╴<lily.Octave 1 [13:14]>
        │  ├╴<lily.Duration Fraction(1, 2) [14:15]>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Slur 'stop' [15:16]>
        ╰╴<lily.Note 'f' (1 child) [17:18]>
           ╰╴<lily.Articulations (2 children)>
              ├╴<lily.Tremolo (1 child) [18:19]>
              │  ╰╴<lily.Duration Fraction(1, 16) [19:21]>
              ╰╴<lily.Direction 0 (1 child) [21:22]>
                 ╰╴<lily.Articulation '.' [22:23]>

.. note::

    We give the root context to the :meth:`parce.transform.Transformer.result`
    method, because one Transformer can build, update and cache the transformed
    result for many source documents at once. By giving the root context, we
    get the correct transformed result.

Now we apply some manipulation to the music. Again add "is" to all the note
heads::

    >>> from quickly.dom import lily
    >>> for note in music // lily.Note:
    ...     note.head += "is"
    ...
    >>> list(music.edits(d.get_root()))
    [(3, 4, 'cis'), (6, 7, 'gis'), (12, 13, 'ais'), (17, 18, 'fis')]

We see the changes. With :meth:`~element.Element.edit` we can directly apply them
to the original document::

    >>> music.edit(d)
    4
    >>> d.text()
    "{ <cis' gis'>4( ais'2) fis:16-. }"

The document has changed. The :meth:`~element.Element.edit` method returns the
number of changes that were made. Now that the original document is modified,
the transformer already has run again in the background to update the nodes
that were changed. Nodes that didn't change (but maybe changed position) are
retained and used again. So to start new manipulations on the document, we need
to request the transformed DOM tree again::

    >>> music = t.result(d.get_root())
    >>> music.dump()
    <lily.Document (1 child)>
     ╰╴<lily.MusicList (3 children) [0:33]>
        ├╴<lily.Music (3 children)>
        │  ├╴<lily.Chord (2 children) [2:13]>
        │  │  ├╴<lily.Note 'cis' (1 child) [3:6]>
        │  │  │  ╰╴<lily.Octave 1 [6:7]>
        │  │  ╰╴<lily.Note 'gis' (1 child) [8:11]>
        │  │     ╰╴<lily.Octave 1 [11:12]>
        │  ├╴<lily.Duration Fraction(1, 4) [13:14]>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Slur 'start' [14:15]>
        ├╴<lily.Note 'ais' (3 children) [16:19]>
        │  ├╴<lily.Octave 1 [19:20]>
        │  ├╴<lily.Duration Fraction(1, 2) [20:21]>
        │  ╰╴<lily.Articulations (1 child)>
        │     ╰╴<lily.Slur 'stop' [21:22]>
        ╰╴<lily.Note 'fis' (1 child) [23:26]>
           ╰╴<lily.Articulations (2 children)>
              ├╴<lily.Tremolo (1 child) [26:27]>
              │  ╰╴<lily.Duration Fraction(1, 16) [27:29]>
              ╰╴<lily.Direction 0 (1 child) [29:30]>
                 ╰╴<lily.Articulation '.' [30:31]>

Let's apply another change, moving all slurs up::

    >>> for slur in music // lily.Slur:
    ...     if slur.head == "start":
    ...         if isinstance(slur.parent, lily.Direction):
    ...             slur.parent.head = 1
    ...         else:
    ...             direction = lily.Direction(1)
    ...             slur.parent[slur.parent.index(slur)] = direction
    ...             direction.append(slur)
    ...
    >>> list(music.edits(d.get_root()))
    [(14, 14, '^')]

One ``^`` needs to be added to the original document::

    >>> music.edit(d)
    1
    >>> d.text()
    "{ <cis' gis'>4^( ais'2) fis:16-. }"

We could also write out the music with ``music.write()`` but the clear
advantage of only applying the changes is that other formatting of the
document, such as whitespace, newlines, comments etc all are preserved.

So with *quickly* we can perform smart music manipulations without being
intrusive to the writer of a LilyPond score.

