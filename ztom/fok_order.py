from ztom.trade_orders import TradeOrder
from ztom.action_order import ActionOrder
from ztom import core
import datetime


class FokOrder(ActionOrder):
    """
    implement basic FOK order by limiting maximum trade order updates and than cancel
    """

    def __init__(self, symbol, amount: float, price: float, side: str, cancel_threshold: float = 0.000001,
                 max_order_updates: int = 10, time_to_cancel: float = 0.0):

        super().__init__(symbol, amount, price, side, cancel_threshold, max_order_updates)
        self.time_to_cancel = time_to_cancel
        self.time_from_create = 0

    @classmethod
    def create_from_start_amount(cls, symbol, start_currency, amount_start, dest_currency, price,
                                 cancel_threshold: float = 0.000001, max_order_updates: int = 10,
                                 time_to_cancel: float = 0.0):

        order = super().create_from_start_amount(symbol, start_currency, amount_start, dest_currency, price,
                                                 cancel_threshold, max_order_updates)
        order.time_to_cancel = time_to_cancel
        return order

    def _init(self):
        super()._init()
        self.state = "fok"  # just to make things a little pretty
        self.active_trade_order.supplementary.update({"parent_action_order": {"state": self.state}})

    # redefine the _on_open_order checker to cancel active trade order if the number of order updates more
    # than max_order_updates
    def _on_open_order(self, active_trade_order: TradeOrder, market_data=None):

        now = datetime.datetime.now().timestamp()
        self.time_from_create = now - active_trade_order.timestamp_open.get("request_received", now)

        if self.time_to_cancel > 0.0:
            if self.time_from_create >= self.time_to_cancel \
                    and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:
                self.tags.append("#timeout")
                return "cancel"
            else:
                return "hold"

        if active_trade_order.update_requests_count >= self.max_order_updates \
                and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:
            return "cancel"
        return "hold"

    def __str_status__(self):
        s = "{start_currency} -{side}-> {dest_currency} filled {filled}/{amount} " \
            "upd {update_requests_count}/{max_order_updates} " \
            "time {time_from_create}/{time_to_cancel}"\
            .format(
                start_currency=self.start_currency,
                side=self.side,
                dest_currency=self.dest_currency,
                filled=self.active_trade_order.filled,
                amount=self.active_trade_order.amount,
                update_requests_count=self.active_trade_order.update_requests_count,
                max_order_updates=self.max_order_updates,
                time_from_create=self.time_from_create,
                time_to_cancel=self.time_to_cancel)
        return s


class FokThresholdTakerPriceOrder(FokOrder):
    """
    FOK order which is cancelled if the taker price drops by defined threshold
    """

    def __init__(self, symbol, amount: float, price: float, side: str,
                 cancel_threshold: float = 0.000001, max_order_updates: int = 10, time_to_cancel: float = 0.0,
                 taker_price_threshold: float = -0.01,
                 threshold_check_after_updates: int = 5):
        """

        :param symbol: pair symbol for order
        :param amount: amount of order in base currency
        :param price: in quote currency
        :param side: "buy" or "sell"
        :param cancel_threshold: cancel current trade order and set new only if the remained amount to fill  is greater than
        this threshold. This is for avoiding the situation of creating new order for less than minimun amount. Usually
        should be minimum order amount/value for the order's pair + commission.
             In ccxt: markets[symbol]["limits"]["amount"]["min"]
        :param max_order_updates: order updates before cancelling
        :param taker_price_threshold:  relative difference between the order's price and current taker price. Should be
        negative for changing price in a "bad" way
        :param threshold_check_after_updates: number of order's updates to start requesting ticker and check price
        threshold
        """

        super().__init__(symbol, amount, price, side, cancel_threshold, max_order_updates, time_to_cancel)

        self.taker_price_threshold = taker_price_threshold
        self.threshold_check_after_updates = threshold_check_after_updates

    @classmethod
    def create_from_start_amount(cls, symbol, start_currency, amount_start, dest_currency, price,
                                 cancel_threshold: float = 0.000001, max_order_updates: int = 10,
                                 time_to_cancel: float = 0.0,
                                 taker_price_threshold: float = -0.01, threshold_check_after_updates: int = 5):

        """
        :param symbol: pair symbol for order
        :param start_currency: start currency to trade from (available currency)
        :param amount_start: amount of start currency
        :param dest_currency: destination currency to trade to
        :param price: price
        :param side: side
        :param cancel_threshold: cancel current trade order and set new only if the remained amount to fill  is greater than
        this threshold. This is for avoiding the situation of creating new order for less than minimun amount. Usually
        should be minimum order amount/value for the order's pair + commission.
             In ccxt: markets[symbol]["limits"]["amount"]["min"]
        :param max_order_updates: order updates before cancelling
        :param taker_price_threshold:  relative difference between the order's price and current taker price. Should be
        negative for changing price in a "bad" way
        :param threshold_check_after_updates: number of order's updates to start requesting ticker and check price
        threshold
        """

        order = super().create_from_start_amount(symbol, start_currency, amount_start, dest_currency, price,
                                                 cancel_threshold, max_order_updates, time_to_cancel)

        order.taker_price_threshold = taker_price_threshold
        order.threshold_check_after_updates = threshold_check_after_updates

        return order

    def _init(self):
        super()._init()
        self.state = "fok"  # just to make things a little pretty
        self.active_trade_order.supplementary.update({"parent_action_order": {"state": self.state}})

    def _on_open_order(self, active_trade_order: TradeOrder, market_data=None):

        # cancel if have reached the maximum number of updates
        # if active_trade_order.update_requests_count >= self.max_order_updates \
        #         and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:
        #     return "cancel"

        if super()._on_open_order(active_trade_order, market_data) == "cancel":
            return "cancel"

        order_command = "hold"

        # here we check if we reached the number of updates where order's price should be checked against ticker
        if active_trade_order.update_requests_count > self.threshold_check_after_updates:

            # let's start requesting the tickers
            order_command = "hold tickers {symbol}".format(symbol=self.symbol)

            # on the first time we will not have the tickers, so just return the ticker requesting command
            if market_data is None:
                return order_command

            # than if market data is present - let's check if it's below or above the threshold
            try:
                current_taker_price = core.get_symbol_order_price_from_tickers(self.start_currency, self.dest_currency,
                                                                               {self.symbol: market_data[0]})["price"]
                if current_taker_price > 0:
                    price_diff = core.relative_target_price_difference(self.side, active_trade_order.price,
                                                                       current_taker_price)

                    if price_diff is not None and price_diff <= self.taker_price_threshold \
                            and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:

                        order_command = "cancel"

                        if "#below_threshold" not in self.tags:
                            self.tags.append("#below_threshold")
                        return order_command

            except Exception as e:
                order_command = "hold tickers {symbol}".format(symbol=self.symbol)

        return order_command
