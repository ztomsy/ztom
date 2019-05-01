from .. import exchange_wrapper as ew


class bittrex(ew.ccxtExchangeWrapper):
    """
    could be outdated! just for reference
    """

    def __init__(self, exchange_id, api_key ="", secret ="" ):
        super(bittrex, self).__init__(exchange_id, api_key, secret )
        self.wrapper_id = "bittrex"


    def _fetch_order_trades(self, order):

        resp = self._ccxt.fetch_order(order.id, order.symbol, {"type": order.side.upper()})
        # if "trades" in resp and len(resp["trades"]) > 0:
        # return resp

        return list([resp])

    def get_exchange_wrapper_id(self):
        return self.wrapper_id


