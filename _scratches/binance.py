import sys
import json
import collections
import jsonpickle
import ztom
from ztom import bot
from ztom.orderbook import OrderBook
from ztom.trade_order_manager import *
import ccxt

start_cur = "ETH"
dest_cur = "BTC"
start_amount = 0.05

bot = ztom.Bot("../_binance.json", "binance_test.log")

bot.start_currency = [start_cur]  # legacy from Bot class

bot.load_config_from_file(bot.config_filename)

bot.init_logging(bot.log_filename)
bot.init_exchange()
bot.load_markets()
bot.load_balance()
bot.fetch_tickers()


order_history_file_name = ztom.utils.get_next_filename_index("./{}_all_objects.json".format(bot.exchange_id))


def test_trade(start_cur, dest_cur, start_amount):

    balance = dict()
    while not balance:
        try:
            balance = bot.exchange.fetch_free_balance()
        except:
            print("Retry fetching balance...")

    init_balance = dict()
    init_balance[start_cur] = balance[start_cur]
    init_balance[dest_cur] = balance[dest_cur]

    symbol = ztom.core.get_symbol(start_cur, dest_cur, bot.markets)
    ob_array = dict()
    while not ob_array:
        try:
            ob_array = bot.exchange._ccxt.fetch_order_book(symbol, 100)
        except:
            print("retying to fetch order book")

    order_book = OrderBook(symbol, ob_array["asks"], ob_array["bids"])

    price = order_book.get_depth_for_destination_currency(start_amount, dest_cur).total_price * 1.0002

    order1 = ztom.TradeOrder.create_limit_order_from_start_amount(symbol, start_cur, start_amount, dest_cur, price)

    order_resps = collections.OrderedDict()

    om = ztom.OrderManagerFok(order1, None, 100, 10)

    try:
        om.fill_order(bot.exchange)
    except OrderManagerErrorUnFilled as e:
        print("Unfilled order. Should cancel and recover/continue")
        try:
            print("Cancelling....")
            om.cancel_order(bot.exchange)
            print(".. Ok")
        except OrderManagerCancelAttemptsExceeded:
            print("Could not cancel. Check the exchange.")

    except OrderManagerError as e:
        print("Unknown  Order Manager error")
        print(type(e).__name__, "!!!", e.args, ' ')

    except ccxt.errors.InsufficientFunds:
        print("Low balance!")
        sys.exit(0)

    except Exception as e:
        print("error")
        print(type(e).__name__, "!!!", e.args, ' ')
        sys.exit(0)

    results = list()

    if order1.filled > 0:
        i = 0
        while bool(results) is not True and i < 100:
            print("getting trades #{}".format(i))
            try:
                results = bot.exchange.get_trades_results(order1)
            except Exception as e:
                print(type(e).__name__, "!!!", e.args, ' ')
                print("retrying to get trades...")
            i += 1

        order1.update_order_from_exchange_resp(results)
        order1.fees = bot.exchange.fees_from_order_trades(order1)
    else:
        print("Order filled with Zero result... Try again")
        sys.exit()


    balance_after_order1 = dict(init_balance)

    i = 0
    while (balance_after_order1[start_cur] == init_balance[start_cur] or
           balance_after_order1[dest_cur] == init_balance[dest_cur]) and i < 50:
        try:
            balance = dict(bot.exchange.fetch_free_balance())
            balance_after_order1[start_cur], balance_after_order1[dest_cur] = balance[start_cur], balance[dest_cur]
        except:
            print("Error receiving balance")

        print("Balance receive attempt {}".format(i))
        i += 1

    all_data = dict()

    all_data["exchange_id"] = bot.exchange_id
    all_data["start_balance"] = init_balance
    all_data["balance_after_order1"] = balance_after_order1
    all_data["start_currency"] = start_cur
    all_data["dest_currency"] = dest_cur
    all_data["symbol"] = symbol
    all_data["price"] = price
    all_data["order1"] = order1
    all_data["order_book_1"] = order_book
    all_data["market"] = bot.markets[symbol]
    all_data["ticker"] = bot.tickers[symbol]
    all_data["balance_after_order1"] = balance_after_order1
    all_data["balance_diff_start_cur"] = init_balance[start_cur] - balance_after_order1[start_cur]
    all_data["balance_diff_dest_cur"] = init_balance[dest_cur] - balance_after_order1[dest_cur]
    all_data["check_balance_dest_curr_diff_eq_filled_dest_minus_fee"] = round(
        balance_after_order1[dest_cur] - (init_balance[dest_cur] + order1.filled_dest_amount -
                                          order1.fees[dest_cur]["amount"]),
        bot.exchange._ccxt.currencies[dest_cur]["precision"])

    all_data["check_balance_src_curr_diff_eq_filled_src"] =round(
        balance_after_order1[start_cur] - (init_balance[start_cur] - order1.filled_start_amount
                                           - order1.fees[start_cur]["amount"]),

        bot.exchange._ccxt.currencies[dest_cur]["precision"])

    # check if deal results are consistent with amount and fees
    if all_data["check_balance_dest_curr_diff_eq_filled_dest_minus_fee"] == 0 \
            and all_data["check_balance_src_curr_diff_eq_filled_src"] == 0:
        all_data["_check_trades_amount_fees"] = True
    else:
        all_data["_check_trades_amount_fees"] = False

    return all_data


report = dict()

print("Trade 1")
print("======================")
report["trade1"] = test_trade(start_cur, dest_cur, start_amount)
print("======================")
print("Trade 2")
report["trade2"] = test_trade(dest_cur, start_cur,
                              report["trade1"]["order1"].filled_dest_amount -
                              report["trade1"]["order1"].fees[dest_cur]["amount"])


print("Check Trade 1:{}".format(report["trade1"]["_check_trades_amount_fees"]))
print("Check Trade 2:{}".format(report["trade2"]["_check_trades_amount_fees"]))

j = jsonpickle.encode(report)

s = json.dumps(json.loads(j), indent=4, sort_keys=True)


with open(order_history_file_name, "w") as file:
    file.writelines(s)

sys.exit(0)
# d = ob.(bal_to_bid, dest_cur)
# price = d.total_price
# amount = d.total_quantity
