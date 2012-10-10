#!/usr/bin/env python

from setuptools import setup, find_packages

from ripestat import VERSION


setup(name='ripestat-text',
      version=VERSION,
      description='Text mode utils for RIPEstat',
      author_email='stat@ripe.net',
      url='https://stat.ripe.net/cli/',
      packages=find_packages(),
      scripts=["scripts/ripestat", "scripts/ripestat-whois-server"]
     )
