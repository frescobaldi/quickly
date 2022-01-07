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
The Scope class finds included documents.
"""


import reprlib
from urllib.parse import urljoin, urlparse

import parce.util

import quickly


class Scope:
    """A Scope helps finding files included by a parce Document.

    Initialize Scope with a parce Document. The
    :attr:`~parce.document.AbstractDocument.url` attribute of the document
    helps finding included files. That url should be absolute.

    The ``parent`` is specified when a new Scope is created by
    :meth:`include_scope`.

    The ``factory`` keyword parameter and attribute is a callable that should
    return a :class:`parce.Document` for a filename. If you don't specify a
    factory, a default one is used that loads a Document from the file system,
    and if found, caches it using a cache based on the file's mtime.

    Specify a factory to use other caching, deferred loading, or to look for a
    document in a list of open documents in a GUI editor etc.

    If desired, add absolute urls to the :attr:`include_path` instance
    attribute, indicating folders where to search for includeable files.

    """
    def __init__(self, doc, parent=None, factory=None, node=None):
        if not factory:
            factory = parce.util.file_cache(quickly.load).__getitem__
        self._document = doc
        self.parent = parent    #: The parent Scope (None for the root Scope)
        self.factory = factory  #: A callable returning a :class:`parce.Document` for a filename.
        self.node = node        #: The node that was specified to :meth:`include_scope`.
        #: A list of directories to search for \include-d files.
        self.include_path = parent.include_path if parent else []
        #: Whether to search in the directory of an included file for new includes.
        self.relative_include = parent.relative_include if parent else True

    def __repr__(self):
        return "<{} {}>".format(type(self).__name__, reprlib.repr(self.document().url))

    def document(self):
        """Return our parce Document."""
        return self._document

    def include_scope(self, url, node=None):
        """Return a child scope for the url.

        If the ``url`` is relative, it is resolved against our document's url
        (if :attr:`relative_include` is True), the root scope's url and the
        urls in the :attr:`include_path`.

        A ``node`` can be given, that's simply put in the :attr:`node`
        attribute of the returned child scope. It can be used to look further
        in the document that included the current document, to find e.g. a
        variable definition.

        Returns None if no includable document could be found. This scope
        inherits the factory, the include_path and the relative_include setting
        of ourselves.

        """
        for u in self.urls(url):
            doc = self.get_document(u)
            if doc:
                return type(self)(doc, self, self.factory, node)

    def ancestors(self):
        """Yield the ancestor scopes."""
        scope = self
        while scope.parent:
            scope = scope.parent
            yield scope

    def root(self):
        """The root scope."""
        scope = self
        for scope in self.ancestors():
            pass
        return scope

    def urls(self, url):
        """Return a list of unique urls representing possibly includable files.

        The list results from the filename of our document (if set and if
        :attr:`relative_include` is True), the filename of the document that
        started the include chain, and the include path.

        The urls are not checked for existence.

        """
        # skip urls already in parent scopes, prevents circular include hangs
        skip = {self.document().url}
        skip.update(scope.document().url for scope in self.ancestors())

        urls = []
        def add(base_url):
            if base_url:
                u = urljoin(base_url, url)
                if u not in skip and u not in urls:
                    urls.append(u)
        if self.relative_include:
            add(self.document().url)
        add(self.root().document().url)
        for u in self.include_path:
            if not u.endswith('/'):
                u += '/'
            add(u)
        return urls

    def get_document(self, url):
        """Return a parce Document at url.

        Returns None if no document can be found. The default implementation
        calls :attr:`factory` with a filename pointing to the local file
        system. OSErrors raised by the factory are suppressed.

        """
        filename = urlparse(url).path
        try:
            return self.factory(filename)
        except OSError:
            pass

