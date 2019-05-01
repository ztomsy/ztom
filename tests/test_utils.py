# -*- coding: utf-8 -*-
from .context import ztom
from ztom import utils
import unittest


class UtilsTestSuite(unittest.TestCase):

    def test_dict_value_from_path(self):

        data = {"tickers": {"ETH/BTC": {"ask": 1, "bid": 2, "mas": {"5": 5}}}}

        # ok
        path_list = "tickers ETH/BTC mas 5".split(" ")
        res = utils.dict_value_from_path(data, path_list)
        self.assertEqual(5, res)

        # ok case insensitive
        path_list = "TICKERS eth/btc MAS".split(" ")
        res = utils.dict_value_from_path(data, path_list)
        self.assertDictEqual({"5": 5}, res)

        # ok to receive dict
        path_list = "tickers ETH/BTC".split(" ")
        res = utils.dict_value_from_path(data, path_list)
        self.assertDictEqual({"ask": 1, "bid": 2, "mas": {"5": 5}}, res)

        # if path not found
        path_list = "tickers EXX/BTC mas 5".split(" ")  # getting the
        res = utils.dict_value_from_path(data, path_list)
        self.assertEqual(None, res)

        # if path not found
        path_list = "ticker ETH/BTC mas 5".split(" ")  # getting the
        res = utils.dict_value_from_path(data, path_list)
        self.assertEqual(None, res)

        # ok case sensitive
        path_list = "tickers ETH/BTC mas".split(" ")
        res = utils.dict_value_from_path(data, path_list)
        self.assertDictEqual({"5": 5}, res)

        # not ok with case sensitive
        path_list = "TICKERS eth/btc MAS".split(" ")
        res = utils.dict_value_from_path(data, path_list, True)
        self.assertEqual(None, res)


if __name__ == '__main__':
    unittest.main()
