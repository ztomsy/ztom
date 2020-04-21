# -*- coding: utf-8 -*-
from .context import ztom
from ztom import FokThresholdTakerPriceOrder, ccxtExchangeWrapper, ActionOrderManager, core, TradeOrder
import unittest
import time

class FokThresholdOrderTestSuite(unittest.TestCase):

    def test_fok_threshold_create(self):
        fto = FokThresholdTakerPriceOrder("ADA/ETH", 1000, 0.32485131 / 1000, "sell", taker_price_threshold=-0.01,
                                          threshold_check_after_updates=10)

        order = fto.active_trade_order
        self.assertEqual(order.dest_currency, "ETH")
        self.assertEqual(order.amount, 1000)
        self.assertEqual(order.side, "sell")
        self.assertEqual(fto.amount, 1000)

        self.assertEqual("fok", order.supplementary["parent_action_order"]["state"])

        self.assertEqual(-0.01, fto.taker_price_threshold)
        self.assertEqual(10, fto.threshold_check_after_updates)

    def test_fok_threshold_from_start_amount(self):
        fto = FokThresholdTakerPriceOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131,
                                                                   taker_price_threshold=-0.05,
                                                                   threshold_check_after_updates=15)

        self.assertEqual(fto.dest_currency, "ETH")
        self.assertEqual(fto.amount, 1000)
        self.assertEqual(fto.start_currency, "ADA")
        self.assertEqual(fto.dest_amount, 0.00032485131*1000)
        self.assertEqual(fto.side, "sell")
        self.assertEqual(fto.amount, 1000)

        self.assertEqual(-0.05, fto.taker_price_threshold)
        self.assertEqual(15, fto.threshold_check_after_updates)

    def test_fok_threshold_flow(self):
        fto = FokThresholdTakerPriceOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131,
                                                                   taker_price_threshold=-0.05,
                                                                   threshold_check_after_updates=5)
        # order update 1
        resp = {"status": "open"}
        order_command = fto.update_from_exchange(resp)
        self.assertEqual("hold", order_command)

        # updates 2 - 5
        for i in range(2, 6):
            resp = {"filled": 0}
            order_command = fto.update_from_exchange(resp)
            self.assertEqual("hold", order_command)

        # update 6 - should start requesting tickers
        resp = {"filled": 0}
        order_command = fto.update_from_exchange(resp)
        self.assertEqual("hold tickers ADA/ETH", order_command)

        # update 7
        # taker price (bid) is above threshold
        market_data = [{"ask":  0.00032485132, "bid":  0.00032485131}]
        order_command = fto.update_from_exchange(resp, market_data)
        self.assertEqual("hold tickers ADA/ETH", order_command)

        # update 8
        # taker price (bid) is above threshold
        market_data = [{"ask": 0.00032485132, "bid": 0.00032485151}]
        order_command = fto.update_from_exchange(resp, market_data)
        self.assertEqual("hold tickers ADA/ETH", order_command)

        # update 9
        # taker price (bid) is below threshold
        market_data = [{"ask": 0.00032485132, "bid": 0.00032485131 * 0.94}]
        order_command = fto.update_from_exchange(resp, market_data)
        self.assertEqual("cancel", order_command)

        # update 10
        # taker price (bid) is above threshold
        # should cancel because of maximum number of updates reached
        market_data = [{"ask": 0.00032485132, "bid": 0.00032485151}]
        order_command = fto.update_from_exchange(resp, market_data)
        self.assertEqual("cancel", order_command)

    def test_fok_threshold_order_manager_canceled_on_threshold(self):
        ex = ccxtExchangeWrapper.load_from_id("binance") # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        ex._offline_tickers = {

           0: {"ETH/BTC": {"ask": 1, "bid": 0.99}},
           1: {"ETH/BTC": {"ask": 1, "bid": 0.95}},
           2: {"ETH/BTC": {"ask": 1, "bid": 0.99}},
           3: {"ETH/BTC": {"ask": 1, "bid": 0.99}},
           4: {"ETH/BTC": {"ask": 1, "bid": 0.99}},
           5: {"ETH/BTC": {"ask": 1, "bid": 0.99}},
           6: {"ETH/BTC": {"ask": 1, "bid": 0.99}},
           7: {"ETH/BTC": {"ask": 1, "bid": 0.95}},
        }

        tickers = ex.fetch_tickers("ETH/BTC")

        taker_price = core.get_symbol_order_price_from_tickers("ETH","BTC", tickers)["price"]

        order = FokThresholdTakerPriceOrder.create_from_start_amount("ETH/BTC", "ETH", 1, "BTC", taker_price,
                                                                     taker_price_threshold=-0.01,
                                                                     threshold_check_after_updates=5)

        om = ActionOrderManager(ex)
        om.request_trades = False

        om.add_order(order)

        while len(om.get_open_orders()) > 0:
            om.proceed_orders()

        closed_order = om.get_closed_orders()[0]  # type: FokThresholdTakerPriceOrder
        trade_order = closed_order.orders_history[0]  # type: TradeOrder

        self.assertEqual("closed", closed_order.status)
        self.assertEqual("canceled", trade_order.status)
        self.assertEqual(["#below_threshold"], order.tags)

        # updates of order:
        # 1 - order created
        # 2 .. 5 - order updated without requesting tickers
        # 6 - request ticker
        # 7 - receives ticker and send command to cancel. 2nd ticker is "bad" because first was used to get price
        #   - check's if it was canceled
        # 8 - updates trades order with the canceled response

        self.assertEqual(8, trade_order.update_requests_count)

    def test_fok_threshold_order_manager_canceled_on_updates_count(self):
        ex = ccxtExchangeWrapper.load_from_id("binance")  # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        ex._offline_tickers = {

            0: {"ETH/BTC": {"ask": 1, "bid": 0.99}},
            1: {"ETH/BTC": {"ask": 1, "bid": 0.96}},
            2: {"ETH/BTC": {"ask": 1, "bid": 0.96}},
            3: {"ETH/BTC": {"ask": 1, "bid": 0.96}},
            4: {"ETH/BTC": {"ask": 1, "bid": 0.96}},
            5: {"ETH/BTC": {"ask": 1, "bid": 0.96}},
            6: {"ETH/BTC": {"ask": 1, "bid": 0.96}},
            7: {"ETH/BTC": {"ask": 1, "bid": 0.96}},
        }

        tickers = ex.fetch_tickers("ETH/BTC")

        taker_price = core.get_symbol_order_price_from_tickers("ETH", "BTC", tickers)["price"]

        order = FokThresholdTakerPriceOrder.create_from_start_amount("ETH/BTC", "ETH", 1, "BTC", taker_price,
                                                                     max_order_updates=10,
                                                                     taker_price_threshold=-0.05,
                                                                     threshold_check_after_updates=5)

        om = ActionOrderManager(ex)
        om.request_trades = False

        om.add_order(order)

        while len(om.get_open_orders()) > 0:
            om.proceed_orders()

        closed_order = om.get_closed_orders()[0]  # type: FokThresholdTakerPriceOrder
        trade_order = closed_order.orders_history[0]  # type: TradeOrder

        self.assertEqual("closed", closed_order.status)
        self.assertEqual("canceled", trade_order.status)
        self.assertEqual(list(), order.tags)

        self.assertEqual(11, trade_order.update_requests_count)

    def test_cancel_by_time(self):
        fok_order_time = FokThresholdTakerPriceOrder("ADA/ETH", 1000, 0.32485131 / 1000, "sell", max_order_updates=10,
                                                time_to_cancel=0.1)

        order_command = fok_order_time.update_from_exchange({})

        ex = ccxtExchangeWrapper.load_from_id("binance")  # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        om = ActionOrderManager(ex)
        om.request_trades = False

        om.add_order(fok_order_time)
        om.proceed_orders()
        time.sleep(0.11)

        om.proceed_orders()
        om.proceed_orders()

        self.assertEqual(fok_order_time.status, "closed")
        self.assertIn("#timeout", fok_order_time.tags)


if __name__ == '__main__':
    unittest.main()
