#!/usr/bin/python

try:
    from ctff import DefaultScanner
except:
    from tff.scanner import DefaultScanner

from ctff import DefaultParser


def _test1():
    """
    >>> scanner = DefaultScanner()
    >>> scanner._ucs4
    False
    >>> scanner = DefaultScanner()
    >>> scanner.assign("01234", "ascii")
    >>> scanner.assign("012344", "ascii")
    >>> for i in scanner: print i
    48
    49
    50
    51
    52
    52
    >>> scanner = DefaultScanner()
    >>> scanner.assign("abcde", "UTF-8")
    >>> print [ c for c in scanner ]
    [97, 98, 99, 100, 101]
    >>> scanner = DefaultScanner()
    >>> scanner.assign("\xcc\xb3\xe2\x80\x80\xe4\x80\xb4\xe4\x80\x82", "UTF-8")
    >>> print [ c for c in scanner ]
    [819, 8192, 16436, 16386]
    >>> parser = DefaultParser()
    """

def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':
    _test()


