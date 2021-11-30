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
LaTeX language and transformation definition.
"""

import itertools

from parce import skip, lexicon, default_target
from parce.rule import bygroup, ifarg, ifeq, ifgroup
import parce.lang.tex
import parce.action as a

from quickly.dom import base, element, lily, scm, tex
from . import lilypond


class Latex(parce.lang.tex.Latex):
    """Latex language definition."""
    @classmethod
    def get_environment_target(cls, name):
        return ifeq(name, "lilypond",
            (lilypond.LilyPond.latex_lilypond_environment, cls.test_lilypond_option),
            super().get_environment_target(name))

    @classmethod
    def common(cls):
        yield r'(\\lilypond)\s*(?:(\{)|(\[))?', bygroup(a.Name.Builtin, a.Delimiter.Brace, a.Delimiter), \
            ifgroup(2, lilypond.LilyPond.latex_lilypond_environment('short form'),
                ifgroup(3, cls.option("lilypond")))
        yield from super().common()

    @lexicon
    def option(cls):
        yield ifarg(r'(\])\s*(\{)'), bygroup(a.Delimiter, a.Delimiter.Brace), -1, \
                lilypond.LilyPond.latex_lilypond_environment('short form')
        yield from super().option
        yield r'\[', a.Delimiter.Bracket    # this can match if we were here looking for a [

    @lexicon
    def test_lilypond_option(cls):
        """One time check for Latex options at the beginning of a LilyPond environment.

        This lexicon never creates a context.

        """
        yield r'(?=\s*\[)', skip, -1, cls.option
        yield default_target, -1


class LatexTransform(base.Transform):
    """Transform Latex quickly.dom."""
    ## Transform methods
    def root(self, items):
        """Process the ``root`` context."""
        return tex.Document(*self.common(items))

    def brace(self, items):
        """Process the ``brace`` context; returns a Brace node."""
        head = items[:1]
        tail = (items.pop(),) if items[-1] == '}' else ()
        return self.factory(tex.Brace, head, tail, *self.common(items[1:]))

    def option(self, items):
        r"""Process the ``option`` context.

        Returns a two-tuple(options, head_origin).

        The options is a list of objects that are finished Option nodes, only the
        first might be incomplete because of a missing opening token. In that
        case the first object is a tuple (contents, tail_origin). (The
        tail_origin might be empty in the case of an imcomplete source text).

        The head_origin is normally empty, only for the ``\lilypond[opts]{``
        command, it is the brace that starts the braced expression.

        """
        command_head = ()
        if items.peek(-1, a.Delimiter.Brace):
            # opening bracket of short form LilyPond command
            command_head = (items.pop(),)
        i = 0
        if items.peek(0, a.Delimiter.Bracket) and items[0].text == '[':
            # complete first Option node
            head_origin = items[0:1]
            i = 1
        else:
            head_origin = ()
        nodes = []
        pos = i
        while True:
            try:
                i = items.index(']', pos)
            except ValueError:
                nodes.append(self.factory(tex.Option, head_origin, (), *self.common(items[pos:])))
                break
            tail_origin = items[i],
            if head_origin:
                # append complete node
                nodes.append(self.factory(tex.Option, head_origin, tail_origin, *self.common(items[pos:i])))
            else:
                # append contents and tail origin, head is in a previous context
                nodes.append( (self.common(items[pos:i]), items[i:i+1]) )
            pos = i + 1
            # another Option node?
            try:
                i = items.index('[', pos)
            except ValueError:
                break
            pos = i + 1
            head_origin = items[i:pos]
        return nodes, command_head

    def environment_option(self, items):
        """Process the ``environment_option`` context.

        Returns a tuple(option, envname), where *option* is a list like the
        first value returned by :meth:`option` and *envname* an
        :class:`~quickly.dom.tex.EnvironmentName` node it it was there at the
        end of the options list, otherwise None.

        """
        env_name = None
        if items.peek(-3, a.Delimiter, a.Name.Tag, a.Delimiter):
            # environment name at end
            env_name = self.factory(tex.EnvironmentName, items[-3:])
            del items[-3:]
        return self.option(items)[0], env_name

    def environment_math(self, items):
        """Process the ``environment_math`` context."""
        return self.environment(items)

    def environment(self, items):
        r"""Process the ``environment`` context.

        Returns a list of nodes, the last is the ``\end`` command.

        """
        end = None
        if items.peek(-4, a.Name.Builtin, a.Delimiter, a.Name.Tag, a.Delimiter):
            end = self.factory(tex.Command, items[-4:-3])
            end.append(self.factory(tex.EnvironmentName, items[-3:]))
            items = items[:-4]
        nodes = self.common(items)
        if end:
            nodes.append(end)
        return nodes

    _math_mapping = element.head_mapping(
        tex.MathInlineParen, tex.MathInlineDollar, tex.MathDisplayBracket,
        tex.MathDisplayDollar)

    def math(self, items):
        """Process the ``math`` context; return a Math node."""
        head = items[:1]
        cls = self._math_mapping[head[0].text]
        tail = (items.pop(),) if len(items) > 1 and items[-1] == cls.tail else ()
        return self.factory(cls, head, tail, *self.common(items[1:]))

    def comment(self, items):
        """Process the ``comment`` context."""
        return self.factory(tex.Comment, items)

    test_lilypond_option = None # never creates content

    ## Helper methods
    def common(self, items):
        """Compose and yield Latex nodes; used in most contexts."""
        result = []
        text = []
        z = len(items)
        i = 0

        def get_options(options):
            """Yield Option nodes; i must be at the ``[``."""
            if isinstance(options[0], tuple):
                head = items[i:i+1]
                contents, tail = options[0]
                yield self.factory(tex.Option, head, tail, *contents)
                options = options[1:]
            yield from options

        def command(t):
            """Return a generic Command node. Arguments are appended as child."""
            nonlocal i
            cmd = self.factory(tex.Command, (t,))
            # options? append as child
            if items.peek(i, a.Delimiter.Bracket, "option"):
                cmd.extend(get_options(items[i+1].obj[0]))
                i += 2
            # braced piece of text? append as child
            if items.peek(i, "brace"):
                cmd.append(items[i].obj)
                i += 1
            return cmd

        def lilypond_command(t):
            r"""Return the Command node for a \lilypond { ... } command."""
            nonlocal i
            cmd = self.factory(tex.Command, (t,))
            if items.peek(i, a.Delimiter.Brace, 'latex_lilypond_environment'):
                options, music, tail = items[i+1].obj
                cmd.append(self.factory(tex.Brace, items[i:i+1], tail, *music))
                i += 2
            elif items.peek(i, a.Delimiter, 'option'):
                options, cmd_head = items[i+1].obj
                cmd.extend(get_options(options))
                i += 2
                if items.peek(i, 'latex_lilypond_environment'):
                    options, music, tail = items[i].obj
                    cmd.append(self.factory(tex.Brace, cmd_head, tail, *music))
                    i += 1
            return cmd

        def environment(t):
            """Return an Environment node, possibly containing LilyPond music."""
            nonlocal i
            env = tex.Environment(self.factory(tex.Command, (t,)))
            if items.peek(i, a.Delimiter, a.Name.Tag, a.Delimiter):
                # no options, add the name
                env[-1].append(self.factory(tex.EnvironmentName, items[i:i+3]))
                i += 3
            elif items.peek(i, a.Delimiter.Bracket, "environment_option"):
                # environment options
                options, env_name = items[i+1].obj
                env[-1].extend(get_options(options))
                if env_name:
                    env[-1].append(env_name)
                i += 2
            # now add the environment
            if i < z and not items[i].is_token:
                if items[i].name in ('environment', 'environment_math'):
                    env.extend(items[i].obj)
                elif items[i].name == 'latex_lilypond_environment':
                    options, music, tail = items[i].obj
                    env[-1].extend(options)
                    env.extend(music)
                else:
                    print("unknown Latex environment:", items[i].name) #TEMP
                i += 1
            return env

        while i < z:
            node = None
            t = items[i]
            i += 1
            if t.is_token:
                if t.action is a.Name.Builtin:
                    if t == r'\lilypond':
                        node = lilypond_command(t)
                    else:   # if t -- r'\begin':
                        node = environment(t)
                elif t.action is a.Name.Command:
                    node = command(t)
                else:
                    text.append(t)
            # t is a context result
            elif isinstance(t.obj, element.Element):
                node = t.obj
            else:
                print("unknown object:", t.name) # TEMP
            if node:
                if text:
                    result.append(self.factory(tex.Text, text))
                    text = []
                result.append(node)
        if text:
            result.append(self.factory(tex.Text, text))
        return result



class LatexAdHocTransform(base.AdHocTransform, LatexTransform):
    """LatexTransform that does not keep the origin tokens."""
    pass


