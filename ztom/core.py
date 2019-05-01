# for  basic exchange operations
import math
from ztom import errors

def get_trade_direction_to_currency(symbol: str, dest_currency: str):
    cs = symbol.split("/")

    if cs[0] == dest_currency:
        return "buy"

    elif cs[1] == dest_currency:
        return "sell"

    else:
        return False


def get_symbol(c1: str, c2: str, markets: dict):
    if c1 + "/" + c2 in markets:
        a = c1 + "/" + c2
    elif c2 + "/" + c1 in markets:
        a = c2 + "/" + c1
    else:
        return False
    return a


def get_order_type(source_cur: str, dest_cur: str, symbol: str):

    if source_cur + "/" + dest_cur == symbol:
        a = "sell"
    elif dest_cur + "/" + source_cur == symbol:
        a = "buy"
    else:
        a = False

    return a


def get_symbol_order_price_from_tickers(source_cur: str, dest_cur: str, tickers: dict):
    """
    returns dict with taker side and price for converting currency source_cur to dest_cur, using the ticker(-s) dict

    :param source_cur: str
    :param dest_cur:  str
    :param tickers: ticker (-s) dict {"sym/bol":{"ask":value, "bid":value}}
    :return: dict of {"symbol": symbol,
                      "order_type": "buy" or "sell",
                      "price_type": "ask" or "bid",
                      "price": price,
                      "maker_price_type": "bid" or "ask",
                      "maker_price":val}

    """
    if source_cur + "/" + dest_cur in tickers:
        symbol = source_cur + "/" + dest_cur
        order_type = "sell"
        price_type = "bid"

        maker_price_type = "ask"

    elif dest_cur + "/" + source_cur in tickers:
        symbol = dest_cur + "/" + source_cur
        order_type = "buy"
        price_type = "ask"

        maker_price_type = "bid"

    else:
        return None

    if symbol in tickers:
        price = tickers[symbol][price_type] if price_type in tickers[symbol] and \
                                               tickers[symbol][price_type] > 0 else None

        maker_price = tickers[symbol][maker_price_type] if maker_price_type in tickers[symbol] and \
                                                           tickers[symbol][maker_price_type] > 0 else None

    else:
        price = None

    a = dict({"symbol": symbol, "order_type": order_type, "price_type": price_type, "price": price,
              "maker_price_type": maker_price_type, "maker_price": maker_price})
    return a


def price_to_precision(fee, precision=8):
    return float(('{:.' + str(precision) + 'f}').format(float(fee)))


def amount_to_precision(amount, precision=0):
    if precision > 0:
        decimal_precision = math.pow(10, precision)
        return math.trunc(amount * decimal_precision) / decimal_precision
    else:
        return float(('%d' % amount))


def relative_target_price_difference(side: str, target_price: float, current_price: float) -> float:
    """
    Returns the relative difference of current_price from target price. Negative vallue could be considered as "bad"
    difference, positive as "good".

    For "sell" order: relative_target_price_difference = (target_price / current_price) - 1
    For "buy" orders: relative_target_price_difference = (current_price / target_price) - 1

    Means that for "buy" order if the price is greater that the target price - the relative difference will be negative.
    For "sell" orders: if the price will be less than target price - the rel. difference will be negative.

    :param side: side of the order to compare
    :param target_price: the price to compare with
    :param current_price: the price which is being compared to target price

    :return: relative difference between the current_price and target_price regarding the order's side or None
    """

    result = None

    if side.lower() == "sell":
        result = (current_price / target_price) - 1
        return result

    if side.lower() == "buy":
        result = 1 - (current_price / target_price)
        return result

    raise (ValueError("Wrong side of the order {}".format(side)))


def convert_currency(start_currency, start_amount, dest_currency: str = None, symbol: str = None, price: float = None,
                     ticker: dict = None, side: str = None, taker: bool = True):
    """
    :returns the amount of :param dest_currency: which could be gained if converted from :param start_amount:
    of :param start_currency:

    :param start_currency: currency to convert from
    :param start_amount: amount of start_currency
    :param dest_currency: currency to convert to
    :param symbol: symbol of pair within the conversion
    :param price: if price is not set, it would be taken from ticker (by default for TAKER price)
    :param side: if symbol is not set, side "buy" or "sell" should be provided
    :param ticker: content of dict returned by fetch_tickers for symbol. ex. fetch_tickers()["ETH/BTC"]
    :param taker: set to False is maker price should be taken from ticker

    """

    if symbol is None:
        if ticker is None:
            raise (Exception("No symbol or ticker provided"))
        if "symbol" in ticker:
            symbol = ticker["symbol"]
        else:
            raise (errors.TickerError("No Symbol in Ticker"))

    if side is None:
        side = get_trade_direction_to_currency(symbol, dest_currency)

        if not side:
            raise (errors.TickerError("Symbol not contains both currencies"))

    if price is None:

        if (taker and side == "buy") or \
                (not taker and side == "sell"):
            price = float(ticker["ask"])

        elif (taker and side == "sell") or \
                (not taker and side == "buy"):
            price = float(ticker["bid"])
        else:
            raise (Exception("Wrong side and taker/maker parameters"))

    if price == 0:
        raise (Exception("Zero price"))

    dest_amount = 0.0

    if side.lower() == "sell":
        dest_amount = start_amount * price

    if side.lower() == "buy":
        dest_amount = start_amount / price

    return dest_amount


def ticker_price_for_dest_amount(side: str, start_amount: float, dest_amount: float):
    """
    :return: price for order to convert start_amount to dest_amount considering order's side
    """

    if dest_amount == 0 or start_amount == 0:
        raise ValueError("Zero start ot dest amount")

    if side is None:
        raise ValueError("RecoveryManagerError: Side not set")
    else:
        side = side.lower()

    if side == "buy":
        return start_amount / dest_amount

    if side == "sell":
        return dest_amount / start_amount

    return False
