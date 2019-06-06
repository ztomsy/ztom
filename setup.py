# -*- coding: utf-8 -*-
# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='ztom',
    version='0.1.0',
    description='HFT and Algo trading package on top of ccxt',
    long_description=readme,
    author='Ivan Averin',
    author_email='i.averin@gmail.com',
    url='https://github.com/ztomsy/ztom',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)

