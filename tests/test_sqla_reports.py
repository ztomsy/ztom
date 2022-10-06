# -*- coding: utf-8 -*-
from .context import ztom
from ztom import ccxtExchangeWrapper
from ztom import TradeOrder
from ztom import ActionOrder, ActionOrderManager
from ztom import TradeOrderReport
import datetime, pytz

from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, func, TIMESTAMP, Float, JSON


import unittest


class SqlaReporterTestSuite(unittest.TestCase):

    def test_trade_order_report_from_trade_order_after_fill(self):

        order = ActionOrder.create_from_start_amount("ETH/BTC","BTC", 1, "ETH", 0.01)

        ew = ccxtExchangeWrapper.load_from_id("binace")  # type: ccxtExchangeWrapper
        ew.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")
        om = ActionOrderManager(ew)

        om.add_order(order)
        while len(om.get_open_orders()) > 0:
            om.proceed_orders()

        trade_order = om.get_closed_orders()[0].orders_history[0]  # type: TradeOrder

        order_report = TradeOrderReport.from_trade_order(trade_order, datetime.datetime.now(tz=pytz.timezone("UTC")),
                                                         supplementary={"order_no": 1})

        self.assertEqual(order_report.symbol, trade_order.symbol)
        self.assertEqual(order_report.side, trade_order.side)
        self.assertEqual(order_report.amount, trade_order.amount)
        self.assertEqual(order_report.filled, trade_order.filled)
        self.assertEqual(order_report.cost, trade_order.cost)

        self.assertListEqual(order_report.trades, trade_order.trades)

        self.assertDictEqual(order_report.timestamp_closed, trade_order.timestamp_closed)
        self.assertDictEqual(order_report.timestamp_open, trade_order.timestamp_open)

        self.assertEqual(order_report.start_currency, trade_order.start_currency)
        self.assertEqual(order_report.start_currency, trade_order.start_currency)

        self.assertEqual("fill", order_report.supplementary["parent_action_order"]["state"])
        self.assertEqual(1, order_report.supplementary["order_no"])













if __name__ == '__main__':
    unittest.main()
