# -*- coding: utf-8 -*-
from .context import ztom as zt
import unittest
from unittest.mock import MagicMock


class RecoveryOrderManagerTestSuite(unittest.TestCase):

    def test_owa_manager_create(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        order = zt.RecoveryOrder("ETH/BTC", "ETH", 1, "BTC", 0.1)
        om = zt.ActionOrderManager(ex)
        om.add_order(order)
        om.set_order_supplementary_data(order, {"report_kpi": 1})
        self.assertEqual(om.supplementary[order.id]["report_kpi"], 1)

    def test_owa_manager_run_order(self):

        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()
        order1 = zt.RecoveryOrder("ABC/XYZ", "ABC", 1, "XYZ", 0.1,
                                  ex.markets["ETH/BTC"]["limits"]["amount"]["min"] * 1.01,
                                  max_best_amount_order_updates=2, max_order_updates=5)

        order2 = zt.RecoveryOrder("USD/RUB", "USD", 1, "RUB", 70)
        om = zt.ActionOrderManager(ex)
        om.add_order(order1)
        om.add_order(order2)
        i = 0
        while len(om.get_open_orders()) > 0:
            i += 1

            if i > 5:
                om.data_for_orders = {"tickers": {
                                          "ABC/XYZ": {"ask": 0.1, "bid": 0.09},
                    "USD/RUB": {"ask": 70, "bid": 69}}
                }

            om.proceed_orders()

        self.assertEqual("closed", order1.status)
        self.assertAlmostEqual(1, order1.filled, delta=0.0001)
        # self.assertEqual(0.1, order1.filled_dest_amount)
        self.assertAlmostEqual(1, order1.filled_start_amount, delta=0.00001)
        self.assertListEqual(list([order1]), om.get_closed_orders())

        om.proceed_orders()
        self.assertEqual(None, om.get_closed_orders())

    def test_owa_could_not_create_trade_order(self):
        ex = zt.ccxtExchangeWrapper.load_from_id("binance")
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        ex.load_markets()

        order1 = zt.RecoveryOrder("ABC/XYZ", "ABC", 1, "XYZ", 0.1,
                                  ex.markets["ETH/BTC"]["limits"]["amount"]["min"] * 1.01,
                                  max_best_amount_order_updates=2, max_order_updates=5)

        om = zt.ActionOrderManager(ex)
        om.offline_order_updates = 6
        om.add_order(order1)

        while len(om.get_open_orders()) > 0:
            om.data_for_orders = {"tickers": {
                "ABC/XYZ": {"ask": 0.1, "bid": 0.09},
                "USD/RUB": {"ask": 70, "bid": 69}}
            }

            om.proceed_orders()

            # override order creation function with None result, so the second order could not be created
            ex.add_offline_order_data = MagicMock(return_value=None)

        self.assertLessEqual("closed", order1.status)
        self.assertLessEqual(1 / 6, order1.filled)  # offline order has 6 updates, so we've run/filled only 1 of them
        self.assertEqual(order1.state, "market_price")


if __name__ == '__main__':
    unittest.main()
