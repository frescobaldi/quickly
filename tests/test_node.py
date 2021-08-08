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
Test the node module.
"""

### find quickly
import sys
sys.path.insert(0, '.')

from quickly.node import Node


class N1(Node):
    pass


class N2(Node):
    pass


class N3(Node):
    pass


class M1(N1):
    pass


class M2(N2):
    pass


class M3(N3):
    pass


tree = \
N1(
    N2(
        N3(),
        M3(),
        N2(),
        M1(),
    ),
    N1(
        M2(),
    ),
)


def test_main():
    assert next(tree//M3) is tree[0][1]
    assert len(list(tree/N2)) == 1
    assert sum(1 for _ in tree//N2) == 3     # M2 inherits from N2 :-)
    assert sum(1 for _ in tree.instances_of(N2)) == 2   # topmost N2's children are skipped
    assert next(tree[1][0] << N1) is tree[1]
    tree2 = tree.copy()
    assert tree.equals(tree2)
    tree2[0][3] = N1()
    assert not tree.equals(tree2)
    assert tree[0][2].common_ancestor(tree[1][0]) is tree
    assert tree[0][2].common_ancestor(tree2[1][0]) is None



if __name__ == "__main__" and 'test_main' in globals():
    test_main()

