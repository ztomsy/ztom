import ztom
from ztom import DealReport
import datetime
import uuid
import pytz
import argparse
import sys
from random import randint


deal_uuid = None
parser = argparse.ArgumentParser()

parser.add_argument("--deal_uuid", help="deal_uuid to update",
                    dest="deal_uuid",
                    action="store", default=None)

deal_uuid = parser.parse_args(sys.argv[1:]).deal_uuid

print("deal_uuid: {}".format(deal_uuid))

reporter = ztom.SqlaReporter("test", "offline")

connection_string = "postgres://ztom_main:ztom@localserver:5432/ztom_dev"

reporter.init_db(connection_string, echo=True)
print("Tables in db: {}".format(list(reporter.metadata.tables.keys())))

if deal_uuid is not None and ztom.DealReport.__tablename__ in list(reporter.metadata.tables.keys()):
    print("Will update the deal_uuid {}".format(deal_uuid))

    deal_report = reporter.session.query(DealReport).filter_by(deal_uuid=deal_uuid).first()  # type: DealReport
    if deal_report is not None:
        reporter.session.add(deal_report)
        print(deal_report)

        deal_data = dict(deal_report.deal_data)
        deal_data["recovery1"] = {"leg": 1, "amount": randint(0, 1000000), "new": "new"}
        # deal_report.deal_data["recovery1"] = {"leg": 1, "amount": 666}
        deal_report.deal_data = deal_data
        reporter.session.commit()

        sys.exit(0)
    else:
        print("Deal not found")
        sys.exit()


tables = reporter.create_tables()
print("Created tables {}".format(tables))


deal_report = DealReport(
    timestamp=datetime.datetime.now(tz=pytz.timezone('UTC')),
    timestamp_start=datetime.datetime.now(tz=pytz.timezone('UTC')),
    exchange="test_exchange",
    instance="test_instance",
    server="test_server",
    deal_type="test",
    deal_uuid=str(uuid.uuid4()),
    status="OK",
    currency="BTC",
    start_amount=1.666,
    result_amount=1.8,
    gross_profit=1.8 - 1.666,
    net_profit=0.1,
    config={"server": "test", "limit": {"hi": 111, "low": 0}, "trades": [1, 2, 3, 4, 5]},
    deal_data={"symbol": "ETH/BTC", "limit": {"hi": 111, "low": 0}, "trades": [1, 2, 3, 4, 5]})

reporter.session.add(deal_report)
reporter.session.commit()

print("OK")


