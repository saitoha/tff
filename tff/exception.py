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


###############################################################################
#
# Exceptions
#
class NotHandledException(Exception):
    ''' thrown when an unknown seqnence is detected '''

    def __init__(self, value):
        """
        >>> e = NotHandledException("test1")
        >>> e.value
        'test1'
        """
        self.value = value

    def __str__(self):
        """
        >>> e = NotHandledException("test2")
        >>> e.value
        'test2'
        """
        return repr(self.value)


class ParseException(Exception):
    ''' thrown when a parse error is detected '''

    def __init__(self, value):
        """
        >>> e = ParseException("test2")
        >>> e.value
        'test2'
        """
        self.value = value

    def __str__(self):
        """
        >>> e = ParseException("test2")
        >>> e.value
        'test2'
        """
        return repr(self.value)


def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':
    _test()
