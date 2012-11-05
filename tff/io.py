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

import os, termios, pty, signal, fcntl, struct, select, errno
import codecs
try:
    from cStringIO import StringIO
except:
    try:
        from StringIO import StringIO
    except:
        from io import StringIO

from interface import * # terminal filter framework interface

BUFFER_SIZE=2048

################################################################################
#
# Scanner implementation
#
class DefaultScanner(Scanner):
    ''' scan input stream and iterate characters '''
    __data = None

    def assign(self, value, termenc):
        self.__data = unicode(value, termenc, 'ignore')

    def __iter__(self):
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
STATE_GROUND = 0
STATE_ESC = 1
STATE_ESC_FINAL = 2

STATE_CSI_PARAMETER = 3
STATE_CSI_INTERMEDIATE = 4
STATE_CSI_FINAL = 5

STATE_OSC = 6
STATE_STR = 7 

class DefaultParser(Parser):
    ''' parse ESC/CSI/string seqneces '''

    def __init__(self):
        self.__parse_state = STATE_GROUND
        self.__csi_parameter = [] 
        self.__csi_intermediate = [] 
        self.__esc_prefix = [] 
        self.__str = [] 
        self.__str_prefix = None 
        self.__str_esc_state = False

    def parse(self, context):
        for c in context:
            if self.__parse_state == STATE_OSC:
                # parse control string
                if c == 0x1b:
                    self.__str_esc_state = True
                elif c == 0x5c and self.__str_esc_state == True:
                    context.dispatch_control_string(self.__str_prefix, self.__str)
                    self.__parse_state = STATE_GROUND
                elif c == 0x07:
                    context.dispatch_control_string(self.__str_prefix, self.__str)
                    self.__parse_state = STATE_GROUND
                elif c < 0x20:
                    self.__parse_state = STATE_GROUND
                else:
                    self.__str.append(c)

            elif self.__parse_state == STATE_STR:
                # parse control string
                if c == 0x1b:
                    self.__str_esc_state = True
                elif c == 0x5c and self.__str_esc_state == True:
                    context.dispatch_control_string(self.__str_prefix, self.__str)
                    self.__parse_state = STATE_GROUND
                elif c < 0x20:
                    self.__parse_state = STATE_GROUND
                else:
                    self.__str.append(c)

            elif c == 0x1b: # ESC
                self.__esc_prefix = []
                self.__parse_state = STATE_ESC

            elif c < 0x20 or c == 0x7f: # control character
                context.dispatch_char(c)
                self.__parse_state = STATE_GROUND

            elif self.__parse_state == STATE_ESC:
                if c == 0x5b: # [
                    self.__csi_parameter = []
                    self.__csi_intermediate = [] 
                    self.__parse_state = STATE_CSI_PARAMETER
                elif c == 0x5d: # ]
                    self.__str_esc_state = False
                    self.__str = [] 
                    self.__str_prefix = c 
                    self.__parse_state = STATE_OSC
                elif c == 0x50 or c == 0x58 or c == 0x5e or c == 0x5f:
                    # P(DCS) or X(SOS) or ^(PM) or _(APC)
                    self.__str_esc_state = False
                    self.__str = []
                    self.__str_prefix = c 
                    self.__parse_state = STATE_STR
                elif 0x20 <= c and c <= 0x2f: # SP to /
                    self.__esc_prefix.append(c)
                    self.__parse_state = STATE_ESC_FINAL
                else:
                    context.dispatch_esc(self.__esc_prefix, c)
                    self.__parse_state = STATE_GROUND

            elif self.__parse_state == STATE_ESC_FINAL:
                context.dispatch_esc(self.__esc_prefix, c)
                self.__parse_state = STATE_GROUND

            elif self.__parse_state == STATE_CSI_PARAMETER:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #     ^
                if 0x30 <= c and c <= 0x3f: # parameter, 0 to ?
                    self.__csi_parameter.append(c)
                elif 0x20 <= c and c <= 0x2f: # intermediate, SP to /
                    self.__csi_intermediate.append(c)
                    self.__parse_state = STATE_CSI_INTERMEDIATE
                elif 0x40 <= c and c <= 0x7e: # Final byte, @ to ~
                    context.dispatch_csi(self.__csi_parameter,
                                         self.__csi_intermediate,
                                         c)
                    self.__parse_state = STATE_GROUND
                else:
                    self.__parse_state = STATE_GROUND

            elif self.__parse_state == STATE_CSI_INTERMEDIATE:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #             ^
                if 0x20 <= c and c <= 0x2f: # intermediate, SP to /
                    self.__csi_intermediate.append(c)
                    self.__parse_state = STATE_CSI_INTERMEDIATE
                elif 0x40 <= c and c <= 0x7e: # Final byte, @ to ~
                    context.dispatch_csi(self.__csi_parameter,
                                         self.__csi_intermediate,
                                         c)
                    self.__parse_state = STATE_GROUND
                else:
                    self.__parse_state = STATE_GROUND

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
    def handle_csi(self, context, parameter, intermediate, final):
        context.write(0x1b) # ESC
        context.write(0x5b) # [
        for c in parameter:
            context.write(c)
        for c in intermediate:
            context.write(c)
        context.write(final)

    def handle_esc(self, context, prefix, final):
        context.write(0x1b) # ESC
        for c in prefix:
            context.write(c)
        context.write(final)

    def handle_control_string(self, context, prefix, value):
        context.write(0x1b) # ESC
        context.write(prefix)
        for c in value:
            context.write(c)
        context.write(0x1b) # ESC
        context.write(0x5c) # \

    def handle_char(self, context, c):
        if c < 0x20 or c == 0x7f:
            context.write(c)
        else: 
            context.write(c)


################################################################################
#
# Dispatcher implementation
#
class ParseContext(OutputStream, EventDispatcher):

    def __init__(self,
                 termenc = 'UTF-8',
                 scanner = DefaultScanner(),
                 handler = DefaultHandler()):
        self.__termenc = termenc
        self.__scanner = scanner 
        self.__handler = handler
        self.__output = codecs.getwriter(termenc)(StringIO())

    def __iter__(self):
        return self.__scanner.__iter__()

    def writestring(self, data):
        self.__output.write(data)

    def assign(self, data):
        self.__scanner.assign(data, self.__termenc)
        self.__output.truncate(0)

# OutputStream
    def write(self, c):
        if c < 0x80:
            self.__output.write(chr(c))
        else:
            try:
                self.__output.write(unichr(c))
            except:
                self.__output.write('?')

    def getvalue(self):
        return self.__output.getvalue()

# EventDispatcher
    def dispatch_esc(self, prefix, final):
        self.__handler.handle_esc(self, prefix, final)

    def dispatch_csi(self, parameter, intermediate, final):
        self.__handler.handle_csi(self, parameter, intermediate, final)

    def dispatch_control_string(self, prefix, value):
        self.__handler.handle_control_string(self, prefix, value)

    def dispatch_char(self, c):
        self.__handler.handle_char(self, c)

################################################################################
#
# Settings
#
class Settings:

    def __init__(self,
                 command,
                 term,
                 lang,
                 termenc,
                 stdin,
                 stdout,
                 inputscanner=DefaultScanner(),
                 inputparser=DefaultParser(),
                 inputhandler=DefaultHandler(),
                 outputscanner=DefaultScanner(),
                 outputparser=DefaultParser(),
                 outputhandler=DefaultHandler()):
        self.command = command
        self.term = term
        self.lang = lang
        self.termenc = termenc
        self.stdin = stdin
        self.stdout = stdout
        self.inputscanner = inputscanner
        self.inputparser = inputparser
        self.inputhandler = inputhandler
        self.outputscanner = outputscanner
        self.outputparser = outputparser
        self.outputhandler = outputhandler

################################################################################
#
# DefaultPTY
#
class DefaultPTY(PTY):

    __stdin_fileno = None
    __backup = None
    __master = None

    def __init__(self, settings):
        self.__stdin_fileno = settings.stdin.fileno()
        self.__backup = termios.tcgetattr(self.__stdin_fileno)
        new = termios.tcgetattr(self.__stdin_fileno)
        new[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK 
                  | termios.ISTRIP | termios.INLCR | termios. IGNCR 
                  | termios.ICRNL | termios.IXON)
        new[3] = new[3] &~ (termios.ECHO | termios.ICANON)

        vdisable = os.fpathconf(self.__stdin_fileno, 'PC_VDISABLE')

        new[6][termios.VINTR] = vdisable     # Ctrl-C
        new[6][termios.VREPRINT] = vdisable  # Ctrl-R
        new[6][termios.VSTART] = vdisable    # Ctrl-Q
        new[6][termios.VSTOP] = vdisable     # Ctrl-S
        new[6][termios.VLNEXT] = vdisable    # Ctrl-V
        new[6][termios.VWERASE] = vdisable   # Ctrl-W
        new[6][termios.VKILL] = vdisable     # Ctrl-X
        new[6][termios.VSUSP] = vdisable     # Ctrl-Z
        new[6][termios.VQUIT] = vdisable     # Ctrl-\

        termios.tcsetattr(self.__stdin_fileno, termios.TCSANOW, new)
        pid, master = pty.fork()
        if not pid:
            os.environ['TERM'] = settings.term 
            os.environ['LANG'] = settings.lang 
            os.execlp('/bin/sh',
                      '/bin/sh', '-c',
                      'cd $HOME && exec %s' % settings.command)

        self.__pid = pid
        self.__master = master
        signal.signal(signal.SIGWINCH, lambda no, frame: self.fitsize())
    
        # call resize once
        self.fitsize()
 
    def __del__(self):
        termios.tcsetattr(self.__stdin_fileno, termios.TCSANOW, self.__backup)

    def fitsize(self):
         winsize = fcntl.ioctl(self.__stdin_fileno, termios.TIOCGWINSZ, 'hhhh')
         height, width = struct.unpack('hh', winsize)
         self.resize(height, width)

    def resize(self, height, width):
         winsize = struct.pack('HHHH', height, width, 0, 0)
         fcntl.ioctl(self.__master, termios.TIOCSWINSZ, winsize)
         # notify Application process that terminal size has been changed.
         os.kill(self.__pid, signal.SIGWINCH)
         return height, width

    def read(self):
        return os.read(self.__master, BUFFER_SIZE)

    def write(self, data):
        os.write(self.__master, data)

    def drive(self):
        master = self.__master
        stdin_fileno = self.__stdin_fileno
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
                                yield data, None
                        elif fd == master:
                            data = self.read()
                            if data:
                                yield None, data
                except OSError, e:
                    no, msg = e
                    if no == errno.EIO:
                        return
                except select.error, e:
                    no, msg = e
                    if no == errno.EINTR:
                        pass
                    else:
                        raise
        finally:
            os.close(master)

 
################################################################################
#
# Session
#
class Session:

    def start(self, settings):

        tty = DefaultPTY(settings)

        input_context = ParseContext(termenc=settings.termenc,
                                     scanner=settings.inputscanner,
                                     handler=settings.inputhandler)
        input_parser = settings.inputparser 

        output_context = ParseContext(termenc=settings.termenc,
                                      scanner=settings.outputscanner,
                                      handler=settings.outputhandler)
        output_parser = settings.outputparser

        stdout = settings.stdout
        for idata, odata in tty.drive():
            if idata:
                input_context.assign(idata)
                input_parser.parse(input_context)
                tty.write(input_context.getvalue())
            if odata:
                output_context.assign(odata)
                output_parser.parse(output_context)
                stdout.write(output_context.getvalue())
                stdout.flush()


''' main '''
if __name__ == '__main__':    
    pass

