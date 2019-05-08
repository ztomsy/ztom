ZTOM
=====

ZTOM is the Python SDK for implementing the Trade Order Management System for crypto exchanges.

It's build upon the `CCXT <https://github.com/ccxt/ccxt>`__ library and simplifies the development of fail-safe applications and trading algorithms by providing tools for managing the trade orders execution and control.

With ZTOM it's possible to create, maintain and cancel trade orders using different triggers and conditions apart from the implementation of exchange's communication API. 

Could be used for Algorithmic (algo) and High Frequency Trading (hft) for prototyping and production.

**Main Features:**

* Customizable exchange REST API wrapper
* Request throttling control
* Order Book depth calculation
* Order's Management
* Configuration (config files, cli)
* Logging, Reporting
* Errors management
* Offline testing:
  * Back testing with prepared marked data 
  * Order execution emulation

Code Example
---------------------


.. code-block:: python

    import time
    import ztom as zt
    
    ex = zt.ccxtExchangeWrapper.load_from_id("binance")
    ex.enable_requests_throttle(60, 1200) # 1200 requests per minute for binance
    
    # just checking in offline mode
    ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
    
    tickers = ex.fetch_tickers()
    
    # sleep to maintain requests rate
    time.sleep(ex.requests_throttle.sleep_time()) 
    
    # below orders object are being created - not actual orders
    order1 = zt.ActionOrder.create_from_start_amount(symbol="BTC/USDT",
                                                start_currency="BTC",
                                                amount_start=1,
                                                dest_currency="USDT",
                                                price=tickers["BTC/USDT"]["ask"])
    
    order2 = zt.ActionOrder.create_from_start_amount("USD/RUB", "USD", 1, 
                                                     "RUB", 70)
    # new OrderManager object
    om = zt.ActionOrderManager(ex)
    
    # adding orders to OM
    # they will not be committed to exchange at this point
    om.add_order(order1)
    om.add_order(order2)
    
    i = 0
    
    while len(om.get_open_orders()) > 0:
    	
      # check if order manager has something to do like create or cancel order  
      # and if yes we will not wait for it 
      if om.pending_actions_number() == 0:
            sleep_time = ex.requests_throttle.sleep_time()
            print("Sleeping for {}s".format(sleep_time))
            time.sleep(sleep_time)
      else:
          print("!!! NO SLEEP. ACTIONS ARE PENDING !!!")
    
     	# here all transaction are committed with the error handling and etc
       om.proceed_orders()
        
       # just to demonstrate how to cancel the order 
       # - operation will be committed on om.proceed_orders()
        if i == 5 and not order.filled > 0 :
          order1.force_close()
    
        i += 1
    
    print(order1.filled)
    print(order2.filled)
    
Tested Exchanges
----------------
Binance

Components and Features Overview
--------------------------------

.. list-table::
   :widths: 50 50
   :header-rows:  1
   
   * - Components
     - Features  
   * - :doc:`exchange_wrapper`
     - communication to exchange via the ccxt offline exchange connection emulation
   * - :doc:`action_order` 
     - implements ""smart"" orders which could perform some actions (creation and cancellation of orders) in dependence
       from the data provided by order manager or application"



Installation
------------

(the installation from pypi will be implemented soon)

**Requirements:**  python3.6+ and some libs

1. Clone the repo:
      .. code-block::

        git clone https://github.com/ztomsy/ztom.git
2. Install the dependencies:
    .. code-block::

        pip3 install -r requirements.txt

3. Install the ztom lib
    .. code-block::

       pip3 install -e .

4. Run some tests:
    .. code-block::

       python3 -m unittest -v -b

License
-------

This project is licensed under the  :doc:`MIT License <LICENSE>` file for details


