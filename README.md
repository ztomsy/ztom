# ZTOM

ZTOM is the Python SDK for implementing the Trade Order Management System for crypto exchanges.

It's build upon the [CCXT ](https://github.com/ccxt/ccxt)library and simplifies the development of fail-safe applications and trading algorithms by providing tools for managing the trade orders execution and some supplementary tools for configuration, flow control, reporting and etc.

With ZTOM it's possible to create, maintain and cancel trade orders using different triggers and conditions apart from the implementation of exchange's communication API. 

Could be used for Algorithmic (algo) and High Frequency Trading (hft) for prototyping and production.



**Main Features:**

* Customizable exchanges REST API wrapper
* Request throttling control
* Order Book depth calculation
* Order's Management
* Configuration (config files, cli)
* Logging, Reporting
* Errors management
* Offline testing:
  * Back testing with prepared marked data 
  * Order execution emulation



# Why it was created

ZTOM was created because of 2 main reasons:

First one is to fail-safe proceeding with the common exchange API use cases like working with orders,  exceptions handling so it could be possible to focus on trading algorithms rather than overcoming all the tech things.   

This allows to create simple and clean "syntax" framework for order management and flow control so it could be possible easily read the code and understand the implemented algorithm as good as increase the speed of development and leverage on rich Python's analytical abilities. 

The second big thing in mind was the implementation of the offline mode for both market data gathering and order execution using the same code as for online trading.  This allows more quickly develop the algos, emulate different cases and as a result launch actual live tests more quickly.  



# Code Example

The order management could be something like this: 

```python
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
```



# Tested Exchanges

Binance



# Components and Features

| **Components**                             | **Features**                                                 |
| ------------------------------------------ | ------------------------------------------------------------ |
| **Core**                                   | **most used for creation apps and algos**                    |
| `ccxtExchangeWrapper`                      | communication to exchange via the ccxt offline exchange connection emulation |
| `action_order`                             | action order base class. allows to implement "smart" orders which could perform some actions (creation and cancellation of  basic orders) in dependence from the data provided by order manager |
| `order_manager`                            | action orders lifecycle managementsafe communications with echange wrapperdata provision for ActionOrders |
| `bot`                                      | configuration, logging, reporting and workflow  management   |
| `throttle`                                 | requests throttle contoll                                    |
| `trade_orders`                             | container of basic trade order data                          |
|                                            |                                                              |
| **Action Orders**                          | various types of action orders                               |
| `fok_orders`                               | fill-or-kill order implementation (with some amount of time or on price changing) |
| `recovery_orders`                          | stop loss taker order implementation                         |
| `maker_stop_loss` (will be added soon)     | maker stop loss order                                        |
|                                            |                                                              |
| **Calculation helpers**                    | Prices, amounts and other helpers for calculations           |
| `core`                                     | essential assets operations (without connections):trade symbol detectionorder  side detectionrelative price differenceprecision convertion |
| `orderbook`                                | orderbooks in-depth amounts and prices calculations          |
|                                            |                                                              |
| **Tech/Supplementary**                     |                                                              |
| `utils`                                    | various general purpose supplementary functions              |
| `datastorage`                              | csv file management                                          |
| `cli`                                      | command line tools                                           |
| `timer`                                    | operations time counter and reporter                         |
| `errors`                                   | some custom exceptions                                       |
|                                            |                                                              |
| **Reporing**                               |                                                              |
| `reporter`                                 | influxdb  client wrapper for db connection management        |
| `reporter_sqla`                            | sqlalchemy wrapper for db connection management              |
| `data models`                              | sqlalchemy tables  to represent trade orders and deals       |
| `grafana dashboards`  (will be added soon) | samples of grafana dashboards                                |





# Installation

(the installation from pypi will be implemented soon)

**Requirements:**  python3.6+ and some libs 



1. Clone the repo: 

   `git clone https://github.com/ztomsy/ztom.git `

   

2. install the dependencies: 

   `pip3 install -r requirements.txt`

   

3.  install the ztom lib

   `pip3 install -e . `

   

4. run some tests: 

   `python3 -m unittest -v -b`



# License

This project is licensed under the MIT License - see the [LICENSE.md](https://gist.github.com/PurpleBooth/LICENSE.md) file for details

