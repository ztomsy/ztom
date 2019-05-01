# -*- coding: utf-8 -*-
from .context import ztom
from ztom import Throttle
import datetime as datetime
import unittest


class ThrottleTestSuite(unittest.TestCase):

    def test_throttle_create(self):
        throttle = Throttle(100, 1000)

        self.assertEqual(100,  throttle.period)
        self.assertEqual(1000, throttle.requests_per_period)

        self.assertEqual(0.0, throttle._current_period_time)
        self.assertEqual(0.0, throttle._requests_in_current_period)
        self.assertEqual(0.0, throttle._period_start_timestamp)

        self.assertEqual(0.1, throttle.allowed_time_for_single_request)

    def test_create_throttle_with_request_weights(self):
        # default

        request_type_weight = {
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

        throttle = Throttle(60, 1000)
        self.assertDictEqual(request_type_weight, throttle.request_weights)

        # some fields changed

        request_type_weight = {
            "fetch_tickers": 10,
            "fetch_my_trades": 66
        }

        throttle = Throttle(60, 100, request_type_weight)

        self.assertDictEqual(
            {
                "single": 1,
                "load_markets": 1,
                "fetch_tickers": 10,
                "fetch_ticker": 1,
                "fetch_order_book": 1,
                "create_order": 1,
                "fetch_order": 1,
                "cancel_order": 1,
                "fetch_my_trades": 66,
                "fetch_balance": 1},
            throttle.request_weights)

        # changed and new added
        request_type_weight = {
            "fetch_tickers": 13,
            "fetch_my_trades": 67,
            "modify_order": 3}
        throttle = Throttle(60, 100, request_type_weight)

        self.assertDictEqual(
            {
                "single": 1,
                "load_markets": 1,
                "fetch_tickers": 13,
                "fetch_ticker": 1,
                "fetch_order_book": 1,
                "create_order": 1,
                "fetch_order": 1,
                "cancel_order": 1,
                "fetch_my_trades": 67,
                "modify_order": 3,
                "fetch_balance": 1},

            throttle.request_weights)

    def test_calc_time_sleep_to_recover_requests_rate(self):
        throttle = Throttle(60, 1000)

        self.assertEqual(0.06, throttle.allowed_time_for_single_request)

        # we should not sleep because have 1 request in allowed_time_for_single_request
        self.assertEqual(0, throttle._calc_time_sleep_to_recover_requests_rate(0.06, 1))

        # more time for single request
        self.assertEqual(0, throttle._calc_time_sleep_to_recover_requests_rate(0.07, 1))

        # less time for single request
        self.assertAlmostEqual(0.01, throttle._calc_time_sleep_to_recover_requests_rate(0.05, 1), 8)

        # more requests than allowed in current_time - so we need to sleep more
        self.assertAlmostEqual(0.07, throttle._calc_time_sleep_to_recover_requests_rate(0.05, 2), 8)
        self.assertAlmostEqual(0.13, throttle._calc_time_sleep_to_recover_requests_rate(0.05, 3), 8)

    def test_add_single_request(self):
        throttle = Throttle(60, 1000)

        throttle._add_request_for_current_period_time(1)
        throttle._add_request_for_current_period_time(2)
        throttle._add_request_for_current_period_time(3)

        self.assertDictEqual(throttle.requests_current_period[0], {
            "timestamp": 1, "request_type": "single", "added": 1})

        self.assertDictEqual(throttle.requests_current_period[1], {
            "timestamp": 2, "request_type": "single", "added": 1})

        self.assertDictEqual(throttle.requests_current_period[2], {
            "timestamp": 3, "request_type": "single", "added": 1})

    def test_update(self):

        throttle = Throttle(60, 1000)

        # we will add first request at timestamp = 1
        throttle._add_request_for_current_period_time(1)
        throttle._add_request_for_current_period_time(2)
        throttle._add_request_for_current_period_time(3)

        throttle.update(60.1)

        self.assertEqual(1, throttle._period_start_timestamp)
        self.assertAlmostEqual(59.1, throttle._current_period_time, 6)

        self.assertDictEqual({'added': 1, 'timestamp': 1, 'request_type': 'single'}, throttle.requests_current_period[0])
        self.assertDictEqual({'added': 1, 'timestamp': 2, 'request_type': 'single'},
                             throttle.requests_current_period[1])
        self.assertDictEqual({'added': 1, 'timestamp': 3, 'request_type': 'single'},
                             throttle.requests_current_period[2])


        # 2 periods ahead
        throttle._add_request_for_current_period_time(100)
        throttle._add_request_for_current_period_time(181)
        throttle._add_request_for_current_period_time(182)
        throttle._add_request_for_current_period_time(183)

        throttle.update(183)
        self.assertAlmostEqual(2, throttle._current_period_time, 6)
        self.assertEqual(throttle._period_start_timestamp, 181)

        self.assertEqual(3, len(throttle.requests_current_period))

        self.assertDictEqual({'added': 1, 'timestamp': 181, 'request_type': 'single'},
                             throttle.requests_current_period[0])

        self.assertDictEqual({'added': 1, 'timestamp': 182, 'request_type': 'single'},
                             throttle.requests_current_period[1])

        self.assertDictEqual({'added': 1, 'timestamp': 183, 'request_type': 'single'},
                             throttle.requests_current_period[2])

        # add request to the of the new period
        throttle._add_request_for_current_period_time(240)
        throttle.update(240)
        self.assertEqual(throttle._period_start_timestamp, 181)
        self.assertEqual(4, len(throttle.requests_current_period))

        throttle._add_request_for_current_period_time(299)
        throttle._add_request_for_current_period_time(300)

        throttle.update(300)
        self.assertEqual(throttle._period_start_timestamp, 241)
        self.assertEqual(2, len(throttle.requests_current_period))
        self.assertEqual(299, throttle.requests_current_period[0]["timestamp"])
        self.assertEqual(300, throttle.requests_current_period[1]["timestamp"])

    def test_requests_sleep_time(self):

        throttle = Throttle(60, 1000)

        throttle.add_request(timestamp=0, request_type="single", requests=1)
        sleep = throttle.sleep_time(timestamp=0)

        self.assertEqual(0, throttle._current_period_time)
        self.assertEqual(1, len(throttle.requests_current_period))
        self.assertEqual(0.06, sleep)

        throttle.add_request(0.061)
        throttle.add_request(0.062)
        throttle.add_request(0.12)

        self.assertEqual(4, len(throttle.requests_current_period))

        sleep = throttle.sleep_time(timestamp=0.12)

        self.assertEqual(4, len(throttle.requests_current_period))

        # we have 4 requests in 0.12 seconds.  if we were requesting with the constant rate 1 request in 0.06s we
        # should be done to 0.24s. Since the current timestamp is 0.12 we should wait for 0.12s until the next
        # request
        self.assertEqual(0.12, sleep)

        throttle.add_request(59, requests=999)

        self.assertEqual(1003, throttle.total_requests_current_period)
        sleep = throttle.sleep_time(59)
        self.assertEqual(1003*0.06 - 59, sleep)

        throttle.add_request(60)
        self.assertEqual(1, throttle.total_requests_current_period)
        self.assertEqual(0.06, throttle.sleep_time(60))

        throttle.add_request(60.061)

        self.assertEqual(2, throttle.total_requests_current_period)
        self.assertAlmostEqual(0.059, throttle.sleep_time(60.061), 8)


if __name__ == '__main__':
    unittest.main()
