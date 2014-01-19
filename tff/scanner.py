#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ***** BEGIN LICENSE BLOCK *****
# Copyright (C) 2012-2014, Hayaki Saito 
# 
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions: 
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software. 
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE. 
# 
# ***** END LICENSE BLOCK *****


from interface import Scanner

###############################################################################
#
# Scanner implementation
#
class DefaultScanner(Scanner):
    ''' scan input stream and iterate UCS code points '''
    _data = None
    _ucs4 = True

    def __init__(self, ucs4=True):
        """
        >>> scanner = DefaultScanner()
        >>> scanner._ucs4
        True
        """
        self._ucs4 = ucs4

    def assign(self, value, termenc):
        """
        >>> scanner = DefaultScanner()
        >>> scanner.assign("01234", "ascii")
        >>> scanner._data
        u'01234'
        """
        self._data = unicode(value, termenc, 'ignore')

    def __iter__(self):
        """
        >>> scanner = DefaultScanner()
        >>> scanner.assign("abcde", "UTF-8")
        >>> print [ c for c in scanner ]
        [97, 98, 99, 100, 101]
        """
        if self._ucs4:
            c1 = 0
            for x in self._data:
                c = ord(x)
                if c >= 0xd800 and c <= 0xdbff:
                    c1 = c - 0xd800
                    continue
                elif c1 != 0 and c >= 0xdc00 and c <= 0xdfff:
                    c = 0x10000 + ((c1 << 10) | (c - 0xdc00))
                    c1 = 0
                yield c
        else:
            for x in self._data:
                yield ord(x)


def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':
    _test()
