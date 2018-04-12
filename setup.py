#!/usr/bin/env python3

from __future__ import absolute_import
import os
from setuptools import setup, find_packages

# Load the README as lonng_description.
# Use pypandoc (if available) to convert MD to RST.
here = os.path.abspath(os.path.dirname(__file__))

try:
    import pypandoc
    long_description = pypandoc.convert("README.md", "rst")

except ImportError:

    with open(os.path.join(here, 'README.md')) as f:
        long_description = f.read()

# Dependencies for the package, once installed.
REQUIREMENTS = [
    'python-dateutil',
    'pycrypto',
    'six'
]

setup(
    name='quasselgrep',

    version='0.1',

    description='quasselgrep',

    long_description=long_description,

    author='Chris Le Sueur',

    author_email='',

    url='https://github.com/fish-face/quasselgrep',

    license="GPLv2",

    install_requires=REQUIREMENTS,

    keywords=['quassel', 'quasselgrep', 'irc', 'logs'],

    packages=find_packages(),

    # See https://pypi.python3.org/pypi?%3Aaction=list_classifiers for others
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    ],

    # Entry points; setuptools will generate scripts that invoke the listed functions.
    entry_points={
        'console_scripts': ['quasselgrep = quasselgrep.quasselgrep:main']
    },
)
