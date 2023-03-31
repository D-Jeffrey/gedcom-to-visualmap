#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='gedcom-to-visualmap',
    version='0.2.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'gedcom-to-visualmap=gedcom_to_visualmap.main:main',
            'gedcom-visual-gui=gedcom_to_map.gedcomVisualGUI:main'
        ]
    },
    install_requires=[
        'Pillow>=8.2.0',
        'networkx>=2.5',
        'gedcompy>=0.3.2',
        'pycairo>=1.20.1'
    ],
    author='D-Jeffrey',
    description='A Python package to convert GEDCOM files to visual maps',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)

