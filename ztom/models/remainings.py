from sqlalchemy import Column, Index,  DateTime, String, Integer, ForeignKey, func, TIMESTAMP, Float, JSON
from ztom.models._sqla_base import Base
from ztom.trade_orders import TradeOrder
import datetime

class Remainings(Base):
    """
    Remainings balance table
    """

    __tablename__ = "remainings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange = Column(String)
    """
    exchange id 
    """
    account = Column(String)
    """
    account Id 
    """

    timestamp = Column(TIMESTAMP(timezone=True), default=datetime.datetime.now)
    """
    timestamp of record insertion
    """

    action = Column(String, nullable=False)
    """
    action: add, fill or aggregate
    """

    currency = Column(String)
    """
    currency of remainings
    """

    amount_delta = Column(Float)
    """
    total amount of remainings of currency
    """
    target_currency = Column(String)
    """
    asset which was intended to be yielded from remaining proceeding
    """
    target_amount_delta = Column(Float)
    """
    considered best target amount
    """
    symbol = Column(String)
    """
    trade pair of an order yielded the remaining when remaining was created
    """

    __table_args__ = (Index('idx_exchange_account_currency_symbol_target_currency',
          'exchange', 'account', 'currency', 'symbol', 'target_currency'),)

    # @classmethod
    # def from_trade_order(cls, order: TradeOrder, timestamp: datetime, deal_uuid: str = None,
    #                      action_order_id: str = None, supplementary: dict = None) -> 'TradeOrderReport':








