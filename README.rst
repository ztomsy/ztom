::

ZTOM is the Python SDK for implementing the Trade Order Management System for crypto exchanges.

It's build upon the CCXT library and aims to provide the boilerplate for developing fail-safe applications and
trading algorithms.

Could be used for Algo and HF Trading for prototyping and even production.

Features:

- Customizable exchange REST API wrapper
- Request Throttling control
- Order Book depth calculation
- Order's Management
- Configuration (config files, cli)
- Logging, Reporting

Installation
=============

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt 
python3 -m pip install -e .


Running the tests: python3 -m unittest -v -b


Usage:
=============
tbd


Project structure have been taken from  `<http://www.kennethreitz.org/essays/repository-structure-and-python>`_.
If you want to learn more about ``setup.py`` files, check out `this repository <https://github.com/kennethreitz/setup.py>`_.