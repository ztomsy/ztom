from .context import ztom
from ztom import ActionOrder, TradeOrder, errors
import unittest
import copy


class ActionOrderBasicTestSuite(unittest.TestCase):

    def test_comparison_eq(self):
        rm1 = ActionOrder("ADA/ETH", 1000, 0.32485131 / 1000, "buy")
        rm2 = ActionOrder("ADA/ETH", 1000, 0.32485131 / 1000, "sell")

        self.assertEqual(rm1, rm1)
        self.assertNotEqual(rm1, rm2)

        rm2.id = rm1.id
        self.assertEqual(rm1, rm1)

        rm2 = copy.copy(rm1)
        self.assertEqual(rm1, rm2)

        rm2.status = "closed"
        self.assertNotEqual(rm1, rm2)

        rm2 = copy.copy(rm1)
        rm2.filled = 1
        self.assertNotEqual(rm1, rm2)


class ActionOrderTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_create_trade_order(self):
        owa_order = ActionOrder("ADA/ETH", 1000, 0.32485131 / 1000, "sell")
        order = owa_order.active_trade_order
        self.assertEqual(order.dest_currency, "ETH")
        self.assertEqual(order.amount, 1000)
        self.assertEqual(order.side, "sell")
        self.assertEqual(owa_order.amount, 1000)

    def test_create_from_start_amount_sell(self):
        owa_order = ActionOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131)

        self.assertEqual(owa_order.dest_currency, "ETH")
        self.assertEqual(owa_order.amount, 1000)
        self.assertEqual(owa_order.start_currency, "ADA")
        self.assertEqual(owa_order.dest_amount, 0.00032485131*1000)
        self.assertEqual(owa_order.side, "sell")
        self.assertEqual(owa_order.amount, 1000)

    def test_create_from_start_amount_buy(self):
        owa_order = ActionOrder.create_from_start_amount("ADA/ETH", "ETH", 0.32485131, "ADA", 0.00032485131)
        self.assertEqual("ADA", owa_order.dest_currency)
        self.assertEqual("ETH", owa_order.start_currency)
        self.assertAlmostEqual(1000, owa_order.amount, 5)
        self.assertAlmostEqual(1000, owa_order.dest_amount, 5)
        self.assertEqual(owa_order.start_amount, 0.32485131)
        self.assertEqual(owa_order.side, "buy")

    def test_update_from_exchange_sell(self):
        owa = ActionOrder("ADA/ETH", 1000, 0.00032485131, "sell")
        resp = {"status": "open", "filled": 500, "cost": 0.32485131/2}
        owa.update_from_exchange(resp)
        self.assertEqual(owa.filled_start_amount, 500)
        self.assertEqual(owa.filled, 500)
        self.assertEqual(owa.status, "open")
        self.assertEqual(owa.state, "fill")

        self.assertEqual("fill", owa.active_trade_order.supplementary["parent_action_order"]["state"])

        self.assertEqual(owa.order_command, "hold")
        self.assertEqual(owa.filled_price, owa.active_trade_order.price)

    def test_update_from_exchange_buy(self):
        owa = ActionOrder("ADA/ETH", 1000, 0.00032485131, "buy")

        # update 1 - partial fill
        resp = {"status": "open", "filled": 500, "cost": 0.32485131 / 2}

        owa.update_from_exchange(resp)
        self.assertEqual(owa.filled_start_amount, 0.32485131 / 2)  #
        self.assertEqual(owa.filled, 500)  # filled amount of trade order in base currency
        self.assertEqual(owa.status, "open")
        self.assertEqual(owa.state, "fill")
        self.assertEqual("fill", owa.active_trade_order.supplementary["parent_action_order"]["state"])
        self.assertEqual(owa.order_command, "hold")
        self.assertEqual(owa.filled_price, owa.active_trade_order.price)

    def test_fill(self):

        owa = ActionOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131)

        # update 1 - partial fill
        resp = {"status":"open", "filled": 500, "cost": 0.32485131/2}
        owa.update_from_exchange(resp)
        self.assertEqual(owa.filled_start_amount, 500)
        self.assertEqual(owa.filled, 500)
        self.assertEqual(owa.status, "open")
        self.assertEqual(owa.state, "fill")
        self.assertEqual("fill", owa.active_trade_order.supplementary["parent_action_order"]["state"])
        self.assertEqual(owa.order_command, "hold")
        self.assertEqual(owa.filled_price, owa.active_trade_order.price)

        # update 2 - complete fill
        resp = {"status": "closed", "filled": 1000, "cost": 0.32485131}
        owa.update_from_exchange(resp)

        self.assertEqual(owa.filled_start_amount, 1000)
        self.assertEqual(owa.filled, 1000)
        self.assertEqual(owa.status, "closed")
        self.assertEqual(owa.order_command, "")
        self.assertEqual(owa.state, "fill")
        self.assertEqual("fill", owa.orders_history[0].supplementary["parent_action_order"]["state"])

        self.assertEqual(1, len(owa.orders_history))

        self.assertListEqual(owa.tags, list())

    def test_force_close(self):
        owa = ActionOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131)

        for i in range(1, 10):
            resp = {"status": "open", "filled": 0, "cost": 0}
            owa.update_from_exchange(resp)
            self.assertEqual(owa.filled, 0)
            self.assertEqual(owa.status, "open")

        self.assertEqual(False, owa._force_close)
        owa.force_close()
        self.assertEqual(True, owa._force_close)

        resp = {"status": "open", "filled": 0, "cost": 0}
        command = owa.update_from_exchange(resp)
        self.assertEqual("cancel", command)

        resp = {"status": "canceled", "filled": 0, "cost": 0}
        owa.update_from_exchange(resp)

        self.assertEqual("closed", owa.status)
        self.assertIn("#force_close", owa.tags)

    def test_report(self):

        owa = ActionOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131)

        # update 1 - partial fill
        resp = {"status": "open", "filled": 500, "cost": 0.32485131/2}
        owa.update_from_exchange(resp)

        # update 2 - complete fill
        resp = {"status": "closed", "filled": 1000, "cost": 0.32485131}
        owa.update_from_exchange(resp)

        self.assertListEqual(owa.tags, list())

        report = owa.report()

        self.assertEqual(1000, report["filled"])
        self.assertEqual("closed", report["status"])
        self.assertNotIn("orders_history", report)
        self.assertEqual(None, report["market_data"])
        self.assertNotIn("tags", report)

        owa.tags.append("#test #data")

        report2 = owa.report()

        self.assertEqual(1000, report2["filled"])
        self.assertEqual("closed", report2["status"])
        self.assertNotIn("orders_history", report2)
        self.assertEqual(None, report2["market_data"])
        self.assertEqual("#test #data", report2["tags"])

    def test_on_open_overriding(self):

        class FokOrder(ActionOrder):
            """
            implement basic FOK order by limiting maximum trade order updates and than cancel
            """
            def _init(self):
                super()._init()
                self.state = "fok"  # just to make things a little pretty

                self.active_trade_order.supplementary.update({"parent_action_order": {"state": self.state}})

            # redefine the _on_open_order checker to cancel active trade order if the number of order updates more
            # than max_order_updates
            def _on_open_order(self, active_trade_order: TradeOrder, market_data = None):
                if active_trade_order.update_requests_count >= self.max_order_updates \
                        and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:
                    return "cancel"
                return "hold"

        # filled and canceled with zero result
        owa = FokOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131)

        for i in range(1, owa.max_order_updates+1):
            resp = {"status": "open", "filled": 0, "cost": 0}
            owa.update_from_exchange(resp)
            self.assertEqual(owa.filled, 0)
            self.assertEqual(owa.status, "open")
            self.assertEqual(owa.state, "fok")

        self.assertEqual(owa.filled, 0)
        self.assertEqual(owa.status, "open")
        self.assertEqual(owa.state, "fok")
        self.assertEqual("fok", owa.active_trade_order.supplementary["parent_action_order"]["state"])

        self.assertEqual(owa.order_command, "cancel")

        owa.update_from_exchange({"status": "canceled", "filled": 500}, {"price": 1})
        self.assertEqual(owa.order_command, "")
        self.assertEqual(owa.status, "closed")

        self.assertEqual("fok", owa.orders_history[0].supplementary["parent_action_order"]["state"])

        # filled ok
        owa = FokOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131)

        for i in range(1, owa.max_order_updates):
            resp = {"status": "open", "filled": (owa.amount/owa.max_order_updates)*i, "cost": 0}
            owa.update_from_exchange(resp)
            self.assertEqual(owa.filled, (owa.amount/owa.max_order_updates)*i)
            self.assertEqual((owa.amount/owa.max_order_updates)*i, owa.get_active_order().filled)
            self.assertEqual(owa.status, "open")
            self.assertEqual("open", owa.get_active_order().status)
            self.assertEqual(owa.state, "fok")
            self.assertEqual(owa.order_command, "hold")

        self.assertEqual(owa.filled, 1000*0.9)
        self.assertEqual(owa.status, "open")
        self.assertEqual(owa.state, "fok")
        self.assertEqual(owa.order_command, "hold")

        owa.update_from_exchange({"status": "closed", "filled": 1000}, {"price": 1})
        self.assertEqual(owa.order_command, "")
        self.assertEqual(owa.status, "closed")

    def test_trade_orders_report_no_order_history(self):

        owa = ActionOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.00032485131)
        orders_report = owa.closed_trade_orders_report()

        if orders_report:
            self.assertEqual(1, 1)

        self.assertEqual(False, bool(orders_report))

    def test_create_next_order_for_remained_amount(self):
        ao = ActionOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)
        to = ao._create_next_trade_order_for_remained_amount(1)

        self.assertEqual(to.dest_currency, "ETH")
        self.assertEqual(to.amount, 1000)
        self.assertEqual(to.side, "sell")
        self.assertEqual(to.price, 1)
        self.assertEqual("fill", to.supplementary["parent_action_order"]["state"])
        self.assertEqual(ao.amount, 1000)

        ao.filled_start_amount = 400

        to = ao._create_next_trade_order_for_remained_amount(666)

        self.assertEqual(to.dest_currency, "ETH")
        self.assertEqual(to.amount, 600)
        self.assertEqual(to.price, 666)

        with self.assertRaises(errors.OrderError) as e:
            ao.filled_start_amount = 1001
            to = ao._create_next_trade_order_for_remained_amount(666)

        self.assertEqual("Bad new order amount -1", e.exception.args[0])

    def test_snapshots(self):
        ao = ActionOrder.create_from_start_amount("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)

        self.assertFalse(ao.changed_from_last_update)

        snapshot = ao._snapshot()
        self.assertEqual(snapshot.symbol, "ADA/ETH")
        self.assertEqual(snapshot.filled, 0.0)
        self.assertEqual("", snapshot.active_trade_order_id)
        self.assertEqual("", snapshot.active_trade_order_status)

        resp = {"status": "open", "filled": 10, "cost": 0}

        ao.update_from_exchange(resp)
        self.assertTrue(ao.changed_from_last_update)
        self.assertEqual(00, ao.previous_snapshot.filled)

        resp = {"status": "open", "filled": 20, "cost": 0}

        ao.update_from_exchange(resp)
        self.assertTrue(ao.changed_from_last_update)
        self.assertEqual(10, ao.previous_snapshot.filled)

        resp = {"status": "open", "filled": 20, "cost": 0}

        ao.update_from_exchange(resp)
        self.assertFalse(ao.changed_from_last_update)
        self.assertEqual(10, ao.previous_snapshot.filled)

        resp = {"status": "open", "filled": 30, "cost": 0}

        ao.update_from_exchange(resp)
        self.assertTrue(ao.changed_from_last_update)
        self.assertEqual(20, ao.previous_snapshot.filled)











