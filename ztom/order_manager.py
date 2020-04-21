from . import TradeOrder
from . import ccxtExchangeWrapper
from . import ActionOrder
from . import core
from . import utils
from datetime import datetime
from .errors import *
import copy
import time
from typing import List


class ActionOrderManager(object):

    LOG_DEBUG = "DEBUG"
    LOG_INFO = "INFO"
    LOG_ERROR = "ERROR"
    LOG_CRITICAL = "CRITICAL"

    DATA_REQUEST_DELIMITER = ";" # Delimiter to specify several data requests within the order command
    DATA_FETCHING_METHODS = {"tickers": "_fetch_ticker"}  # should be in lower case

    def __init__(self, exchange: ccxtExchangeWrapper, max_order_update_attempts=20, max_cancel_attempts=10,
                 request_sleep=0.0):
        self.orders = list()

        if not int(max_order_update_attempts):
            raise(OwaManagerError("Bad max_order_update_attempts {}".format(max_order_update_attempts)))

        if not int(max_cancel_attempts):
            raise(OwaManagerError("Bad max_cancel_attempts {}".format(max_cancel_attempts)))

        self.max_order_update_attempts = max_order_update_attempts
        self.max_cancel_attempts = max_cancel_attempts

        self.last_update_time = datetime(1, 1, 1, 1, 1, 1, 1)

        self.orders = list()
        self._prev_orders_status = dict()  # dict of orders by id

        self.exchange = exchange
        self.supplementary = dict()  # dict of supplementary data  as {"order_id": {dict of data}}

        self._last_update_closed_orders = list()  # closed orders from last update
        self.request_sleep = request_sleep

        self.request_trades = True  # set to False if trades are not needed for collecting all the order's data
        """
        set to False if trades are not needed for collecting all the order's data
        """

        self.data_for_orders = dict()  # data for orders provided externally. resets on every proceed_orders()
        self._prepared_data_for_orders = dict()  # data for orders compiled from external data and fetched data

        self.offline_order_updates = 10  # number of trades for offline order data
        self.offline_order_zero_fill_updates = 0
        """
        number of order updates with zero filled amount  
        """

    def _create_order(self, order: TradeOrder):

        if self.exchange.offline and order.internal_id not in self.exchange._offline_orders_data:
            self.exchange.add_offline_order_data(order, self.offline_order_updates,
                                                 self.offline_order_zero_fill_updates)

        results = None
        i = 0
        while bool(results) is not True and i < self.max_order_update_attempts:
            self.log(self.LOG_DEBUG, "creating order attempt #{}".format(i))
            try:
                results = self.exchange.place_limit_order(order)
            except Exception as e:
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "retrying to create order...")

                self.log(self.LOG_INFO, "Pause for {}s".format(self.request_sleep))
                time.sleep(self.request_sleep)

            i += 1

        return results

    def _update_order(self, order: TradeOrder):
        results = None
        i = 0
        while bool(results) is not True and i < self.max_order_update_attempts:
            self.log(self.LOG_DEBUG, "..updating trade order {} / {}".format(i,self.max_order_update_attempts ))
            try:
                results = self.exchange.get_order_update(order)
            except Exception as e:
                self.log(self.LOG_ERROR, "Could not update order")
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "Pause for {}s".format(self.request_sleep))
                time.sleep(self.request_sleep)
            i += 1

        return results

    def _cancel_order(self, order: TradeOrder):
        return self.exchange.cancel_order(order)

    # blocking method !!!!!
    def cancel_order(self, trade_order: TradeOrder):
        cancel_attempt = 0

        while cancel_attempt < self.max_cancel_attempts:
            cancel_attempt += 1
            try:
                self._cancel_order(trade_order)

            except Exception as e:
                self.log(self.LOG_ERROR, "Cancel error...")
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "Pause for {}s".format(self.request_sleep))
                time.sleep(self.request_sleep)

            finally:
                self.log(self.LOG_DEBUG, "Updating the Trade Order to check if it was canceled or closed...")
                resp = self._update_order(trade_order)
                self.log(self.LOG_DEBUG, "Update resp: {}".format(resp))
                if resp is not None and "status" in resp and (resp["status"] == "closed"
                                                              or resp["status"] == "canceled"):
                    self.log(self.LOG_DEBUG, "... canceled with status {}".format(resp["status"]))
                    return resp

        return None

    def log(self, level, msg, msg_list=None):
        if msg_list is None:
            print("{} {}".format(level, msg))
        else:
            print("{} {}".format(level, msg))
            for line in msg_list:
                print("{} ... {}".format(level, line))

    def _get_trade_results(self, order: TradeOrder):

        results = None
        i = 0
        while bool(results) is not True and i < self.max_order_update_attempts:
            self.log(self.LOG_DEBUG, "getting trades #{}".format(i))
            try:
                results = self.exchange.get_trades_results(order)
                return results
            except Exception as e:
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "Pause for {}s".format(self.request_sleep))
                time.sleep(self.request_sleep)
                self.log(self.LOG_INFO, "retrying to get trades...")
            i += 1

        return None

    def add_order(self, order: ActionOrder):
        self.orders.append(order)

    def get_order_by_uuid(self, uuid):
        pass

    def _update_order_from_exchange(self, order: ActionOrder, resp, market_data=None):

        try:
            order.update_from_exchange(resp, market_data)
        except Exception as e:
            self.log(self.LOG_ERROR, type(e).__name__)
            self.log(self.LOG_ERROR, e.args)

    def _fetch_taker_price_from_exchange_legacy(self, order: ActionOrder):
        if self.exchange.offline:
            return self.exchange.price_to_precision(order.symbol, order.price*0.999)
        try:

            ticker = self.exchange.fetch_tickers(order.symbol)

            price = core.get_symbol_order_price_from_tickers(order.start_currency, order.dest_currency,ticker)["price"]
            return price

        except Exception as e:
            self.log(self.LOG_ERROR, "Could not fetch tickers")
            self.log(self.LOG_ERROR, type(e).__name__)
            self.log(self.LOG_ERROR, e.args)

        return None

    def _fetch_ticker(self, request_params: str):
        """
        Fetching ticker(-s) from the exchange.Could be specified to request all the tickers, ticker for symbol other
        parameters are ignoder.

        Examples for the full data request command (note that "ticker" should not be in request_parameters, because it
        presents in data request command):

        data request commands:

        "ticker" - returns all the tickers (request_params is empty)
        "ticker ETH/BTC" - returns all the ticker fields
        "ticker ETH/BTC ask" - returns all the ticker's fields

        :param request_params: [symbol] [field_in ticker]
        :return: should return the value in the nested dict constructed from the request_params :
        {"request_params_1":{"request_params_2: {.... : value}}}

        """

        request_params_split = request_params.split(" ")
        symbol = request_params_split[0]

        ticker = self.exchange.fetch_tickers(symbol)

        # if len(request_params.split(" ")) > 1:
        #     return utils.dict_value_from_path(ticker, request_params_split)
        return ticker

    def get_open_orders(self):
        return list(filter(lambda x: x.status != "closed", self.orders))

    def have_open_orders(self):
        """
        returns True if there are open orders or False if no

        """
        if len(list(filter(lambda x: x.status != "closed", self.orders))) >0 :
            return True
        return False


    def get_order_by_id(self, order_id):
        o = (order for order in self.orders if order.id == order_id)
        return o

    def set_order_supplementary_data(self, order: ActionOrder, data: dict):
        """
        Add supplementary data (as dict) for order. For reporting or other purposes. The data will be stored as
        supplementary[order.id] in order manager. This method will override previously stored data.
        :param data: dict of data
        :param order: order object reference
        :return: True
        """

        self.supplementary[order.id] = copy.copy(data)

        return True

    @staticmethod
    def _order_action(order_command: str) -> str:
        """
        parse the request for command and data from the order and extracts the order command (action)
        order command could consists from: ORDER_COMMAND [DATA_REQUEST_KEY [DATA_REQUEST_PARAMETERS]]

        There are could be several data requests separated by ";" (ActionOrderManager.DATA_REQUEST_DELIMITER).

        Trailing spaces and delimiters will be omitted.

        Examples:
        - "cancel ticker"
        - "cancel ticker eth/btc; ma eth/btc"

        :param order_command: command from ActionOrder
        :return: order action: "hold", "new", "cancel"

        """
        return order_command.split(" ")[0]

    @staticmethod
    def _data_requests(order_command: str) -> List[str]:
        """
        parse the order command and extract the data requests as list
        :param order_command: command from ActionOrder
        :return: list of data_requests or None if there is no data request
        """

        splitted_command = order_command.split(" ", 1)

        if len(splitted_command) > 1:
            data_request = order_command.split(" ", 1)[1]
            data_requests = data_request.split(ActionOrderManager.DATA_REQUEST_DELIMITER)
            data_requests_stripped = [dr.strip() for dr in data_requests if dr is not None and dr.strip() != ""]
            return data_requests_stripped
        else:
            return None

    def _single_data_request_value(self, data_request: str, action_order_id: str = "NOT_SET"):
        """
        parses the data request, checks if the available data for requested KEY is in self.data_for_orders dict
        or  calls the data gathering method from the self.DATA_FETCHING_METHODS dict and returns the result.

        The dict self.data_for_orders is constructed in following way:

            self.data_for_orders = {
                "data_request_key":{"parameter":value}
            }
            or
            {"data_request_key":value} if there is nor parameter considered

        Example:
            self.data_for_orders = {
                "tickers":{"ETH/BTC":{"ask": 1213, "bid":123123,
                           "ETH/USDT":{"ask": 1213, "bid":123123},
                "ma5": {"ETH/BTC":12}
            }

        :param data_request:str
        :return: data for order as {"data_request_key":value}
        """

        if not data_request:
            self.log(self.LOG_ERROR, "Order {action_order_id}. Empty data request".format(
                action_order_id=action_order_id))

            raise(OwaManagerError("Order {action_order_id}. Empty data request".format(
                action_order_id=action_order_id)))

        data_request_split = data_request.split(" ")
        # data_request_all = data_request_split[0:]

        data_request_key = data_request_split[0]
        data_request_parameters = " ".join(data_request_split[1:])

        self.log(self.LOG_INFO, "Order {action_order_id}. Data request: {data_request} ".format(
            action_order_id=action_order_id, data_request=data_request))

        # try to fetch the data from self.data_for_orders
        # if there is no data with a requested key so all the data with this key will be invoked by Order Manager

        if data_request_key.upper() in [key.upper() for key in self.data_for_orders.keys()]:

            self.log(self.LOG_INFO, "Order {action_order_id}. Getting data from self.data_for_orders.".format(
                action_order_id=action_order_id))

            request_value_from_data = utils.dict_value_from_path(self.data_for_orders, data_request_split)

            return request_value_from_data

        # calling the data fetching method in correspondence to data_request_key
        if data_request_key in self.DATA_FETCHING_METHODS:

            self.log(self.LOG_INFO,
                     "Order {action_order_id}. Calling {func} for data with params {params}".format(
                         action_order_id=action_order_id, func=self.DATA_FETCHING_METHODS[data_request_key.lower()],
                         params = data_request_parameters))

            _func = getattr(self, self.DATA_FETCHING_METHODS[data_request_key.lower()])
            result_value = _func(data_request_parameters)

            # we should recreate the dict with the data in order to find the value from path,
            # so adding the data request key to the results from the fetching method
            result_dict = {data_request_key: result_value}

            result = utils.dict_value_from_path(result_dict, data_request_split)

            return result

        # return None if no data source was found
        self.log(self.LOG_ERROR, "Order {action_order_id}. No data source found! ".format(
            action_order_id=action_order_id))
        return None

    def _data_request_list_values(self, data_request_list: List[str], action_order_id: str = "NOT_SET"):

        if data_request_list is None or len(data_request_list) < 1:
            return None

        results = list()
        for dr in data_request_list:

            try:
                results.append(self._single_data_request_value(dr, action_order_id))

            except Exception as e:
                results.append(None)
                self.log(self.LOG_ERROR, "Order {action_order_id}. Could not get data for request:"
                                         " '{data_request}'".format(data_request=dr, action_order_id=action_order_id))
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)

        return results

    # call back when the OwaOrder is being closed
    def on_order_close(self, order):
        pass

    def proceed_orders(self):

        self._last_update_closed_orders = list()
        open_active_orders = list(filter(lambda x: x.status != "closed" and x.active_trade_order is not None, self.orders)) #type: List[ActionOrder]

        # open_orders = list(filter(lambda x: x.status != "closed", self.orders))
        # iterate through open ActionOrders with presented trade orders.
        # so there should be always active trade order within the ActionOrder
        #
        for order in open_active_orders:

            self._prev_orders_status[order.id] = copy.copy(order)

            if order.changed_from_last_update:
                # ActionOrder general status log
                self.log(self.LOG_INFO, "Order {action_order_id} STATUS {action_order_str_status}"
                         .format(action_order_id=order.id,
                                 action_order_str_status=order.__str_status__()))

            order_action = self._order_action(order.order_command)
            data_requests = self._data_requests(order.order_command)

            if order_action == "new":
                self.log(self.LOG_INFO, "Order {} creating new trade order for {} -{}-> {} amount {} price {}".format(
                    order.id, order.start_currency, order.side, order.dest_currency, order.get_active_order().amount,
                    order.get_active_order().price))

                if order.get_active_order().status != "open":
                    resp = self._create_order(order.get_active_order())

                    # if could not create Trade Order - than close the whole RecoveryOrder and report
                    if resp is None or ("id" not in resp):
                        self.log(self.LOG_ERROR, "Order {} could not create new trade order".format(order.id))
                        self.log(self.LOG_ERROR, "Order {} to be closed".format(order.id))
                        order.close_order()
                    else:

                        market_data = self._data_request_list_values(data_requests, order.id)
                        self._update_order_from_exchange(order, resp, market_data)

                        self.log(self.LOG_INFO,
                                 "Order {} CREATED new trade order for {} -{}-> {} amount {} price {}".format(
                                     order.id, order.start_currency, order.side, order.dest_currency,
                                     resp["amount"],
                                     resp["price"]))




                else:
                    raise OwaManagerError("Order already set")

            elif order_action == "hold":

                resp = self._update_order(order.get_active_order())

                if resp is None:
                    self.log(self.LOG_INFO, "skipping order")
                    continue

                if "status" in resp and resp["status"] == "closed" or resp["status"] == "canceled":
                    self.log(self.LOG_INFO, "Order {} trade order have been closed with status {}  {} -{}-> {}".format(
                        order.id, resp["status"], order.start_currency, order.side, order.dest_currency))

                    if self.request_trades:
                        # workaround.we should have updated order data before getting the correct trades results from trades
                        order.active_trade_order.update_order_from_exchange_resp(resp)

                        if resp["filled"] > 0:
                            try:
                                trades = self._get_trade_results(order.get_active_order())
                                if trades is not None and len(trades["trades"]) > 0:
                                    for key, value in trades.items():
                                        if value is not None:
                                            resp[key] = value
                                else:
                                    self.log(self.LOG_ERROR, "skipping getting trades for this order")

                            except Exception as e:
                                self.log(self.LOG_ERROR, "Error collecting trades result")
                                self.log(self.LOG_ERROR, type(e).__name__)
                                self.log(self.LOG_ERROR, e.args)
                                self.log(self.LOG_ERROR, "Trades: {}".format(trades))

                market_data = self._data_request_list_values(data_requests, order.id)

                self._update_order_from_exchange(order, resp, market_data)

                if order.get_active_order() is not None:
                    if order.changed_from_last_update:
                        self.log(self.LOG_INFO, str(order))
                else:
                    o = order.orders_history[-1]
                    self.log(self.LOG_INFO, "Order {} trade order closed {} with status {} filled {}/{}".format(
                        order.id, o.update_requests_count, o.status, o.filled,
                        o.amount))

            elif order_action == "cancel":
                self.log(self.LOG_INFO, "Order {} Proceed to cancelling trade order# {} {} {} -{}-> {} ".format(
                    order.id, order.get_active_order().id, order.get_active_order().symbol, order.start_currency,
                    order.side, order.dest_currency))

                # self.log(self.LOG_INFO, "... order {} Fetching ticker {}".format(order.id, order.symbol))
                #
                # price = self._fetch_taker_price_from_exchange_legacy(order)
                #
                # if price is None:
                #     self.log(self.LOG_ERROR, "New price getting error. Skipping the order update")
                #     continue
                #
                # self.log(self.LOG_INFO, ".. cancelling Order {} trade order {}".format(
                #     order.id, order.get_active_order().id))

                resp = self.cancel_order(order.get_active_order())

                # if could not cancel - just skip
                if resp is not None:

                    if self.request_trades:
                        order.active_trade_order.update_order_from_exchange_resp(resp)  # workaround

                        if order.get_active_order().filled > 0:
                            trades = self._get_trade_results(order.get_active_order())
                            try:
                                if trades is not None and trades["trades"] is not None and len(trades["trades"]) > 0:
                                    for key, value in trades.items():
                                        if value is not None:
                                            resp[key] = value
                            except Exception as e:
                                self.log(self.LOG_ERROR, "Error collecting trades result")
                                self.log(self.LOG_ERROR, type(e).__name__)
                                self.log(self.LOG_ERROR, e.args)
                                self.log(self.LOG_ERROR, "Trades: {}".format(trades))

                    resp["status"] = "canceled"  # override exchange response
                    # self._update_order_from_exchange(order, resp, {"price": price})
                    o = order.get_active_order()
                    self.log(self.LOG_INFO, "Order {} trade order closed {} with status {} filled {}/{}".format(
                        order.id, o.update_requests_count,  o.status, o.filled,
                        o.amount))

                    market_data = self._data_request_list_values(data_requests, order.id)
                    self._update_order_from_exchange(order, resp, market_data)

                else:
                    self.log(self.LOG_ERROR, "Could not cancel. Skipping...")

            else:
                raise OwaManagerError("Unknown order command")

            if order.status != "open":

                self.log(self.LOG_INFO, "Order {} Status: {}. State {}. Total filled {}/{}".format(order.id,
                                                                                                   order.status,
                                                                                                   order.state,
                                                                                                   order.filled,
                                                                                                   order.amount))

                self._last_update_closed_orders.append(order)
                # self.on_order_close(order)

        # let's clean data_for_orders in the the end of orders iteration
        self.data_for_orders = dict()

    def get_closed_orders(self):
        """
        get the list of orders which became closed from the last update
        :return: list of closed orders or None if there is no any
        """
        if len(self._last_update_closed_orders) > 0:
            return self._last_update_closed_orders
        else:
            return None

    def pending_actions_number(self):
        """
        returns the count of open orders waiting to perform "new" or "cancel" commands
        """

        orders_with_actions = list(filter(lambda x: x.status != "closed" and x.active_trade_order is not None
                                                    and self._order_action(x.order_command) in ("new", "cancel"),
                                          self.orders))

        return len(orders_with_actions)
