Remainings Management
=====================

For **Remainings** we will consider some amount of assets which appear because of order execution and could not be
processed with the next orders.
  
Sources of remainings:
 - order was not filled by 100% and cancelled within FOK or other ActionOrder
 - target order amount was less than minimum amount so exchange rejected to create order


#### Typical case for remainings management  
   
Consider you have placed FOK order with time constraint to sell 1 BTC for ETH and it was canceled/closed by order manager:
 - FOK was closed because of time and filled for 0.9999 BTC so there is 0.0001 remained unfilled
 - Exchange not allows to place any order for 0.0001    
 - You could have several situations of this kind within your trading application

So, in order to convert all the BTCs remainings you have to collect all the remained BTC until its amount will be enough 
to place an order and actually run the orders.


#### Remaining definition

We will define remaining as a set of following data:
- remained currency/asset
- target currency and pair's symbol of order which produced remaining
- amount of remaining 

Using this data it will be possible to create orders in accordance to remaining's target currency.
The efficiency of converting remainings could be tracked by accumulation target asset's amount. 

To deal with remainings ZTOM will provide following capabilities: 

- Remainings Management Workflow
- Data structures tailored for remainings management 
- Supplemental Tools and dashboards  

Workflow
-------- 
0. ActionOrder have been closed with some remaining amount
1. Add remaining to remainings balance tracking db
2. Wait until amount of some remaining asset will be enough for creating order to convert remaining into target currency
3. Place an ActionOrder to trade particular remained currency into and target currency 
4. Add remainings deduction to db on filled amount of ActionOrder 
5. Create Deal record in accordance of trading result

Data structures
---------------
Following data structures are involved during remainings management. 

1. Remainings balance change for tracking all remainings changes  
2. Deal record when some of the remainings were filled.  
3. (optional) Remainings events to track separate adding and filling remainings (within the common events reporting capabilities)

## Remainings balance change table (remainings_balance)
 
- remainings_balance_id  
- exchange_id
- account_id
- timestamp
- action: add, fill (deduct) remainings or aggregate records to optimize table
- currency: currency of remainings
- symbol: trade pair of an order yielded the remaining when remaining was created
- amount_delta: change of amount of currency. could be positive or negative 
- target_currency: asset which was intended to be yielded from remaining proceeding 
- target_amount_delta: considered target amount delta

## Deal report of remaining conversion result

Essential Content of deal report: 
- deal_type: "REMAININGS_CONVERT"
- deal_uuid: new deal_uuid
- status: "FILLED", "ERROR" 
- currency: target currency of remaining conversoin
- start_amount: 0 
- result_amount: filled target currency amount
- gross_profit: filled target currency amount

TODO: add sample generating Deal Report from ActionOrder
```python
import datetime, pytz
from ztom import ActionOrder, Bot, DealReport


bot = Bot(...)
order = ActionOrder(...)
            
deal_report = DealReport(
                timestamp=datetime.now(tz=pytz.timezone("UTC")),
                timestamp_start=datetime.fromtimestamp(order.timestamp, tz=pytz.timezone("UTC")),
                exchange=bot.exchange.exchange_id,
                instance=bot.server_id,
                server=bot.server_id,
                deal_type="REMAININGS_CONVERT",
                deal_uuid="134134-1341234-1341341-2341",
                status="FILLED",
                currency=order.dest_currency,
                start_amount=0.0,
                result_amount=order.filled_dest_amount,
                gross_profit=order.filled_dest_amount,
                net_profit=0.0,
                config=bot.config,
                deal_data={})
``` 
 
## Remainings events (optional)

For tracking adding and filling remainings following date should be tracked or reported.

#### Adding remaining

When adding remaining we should record the particular data regarding added remaining so later it's possible to distinguish
the dynamics of adding remainings.     

- type of event: REMAININGS_ADD
- event_source_id: deal_uuid
- payload:  
  ```JSON
  {
  "deal_uuid": "1233-ABCDH-DDD-sAAAA",
  "currency": "BTC",
  "amount": 0.0001, 
  "target_currency": "ETH",
  "target_amount": "0.000001",
  "symbol": "BTC/ETH", 
  "exchange_id": "superDex", 
  "account_id": "trader_bot_1",
  "timestamps": {
    "trade_order_created": 123123123123,
    "trade_order_closed": 123123123163 
  },
  "ActionOrder": 
    {
    "id": 1414
     }
  } 
  ```
#### Filling remaining
- type of event: REMAININGS_FILL
- event_source_id: deal_uuid
- payload:  
  ```JSON
  {
  "currency": "BTC",
  "amount": 0.01,
  "filled_amount": 0.005,
  "average_price": 231,
  "target_currency": "ETH",
  "target_amount": "0.01",
  "filled_target_amount": "0.005",
  "symbol": "BTC/ETH", 
  "exchange_id": "superDex", 
  "account_id": "trader_bot_1",
  "timestamps": {
    "trade_order_created": 123123123123,
    "trade_order_closed": 123123123163 
  },
  "ActionOrder": 
    {
    "id": 1414
     }
  } 
  ``` 


