from ztom import core
from ztom import errors
from ztom import TradeOrder
from ztom import ActionOrder
import time
import uuid
from ztom import ccxtExchangeWrapper



class RecoveryOrder(ActionOrder):

    def __init__(self, symbol, start_currency: str, start_amount: float, dest_currency: str,
                 dest_amount: float=0.0,
                 fee: float=0.0, cancel_threshold: float=0.000001, max_best_amount_order_updates: int=50,
                 max_order_updates: int=10):
        """
        Creates the Recovery Order. Recovery Order is aimed to be filled for the setted dest amount and if fails fills
        on best market price.

        Workflow of Recovery Order:
        - create limit order with the price in accordance to receive the dest amount
        - if this order is not filled, than cancel it and run a series of consecutive limit orders on ticker
         price (taker)

        :param symbol: pair symbol for order
        :param start_currency: start currency to trade from (available currency)
        :param start_amount: amount of start currency
        :param dest_currency: destination currency to trade to
        :param dest_amount: amount of dest currency
        :param fee: exchange fee for order (not used)
        :param cancel_threshold: cancel current trade order and set new only if the remained amount to fill  is greater than
        this threshold. This is for avoiding the situation of creating new order for less than minimun amount. Usually
        should be minimum order amount/value for the order's pair + commission.
             In ccxt: markets[symbol]["limits"]["amount"]["min"]
        :param max_best_amount_order_updates: number of best amount trade order updates before cancelling
        :param max_order_updates:  max order updates for market price trade orders

        """

        # just to instantiate class, will set all the necessary parameters properly below
        super().__init__(symbol, 0.0, 1, "")

        self.id = str(uuid.uuid4())
        self.timestamp = time.time()  # timestamp of object creation
        self.timestamp_close = float()

        self.symbol = symbol
        self.start_currency = start_currency
        self.start_amount = start_amount
        self.dest_currency = dest_currency
        self.fee = fee
        self.cancel_threshold = cancel_threshold  #
        self.best_dest_amount = dest_amount
        self.best_price = 0.0
        self.price = 0.0

        self.status = "new"  # new, open, closed
        self.state = "best_amount"  # "market_price" for reporting purposes

        self.filled_dest_amount = 0.0
        self.filled_start_amount = 0.0
        self.filled_price = 0.0

        self.filled = 0.0  # filled amount of base currency
        self.amount = 0.0  # total expected amount of to be filled base currency

        self.max_best_amount_orders_updates = max_best_amount_order_updates  # max order updates for best amount
        self.max_order_updates = max_order_updates  # max amount of order updates for market price orders

        self.order_command = None  # None, new, cancel

        if symbol is not None:
            self.side = core.get_trade_direction_to_currency(symbol, self.dest_currency)
            if self.side == "buy":
                self.amount = self.best_dest_amount
            else:
                self.amount = self.start_amount

        self.active_trade_order = None  # type: TradeOrder
        self.orders_history = list()

        self.market_data = dict()  # market data dict: {symbol : {price :{"buy": <ask_price>, "sell": <sell_price>}}

        self._prev_filled_dest_amount = 0.0   # filled amounts on previous orders
        self._prev_filled_start_amount = 0.0  # filled amountsbot, on previous orders
        self._prev_filled = 0.0               # filled amounts on previous orders

        self._force_close = False
        self._init_best_amount()

    # @property
    # def symbol(self):
    #     return self.__symbol
    #
    # # set the symbol and side of recovery order
    # @symbol.setter
    # def symbol(self, value):
    #     self.__symbol = value
    #     if value is not None:
    #         self.side = core.get_trade_direction_to_currency(value, self.dest_currency)

    def _init_best_amount(self):

        self.status = "open"
        self.state = "best_amount"
        self.order_command = "new"

        price = self._get_recovery_price_for_best_dest_amount()
        self.active_trade_order = self._create_recovery_order(price, self.state)

    def _init_market_price(self):
        try:
            price = self.market_data[self.symbol]["price"][self.side]
        except Exception:
            raise errors.OrderError("Could not set price from market data")

        self.status = "open"
        self.state = "market_price"
        self.order_command = "new"

        self.active_trade_order = self._create_recovery_order(price, self.state)

    def _get_recovery_price_for_best_dest_amount(self):
        """
        :return: price for recovery order from target_amount and target_currency without fee
        """
        if self.best_dest_amount == 0 or self.start_amount == 0:
            raise errors.OrderError("RecoveryManagerError: Zero start ot dest amount")

        if self.symbol is None:
            raise errors.OrderError("RecoveryManagerError: Symbol is not set")

        if self.side is None:
            raise errors.OrderError("RecoveryManagerError: Side not set")

        if self.side == "buy":
            return self.start_amount / self.best_dest_amount
        if self.side == "sell":
            return self.best_dest_amount / self.start_amount
        return False

    def _create_recovery_order(self, price, state:str):

        amount = self.start_amount - self.filled_start_amount

        if amount <= 0:
            raise errors.OrderError("Bad new order amount {}".format(amount))

        order_params = (self.symbol, self.start_currency, amount,
                        self.dest_currency, price)

        if False not in order_params:
            self.price = price
            order = TradeOrder.create_limit_order_from_start_amount(*order_params)  # type: TradeOrder
            order.supplementary.update({"parent_action_order": {"state": state}})
            return order

        else:
            raise errors.OrderError("Not all parameters for Order are set")

    def _on_open_order(self, active_trade_order: TradeOrder, market_data):
        self.order_command = "hold"

        current_state_max_order_updates = self.max_best_amount_orders_updates if self.state == "best_amount" \
            else self.max_order_updates

        if self.active_trade_order.update_requests_count >= current_state_max_order_updates \
                and self.active_trade_order.amount - self.active_trade_order.filled > self.cancel_threshold:
            # add ticker request command to order manager
            self.order_command = "cancel tickers {symbol}".format(symbol=self.active_trade_order.symbol)

        return self.order_command

    def _on_closed_order(self, active_trade_order: TradeOrder, market_data=None):
        if self.filled_start_amount >= self.start_amount * 0.99999:  # close order if filled amount is OK
            self.order_command = ""
            self._close_active_order()
            self.close_order()
            return self.order_command

        self.state = "market_price"  # else set new order status
        if market_data is not None and market_data[0] is not None:
            self._close_active_order()

            ticker = market_data[0]

            new_price = core.get_symbol_order_price_from_tickers(self.start_currency, self.dest_currency,
                                                                 {self.symbol: ticker})["price"]

            self.active_trade_order = self._create_recovery_order(new_price, self.state)
            self.order_command = "new"
        else:
            # if we did not received ticker - so just re request the ticker
            self.order_command = "hold tickers {symbol}".format(symbol=self.active_trade_order.symbol)

            # print("New price not set... Hodling..")
            # raise errors.OrderError("New price not set")

        return self.order_command


