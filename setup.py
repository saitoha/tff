# -*- coding: utf-8 -*-

from setuptools import setup, find_packages, Extension
from tff import __version__, __license__, __author__, __doc__

import inspect, os

filename = inspect.getfile(inspect.currentframe())
dirpath = os.path.abspath(os.path.dirname(filename))

setup(name                  = 'tff',
      version               = __version__,
      description           = 'Terminal Filter Framework',
      long_description      = open(dirpath + "/README.rst").read(),
      py_modules            = ['tff'],
      ext_modules           = [Extension('ctff', sources = ['ctff.c'])],
      eager_resources       = [],
      classifiers           = ['Development Status :: 4 - Beta',
                               'Topic :: Terminals',
                               'Environment :: Console',
                               'Intended Audience :: Developers',
                               'License :: OSI Approved :: MIT License',
                               'Programming Language :: Python'
                               ],
      keywords              = 'terminal filter',
      author                = __author__,
      author_email          = 'user@zuse.jp',
      url                   = 'https://github.com/saitoha/tff',
      license               = __license__,
      packages              = find_packages(exclude=['test']),
      zip_safe              = False,
      include_package_data  = False,
      install_requires      = [],
      )

