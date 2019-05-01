
from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, func, TIMESTAMP, Float, JSON
from ztom.models._sqla_base import Base


class DealReport(Base):
    """
    Fields:
    timestamp should be timezone aware. for example timestamp=datetime.datetime.now(tz=pytz.timezone('UTC')),
    timestamp_start should be timezone aware
    exchange
    instance
    server
    deal_type
    deal_uuid
    status
    currency
    start_amount
    result_amount
    gross_profit
    net_profit
    config
    deal_data
    """

    __tablename__ = "deal_reports"

    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True))
    timestamp_start = Column(TIMESTAMP(timezone=True))
    exchange = Column(String)
    instance = Column(String)
    server = Column(String)
    deal_type = Column(String)
    deal_uuid = Column(String)
    status = Column(String)
    currency = Column(String)
    start_amount = Column(Float)
    result_amount = Column(Float)
    gross_profit = Column(Float)
    net_profit = Column(Float)
    config = Column(JSON)
    deal_data = Column(JSON)

