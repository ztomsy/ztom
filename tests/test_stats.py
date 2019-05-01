from .context import ztom
from ztom import stats_influx
import unittest
import json


class StatsTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_tags(self):
        deal_row = {"server-id" : "Arb2",

                    'BNB-after': 41.78100931,
                    'BNB-before': 41.78100931,
                    'after-start': 26125.586834,
                    'bal-after': 89.49255701,
                    'bal-before': 89.49255701,
                    'deal-uuid': '8091d4cf-e3b5-4b14-b935-ce3eb94de12c',
                    'status': 'Ok',
                    'tags': '#bal_reduce#incrStart',
                    'ticker': 434614,
                    'time-start': '2018-05-10 09:49:37.077615',
                    'timestamp': '2018-05-10 17:05:02.664449'}

        stats_db = stats_influx.StatsInflux("13.231.173.161", 8086, "dev", "deals_results")
        tags = list(["deal-uuid", "server-id"])

        tags_dict = dict()
        for i in tags:
            tags_dict[i] = deal_row[i]

        stats_db.set_tags(tags)
        self.assertEqual(stats_db.tags, tags)

        stats_data = stats_db.extract_tags_and_fields(deal_row)

        self.assertDictEqual(stats_data["tags"], tags_dict)

        for i in range(1, len(tags)+1):
            self.assertNotIn(tags[i-1], stats_data["fields"])


if __name__ == '__main__':
    unittest.main()
