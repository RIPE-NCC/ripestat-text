#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='ripestat-text',
      version='0.1',
      description='Text mode utils for RIPEstat',
      author_email='stat@ripe.net',
      url='https://stat.ripe.net/cli/',
      packages=find_packages(),
      scripts=["scripts/ripestat", "scripts/ripestat-whois-server"]
     )
