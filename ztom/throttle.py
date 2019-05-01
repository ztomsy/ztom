from datetime import datetime
import time
import collections


class Throttle(object):

    REQUEST_TYPE_WEIGHT = {
        "single": 1,
        "load_markets": 1,
        "fetch_tickers": 1,
        "fetch_ticker": 1,
        "fetch_order_book": 1,
        "create_order": 1,
        "fetch_order": 1,
        "cancel_order": 1,
        "fetch_my_trades": 1,
        "fetch_balance": 1}

    def __init__(self, period: float = 60.0, requests_per_period: int = 60, requests_weights: dict = None):
        """

        Requests with the timestamps >=0 and < period_start + current_period_time are belong to respective period.

        :param period: period in seconds
        :param requests_per_period: maximumum amount of requests during the period
        """

        self.period = period
        self.requests_per_period = requests_per_period

        self.total_requests_current_period = int()

        self.requests_current_period = list()  # - list of requests in current period
        # dicts of:
        #  {"timestamp": timestamp, "request_type": request_type, "added": requests,
        #                                      "total_requests_to_time": net_requests}
        # request_type: type of request
        # added: number of requests of the type added on timestamp time
        # total_requests_to_time - cumulative number of "single" requests up to timestamp

        self._current_period_time = float()
        self._period_start_timestamp = 0.0
        self._requests_in_current_period = int()

        self.request_weights = Throttle.REQUEST_TYPE_WEIGHT

        if requests_weights is not None:
            self.request_weights.update(requests_weights)

        # min allowed time between single requests
        self.allowed_time_for_single_request = self.period / self.requests_per_period \
            if self.requests_per_period != 0 else 0

        self.periods_since_start = 0

    def update(self, current_time_stamp: float = None):
        """
        updates the internal time. If the time passed since the last update greater than period duration - the new
        period is initiated:
        - period start time is set as prev_period_time + number_of_periods*self.period
        - current period time is set in accordance to period start time
        - requests_current_


        :param current_time_stamp:
        :return:
        """

        if len(self.requests_current_period) > 0:
            self._period_start_timestamp = self.requests_current_period[0]["timestamp"]
        else:
            # nothing to update
            return False

        if current_time_stamp is None:
            current_time_stamp = datetime.now().timestamp()

        last_period_start_timestamp = self._period_start_timestamp

        number_of_periods_since_last_update = (current_time_stamp - last_period_start_timestamp) // self.period

        self._period_start_timestamp = last_period_start_timestamp + number_of_periods_since_last_update*self.period

        self._current_period_time = current_time_stamp - self._period_start_timestamp

        if number_of_periods_since_last_update > 0:
            self.periods_since_start += int(number_of_periods_since_last_update)

            self.requests_current_period = \
                [k for k in self.requests_current_period
                 if self._period_start_timestamp <= k["timestamp"] <= current_time_stamp]

            self.total_requests_current_period = \
                sum([k["added"] * self.request_weights[k["request_type"]] for k in self.requests_current_period])

        # else:
        #     self.requests_current_period = list()
        #     self.total_requests_current_period = 0

    def _add_request_for_current_period_time(self, timestamp, request_type: str = "single", requests: int = 1):

        net_requests = self.request_weights[request_type] * requests
        self.total_requests_current_period += net_requests

        self.requests_current_period.append({"timestamp": timestamp, "request_type": request_type, "added": requests
                                             })

        # return self.requests_in_current_period

    def add_request(self, timestamp=None,  request_type: str ="single", requests: int = 1):
        """
        adds the requests and updates the state of throttle  object
        :param timestamp: current or request's timestamp. if not set current system's timestamp will be used
        :param request_type:
        :param requests
        :return:
        """

        if timestamp is None:
            timestamp = datetime.timestamp(datetime.now())

        self._add_request_for_current_period_time(timestamp, request_type, requests )
        self.update(timestamp)

    def _calc_time_sleep_to_recover_requests_rate(self, current_period_time, requests_in_current_period) -> float:
        """
        Returns the sleep time to recover requests rate till the end of the current period.
        :return: sleep time in seconds
        """

        sleep_time = 0.0

        if requests_in_current_period * self.allowed_time_for_single_request > current_period_time:
            sleep_time = requests_in_current_period * self.allowed_time_for_single_request - current_period_time

        return sleep_time

    def sleep_time(self, timestamp=None):
        """
        get the current sleep time in seconds in order to maintain the maximun requests per period.

        :param timestamp: if not set - the current system's timestamp will be taken
        :return: sleep time in seconds
        """
        if timestamp is None:
            timestamp = datetime.timestamp(datetime.now())

       # self.update(timestamp)

        requests_in_current_period = 0
        if len(self.requests_current_period) > 0:
            requests_in_current_period = self.total_requests_current_period

        return self._calc_time_sleep_to_recover_requests_rate(timestamp - self._period_start_timestamp,
                                                              requests_in_current_period)

