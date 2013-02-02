#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ***** BEGIN LICENSE BLOCK *****
# Copyright (C) 2012  Hayaki Saito <user@zuse.jp>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
        test1
        """
        self.value = value

    def __str__(self):
        """
        >>> e = NotHandledException("test2")
        >>> print e
        'test2'
        """
        return repr(self.value)


class ParseException(Exception):
    ''' thrown when a parse error is detected '''

    def __init__(self, value):
        """
        >>> e = ParseException("test2")
        >>> e.value
        test2
        """
        self.value = value

    def __str__(self):
        """
        >>> e = ParseException("test2")
        >>> print e
        'test2'
        """
        return repr(self.value)


def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':
    _test()
