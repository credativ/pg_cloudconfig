#!/usr/bin/env python3
from setuptools import find_packages, setup

setup(
    name='pg_cloudconifg',
    version='0.2',
    license='GPL3',
    author='Alexander Sosna',
    author_email='alexander.sosna@credativ.de',
    description='Tool to set optimized defaults for PostgreSQL in virtual environments.',
    # long_description=readme,
    packages=find_packages(exclude=('tests','doc',)),
    zip_safe=False,
    platforms='any',
    install_requires=[
        'datetime',
        'pint',
    ],
    entry_points={
        'console_scripts': [
            'pg_cloudconfig = pg_cloudconfig.command:main',
        ],
    },
)