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
import codecs
from interface import * # terminal filter framework interface

BUFFER_SIZE = 2048

################################################################################
#
# Exceptions 
#
class NotHandledException(Exception):
    ''' thrown when unknown seqnence is detected '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ParseException(Exception):
    ''' thrown when parse error is detected '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


################################################################################
#
# Scanner implementation
#
class DefaultScanner(Scanner):
    ''' scan input stream and iterate UCS-2 code points '''
    __data = None
    _ucs4 = False

    def __init__(self, ucs4=False):
        self._ucs4 = ucs4

    def assign(self, value, termenc):
        self.__data = unicode(value, termenc, 'ignore')

    def __iter__(self):
        if self._ucs4:
            c1 = 0
            for x in self.__data:
                c = ord(x) 
                if c >= 0xd800 and c <= 0xdbff:
                    c1 = c - 0xd800
                    continue
                elif c1 != 0 and c >= 0xdc00 and c <= 0xdfff:
                    c =  0x10000 + ((c1 << 10) | (c - 0xdc00))
                    c1 = 0
                yield c
        else:
            for x in self.__data:
                yield ord(x)

################################################################################
#
# Simple Parser implementation
#
class SimpleParser(Parser):
    ''' simple parser, don't parse ESC/CSI/string seqneces '''
    def __init__(self):
        pass

    def parse(self, context):
        for c in context:
            context.dispatch_char(c)
 
################################################################################
#
# Default Parser implementation
#
_STATE_GROUND = 0
_STATE_ESC = 1
_STATE_ESC_INTERMEDIATE = 2
_STATE_CSI_PARAMETER = 3
_STATE_CSI_INTERMEDIATE = 4
_STATE_OSC = 6
_STATE_STR = 7 

class DefaultParser(Parser):
    ''' parse ESC/CSI/string seqneces '''

    def __init__(self):
        self.__parse_state = _STATE_GROUND
        self.__csi_parameter = [] 
        self.__csi_intermediate = [] 
        self.__esc_intermediate = [] 
        self.__str = [] 
        self.__str_prefix = None 
        self.__str_esc_state = False

    def parse(self, context):
        for c in context:
            if self.__parse_state == _STATE_OSC:
                # parse control string
                if c == 0x1b:
                    self.__str_esc_state = True
                elif c == 0x5c and self.__str_esc_state == True:
                    context.dispatch_control_string(self.__str_prefix, self.__str)
                    self.__parse_state = _STATE_GROUND
                elif c == 0x07:
                    context.dispatch_control_string(self.__str_prefix, self.__str)
                    self.__parse_state = _STATE_GROUND
                elif c < 0x20:
                    self.__parse_state = _STATE_GROUND
                else:
                    self.__str.append(c)

            elif self.__parse_state == _STATE_STR:
                # parse control string
                if c == 0x1b:
                    self.__str_esc_state = True
                elif c == 0x5c and self.__str_esc_state == True:
                    context.dispatch_control_string(self.__str_prefix, self.__str)
                    self.__parse_state = _STATE_GROUND
                elif c < 0x20:
                    self.__parse_state = _STATE_GROUND
                else:
                    self.__str.append(c)

            elif c == 0x1b: # ESC
                self.__esc_intermediate = []
                self.__parse_state = _STATE_ESC

            elif c < 0x20 or c == 0x7f: # control character
                context.dispatch_char(c)
                #self.__parse_state = _STATE_GROUND

            elif self.__parse_state == _STATE_ESC:
                if c == 0x5b: # [
                    self.__csi_parameter = []
                    self.__csi_intermediate = [] 
                    self.__parse_state = _STATE_CSI_PARAMETER
                elif c == 0x5d: # ]
                    self.__str_esc_state = False
                    self.__str = [] 
                    self.__str_prefix = c 
                    self.__parse_state = _STATE_OSC
                elif c == 0x50 or c == 0x58 or c == 0x5e or c == 0x5f:
                    # P(DCS) or X(SOS) or ^(PM) or _(APC)
                    self.__str_esc_state = False
                    self.__str = []
                    self.__str_prefix = c 
                    self.__parse_state = _STATE_STR
                elif 0x20 <= c and c <= 0x2f: # SP to /
                    self.__esc_intermediate.append(c)
                    self.__parse_state = _STATE_ESC_INTERMEDIATE
                elif c <= 0x7e: # ~
                    context.dispatch_esc(self.__esc_intermediate, c)
                    self.__parse_state = _STATE_GROUND
                else:
                    self.__parse_state = _STATE_GROUND
                    #raise ParseException("Unknown ESC seqnence detected.")

            elif self.__parse_state == _STATE_ESC_INTERMEDIATE:
                if c <= 0x1f: # Control char 
                    context.dispatch_char(c)
                elif 0x20 <= c and c <= 0x2f: # SP to /
                    self.__esc_intermediate.append(c)
                    self.__parse_state = _STATE_ESC_INTERMEDIATE
                elif 0x30 <= c and c <= 0x7e: # 0 to ~, Final byte
                    context.dispatch_esc(self.__esc_intermediate, c)
                    self.__parse_state = _STATE_GROUND
                else:
                    self.__parse_state = _STATE_GROUND
                    #raise ParseException("Unknown ESC seqnence detected.")

            elif self.__parse_state == _STATE_CSI_PARAMETER:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #     ^
                if 0x30 <= c and c <= 0x3f: # parameter, 0 to ?
                    self.__csi_parameter.append(c)
                elif 0x20 <= c and c <= 0x2f: # intermediate, SP to /
                    self.__csi_intermediate.append(c)
                    self.__parse_state = _STATE_CSI_INTERMEDIATE
                elif 0x40 <= c and c <= 0x7e: # Final byte, @ to ~
                    context.dispatch_csi(self.__csi_parameter,
                                         self.__csi_intermediate,
                                         c)
                    self.__parse_state = _STATE_GROUND
                else:
                    self.__parse_state = _STATE_GROUND
                    #raise ParseException("Unknown CSI seqnence detected.")

            elif self.__parse_state == _STATE_CSI_INTERMEDIATE:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #             ^
                if 0x20 <= c and c <= 0x2f: # intermediate, SP to /
                    self.__csi_intermediate.append(c)
                    self.__parse_state = _STATE_CSI_INTERMEDIATE
                elif 0x40 <= c and c <= 0x7e: # Final byte, @ to ~
                    context.dispatch_csi(self.__csi_parameter,
                                         self.__csi_intermediate,
                                         c)
                    self.__parse_state = _STATE_GROUND
                else:
                    self.__parse_state = _STATE_GROUND
                    #raise ParseException("Unknown CSI seqnence detected.")

            else:
                context.dispatch_char(c)


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

    def handle_csi(self, context, parameter, intermediate, final):
        return False

    def handle_esc(self, context, intermediate, final):
        return False

    def handle_control_string(self, context, prefix, value):
        return False

    def handle_char(self, context, c):
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
            self.__output = codecs.getwriter(termenc)(StringIO())
        else:
            self.__output = codecs.getwriter(termenc)(output)
        self.__target_output = output
        self._buffering = buffering

    def __iter__(self):
        return self.__scanner.__iter__()

    def writestring(self, data):
        self.__output.write(data)

    def assign(self, data):
        self.__scanner.assign(data, self.__termenc)
        if self._buffering:
            self.__output.truncate(0)

# OutputStream
    def write(self, c):
        if c < 0x80:
            self.__output.write(chr(c))
        elif c >= 0xd800 and c <= 0xdbff:
            self.__c1 = c
        elif c >= 0xdc00 and c <= 0xdfff:
            self.__output.write(unichr(self.__c1) + unichr(c))
        elif c < 0x10000:
            self.__output.write(unichr(c))
        else: # c > 0x10000
            c -= 0x10000
            c1 = (c >> 10) + 0xd800
            c2 = (c & 0x3ff) + 0xdc00
            self.__output.write(unichr(c1) + unichr(c2))

    def flush(self):
        if self._buffering:
            self.__target_output.write(self.__output)
        self.__target_output.flush()


# EventDispatcher
    def dispatch_esc(self, intermediate, final):
        if not self.__handler.handle_esc(self, intermediate, final):
            self.write(0x1b) # ESC
            for c in intermediate:
                self.write(c)
            self.write(final)

    def dispatch_csi(self, parameter, intermediate, final):
        if not self.__handler.handle_csi(self, parameter, intermediate, final):
            self.write(0x1b) # ESC
            self.write(0x5b) # [
            for c in parameter:
                self.write(c)
            for c in intermediate:
                self.write(c)
            self.write(final)

    def dispatch_control_string(self, prefix, value):
        if not self.__handler.handle_control_string(self, prefix, value):
            self.write(0x1b) # ESC
            self.write(prefix)
            for c in value:
                self.write(c)
            self.write(0x1b) # ESC
            self.write(0x5c) # \

    def dispatch_char(self, c):
        if not self.__handler.handle_char(self, c):
            if c < 0x20 or c == 0x7f:
                self.write(c)
            else: 
                self.write(c)

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

        ## c_lflag
        term[3] = term[3] &~ (termios.ECHO | termios.ICANON)

        # c_cc
        vdisable = os.fpathconf(self._stdin_fileno, 'PC_VDISABLE')
        term[6][termios.VINTR] = vdisable     # Ctrl-C
        term[6][termios.VREPRINT] = vdisable  # Ctrl-R
        term[6][termios.VSTART] = vdisable    # Ctrl-Q
        term[6][termios.VSTOP] = vdisable     # Ctrl-S
        term[6][termios.VLNEXT] = vdisable    # Ctrl-V
        term[6][termios.VWERASE] = vdisable   # Ctrl-W
        term[6][termios.VKILL] = vdisable     # Ctrl-X
        term[6][termios.VSUSP] = vdisable     # Ctrl-Z
        term[6][termios.VQUIT] = vdisable     # Ctrl-\

        VDSUSP = 11
        term[6][VDSUSP] = vdisable    # Ctrl-Y

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
        return os.read(self._master, BUFFER_SIZE)

    def write(self, data):
        os.write(self._master, data)

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
                            data = os.read(stdin_fileno, BUFFER_SIZE)
                            if data:
                                yield data, None, None
                        elif fd == master:
                            data = self.read()
                            if data:
                                yield None, data, None
                except OSError, e:
                    no, msg = e
                    if no == errno.EIO:
                        return
                except select.error, e:
                    no, msg = e
                    if no == errno.EINTR:
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
        signal.signal(signal.SIGWINCH, onresize)

        inputhandler.handle_start(inputcontext)
        outputhandler.handle_start(outputcontext)
        inputhandler.handle_draw(inputcontext)
        outputhandler.handle_draw(outputcontext)
        outputcontext.flush()
        try:
            for idata, odata, edata in tty.drive():
                if idata:
                    inputcontext.assign(idata)
                    inputparser.parse(inputcontext)
                    inputhandler.handle_draw(inputcontext)
                    #inputcontext.flush()
                    stdout.flush()
                if odata:
                    outputcontext.assign(odata)
                    outputparser.parse(outputcontext)
                    outputhandler.handle_draw(outputcontext)
                    outputcontext.flush()
                if edata:
                    if self._resized:
                        self._resized = False
                        row, col = tty.fitsize()
                        inputhandler.handle_resize(inputcontext, row, col)
                        outputhandler.handle_resize(outputcontext, row, col)
                        inputhandler.handle_draw(inputcontext)
                        outputhandler.handle_draw(outputcontext)
                    else:
                        raise edata
        finally:
            inputhandler.handle_end(inputcontext)
            outputhandler.handle_end(outputcontext)

''' main '''
if __name__ == '__main__':    
    pass

