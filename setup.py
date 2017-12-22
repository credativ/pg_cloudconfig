#!/usr/bin/env python3
import codecs
import os
import re
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='pg_cloudconfig',
    version=find_version("pg_cloudconfig", "pg_cloudconfig.py"),
    license='GPL3',
    author='Alexander Sosna',
    author_email='alexander.sosna@credativ.de',
    description=
    'Tool to set optimized defaults for PostgreSQL in virtual environments.',
    keywords="postgres postgresql tune tuning cloud",
    url="https://github.com/credativ/pg_cloudconfig",
    packages=find_packages(exclude=(
        'tests',
        'doc',
    )),
    zip_safe=True,
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3'
    ],
    install_requires=[
        'pint',
    ],
    entry_points={
        'console_scripts': [
            'pg_cloudconfig = pg_cloudconfig.pg_cloudconfig:main',
        ],
    },
)
