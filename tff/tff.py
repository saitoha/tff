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
# terminal filter framework interface
from interface import EventObserver, EventDispatcher, OutputStream, PTY
#from exception import NotHandleException, ParseException

_BUFFER_SIZE = 8192
_ESC_TIMEOUT = 0.5  # sec

try:
    from ctff import DefaultScanner
except:
    from scanner import DefaultScanner

try:
    from ctff import DefaultParser as OutputParser
except:
    from parser import DefaultParser as OutputParser
 
from parser import DefaultParser

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

    __c1 = 0

    def __init__(self,
                 output,
                 termenc='UTF-8',
                 scanner=DefaultScanner(),
                 handler=DefaultHandler(),
                 buffering=False):
        self.__termenc = termenc
        self.__scanner = scanner
        self.__handler = handler
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
            self.__c1 = c
        elif c < 0xe000:
            self._output.write(unichr(self.__c1) + unichr(c))
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

###############################################################################
#
# Terminal
#
class Terminal:

    tty = None

    def __init__(self, tty):
        self.tty = tty

    def start(self, termenc, inputhandler, outputhandler, inputparser, outputparser, listener):

        inputcontext = ParseContext(output=self.tty,
                                    termenc=termenc,
                                    scanner=DefaultScanner(),
                                    handler=inputhandler,
                                    buffering=False)
        outputcontext = ParseContext(output=sys.stdout,
                                     termenc=termenc,
                                     scanner=DefaultScanner(),
                                     handler=outputhandler,
                                     buffering=False)

        self._inputparser = inputparser
        self._outputparser = outputparser
        self._listener = listener
        self._inputparser.init(inputcontext)
        self._outputparser.init(outputcontext)
        listener.handle_start(outputcontext)
        self._outputcontext = outputcontext

    def fileno(self):
        return self.tty.fileno()

    def close(self):
        self.tty.close()

    def end(self):
        self._listener.handle_end(self._outputcontext)

    def on_write(self, data):
        self._inputparser.parse(data)

    def on_read(self, fd):
        if fd == self.tty.fileno():
            data = self.tty.read()
            self._outputparser.parse(data)

###############################################################################
#
# Session
#
class Session:

    def __init__(self, tty):

        self._alive = True
        self.terminal = Terminal(tty)
        self.tty = tty
        self._input_target = tty
        main_master = self.tty.fileno()
        stdin_fileno = self.tty.stdin_fileno()
        self._rfds = [stdin_fileno, main_master]
        self._wfds = []
        self._xfds = [stdin_fileno, main_master]
        self._resized = False
        self._ttymap = {}

    def add_subtty(self, term, lang, command, row, col,
                   termenc, inputhandler, outputhandler, listener):

        tty = DefaultPTY(term, lang, command, sys.stdin)
        tty.resize(row, col)
        process = Terminal(tty)

        fd = tty.fileno()
        self._rfds.append(fd)
        self._xfds.append(fd)
        self._ttymap[fd] = process

        process.start(termenc,
                      inputhandler,
                      outputhandler,
                      DefaultParser(),
                      DefaultParser(),
                      listener)

        self._input_target = tty
        return tty

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
                self._inputparser.reset()
                self._inputcontext.dispatch_char(0x1b)
                self._inputhandler.handle_draw(self._outputcontext)
                self._outputhandler.handle_draw(self._outputcontext)
                #self._inputcontext.flush()
                self._outputcontext.flush()
            self._esc_timer = threading.Timer(_ESC_TIMEOUT, dispatch_esc)
            self._esc_timer.start()

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

    def process_output(self, data):
        self._outputparser.parse(data)
        self._inputhandler.handle_draw(self._outputcontext)
        self._outputhandler.handle_draw(self._outputcontext)
        #self._inputcontext.flush()
        self._outputcontext.flush()

    def process_resize(self, row, col):
        try:
            self._inputhandler.handle_resize(self._inputcontext, row, col)
            self._outputhandler.handle_resize(self._outputcontext, row, col)
        finally:
            self._resized = False

    def focus_subprocess(self, tty):
        self._input_target = tty

    def blur_subprocess(self, tty):
        self._input_target = self.tty

    def destruct_subprocesses(self):
        for fd in self._ttymap:
            self.destruct_subprocess(fd)

    def destruct_subprocess(self, fd):
        if fd in self._ttymap:
            self._input_target = self.tty
            if fd in self._rfds:
                self._rfds.remove(fd)
            if fd in self._xfds:
                self._xfds.remove(fd)
            process = self._ttymap[fd]
            process.end()
            process.close()
            del self._ttymap[fd]
            self.process_output("")

    def drive(self):

        def onresize(no, frame):
            ''' handle resize '''
            self._resized = True
        try:
            signal.signal(signal.SIGWINCH, onresize)
        except ValueError:
            pass

        main_master = self.tty.fileno()
        stdin_fileno = self.tty.stdin_fileno()
        try:
            while self._alive:

                try:
                    rfds = self._rfds
                    wfds = self._wfds
                    xfds = self._xfds
                    rfd, wfd, xfd = select.select(rfds, wfds, xfds)
                    if xfd:
                        for fd in xfd:
                            if fd == main_master:
                                return
                            elif fd == stdin_fileno:
                                return
                            else:
                                if fd in self._ttymap:
                                    self.destruct_subprocess(fd)
                                    continue
                                else:
                                    return
                    if self._resized:
                        self._resized = False
                        row, col = self.tty.fitsize()
                        self.process_resize(row, col)
                    for fd in rfd:
                        if fd == main_master:
                            data = self.tty.read()
                            self.process_output(data)
                        elif fd == stdin_fileno:
                            data = os.read(stdin_fileno, _BUFFER_SIZE)
                            if self._input_target == self.tty:
                                self.process_input(data)
                            else:
                                target_fd = self._input_target.fileno()
                                process = self._ttymap[target_fd]
                                process.on_write(data)
                                self.process_input("")
                        elif self._ttymap:
                            target_fd = self._input_target.fileno()
                            process = self._ttymap[target_fd]
                            process.on_read(fd)
                            self.process_output("")
                except select.error, e:
                    no, msg = e
                    self._input_target = self.tty
                    if no == errno.EINTR:
                        # The call was interrupted by a signal
                        self._resized = True
                    elif no == errno.EBADF:
                        for fd in self._ttymap:
                            self.destruct_subprocess(fd)
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
                self.process_end()
            finally:
                self.tty.close()
                self._input_target = self.tty
                for fd in self._ttymap:
                    process = self._ttymap[fd]
                    process.end()
                    process.close()
                self.ttymap = {}

    def start(self,
              termenc,
              stdin=sys.stdin,
              stdout=sys.stdout,
              inputscanner=DefaultScanner(),
              inputparser=DefaultParser(),
              inputhandler=DefaultHandler(),
              outputscanner=DefaultScanner(),
              outputparser=OutputParser(),
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
        inputparser.init(inputcontext)
        outputparser.init(outputcontext)

        self._resized = False

        def onclose(no, frame):
            pid, status = os.wait()
            if pid == self.tty.pid:
                self._alive = False
            self._input_target = self.tty

        signal.signal(signal.SIGCHLD, onclose)

        self._inputhandler = inputhandler
        self._outputhandler = outputhandler
        self._inputcontext = inputcontext
        self._outputcontext = outputcontext
        self._inputparser = inputparser
        self._outputparser = outputparser

        self._esc_timer = None
        self.drive()


def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':
    _test()
