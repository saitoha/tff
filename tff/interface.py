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

import abc


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

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def handle_start(self, context):
        pass

    @abc.abstractmethod
    def handle_end(self, context):
        pass

    @abc.abstractmethod
    def handle_csi(self, context, params, intermediate, final):
        pass

    @abc.abstractmethod
    def handle_esc(self, context, prefix, final):
        pass

    @abc.abstractmethod
    def handle_control_string(self, context, prefix, value):
        pass

    @abc.abstractmethod
    def handle_char(self, context, c):
        pass

    @abc.abstractmethod
    def handle_draw(self, context):
        pass

    #@abc.abstractmethod
    #def handle_invalid(self, context, seq):
    #    return False

    @abc.abstractmethod
    def handle_resize(self, context, row, col):
        pass


class Scanner:
    ''' forward input iterator '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __iter__(self):
        yield

    @abc.abstractmethod
    def assign(self, value, termenc):
        yield


class OutputStream:
    ''' abstruct TTY output stream '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def write(self, c):
        pass

    @abc.abstractmethod
    def flush(self):
        pass


class EventDispatcher:
    ''' Dispatch interface of terminal sequence event oriented parser '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def dispatch_esc(self, prefix, final):
        pass

    @abc.abstractmethod
    def dispatch_csi(self, prefix, params, final):
        pass

    @abc.abstractmethod
    def dispatch_control_string(self, prefix, value):
        pass

    @abc.abstractmethod
    def dispatch_char(self, c):
        pass


class Parser:
    ''' abstruct Parser '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def parse(self, context):
        pass


class PTY:
    ''' abstruct PTY device '''

    @abc.abstractmethod
    def fitsize(self):
        pass

    @abc.abstractmethod
    def resize(self, height, width):
        pass

    @abc.abstractmethod
    def read(self):
        pass

    @abc.abstractmethod
    def write(self, data):
        pass

    @abc.abstractmethod
    def xon(self):
        pass

    @abc.abstractmethod
    def xoff(self):
        pass

    @abc.abstractmethod
    def drive(self):
        pass
