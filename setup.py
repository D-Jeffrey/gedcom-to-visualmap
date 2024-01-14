#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name='gedcom-to-visualmap',
    version='0.2.4.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'gedcom-to-visualmap=gedcom_to_visualmap.main:main',
            'gedcom-visual-gui=gedcom_to_map.gedcomVisualGUI:main'
        ]
    },
    install_requires=[
        'ged4py>=0.4.4',
        'simplekml>=1.3.6',
        'geopy>=2.3.0',
        'folium>=0.14.0',
        'wxPython>=4.1.0',
        
    ],
    author='D-Jeffrey',
    description='A Python package to convert GEDCOM files to visual maps',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)
