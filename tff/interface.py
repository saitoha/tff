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
        pass

    def handle_end(self, context):
        pass

    def handle_csi(self, context, params, intermediate, final):
        pass

    def handle_esc(self, context, prefix, final):
        pass

    def handle_control_string(self, context, prefix, value):
        pass

    def handle_char(self, context, c):
        pass

    def handle_draw(self, context):
        pass

    #def handle_invalid(self, context, seq):
    #    return False

    def handle_resize(self, context, row, col):
        pass


class Scanner:
    ''' forward input iterator '''

    def __iter__(self):
        yield

    def assign(self, value, termenc):
        yield


class OutputStream:
    ''' abstruct TTY output stream '''

    def write(self, c):
        pass

    def flush(self):
        pass


class EventDispatcher:
    ''' Dispatch interface of terminal sequence event oriented parser '''

    def dispatch_esc(self, prefix, final):
        pass

    def dispatch_csi(self, prefix, params, final):
        pass

    def dispatch_control_string(self, prefix, value):
        pass

    def dispatch_char(self, c):
        pass


class Parser:
    ''' abstruct Parser '''

    def parse(self, context):
        pass


class PTY:
    ''' abstruct PTY device '''

    def fitsize(self):
        pass

    def resize(self, height, width):
        pass

    def read(self):
        pass

    def write(self, data):
        pass

    def xon(self):
        pass

    def xoff(self):
        pass

    def drive(self):
        pass
