#!/usr/bin/env python3
from setuptools import find_packages, setup

setup(
    name='pg_cloudconfig',
    version='0.4',
    license='GPL3',
    author='Alexander Sosna',
    author_email='alexander.sosna@credativ.de',
    description='Tool to set optimized defaults for PostgreSQL in virtual environments.',
    keywords = "postgres postgresql tune tuning cloud",
    url = "https://github.com/credativ/pg_cloudconfig",
    packages=find_packages(exclude=('tests','doc',)),
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
            'pg_cloudconfig = pg_cloudconfig.command:main',
        ],
    },
)
