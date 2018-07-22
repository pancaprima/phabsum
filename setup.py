# encoding: utf-8

from setuptools import setup, find_packages, Command
import sys, os, re, ast

setup(
    name='phabsum',
    version='0.0.2',
    description="Phabricator Summarizer by Prima",
    long_description="""I hate manual""",
    classifiers=[
        "Programming Language :: Python :: 2.7",
    ],
    keywords='',
    author='Fernanda Panca Prima',
    author_email='pancaprima8@.com',
    url='',
    license='',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=["gspread","oauth2client"],
    entry_points={
        'console_scripts': [
            'phabsum = phabsum.main:main',
        ]
    },
)
