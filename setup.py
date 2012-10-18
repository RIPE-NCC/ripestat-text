#!/usr/bin/env python

from setuptools import setup, find_packages

from ripestat import VERSION


setup(name='ripestat-text',
      version=VERSION,
      description='Text mode utils for RIPEstat',
      author_email='stat@ripe.net',
      url='https://github.com/RIPE-NCC/ripestat-text',
      packages=find_packages(),
      scripts=["scripts/ripestat", "scripts/ripestat-whois-server"]
     )
