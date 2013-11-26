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

    #def handle_invalid(self, context, seq):
    #    return False

    def handle_resize(self, context, row, col):
        raise NotImplementedError("EventObserver::handle_resize")


class Scanner:
    ''' forward input iterator '''

    def __iter__(self):
        raise NotImplementedError("Scanner::__iter__")

    def assign(self, value, termenc):
        raise NotImplementedError("Scanner::assign")


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
