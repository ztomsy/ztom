.. automodule:: ztom.ccxtExchangeWrapper


ccxtExchangeWrapper
===================

Encapsulates the data and methods, provided by CCXT library and eliminates differences between various exchanges via
separate wrappers. Also this class provides offline testing and back-testing capabilities.

.. important:: About wrapping
   ccxtExcahngeWrapper should be treated as main point of implementation of differences between exchanges, so the
   other ZTOM modules could not care about exchanges differences!

Wrapping Approach
-----------------
In ZTOM wrapped ccxt methods provide the following capabilities:

- online communication with the exchange in some generic ccxt format. This also includes work with orders.
- offline "live" emulation of exchange requesting via json and csv files or directly via code in app.
  Live means that data requested consecutively could be different just like from the real exchange.
- customisation of input/output data for every single exchange via separate wrapping classes

Wrapped methods:

- tickers fetching
- market fetching
- balance fetching
- orders placement
- orders updates
- orders cancellation
- user's trades fetching


Supported Exchanges
-------------------
1. Binance - fully supported
2. Kucoin - should be revised, however could be used as illustration of implementing the differences between exchanges


Quick Start
-----------


dasd fsad fasd

