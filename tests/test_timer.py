# -*- coding: utf-8 -*-
from .context import ztom
import unittest
import ztom.timer
import time

class TimerTestSuite(unittest.TestCase):

    def test_timer(self):
        zt_timer = ztom.timer.Timer()

        timestamp_start = time.time()

        zt_timer.notch("start")
        time.sleep(0.1)
        zt_timer.notch("notch1")
        time.sleep(0.3)
        zt_timer.notch("notch2")

        timestamps = zt_timer.timestamps("timestamp_")

        self.assertAlmostEqual(timestamp_start+0.1, timestamps["timestamp_notch1"], 1)
        self.assertAlmostEqual(timestamp_start + 0.1 + 0.3, timestamps["timestamp_notch2"], 1)


if __name__ == '__main__':
    unittest.main()
