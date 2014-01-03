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

