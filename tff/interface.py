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
