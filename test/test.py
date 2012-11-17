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

import sys, os

current = os.path.abspath(os.path.dirname(__file__))
parent = os.path.join(current, '..')
sys.path.insert(0, parent)

import tff

#settings = tff.Settings(command=os.path.join(current, 'test1.py'),
#                        term='xterm',
#                        lang='en_JS.UTF-8',
#                        termenc='UTF-8',
#                        stdin=sys.stdin,
#                        stdout=sys.stdout,
#                        inputscanner=tff.DefaultScanner(),
#                        inputparser=tff.DefaultParser(),
#                        inputhandler=tff.DefaultHandler(),
#                        outputscanner=tff.DefaultScanner(),
#                        outputparser=tff.DefaultParser(),
#                        outputhandler=tff.DefaultHandler())
#session = tff.Session()
#session.start(settings)

print "ok"

