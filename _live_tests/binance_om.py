import ztom
import time
import datetime


bot = ztom.Bot("_binance_test.json")

bot.load_config_from_file(bot.config_filename)

bot.init_exchange()

if bot.offline:
    bot.init_offline_mode()

# bot.init_remote_reports()

bot.load_markets()

# init parameters
symbol = "ETH/BTC"
start_currency = "BTC"
dest_currency = "ETH"
start_amount = 0.002

order1_max_updates = 40
cancel_threshold = 0.001

order_manager_sleep = 0.5

ticker = bot.exchange.fetch_tickers(symbol)[symbol]

depth = 1

om = ztom.ActionOrderManager(bot.exchange, order1_max_updates, 50, 0.1)
om.log = bot.log  # override order manager logger to the bot logger
om.LOG_INFO = bot.LOG_INFO
om.LOG_ERROR = bot.LOG_ERROR
om.LOG_DEBUG = bot.LOG_DEBUG
om.LOG_CRITICAL = bot.LOG_CRITICAL

start_price = ticker["ask"] if ztom.core.get_trade_direction_to_currency(symbol, dest_currency) == "buy" \
    else ticker["bid"]

start_price = start_price * 0.995

order1 = ztom.FokOrder.create_from_start_amount(symbol, start_currency, start_amount,
                                                dest_currency, start_price, cancel_threshold, order1_max_updates)

om.add_order(order1)

while len(om.get_open_orders()) > 0:
    om.proceed_orders()
    time.sleep(order_manager_sleep)

closed_trade_orders = om.get_closed_orders()[0].orders_history
date_time = datetime.datetime.utcnow().timestamp()

reporter = ztom.MongoReporter("test", bot.exchange_id)
reporter.init_db(default_data_base="test", default_collection="trade_orders")

for order in closed_trade_orders:
    report = order.report()
    report_result = reporter.push_report(report, "orders_test")
    print(report)
    print(report_result.inserted_id)














