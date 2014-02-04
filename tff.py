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

__author__  = "Hayaki Saito (user@zuse.jp)"
__version__ = "0.2.9"
__license__ = "MIT"
signature   = '2aaf89c556a5779adf2d6749de196cad'

import sys
import os
import termios
import pty
import signal
import fcntl
import struct
import select
import errno
import codecs
import threading
import logging

_BUFFER_SIZE = 8192
_ESC_TIMEOUT = 0.5  # sec

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


###############################################################################
#
# interfaces
#
# - EventObserver
# - Scanner
# - OutputStream
# - Parser
# - PTY
#
class EventObserver:
    ''' adapt to event driven ECMA-35/48 parser model '''

    def handle_start(self, context):
        raise NotImplementedError("EventObserver::handle_start")

    def handle_end(self, context):
        raise NotImplementedError("EventObserver::handle_end")

    def handle_csi(self, context, params, intermediate, final):
        raise NotImplementedError("EventObserver::handle_csi")

    def handle_esc(self, context, prefix, final):
        raise NotImplementedError("EventObserver::handle_esc")

    def handle_control_string(self, context, prefix, value):
        raise NotImplementedError("EventObserver::handle_control_string")

    def handle_char(self, context, c):
        raise NotImplementedError("EventObserver::handle_char")

    def handle_draw(self, context):
        raise NotImplementedError("EventObserver::handle_draw")

    def handle_invalid(self, context, seq):
        raise NotImplementedError("EventObserver::handle_invalid")

    def handle_resize(self, context, row, col):
        raise NotImplementedError("EventObserver::handle_resize")


class Scanner:
    ''' forward input iterator '''

    def __iter__(self):
        raise NotImplementedError("Scanner::__iter__")

    # deprecated
    def assign(self, value, termenc):
        raise NotImplementedError("Scanner::assign")

    def continuous_assign(self, value, termenc):
        raise NotImplementedError("Scanner::continuous_assign")

class OutputStream:
    ''' abstruct TTY output stream '''

    def write(self, c):
        raise NotImplementedError("OutputStream::write")

    def flush(self):
        raise NotImplementedError("OutputStream::flush")


class EventDispatcher:
    ''' Dispatch interface of terminal sequence event oriented parser '''

    def dispatch_esc(self, prefix, final):
        raise NotImplementedError("EventDispatcher::dispatch_esc")

    def dispatch_csi(self, prefix, params, final):
        raise NotImplementedError("EventDispatcher::dispatch_csi")

    def dispatch_control_string(self, prefix, value):
        raise NotImplementedError("EventDispatcher::dispatch_control_string")

    def dispatch_char(self, c):
        raise NotImplementedError("EventDispatcher::dispatch_char")


class Parser:
    ''' abstruct Parser '''

    def parse(self, context):
        raise NotImplementedError("Parser::parse")


class PTY:
    ''' abstruct PTY device '''

    def fitsize(self):
        raise NotImplementedError("PTY::fitsize")

    def resize(self, height, width):
        raise NotImplementedError("PTY::resize")

    def read(self):
        raise NotImplementedError("PTY::read")

    def write(self, data):
        raise NotImplementedError("PTY::write")

    def xon(self):
        raise NotImplementedError("PTY::xon")

    def xoff(self):
        raise NotImplementedError("PTY::xoff")

    def drive(self):
        raise NotImplementedError("PTY::drive")


###############################################################################
#
# Simple Parser implementation
#
class SimpleParser(Parser):
    ''' simple parser, don't parse ESC/CSI/string seqneces '''

    class _MockContext:

        def __init__(self):
            self.output = []

        def __iter__(self):
            for i in [1, 2, 3, 4, 5]:
                yield i

        def dispatch_char(self, c):
            self.output.append(c)

    def parse(self, context):
        """
        >>> parser = SimpleParser()
        >>> context = SimpleParser._MockContext()
        >>> parser.parse(context)
        >>> context.output
        [1, 2, 3, 4, 5]
        """
        for c in context:
            context.dispatch_char(c)


###############################################################################
#
# Default Parser implementation
#
_STATE_GROUND = 0
_STATE_ESC = 1
_STATE_ESC_INTERMEDIATE = 2
_STATE_CSI_PARAMETER = 3
_STATE_CSI_INTERMEDIATE = 4
_STATE_SS2 = 6
_STATE_SS3 = 7
_STATE_OSC = 8
_STATE_OSC_ESC = 9
_STATE_STR = 10
_STATE_STR_ESC = 11


class _MockHandler:

    def handle_csi(self, context, parameter, intermediate, final):
        print (parameter, intermediate, final)

    def handle_esc(self, context, intermediate, final):
        print (intermediate, final)

    def handle_control_string(self, context, prefix, value):
        print (prefix, value)

    def handle_char(self, context, c):
        print (c)


class DefaultParser(Parser):
    ''' parse ESC/CSI/string seqneces '''

    def __init__(self):
        self.reset()

    def init(self, context):
        self.__context = context

    def state_is_esc(self):
        return self.__state != _STATE_GROUND

    def flush(self):
        pbytes = self.__pbytes
        ibytes = self.__ibytes
        state = self.__state
        context = self.__context
        if state == _STATE_ESC:
            context.dispatch_char(0x1b)
        elif state == _STATE_ESC_INTERMEDIATE:
            context.dispatch_invalid([0x1b] + ibytes)
        elif state == _STATE_CSI_INTERMEDIATE:
            context.dispatch_invalid([0x1b, 0x5b] + ibytes)
        elif state == _STATE_CSI_PARAMETER:
            context.dispatch_invalid([0x1b, 0x5b] + ibytes + pbytes)

    def reset(self):
        self.__state = _STATE_GROUND
        self.__pbytes = []
        self.__ibytes = []

    def parse(self, data):

        context = self.__context
        context.assign(data)
        pbytes = self.__pbytes
        ibytes = self.__ibytes
        state = self.__state
        for c in context:

            if state == _STATE_GROUND:
                if c == 0x1b:  # ESC
                    ibytes = []
                    state = _STATE_ESC

                else:  # control character
                    context.dispatch_char(c)

            elif state == _STATE_ESC:
                #
                # - ISO-6429 independent escape sequense
                #
                #     ESC F
                #
                # - ISO-2022 designation sequence
                #
                #     ESC I ... I F
                #
                if c == 0x5b:  # [
                    pbytes = []
                    state = _STATE_CSI_PARAMETER
                elif c == 0x5d:  # ]
                    pbytes = [c]
                    state = _STATE_OSC
                elif c == 0x4e:  # N
                    state = _STATE_SS2
                elif c == 0x4f:  # O
                    state = _STATE_SS3
                elif c == 0x50 or c == 0x58 or c == 0x5e or c == 0x5f:
                    # P(DCS) or X(SOS) or ^(PM) or _(APC)
                    pbytes = [c]
                    state = _STATE_STR
                elif c < 0x20:  # control character
                    if c == 0x1b:  # ESC
                        seq = [0x1b]
                        context.dispatch_invalid(seq)
                        ibytes = []
                        state = _STATE_ESC
                    elif c == 0x18 or c == 0x1a:
                        seq = [0x1b]
                        context.dispatch_invalid(seq)
                        context.dispatch_char(c)
                        state = _STATE_GROUND
                    else:
                        context.dispatch_char(c)
                elif c <= 0x2f:  # SP to /
                    ibytes.append(c)
                    state = _STATE_ESC_INTERMEDIATE
                elif c <= 0x7e:  # ~
                    context.dispatch_esc(ibytes, c)
                    state = _STATE_GROUND
                elif c == 0x7f:  # control character
                    context.dispatch_char(c)
                else:
                    seq = [0x1b, c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND

            elif state == _STATE_CSI_PARAMETER:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #     ^
                if c > 0x7e:
                    if c == 0x7f:  # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b, 0x5b] + pbytes
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x3f:  # Final byte, @ to ~
                    context.dispatch_csi(pbytes, ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x2f:  # parameter, 0 to ?
                    pbytes.append(c)
                elif c > 0x1f:  # intermediate, SP to /
                    ibytes.append(c)
                    state = _STATE_CSI_INTERMEDIATE

                # control chars
                elif c == 0x1b:  # ESC
                    seq = [0x1b, 0x5b] + pbytes
                    context.dispatch_invalid(seq)
                    ibytes = []
                    state = _STATE_ESC

                elif c == 0x18 or c == 0x1a:  # CAN, SUB
                    seq = [0x1b, 0x5b] + pbytes
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)
                    state = _STATE_GROUND

                else:
                    context.dispatch_char(c)

            elif state == _STATE_CSI_INTERMEDIATE:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #             ^
                if c > 0x7e:
                    if c == 0x7f:  # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b, 0x5b] + pbytes + ibytes
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x3f:  # Final byte, @ to ~
                    context.dispatch_csi(pbytes, ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x2f:
                    seq = [0x1b, 0x5b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                elif c > 0x1f:  # intermediate, SP to /
                    ibytes.append(c)
                    state = _STATE_CSI_INTERMEDIATE

                # control chars
                elif c == 0x1b:  # ESC
                    seq = [0x1b, 0x5b] + pbytes + ibytes
                    context.dispatch_invalid(seq)
                    ibytes = []
                    state = _STATE_ESC
                elif c == 0x18 or c == 0x1a:
                    seq = [0x1b, 0x5b] + pbytes + ibytes
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)
                    state = _STATE_GROUND
                else:
                    context.dispatch_char(c)

            elif state == _STATE_ESC_INTERMEDIATE:
                if c > 0x7e:
                    if c == 0x7f:  # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b] + ibytes + [c]
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x2f:  # 0 to ~, Final byte
                    context.dispatch_esc(ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x1f:  # SP to /
                    ibytes.append(c)
                    state = _STATE_ESC_INTERMEDIATE
                elif c == 0x1b:  # ESC
                    seq = [0x1b] + ibytes
                    context.dispatch_invalid(seq)
                    ibytes = []
                    state = _STATE_ESC
                elif c == 0x18 or c == 0x1a:
                    seq = [0x1b] + ibytes
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)
                    state = _STATE_GROUND
                else:
                    context.dispatch_char(c)

            elif state == _STATE_OSC:
                # parse control string
                if c == 0x07:
                    context.dispatch_control_string(pbytes[0], ibytes)
                    state = _STATE_GROUND
                elif c < 0x08:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                elif c < 0x0e:
                    ibytes.append(c)
                elif c == 0x1b:
                    state = _STATE_OSC_ESC
                elif c < 0x20:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                else:
                    ibytes.append(c)

            elif state == _STATE_STR:
                # parse control string
                # 00/08 - 00/13, 02/00 - 07/14
                #
                if c < 0x08:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                elif c < 0x0e:
                    ibytes.append(c)
                elif c == 0x1b:
                    state = _STATE_STR_ESC
                elif c < 0x20:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                else:
                    ibytes.append(c)

            elif state == _STATE_OSC_ESC:
                # parse control string
                if c == 0x5c:
                    context.dispatch_control_string(pbytes[0], ibytes)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b] + pbytes + ibytes + [0x1b, c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND

            elif state == _STATE_STR_ESC:
                # parse control string
                # 00/08 - 00/13, 02/00 - 07/14
                #
                if c == 0x5c:
                    context.dispatch_control_string(pbytes[0], ibytes)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b] + pbytes + ibytes + [0x1b, c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND

            elif state == _STATE_SS3:
                if c < 0x20:  # control character
                    if c == 0x1b:  # ESC
                        seq = [0x1b, 0x4f]
                        context.dispatch_invalid(seq)
                        ibytes = []
                        state = _STATE_ESC
                    elif c == 0x18 or c == 0x1a:
                        seq = [0x1b, 0x4f]
                        context.dispatch_invalid(seq)
                        context.dispatch_char(c)
                        state = _STATE_GROUND
                    else:
                        context.dispatch_char(c)
                elif c < 0x7f:
                    context.dispatch_ss3(c)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b, 0x4f]
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)

            elif state == _STATE_SS2:
                if c < 0x20:  # control character
                    if c == 0x1b:  # ESC
                        seq = [0x1b, 0x4e]
                        context.dispatch_invalid(seq)
                        ibytes = []
                        state = _STATE_ESC
                    elif c == 0x18 or c == 0x1a:
                        seq = [0x1b, 0x4e]
                        context.dispatch_invalid(seq)
                        context.dispatch_char(c)
                        state = _STATE_GROUND
                    else:
                        context.dispatch_char(c)
                elif c < 0x7f:
                    context.dispatch_ss2(c)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b, 0x4f]
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)

        self.__pbytes = pbytes
        self.__ibytes = ibytes
        self.__state = state



###############################################################################
#
# Scanner implementation
#
class DefaultScanner(Scanner):
    ''' scan input stream and iterate UCS code points '''

    def __init__(self, ucs4=True, termenc=None):
        """
        >>> scanner = DefaultScanner()
        >>> scanner._ucs4
        True
        """
        self._data = None
        self._ucs4 = ucs4
        if termenc:
            self._decoder = codecs.getincrementaldecoder(termenc)(errors='replace')
            self._termenc = termenc
        else:
            self._decoder = None
            self._termenc = None

    # deprecated
    def assign(self, value, termenc):
        """
        >>> scanner = DefaultScanner()
        >>> scanner.assign("01234", "ascii")
        >>> scanner._data
        u'01234'
        """
        if self._termenc != termenc:
            self._decoder = codecs.getincrementaldecoder(termenc)(errors='replace')
            self._termenc = termenc
        self._data = self._decoder.decode(value)

    def continuous_assign(self, value):
        """
        >>> scanner = DefaultScanner(termenc="utf-8")
        >>> scanner.continuous_assign("01234")
        >>> scanner._data
        u'01234'
        """
        self._data = self._decoder.decode(value)

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



###############################################################################
#
# Handler implementation
#
class DefaultHandler(EventObserver):
    ''' default handler, pass through all ESC/CSI/string seqnceses '''
    def __init__(self):
        pass

# EventObserver
    def handle_start(self, context):
        pass

    def handle_end(self, context):
        pass

    def handle_esc(self, context, intermediate, final):
        return False

    def handle_csi(self, context, parameter, intermediate, final):
        return False

    def handle_ss2(self, context, final):
        return False

    def handle_ss3(self, context, final):
        return False

    def handle_control_string(self, context, prefix, value):
        return False

    def handle_char(self, context, c):
        return False

    def handle_invalid(self, context, seq):
        return False

    def handle_draw(self, context):
        pass

    def handle_resize(self, context, row, col):
        pass


###############################################################################
#
# Multiplexer implementation
#
class FilterMultiplexer(EventObserver):

    def __init__(self, lhs, rhs):
        self.__lhs = lhs
        self.__rhs = rhs

    def get_lhs(self):
        return self.__lhs

    def get_rhs(self):
        return self.__rhs

    def handle_start(self, context):
        handled_lhs = self.__lhs.handle_start(context)
        handled_rhs = self.__rhs.handle_start(context)
        return handled_lhs and handled_rhs

    def handle_end(self, context):
        handled_lhs = self.__lhs.handle_end(context)
        handled_rhs = self.__rhs.handle_end(context)
        return handled_lhs and handled_rhs

    def handle_flush(self, context):
        handled_lhs = self.__lhs.handle_flush(context)
        handled_rhs = self.__rhs.handle_flush(context)
        return handled_lhs and handled_rhs

    def handle_csi(self, context, params, intermediate, final):
        handled_lhs = self.__lhs.handle_csi(context, params,
                                            intermediate, final)
        handled_rhs = self.__rhs.handle_csi(context, params,
                                            intermediate, final)
        return handled_lhs and handled_rhs

    def handle_esc(self, context, intermediate, final):
        handled_lhs = self.__lhs.handle_esc(context, intermediate, final)
        handled_rhs = self.__rhs.handle_esc(context, intermediate, final)
        return handled_lhs and handled_rhs

    def handle_control_string(self, context, prefix, value):
        handled_lhs = self.__lhs.handle_control_string(context, prefix, value)
        handled_rhs = self.__rhs.handle_control_string(context, prefix, value)
        return handled_lhs and handled_rhs

    def handle_char(self, context, c):
        handled_lhs = self.__lhs.handle_char(context, c)
        handled_rhs = self.__rhs.handle_char(context, c)
        return handled_lhs and handled_rhs

    def handle_invalid(self, context, seq):
        handled_lhs = self.__lhs.handle_invalid(context, seq)
        handled_rhs = self.__rhs.handle_invalid(context, seq)
        return handled_lhs and handled_rhs

    def handle_draw(self, context):
        handled_lhs = self.__lhs.handle_draw(context)
        handled_rhs = self.__rhs.handle_draw(context)
        return handled_lhs and handled_rhs

    def handle_resize(self, context, row, col):
        handled_lhs = self.__lhs.handle_resize(context, row, col)
        handled_rhs = self.__rhs.handle_resize(context, row, col)
        return handled_lhs and handled_rhs


###############################################################################
#
# Dispatcher implementation
#
class ParseContext(OutputStream, EventDispatcher):

    def __init__(self,
                 output,
                 termenc='UTF-8',
                 scanner=DefaultScanner(),
                 handler=DefaultHandler(),
                 buffering=False):
        self.__termenc = termenc
        self.__scanner = scanner
        self.__handler = handler
        self._c1 = 0

        if buffering:
            try:
                from cStringIO import StringIO
                self._output = codecs.getwriter(termenc)(StringIO())
            except ImportError:
                try:
                    from StringIO import StringIO
                    self._output = codecs.getwriter(termenc)(StringIO())
                except ImportError:
                    from io import StringIO
                    self._output = codecs.getwriter(termenc)(StringIO())
        else:
            self._output = codecs.getwriter(termenc)(output)
        self._target_output = output
        self._buffering = buffering

    def __iter__(self):
        return self.__scanner.__iter__()

    def assign(self, data):
        self.__scanner.assign(data, self.__termenc)
        if self._buffering:
            self._output.truncate(0)

    def sethandler(self, handler):
        self.__handler = handler

    def putu(self, data):
        self._output.write(data)

    def puts(self, data):
        self._target_output.write(data)

    def put(self, c):
        if c < 0x80:
            self._output.write(chr(c))
        elif c < 0xd800:
            self._output.write(unichr(c))
        elif c < 0xdc00:
            self._c1 = c
        elif c < 0xe000:
            self._output.write(unichr(self._c1) + unichr(c))
        elif c < 0x10000:
            self._output.write(unichr(c))
        else:  # c > 0x10000
            c -= 0x10000
            c1 = (c >> 10) + 0xd800
            c2 = (c & 0x3ff) + 0xdc00
            self._output.write(unichr(c1) + unichr(c2))

    # obsoluted!!
    def writestring(self, data):
        try:
            self._target_output.write(data)
        except Exception:
            self._output.write(data)

# OutputStream
    # obsoluted!!
    def write(self, c):
        self.put(c)

    def flush(self):
        if self._buffering:
            self._target_output.write(self._output)
        try:
            self._target_output.flush()
        except IOError:
            pass

# EventDispatcher
    def dispatch_esc(self, intermediate, final):
        if not self.__handler.handle_esc(self, intermediate, final):
            self.put(0x1b)  # ESC
            for c in intermediate:
                self.put(c)
            self.put(final)

    def dispatch_csi(self, parameter, intermediate, final):
        if not self.__handler.handle_csi(self, parameter, intermediate, final):
            self.put(0x1b)  # ESC
            self.put(0x5b)  # [
            for c in parameter:
                self.put(c)
            for c in intermediate:
                self.put(c)
            self.put(final)

    def dispatch_ss2(self, final):
        if not self.__handler.handle_ss2(self, final):
            self.put(0x1b)  # ESC
            self.put(0x4e)  # N
            self.put(final)

    def dispatch_ss3(self, final):
        if not self.__handler.handle_ss3(self, final):
            self.put(0x1b)  # ESC
            self.put(0x4f)  # O
            self.put(final)

    def dispatch_control_string(self, prefix, value):
        if not self.__handler.handle_control_string(self, prefix, value):
            self.put(0x1b)  # ESC
            self.put(prefix)
            for c in value:
                self.put(c)
            self.put(0x1b)  # ESC
            self.put(0x5c)  # \

    def dispatch_char(self, c):
        if not self.__handler.handle_char(self, c):
            self.put(c)

    def dispatch_invalid(self, seq):
        if not self.__handler.handle_invalid(self, seq):
            for c in seq:
                self.put(c)


###############################################################################
#
# DefaultPTY
#
class DefaultPTY(PTY):

    def __init__(self, term, lang, command, stdin):
        self._stdin_fileno = stdin.fileno()
        backup = termios.tcgetattr(self._stdin_fileno)
        self._backup_termios = backup
        pid, master = pty.fork()
        if not pid:
            os.environ['TERM'] = term
            os.environ['LANG'] = lang
            os.execlp('/bin/sh',
                      '/bin/sh', '-c',
                      'exec %s' % command)

        self.__setupterm(self._stdin_fileno)
        self.pid = pid
        self._master = master

    def close(self):
        #self.restore_term()
        try:
            os.close(self._master)
        except OSError, e:
            logging.exception(e)
            logging.info("DefaultPTY.close: master=%d" % self._master)

    def restore_term(self):
        termios.tcsetattr(self._stdin_fileno,
                          termios.TCSANOW,
                          self._backup_termios)

    def __setupterm(self, fd):
        term = termios.tcgetattr(fd)

        ## c_iflag
        #IUTF8 = 16384
        term[0] &= ~(termios.IGNBRK
                     | termios.BRKINT
                     | termios.PARMRK
                     | termios.ISTRIP
                     | termios.INLCR
                     | termios.IGNCR
                     | termios.ICRNL
                     | termios.IXON)

        term[1] &= ~(termios.OPOST
                     | termios.ONLCR)

        # c_cflag
        c_cflag = term[2]
        c_cflag &= ~(termios.CSIZE | termios.PARENB)
        c_cflag |= termios.CS8
        term[2] = c_cflag

        ## c_lflag
        c_lflag = term[3]
        c_lflag &= ~(termios.ECHO
                     | termios.ECHONL
                     | termios.ICANON
                     | termios.ISIG
                     | termios.IEXTEN)
        term[3] = c_lflag

        # c_cc
        # this PTY is jast a filter, so it must not fire signals
        vdisable = os.fpathconf(self._stdin_fileno, 'PC_VDISABLE')
        VDSUSP = 11
        c_cc = term[6]
        c_cc[termios.VEOF] = vdisable  # Ctrl-D
        c_cc[termios.VINTR] = vdisable  # Ctrl-C
        c_cc[termios.VREPRINT] = vdisable  # Ctrl-R
        c_cc[termios.VSTART] = vdisable  # Ctrl-Q
        c_cc[termios.VSTOP] = vdisable  # Ctrl-S
        c_cc[termios.VLNEXT] = vdisable  # Ctrl-V
        c_cc[termios.VWERASE] = vdisable  # Ctrl-W
        c_cc[termios.VKILL] = vdisable  # Ctrl-X
        c_cc[termios.VSUSP] = vdisable  # Ctrl-Z
        c_cc[termios.VQUIT] = vdisable  # Ctrl-\
        c_cc[VDSUSP] = vdisable  # Ctrl-Y

        termios.tcsetattr(fd, termios.TCSANOW, term)

    def __resize_impl(self, winsize):
        fcntl.ioctl(self._master, termios.TIOCSWINSZ, winsize)
        # notify Application process that terminal size has been changed.
        os.kill(self.pid, signal.SIGWINCH)

    def fitsize(self):
        winsize = fcntl.ioctl(self._stdin_fileno, termios.TIOCGWINSZ, 'hhhh')
        height, width = struct.unpack('hh', winsize)
        self.__resize_impl(winsize)
        return height, width

    def resize(self, height, width):
        winsize = struct.pack('HHHH', height, width, 0, 0)
        self.__resize_impl(winsize)
        return height, width

    def fileno(self):
        return self._master

    def stdin_fileno(self):
        return self._stdin_fileno

    def read(self):
        return os.read(self._master, _BUFFER_SIZE)

    def write(self, data):
        os.write(self._master, data)

    def flush(self):
        pass
        #os.fsync(self._master)

    def xoff(self):
        #fcntl.ioctl(self._master, termios.TIOCSTOP, 0)
        termios.tcflow(self._master, termios.TCOOFF)

    def xon(self):
        #fcntl.ioctl(self._master, termios.TIOCSTART, 0)
        termios.tcflow(self._master, termios.TCOON)

class MockParseContext(ParseContext):

    def __init__(self):
        from StringIO import StringIO
        output = StringIO()
        ParseContext.__init__(self, output)


###############################################################################
#
# Process
#
class Process:

    _tty = None
    _esc_timer = None

    def __init__(self, tty):
        self._tty = tty

    def start(self, termenc,
              inputhandler, outputhandler,
              inputparser, outputparser,
              inputscanner, outputscanner,
              buffering=False,
              stdout=sys.stdout):

        inputcontext = ParseContext(output=self._tty,
                                    termenc=termenc,
                                    scanner=inputscanner,
                                    handler=inputhandler,
                                    buffering=buffering)
        outputcontext = ParseContext(output=stdout,
                                     termenc=termenc,
                                     scanner=outputscanner,
                                     handler=outputhandler,
                                     buffering=buffering)

        inputparser.init(inputcontext)
        outputparser.init(outputcontext)

        self._inputhandler = inputhandler
        self._outputhandler = outputhandler
        self._inputparser = inputparser
        self._outputparser = outputparser
        self._inputcontext = inputcontext
        self._outputcontext = outputcontext
        inputhandler.handle_start(outputcontext)
        outputhandler.handle_start(outputcontext)

    def getpid(self):
        return self._tty.pid

    def is_alive(self):
        return self._tty is not None 

    def fileno(self):
        return self._tty.fileno()

    def stdin_fileno(self):
        return self._tty.stdin_fileno()

    def read(self):
        return self._tty.read()

    def write(self, data):
        self._tty.write(data)

    def close(self):
        if self._tty is not None:
            self._tty.close()
            self._tty = None

    def end(self):
        self._inputhandler.handle_end(self._outputcontext)
        self._outputhandler.handle_end(self._outputcontext)

    def resize(self, row, col):
        self._tty.resize(row, col)

    def fitsize(self):
        return self._tty.fitsize()

    def on_write(self, data):
        self._inputparser.parse(data)

    def process_start(self):
        self._inputhandler.handle_start(self._inputcontext)
        self._outputhandler.handle_start(self._outputcontext)
        self._inputhandler.handle_draw(self._outputcontext)
        self._outputhandler.handle_draw(self._outputcontext)
        #self._inputcontext.flush()
        self._outputcontext.flush()

    def process_end(self):
        self._inputhandler.handle_end(self._inputcontext)
        self._outputhandler.handle_end(self._outputcontext)

    def process_resize(self, row, col):
        try:
            self._inputhandler.handle_resize(self._inputcontext, row, col)
            self._outputhandler.handle_resize(self._outputcontext, row, col)
        finally:
            self._resized = False

    def process_input(self, data):
        if not self._esc_timer is None:
            self._esc_timer.cancel()
            self._esc_timer = None

        self._inputparser.parse(data)

        # set ESC timer
        if not self._inputparser.state_is_esc():
            self._inputhandler.handle_draw(self._outputcontext)
            self._outputhandler.handle_draw(self._outputcontext)
            #self._inputcontext.flush()
            self._outputcontext.flush()
        else:
            def dispatch_esc():
                self._inputparser.flush()
                self._inputparser.reset()
                self._inputhandler.handle_draw(self._outputcontext)
                self._outputhandler.handle_draw(self._outputcontext)
                #self._inputcontext.flush()
                self._outputcontext.flush()
            self._esc_timer = threading.Timer(_ESC_TIMEOUT, dispatch_esc)
            self._esc_timer.start()

    def process_output(self, data):
        self._outputparser.parse(data)
        if not self._outputparser.state_is_esc():
            self._inputhandler.handle_draw(self._outputcontext)
            self._outputhandler.handle_draw(self._outputcontext)
            #self._inputcontext.flush()
            self._outputcontext.flush()

    def on_read(self, data):
        self._outputparser.parse(data)

    def drain(self):
        self._inputparser.reset()
        self._inputcontext.assign('')


###############################################################################
#
# Session
#
class Session:

    def __init__(self, tty):

        self._alive = True
        self._mainprocess = Process(tty)
        self._input_target = self._mainprocess
        stdin_fileno = self._mainprocess.stdin_fileno()
        self._rfds = [stdin_fileno]
        self._xfds = [stdin_fileno]
        self._resized = False
        self._process_map = {}

    def add_subtty(self, term, lang,
                   command, row, col,
                   termenc,
                   inputhandler=DefaultHandler(),
                   outputhandler=DefaultHandler()):

        tty = DefaultPTY(term, lang, command, sys.stdin)
        tty.resize(row, col)
        process = Process(tty)

        self._init_process(process,
                           termenc,
                           inputhandler, outputhandler,
                           DefaultParser(), DefaultParser(),
                           DefaultScanner(), DefaultScanner(),
                           buffering=False)
        self.focus_process(process)
        return process

    def getactiveprocess(self):
        return self._input_target

    def process_is_active(self, process):
        return self._input_target == process

    def focus_process(self, process):
        if process.is_alive():
            logging.info("Switching focus: fileno=%d" % process.fileno())
            self._input_target.drain()
            self._input_target = process

    def blur_process(self):
        process = self._mainprocess
        if process.is_alive():
            logging.info("Switching focus: fileno=%d (main process)" % process.fileno())
            self._input_target.drain()
            self._input_target = process

    def destruct_process(self, process):
        fd = process.fileno()
        if fd in self._rfds:
            self._rfds.remove(fd)
        if fd in self._xfds:
            self._xfds.remove(fd)
        process.end()
        process.close()
        del self._process_map[fd]

        self.focus_process(self._mainprocess)
        self._mainprocess.process_output("")

    def drive(self):

        def onresize(no, frame):
            ''' handle resize '''
            self._resized = True

        try:
            signal.signal(signal.SIGWINCH, onresize)
        except ValueError:
            pass

        stdin_fileno = self._mainprocess.stdin_fileno()
        try:
            while self._alive:
                try:
                    rfd, wfd, xfd = select.select(self._rfds, [], self._xfds, 0.6)
                    if xfd:
                        for fd in xfd:
                            if fd in self._process_map:
                                process = self._process_map[fd]
                                self.destruct_process(process)
                                continue
                    if self._resized:
                        self._resized = False
                        row, col = self._mainprocess.fitsize()
                        self._mainprocess.process_resize(row, col)
                    if rfd:
                        for fd in rfd:
                            if fd == stdin_fileno:
                                data = os.read(stdin_fileno, _BUFFER_SIZE)
                                if self._input_target.is_alive():
                                    target_fd = self._input_target.fileno()
                                    process = self._process_map[target_fd]
                                    process.process_input(data)
                                    self._mainprocess.process_input("")
                            elif self._process_map:
                                process_map = self._process_map
                                if fd in process_map:
                                    process = process_map[fd]
                                    if self._input_target.is_alive():
                                        if fd == self._input_target.fileno():
                                            data = process.read()
                                            process.on_read(data)
                                            self._mainprocess.process_output("")
                    else:
                        pass
                except select.error, e:
                    no, msg = e
                    if no == errno.EINTR:
                        # The call was interrupted by a signal
                        self._resized = True
                    elif no == errno.EBADF:
                        for fd in self._process_map:
                            process = self._process_map[fd]
                            self.destruct_process(process)
                    else:
                        raise e
                except OSError, e:
                    no, msg = e
                    if no == errno.EINTR:
                        # The call was interrupted by a signal
                        self._resized = True
                    else:
                        raise e
        except OSError, e:
            no, msg = e
            if no == errno.EIO:
                return
            elif no == errno.EBADF:
                return
            else:
                raise e
        finally:
            try:
                self._mainprocess.process_end()
            finally:
                for fd in self._process_map:
                    process = self._process_map[fd]
                    process.end()
                    process.close()

    def start(self,
              termenc,
              stdin=sys.stdin,
              stdout=sys.stdout,
              inputscanner=DefaultScanner(),
              inputparser=DefaultParser(),
              inputhandler=DefaultHandler(),
              outputscanner=DefaultScanner(),
              outputparser=DefaultParser(),
              outputhandler=DefaultHandler(),
              buffering=False):

        mainprocess = self._mainprocess

        self._init_process(mainprocess,
                           termenc,
                           inputhandler, outputhandler,
                           inputparser, outputparser,
                           inputscanner, outputscanner,
                           buffering)
        self.focus_process(mainprocess)

        self._resized = False

        def onclose(no, frame):
            pid, status = os.wait()
            if not mainprocess.is_alive():
                self._alive = False
            elif pid == mainprocess.getpid():
                self._alive = False
            else:
                self.focus_process(mainprocess)

        signal.signal(signal.SIGCHLD, onclose)

        self.drive()

    def _init_process(self,
                      process,
                      termenc,
                      inputhandler, outputhandler,
                      inputparser, outputparser,
                      inputscanner, outputscanner,
                      buffering):

        fd = process.fileno()
        self._rfds.append(fd)
        self._xfds.append(fd)
        self._process_map[fd] = process

        process.start(termenc,
                      inputhandler,
                      outputhandler,
                      inputparser,
                      outputparser,
                      inputscanner,
                      outputscanner,
                      buffering)


def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':

    import inspect
    import hashlib
    import sys
    
    thismodule = sys.modules[__name__]
    md5 = hashlib.md5()
    specs = []
    for name, member in inspect.getmembers(thismodule):
        if inspect.isclass(member):
            if name[0] != "_":
                classname = name
                for name, member in inspect.getmembers(member):
                    if inspect.ismethod(member):
                        if name.startswith("__") or name[0] != "_":
                            argspec = inspect.getargspec(member)
                            args, varargs, keywords, defaultvalue = argspec
                            specstr = "%s.%s.%s" % (classname, name, args)
                            specs.append(specstr)
    specs.sort()
    md5.update("".join(specs))
    sys.stdout.write(md5.hexdigest())


