import os
import time
from dotenv import load_dotenv
import ztom

load_dotenv()

api_key = os.getenv("ZTOM_API_KEY")
secret = os.getenv("ZTOM_SECRET")

ew = ztom.ccxtExchangeWrapper("binance", api_key=api_key, secret=secret)
ew.enable_requests_throttle()
ew.load_markets()
tickers = ew.fetch_tickers()


order = ztom.FokOrder.create_from_start_amount(
    "BNB/BUSD",
    start_currency="BNB",
    amount_start=0.1,
    dest_currency="BUSD",
    price=tickers["BNB/BUSD"]["ask"],
    time_to_cancel=600,
)

om = ztom.ActionOrderManager(ew)
om.add_order(order)

print("Sleeping for {}s".format(om.request_sleep))
time.sleep(om.request_sleep)


while om.have_open_orders():
    # if om.pending_actions_number() == 0:
    #     sleep_time = ew.requests_throttle.sleep_time()
    #     print("Sleeping for {}s".format(sleep_time))
    #     time.sleep(sleep_time)
    # else:
    #   print("!!! NO SLEEP. ACTIONS ARE PENDING !!!")
    om.proceed_orders()

    print(f"Order status {order.status} filled {order.filled}/{order.amount}")

    time.sleep(om.request_sleep)

print("Result")
print(f"Order status {order.status} filled {order.filled}/{order.amount}")

