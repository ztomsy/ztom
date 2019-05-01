# -*- coding: utf-8 -*-
from .context import ztom

import unittest


class OrderBookTestSuite(unittest.TestCase):

    def ignore_test_orderbook(self):
        asks = [(1., 1.), (2., 3.)]
        bids = [(3., 1.)]
        orderbook = ztom.OrderBook('S', asks, bids)

        self.assertEqual(len(orderbook.csv_header()), 4)
        self.assertEqual(len(orderbook.csv_rows(6)), 4)

    def test_depth(self):
        ob = dict()
        ob["asks"] = [[0.0963510000, 2],
                      [0.0963880000, 2],
                      [0.0964390000, 3]]

        ob["bids"] = [[0.0963360000, 1],
                      [0.0963300000, 2],
                      [0.0963280000, 3]]

        orderbook = ztom.OrderBook("ETH/BTC", ob["asks"], ob["bids"])

        self.assertEqual(
            orderbook.get_depth(0.096351, "buy", "quote"),
            ztom.Depth(
                total_quantity=1.0,
                total_price=0.096351,
                depth=1,
                currency="base"
            )
        )

        # self.assertEqual(
        #     orderbook.get_depth(0.1, "buy", "quote"),
        #     tgk.Depth(
        #         total_quantity=1.0378574096360542,   1.037871947359135
        #         total_price=0.09635234963063667,
        #         depth=2,
        #         currency="base"
        #     )
        # )

        self.assertEqual(
            orderbook.get_depth(0.1, "buy", "quote"),
            ztom.Depth(
                total_quantity=1.037871947359135,
                total_price = 0.09635099999999999,
                depth = 1,
                currency = "base"
                )
        )


        self.assertEqual(
            orderbook.get_depth(1, "sell"),
            ztom.Depth(
                total_quantity=0.096336,
                total_price=0.096336,
                depth=1,
                currency="quote"
            )
        )
        self.assertEqual(
            orderbook.get_depth(5, "sell"),
            ztom.Depth(
                total_quantity=0.481652,
                total_price=0.09633040000000001,
                depth=3,
                currency="quote"
            )
        )
        # amount more than available in OrderBook

        self.assertEqual(ztom.Depth(
                    total_quantity=0.0963360000*1 + 0.0963300000*2+0.0963280000*3,
                    total_price=0.09633000000000001,
                    depth=3,
                    currency="quote", filled_share=6/10), orderbook.get_depth(10, "sell"))

    def test_sorted(self):
        ob = dict()
        ob["asks"] = [[3, 10],
                      [1, 2],
                      [2, 3]]

        ob["bids"] = [[5, 1],
                      [4, 2],
                      [6, 3]]

        orderbook = ztom.OrderBook("ETH/BTC", ob["asks"], ob["bids"])

        self.assertEqual(1, orderbook.asks[0].price)
        self.assertEqual(2, orderbook.asks[1].price)
        self.assertEqual(3, orderbook.asks[2].price)

        self.assertEqual(6, orderbook.bids[0].price)
        self.assertEqual(5, orderbook.bids[1].price)
        self.assertEqual(4, orderbook.bids[2].price)

    def test_trade_direction(self):
        ob = dict()
        ob["asks"] = [[3, 10],
                      [1, 2],
                      [2, 3]]

        ob["bids"] = [[5, 1],
                      [4, 2],
                      [6, 3]]

        orderbook = ztom.OrderBook("ETH/BTC", ob["asks"], ob["bids"])

        self.assertEqual("sell", orderbook.get_trade_direction_to_currency("BTC"))
        self.assertEqual("buy", orderbook.get_trade_direction_to_currency("ETH"))
        self.assertEqual(False, orderbook.get_trade_direction_to_currency("XYZ"))

    def test_order_book_depth_for_destination_currency(self):

        ob = dict()
        ob["asks"] = [[0.0963510000, 2],
                      [0.0963880000, 2],
                      [0.0964390000, 3]]

        ob["bids"] = [[0.0963360000, 1],
                      [0.0963300000, 2],
                      [0.0963280000, 3]]

        orderbook = ztom.OrderBook("ETH/BTC", ob["asks"], ob["bids"])

        self.assertEqual(orderbook.get_depth_for_destination_currency(0.1, "ETH"),
                         ztom.Depth(total_quantity=1.037871947359135, total_price=0.096351, depth=1, currency="base"))

        self.assertEqual(orderbook.get_depth_for_destination_currency(0.3, "ETH"),
                         ztom.Depth(total_quantity=3.1131883637, total_price=0.0963642302, depth=2, currency="base"))

        self.assertEqual(orderbook.get_depth_for_destination_currency(1, "BTC"),
                         ztom.Depth(total_quantity=0.0963360000, total_price=0.0963360000, depth=1,
                                    currency="quote"))

        self.assertEqual(orderbook.get_depth_for_destination_currency(5, "BTC"),
                         ztom.Depth(
                             total_quantity=0.481652,
                             total_price=0.09633040000000001,
                             depth=3,
                             currency="quote"))

    def test_order_book_depth_for_side(self):

        ob = dict()
        ob["asks"] = [[0.0963510000, 2],
                      [0.0963880000, 2],
                      [0.0964390000, 3]]

        ob["bids"] = [[0.0963360000, 1],
                      [0.0963300000, 2],
                      [0.0963280000, 3]]

        orderbook = ztom.OrderBook("ETH/BTC", ob["asks"], ob["bids"])

        self.assertEqual(orderbook.get_depth_for_trade_side(0.1, "buy"),
                         ztom.Depth(total_quantity=1.037871947359135, total_price=0.096351, depth=1, currency="base"))

        self.assertEqual(orderbook.get_depth_for_trade_side(1, "sell"),
                         ztom.Depth(total_quantity=0.0963360000, total_price=0.0963360000, depth=1,
                                    currency="quote"))


if __name__ == '__main__':
    unittest.main()