#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='gedcomtomap',
    version='0.0.2',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)