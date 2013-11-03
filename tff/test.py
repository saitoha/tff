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

#class DefaultScanner(Scanner):
#    ''' scan input stream and iterate UCS-2 code points '''
#    _data = None
#    _ucs4 = False
#
#    def __init__(self, ucs4=False):
#        """
#        >>> scanner = DefaultScanner()
#        >>> scanner._ucs4
#        False
#        """
#        self._ucs4 = ucs4
#
#    def assign(self, value, termenc):
#        """
#        >>> scanner = DefaultScanner()
#        >>> scanner.assign("01234", "ascii")
#        >>> scanner._data
#        u'01234'
#        """
#        self._data = unicode(value, termenc, 'ignore')
#
#    def __iter__(self):
#        """
#        >>> scanner = DefaultScanner()
#        >>> scanner.assign("abcde", "UTF-8")
#        >>> print [ c for c in scanner ]
#        [97, 98, 99, 100, 101]
#        """
#        if self._ucs4:
#            c1 = 0
#            for x in self._data:
#                c = ord(x)
#                if c >= 0xd800 and c <= 0xdbff:
#                    c1 = c - 0xd800
#                    continue
#                elif c1 != 0 and c >= 0xdc00 and c <= 0xdfff:
#                    c = 0x10000 + ((c1 << 10) | (c - 0xdc00))
#                    c1 = 0
#                yield c
#        else:
#            for x in self._data:
#                yield ord(x)
#


