#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


install_requires = [
    'pytest>=3.0.0',
    'pytest-exceptional>=0.1.1',
    'pysipp',
]


try:
    from shutil import which  # noqa
except ImportError:
    install_requires.append('backports.shutil_which')


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='pytest-sipp',
    version='0.1.0',
    author='Simon Gomizelj',
    author_email='simon@vodik.xyz',
    maintainer='Simon Gomizelj',
    maintainer_email='simon@vodik.xyz',
    license='GNU GPL v3.0',
    url='https://github.com/vodik/pytest-sipp',
    description='A small plugin to automate sipp tests with pytest',
    long_description=read('README.rst'),
    py_modules=['pytest_sipp'],
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],
    entry_points={
        'pytest11': [
            'sipp = pytest_sipp',
        ],
    },
)
