# -*- coding: utf-8 -*-
from .context import ztom
from ztom import OrderManagerError, OrderManagerErrorUnFilled, OrderManagerCancelAttemptsExceeded
import unittest


class TradeOrderManagerTestSuite(unittest.TestCase):

    def test_order_manager_create(self):

        limits = {"BTC": 0.002, "ETH": 0.02, "BNB": 1, "USDT": 20}

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 1, "BTC", 0.07)
        om = ztom.OrderManagerFok(order, limits)

        self.assertEqual(om.limits, limits)
        self.assertEqual(om.min_filled_amount, 0.002)

        order = ztom.TradeOrder.create_limit_order_from_start_amount("USDT/ETH", "USDT", 1, "ETH", 500)
        om = ztom.OrderManagerFok(order, limits)

        self.assertEqual(om.limits, limits)
        self.assertEqual(om.min_filled_amount, 0.02)

        order = ztom.TradeOrder.create_limit_order_from_start_amount("XXX/YYY", "XXX", 1, "YYY", 500)

        with self.assertRaises(OrderManagerError) as cm:
            om = ztom.OrderManagerFok(order, limits)

        e = cm.exception
        self.assertEqual(type(e), OrderManagerError)

    def test_order_manager_fok_proceed_update_ok(self):
        limits = {"BTC": 0.0002, "ETH": 0.02, "BNB": 1, "USDT": 20}

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")

        ex.load_markets()
        ex.fetch_tickers()

        om = ztom.OrderManagerFok(order)

        order_resp = ex.place_limit_order(order)
        order.update_order_from_exchange_resp(order_resp)

        while om.proceed_update()["action"] == "hold":
            update_resp = ex.get_order_update(order)
            order.update_order_from_exchange_resp(update_resp)

        self.assertEqual(order.status, "closed")
        self.assertEqual(order.filled_start_amount, 0.5)

    def test_order_manager_fok_proceed_update_cancel(self):
        limits = {"BTC": 0.0002, "ETH": 0.02, "BNB": 1, "USDT": 20}

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")

        ex.load_markets()
        ex.fetch_tickers()

        om = ztom.OrderManagerFok(order, None, 4)

        order_resp = ex.place_limit_order(order)
        order.update_order_from_exchange_resp(order_resp)

        while om.proceed_update()["action"] == "hold":
            update_resp = ex.get_order_update(order)
            om.order_update_requests += 1
            order.update_order_from_exchange_resp(update_resp)

        self.assertEqual(order.status, "open")
        self.assertEqual(order.filled_start_amount, 0.000818)
        self.assertEqual(order.filled_dest_amount, 6.029e-05)
        self.assertEqual(om.last_response["action"], "cancel")

    @unittest.skip  # not implemented
    def test_order_manager_fok_proceed_update_skip(self):
        limits = {"BTC": 0.0002, "ETH": 0.02, "BNB": 1, "USDT": 20}

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")

        ex.load_markets()
        ex.fetch_tickers()

        om = ztom.OrderManagerFok(order, updates_to_kill=3)

        order_resp = ex.place_limit_order(order)
        order.update_order_from_exchange_resp(order_resp)

        while om.proceed_update()["action"] == "hold":
            update_resp = ex.get_order_update(order)
            order.update_order_from_exchange_resp(update_resp)

        self.assertEqual(order.status, "open")
        self.assertEqual(order.filled_src_amount, 0.0001)
        self.assertEqual(order.filled_dest_amount, 0.000006633)
        self.assertEqual(om.last_response["action"], "cancel")

    def test_order_manager_fill_ok(self):

        limits = {"BTC": 0.0002, "ETH": 0.02, "BNB": 1, "USDT": 20}
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")
        ex.load_markets()
        ex.fetch_tickers()

        om = ztom.OrderManagerFok(order, None, 100)

        om.fill_order(ex)

        self.assertEqual(order.status, "closed")
        self.assertEqual(order.filled_dest_amount, 0.5 * order.price)

        self.assertEqual(om.last_response["action"], "complete_order")
        self.assertEqual(om.last_response["action"], "complete_order")
        self.assertEqual(om.last_response["status"], "closed")

    def test_order_manager_fill_cancel(self):
        limits = {"BTC": 0.0002, "ETH": 0.02, "BNB": 1, "USDT": 20}

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")

        ex.load_markets()
        ex.fetch_tickers()

        om = ztom.OrderManagerFok(order, None, 4)

        with self.assertRaises(OrderManagerErrorUnFilled) as cm:
            om.fill_order(ex)

        e = cm.exception

        self.assertEqual(type(e), OrderManagerErrorUnFilled)
        self.assertEqual(order.status, "open")
        self.assertEqual(om.last_response["action"], "cancel")

        self.assertIn("max number of updates reached", om.last_response["reason"])

        self.assertEqual(order.filled_start_amount, 0.000818)
        self.assertEqual(order.filled_dest_amount, 6.029e-05)
        self.assertEqual(om.last_response["status"], "open")

    def test_order_manager_cancel_ok(self):
        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_binance_cancel.json")

        ex.load_markets()
        ex.fetch_tickers()

        om = ztom.OrderManagerFok(order, None, 2)  # 1st request to create order . 2nd to get first update

        try:
            om.fill_order(ex)
        except OrderManagerErrorUnFilled as e:
            om.cancel_order(ex)

        self.assertEqual("canceled", om.order.status)

    def test_order_manager_cancel_cancel_attemptsExceed(self):

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_binance_cancel.json")

        ex.load_markets()
        ex.fetch_tickers()

        ex._offline_cancel_order = lambda x: None  # override offline cancel function

        om = ztom.OrderManagerFok(order, None, 1, 1)  # 1st request to create order . 2nd to get first update

        try:
            om.fill_order(ex)
        except OrderManagerErrorUnFilled as e:
            with self.assertRaises(OrderManagerCancelAttemptsExceeded) as cm:
                om.cancel_order(ex)

        # self.assertEqual(om.order.status, "open")

    def test_order_manager_cancel_cancel_notok(self):

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_binance_error.json")

        ex.load_markets()
        ex.fetch_tickers()

        ex._offline_cancel_order = lambda x: None  # override offline cancel function

        om = ztom.OrderManagerFok(order, None, 10, 1)  # 1st request to create order . 2nd to get first update

        try:
            om.fill_order(ex)
        except OrderManagerErrorUnFilled:
            with self.assertRaises(OrderManagerCancelAttemptsExceeded):
                om.cancel_order(ex)

        # self.assertEqual(om.order.status, "open")

    @unittest.skip  # not implemented
    def test_order_manager_run_less_than_min(self):

        limits = {"BTC": 0.0002, "ETH": 0.02, "BNB": 1, "USDT": 20}

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "ETH", 0.5, "BTC",
                                                                     0.06633157807472399)
        ex = ztom.ccxtExchangeWrapper.load_from_id("kucoin")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_multi.json")

        ex.load_markets()
        ex.fetch_tickers()

        om = ztom.OrderManagerFok(order, limits, 3)

        with self.assertRaises(OrderManagerErrorUnFilled) as cm:
            om.fill_order(ex)

        e = cm.exception

        self.assertEqual(type(e), OrderManagerErrorUnFilled)
        self.assertEqual(order.status, "open")
        self.assertEqual(order.filled_src_amount, 0.0001)
        self.assertEqual(order.filled_dest_amount, 0.000006633)
        self.assertEqual(om.last_response["action"], "cancel")
        self.assertIn("min amount have not reached", om.last_response["reason"])

    @unittest.skip  # feature removed
    def test_do_not_cancel_min_threshold_zero(self):
        ex = ztom.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_buy.json")

        ex.load_markets()
        ex.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "BTC", 0.005, "ETH",
                                                                     0.07381590480571001)
        ex.add_offline_order_data(order, 9)  # when creating the order update counts

        om = ztom.OrderManagerFok(order, None, updates_to_kill=9, max_cancel_attempts=10,
                                  max_order_update_attempts=1,
                                  request_sleep=0.0,
                                  cancel_threshold=0.0)

        with self.assertRaises(OrderManagerErrorUnFilled) as cm:
            om.fill_order(ex)

        e = cm.exception

        self.assertEqual(type(e), OrderManagerErrorUnFilled)
        self.assertEqual(order.status, "open")
        self.assertLessEqual(order.amount - order.filled, order.amount/9)

        self.assertEqual(9, om.order.update_requests_count)  # no extra update because of not cancel threshold is zero

    @unittest.skip  # feature removed
    def test_do_not_cancel_min_threshold_non_zero(self):
        ex = ztom.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_buy.json")
        ex.load_markets()
        ex.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "BTC", 0.005, "ETH",
                                                                     0.07381590480571001)
        ex.add_offline_order_data(order, 9)  # when creating the order update counts

        om = ztom.OrderManagerFok(order, None, updates_to_kill=9, max_cancel_attempts=10,
                                  max_order_update_attempts=1,
                                  request_sleep=0.0,
                                  cancel_threshold=0.01)
        om.fill_order(ex)

        # one extra update because of not cancelling on remained filled amount is less than cancel_threshold
        self.assertEqual(10, om.order.update_requests_count)
        self.assertEqual("closed", order.status)

    @unittest.skip  # feature removed
    def test_do_cancel_min_threshold_and_amount_is_less(self):
        ex = ztom.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets_binance.json", "test_data/tickers_binance.csv",
                            "test_data/orders_kucoin_buy.json")
        ex.load_markets()
        ex.fetch_tickers()

        order = ztom.TradeOrder.create_limit_order_from_start_amount("ETH/BTC", "BTC", 0.0005, "ETH",
                                                                     0.07381590480571001)
        ex.add_offline_order_data(order, 15)  # when creating the order update counts

        om = ztom.OrderManagerFok(order, None, updates_to_kill=9, max_cancel_attempts=10,
                                  max_order_update_attempts=1,
                                  request_sleep=0.0,
                                  cancel_threshold=0.01)

        with self.assertRaises(OrderManagerErrorUnFilled) as cm:
            om.fill_order(ex)

        e = cm.exception

        self.assertEqual(type(e), OrderManagerErrorUnFilled)
        self.assertEqual(order.status, "open")




if __name__ == '__main__':
    unittest.main()
