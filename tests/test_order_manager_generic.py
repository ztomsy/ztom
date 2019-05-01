# -*- coding: utf-8 -*-
from .context import ztom as zt
from ztom import ActionOrder
import unittest
from unittest.mock import MagicMock


class OrderManagerTestSuite(unittest.TestCase):

    def test_get_order_command(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        om = zt.ActionOrderManager(ex)

        order_command = "cancel ticker"
        order_action = om._order_action(order_command)
        self.assertEqual("cancel", order_action)

        order_command = "cancel"
        order_action = om._order_action(order_command)
        self.assertEqual("cancel", order_action)

        order_command = "cancel  "
        order_action = om._order_action(order_command)
        self.assertEqual("cancel", order_action)

        order_command = "new ticker ETH/BTC"
        order_action = om._order_action(order_command)
        self.assertEqual("new", order_action)

    def test_get_data_request(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        om = zt.ActionOrderManager(ex)

        order_command = "cancel ticker"
        data_request = om._data_requests(order_command)
        self.assertEqual("ticker", data_request[0])

        order_command = "cancel ticker ETH/BTC  ;  "
        data_request = om._data_requests(order_command)
        self.assertEqual("ticker ETH/BTC", data_request[0])

        order_command = "cancel"
        data_request = om._data_requests(order_command)
        self.assertEqual(None, data_request)

        order_command = "cancel ticker eth/btc; ma eth/btc  ;"
        data_request = om._data_requests(order_command)
        self.assertListEqual(["ticker eth/btc", "ma eth/btc"], data_request)

        order_command = "hold ticker eth/btc; ma eth/btc"
        data_request = om._data_requests(order_command)
        self.assertListEqual(["ticker eth/btc", "ma eth/btc"], data_request)

    def test_owa_manager_create(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        order = zt.ActionOrder.create_from_start_amount("ETH/BTC", "ETH", 0.05, "BTC", 0.001)
        om = zt.ActionOrderManager(ex)
        om.add_order(order)
        om.set_order_supplementary_data(order, {"report_kpi": 1})
        self.assertEqual(om.supplementary[order.id]["report_kpi"], 1)

    def test_owa_manager_fill_orders(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        order1 = zt.ActionOrder.create_from_start_amount("ABC/XYZ", "ABC", 1, "XYZ", 0.1)
        order2 = zt.ActionOrder.create_from_start_amount("USD/RUB", "USD", 1, "RUB", 70)

        om = zt.ActionOrderManager(ex)

        om.add_order(order1)
        om.add_order(order2)

        self.assertEqual(2, om.pending_actions_number())

        while len(om.get_open_orders()) > 0:
            om.proceed_orders()

            # orders are being filled without additional commands
            self.assertEqual(0, om.pending_actions_number())

        self.assertEqual("closed", order1.status)
        self.assertEqual("closed", order2.status)

        self.assertAlmostEqual(1, order1.filled, delta=0.0001)
        self.assertAlmostEqual(1, order1.filled_start_amount, delta=0.00001)
        self.assertAlmostEqual(0.1, order1.filled_dest_amount, delta=0.00001)

        self.assertAlmostEqual(1, order2.filled, delta=0.00001)
        self.assertAlmostEqual(70, order2.filled_dest_amount, delta=0.0001)
        self.assertAlmostEqual(1, order2.filled_start_amount, delta=0.00001)

        self.assertListEqual(list([order1, order2]), om.get_closed_orders())

        om.proceed_orders()
        self.assertEqual(None, om.get_closed_orders())

    def test_force_close(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        tickers = ex.fetch_tickers()

        order1 = zt.ActionOrder.create_from_start_amount(symbol="BTC/USDT", start_currency="BTC",
                                                         amount_start=1, dest_currency="USDT",
                                                         price=tickers["BTC/USDT"]["ask"])

        order2 = zt.ActionOrder.create_from_start_amount("USD/RUB", "USD", 1, "RUB", 70)

        om = zt.ActionOrderManager(ex)

        om.add_order(order1)
        om.add_order(order2)

        i = 0
        while len(om.get_open_orders()) > 0:
            om.proceed_orders()

            if i == 6:
                self.assertEqual(0, om.pending_actions_number())

            if i == 5:
                order1.force_close()
                self.assertEqual(True, order1._force_close)
                self.assertEqual(1, om.pending_actions_number())

            i += 1

        self.assertAlmostEqual(0.5, order1.filled, delta=0.0001)
        self.assertAlmostEqual(0.5, order1.filled_start_amount, delta=0.00001)
        self.assertAlmostEqual(4113.5, order1.filled_dest_amount, delta=0.00001)
        self.assertIn("#force_close", order1.tags)

        self.assertAlmostEqual(1, order2.filled, delta=0.00001)
        self.assertAlmostEqual(70, order2.filled_dest_amount, delta=0.0001)
        self.assertAlmostEqual(1, order2.filled_start_amount, delta=0.00001)

    def test_owa_could_not_create_trade_order(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()

        # override offline order creation function with None result, so the trade order could not be created
        ex.add_offline_order_data = MagicMock(return_value=None)

        order1 = zt.ActionOrder.create_from_start_amount("ABC/XYZ", "ABC", 1, "XYZ", 0.1)

        om = zt.ActionOrderManager(ex)
        om.add_order(order1)

        while len(om.get_open_orders()) > 0:
            om.proceed_orders()

        self.assertLessEqual("closed", order1.status)
        self.assertEqual(0.0, order1.filled)  # offline order has 6 updates, so we've run/filled only 1 of them
        self.assertEqual(order1.state, "fill")

    def test_om_skip_getting_trades(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")  # type: zt.ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        order1 = zt.ActionOrder.create_from_start_amount("ABC/XYZ", "ABC", 1, "XYZ", 0.1)

        om = zt.ActionOrderManager(ex)
        self.assertEqual(True, om.request_trades)
        om.request_trades = False
        ex.trades_in_offline_order_update = False

        om.add_order(order1)
        # om.add_order(order2)

        while len(om.get_open_orders()) > 0:
            om.proceed_orders()

        for o in order1.orders_history:
            self.assertEqual(0, len(o.trades))

        self.assertAlmostEqual(1, order1.filled, delta=0.0001)
        self.assertAlmostEqual(1, order1.filled_start_amount, delta=0.00001)
        self.assertAlmostEqual(0.1, order1.filled_dest_amount, delta=0.00001)

    def test_single_data_request_value_from_data_for_orders(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()

        om = zt.ActionOrderManager(ex)

        om.data_for_orders = {"tickers": {"ETH/BTC": {"ask": 1, "bid": 2, "mas": {"5": 5}}}}

        val = om._single_data_request_value("tickers eth/btc ask")
        self.assertEqual(1, val)

        val = om._single_data_request_value("tickers eth/btc")
        self.assertEqual({"ask": 1, "bid": 2, "mas": {"5": 5}}, val)

        val = om._single_data_request_value("tickers")
        self.assertDictEqual({"ETH/BTC": {"ask": 1, "bid": 2, "mas": {"5": 5}}}, val)

        val = om._single_data_request_value("markets")
        self.assertEqual(None, val)

        val = om._single_data_request_value("tickers BTC/USDT")
        self.assertEqual(None, val)

    def test_single_data_request_value_from_exchange(self):

        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()

        om = zt.ActionOrderManager(ex)

        val = om._single_data_request_value("tickers ETH/USDT")
        self.assertDictEqual(om.exchange.tickers["ETH/USDT"], val)

        val = om._single_data_request_value("tickers ETH/USDT ask")
        self.assertEqual(682.81, val)  # second fetch

        # third fetch
        val = om._single_data_request_value("tickers")
        self.assertEqual(om.exchange.tickers, val)

        with self.assertRaises(Exception) as cm:
            val = om._single_data_request_value("tickers")
        e = cm.exception

        self.assertEqual(type(e), zt.ExchangeWrapperOfflineFetchError)

    def test_single_data_request_mixed_from_data_for_orders_and_exchange(self):

        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()

        om = zt.ActionOrderManager(ex)
        om.data_for_orders = {"ma": {"ETH/USDT": 1}}

        ma = om._single_data_request_value("MA ETH/USDT")
        tickers = om._single_data_request_value("tickers")

        self.assertEqual(1, ma)
        self.assertEqual(om.exchange.tickers, tickers)

    def test_data_request_list(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()

        om = zt.ActionOrderManager(ex)
        om.data_for_orders = {"ma": {"ETH/USDT": 1}}

        order_command = "hold"
        data_request_list = om._data_requests(order_command)
        results = om._data_request_list_values(data_request_list)
        self.assertEqual(None, results)


        order_command = "hold tickers;ma ETH/USDT"
        data_request_list = om._data_requests(order_command)
        results = om._data_request_list_values(data_request_list)
        self.assertListEqual([om.exchange.tickers, 1], results)

        order_command = "hold tickers"
        data_request_list = om._data_requests(order_command)
        results = om._data_request_list_values(data_request_list)
        self.assertListEqual([om.exchange.tickers], results)

        order_command = "hold tickers; mas; ;"
        data_request_list = om._data_requests(order_command)
        results = om._data_request_list_values(data_request_list)
        self.assertListEqual([om.exchange.tickers, None], results)

        order_command = "   hold tickers; mas;"
        data_request_list = om._data_requests(order_command)
        results = om._data_request_list_values(data_request_list)
        self.assertListEqual([None, None], results)

    def test_om_data_requests_from_orders_commands(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()

        om = zt.ActionOrderManager(ex)

        order = ActionOrder("USD/RUR", 1, 70, "buy")
        order2 = ActionOrder("EUR/RUR", 1, 75, "buy")

        om.add_order(order)

        om.add_order(order2)

        order.order_command = "new tickers"
        order2.order_command = "new ma"

        # check for number of actionsv- should be 2 actions
        self.assertEqual(2, om.pending_actions_number())

        om.data_for_orders = {"ma": 5}
        om.proceed_orders()  # proceed "new command with data request from exchange

        self.assertDictEqual(om.exchange.tickers, order.market_data[0])
        self.assertEqual(5, order2.market_data[0])
        self.assertDictEqual(om.data_for_orders, dict())  # check that data_for_orders was cleaned by order manager

        self.assertEqual(0, om.pending_actions_number())

        order.order_command = "hold tickers ETH/BTC ask;ma 5"  # will be second ticker from tickers.csv file and ma 5
        order2.order_command = "hold ma 5"
        om.data_for_orders = {"ma": {"5": 71}}  # let's add some more data
        om.proceed_orders()

        self.assertEqual(0.082975, order.market_data[0])
        self.assertEqual(71, order.market_data[1])
        self.assertEqual(71, order2.market_data[0])

        self.assertDictEqual(om.data_for_orders, dict())  # check that data_for_orders was cleaned by order manager

        # no market data
        order.order_command = "hold"
        order2.order_command = "hold ma"
        # om.data_for_orders = {"ma": {"5": 71}}  # let's add some more data
        om.proceed_orders()
        self.assertEqual(None, order.market_data)
        self.assertEqual(None, order2.market_data[0])  # no data was found with the request

        self.assertDictEqual(om.data_for_orders, dict())  # check that data_for_orders was cleaned by order manager
        self.assertEqual(None, order2.market_data[0])

        # 3rd request
        order.order_command = "hold tickers ETH/BTC bid"
        om.proceed_orders()
        self.assertEqual(0.082921, order.market_data[0])

        # 4rth request - no data available
        order.order_command = "cancel tickers ETH/BTC bid; ma 5"
        order2.order_command = "cancel tickers ETH/BTC bid; ma 5"

        om.data_for_orders = {"ma": {"5": 71}}  # let's add some more data
        om.proceed_orders()
        self.assertEqual(None, order.market_data[0])
        self.assertEqual(None, order2.market_data[0])

        self.assertEqual(71, order.market_data[1])
        self.assertEqual(71, order2.market_data[1])

    def test_offline_order_zero_fill_updates(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")  # type: zt.ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        order1 = zt.ActionOrder.create_from_start_amount("ABC/XYZ", "ABC", 1, "XYZ", 0.1)

        om = zt.ActionOrderManager(ex)
        self.assertEqual(True, om.request_trades)
        om.request_trades = False
        om.offline_order_zero_fill_updates = 4
        ex.trades_in_offline_order_update = False

        om.add_order(order1)
        om.proceed_orders()

        order_data = ex._offline_orders_data[order1.active_trade_order.internal_id]["_offline_order"]["updates"]
        for i in range(0, 4):
            self.assertEqual(0, order_data[i]["filled"])

        self.assertLess(0, order_data[4]["filled"])



if __name__ == '__main__':
    unittest.main()

