TFF - Terminal Filter Framework
===============================

This module provides basic interfaces for terminal I/O filter applications,
and exports some default implementations such as Scanner, Parser ...etc.

Install
-------

via github ::

    $ git clone https://github.com/saitoha/tff.git
    $ cd tff
    $ python setup.py install

or via pip ::

    $ pip install tff


Requirements
------------
Python 2.6/2.7 unix/linux version


Exported Interfaces
-------------------

Following interfaces are exported from tff/interface.py

- tff.EventObserver

    adapt to event driven ECMA-35/48 parser model

- tff.OutputStream:

    Abstructed TTY output stream 

- tff.EventDispatcher

    Dispatch interface of terminal sequence event oriented parser

- tff.Parser:

    Abstruct event driven Parser. dispatch parser event to event dispatcher

- tff.PTY:

    Abstructed PTY device


License
----------
MIT License


Dependents
----------

 - canossa 
   https://github.com/saitoha/canossa

 - sentimental-skk
   https://github.com/saitoha/sentimental-skk

 - drcsterm 
   https://github.com/saitoha/drcsterm

 - sixelterm 
   https://github.com/saitoha/sixelterm

 - jacot 
   https://github.com/saitoha/jacot

