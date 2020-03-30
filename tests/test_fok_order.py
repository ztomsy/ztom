import unittest
from ztom import FokOrder, ccxtExchangeWrapper, ActionOrderManager, core, TradeOrder
import time


class FokTestSuite(unittest.TestCase):
    def test_fok_create(self):
        fok_order = FokOrder("ADA/ETH", 1000, 0.32485131 / 1000, "sell", max_order_updates=10, time_to_cancel=10)

        order = fok_order.active_trade_order
        self.assertEqual(order.dest_currency, "ETH")
        self.assertEqual(order.amount, 1000)
        self.assertEqual(order.side, "sell")
        self.assertEqual(fok_order.amount, 1000)

        self.assertEqual(fok_order.time_to_cancel, 10)

        self.assertEqual("fok", order.supplementary["parent_action_order"]["state"])

    def test_cancel_by_time(self):
        fok_order = FokOrder("ADA/ETH", 1000, 0.32485131 / 1000, "sell", max_order_updates=10, time_to_cancel=0.1)

        order_command = fok_order.update_from_exchange({})

        ex = ccxtExchangeWrapper.load_from_id("binance")  # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        om = ActionOrderManager(ex)
        om.request_trades = False

        om.add_order(fok_order)
        om.proceed_orders()
        time.sleep(0.11)

        om.proceed_orders()
        om.proceed_orders()

        self.assertEqual(fok_order.status, "closed")
        self.assertIn("#timeout", fok_order.tags)

    def test_cancel_by_updates(self):
        fok_order = FokOrder("ADA/ETH", 1000, 0.32485131 / 1000, "sell", max_order_updates=10)

        order_command = fok_order.update_from_exchange({})

        ex = ccxtExchangeWrapper.load_from_id("binance")  # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        om = ActionOrderManager(ex)
        om.request_trades = False

        om.add_order(fok_order)
        om.proceed_orders()
        time.sleep(0.11)

        while len(om.get_open_orders())>0:
            om.proceed_orders()

        self.assertEqual(fok_order.status, "closed")
        self.assertEqual(11, fok_order.orders_history[0].update_requests_count)
        self.assertNotIn("#timeout", fok_order.tags)
















if __name__ == '__main__':
    unittest.main()
