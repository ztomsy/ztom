import copy
import datetime
import json
import logging
import sys

import ztom
from . import timer
from . import utils
from .cli import *
from .reporter import Reporter, MongoReporter
from .trade_order_manager import *
from .trade_orders import *
from .reporter_sqla import SqlaReporter
import yaml

class Bot:

    def __init__(self, default_config: str, log_filename=None):

        self.session_uuid = str(uuid.uuid4())
        self.fetch_number = 0
        self.errors = 0

        self.config_filename = default_config
        self.exchange_id = ""
        self.server_id = ""
        self.script_id = ""

        self.commission = float()

        self.api_key = dict()

        self.min_amounts = dict()

        self.max_trades_updates = 0

        self.order_update_total_requests = 0
        self.order_update_requests_for_time_out = 0
        self.order_update_time_out = 0
        self.max_oder_books_fetch_attempts = 0
        self.request_sleep = 0.0  # sleep time between requests in seconds
        self.max_order_update_attempts = 0
        self.om_proceed_sleep = 0.0

        self.timer = ...  # type: timer.Timer

        self.lap_time = float()
        self.max_requests_per_lap = 0.0

        self.test_balance = float()
        self.force_start_amount = float()

        self.debug = bool()
        self.run_once = False
        self.noauth = False
        self.offline = False

        self.recovery_server = ""

        self.tickers_file = str()
        self.offline_tickers_file = "test_data/tickers.csv"
        self.offline_order_books_file = ""
        self.offline_markets_file = "test_data/markets.json"



        self.logger = logging
        self.log_filename = log_filename

        self.logger = self.init_logging(self.log_filename)

        self.LOG_DEBUG = logging.DEBUG
        self.LOG_INFO = logging.INFO
        self.LOG_ERROR = logging.ERROR
        self.LOG_CRITICAL = logging.CRITICAL

        self.report_all_deals_filename = str()
        self.report_tickers_filename = str()
        self.report_deals_filename = str()
        self.report_prev_tickers_filename = str()

        self.report_dir = str()
        self.deals_file_id = int()

        self.influxdb = dict()
        self.reporter = None  # type: ztom.Reporter

        # self.mongo = None  # configuration for mongo type: dict
        # self.mongo_reporter = None # type: ztom.MongoReporter

        self.sqla = None  # configuration for sqlalchemy reporter
        self.sqla_reporter = None # type: SqlaReporter

        self.exchange = None # type: ztom.ccxtExchangeWrapper

        self.markets = dict()
        self.tickers = dict()

        self.balance = float()

        self.time = timer.Timer
        self.last_proceed_report = dict()

        # load config from json

    def load_config_from_file(self, config_file):

        with open(config_file) as json_data_file:
            cnf = json.load(json_data_file)

        for i in cnf:
            attr_val = cnf[i]
            if not bool(getattr(self, i)) and attr_val is not None:
                setattr(self, i, attr_val)

    def load_config_from_yml(self, yml_file):
        with open('items.yaml') as f:
            cnf = yaml.load(f, Loader=yaml.FullLoader)

            for i in cnf:
                attr_val = cnf[i]
                if not bool(getattr(self, i)) and attr_val is not None:
                    setattr(self, i, attr_val)

    def get_cli_parameters(self, args):
        return get_cli_parameters(args)

    # parse cli
    def set_from_cli(self, args):

        cli_args = self.get_cli_parameters(args)

        for i in cli_args.__dict__:
            attr_val = getattr(cli_args, i)
            if attr_val is not None:
                setattr(self, i, attr_val)

    #
    # init logging
    #

    def init_logging(self, file_log=None):

        log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        logger = logging.getLogger("bot")

        if file_log is not None:
            file_handler = logging.FileHandler(file_log)
            file_handler.setFormatter(log_formatter)
            logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

        logger.setLevel(logging.INFO)

        return logger

    def set_log_level(self, log_level):

        self.logger.setLevel(log_level)

    def log(self, level, msg, msg_list=None):
        if msg_list is None:
            self.logger.log(level, msg)
        else:
            self.logger.log(level, msg)
            for line in msg_list:
                self.logger.log(level, "... " + str(line))

    def init_reports(self, directory):

        self.deals_file_id = utils.get_next_report_filename(directory, self.report_deals_filename)

        self.report_deals_filename = self.report_deals_filename % (directory, self.deals_file_id)
        self.report_prev_tickers_filename = self.report_prev_tickers_filename % (directory, self.deals_file_id)
        self.report_dir = directory

    def init_remote_reports(self):

        if self.influxdb is not None and "enabled" in self.influxdb and self.influxdb["enabled"]:
            self.reporter = Reporter(self.server_id, self.exchange_id)
            self.reporter.init_db(self.influxdb["host"], self.influxdb["port"], self.influxdb["db"],
                                  self.influxdb["measurement"])

        # if self.mongo is not None and self.mongo["enabled"]:
        #     self.mongo_reporter = MongoReporter(self.server_id, self.exchange_id)
        #     self.mongo_reporter.init_db(self.mongo["host"], None, self.mongo["db"],
        #                                 self.mongo["tables"]["results"])
        # else:
        #     self.log(self.LOG_ERROR, "Mongo is not configured or disabled.. ")

        if self.sqla is not None and "enabled" in self.sqla and self.sqla["enabled"]:
            self.log(self.LOG_INFO, "SQLA Reporter Enabled")
            self.log(self.LOG_INFO, "SQLA connection string {}".format(self.sqla["connection_string"]))

            self.sqla_reporter = SqlaReporter(self.server_id, self.exchange_id)
            self.sqla_reporter.init_db(self.sqla["connection_string"])
            created_tables = self.sqla_reporter.create_tables()
            if len(created_tables) > 0:
                self.log(self.LOG_INFO, "... created tables {}".format(created_tables))





    def init_timer(self):
        self.timer = timer.Timer()

    def init_exchange(self):
        # exchange = getattr(ccxt, self.exchange_id)
        # self.exchange = exchange({'apiKey': self.api_key["apiKey"], 'secret': self.api_key["secret"] })
        # self.exchange.load_markets()
        if not self.noauth:
            self.exchange = ccxtExchangeWrapper.load_from_id(self.exchange_id, self.api_key["apiKey"],
                                                                     self.api_key["secret"])
        else:
            self.exchange = ztom.ccxtExchangeWrapper.load_from_id(self.exchange_id)

    def init_offline_mode(self):
        self.exchange.set_offline_mode(self.offline_markets_file, self.offline_tickers_file)

        if self.offline_order_books_file:
            self.exchange.load_offline_order_books_from_csv(self.offline_order_books_file)

        self.log(self.LOG_INFO, "Offline Mode")
        self.log(self.LOG_INFO, "..markets file: {}".format(self.offline_markets_file))
        self.log(self.LOG_INFO, "..tickers file: {}".format(self.offline_tickers_file))
        if self.offline_order_books_file:
            self.log(self.LOG_INFO, "..order books file: {}".format(self.offline_order_books_file))
        else:
            self.log(self.LOG_INFO, "..order books will be created from tickers")



    def load_markets(self):
        self.markets = self.exchange.load_markets()

    def load_balance(self):

        if self.test_balance > 0:
            self.balance = self.test_balance
            return self.test_balance
        else:
            self.balance = self.exchange.fetch_free_balance()[self.start_currency[0]] if not self.offline else 0.0
            return self.balance

    def get_order_books_async(self, symbols: list):
        """
        returns the dict of {"symbol": OrderBook} in offline mode the order book is single line - ticker price and big
         amount
        :param symbols: list of symbols to get orderbooks
        :return: returns the dict of {"symbol": OrderBook}
        """
        i = 0
        ob_array = list()

        while len(ob_array) < len(symbols) and i < self.max_oder_books_fetch_attempts:
            i += 1
            try:
                ob_array = self.exchange.get_order_books_async(symbols)
            except Exception as e:
                self.log(self.LOG_ERROR, "Error while fetching order books exchange_id:{} session_uuid:{}"
                                         " fetch_num:{}:".
                         format(self.exchange_id, self.session_uuid, self.fetch_number))
                self.log(self.LOG_ERROR, "Exception: {}".format(type(e).__name__))
                self.log(self.LOG_ERROR, "Exception body:", e.args)

                self.log(self.LOG_ERROR, "Sleeping before next request")
                time.sleep(self.request_sleep)

        if len(ob_array) < len(symbols):
            raise Exception("Could not fetch all order books. Fetched: {}".format(len(ob_array)))

        order_books = dict()
        for ob in ob_array:
            order_books[ob["symbol"]] = ztom.OrderBook(ob["symbol"], ob["asks"], ob["bids"])

        return order_books

    def fetch_tickers(self):
        self.fetch_number += 1
        self.tickers = self.exchange.fetch_tickers()
        return self.tickers

    def log_order_create(self, order_manager: ztom.OrderManagerFok):
        self.log(self.LOG_INFO, "Tick {}: Order {} created. Filled dest curr:{} / {} ".format(
            order_manager.order.update_requests_count,
            order_manager.order.id,
            order_manager.order.filled_dest_amount,
            order_manager.order.amount_dest))

    # here is the sleep between updates is implemented! needed to be fixed
    def log_order_update(self, order_manager: ztom.OrderManagerFok):
        self.log(self.LOG_INFO, "Order {} update req# {}/{} (to timer {}). Status:{}. Filled amount:{} / {} ".format(
            order_manager.order.id,
            order_manager.order.update_requests_count,
            order_manager.updates_to_kill,
            self.order_update_requests_for_time_out,
            order_manager.order.status,
            order_manager.order.filled,
            order_manager.order.amount))

        now_order = datetime.now()

        if order_manager.order.status == "open" and \
                order_manager.order.update_requests_count >= self.order_update_requests_for_time_out:

            if order_manager.order.update_requests_count >= order_manager.updates_to_kill:
                self.log(self.LOG_INFO, "...last update will no sleep")

            else:
                self.log(self.LOG_INFO, "...reached the number of order updates for timeout")

                if (now_order - order_manager.last_update_time).total_seconds() < self.order_update_time_out:
                    self.log(self.LOG_INFO, "...sleeping while order update for {}".format(self.order_update_time_out))
                    time.sleep(self.order_update_time_out)

                order_manager.last_update_time = datetime.now()

    def log_on_order_update_error(self, order_manager, exception):
        self.log(self.LOG_ERROR, "Error updating  order_id: {}".format(order_manager.order.id))
        self.log(self.LOG_ERROR, "Exception: {}".format(type(exception).__name__))

        for ll in exception.args:
            self.log(self.LOG_ERROR, type(exception).__name__ + ll)

        return True

    def assign_updates_functions_for_order_manager(self):
        OrderManagerFok.on_order_create = lambda _order_manager: self.log_order_create(_order_manager)
        OrderManagerFok.on_order_update = lambda _order_manager: self.log_order_update(_order_manager)
        OrderManagerFok.on_order_update_error = lambda _order_manager, _exception: self.log_on_order_update_error(
            _order_manager, _exception)

    def do_trade(self, symbol, start_currency, dest_currency, amount, side, price):

        order = TradeOrder.create_limit_order_from_start_amount(symbol, start_currency, amount, dest_currency, price)

        if self.offline:
            o = self.exchange.create_order_offline_data(order, 10)
            self.exchange._offline_order = copy.copy(o)
            self.exchange._offline_trades = copy.copy(o["trades"])
            self.exchange._offline_order_update_index = 0
            self.exchange._offline_order_cancelled = False

        order_manager = OrderManagerFok(order, None, updates_to_kill=self.order_update_total_requests,
                                        max_cancel_attempts=self.order_update_total_requests,
                                        max_order_update_attempts=self.order_update_total_requests,
                                        request_sleep=self.request_sleep)
        order_manager.log = self.log
        order_manager.LOG_INFO = self.LOG_INFO
        order_manager.LOG_ERROR = self.LOG_ERROR
        order_manager.LOG_DEBUG = self.LOG_DEBUG
        order_manager.LOG_CRITICAL = self.LOG_CRITICAL

        try:
            order_manager.fill_order(self.exchange)
        except OrderManagerErrorUnFilled:
            try:
                self.log(self.LOG_INFO, "Cancelling order...")
                order_manager.cancel_order(self.exchange)

            except OrderManagerCancelAttemptsExceeded:
                self.log(self.LOG_ERROR, "Could not cancel order")
                self.errors += 1

        except Exception as e:
            self.log(self.LOG_ERROR, "Order error")
            self.log(self.LOG_ERROR, "Exception: {}".format(type(e).__name__))
            self.log(self.LOG_ERROR, "Exception body:", e.args)
            self.log(self.LOG_ERROR, order.info)

            self.errors += 1
        return order

    def get_trade_results(self, order: TradeOrder):

        results = list()
        i = 0
        while bool(results) is not True and i < self.max_trades_updates:
            self.log(self.LOG_INFO, "getting trades #{}".format(i))
            try:
                results = self.exchange.get_trades_results(order)
            except Exception as e:
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "retrying to get trades... after sleep for {}s".format(self.request_sleep))

                time.sleep(self.request_sleep)
                self.log(self.LOG_INFO, "sleep done")
            i += 1

        return results

    def create_recovery_data(self, deal_uuid, start_cur: str, dest_cur: str, start_amount: float,
                             best_dest_amount: float, leg: int) -> dict:
        recovery_dict = dict()
        recovery_dict["deal-uuid"] = deal_uuid
        recovery_dict["symbol"] = core.get_symbol(start_cur, dest_cur, self.markets)
        recovery_dict["start_cur"] = start_cur
        recovery_dict["dest_cur"] = dest_cur
        recovery_dict["start_amount"] = start_amount
        recovery_dict["best_dest_amount"] = best_dest_amount
        recovery_dict["leg"] = leg  # order leg to recover from
        recovery_dict["timestamp"] = time.time()

        return recovery_dict

    def print_recovery_data(self, recovery_data):
        self.log(self.LOG_INFO, "leg {}".format(recovery_data["leg"]))
        self.log(self.LOG_INFO, "Recover  {} {} -> {} {} ".
                 format(recovery_data["start_cur"], recovery_data["start_amount"],
                        recovery_data["dest_cur"], recovery_data["best_dest_amount"]))

    def send_recovery_request(self, recovery_data: dict):
        """
        could be used to call the external server for some actions. Server is excluded from the release
        """
        pass
        # self.log(self.LOG_INFO, "Sending recovery request...")
        # try:
        #
        #     resp = rest_server.rest_call_json(
        #         "{}:{}/order/".format(self.recovery_server["host"], self.recovery_server["port"]),
        #         recovery_data, "PUT")
        #
        # except Exception as e:
        #     self.log(self.LOG_ERROR, "Could not send recovery request")
        #     self.log(self.LOG_ERROR, "Exception: {}".format(type(e).__name__))
        #     self.log(self.LOG_ERROR, "Exception body:", e.args)
        #     return False
        #
        # self.log(self.LOG_INFO, "Response: {}".format(resp))


    @staticmethod
    def get_report_fields():
        return list(["field1", "field2"])

    def get_deal_report(self, data: dict, recovery_data, order1: TradeOrder):

        report_fields = self.get_report_fields()

        report = dict()

        wt = copy.copy(data)

        # adding report data which  not included in deal's data
        wt["server-id"] = self.server_id
        wt["exchange-id"] = self.exchange_id
        wt["dbg"] = self.debug
        wt["session-uuid"] = self.session_uuid
        wt["errors"] = self.errors
        wt["fetch_number"] = self.fetch_number

        wt["status"] = "InRecovery" if len(recovery_data) > 0 else data["status"]

        wt["order-status"] = order1.status if order1 is not None else None

        wt["order-filled"] = order1.filled / order1.amount if order1 is not None and order1.amount != 0 else 0.0

        wt["order-updates"] = order1.update_requests_count if order1 is not None else None

        wt["order-price-fact"] = order1.cost / order1.filled if order1 is not None and order1.filled != 0 else 0.0

        wt["order-fee"] = order1.fees[order1.dest_currency]["amount"] if order1 is not None and \
                                                                        order1.dest_currency in order1.fees else None


        # collect timer data
        time_report = self.timer.results_dict()

        for f in time_report:
            report_fields.append(f)
            wt[f] = time_report[f]

        # copy working triangle data into report
        for f in report_fields:
            if f in wt:
                report[f] = wt[f]

        return report

    def log_report(self, report):
        for r in self.get_report_fields():
            self.log(self.LOG_INFO, "{} = {}".format(r, report[r] if r in report else "None"))

    def send_remote_report(self, report):
        if self.reporter is not None:
            for r in report:
                self.reporter.set_indicator(r, report[r])


            try:
                self.reporter.push_to_influx()
                self.log(self.LOG_INFO, "Sending report to influx....")

            except Exception as e:
                self.log(self.LOG_ERROR, "...could not send the report")
                self.log(self.LOG_ERROR, e.args)


    def min_order_amount(self, symbol: str, price:float, min_amounts: dict() = None, sure_coefficient: float = 1.001):
        """
        Get the minimum order amount for trading pair. The result amount is multiplied on sure_coefficient in order
        to avoid price fluctuations. Returns zero if there is no setting for some currency or wrong price. Could be used
        for exchanges which are not providing minimum order amount or for controlling the minimum amounts.

        :param symbol: pair symbol
        :param price: price of order
        :param min_amounts: dict with the min_amounts: "min_amounts": {"BTC": 0.002, "ETH": 0.02, "BNB": 1, "USDT": 20}.
         Could be taken from bot/config (by default) or set explicitly.
        :param sure_coefficient: coefficient applied to min amouint. 1.001 by default

        :return:float : min_amount
        """

        min_amounts = min_amounts or self.min_amounts
        quote_currency = symbol.split("/")[1]

        if min_amounts is None or quote_currency not in min_amounts or min_amounts[quote_currency] == 0:
            return 0.0

        if price == 0:
            return 0.0

        return min_amounts[quote_currency]*sure_coefficient / price



    @staticmethod
    def print_logo(product=""):
        print('TTTTTTTTTT    K    K     GGGGG')
        print('    T         K   K     G')
        print('    T         KKKK      G')
        print('    T         K  K      G  GG')
        print('    T         K   K     G    G')
        print('    T         K    K     GGGGG')
        print('-' * 36)
        print('          %s               ' % product)
        print('-' * 36)
