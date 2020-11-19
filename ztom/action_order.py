from collections import namedtuple
from typing import NamedTuple
from ztom import core
from ztom import errors
from ztom import TradeOrder
import copy
import uuid
import time


class ActionOrderSnapshot(NamedTuple):
    symbol: str = ""
    amount: float = 0.0
    price: float = 0.0
    side: str = ""
    status: str = ""
    state: str = ""
    filled: float = 0.0
    active_trade_order_id: str = ""
    active_trade_order_status: str = ""


class ActionOrder(object):

    # ActionOrderSnapshot = namedtuple("ActionOrderSnapshot", [
    #     "symbol",
    #     "amount",
    #     "price",
    #     "side",
    #     "status",
    #     "state",
    #     "filled",
    #     "active_trade_order_id"])

    def __eq__(self, other):
        fields_to_compare = list(["id", "status", "symbol", "start_currency", "dest_currency",
                                  "status", "state", "filled_dest_amount", "filled_start_amount",
                                  "filled_price", "filled", "amount"])
        for f in fields_to_compare:
            if getattr(self, f) != getattr(other, f): return False
        return True

    def __init__(self, symbol, amount: float, price: float, side: str,
                 cancel_threshold: float = 0.000001, max_order_updates: int = 10):

        if price is None or price <= 0:
            raise errors.OrderError("Wrong price {}".format(price))

        self.id = str(uuid.uuid4())  # internal ID

        self.timestamp = time.time()  # timestamp of object creation
        self.timestamp_close = float()

        # Generic order Parameters
        self.symbol = symbol
        self.amount = amount
        self.price = price
        self.side = side

        self.cancel_threshold = cancel_threshold  # do not cancel if less than this threshold

        self.status = "new"  # new, open, closed

        self.filled_dest_amount = 0.0
        self.filled_start_amount = 0.0
        self.filled_price = 0.0

        self.filled = 0.0  # filled amount of base currency

        self.max_order_updates = max_order_updates  # max amount of order updates

        self.order_command = None  # None, new, cancel

        self.active_trade_order = None
        self.orders_history = list()  # type: List[TradeOrder]

        self.market_data = list()  # list of data received by via order commands

        self._prev_filled_dest_amount = 0.0  # filled amounts on previous orders
        self._prev_filled_start_amount = 0.0  # filled amountsbot, on previous orders
        self._prev_filled = 0.0  # filled amounts on previous orders

        # create initial trade order
        self.active_trade_order = self._create_initial_trade_order()  # type: TradeOrder

        # different tags for additional information
        self.tags = list()

        self.changed_from_last_update = True
        """
        is changed from last update
        """

        self.previous_snapshot: ActionOrderSnapshot = ActionOrderSnapshot()

        self._force_close = False
        """
        flag to force ActionOrder  closing. Means to cancel current trade order and finalize
        """

        # init the global parameters of order and state
        self._init()

    @classmethod
    def create_from_start_amount(cls, symbol, start_currency, amount_start, dest_currency, price,
                                 cancel_threshold: float = 0.000001, max_order_updates: int = 10):

        side = core.get_order_type(start_currency, dest_currency, symbol)

        if not side:
            raise errors.OrderError("Wrong symbol {} for trade {} - {}".format(symbol, start_currency, dest_currency))

        if price <= 0:
            raise errors.OrderError("Wrong price. Symbol: {}, Side:{}, Price:{} ".format(symbol, side, price))

        if side == "sell":
            amount = amount_start

        elif side == "buy":
            amount = amount_start / price

        owa_order = cls(symbol, amount, price, side, cancel_threshold, max_order_updates)
        return owa_order

    def _create_initial_trade_order(self):
        active_trade_order = TradeOrder("limit", self.symbol, self.amount, self.side, self.price)
        return active_trade_order

    def _init(self):
        self.start_currency = self.active_trade_order.start_currency
        self.dest_currency = self.active_trade_order.dest_currency

        self.start_amount = self.active_trade_order.amount_start
        self.dest_amount = self.active_trade_order.amount_dest

        self.status = "open"
        self.state = "fill"
        self.order_command = "new"

        self.active_trade_order.supplementary.update({"parent_action_order": {"state": self.state}})

    # todo check if active_order is closed or cancelled
    def close_order(self):
        # self.close_active_order()
        self.status = "closed"
        self.active_trade_order = None
        self.order_command = ""
        self.timestamp_close = time.time()
        if self._force_close:
            self.tags.append("#force_close")

        self._force_close = False

    def get_active_order(self):
        return self.active_trade_order

    def _set_active_order(self, order: TradeOrder):
        self.active_trade_order = order

    def _close_active_order(self):
        if self.active_trade_order.status == "closed" or self.active_trade_order.status == "canceled":
            self.orders_history.append(copy.copy(self.active_trade_order))
            self.active_trade_order = None
            self.order_command = ""

            self._prev_filled = copy.copy(self.filled)
            self._prev_filled_start_amount = copy.copy(self.filled_start_amount)
            self._prev_filled_dest_amount = copy.copy(self.filled_dest_amount)

        else:
            raise errors.OrderError("Active Trade order is not closed {}".format(self.active_trade_order.status))

    def update_from_exchange(self, resp, market_data=None):
        """
        :param resp:
        :param market_data: some market data (price, orderbook?) for new tradeOrder
        :return: updates the self.order_command and returns it

        """
        snapshot_before_update = self._snapshot()

        self.active_trade_order.update_order_from_exchange_resp(resp)
        self.market_data = market_data

        self.filled_dest_amount = self._prev_filled_dest_amount + self.active_trade_order.filled_dest_amount
        self.filled_start_amount = self._prev_filled_start_amount + self.active_trade_order.filled_start_amount

        if self.filled_dest_amount != 0 and self.filled_start_amount != 0:
            self.filled_price = self.filled_start_amount / self.filled_dest_amount if self.side == "buy" else \
                self.filled_dest_amount / self.filled_start_amount

        self.filled = self._prev_filled + self.active_trade_order.filled

        snapshot_after_update = self._snapshot()

        if snapshot_before_update != snapshot_after_update:
            self.changed_from_last_update = True
            self.previous_snapshot = snapshot_before_update
        else:
            self.changed_from_last_update = False

        if self.active_trade_order.status == "open":

            # proceed with forced order closing
            if not self._force_close:
                self.order_command = "hold"
            else:
                self.order_command = "cancel"
                return "cancel"

            next_command = self._on_open_order(self.active_trade_order, market_data)

            if next_command is not None:
                self.order_command = next_command
            return self.order_command

        if self.active_trade_order.status == "closed":
            self.order_command = ""

            next_command = self._on_closed_order(self.active_trade_order, market_data)

            if next_command is not None:
                self.order_command = next_command
            return self.order_command

        if self.active_trade_order.status == "canceled":
            self.order_command = ""

            next_command = self._on_closed_order(self.active_trade_order, market_data)

            if next_command is not None:
                self.order_command = next_command
            return self.order_command

    def _on_open_order(self, active_trade_order: TradeOrder, market_data):
        """
        This method is called when the active order is open. Should return  the next order command
        for active_order which should execute the order manager. Could be "cancel", "new" or "hold".
        This command is applied to self.active_trade_order. In case of the new order the active order should be should be
        created here.

        example of _on_open_order for FOK order based on number of trade order updates:

        if active_trade_order.update_requests_count >= self.max_order_updates \
                and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:
            return "cancel"
        return "hold"

        :return: str "cancel", "hold",  "new" or None
        """
        pass
        return "hold"

    def _on_closed_order(self, active_trade_order: TradeOrder, market_data=None):
        """
        This method is called when the active order was closed. Should return  the next order command
        for active_order which should execute the order manager. Optionally should close the active trade order and/or
        OWA order itself (if needed).
        This command is applied to self.active_trade_order.
        In case of the new order the active trade order should be created here.
        :return: str "cancel", "hold", "new" or None
        """
        self._close_active_order()
        self.close_order()
        return None  # return None because  Order Manager should not proceed the closed/canceled orders

    # def _on_canceled_order(self, active_trade_order: TradeOrder):
    #     """
    #     This method is called when the active order was canceled. Should return  the next order command
    #     for active_order which should execute the order manager. Optionally should close the active trade order and/or
    #     OWA order itself (if needed).
    #     This command is applied to self.active_trade_order.
    #     In case of the new order the active trade order should be created here.
    #     :return: str "cancel", "hold" , "new" or None
    #     """
    #     self._close_active_order()
    #     self.close_order()
    #     return None  # return None because  Order Manager should not proceed the closed/canceled orders

    def closed_trade_orders_report(self):
        """
        list of dict with TradeOrder reports for closed TradeOrders or None
        :return: list of dict with TradeOrder reports or empty list
        """
        report = list()

        for o in self.orders_history:
            report.append(o.report())

        return report

    def report(self):
        """
        create report dict for the all non callable fields of class
        :return: dict
        """

        report = dict((key, value) for key, value in self.__dict__.items()
                      if not callable(value) and not key.startswith('__') and not isinstance(value, list)
                      and not isinstance(value, dict))

        if len(self.tags) > 0:
            report["tags"] = " ".join(self.tags)

        return report

    def force_close(self):
        """
        force to send cancel command to order manager in order
        :return:
        """

        if self.status != "closed" and self.active_trade_order is not None and self.active_trade_order.status == "open":
            self._force_close = True
            self.order_command = "cancel"

        elif self.active_trade_order is not None and self.active_trade_order.status not in ("closed", "canceled"):
            self._force_close = True
            self.close_order()
            # self.order_command = "cancel"

    def _create_next_trade_order_for_remained_amount(self, price):
        """
        creates the next trade order for unfilled amount of Action order

        :param price: price of the new order
        :return:
        """

        amount = self.start_amount - self.filled_start_amount

        if amount <= 0:
            raise errors.OrderError("Bad new order amount {}".format(amount))

        order_params = (self.symbol, self.start_currency, amount,
                        self.dest_currency, price)

        if False not in order_params:
            # self.price = price
            order = TradeOrder.create_limit_order_from_start_amount(*order_params)  # type: TradeOrder
            order.supplementary.update({"parent_action_order": {"state": self.state}})
            return order

        else:
            raise errors.OrderError("Not all parameters for Order are set")

    def __str_status__(self):
        """
        Returns string respresentation of essential order informatin, Used in order manager logging
        """
        s = "{start_currency} -{side}-> {dest_currency} filled {filled}/{amount}" \
            .format(
                    start_currency=self.start_currency,
                    side=self.side,
                    dest_currency=self.dest_currency,
                    filled=self.filled,
                    amount=self.amount)
        return s

    def __str__(self):
        s = "ActionOrder " + self.__str_status__()
        return s

    def _snapshot(self):
        """
        returns snapshot of current ActionOrder
        """
        return ActionOrderSnapshot(
            self.symbol,
            self.amount,
            self.price,
            self.side,
            self.status,
            self.state,
            self.filled,
            getattr(getattr(self, "active_trade_order", {"id": None}), "id", None),
            getattr(getattr(self, "active_trade_order", {"status": None}), "status", None)
        )

