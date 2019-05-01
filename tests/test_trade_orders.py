# -*- coding: utf-8 -*-
from .context import ztom
from ztom.trade_orders import *
import ccxt
import unittest


class TradeOrderTestSuite(unittest.TestCase):

    def test_trade_order_create(self):

        trade_order = TradeOrder("limit", "ETH/BTC", 1, "buy")

        self.assertEqual(trade_order.side, "buy")
        self.assertEqual(trade_order.symbol, "ETH/BTC")
        self.assertEqual(trade_order.amount, 1)

        self.assertEqual(trade_order.start_currency, "BTC")
        self.assertEqual(trade_order.dest_currency, "ETH")

        trade_order = TradeOrder("limit", "ETH/BTC", 1, "sell")

        self.assertEqual(trade_order.side, "sell")
        self.assertEqual(trade_order.symbol, "ETH/BTC")
        self.assertEqual(trade_order.amount, 1)

        self.assertEqual(trade_order.start_currency, "ETH")
        self.assertEqual(trade_order.dest_currency, "BTC")




    def test_create_limit_order_from_start_amount(self):

        symbol = "ETH/BTC"

        order = TradeOrder.create_limit_order_from_start_amount(symbol, "ETH", 1, "BTC", 0.08)
        self.assertEqual(order.side, "sell")
        self.assertEqual(order.amount, 1)
        self.assertEqual(order.amount_start, 1)
        self.assertEqual(order.id, "")

        order = TradeOrder.create_limit_order_from_start_amount(symbol, "BTC", 1, "ETH", 0.08)
        self.assertEqual(order.side, "buy")
        self.assertEqual(order.amount, 1/0.08)
        self.assertEqual(order.amount_start, 1)

        with self.assertRaises(OrderErrorSymbolNotFound) as cm:
            TradeOrder.create_limit_order_from_start_amount(symbol, "BTC", 1, "USD", 0.08)
        e = cm.exception
        self.assertEqual(type(e), OrderErrorSymbolNotFound)

        with self.assertRaises(OrderErrorBadPrice) as cm:
            TradeOrder.create_limit_order_from_start_amount(symbol, "BTC", 1, "ETH", 0)
        e = cm.exception
        self.assertEqual(type(e), OrderErrorBadPrice)

    def test_update_order_from_exchange_data(self):

        binance_responce = {'price': 0.07946, 'trades': None, 'side': 'sell', 'type': 'limit', 'cost': 0.003973,
                            'status': 'closed',
               'info': {'symbol': 'ETHBTC', 'orderId': 169675546, 'side': 'SELL', 'timeInForce': 'GTC',
                        'price': '0.07946000',
                        'status': 'FILLED', 'clientOrderId': 'SwstQ0eZ0ZJKr2y4uPQin2', 'executedQty': '0.05000000',
                        'origQty': '0.05000000', 'type': 'LIMIT', 'transactTime': 1529586827997}, 'filled': 0.05,
               'timestamp': 1529586827997, 'fee': None, 'symbol': 'ETH/BTC', 'id': '169675546',
               'datetime': '2018-06-21T13:13:48.997Z', 'lastTradeTimestamp': None, 'remaining': 0.0, 'amount': 0.05}

        symbol = "ETH/BTC"

        order = TradeOrder.create_limit_order_from_start_amount(symbol, "ETH", 1, "BTC", 0.08)

        order.update_order_from_exchange_resp(binance_responce)
        for field in order._UPDATE_FROM_EXCHANGE_FIELDS:
            if field in binance_responce and binance_responce[field] is not None:
                self.assertEqual(binance_responce[field], getattr(order, field))

        order.update_order_from_exchange_resp(None)
        self.assertEqual(2, order.update_requests_count)

    def test_offline_sell_order(self):

        ex = ztom.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_binance.json")

        self.assertEqual(len(ex._offline_order["updates"]), 4)
        self.assertEqual(ex._offline_order["create"]["id"], "170254693")

        ex.load_markets()
        ex.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.05 / 3, "BTC", 0.077212)

        order_resp = ex.place_limit_order(order)
        order.update_order_from_exchange_resp(order_resp)

        self.assertEqual(order.filled, 0)
        self.assertEqual(order.status, "open")

        order_resps = dict()
        order_resps["updates"] = list()

        tick = 0
        while order.status != "closed" and order.status != "canceled":
            update_resp = ex.get_order_update(order)
            order.update_order_from_exchange_resp(update_resp)
            order_resps["updates"].append(update_resp)
            tick += 1

        self.assertEqual(len(order_resps["updates"]), 4)
        self.assertEqual(order.status, "closed")
        self.assertEqual(order.filled, 0.016)

        self.assertEqual(order.filled_start_amount, order.filled)
        self.assertEqual(order.filled_dest_amount, order.cost)

        for idx, val in enumerate(order_resps["updates"]):
            self.assertEqual(val["filled"], ex._offline_order["updates"][idx]["filled"])

    def test_offline_buy_order(self):

        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_buy.json")

        ex.load_markets()
        ex.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "BTC", 0.05, "ETH",
                                                                     0.07381590480571001)

        order_resp = ex.place_limit_order(order)
        order.update_order_from_exchange_resp(order_resp)

        order_resps = dict()
        order_resps["updates"] = list()

        tick = 0
        while order.status != "closed" and order.status != "canceled":
            update_resp = ex.get_order_update(order)
            order.update_order_from_exchange_resp(update_resp)
            order_resps["updates"].append(update_resp)
            tick += 1

        # self.assertEqual(len(order_resps["updates"]), 4)
        self.assertEqual(order.status, "closed")
        self.assertEqual(order.filled, order.filled_dest_amount)

        self.assertEqual(order.filled_start_amount, order.cost)
        self.assertEqual(order.filled_dest_amount, order.filled)

        self.maxDiff = None
        # self.assertListEqual(order_resps["updates"], ex._offline_order["updates"])
        for idx, val in enumerate(order_resps["updates"]):
            self.assertEqual(val["filled"], ex._offline_order["updates"][idx]["filled"])

    def test_offline_sell_multi(self):

        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")

        ex.load_markets()
        ex.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)

        order_resp = ex.place_limit_order(order)
        order.update_order_from_exchange_resp(order_resp)

        order_resps = dict()
        order_resps["updates"] = list()

        tick = 0
        while order.status != "closed" and order.status != "canceled":
            update_resp = ex.get_order_update(order)
            order.update_order_from_exchange_resp(update_resp)
            order_resps["updates"].append(update_resp)

            self.assertEqual(order.filled_start_amount, order.filled)
            self.assertEqual(order.filled_dest_amount, order.cost)

            tick += 1

        # self.assertEqual(len(order_resps["updates"]), 4)
        self.assertEqual(order.status, "closed")

        self.assertEqual(order.filled_start_amount, order.filled)
        self.assertEqual(order.filled_dest_amount, order.cost)

        for idx, val in enumerate(order_resps["updates"]):
            self.assertEqual(val["filled"], ex._offline_order["updates"][idx]["filled"])

        trades = ex.get_trades(order)

        self.assertListEqual(trades, order.trades)

    def test_fees_from_trades(self):
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin") # type: ztom.ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")

        ex.load_markets()
        ex.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 5, "BTC",
                                                                     0.06633157807472399)
        order.id = 1

        resp = {
            "status": "closed",

            "trades":
                [
                    {"amount": 1, "price": 0.06633, "order": 1, 'fee': {'cost': 0.001, 'currency': 'ETH'}},
                    {"amount": 2, "price": 0.06633, "order": 1, 'fee': {'cost': 0.002, 'currency': 'ETH'}},
                    {"amount": 1, "price": 0.06633, "order": 1, 'fee': {'cost': 0.001, 'currency': 'ETH'}}
                ]

        }
        order.update_order_from_exchange_resp(resp)

        fees = ex.fees_from_order_trades(order)

        self.assertEqual(fees["ETH"]["amount"], 0.004)
        self.assertEqual(fees["BTC"]["amount"], 0.0)

        # fees in dest currency
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 5, "BTC",
                                                                     0.06633157807472399)
        order.id = 1

        resp = {
            "status": "closed",

            "trades":
                [
                    {"amount": 1, "price": 0.06633, "order": 1, 'fee': {'cost': 0.0001, 'currency': 'BTC'}},
                    {"amount": 2, "price": 0.06633, "order": 1, 'fee': {'cost': 0.0002, 'currency': 'BTC'}},
                    {"amount": 1, "price": 0.06633, "order": 1, 'fee': {'cost': 0.0001, 'currency': 'BTC'}}
                ]

        }
        order.update_order_from_exchange_resp(resp)

        fees = ex.fees_from_order_trades(order)

        self.assertEqual(fees["ETH"]["amount"], 0.0)
        self.assertEqual(fees["BTC"]["amount"], 0.0004)

        # 3rd currency
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 5, "BTC",
                                                                     0.06633157807472399)
        order.id = 1

        resp = {
            "status": "closed",

            "trades":
                [
                    {"amount": 1, "price": 0.06633, "order": 1, 'fee': {'cost': 1, 'currency': 'BNB'}},
                    {"amount": 2, "price": 0.06633, "order": 1, 'fee': {'cost': 2, 'currency': 'BNB'}},
                    {"amount": 1, "price": 0.06633, "order": 1, 'fee': {'cost': 1, 'currency': 'BNB'}}
                ]

        }
        order.update_order_from_exchange_resp(resp)

        fees = ex.fees_from_order_trades(order)

        self.assertEqual(fees["ETH"]["amount"], 0.0)
        self.assertEqual(fees["BTC"]["amount"], 0.000)
        self.assertEqual(fees["BNB"]["amount"], 4)

        # no trades
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 5, "BTC",
                                                                     0.06633157807472399)
        order.id = 1

        resp = {
            "status": "closed"
        }

        order.update_order_from_exchange_resp(resp)

        fees = ex.fees_from_order_trades(order)

        self.assertEqual(fees["ETH"]["amount"], 0.0)
        self.assertEqual(fees["BTC"]["amount"], 0.0)

    def test_total_amounts_from_trades(self):

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        order.id = 1

        trades = [
            {"amount": 1 , "price": 1, "order": 1},
            {"amount": 2, "price": 2, "order": 1},
            {"amount": 3, "price": 4, "order": 1},
            {"amount": 1, "price": 0.123456789, "order": 1}
            ]

        total = order.total_amounts_from_trades(trades)

        self.assertEqual(total["amount"], 7)
        self.assertEqual(total["cost"], 17.123456789)
        self.assertEqual(total["price"], 17.123456789 / 7)

    def test_report(self):

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        order.id = 1

        trades = [
            {"amount": 1 , "price": 1, "order": 1},
            {"amount": 2, "price": 2, "order": 1},
            {"amount": 3, "price": 4, "order": 1},
            {"amount": 1, "price": 0.123456789, "order": 1}
            ]

        order.update_order_from_exchange_resp({"trades": trades})

        report = order.report()

        self.assertEqual(order.amount, report["amount"])
        self.assertListEqual(order.trades, report["trades"])







if __name__ == '__main__':
    unittest.main()