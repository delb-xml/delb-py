#!/usr/bin/env python

# for now this file exists solely to run on ReadTheDocs

from setuptools import setup


VERSION = "0.1a1"

setup(
    name="lxml-domesque",
    version=VERSION,
    packages=["lxml_domesque"],
    install_requires=["cssselect", "lxml"],
)
