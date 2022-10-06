# -*- coding: utf-8 -*-

from .context import ztom

import unittest
import copy
import datetime
import time


class ExchageWrapperTestSuite(unittest.TestCase):

    def test_create_wrapped(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        self.assertEqual(exchange.get_exchange_wrapper_id(), "binance")
        self.assertEqual(exchange._ccxt.id, "binance")

    def test_create_wrapped2(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        self.assertEqual(exchange.get_exchange_wrapper_id(), "kucoin")
        self.assertEqual(exchange._ccxt.id, "kucoin")

    def test_create_generic(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("bitfinex")
        self.assertEqual(exchange.get_exchange_wrapper_id(), "generic")
        self.assertEqual(exchange._ccxt.id, "bitfinex")

    @unittest.skip
    def test_online_fetch_ticker_wrapped(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        self.assertEqual(exchange.fetch_tickers()["ETH/BTC"]["last"], None)

    @unittest.skip
    def test_fetch_ticker_generic(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        self.assertIsNot(exchange.fetch_tickers()["ETH/BTC"]["last"], None)

    def test_load_markets_from_file(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        markets = exchange.load_markets_from_json_file("test_data/markets_binance.json")

        self.assertEqual(markets["ETH/BTC"]["active"], True)

    def test_load_tickers_from_csv(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        tickers = exchange.load_tickers_from_csv("test_data/tickers_binance.csv")

        self.assertEqual(len(tickers), 3)
        self.assertEqual(tickers[2]["ETH/BTC"]["ask"], 0.082975)

    def test_init_offline_mode(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")

        self.assertEqual(exchange.offline, True)
        self.assertEqual(exchange._offline_tickers[2]["ETH/BTC"]["ask"], 0.082975)
        self.assertEqual(exchange._offline_markets["ETH/BTC"]["active"], True)

    def test_offline_tickers_fetch(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        tickers = list()
        for _ in exchange._offline_tickers:
            tickers.append(exchange._offline_fetch_tickers())

        self.assertEqual(len(tickers), 3)
        self.assertEqual(tickers[0]["ETH/BTC"]["bidVolume"], 10.011)
        self.assertEqual(tickers[1]["ETH/BTC"]["bidVolume"], 10.056)
        self.assertEqual(tickers[2]["ETH/BTC"]["bidVolume"], 10)

        with self.assertRaises(ztom.ExchangeWrapperOfflineFetchError) as cm:
            exchange._offline_fetch_tickers()

        e = cm.exception
        self.assertEqual(type(e), ztom.ExchangeWrapperOfflineFetchError)

    def test_offline_load_markets(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        markets = exchange._offline_load_markets()
        self.assertEqual(markets["ETH/BTC"]["active"], True)

        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")

        with self.assertRaises(ztom.ExchangeWrapperOfflineFetchError) as cm:
            exchange._offline_load_markets()

        e = cm.exception
        self.assertEqual(type(e), ztom.ExchangeWrapperOfflineFetchError)

    def test_offline_mode(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")

        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()

        self.assertEqual(tickers["ETH/BTC"]["bidVolume"], 10.011)
        self.assertEqual(len(tickers), len(markets))

    def test_get_results_from_trades(self):
        """
        getting trades from file
        """
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")  # type: ztom.ccxtExchangeWrapper
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                                  "test_data/orders_kucoin_multi.json")

        exchange.offline_load_trades_from_file("test_data/orders_trades_kucoin.json")

        # sell order
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)

        om = ztom.OrderManagerFok(order)
        om.fill_order(exchange)

        result = exchange.get_trades_results(order)
        self.assertEqual(result["filled"], 0.5)
        self.assertEqual(result["cost"], 0.03685088)
        self.assertEqual(result["dest_amount"], 0.03685088)
        self.assertEqual(result["src_amount"], 0.5)
        self.assertGreaterEqual(result["price"], 0.03685088 / 0.5)

        order.side = "buy"

        result = exchange.get_trades_results(order)
        self.assertEqual(result["filled"], 0.5)
        self.assertEqual(result["cost"], 0.03685088)
        self.assertEqual(result["dest_amount"], 0.5)
        self.assertEqual(result["src_amount"], 0.03685088)
        self.assertGreaterEqual(result["price"], 0.03685088 / 0.5)

    def test_precision(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        exchange.load_markets()
        symbol = "ETH/BTC"  # amount precision =3, price_precision = 6

        self.assertEqual(1.399, exchange.amount_to_precision(symbol, 1.399))
        self.assertEqual(1.399, exchange.amount_to_precision(symbol, 1.3999))

        self.assertEqual(1.399, exchange.price_to_precision(symbol, 1.399))
        self.assertEqual(1.3999, exchange.price_to_precision(symbol, 1.3999))
        self.assertEqual(1.123457, exchange.price_to_precision(symbol, 1.123456789))

        exchange.markets["ETH/BTC"] = None  # default precisions for price and amount 8

        self.assertEqual(1.12345678, exchange.amount_to_precision(symbol, 1.123456789))
        self.assertEqual(1.12345678, exchange.amount_to_precision(symbol, 1.123456789))

    @unittest.skip
    def test_precision_online(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.load_markets()
        symbol = "GNT/ETH"

        self.assertEqual(exchange.amount_to_precision(symbol, 1.3999999),
                         exchange._ccxt.amount_to_precision(symbol, 1.3999999))

        self.assertEqual(exchange.price_to_precision(symbol, 1.123456789),
                         exchange._ccxt.price_to_precision(symbol, 1.123456789)
                         )

    def test_create_order_book_array_from_ticker(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        exchange.load_markets()
        exchange.fetch_tickers()

        ob_array = exchange._create_order_book_array_from_ticker(exchange.tickers["ETH/USDT"])
        self.assertEqual(ob_array["asks"], [[682.82, 99999999]])
        self.assertEqual(ob_array["bids"], [[682.5, 99999999]])

    def test_create_order_offline_data(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        exchange.load_markets()
        exchange.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)

        o = exchange.create_order_offline_data(order, 10)

        self.assertEqual(exchange.price_to_precision(order.symbol, order.price),
                         exchange.price_to_precision(order.symbol, o["create"]["price"]))

        self.assertEqual(exchange.amount_to_precision(order.symbol, order.amount),
                         exchange.amount_to_precision(order.symbol, o["create"]["amount"]))

        self.assertEqual(exchange.price_to_precision(order.symbol, order.amount_dest),
                         exchange.price_to_precision(order.symbol, o["updates"][-1]["cost"]))

        exchange._offline_order = o
        exchange._offline_trades = o["trades"]

        om = ztom.OrderManagerFok(order)
        om.fill_order(exchange)

        self.assertEqual(0.5, order.filled)

        result = exchange.get_trades_results(order)
        # self.assertEqual(result["filled"], 0.5)
        self.assertEqual(result["cost"], exchange.price_to_precision(order.symbol, order.cost))
        self.assertEqual(result["dest_amount"], exchange.price_to_precision(order.symbol, order.cost))
        # self.assertEqual(result["src_amount"], 0.5)
        self.assertGreaterEqual(result["price"], order.price)

    def test_create_order_offline_data_zero_fill_updates(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance") # type: ztom.ccxtExchangeWrapper
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        exchange.load_markets()
        exchange.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        # zero_fill_updates > 0 < updates_to_fill
        o = exchange.create_order_offline_data(order, 10, 5)

        for i in range(0, 5):
            self.assertEqual(0, o["updates"][i]["filled"])
            self.assertEqual(0, o["updates"][i]["cost"])
            self.assertListEqual(list(), o["updates"][i]["trades"])

        self.assertEqual(0.1, o["updates"][5]["filled"])
        self.assertEqual(0.2, o["updates"][6]["filled"])
        self.assertEqual(0.3, o["updates"][7]["filled"])
        self.assertEqual(0.4, o["updates"][8]["filled"])
        self.assertEqual(0.5, o["updates"][9]["filled"])

        exchange._offline_order = o
        exchange._offline_trades = o["trades"]

        self.assertEqual(len(o["updates"]), 10)

        om = ztom.OrderManagerFok(order)
        om.fill_order(exchange)

        self.assertEqual(0.5, order.filled)

        result = exchange.get_trades_results(order)

        self.assertEqual(result["cost"], exchange.price_to_precision(order.symbol, order.cost))
        self.assertEqual(result["dest_amount"], exchange.price_to_precision(order.symbol, order.cost))
        self.assertGreaterEqual(result["price"], order.price)

        # zero_fill_updates == updates_to_fill
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        # zero_fill_updates > 0 < updates_to_fill
        o = exchange.create_order_offline_data(order, 10, 10)

        self.assertEqual(len(o["updates"]), 10)

        for u in o["updates"]:
            self.assertEqual(0, u["filled"])
            self.assertEqual(0, u["cost"])
            self.assertListEqual(u["trades"], list())

        # zero_fill_updates == updates_to_fill
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        # zero_fill_updates > updates_to_fill
        o = exchange.create_order_offline_data(order, 10, 10)

        self.assertEqual(len(o["updates"]), 10)

        for u in o["updates"]:
            self.assertEqual("open", u["status"])
            self.assertEqual(0, u["filled"])
            self.assertEqual(0, u["cost"])
            self.assertListEqual(u["trades"], list())

        # zero_fill_updates = 0
        o = exchange.create_order_offline_data(order, 10, 0)

        self.assertEqual(len(o["updates"]), 10)
        for u in o["updates"]:
            self.assertLess(0, u["filled"])

    def test_multiple_offline_orders(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        exchange.load_markets()
        exchange.fetch_tickers()

        # at this point order has not id, because order should receive it's id from the exchange
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)

        int_order_id = exchange.add_offline_order_data(order, 1)

        self.assertEqual(0, exchange._offline_orders_data[int_order_id]["_offline_order_update_index"])
        self.assertEqual("open", exchange._offline_orders_data[int_order_id]["_offline_order"]["create"]["status"])
        self.assertEqual(int_order_id, order.internal_id)

        order2 = ztom.TradeOrder.create_limit_order_from_start_amount("USD/RUB", "RUB", 70, "USD", 70)
        exchange.add_offline_order_data(order2, 4)

        resp_order1 = exchange.place_limit_order(order)
        resp_order2 = exchange.place_limit_order(order2)

        self.assertEqual(resp_order1["amount"], order.amount)
        self.assertEqual(resp_order2["amount"], order2.amount)

        resp1 = exchange.get_order_update(order)
        resp2 = exchange.get_order_update(order2)
        resp2 = exchange.get_order_update(order2)
        resp2 = exchange.get_order_update(order2)

        order.update_order_from_exchange_resp(resp1)
        order2.update_order_from_exchange_resp(resp2)
        order2.update_order_from_exchange_resp(resp2)

        self.assertEqual(1, exchange._offline_orders_data[order.internal_id]["_offline_order_update_index"])
        self.assertEqual(3, exchange._offline_orders_data[order2.internal_id]["_offline_order_update_index"])

        self.assertEqual("closed", order.status)
        self.assertEqual(0.5, order.filled)

        self.assertEqual("open", order2.status)

        resp2 = exchange.cancel_order(order2)
        order2.update_order_from_exchange_resp(resp2)
        self.assertEqual("canceled", order2.status)
        self.assertEqual(3 / 4, order2.filled)

    def test_offline_get_trades_from_order_offline_data(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance") # type: ztom.ccxtExchangeWrapper
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        exchange.load_markets()
        exchange.fetch_tickers()

        # at this point order has not id, because order should receive it's id from the exchange
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)

        exchange.add_offline_order_data(order, 2)
        resp_order1 = exchange.place_limit_order(order)

        self.assertNotIn("trades", resp_order1)

        resp = exchange.get_order_update(order)

        self.assertIn("trades", resp)
        self.assertEqual(0.5 / 2, resp["trades"][0]["amount"])


        resp = exchange.get_order_update(order)

        self.assertEqual(2* (0.5 / 2), resp["filled"])

        self.assertIn("trades", resp)
        self.assertEqual(0.5 / 2, resp["trades"][0]["amount"])
        self.assertEqual(0.5 / 2, resp["trades"][1]["amount"])

        # check trades after order is filled
        resp_trades = exchange.get_trades(order)
        self.assertEqual(0.5 / 2, resp_trades[0]["amount"])
        self.assertEqual(0.5 / 2, resp_trades[1]["amount"])

        resp_trades = exchange.get_trades(order)
        self.assertEqual(0.5 / 2, resp_trades[0]["amount"])
        self.assertEqual(0.5 / 2, resp_trades[1]["amount"])

    def test_get_trades_if_not_in_order_data(self):
        """
        in this case trades are not returned via get_trades method. This mode for exchange wrapper could be set by
        exchange.trades_in_offline_order_update = False
        """
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance") # type: ztom.ccxtExchangeWrapper
        self.assertEqual(True, exchange.trades_in_offline_order_update)
        exchange.trades_in_offline_order_update = False

        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")
        exchange.load_markets()
        exchange.fetch_tickers()

        # at this point order has not id, because order should receive it's id from the exchange
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)

        exchange.add_offline_order_data(order, 2)
        resp_order1 = exchange.place_limit_order(order)

        self.assertNotIn("trades", resp_order1)

        resp = exchange.get_order_update(order)
        order.update_order_from_exchange_resp(resp)

        self.assertNotIn("trades", resp)
        self.assertEqual(0, len(order.trades))

        resp = exchange.get_order_update(order)
        order.update_order_from_exchange_resp(resp)

        self.assertEqual(2* (0.5 / 2), resp["filled"])
        self.assertNotIn("trades", resp)

        # check trades after order is filled
        resp_trades = exchange.get_trades(order)
        self.assertEqual(0.5 / 2, resp_trades[0]["amount"])
        self.assertEqual(0.5 / 2, resp_trades[1]["amount"])

        resp_trades = exchange.get_trades(order)
        self.assertEqual(0.5 / 2, resp_trades[0]["amount"])
        self.assertEqual(0.5 / 2, resp_trades[1]["amount"])

        # update order with the trades responce
        order.update_order_from_exchange_resp({"trades": resp_trades})
        self.assertEqual(2, len(order.trades))

        results_from_trades = exchange.get_trades_results(order)

        self.assertEqual(order.filled, results_from_trades["filled"])


    def test_offline_order_book_fetch(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")

        offline_order_books = dict()
        offline_order_books["USD/RUR"] = list()
        offline_order_books["USD/RUR"].append({"bids": [[70, 1.1], [69, 2.1], [60, 3.1]],
                                               "asks": [[71, 1.2], [72, 2.2], [73, 3.2]]})

        offline_order_books["USD/RUR"].append({"bids": [[70, 4.1], [69, 5.1], [60, 6.1]],
                                               "asks": [[71, 4.2], [72, 5.2], [73, 6.2]]})

        offline_order_books["USD/RUR"].append({"bids": [[70, 7.1], [69, 8.1], [60, 9.1]],
                                               "asks": [[71, 7.2], [72, 8.2], [73, 9.2]]})

        offline_order_books["EUR/RUR"] = list()
        offline_order_books["EUR/RUR"].append({"bids": [[75, 11.1], [74, 12.1], [70, 13.1]],
                                               "asks": [[76, 11.2], [77, 12.2], [78, 13.2]]})

        offline_order_books["EUR/RUR"].append({"bids": [[75, 14.1], [74, 15.1], [70, 16.1]],
                                               "asks": [[76, 14.2], [77, 15.2], [78, 16.2]]})

        offline_order_books["EUR/RUR"].append({"bids": [[76, 17.1], [73, 18.1], [70, 19.1]],
                                               "asks": [[72, 17.2], [73, 18.2], [74, 19.2]]})

        exchange._offline_order_books = copy.copy(offline_order_books)

        self.assertDictEqual(offline_order_books["USD/RUR"][0], exchange.fetch_order_book("USD/RUR"))
        self.assertDictEqual(offline_order_books["USD/RUR"][1], exchange.fetch_order_book("USD/RUR"))
        self.assertDictEqual(offline_order_books["EUR/RUR"][0], exchange.fetch_order_book("EUR/RUR"))
        self.assertDictEqual(offline_order_books["USD/RUR"][2], exchange.fetch_order_book("USD/RUR"))
        self.assertDictEqual(offline_order_books["EUR/RUR"][1], exchange.fetch_order_book("EUR/RUR"))

        # testing exception if no order books  lef for symbol
        with self.assertRaises(ztom.ExchangeWrapperOfflineFetchError) as cm:
            exchange.fetch_order_book("USD/RUR")
        e = cm.exception
        self.assertEqual(type(e), ztom.ExchangeWrapperOfflineFetchError)

        # stil order book is available for other symbol
        self.assertDictEqual(offline_order_books["EUR/RUR"][2], exchange.fetch_order_book("EUR/RUR"))

        # try to fetch non available OB
        with self.assertRaises(ztom.ExchangeWrapperOfflineFetchError) as cm:
            exchange.fetch_order_book("ETH/BTC")
        e = cm.exception
        self.assertEqual(type(e), ztom.ExchangeWrapperOfflineFetchError)
        self.assertIn("ETH/BTC", e.args[0])

    def test_offline_order_books_load_from_file(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")

        file_name = "test_data/order_books.csv"
        order_books = exchange.load_offline_order_books_from_csv(file_name)

        self.assertIn("ETH/BTC", order_books)
        self.assertIn("FUEL/BTC", order_books)
        self.assertIn("FUEL/ETH", order_books)
        self.assertIn("WAVES/BTC", order_books)
        self.assertIn("WAVES/ETH", order_books)
        self.assertIn("ZRX/ETH", order_books)
        self.assertIn("ZRX/BTC", order_books)

        self.assertEqual(6, len(order_books["ETH/BTC"]))
        self.assertEqual(1, len(order_books["WAVES/ETH"]))

        self.assertEqual(10, len(order_books["ETH/BTC"][0]["asks"]))
        self.assertEqual(10, len(order_books["ETH/BTC"][0]["bids"]))

        self.assertEqual(10, len(order_books["ETH/BTC"][4]["asks"]))
        self.assertEqual(10, len(order_books["ETH/BTC"][4]["bids"]))

        self.assertEqual(0.092306, order_books["ETH/BTC"][4]["asks"][0][0])

        self.assertEqual(0.00133205, order_books["ZRX/ETH"][1]["asks"][2][0])

        ob = exchange.fetch_order_book("WAVES/ETH")
        self.assertEqual(0.008239, ob["bids"][2][0])

    def test_offline_order_books_async(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")  # type: ztom.ccxtExchangeWrapper
        exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")

        # exchange.init_async_exchange()

        exchange.fetch_tickers()

        file_name = "test_data/order_books.csv"
        exchange.load_offline_order_books_from_csv(file_name)

        order_books = exchange.get_order_books_async(["ETH/BTC", "WAVES/ETH", "AMB/ETH"])  # AMB/ETH taken from tickers

        self.assertEqual(10, len(order_books[0]["asks"]))
        self.assertEqual(False, order_books[0]["from_ticker"])

        self.assertEqual(0.008239, order_books[1]["bids"][2][0])

        self.assertEqual(0.00064991, order_books[2]["asks"][0][0])
        self.assertEqual(99999999, order_books[2]["asks"][0][1])
        self.assertEqual(True, order_books[2]["from_ticker"])

    def test_online_order_books_async(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")  # type: ztom.ccxtExchangeWrapper
        # exchange.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv")

        exchange.init_async_exchange()

        exchange.fetch_tickers()

        # file_name = "test_data/order_books.csv"
        # exchange.load_offline_order_books_from_csv(file_name)

        order_books = exchange.get_order_books_async(["ETH/BTC", "WAVES/ETH", "AMB/ETH"])  # AMB/ETH taken from tickers

        self.assertIn('asks', order_books[0])
        self.assertIn('asks', order_books[1])
        self.assertIn('asks', order_books[1])

        # self.assertEqual(10, len(order_books[0]["asks"]))
        # self.assertEqual(False, order_books[0]["from_ticker"])
        #
        # self.assertEqual(0.008239, order_books[1]["bids"][2][0])
        #
        # self.assertEqual(0.00064991, order_books[2]["asks"][0][0])
        # self.assertEqual(99999999, order_books[2]["asks"][0][1])
        # self.assertEqual(True, order_books[2]["from_ticker"])

    def test_fetch_order_book(self):
        e = ztom.ccxtExchangeWrapper.load_from_id("binance")  # type: ztom.ccxtExchangeWrapper
        e.load_markets()
        ob = e.fetch_order_book("ETH/BTC")
        self.assertIn("asks", ob)
        self.assertIn("bids", ob)

    def test_fetch_markets_if_markets_were_not_loaded(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")  # type: ztom.ccxtExchangeWrapper

        # force offline mode
        exchange.offline = True

        exchange._offline_markets = {
            "BTC/USDC": {"active": True}
        }

        exchange._offline_tickers[0] = {"BTC/USDC": {"ask": 222}}

        tickers = exchange.fetch_tickers()

        self.assertDictEqual({"BTC/USDC": {"active": True}}, exchange.markets)

        self.assertDictEqual({"BTC/USDC": {"ask": 222}}, tickers)
        self.assertDictEqual({"BTC/USDC": {"ask": 222}}, exchange.tickers)

        self.assertNotIn("USDC/BTC", tickers)

    def test_filter_active_markets_and_tickers(self):
        exchange = ztom.ccxtExchangeWrapper.load_from_id("binance")  # type: ztom.ccxtExchangeWrapper

        # force offline mode
        exchange.offline = True

        # "active" attribute presents
        exchange._offline_markets = {"USDC/BTC": {"active": False},
                                     "BTC/USDC": {"active": True}
                                     }
        exchange._offline_tickers[0] = {"USDC/BTC": {"ask": 111},
                                        "BTC/USDC": {"ask": 222}}

        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()

        self.assertDictEqual({"BTC/USDC": {"active": True}}, markets)
        self.assertDictEqual({"BTC/USDC": {"active": True}}, exchange.markets)

        self.assertDictEqual({"BTC/USDC": {"ask": 222}}, tickers)
        self.assertDictEqual({"BTC/USDC": {"ask": 222}}, exchange.tickers)

        self.assertNotIn("USDC/BTC", tickers)

        # second tickers fetch - no active markets for tickers
        exchange._offline_tickers[1] = {"USD/RUR": {"ask": 666}}
        tickers = exchange.fetch_tickers()
        self.assertDictEqual({}, tickers)

        # 3rd fetch - single ticker
        exchange._offline_tickers[2] = {"USD/RUR": {"ask": 666},
                                        "BTC/USDC": {"ask": 333}}

        tickers = exchange.fetch_tickers("USD/RUR")
        self.assertDictEqual({}, tickers)

        # no active markets
        exchange._offline_markets = {"USD/RUB": {"bid": 666}}
        exchange.load_markets()

        # with self.assertRaises(Exception) as e:
        #     markets = exchange.get_markets()
        #
        # self.assertEqual(type(e.exception), ztom.ExchangeWrapperError)
        # self.assertEqual(e.exception.args[0], "No active markets")

        exchange._offline_tickers[3] = {"USD/RUR": {"ask": 666},
                                        "BTC/USDC": {"ask": 333}}

        tickers = exchange.fetch_tickers()
        self.assertEqual({}, tickers)

    def test_throttle_override_by_wrapper_throttle(self):
        ew = ztom.ccxtExchangeWrapper("binance")
        ew.enable_requests_throttle()

        self.assertEqual(60, ew.requests_throttle.period)
        self.assertEqual(100, ew.requests_throttle.requests_per_period)

        self.assertDictEqual({
            "single": 1,
            "load_markets": 1,
            "fetch_tickers": 1,
            "fetch_ticker": 1,
            "fetch_order_book": 1,
            "create_order": 1,
            "fetch_order": 1,
            "cancel_order": 1,
            "fetch_my_trades": 1,
            "fetch_balance": 1},
            ew.requests_throttle.request_weights)

        # ztom.exchanges.binance.REQUEST_TYPE_WIGHTS.update({"fetch_tickers": 10, "modify": 666})
        ew = ztom.ccxtExchangeWrapper.load_from_id("binance")
        ew.enable_requests_throttle()

        self.assertEqual(60, ew.requests_throttle.period)
        self.assertEqual(1200, ew.requests_throttle.requests_per_period)

        self.assertEqual(ew.requests_throttle.request_weights["fetch_tickers"], 2)
        # self.assertEqual(ew.requests_throttle.request_weights["modify"], 666)

    def test_throttle_override_default_on_init(self):
        ew = ztom.ccxtExchangeWrapper.load_from_id("binance")
        ew.enable_requests_throttle(10, 100, {"load_markets": 40})

        self.assertEqual(10, ew.requests_throttle.period)
        self.assertEqual(100, ew.requests_throttle.requests_per_period)

        self.assertDictEqual({
            "single": 1,
            "load_markets": 40,
            "fetch_tickers": 2,
            "fetch_ticker": 1,
            "fetch_order_book": 1,
            "create_order": 1,
            "fetch_order": 1,
            "cancel_order": 1,
            "fetch_my_trades": 1,
            "fetch_balance": 5},
            ew.requests_throttle.request_weights)

        ew = ztom.ccxtExchangeWrapper("binance")
        ew.enable_requests_throttle(4, 444)

        self.assertEqual(4, ew.requests_throttle.period)
        self.assertEqual(444, ew.requests_throttle.requests_per_period)

        self.assertDictEqual(ew.REQUEST_TYPE_WIGHTS, ew.requests_throttle.request_weights)

    def test_throttle_generic(self):
        ew = ztom.ccxtExchangeWrapper("binance")
        ew.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ew.enable_requests_throttle()

        self.assertEqual(ew.requests_throttle.period, 60)
        self.assertEqual(ew.requests_throttle.requests_per_period, 100)

        markets_timestamp = datetime.datetime.timestamp(datetime.datetime.now())
        time.sleep(0.1)
        ew.load_markets()

        self.assertEqual(1, len(ew.requests_throttle.requests_current_period))
        # self.assertAlmostEqual(ew.requests_throttle.requests_current_period[0]["timestamp"], markets_timestamp, 2)

        time_diff = ew.requests_throttle.requests_current_period[0]["timestamp"] - markets_timestamp
        self.assertAlmostEqual(0.1, time_diff, 1)
        time.sleep(0.1)

        sleep = ew.requests_throttle.sleep_time()
        self.assertAlmostEqual(0.6 - 0.1, sleep, 1)

    def test_throttle_all_request_types(self):
        ew = ztom.ccxtExchangeWrapper("binance")
        ew.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        ew.set_offline_balance(
            {'free': {
                     'BTC': 1,
                     'USD': 123.00},
             "BTC": {"free": 1},
             "USDT": {"free": 123}
             }
        )

        ew.enable_requests_throttle()

        ew.load_markets()
        self.assertEqual(1, len(ew.requests_throttle.requests_current_period))

        ew.fetch_tickers()
        self.assertEqual(2, len(ew.requests_throttle.requests_current_period))

        ew.fetch_order_book("ETH/BTC")
        self.assertEqual(3, len(ew.requests_throttle.requests_current_period))

        order = ztom.TradeOrder("limit", "ETH/BTC", 1, "buy", ew.tickers["ETH/BTC"]["bid"])
        ew.add_offline_order_data(order)

        ew.place_limit_order(order)
        self.assertEqual(4, len(ew.requests_throttle.requests_current_period))

        ew.get_order_update(order)
        self.assertEqual(5, len(ew.requests_throttle.requests_current_period))

        ew.get_trades(order)
        self.assertEqual(6, len(ew.requests_throttle.requests_current_period))

        ew.cancel_order(order)
        self.assertEqual(7, len(ew.requests_throttle.requests_current_period))

        ew.fetch_free_balance()
        self.assertEqual(8, len(ew.requests_throttle.requests_current_period))

        self.assertEqual("load_markets", ew.requests_throttle.requests_current_period[0]["request_type"])
        self.assertEqual("fetch_tickers", ew.requests_throttle.requests_current_period[1]["request_type"])
        self.assertEqual("fetch_order_book", ew.requests_throttle.requests_current_period[2]["request_type"])
        self.assertEqual("create_order", ew.requests_throttle.requests_current_period[3]["request_type"])
        self.assertEqual("fetch_order", ew.requests_throttle.requests_current_period[4]["request_type"])
        self.assertEqual("fetch_my_trades", ew.requests_throttle.requests_current_period[5]["request_type"])
        self.assertEqual("cancel_order", ew.requests_throttle.requests_current_period[6]["request_type"])
        self.assertEqual("fetch_balance", ew.requests_throttle.requests_current_period[7]["request_type"])

        self.assertEqual(8, ew.requests_throttle.total_requests_current_period)

        # 2nd round
        ew.load_markets()
        self.assertEqual(9, len(ew.requests_throttle.requests_current_period))

        ew.fetch_tickers()
        self.assertEqual(10, len(ew.requests_throttle.requests_current_period))

        ew.fetch_order_book("ETH/BTC")
        self.assertEqual(11, len(ew.requests_throttle.requests_current_period))

        order = ztom.TradeOrder("limit", "ETH/BTC", 1, "buy", ew.tickers["ETH/BTC"]["bid"])
        ew.add_offline_order_data(order)

        ew.place_limit_order(order)
        self.assertEqual(12, len(ew.requests_throttle.requests_current_period))

        ew.get_order_update(order)
        self.assertEqual(13, len(ew.requests_throttle.requests_current_period))

        ew.get_trades(order)
        self.assertEqual(14, len(ew.requests_throttle.requests_current_period))

        ew.cancel_order(order)
        self.assertEqual(15, len(ew.requests_throttle.requests_current_period))

        ew.fetch_free_balance()
        self.assertEqual(16, len(ew.requests_throttle.requests_current_period))

        self.assertEqual("load_markets", ew.requests_throttle.requests_current_period[8]["request_type"])
        self.assertEqual("fetch_tickers", ew.requests_throttle.requests_current_period[9]["request_type"])
        self.assertEqual("fetch_order_book", ew.requests_throttle.requests_current_period[10]["request_type"])
        self.assertEqual("create_order", ew.requests_throttle.requests_current_period[11]["request_type"])
        self.assertEqual("fetch_order", ew.requests_throttle.requests_current_period[12]["request_type"])
        self.assertEqual("fetch_my_trades", ew.requests_throttle.requests_current_period[13]["request_type"])
        self.assertEqual("cancel_order", ew.requests_throttle.requests_current_period[14]["request_type"])
        self.assertEqual("fetch_balance", ew.requests_throttle.requests_current_period[15]["request_type"])

        self.assertEqual(16, ew.requests_throttle.total_requests_current_period)


    def test_throttle_control_no_sleep(self):

        ew = ztom.ccxtExchangeWrapper("binance")
        ew.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ew.set_offline_balance(
            {'free': {
                     'BTC': 1,
                     'USD': 123.00},
             "BTC": {"free": 1},
             "USDT": {"free": 123}
             }
        )

        ew._offline_tickers = list()

        for i in range(0,1000):
            ew._offline_tickers.append({"BTC/USDT" :{"ask": 3500+i*0.01, "bid":3400+i*0.01}})

        ew.enable_requests_throttle(60, 100)

        ew.load_markets()
        sleep_time = ew.requests_throttle.sleep_time()
        time.sleep(sleep_time)

        for i in range(0, 99):
            tickers = ew.fetch_tickers()
            self.assertAlmostEqual(0.6*(i+1), ew.requests_throttle.sleep_time(), 1)

        self.assertEqual(100, len(ew.requests_throttle.requests_current_period))

        self.assertEqual(100, len(ew.requests_throttle.requests_current_period))

    def test_throttle_control_sleep(self):

        ew = ztom.ccxtExchangeWrapper("binance")
        ew.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ew.set_offline_balance(
            {'free': {
                     'BTC': 1,
                     'USD': 123.00},
             "BTC": {"free": 1},
             "USDT": {"free": 123}
             }
        )

        ew._offline_tickers = list()

        for i in range(0,1000):
            ew._offline_tickers.append({"BTC/USDT" :{"ask": 3500+i*0.01, "bid":3400+i*0.01}})

        ew.enable_requests_throttle(0.5, 10)

        ew.load_markets()
        time.sleep(ew.requests_throttle.sleep_time())

        for i in range(2, 11):
            tickers = ew.fetch_tickers()

            self.assertEqual(i, ew.requests_throttle.total_requests_current_period)

            sleep_time = ew.requests_throttle.sleep_time()

            print("Periods since start: {}".format(ew.requests_throttle.periods_since_start))
            print("Request num {}".format(i))
            print("Sleeping for {}".format(sleep_time))

            # self.assertAlmostEqual(0.1, sleep_time, 1)
            time.sleep(sleep_time)

        #########

        for i in range(11, 41):
            tickers = ew.fetch_tickers()

            print("Request num {}".format(i))

            self.assertEqual(((i-1) // ew.requests_throttle.requests_per_period),
                             ew.requests_throttle.periods_since_start)

            if i % (ew.requests_throttle.periods_since_start * ew.requests_throttle.requests_per_period) != 0:
                self.assertEqual(
                    i % (ew.requests_throttle.periods_since_start * ew.requests_throttle.requests_per_period),
                    ew.requests_throttle.total_requests_current_period
                )
            else:
                self.assertEqual(i / (ew.requests_throttle.periods_since_start+1),
                                 ew.requests_throttle.total_requests_current_period)

            sleep_time = ew.requests_throttle.sleep_time()

            print("Periods since start: {}".format(ew.requests_throttle.periods_since_start))
            print("Sleeping for {}".format(sleep_time))
            print("Requests current period {}".format(ew.requests_throttle.total_requests_current_period))

            # self.assertAlmostEqual(0.1, sleep_time, 1)

            time.sleep(sleep_time)

        # ew.requests_throttle.update()

        # self.assertEqual(20, len(ew.requests_throttle.requests_current_period))
        # self.assertAlmostEqual(0.9, ew.requests_throttle._current_period_time, 1)


if __name__ == '__main__':
    unittest.main()
