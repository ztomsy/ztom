# -*- coding: utf-8 -*-
from .context import ztom

import unittest
import os
import time
import uuid


# todo - tests for reports directories creation

class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def setUp(self):
        self.default_config = "_config_default.json"
        self.default_log = "_log_default.log"

        self.bot = ztom.Bot(self.default_config, self.default_log)

    def test_create_bot(self):
        self.bot.load_config_from_json(self.default_config)

        self.assertEqual(self.bot.api_key["apiKey"], "testApiKey")
        self.assertEqual(self.bot.server_id, "CORE1")

        uuid_obj = uuid.UUID(self.bot.session_uuid)

        self.assertEqual(self.bot.session_uuid, str(uuid_obj))

        # todo: test for checking if log file created

    def test_load_config_from_yml(self):
        bot = ztom.Bot("_config_default.yml", self.default_log)
        bot.load_config_from_yml(bot.config_filename)

        self.assertEqual(bot.api_key["apiKey"], "testApiKey")
        self.assertEqual(bot.server_id, "CORE2")

    def test_load_config_from_file(self):
        bot = ztom.Bot("_config_default.yml", self.default_log)
        bot.load_config_from_file(bot.config_filename)

        self.assertEqual(bot.api_key["apiKey"], "testApiKey")
        self.assertEqual(bot.server_id, "CORE2")

        bot = ztom.Bot("_config_default.json", self.default_log)
        bot.load_config_from_file(bot.config_filename)

        self.assertEqual(bot.api_key["apiKey"], "testApiKey")
        self.assertEqual(bot.server_id, "CORE1")

        with self.assertRaises(Exception) as context:
            bot = ztom.Bot("_config_default.txt", self.default_log)
            bot.load_config_from_file(bot.config_filename)

        self.assertTrue("Wrong config file extension. Should be json or yml." in context.exception.args)

    def test_cli_overrides_config_file(self):
        self.bot.debug = True

        self.bot.set_from_cli("--config _config_default.json --balance 2 --noauth --debug --exchange kraken".split(" "))

        self.bot.load_config_from_file(self.bot.config_filename)

        self.assertEqual(self.bot.debug, True)
        self.assertEqual(True, self.bot.noauth)

        self.assertEqual(self.bot.exchange_id, "kraken")

        self.assertEqual(self.bot.config_filename, "_config_default.json")

        self.assertEqual(self.bot.api_key["apiKey"], "testApiKey")
        self.assertEqual(self.bot.test_balance, 2)

    def test_load_offline_data(self):

        cli = "--balance 1 offline -ob test_data/order_books.csv -m test_data/markets.json"
        self.bot.set_from_cli(cli.split(" "))

        print("OK")



    def test_multi_logging(self):
        self.bot.log(self.bot.LOG_ERROR, "ERRORS", list(("error line 1", "error line 2", "error line 3")))

    def test_logging(self):
        default_config = "_config_default.json"
        default_log = "_log_default.log"

        bot = ztom.Bot(default_config, default_log)

        bot.log(bot.LOG_INFO, "Test")

        with open(default_log, 'r') as myfile:
            log_file = myfile.read()
            myfile.close()

        self.assertGreater(log_file.find("Test"), -1)

        handlers = bot.logger.handlers[:]
        for handler in handlers:
            handler.close()
            bot.logger.removeHandler(handler)

        os.remove(default_log)

    def test_timer(self):
        timer = ztom.Timer()
        timer.notch("start")
        time.sleep(0.1)
        timer.notch("finish")

        self.assertEqual(timer.notches[0]["name"], "start")
        self.assertAlmostEqual(timer.notches[1]["duration"], 0.1, 1)

    def test_reporter_init(self):
        self.bot.load_config_from_file(self.default_config)

        self.assertEqual(self.bot.influxdb["measurement"], "status")
        self.bot.init_remote_reports()

    def test_exchange_init(self):
        pass

    def test_min_amount_ok(self):
        self.bot.min_amounts = {"BTC": 0.002, "ETH": 0.02, "BNB": 1, "USDT": 20}
        symbol = "ETH/BTC"
        price = 0.03185046
        sure_coef = 1.003

        self.assertEqual((0.002 / 0.03185046) * 1.001, self.bot.min_order_amount(symbol, price))
        self.assertEqual((0.002 / 0.03185046) * 1.003,
                         self.bot.min_order_amount(symbol, price, sure_coefficient=sure_coef))

        self.assertEqual((1 / 0.00000233) * 1.003,
                         self.bot.min_order_amount("BTC/RUR", 0.00000233, {"RUR": 1}, sure_coefficient=sure_coef))

    def test_min_amount_not_ok(self):
        self.bot.min_amounts = {"BTC": 0.002, "ETH": 0.02, "BNB": 1, "USDT": 20}

        symbol = "ETH/RUB"
        price = 0.03185046

        self.assertEqual(0, self.bot.min_order_amount(symbol, price))
        self.assertEqual(0, self.bot.min_order_amount("ETH/BTC", 0.0))
        self.assertEqual(0, self.bot.min_order_amount("ETH/BTC", 0.03185046, {"BTC": 0.0}))

        self.bot.min_amounts = None
        self.assertEqual(0, self.bot.min_order_amount(symbol, price))


if __name__ == '__main__':
    unittest.main()
