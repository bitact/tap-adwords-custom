#!/usr/bin/env python

from setuptools import setup

setup(name='tap-adwords',
        version="1.12.0",
        description='Singer.io tap for extracting data from the Adwords api',
        author='Stitch',
        url='http://singer.io',
        classifiers=['Programming Language :: Python :: 3 :: Only'],
        py_modules=['tap_adwords'],
        install_requires=[
        'singer-python==5.9.0',
        'requests==2.22.0',
        'googleads==17.0.0',
        'pytz==2018.4',
        'zeep==3.1.0', # googleads dependency, pinned to 3.1.0 (tested version)
        ],
        extras_require={
            'dev': [
                'ipdb==0.11',
                'pylint'
            ]
        },
        entry_points='''
            [console_scripts]
            tap-adwords=tap_adwords:main
        ''',
        packages=['tap_adwords']
)