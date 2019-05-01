import itertools
import math


class Depth:
    """
    Represents depth calculation in order book
    """

    def __init__(self, total_quantity, total_price, depth, currency="quote", filled_share=1):
        """

        :param total_quantity: total quantity of :param currency: filled within order book
        :param total_price: average price
        :param depth: final level of orderbook where amount is being filled
        :param currency: result currency
        :param filled_share: filled quantity / amount
        """
        self.total_quantity = total_quantity
        self.total_price = total_price
        self.depth = depth
        self.currency = currency
        self.filled_share = filled_share

    def __eq__(self, other):

        return math.isclose(self.total_quantity, other.total_quantity, rel_tol=1e-8) and \
               math.isclose(self.total_price, other.total_price, rel_tol=1e-8) and \
               self.depth == other.depth and \
               self.currency == other.currency and \
               self.filled_share == other.filled_share

    def __str__(self):

        return "Depth: total_qty %s, total_price: %s, depth: %s, currency: %s, filled: %s" % (self.total_quantity,
                                                                                              self.total_price,
                                                                                              self.depth,
                                                                                              self.currency,
                                                                                              self.filled_share)
    __repr__ = __str__

class Order:
    def __init__(self, price, quantity):
        self.quantity = float(quantity) if quantity else 0.0
        self.price = float(price) if price else 0.0

    def __str__(self):
        return 'Order[p:%s q:%s]' % (self.price, self.quantity)


class OrderBook:
    def __init__(self, symbol, asks, bids):
        self.symbol = symbol

        self.asks = sorted(list(map(lambda x: Order(x[0], x[1]), asks)), key=lambda x: x.price)
        self.bids = sorted(list(map(lambda x: Order(x[0], x[1]), bids)), key=lambda x: x.price, reverse=True)

    def __str__(self):
        asks_str = '\n'.join(list(map(lambda o: str(o), self.asks)))
        bids_str = '\n'.join(list(map(lambda o: str(o), self.bids)))
        return ('OrderBook['
                '\tAsks:\n'
                '\t\t%s'
                '\tBids:\n'
                '\t\t%s') % (asks_str, bids_str)

    __repr__ = __str__

    @staticmethod
    def csv_header():
        return ['ask', 'ask-qty', 'bid', 'bid-qty']

    def to_csv(self, order1, order2, precision, as_list=False):
        template = '{0:.%sf}' % precision
        quantity1 = template.format(order1.quantity) or ''
        price1 = template.format(order1.price) or ''
        quantity2 = template.format(order2.quantity) if order2 is not None else ''
        price2 = template.format(order2.price) if order2 is not None else ''
        if not as_list:
            return '%s, %s, %s, %s' % (quantity1, price1, quantity2, price2)
        else:
            return list([price1, quantity1, price2, quantity2])

    # use as_list=True if return as list

    def csv_rows(self, precision, as_list=False):
        table = itertools.zip_longest(self.asks, self.bids)
        rows = list(map(lambda pair: self.to_csv(pair[0], pair[1], precision, as_list), table))
        return rows

    #
    #

    def get_depth(self, amount, direction, currency="base"):
        """
        get order book depth for taker positions, qty and average price for amount of base or quote currency amount
        for buy or sell side in case of return None if not enough amount or Depth instance


        :param amount:
        :param direction:
        :param currency:
        :return: Depth object
        """
        order_fills = self.asks if direction == 'buy' else self.bids

        if currency == "base":  # we collect base currency from setted quote
            amount = amount
            add_amount = lambda x: x.quantity  # plain base quantity in orderbook
            add_total = lambda x: x.quantity * x.price  # base amount
            ob_qty = lambda x: x.quantity  # base amount
            currency="quote"

        elif currency == "quote":
            add_amount = lambda x: x.quantity * x.price  # we collect quote currency - so multiplying
            add_total = lambda x: x.quantity
            ob_qty = lambda x: x.quantity / x.price  # base from quote
            currency = "base"

        else:
            return None

        amount_filled = 0
        total_quantity = 0
        depth = 0

        while depth < len(order_fills) and amount_filled < amount:

            quantity = add_amount(order_fills[depth])

            if amount_filled + quantity >= amount:
                # quantity = amount - amount_filled
                # order_fills[depth].quantity = ob_qty(Order(order_fills[depth].price, quantity))

                total_quantity += add_total( Order(order_fills[depth].price, ob_qty(Order(order_fills[depth].price, amount - amount_filled))))
                amount_filled = amount

            else:
                amount_filled += quantity
                total_quantity += add_total(order_fills[depth])

            depth += 1

        # if amount_filled < amount:
        #
        # else:

        if direction == "buy":
            price = amount_filled / total_quantity  # were collecting total_qty in base from amount quote

        if direction == "sell":
            price = total_quantity / amount_filled  # were collecting total_qty in base from amount quote

        return Depth(total_quantity, price, depth, currency, amount_filled / amount)

    #
    # get trade direction to receive  dest_currency
    #
    def get_trade_direction_to_currency(self, dest_currency):
        cs = self.symbol.split("/")

        if cs[0] == dest_currency:
            return "buy"

        elif cs[1] == dest_currency:
            return "sell"

        else:
            return False

    #
    # get depth for destination currency for initial amount of available currency in symbol and trade direction side
    #
    def get_depth_for_destination_currency(self, init_amount, dest_currency):

        direction = self.get_trade_direction_to_currency(dest_currency)

        if direction == "buy":
            return self.get_depth(init_amount, "buy", "quote")

        if direction == "sell":
            return self.get_depth(init_amount, "sell", "base")

        return False

    #
    # get orderbook price and result for trade side (buy or sell) of initial amount of start currency
    # if buy - on start we have quote currency  and result will be for base
    # if sell - we have base currency and result in quote
    #
    def get_depth_for_trade_side(self, start_amount:float, side:str):

        if side == "buy":
            return self.get_depth(start_amount, "buy", "quote")

        if side == "sell":
            return self.get_depth(start_amount, "sell", "base")

        return False
