import ztom
from ztom import Remainings
from sqlalchemy.exc import IntegrityError

reporter = ztom.SqlaReporter("test", "testEx")

connection_string = "postgres://postgres:12345@localhost:5432/ztom"

reporter.init_db(connection_string, echo=True)

print("Tables in db: {}".format(list(reporter.metadata.tables.keys())))


tables = reporter.create_tables()
print("Created tables {}".format(tables))

remainings = Remainings(

    exchange="binance",
    account="test",
    currency="BTC",
    action='FILL',
    symbol="BTC/USDT",
    target_currency="USDT",
    amount_delta=-0.5,
    target_amount_delta=5000

)

reporter.session.add(remainings)
print(remainings)

try:
    reporter.session.commit()
except IntegrityError as e:
    print("Integrity error")

"""
TODO: The flow: 
- try to update 
- try to insert if prev update failed
- try to update in prev insert failed 
"""

