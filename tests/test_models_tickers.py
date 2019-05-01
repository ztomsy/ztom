# -*- coding: utf-8 -*-
from .context import ztom
from ztom import ccxtExchangeWrapper
from ztom.models.tickers import Tickers
import unittest


class TickersModelTestSuite(unittest.TestCase):

    def test_model_tickers_list_from_dict(self):
        ex = ztom.ccxtExchangeWrapper.load_from_id("binance")  # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers.csv")

        tickers = ex.fetch_tickers()

        tickers_list = Tickers.bulk_list_from_tickers(ex.exchange_id, tickers)

        for t in tickers_list:
            self.assertEqual(t["exchange"], ex.exchange_id)
            self.assertEqual(t["ask"], tickers[t["symbol"]]["ask"])
            self.assertEqual(t["ask_quantity"], tickers[t["symbol"]]["askVolume"])


if __name__ == '__main__':
    unittest.main()
