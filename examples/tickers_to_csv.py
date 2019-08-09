import ztom
import csv
import json
import datetime

"""
This will save markets data and tickers and to tickers.csv and markets.json in current folder. These files could be 
used as an offline data sources for ztom. 

"""

# parameters
number_of_fetches = 10
exchange_id = "binance"
append_tickers = False
symbols_to_save = ["ETH/BTC", "BNB/ETH", "BNB/BTC"]  # [] if to save all the symbols

"""
/// start  
"""

print("Started")
storage = ztom.DataStorage(".")

storage.register("tickers", ["fetch_id", "timestamp", "symbol", "ask", "bid", "askVolume", "bidVolume"],
                 overwrite=not append_tickers)

last_fetch_id = 0
# getting last fetch_id in csv file
if append_tickers:
    with open(storage.entities["tickers"]["full_path"], "r") as csvfile:
        not_header = False
        for row in csv.reader(csvfile):
            last_row = row

    if last_row is not None and last_row[0] != storage.entities["tickers"]["headers"][0]:
        last_fetch_id = int(last_row[0]) + 1

    print("Last fetch_id: {}".format(last_fetch_id))


ex = ztom.ccxtExchangeWrapper.load_from_id(exchange_id)  # type: ztom.ccxtExchangeWrapper
ex.enable_requests_throttle()
ex.load_markets()

markets_to_save = dict()

if len(symbols_to_save) > 0:
    markets_to_save = {k: v for k, v in ex.markets.items() if k in symbols_to_save}
else:
    markets_to_save = ex.markets


with open('markets.json', 'w') as outfile:
    json.dump(markets_to_save, outfile)

print("Init exchange")

for i in range(0, number_of_fetches):

    if i > 0:
        sleep_time = ex.requests_throttle.sleep_time()

        print("Request in current period {}/{} sleeping for {} ".format(
            ex.requests_throttle.total_requests_current_period,
            ex.requests_throttle.requests_per_period,
            sleep_time))

    print("Fetching tickers {}/{}...".format(i + 1, number_of_fetches))
    tickers = ex.fetch_tickers()  # type: dict
    print("... done")

    tickers_to_save = list()
    time_stamp = datetime.datetime.now().timestamp()

    for symbol, ticker in tickers.items():
        if (len(symbols_to_save) > 0 and symbol in symbols_to_save) or len(symbols_to_save) == 0:
            tickers_to_save.append({"fetch_id": i+last_fetch_id, "timestamp": time_stamp, "symbol": symbol,
                                    "ask": ticker["ask"],
                                    "bid": ticker["bid"],
                                    "askVolume": ticker["askVolume"],
                                    "bidVolume": ticker["bidVolume"]})

    storage.save_dict_all("tickers", tickers_to_save)



print("OK")
