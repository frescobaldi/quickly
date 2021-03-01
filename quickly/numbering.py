# -*- coding: utf-8 -*-
#
# This file is part of `quickly`, a library for LilyPond and the `.ly` format
#
# Copyright © 2019-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Functions dealing with numbering of voices, parts etcetera.
"""


import string



def int2roman(n):
    """Convert an integer value to a roman number string.

    E.g. 1 -> "I", 12 -> "XII", 2015 -> "MMXV"

    ``n`` has to be an integer >= 1; raises ValueError otherwise.

    """
    if n < 1:
        raise ValueError('Roman numerals must be positive integers, got %s' % n)

    roman_numerals = (
        ("M", 1000), ("CM", 900), ("D", 500), ("CD", 400),
        ("C", 100), ("XC", 90), ("L", 50), ("XL", 40), ("X", 10), ("IX", 9), ("V", 5),
        ("IV", 4), ("I", 1),
    )

    roman = []
    for char, num in roman_numerals:
        k, n = divmod(n, num)
        roman.append(char * k)
    return "".join(roman)


def roman2int(s):
    """Convert a string with a roman numeral to an integer.

    E.g. "MCMLXVII" -> 1967, "iii" -> 3

    Raises a KeyError on invalid characters.

    """

    roman_numerals = {'I':1, 'V':5, 'X':10, 'L':50, 'C':100, 'D':500, 'M':1000 }
    num = prev = 0
    for char in reversed(s.upper()):
        val = roman_numerals[char]
        if val < prev:
            num -= val
            continue
        prev = val
        num += val
    return num


def int2letter(n, chars=string.ascii_uppercase):
    """Convert an integer to one or more letters.

    E.g. 1 -> "A", 2 -> "B", ... 26 -> "Z", 27 -> "AA", etc.
    Zero returns the empty string.

    chars is the string to pick characters from, defaulting to
    ``string.ascii_uppercase``.

    """
    mod = len(chars)
    result = []
    while n > 0:
        n, c = divmod(n - 1, mod)
        result.append(c)
    return "".join(chars[c] for c in reversed(result))


def letter2int(s, chars=string.ascii_uppercase):
    """Convert a string with letters to an integer.

    E.g. "AA" -> 27

    An empty string yields 0. Raises a ValueError when a character is not
    available in ``chars`` (which defaults to ``string.ascii_uppercase``).

    """
    mod = len(chars)
    result = 0
    for char in s:
        result *= mod
        result += chars.index(char) + 1
    return result


_nums = (
    '', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
    'sixteen', 'seventeen', 'eighteen', 'nineteen')

_tens = (
    'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty',
    'ninety')


def int2text(n):
    """Convert an integer to the English language name of that integer.

    E.g. converts 1 to "One". Supports numbers 0 to 999999.
    This can be used in LilyPond identifiers (that do not support digits).

    """
    result = []
    if n >= 1000:
        hundreds, n = divmod(n, 1000)
        result.append(int2text(hundreds) + "Thousand")
    if n >= 100:
        tens, n = divmod(n, 100)
        result.append(_nums[tens].title() + "Hundred")
    if n < 20:
        result.append(_nums[n].title())
    else:
        tens, n = divmod(n, 10)
        result.append(_tens[tens-2].title() + _nums[n].title())
    text = "".join(result)
    return text or 'Zero'


def text2int(s):
    """Convert a text number in English language to an integer.

    E.g. "TwentyOne" -> 21, 'three' -> 3

    Ignores preceding other text.

    """
    s = s.strip().lower()
    if s in ('', 'zero'):
        return 0
    for num, t in enumerate(_nums[1:], 1):
        if s.endswith(t):
            s = s[:-len(t)]
            break
    else:
        num = 0
    if s:
        for n, t in enumerate(_tens, 2):
            if s.endswith(t):
                s = s[:-len(t)]
                num += n*10
                break
        if s.endswith('hundred'):
            s = s[:-7]
            if s:
                for n, t in enumerate(_nums[1:], 1):
                    if s.endswith(t):
                        s = s[:-len(t)]
                        num += n*100
                        break
            else:
                num += 100
        if s.endswith('thousand'):
            s = s[:-8]
            if s:
                num += text2int(s) * 1000
            else:
                num += 1000
    return num

