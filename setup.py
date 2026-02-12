#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name='gedcom-to-visualmap',
    version='0.2.5.5',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'gedcom-to-visualmap=gedcom_to_map.gv.main:main',
            'gedcom-visual-gui=gedcom_to_map.gv.main:main',
            'gv=gedcom_to_map.gv.main:main',
        ]
    },
    install_requires=[
        'ged4py>=0.4.4',
        'simplekml>=1.3.6',
        'geopy>=2.3.0',
        'folium>=0.16.0',
        'branca>=0.7.0',
        'wxPython>=4.1.0',
        'selenium>=4.0.0',
        'xyzservices>=2025.1.0',
        'pyyaml>=6.0',
        'rapidfuzz>=3.0.0',
        'pycountry>=22.3.5',
        'pycountry-convert>=0.7.2',
        'pandas>=2.0.0',
        'seaborn>=0.12.0',
        'matplotlib>=3.7.0',
        'pytest>=7.0.0',
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
