import ztom
import csv
"""
This will save all fetched tickers to tickers.csv file in current folder. 
"""

# parameters
number_of_fetches = 10
exchange_id = "binance"
append = False

"""
/// start  
"""

print("Started")
storage = ztom.DataStorage(".")

storage.register("tickers", ["fetch_id", "timestamp", "symbol", "ask", "bid", "askVolume", "bidVolume"],
                 overwrite=not append)

last_fetch_id = 0
# getting last fetch_id in csv file
if append:
    with open(storage.entities["tickers"]["full_path"], "r") as csvfile:
        not_header = False
        for row in csv.reader(csvfile):
            last_row = row

    if last_row is not None and last_row[0] != storage.entities["tickers"]["headers"][0]:
        last_fetch_id = int(last_row[0]) + 1

    print("Last fetch_id: {}".format(last_fetch_id))


ex = ztom.ccxtExchangeWrapper.load_from_id(exchange_id)  # type: ztom.ccxtExchangeWrapper
ex.enable_requests_throttle()

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

    for symbol, ticker in tickers.items():
        tickers_to_save.append({"fetch_id": i+last_fetch_id, "timestamp": "000000000000", "symbol": symbol,
                                "ask": ticker["ask"],
                                "bid": ticker["bid"],
                                "askVolume": ticker["askVolume"],
                                "bidVolume": ticker["bidVolume"]})

    storage.save_dict_all("tickers", tickers_to_save)

print("OK")
