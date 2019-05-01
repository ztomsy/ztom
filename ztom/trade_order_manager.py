from ztom import TradeOrder
from ztom.exchange_wrapper import ccxtExchangeWrapper
from datetime import datetime
import time

class OrderManagerError(Exception):
    pass


class OrderManagerErrorUnFilled(Exception):
    pass


class OrderManagerErrorSkip(Exception):
    pass


class OrderManagerCancelAttemptsExceeded(Exception):
    pass


class OrderManagerFok(object):

    # limits - dict of limits to wait till cancel the order. ex: {"BTC": 0.002, "ETH": 0.02, "BNB": 1, "USDT": 20}
    # updates_to_kill - number of updates after which to cancel the order if it's not filled
    # usage:
    # after init and the update of the order call the proceed_update
    # it should return:
    # - "complete_order" if the order was fully filled within the requests limit
    # - "cancel" to cancel the order because max amount of updates was reached and filled more that min amount so it's
    #    possible to recover
    # - "skip" - when the order have not reached the min amount within the number of updates limit.
    LOG_DEBUG = "DEBUG"
    LOG_INFO = "INFO"
    LOG_ERROR = "ERROR"
    LOG_CRITICAL = "CRITICAL"

    def __init__(self, order: TradeOrder, limits=None, updates_to_kill=100, max_cancel_attempts=10,
                 max_order_update_attempts=1, request_sleep=0.0):
        """
        Creates single order FOK order manager.
        :param order:
        :param limits:
        :param updates_to_kill:
        :param max_cancel_attempts:
        :param max_order_update_attempts:
        :param request_sleep:
        :param cancel_threshold: cancel current trade order (when the other conditions are met) only if the remained
         amount to fill is greater than this threshold. This is for avoiding the situation of creating new order for
        less than minimun amount. Usually should be minimum order amount for the order's pair + commission (if applied).
        In ccxt: markets[symbol]["limits"]["amount"]["min"]
        """
        self.order = order

        self.min_filled_dest_amount = float
        self.min_filled_src_amount = float


        self.updates_to_kill = updates_to_kill
        self.max_cancel_attempts = max_cancel_attempts
        self.max_order_requests_attempts = max_order_update_attempts
        self.request_sleep = request_sleep
        # self.cancel_threshold = cancel_threshold

        self.order_update_requests = 0

        self.next_actions_list = ["hold," "cancel", "create_new"]
        self.next_action = str

        self.limits = dict

        self.min_filled_amount = float  # min amount of filled quote currency. should check cost in order to maintain

        if limits is not None:
            self.set_filled_min_amount(limits)

        self.last_response = dict()

        self.last_update_time = datetime(1, 1, 1, 1, 1, 1, 1)

    def log(self, level, msg, msg_list=None):
        if msg_list is None:
            print("{} {}".format(level, msg))
        else:
            print("{} {}".format(level, msg))
            for line in msg_list:
                print("{} ... {}".format(level, line))

    def set_filled_min_amount(self, limits: dict):
        self.limits = limits
        if self.order.symbol.split("/")[1] in limits:
            self.min_filled_amount = limits[self.order.symbol.split("/")[1]]
        else:
            raise OrderManagerError("Limit for {} not found".format(self.order.symbol))

    def on_order_create(self):
        print("Order {} created. Filled dest curr:{} / {} ".format(self.order.id, self.order.filled_dest_amount,
                                                                   self.order.amount_dest))
        return True

    def on_order_update(self):
        print("Order {} updated #{}/{}. Filled dest curr:{} / {} ".format(self.order.id,
                                                                         self.order.update_requests_count,
                                                                         self.updates_to_kill,
                                                                         self.order.filled_dest_amount,
                                                                   self.order.amount_dest))

        return True

    def on_order_update_error(self, exception):
        print("Error on order_id: {}".format(self.order.id))
        print("Exception: {}".format(type(exception).__name__))
        print("Exception body:", exception.args)
        return True

    def proceed_update(self):
        response = dict()

        # if self.order.update_requests_count >= self.updates_to_kill > 0 and\
        #         (self.order.cost > self.min_filled_amount) and (self.order.status != "closed" or
        #                                                           self.order.status != "canceled"):
        #     response["action"] = "cancel"
        #     response["reason"] = "max number of updates and min amount reached"
        #     self.last_response = response
        #     return response

        if (self.order_update_requests +1 >= self.updates_to_kill) and\
                (self.order.status != "closed" or self.order.status != "canceled"):

            response["action"] = "cancel"
            response["reason"] = "max number of updates reached"
            response["status"] = self.order.status
            self.last_response = response
            return response

        elif self.order.status == "closed" or self.order.status == "canceled":
            response["action"] = "complete_order"
            response["reason"] = "order closed"
            response["status"] = self.order.status
            self.last_response = response
            return response

        response["action"] = "hold"
        response["reason"] = "max number of updates/limits not reached"
        self.last_response = response
        return response

    def _create_order(self, exchange_wrapper: ccxtExchangeWrapper):

        results = None
        i = 0
        while bool(results) is not True and i < self.max_order_requests_attempts:
            self.log(self.LOG_INFO, ".. placing order #{}/{}".format(i, self.max_order_requests_attempts))
            try:
                results = exchange_wrapper.place_limit_order(self.order)
            except Exception as e:
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "retrying to place order... after sleep for {}s".format(self.request_sleep))
                time.sleep(self.request_sleep)
                self.log(self.LOG_INFO, "sleep done")
            i += 1

        return results

    def _update_order(self, exchange_wrapper: ccxtExchangeWrapper):
        results = None
        i = 0
        while bool(results) is not True and i < self.max_order_requests_attempts:
            self.log(self.LOG_INFO, ".. getting update attempt #{}/{}".format(i, self.max_order_requests_attempts))
            try:
                results = exchange_wrapper.get_order_update(self.order)
            except Exception as e:
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "retrying to get order UPDATE... after sleep for {}s".format(self.request_sleep))
                time.sleep(self.request_sleep)
                self.log(self.LOG_INFO, "sleep done")
            i += 1

        return results

    def _cancel_order(self, exchange_wrapper: ccxtExchangeWrapper):
        exchange_wrapper.cancel_order(self.order)


    # blocking method !!!!!
    def cancel_order(self, exchange):
        # cancel_attempt = 0
        #
        # while self.order.status != "canceled" and self.order.status != "closed":
        #     cancel_attempt += 1
        #     try:
        #         self._cancel_order(exchange)
        #
        #     except Exception as e:
        #         self.on_order_update_error(e)
        #
        #     finally:
        #         resp = None
        #         try:
        #             resp = self._update_order(exchange)
        #
        #         except Exception as e1:
        #             self.on_order_update_error(e1)
        #
        #         finally:
        #             self.order.update_order_from_exchange_resp(resp)
        #             self.on_order_update()
        #
        #         if cancel_attempt >= self.max_cancel_attempts:
        #             raise OrderManagerCancelAttemptsExceeded("Cancel Attempts Exceeded")

        cancel_attempt = 0

        while cancel_attempt < self.max_cancel_attempts:
            cancel_attempt += 1
            try:
                self.log(self.LOG_INFO, ".. Canceling order attempt #{}/{}".format(cancel_attempt,
                                                                                   self.max_cancel_attempts))
                self._cancel_order(exchange)

            except Exception as e:
                self.log(self.LOG_ERROR, "Cancel error...")
                self.log(self.LOG_ERROR, type(e).__name__)
                self.log(self.LOG_ERROR, e.args)
                self.log(self.LOG_INFO, "Pause for {}s".format(self.request_sleep))
                time.sleep(self.request_sleep)

            finally:
                self.log(self.LOG_INFO, "Updating the Trade Order to check if it was canceled or closed...")
                resp = self._update_order(exchange)

                self.order.update_order_from_exchange_resp(resp)
                self.on_order_update()

                self.log(self.LOG_INFO, "Update resp: {}".format(resp))
                if resp is not None and "status" in resp and (resp["status"] == "closed"
                                                              or resp["status"] == "canceled"):
                    self.log(self.LOG_INFO, "... canceled with status {}".format(resp["status"]))

                    return True
            if cancel_attempt >= self.max_cancel_attempts:
                raise OrderManagerCancelAttemptsExceeded("Cancel Attempts Exceeded")

        return None

    # blocking method !!!!!
    def fill_order(self, exchange):

        order_resp = self._create_order(exchange)

        if order_resp is None:
            raise OrderManagerError("Could not create Order")

        self.order.update_order_from_exchange_resp(order_resp)
        self.on_order_create()

        while  self.proceed_update()["action"] == "hold":
            self.order_update_requests += 1
            update_resp = None
            try:
                update_resp = self._update_order(exchange)
            except Exception as e:
                self.on_order_update_error(e)
            finally:
                self.order.update_order_from_exchange_resp(update_resp)
                self.on_order_update()



        if self.last_response["action"] == "complete_order":
            return True

        if self.last_response["action"] == "cancel":
            raise OrderManagerErrorUnFilled("Order not filled: {}".format(self.last_response["reason"]))

        raise OrderManagerError("Order not filled: Unknown error")
