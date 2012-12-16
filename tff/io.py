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

import sys, os, termios, pty, signal, fcntl, struct, select, errno
import codecs, threading
from interface import * # terminal filter framework interface
from exception import *

_BUFFER_SIZE = 2048
_ESC_TIMEOUT = 0.1 # sec

################################################################################
#
# Scanner implementation
#
class DefaultScanner(Scanner):
    ''' scan input stream and iterate UCS-2 code points '''
    _data = None
    _ucs4 = False

    def __init__(self, ucs4=False):
        """
        >>> scanner = DefaultScanner()
        >>> scanner._ucs4
        False
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
                    c =  0x10000 + ((c1 << 10) | (c - 0xdc00))
                    c1 = 0
                yield c
        else:
            for x in self._data:
                yield ord(x)

################################################################################
#
# Simple Parser implementation
#
class SimpleParser(Parser):
    ''' simple parser, don't parse ESC/CSI/string seqneces '''

    class _MockContext:

        output = []

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
 
################################################################################
#
# Default Parser implementation
#
_STATE_GROUND           = 0
_STATE_ESC              = 1
_STATE_ESC_INTERMEDIATE = 2
_STATE_CSI_PARAMETER    = 3
_STATE_CSI_INTERMEDIATE = 4
_STATE_SS2              = 6
_STATE_SS3              = 7
_STATE_OSC              = 8
_STATE_OSC_ESC          = 9
_STATE_STR              = 10 
_STATE_STR_ESC          = 11

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

    esc_timeout = _ESC_TIMEOUT 

    def __init__(self):
        self.__state = _STATE_GROUND
        self.__pbytes = [] 
        self.__ibytes = [] 
        self.__timer = None

    def parse(self, context):

        pbytes = self.__pbytes
        ibytes = self.__ibytes
        state = self.__state

        if self.__state == _STATE_ESC:
            if not self.__timer is None:
                self.__timer.cancel()

        for c in context:

            if state == _STATE_GROUND:
                if c == 0x1b: # ESC
                    del ibytes[:]
                    state = _STATE_ESC

                else: # control character
                    context.dispatch_char(c)

            elif state == _STATE_CSI_PARAMETER:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #     ^
                if c > 0x7e:
                    if c == 0x7f: # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b, 0x5b] + pbytes
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x3f: # Final byte, @ to ~
                    context.dispatch_csi(pbytes, ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x2f: # parameter, 0 to ?
                    pbytes.append(c)
                elif c > 0x1f: # intermediate, SP to /
                    ibytes.append(c)
                    state = _STATE_CSI_INTERMEDIATE
                elif c == 0x1b: # ESC
                    seq = [0x1b, 0x5b] + pbytes
                    context.dispatch_invalid(seq)
                    del ibytes[:]
                    state = _STATE_ESC
                elif c == 0x18 or c == 0x1a: # CAN, SUB
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
                    if c == 0x7f: # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b, 0x5b] + pbytes + ibytes
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x3f: # Final byte, @ to ~
                    context.dispatch_csi(pbytes, ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x2f:
                    seq = [0x1b, 0x5b] + pbytes + ibytes
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                elif c > 0x1f: # intermediate, SP to /
                    ibytes.append(c)
                    state = _STATE_CSI_INTERMEDIATE
                elif c == 0x1b: # ESC
                    seq = [0x1b, 0x5b] + pbytes + ibytes
                    context.dispatch_invalid(seq)
                    del ibytes[:]
                    state = _STATE_ESC
                elif c == 0x18 or c == 0x1a:
                    seq = [0x1b, 0x5b] + pbytes + ibytes
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)
                    state = _STATE_GROUND
                else:
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
                if c == 0x5b: # [
                    del pbytes[:]
                    state = _STATE_CSI_PARAMETER
                elif c == 0x5d: # ]
                    del pbytes[:] 
                    pbytes.append(c)
                    state = _STATE_OSC
                elif c == 0x4e: # N
                    state = _STATE_SS2
                elif c == 0x4f: # O
                    state = _STATE_SS3
                elif c == 0x50 or c == 0x58 or c == 0x5e or c == 0x5f:
                    # P(DCS) or X(SOS) or ^(PM) or _(APC)
                    del pbytes[:]
                    pbytes.append(c)
                    state = _STATE_STR
                elif c < 0x20: # control character
                    if c == 0x1b: # ESC
                        seq = [0x1b]
                        context.dispatch_invalid(seq)
                        del ibytes[:]
                        state = _STATE_ESC
                    elif c == 0x18 or c == 0x1a:
                        seq = [0x1b]
                        context.dispatch_invalid(seq)
                        context.dispatch_char(c)
                        state = _STATE_GROUND
                    else:
                        context.dispatch_char(c)
                elif c <= 0x2f: # SP to /
                    ibytes.append(c)
                    state = _STATE_ESC_INTERMEDIATE
                elif c <= 0x7e: # ~
                    context.dispatch_esc(ibytes, c)
                    state = _STATE_GROUND
                elif c == 0x7f: # control character
                    context.dispatch_char(c)
                else:
                    seq = [0x1b, c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND

            elif state == _STATE_ESC_INTERMEDIATE:
                if c > 0x7e:
                    if c == 0x7f: # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b] + ibytes
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x2f: # 0 to ~, Final byte
                    context.dispatch_esc(ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x1f: # SP to /
                    ibytes.append(c)
                    state = _STATE_ESC_INTERMEDIATE
                elif c == 0x1b: # ESC
                    seq = [0x1b] + ibytes
                    context.dispatch_invalid(seq)
                    del ibytes[:]
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
                if c < 0x20: # control character
                    if c == 0x1b: # ESC
                        seq = [0x1b, 0x4f]
                        context.dispatch_invalid(seq)
                        del ibytes[:]
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
                if c < 0x20: # control character
                    if c == 0x1b: # ESC
                        seq = [0x1b, 0x4e]
                        context.dispatch_invalid(seq)
                        del ibytes[:]
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

        # set ESC timer
        if self.__state == _STATE_ESC:
            def dispatch_esc():
                self.__state = _STATE_GROUND
                context.dispatch_char(0x1b)
            self.__timer = threading.Timer(self.esc_timeout, dispatch_esc)
            self.__timer.start()

################################################################################
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

    def handle_char(self, context, c):
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


################################################################################
#
# Multiplexer implementation
#
class FilterMultiplexer(EventObserver):

    def __init__(self, lhs, rhs):
        self.__lhs = lhs
        self.__rhs = rhs

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
        handled_lhs = self.__lhs.handle_csi(context, params, intermediate, final)
        handled_rhs = self.__rhs.handle_csi(context, params, intermediate, final)
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


################################################################################
#
# Dispatcher implementation
#
class ParseContext(OutputStream, EventDispatcher):

    __c1 = 0

    def __init__(self,
                 output,
                 termenc = 'UTF-8',
                 scanner = DefaultScanner(),
                 handler = DefaultHandler(),
                 buffering = False):
        self.__termenc = termenc
        self.__scanner = scanner 
        self.__handler = handler
        if buffering:
            try:
                from cStringIO import StringIO
            except:
                try:
                    from StringIO import StringIO
                except:
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
            self.__c1 = c
        elif c < 0xe000:
            self._output.write(unichr(self.__c1) + unichr(c))
        elif c < 0x10000:
            self._output.write(unichr(c))
        else: # c > 0x10000
            c -= 0x10000
            c1 = (c >> 10) + 0xd800
            c2 = (c & 0x3ff) + 0xdc00
            self._output.write(unichr(c1) + unichr(c2))

    # obsoluted!!
    def writestring(self, data):
        try:
            self._target_output.write(data)
        except:
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
        except IOError, e:
            pass

# EventDispatcher
    def dispatch_esc(self, intermediate, final):
        if not self.__handler.handle_esc(self, intermediate, final):
            self.put(0x1b) # ESC
            for c in intermediate:
                self.put(c)
            self.put(final)

    def dispatch_csi(self, parameter, intermediate, final):
        if not self.__handler.handle_csi(self, parameter, intermediate, final):
            self.put(0x1b) # ESC
            self.put(0x5b) # [
            for c in parameter:
                self.put(c)
            for c in intermediate:
                self.put(c)
            self.put(final)

    def dispatch_ss2(self, final):
        if not self.__handler.handle_ss2(self, final):
            self.put(0x1b) # ESC
            self.put(0x4e) # N
            self.put(final)

    def dispatch_ss3(self, final):
        if not self.__handler.handle_ss3(self, final):
            self.put(0x1b) # ESC
            self.put(0x4f) # O
            self.put(final)

    def dispatch_control_string(self, prefix, value):
        if not self.__handler.handle_control_string(self, prefix, value):
            self.put(0x1b) # ESC
            self.put(prefix)
            for c in value:
                self.put(c)
            self.put(0x1b) # ESC
            self.put(0x5c) # \

    def dispatch_char(self, c):
        if not self.__handler.handle_char(self, c):
            #if c < 0x20 or c == 0x7f:
            #    self.put(c)
            #else: 
            self.put(c)

    def dispatch_invalid(self, seq):
        if not self.__handler.handle_invalid(self, seq):
            for c in seq:
                self.put(c)

################################################################################
#
# DefaultPTY
#
class DefaultPTY(PTY):

    _stdin_fileno = None
    _backup_termios = None
    _master = None

    def __init__(self, term, lang, command, stdin):
        self._stdin_fileno = stdin.fileno()
        backup = termios.tcgetattr(self._stdin_fileno)
        self.__setupterm(self._stdin_fileno)
        pid, master = pty.fork()
        if not pid:
            os.environ['TERM'] = term 
            os.environ['LANG'] = lang 

            term = termios.tcgetattr(0)

            # c_oflag
            term[1] = backup[1]
            #term[1] &= ~termios.ONLCR 
            # c_cflag
            #term[2] &= ~(termios.CSIZE | termios.PARENB)
            #term[2] |= termios.CS8
            
            termios.tcsetattr(0, termios.TCSANOW, term)
            os.execlp('/bin/sh',
                      '/bin/sh', '-c',
                      'exec %s' % command)

        self.__pid = pid
        self._master = master
    
    def __del__(self):
        termios.tcsetattr(self._stdin_fileno,
                          termios.TCSANOW,
                          self._backup_termios)

    def __setupterm(self, fd):
        self._backup_termios = termios.tcgetattr(fd)
        term = termios.tcgetattr(fd)

        ## c_iflag
        #IUTF8 = 16384
        term[0] &= ~(termios.IGNBRK
                  | termios.BRKINT
                  | termios.PARMRK 
                  | termios.ISTRIP
                  | termios.INLCR
                  | termios.IGNCR 
                  | termios.ICRNL)

        term[1] &= ~termios.ONLCR 

        ## c_lflag
        term[3] = term[3] &~ (termios.ECHO | termios.ICANON)

        # c_cc
        # this PTY is jast a filter, so it must not fire signals
        vdisable = os.fpathconf(self._stdin_fileno, 'PC_VDISABLE')
        VDSUSP = 11
        c_cc = term[6]
        c_cc[termios.VINTR]    = vdisable  # Ctrl-C
        c_cc[termios.VREPRINT] = vdisable  # Ctrl-R
        c_cc[termios.VSTART]   = vdisable  # Ctrl-Q
        c_cc[termios.VSTOP]    = vdisable  # Ctrl-S
        c_cc[termios.VLNEXT]   = vdisable  # Ctrl-V
        c_cc[termios.VWERASE]  = vdisable  # Ctrl-W
        c_cc[termios.VKILL]    = vdisable  # Ctrl-X
        c_cc[termios.VSUSP]    = vdisable  # Ctrl-Z
        c_cc[termios.VQUIT]    = vdisable  # Ctrl-\
        c_cc[VDSUSP]           = vdisable  # Ctrl-Y

        termios.tcsetattr(fd, termios.TCSANOW, term)

    def __resize_impl(self, winsize):
         fcntl.ioctl(self._master, termios.TIOCSWINSZ, winsize)
         # notify Application process that terminal size has been changed.
         os.kill(self.__pid, signal.SIGWINCH)

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

    def drive(self):
        master = self._master
        stdin_fileno = self._stdin_fileno
        rfds = [stdin_fileno, master]
        wfds = []
        xfds = [stdin_fileno, master]
        try:
            while True: 
                try:
                    rfd, wfd, xfd = select.select(rfds, wfds, xfds)
                    if xfd:
                        break
                    for fd in rfd:
                        if fd == stdin_fileno:
                            data = os.read(stdin_fileno, _BUFFER_SIZE)
                            if data:
                                yield data, None, None
                        elif fd == master:
                            data = self.read()
                            if data:
                                yield None, data, None
                except select.error, e:
                    no, msg = e
                    if no == errno.EINTR: # The call was interrupted by a signal
                        yield None, None, e
                    else:
                        raise e
        finally:
            os.close(master)


 
################################################################################
#
# Session
#
class Session:

    def __init__(self, tty):
        self.tty = tty

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
 
        tty = self.tty
        inputcontext = ParseContext(output=tty,
                                    termenc=termenc,
                                    scanner=inputscanner,
                                    handler=inputhandler,
                                    buffering=buffering)
        outputcontext = ParseContext(output=stdout,
                                     termenc=termenc,
                                     scanner=outputscanner,
                                     handler=outputhandler,
                                     buffering=buffering)
        self._resized = False

        def onresize(no, frame):
            if not self._resized:
                self._resized = True
        try:
            signal.signal(signal.SIGWINCH, onresize)
        except ValueError:
            pass

        def onclose(no, frame):
            sys.exit(0)

        try:
            signal.signal(signal.SIGCHLD, onclose)
        except ValueError:
            pass

        inputhandler.handle_start(inputcontext)
        outputhandler.handle_start(outputcontext)
        inputhandler.handle_draw(inputcontext)
        outputhandler.handle_draw(outputcontext)
        inputcontext.flush()
        outputcontext.flush()
        
        try:
            for idata, odata, edata in tty.drive():
                if idata:
                    inputcontext.assign(idata)
                    inputparser.parse(inputcontext)
                    inputhandler.handle_draw(outputcontext)
                    outputhandler.handle_draw(outputcontext)
                    inputcontext.flush()
                    outputcontext.flush()
                if odata:
                    outputcontext.assign(odata)
                    outputparser.parse(outputcontext)
                    inputhandler.handle_draw(outputcontext)
                    outputhandler.handle_draw(outputcontext)
                    inputcontext.flush()
                    outputcontext.flush()
                if self._resized:
                    row, col = tty.fitsize()
                    self._resized = False
                    inputhandler.handle_resize(inputcontext, row, col)
                    outputhandler.handle_resize(outputcontext, row, col)
                    self._dirty = True
        except OSError, e:
            no, msg = e
            if no == errno.EIO:
                return
            else:
                raise e
        finally:
            inputhandler.handle_end(inputcontext)
            outputhandler.handle_end(outputcontext)


def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':    
    _test()

