import ccxt
import ccxt.async_support as accxt
import asyncio
import csv
import json
import uuid
import time
import datetime
from . import exchanges
from . import core
from .throttle import Throttle
from .trade_orders import TradeOrder
from typing import TypeVar
import copy

EW = TypeVar('EW', bound='ccxtExchangeWrapper')


class ExchangeWrapperError(Exception):
    """Basic exception for errors raised by ccxtExchangeWrapper"""
    pass


class ExchangeWrapperOfflineFetchError(ExchangeWrapperError):
    """Exception for Offline fetching errors"""
    pass


class ccxtExchangeWrapper:
    """
     Encapsulates the data and methods, provided by CCXT library, in order to unify the the order management
     capabilities between various exhanges. Also this class provides offline mode for using predefined responses from
     exchanges and throttling control.

     This is done via using separate wrappers placed under exchange folder.

     Attributes:
         exchange_id: a string exchange id as in ccxt
         requests_throttle: ztom.Throttle object for throttling control
         offline: boolean to represent current working mode. False by default, means that wrapper is in online mode.
         tickers: dict of last fatched tickers
         markets: dict of last fetched markets
         order_book_length: int for setting the degault depth for fetching order books
         markets_json_file: string with the path to jason file with markets information used in offline mode
         tickers_csv_file: string with the path to jason file with tickers in offline mode
         PERIOD_SECONDS: float in seconds representing the period time used in Throttle management. Default is 60.
         REQUESTS_PER_PERIOD: int of maximumum amount of requests during the period
         REQUEST_TYPE_WIGHTS: dict which sets the weight (amount of "requests") for different exchange operations.
          {"key": value} where "key" is the string representing the operation and "value" is the weight in requests.
          Example:
              REQUEST_TYPE_WIGHTS = {
                "single": 1,
                "load_markets": 1,
                "fetch_tickers": 1,
                "fetch_ticker": 1,
                "fetch_order_book": 1,
                "create_order": 1,
                "fetch_order": 1,
                "cancel_order": 1,
                "fetch_my_trades": 1,
                "fetch_balance": 1
            }
    """
    _ccxt = None  # type: ccxt.Exchange
    _async_ccxt = ...  # type accxt.Exchange
    _PRECISION_AMOUNT = 8  # default amount precision for offline mode
    _PRECISION_PRICE = 8  # default price precision for offline mode

    PERIOD_SECONDS = 60
    REQUESTS_PER_PERIOD = 100
    REQUEST_TYPE_WIGHTS = {
        "single": 1,
        "load_markets": 1,
        "fetch_tickers": 1,
        "fetch_ticker": 1,
        "fetch_order_book": 1,
        "create_order": 1,
        "fetch_order": 1,
        "cancel_order": 1,
        "fetch_my_trades": 1,
        "fetch_balance": 1
    }

    @classmethod
    def load_from_id(cls, exchange_id, api_key=None, secret=None, offline=False) -> EW:
        """
        Main constructor, which load the wrapper for passed exchange_id. If there is no wrapper for exchnage_id - the
        generic wrapper will be loaded. Could be used without credentials if api_key is not provided.
        Args:
            exchange_id: a string exchange id as in ccxt
            api_key: string with the api_key
            secret: string with the secret
            offline: bool which could be set to True if needed to use the wrapper in offline mode

        Returns:
            ccxtExchangeWrapper object. The ccxtExchangeWrapper._ccxt will contain the ccxt object of initialized
             exchange.

        Raises:
            could raise standart ccxt exceptions
        """

        try:
            exchange = getattr(exchanges, exchange_id)
            exchange = exchange(exchange_id, api_key, secret)
            return exchange
        except AttributeError:
            return cls(exchange_id, api_key, secret, offline)

    def __init__(self, exchange_id, api_key="", secret="", offline=False):
        """
        Default constructor of wrapper. This will not load the wrapper, however will iniate the exchange and put it into
         _ccxt attribute.

        For Args see the load_from_id method.

        """

        if hasattr(ccxt, exchange_id):
            exchange = getattr(ccxt, exchange_id)
            self._ccxt = exchange({'apiKey': api_key, 'secret': secret})

        self.exchange_id = exchange_id

        self.wrapper_id = "generic"

        self.requests_throttle = None  # type: Throttle
        self.offline = offline

        # if True than return trades in order update response.
        # False no trades
        self.trades_in_offline_order_update = True

        # use last tickers from file when the number of fetches exceeds tickers in file
        self.offline_use_last_tickers = False

        self.tickers = dict()
        self.markets = dict()

        self.order_book_length = 100  # default order book length

        self._offline_balance = dict()
        self._offline_markets = dict()
        self._offline_tickers = dict()
        self._offline_tickers_current_index = 0

        self._offline_order_books = dict()  # {"symbol": list(order_book_array_fetch)}
        self._offline_order_books_current_index = dict()  # {"symbol": current_fetch_index}

        self._offline_order = dict()
        self._offline_order_update_index = 0
        self._offline_order_cancelled = False

        self._offline_trades = list()

        # _offline_orders_data - dict of off-line orders data as {order_id: {
        #                                                               "_offline_order": {}
        #                                                               "_offline_order_update_index": int
        #                                                               "_offline_order_cancelled": {}
        #                                                               "_offline_order_trades" : {}
        self._offline_orders_data = dict()
        self.markets_json_file = str
        self.tickers_csv_file = str

    def enable_requests_throttle(self, period=None, requests_per_period=None, request_type_weights=None):
        """
        Enables the requests counting anf throttling (creates the requests_throttle object). If not called or
        self.requests_throttle is None the counting of requests counting will not occur.

        If passed parameters will be not set, the default wrapper's parameters (PERIOD_SECONDS, REQUESTS_PER_PERIOD,
           REQUEST_TYPE_WIGHTS) will be used.

        For arguments definition bee the Throttle class reference.

        Returns:
            Nothing. Just set's the self.requests_throttle with the initiated Throttle object
        """

        if period is None:
            period = self.PERIOD_SECONDS

        if requests_per_period is None:
            requests_per_period = self.REQUESTS_PER_PERIOD

        if request_type_weights is None:
            request_type_weights = self.REQUEST_TYPE_WIGHTS

        self.requests_throttle = Throttle(period, requests_per_period, request_type_weights)

    def _load_markets(self):
        """
            generic method for loading markets could be redefined in custom exchange wrapper

            Returns:
                dict of ccxt.load_markets()
        """
        return self._ccxt.load_markets()

    def _fetch_ohlcv(self, symbol: str, timeframe, since=None, limit=None):
        """
            generic method for loading ohlcv could be redefined in custom exchange wrapper
        """
        return self._ccxt.fetch_ohlcv(symbol, symbol, timeframe, since, limit, params={})

    def _fetch_tickers(self, symbol=None):
        """
        generic method for fetching tickers could be redefined in custom exchange wrapper
        """
        return self._ccxt.fetch_tickers(symbol)

    def _fetch_order_book(self, symbol: str, length=None, params=None):
        """
         generic method for fetching order books could be redefined in custom exchange wrapper
        """
        if not params:
            params = dict()
        return self._ccxt.fetch_order_book(symbol, length, params)

    def fetch_order_book(self, symbol: str, length=None, params=None):
        """
        Fetches order books from exchange or from offline data (in offline mode). If the throttling is enabled,
        the requests with the weight of "fetch_order_book" will be counted.
        Args:
            symbol: string with symbol in ccxt format (ex "ETH/BTC")
            length: int of depth for requested order book if not set the self.order_book_length will be used
            params:

        Returns: list which contains order book in ccxt format

        """

        result = None
        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="fetch_order_book")

        if not self.offline:
            length = self.order_book_length if not length else length
            result = self._fetch_order_book(symbol, length, params)
        else:
            result = self._offline_fetch_order_book(symbol, length, params)

        return result

    def load_markets(self):
        """
        Loads the active markets from the exchange or offline data. Should be called before fetching any tickers and
        creating, proceeding orders.

        If the throttling is enabled, the requests with the weight of "load_markets" will be counted.

        Returns: dict
        """

        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="load_markets")

        if not self.offline:
            markets = self._load_markets()
        else:
            markets = self._offline_load_markets()

        markets = {k: v for k, v in markets.items() if "active" in v and v["active"]}

        if len(markets) < 1:
            self.markets = dict()
            # raise(ExchangeWrapperError("No active markets"))

        self.markets = markets
        return markets

    def fetch_tickers(self, symbol: str = None):
        """
         Fetches tickers or single ticker if the symbol of specifiled from exchange or offline data. Same as ccxt's
          fetch_tickers(). If is offline mode - returns data from the _offline_tickers list.

        If markets were not previously loaded - invokes load_markets() method.

        If the throttling is enabled, the requests with the weight of "fetch_tickers" or "fetch_ticker" if symbol is
         specified.

        Args:
         symbol: string with the single symbol. if ommitted all tickers will be returned
        Returns:
             dict{"[symbol]":ticker_data_duct}
        """

        if symbol is None:
            if self.requests_throttle is not None:
                self.requests_throttle.add_request(request_type="fetch_tickers")
        else:
            if self.requests_throttle is not None:
                self.requests_throttle.add_request(request_type="fetch_ticker")

        if len(self.markets) < 1:
            self.load_markets()

        if not self.offline:
            self.tickers = self._fetch_tickers(symbol)
        else:
            self.tickers = self._offline_fetch_tickers()

            if symbol:
                self.tickers = {symbol: self.tickers[symbol]}

        # filtering tickers for active markets only
        tickers = {k: v for k, v in self.tickers.items() if k in self.markets and self.markets[k]["active"]}
        self.tickers = tickers

        return self.tickers

    def get_exchange_wrapper_id(self):
        return "generic"

    # init offline fetching
    def set_offline_mode(self, markets_json_file: str, tickers_csv_file: str, orders_json_file: str = None):
        """
        Set the wrapper to work in offline mode. Should be called before any exchange requests.

        Args:
            markets_json_file: string with the path to jason file with markets information
            tickers_csv_file: string with the path to jason file with tickers in offline mode
            orders_json_file: depreciated

        Returns:
            sets the self.offline to true

        """

        self.markets_json_file = markets_json_file
        self.tickers_csv_file = tickers_csv_file

        self.offline = True
        self._offline_tickers_current_index = 0
        if markets_json_file is not None:
            self._offline_markets = self.load_markets_from_json_file(markets_json_file)
        if tickers_csv_file is not None:
            self._offline_tickers = self.load_tickers_from_csv(tickers_csv_file)

        if orders_json_file is not None:
            self._offline_order = self.load_order_from_json(orders_json_file)

    @staticmethod
    def load_markets_from_json_file(markets_json_file):
        """
         Supplementary method.
        """

        with open(markets_json_file) as json_file:
            json_data = json.load(json_file)

        return json_data

    @staticmethod
    def load_tickers_from_csv(tickers_csv_file):
        """
         Supplementary method.
        """
        tickers = dict()

        csv_float_fields = ["ask", "bid", "askVolume", "bidVolume"]

        with open(tickers_csv_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if int(row["fetch_id"]) not in tickers:
                    tickers[int(row["fetch_id"])] = dict()

                row_value = dict()
                for v in csv_float_fields:
                    try:
                        row_value[v] = float(row[v])
                    except ValueError:
                        row_value[v] = None

                tickers[int(row["fetch_id"])][row["symbol"]] = dict({"ask": row_value["ask"],
                                                                     "bid": row_value["bid"],
                                                                     "askVolume": row_value["askVolume"],
                                                                     "bidVolume": row_value["bidVolume"]})
        return tickers

    @staticmethod
    def load_order_from_json(order_jason_file):
        with open(order_jason_file) as json_file:
            json_data = json.load(json_file)
        return json_data

    def set_offline_balance(self, balance: dict):
        """
         Sets the information for offline balance fetching.
         Args:
             balance: dict of balances as fetched in ccxt
        """
        self._offline_balance = balance

    def load_offline_order_books_from_csv(self, file_name):
        """
        Loads the order books data which could be later available via fetch_order_books in offine mode (sets the
        self._offline_order_books dict). Also returns the fetched data.

        Args:
            file_name: name of csv file.
                File format format:
                fetch_id | symbol | ask | ask-qty | bid | bid-qty

                where,

                "fetch_id"  is the id of fetch of the whole order book,  column could be any.

                example:

                    fetch	symbol	ask	ask-qty	bid	bid-qty
                    0	ETH/BTC	0.092727	1.451	0.092698	0.3685058
                    0	ETH/BTC	0.092728	0.026	0.092697	23.058
                    ....
                    0	ETH/BTC	0.092774	1.815	0.092603	8.662
                    0	FUEL/BTC	0.0000131	2607.6335877863	0.00001287	2615
                    0	FUEL/BTC	0.00001311	2695	0.00001281	9828
                    ...
                    1	FUEL/BTC	0.00001343	216	0.00001263	8628
                    1	FUEL/BTC	0.00001346	2162	0.00001261	150
                    1   FUEL/ETH	0.00014092	2331	0.000138	2607
                    1 	FUEL/ETH	0.00014205	2460	0.00013722	21133

        Returns:
            dict, containing data for offline order books
        """
        order_books = dict()
        order_books_indexes = dict()  # key is the csv's first column val., value is the current index in order books

        i = 0
        with open(file_name, newline='') as f:
            reader = csv.DictReader(f)
            index_field_name = reader.fieldnames[0]

            for row in reader:
                if row["symbol"] not in order_books:
                    order_books[row["symbol"]] = list()
                    order_books_indexes[row["symbol"]] = list()

                if row[index_field_name] not in order_books_indexes[row['symbol']]:
                    order_books_indexes[row["symbol"]].append(row[index_field_name])
                    order_books[row["symbol"]].append(dict({"asks": list(), "bids": list()}))

                fetch_index = order_books_indexes[row["symbol"]].index(row[index_field_name])

                order_books[row["symbol"]][fetch_index]["asks"].append(list([float(row['ask']), float(row['ask-qty'])]))
                order_books[row["symbol"]][fetch_index]["bids"].append(list([float(row['bid']), float(row['bid-qty'])]))

            self._offline_order_books = order_books
            return order_books

    def _offline_fetch_tickers(self):
        if self._offline_tickers_current_index < len(self._offline_tickers):
            tickers = self._offline_tickers[self._offline_tickers_current_index]
            self._offline_tickers_current_index += 1
            return tickers

        else:
            if not self.offline_use_last_tickers:
                raise (ExchangeWrapperOfflineFetchError(
                    "No more loaded tickers. Total tickers: {}".format(len(self._offline_tickers))))
            else:
                tickers = self._offline_tickers[self._offline_tickers_current_index-1]
                return tickers


    def _offline_fetch_order_book(self, symbol, length=None, params=None):

        # create orderbook from tickers
        if symbol not in self._offline_order_books:

            if len(self.tickers) < 1 or symbol not in self.tickers:
                raise (ExchangeWrapperOfflineFetchError(
                    "No tickers loaded offline for symbol {}. "
                    "use .get_tickers() first or load order book csv file".format(symbol)))

            ob = self._create_order_book_array_from_ticker(self.tickers[symbol])
            ob["from_ticker"] = True
            ob["symbol"] = symbol
            return ob

        if symbol not in self._offline_order_books_current_index:
            self._offline_order_books_current_index[symbol] = 0

        if self._offline_order_books_current_index[symbol] >= len(self._offline_order_books[symbol]):
            raise (ExchangeWrapperOfflineFetchError(
                "No more loaded order books for {}. Total order books: {}".format(symbol, len(
                    self._offline_order_books[symbol]))))

        order_book = self._offline_order_books[symbol][self._offline_order_books_current_index[symbol]]
        self._offline_order_books_current_index[symbol] += 1

        return order_book

    def _offline_create_order(self, order: TradeOrder = None):
        if order is not None and order.internal_id in self._offline_orders_data:
            return self._offline_orders_data[order.internal_id]["_offline_order"]["create"]
        return self._offline_order["create"]

    def _offline_fetch_order(self, order: TradeOrder = None):

        if order is not None and order.internal_id in self._offline_orders_data:
            _offline_order_update_index = self._offline_orders_data[order.internal_id]["_offline_order_update_index"]
            _offline_order = self._offline_orders_data[order.internal_id]["_offline_order"]
            _offline_order_cancelled = self._offline_orders_data[order.internal_id]["_offline_order_cancelled"]

        else:
            _offline_order_update_index = self._offline_order_update_index
            _offline_order = self._offline_order
            _offline_order_cancelled = self._offline_order_cancelled

        if _offline_order_update_index < len(_offline_order["updates"]):
            order_resp = _offline_order["updates"][_offline_order_update_index].copy()

            if not _offline_order_cancelled:
                if order is not None and order.internal_id in self._offline_orders_data:
                    self._offline_orders_data[order.internal_id]["_offline_order_update_index"] += 1
                else:
                    self._offline_order_update_index += 1
            else:
                # order_resp = _offline_order["cancel"]
                order_resp = dict({"status": "canceled", "filled": order.filled})

            if not self.trades_in_offline_order_update:
                if "trades" in  order_resp:
                    order_resp.pop("trades")

            return order_resp

        else:
            raise (ExchangeWrapperOfflineFetchError(
                "No more order updates in file. Total tickers: {}".format(len(self._offline_order["updates"]))))

    def _offline_cancel_order(self, order: TradeOrder = None):

        if order is not None and order.internal_id in self._offline_orders_data:

            if "cancel" not in self._offline_orders_data[order.internal_id]["_offline_order"]:
                # self._offline_order["cancel"] = True
                self._offline_orders_data[order.internal_id]["_offline_order"]["cancel"] = dict({"status": "canceled"})

            if not self._offline_orders_data[order.internal_id]["_offline_order_cancelled"]:
                self._offline_orders_data[order.internal_id]["_offline_order_update_index"] -= 1

            self._offline_orders_data[order.internal_id]["_offline_order_cancelled"] = True
            # return self._offline_orders_data[order.internal_id]["_offline_order"]["cancel"]
            return dict({"status": "canceled", "filled": order.filled})

        else:
            if "cancel" not in self._offline_order:
                # self._offline_order["cancel"] = True
                self._offline_order["cancel"] = dict({"status": "canceled"})

            if not self._offline_order_cancelled:
                self._offline_order_update_index -= 1

            self._offline_order_cancelled = True
            return self._offline_order["cancel"]

    def _offline_load_markets(self):
        if self._offline_markets is not None and len(self._offline_markets):
            return self._offline_markets

        else:
            raise (ExchangeWrapperOfflineFetchError(
                "Markets are not loaded".format(len(self._offline_tickers))))

    def _create_order(self, symbol, order_type, side, amount, price=None):
        # create_order(self, symbol, type, side, amount, price=None, params={})
        return self._ccxt.create_order(symbol, order_type, side, amount, price)

    def _fetch_order(self, order: TradeOrder):
        return self._ccxt.fetch_order(order.id)

    def _cancel_order(self, order: TradeOrder):
        return self._ccxt.cancel_order(order.id)

    def place_limit_order(self, order: TradeOrder):
        """
        Sends the request to exchange to place limit order which parameters described in order object. Exchange responce
         returned by this method could be used to update the TradeOrder object.

         In offline mode the order responses are taken from the self._offline_orders_data.

         Adds the  dict {"timestamp_open": timestamps_dict, "timestamp_closed": timestamps_dict }  with the
         information on timestamps of opening and closing the order (if the order was closed on placement request).

         Each "timestamps_dict" contains following fields:
          - request_placed - timestamp when the request was sent
          - request_received - timestamp when the request received from the exchange
          - from_exchange - timestamp of order from the exchange

         If throttling is enabled counts the weight of "create_order" request.

        Args:
            order: TradeOrder object with the order parameters

        Returns:
            dict with the exchange response which could be used for updating TradeOrder object

        """

        timestamp_open = dict()
        timestamp_open["request_placed"] = datetime.datetime.now().timestamp()

        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="create_order")

        if self.offline:
            result = self._offline_create_order(order)

            timestamp_open["request_received"] = datetime.datetime.now().timestamp()
            timestamp_open["from_exchange"] = datetime.datetime.now().timestamp()
            result["timestamp_open"] = timestamp_open

            # check if order was closed on placement
            if result["status"] in ("closed", "canceled"):
                timestamp_closed = dict()
                timestamp_closed["request_received"] = timestamp_open["request_placed"]
                timestamp_closed["request_placed"] = timestamp_open["request_received"]
                timestamp_closed["from_exchange"] = datetime.datetime.now().timestamp()
                result["timestamp_closed"] = timestamp_closed

            return result

        else:
            result = self._create_order(order.symbol, "limit", order.side, order.amount, order.price)

            timestamp_open["request_received"] = datetime.datetime.now().timestamp()

            # noinspection PyBroadException
            try:
                timestamp_open["from_exchange"] = result["timestamp"] / 1000
            except Exception:
                timestamp_open["from_exchange"] = None

            result["timestamp_open"] = timestamp_open

            # check if order was closed on placement
            if result["status"] in ("closed", "canceled"):
                timestamp_closed = dict()
                timestamp_closed["request_received"] = timestamp_open["request_received"]
                timestamp_closed["request_placed"] = timestamp_open["request_placed"]

                # noinspection PyBroadException
                try:
                    timestamp_closed["from_exchange"] = timestamp_open["from_exchange"]
                except Exception:
                    timestamp_closed["from_exchange"] = None

                result["timestamp_closed"] = timestamp_closed

            return result

    def get_order_update(self, order: TradeOrder):
        """
        Returns the order's data requested from the exchange or from offline data (offline mode documentation for details).

        If throttling is enabled counts the weight of "fetch_order" request.

        Args:
            order: TradeOrder object which should be requested from the exchange

        Returns:
            dict with the order data in ccxt format

        """

        timestamp_closed = dict()
        timestamp_closed["request_placed"] = datetime.datetime.now().timestamp()

        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="fetch_order")

        if self.offline:
            result = self._offline_fetch_order(order)

            if result["status"] in ("closed", "canceled"):
                timestamp_closed["request_received"] = datetime.datetime.now().timestamp()
                timestamp_closed["from_exchange"] = datetime.datetime.now().timestamp()
                result["timestamp_closed"] = timestamp_closed

            return result

        else:
            result = self._fetch_order(order)

            # check if order was closed
            if result["status"] in ("closed", "canceled"):
                timestamp_closed["request_received"] = datetime.datetime.now().timestamp()

                # noinspection PyBroadException
                try:
                    timestamp_closed["from_exchange"] = result["lastTradeTimestamp"] / 1000
                except Exception:
                    timestamp_closed["from_exchange"] = None

                result["timestamp_closed"] = timestamp_closed

            return result

    def cancel_order(self, order: TradeOrder):
        """
        Send the request to exchange to cancel the order and returns the exchange's responce. In offline mode response
        is created from the self._offline_orders_data.

        If throttling is enabled counts the weight of "cancel_order" request.

        Args:
            order: TradeOrder object

        Returns:
            dict with the exchange response which could be used for updating the TradeOrder

        """
        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="cancel_order")

        if self.offline:
            return self._offline_cancel_order(order)
        else:
            return self._cancel_order(order)

    def offline_load_trades_from_file(self, trades_json_file):
        with open(trades_json_file) as json_file:
            json_data = json.load(json_file)
        self._offline_trades = json_data["trades"]

    def _offline_fetch_trades(self):

        if self._offline_order["updates"][self._offline_order_update_index - 1]["trades"] is not None and \
                len(self._offline_order["updates"][self._offline_order_update_index - 1]["trades"]) > 0:
            return self._offline_order["updates"][self._offline_order_update_index - 1]["trades"]

        if self._offline_trades is not None:
            return self._offline_trades

        else:
            raise ExchangeWrapperOfflineFetchError(
                "Offline trades are not loaded")

    def _fetch_order_trades(self, order):
        trades = list()

        resp = self._ccxt.fetch_my_trades(order.symbol, order.timestamp)

        # checking if order id in trades == order id from order
        for trade in resp:
            if trade['order'] == order.id:
                trades.append(trade)

        return trades

    def _offline_fetch_order_trades(self, order: TradeOrder):

        _offline_order_update_index = 0
        _offline_order = None

        if order is not None and order.internal_id in self._offline_orders_data:
            _offline_order_update_index = self._offline_orders_data[order.internal_id]["_offline_order_update_index"]
            _offline_order = self._offline_orders_data[order.internal_id]["_offline_order"]

        if 0 < _offline_order_update_index and _offline_order_update_index >= len(_offline_order["updates"]):
            _offline_order_update_index = len(_offline_order["updates"]) - 1

        trades = _offline_order["updates"][_offline_order_update_index]["trades"]

        return trades

    def get_trades(self, order: TradeOrder):
        """
        Returns  the trades of placed order and checks if amount in trades equal to order's filled amount.

        Throttling: the requests with the weight of "fetch_my_trades" will be counted.

        If the trades information contains in order's data - just extracts it from the order object (some exchanges
        returns the trades within the order update information, for example kucoin). In this case the request is not
        counted within the throttling control.

        Args:
            order: TradeOrder object for which the trades are being requested.

        Returns:
            dict of trades as in ccxt:

        Raises:
            ExchangeWrapperError if the amount calculated from trades not matches the filled order's amount or
            filled amount is zero

        """

        if self.offline:
            if self.requests_throttle is not None:
                self.requests_throttle.add_request(request_type="fetch_my_trades")

            if order.trades and len(order.trades) > 0:
                trades = order.trades
            else:
                trades = self._offline_fetch_order_trades(order)
            return trades

        else:
            amount_from_trades = 0.0

            if len(order.trades) > 0:
                amount_from_trades = self.amount_to_precision(order.symbol,
                                                              sum(item['amount'] for item in order.trades))

            if amount_from_trades < order.filled * 0.9999999:

                if self.requests_throttle is not None:
                    self.requests_throttle.add_request(request_type="fetch_my_trades")

                resp = self._fetch_order_trades(order)

                amount_from_trades = self.amount_to_precision(order.symbol, sum(item['amount'] for item in resp))
            else:
                resp = order.trades

            if len(resp) > 0 and \
                    (order.filled == amount_from_trades or (amount_from_trades / order.filled) >= 0.999):
                return resp

            else:
                raise ExchangeWrapperError(
                    "Zero fill or Amount in Trades is not matching order filled Amount {} != {}".format(
                        amount_from_trades, order.filled))

    @staticmethod
    def fees_from_order_trades(order: TradeOrder):
        """
        Extracts the fees as  dict of ["<CURRENCY>"]["amount"] from order's trades and order's fee field.
        In order to extract fees from trades - Order should be updated with trades before calling this method.
        This method does not request the exchange!

        Args:
            order: TradeOrder
        Returns:
          dict: key is currency and value is amount of fee collected in this currency. In some rare
          cases fee could be taken in several currencies:
           {"ETH":0.00001,
           "BNB":0.0000000001}
        """
        total_fee = dict()

        for t in order.trades:
            if "fee" not in t:
                break

            if t["fee"]["currency"] not in total_fee:
                total_fee[t["fee"]["currency"]] = dict()
                total_fee[t["fee"]["currency"]]["amount"] = 0

            total_fee[t["fee"]["currency"]]["amount"] += t["fee"]["cost"]

        for c in order.start_currency, order.dest_currency:
            if c not in total_fee:
                total_fee[c] = dict({"amount": 0.0})

        return total_fee

    # fetch or (get from order) the trades within the order and return the result calculated by trades:
    # dict = {
    #       "trades": dict of trades from ccxt
    #       "amount" : filled amount of order (base currency)
    #       "cost": filled amount if quote currency
    #       "price" : total order price
    #       "dest_amount" : amount of received destination currency
    #       "src_amount" :  amount of spent source currency

    def get_trades_results(self, order: TradeOrder):
        """
        Fetches or gets from order (if available) the trades within the order and return the result amounts calculated
        from trades:
        dict = {
          "trades": dict of trades from ccxt
          "filled" : filled amount of order (base currency)
          "cost": filled amount if quote currency
          "price" : total (average) order filled price
          "dest_amount" : amount of received destination currency of order
          "src_amount" :  amount of spent source currency of order}

        This dict could be used to update TradeOrder. Update order with this data only if filled amount of order is
         almost equal with the recent "filled" amount received from the order!!!!

        Args:
            order: TradeOrder
        Returns:
             dict with the order's update data
        """

        trades = self.get_trades(order)
        results = order.total_amounts_from_trades(trades)
        results["trades"] = trades
        results["filled"] = results["amount"]
        results["cost"] = self.price_to_precision(order.symbol, results["cost"])

        results["price"] = self.price_to_precision(order.symbol, results["cost"] / results["amount"])

        if order.side == "buy":
            results["dest_amount"] = results["filled"]
            results["src_amount"] = results["cost"]

        elif order.side == "sell":
            results["dest_amount"] = results["cost"]
            results["src_amount"] = results["filled"]

        # we dont need "amount" because amount provided by trades is filled amount not the order's amount
        results.pop("amount")

        return results

    def amount_to_precision(self, symbol, amount):
        """
        returns the converted amount to precision set using the ccxt's amount_to_precision method for online mode or
        tooks the precision from the offline markets data self.markets[symbol]["precision"]["amount"] (if available)
        in offline mode. If the precision information not found uses the default's wrapper's precision value.

        Usually amount to precision are used for calculating the amount of base currency order.

        Args:
            symbol: string with the symbol
            amount: float with the amount to be converted to precision

        Returns:
            float
        """
        if self._ccxt is not None and not self.offline:
            return float(self._ccxt.amount_to_precision(symbol, amount))

        elif self.markets is not None and symbol in self.markets and self.markets[symbol] is not None \
                and "precision" in self.markets[symbol]:
            return core.amount_to_precision(amount, self.markets[symbol]["precision"]["amount"])

        else:
            return core.amount_to_precision(amount, self._PRECISION_AMOUNT)

    def price_to_precision(self, symbol, amount):
        """
        returns the converted amount to precision set using the ccxt's price_to_precision method for online mode or
        tooks the precision from the offline markets data self.markets[symbol]["precision"]["price"] (if available) in
        offline mode. If the precision information not found uses the default's wrapper's precision value.

        Usually amount to precision are used for calculating the amount of quote currency of order or price.

        Args:
            symbol: string with the symbol
            amount: float with the amount to be converted to precision

        Returns:
            float
        """

        if self._ccxt is not None and not self.offline:
            return float(self._ccxt.price_to_precision(symbol, amount))
        elif self.markets is not None and symbol in self.markets and self.markets[symbol] is not None \
                and "precision" in self.markets[symbol]:
            return core.price_to_precision(amount, self.markets[symbol]["precision"]["price"])
        else:
            return core.price_to_precision(amount, self._PRECISION_PRICE)

    @staticmethod
    async def _async_load_markets(exchange):
        await exchange.load_markets()

    async def _get_order_book_async(self, symbol):

        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="fetch_order_book")

        if not self.offline:
            ob = await self._async_ccxt.fetch_order_book(symbol, 100)

        else:
            if not self._offline_order_books or symbol not in self._offline_order_books:
                ob = self._create_order_book_array_from_ticker(self.tickers[symbol])
                ob["from_ticker"] = True
            else:
                ob = self.fetch_order_book(symbol, 100)
                ob["from_ticker"] = False

        ob["symbol"] = symbol
        return ob

    def init_async_exchange(self):
        """
        Inits async ccxt exchange object and load markets
        """
        exchange_async = getattr(accxt, self.exchange_id)
        self._async_ccxt = exchange_async()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._async_load_markets(self._async_ccxt))

    def get_order_books_async(self, symbols):
        """
        Fetches the order books for list of symbols in async mode. Waits till the all order books are being fetched.

        In offline mode if the order book data is not loaded - the order book will be created from the ticker price.

        If the throttling is enabled, the requests with the weight of "fetch_order_book" will be counted for every
        requested order book in list.

        Args:
            symbols: list of symbols to be fetched

        Returns:
            dict  of order books data where key is the symbol of fetched order book

        """
        loop = asyncio.get_event_loop()
        tasks = list()

        for s in symbols:
            tasks.append(self._get_order_book_async(s))

        ob_array = loop.run_until_complete(asyncio.gather(*tasks))
        return ob_array

    def fetch_free_balance(self):
        """
        Fetched the free balance from the exchange. In offline mode returns the  self._offline_balance["free"]
        If the throttling is enabled, the requests with the weight of "fetch_balance" will be counted.

        Returns:
            dict with the balances as in ccxt

        """
        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="fetch_balance")

        result = None
        if self.offline:
            result = self._offline_balance["free"]
        else:
            result = self._ccxt.fetch_free_balance()

        return result

    def fetch_balance(self):
        """
        Fetched the all balances from the exchange. In offline mode returns the  self._offline_balance
        If the throttling is enabled, the requests with the weight of "fetch_balance" will be counted.

        Returns:
            dict with the balances as in ccxt

        """

        if self.requests_throttle is not None:
            self.requests_throttle.add_request(request_type="fetch_balance")

        result = None
        if self.offline:
            result = self._offline_balance
        else:
            result = self._ccxt.fetch_balance()

        return result

    def _create_order_book_array_from_ticker(self, ticker) -> dict:
        ob = dict()
        ob["asks"] = [[ticker["ask"], 99999999]]
        ob["bids"] = [[ticker["bid"], 99999999]]
        return ob

    def create_order_offline_data(self, order: TradeOrder, updates_to_fill: int = 1, zero_fill_updates: int = 0):
        """
        Creates offline data for order's updates. The fill amount will be set in accordace to arguments.

        Args:
            order: TradeOrde: order for which data will be generated
            updates_to_fill: number of updates till 100% fill of order in linear manner.
            zero_fill_updates: number of updates from creation of order while fill amount will be zero.
            Should be less or equal to updates_to_fill. The rest updates till updates_to_fill will fill the 100%.

        Returns:
             order responses data to be provided via offline_fetch_order
        """

        order_resp = dict()
        order_resp["create"] = dict()
        order_resp["create"]["amount"] = self.amount_to_precision(order.symbol, order.amount)
        order_resp["create"]["price"] = self.price_to_precision(order.symbol, order.price)
        order_resp["create"]["status"] = "open"
        order_resp["create"]["filled"] = 0.0
        order_resp["create"]["id"] = str(uuid.uuid4())
        order_resp["create"]["timestamp"] = int(time.time() * 1000)

        order_resp["updates"] = list()
        order_resp["trades"] = list()

        for i in range(0, updates_to_fill):
            update = dict()
            if i < zero_fill_updates:
                update["filled"] = 0.0
            else:
                update["filled"] = (order.amount * (i - zero_fill_updates + 1)) / (updates_to_fill - zero_fill_updates)

            update["cost"] = update["filled"] * order.price
            update["status"] = "open"
            if i >= zero_fill_updates:
                trade = dict({"amount": order.amount / (updates_to_fill - zero_fill_updates),
                              "price": order.price,
                              "cost": (order.amount / (updates_to_fill - zero_fill_updates)) * order.price,
                              "order": order_resp["create"]["id"]})
            else:
                trade = None

            if i > 0:
                update["trades"] = order_resp["updates"][i - 1]["trades"][0:i]
            else:
                update["trades"] = list()

            if trade is not None:
                update["trades"].append(trade)

            if i == updates_to_fill - 1 and updates_to_fill > zero_fill_updates:
                update["status"] = "closed"
                update["filled"] = order.amount
                update["cost"] = update["filled"] * order.price

            elif i == updates_to_fill - 1 and updates_to_fill <= zero_fill_updates:
                update["status"] = "open"
                update["filled"] = 0
                update["cost"] = 0


            order_resp["updates"].append(update)

        # order_resp["trades"] = update["trades"]

        order_resp["cancel"] = dict({"status": "canceled"})

        return order_resp

    def add_offline_order_data(self, order: TradeOrder, updates_to_fill=1, fill_zero_updates=0):
        """
        Creates and adds the offline order updates data.
        Parameters  as in create_order_offline_data

        Returns:
            int with the order's internal id

        """
        o = self.create_order_offline_data(order, updates_to_fill, fill_zero_updates)
        order_id = order.internal_id
        self._offline_orders_data[order_id] = dict()
        self._offline_orders_data[order_id]["_offline_order"] = o
        self._offline_orders_data[order_id]["_offline_trades"] = o['trades']
        self._offline_orders_data[order_id]["_offline_order_update_index"] = 0
        self._offline_orders_data[order_id]["_offline_order_cancelled"] = False
        return order_id
