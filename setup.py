#!/usr/bin/env python

from setuptools import setup, find_packages

from ripestat import __version__


setup(name='ripestat-text',
      version=__version__,
      description='Text mode utils for RIPEstat',
      author_email='stat@ripe.net',
      url='https://github.com/RIPE-NCC/ripestat-text',
      packages=find_packages(),
      scripts=["scripts/ripestat", "scripts/ripestat-text-server"]
     )
