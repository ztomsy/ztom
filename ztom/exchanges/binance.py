from .. import exchange_wrapper as ew
from ..throttle import Throttle

class binance(ew.ccxtExchangeWrapper):

    PERIOD_SECONDS = 60
    REQUESTS_PER_PERIOD = 1200
    REQUEST_TYPE_WIGHTS = {
            "single": 1,
            "load_markets": 40,
            "fetch_tickers": 2,
            "fetch_ticker": 1,
            "fetch_order_book": 1,  # !!! if limit of order book will be more 100 - it will cost more
            "create_order": 1,
            "fetch_order": 1,
            "cancel_order": 1,
            "fetch_my_trades": 1,
            "fetch_balance": 5}

    def _patch_fetch_bids_asks(self, symbols=None, params={}):
        """
        fix for ccxt's method fetch_bids_asks for fetching single ticker from bids and asks
        """
        self._ccxt.load_markets()
        rawTickers = self._ccxt.publicGetTickerBookTicker(params)
        if type(rawTickers) != list:
            rawTickers=[rawTickers]
        return self._ccxt.parse_tickers(rawTickers, symbols)

    def __init__(self, exchange_id, api_key ="", secret ="" ):
        super(binance, self).__init__(exchange_id, api_key, secret )
        self.wrapper_id = "binance"

        # self._ccxt.fetch_bids_asks = self._patch_fetch_bids_asks

    def _fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None):
        '''
        redefine function to fetch different timeframes
        '''
        return self._ccxt.fetch_ohlcv(symbol, timeframe='1m', since=None, limit=None)

    def _fetch_tickers(self, symbol=None):
        if symbol is None:
            return self._ccxt.fetch_bids_asks(symbol)
        else:
            return self._patch_fetch_bids_asks(symbols=symbol, params={"symbol": self.markets[symbol]["id"]})

    def _create_order(self, symbol, order_type, side, amount, price=None):
        resp = self._ccxt.create_order(symbol, order_type, side, amount, price, {"newOrderRespType": "FULL"})
        resp["cost"] = float(resp["info"]["cummulativeQuoteQty"])
        return resp

    def _fetch_order(self, order):
            resp = self._ccxt.fetch_order(order.id, order.symbol)
            resp["cost"] = float(resp["info"]["cummulativeQuoteQty"])
            return resp

    def _cancel_order(self, order):
        resp = self._ccxt.cancel_order(order.id, order.symbol)
        return resp

    def get_exchange_wrapper_id(self):
        return self.wrapper_id


