
from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, func, TIMESTAMP, Float, JSON
from ztom.models._sqla_base import Base
from ztom.trade_orders import TradeOrder
import datetime
import copy


class TradeOrderReport(Base):

    __tablename__ = "trade_orders"

    id = Column(Integer, primary_key=True) # db id
    timestamp = Column(TIMESTAMP(timezone=True))  #timestamp of adding record

    deal_uuid = Column(String)  # deal_uuid by which order was generated
    action_order_uuid = Column(String)  # actionOrder.id 's by which order was generated

    id_from_exchange = Column(String)  # TradeOrder.id from exchange
    internal_id = Column(String)  # internal id for offline orders management

    status = Column(String)  # 'open', 'closed', 'canceled'

    # dicts of proceeded UTC timestamps: {"request_sent":value, "request_received":value, "from_exchange":value}
    timestamp_open = Column(JSON)  # on placing order
    timestamp_closed = Column(JSON)  # on closing order

    symbol = Column(String)
    type = Column(String)  # order type (limit)
    side = Column(String)  # buy or sell
    amount = Column(Float)  # ordered amount of base currency
    init_price = Column(Float)  # initial price, when create order
    price = Column(Float)  # placed price, could be updated from exchange

    start_currency = Column(String)
    dest_currency = Column(String)

    fee = Column(JSON)  # fee from ccxt

    trades = Column(JSON)
    fees = Column(JSON)

    precision_amount = Column(Float)
    price_precision = Column(Float)

    filled = Column(Float)  # filled amount of base currency
    remaining = Column(Float)  # remaining amount to fill
    cost = Column(Float)  # filled amount of quote currency 'filled' * 'price'

    info = Column(JSON)  # the original response from exchange

    # order_book = Column(JSON)

    amount_start = Column(Float)  # amount of start currency
    amount_dest = Column(Float)  # amount of dest currency

    update_requests_count = Column(Integer)  # number of updates of order. should be in correspondence with API requests

    filled_start_amount = Column(Float)  # filled amount of start currency
    filled_dest_amount = Column(Float)  # filled amount of dest currency

    supplementary = Column(JSON)

    @classmethod
    def from_trade_order(cls, order: TradeOrder, timestamp: datetime, deal_uuid: str = None,
                         action_order_id: str = None, supplementary: dict = None) -> 'TradeOrderReport':
        """
        creates TradeOrderReport sqlalchemy table from TradeOrder object. Provide deal_uuid and action_order_uuid to
        connect Trade Order to deal and action order. if :param supplementary: will be provided - it will be added with
        the supplementary field of original TradeOrder.

        :param order: source TradeOrder object
        :param timestamp: datetime with timezone will be used to fill timestamp field in table
        :param deal_uuid:  deal_uuid - optional
        :param action_order_id: optional
        :param supplementary: add supplementary data to existing order's supplementary field
        :return: sqlalchemy table TradeOrderReport
        """

        supplementary_from_order = copy.copy(order.supplementary)
        if supplementary is not None:
            supplementary_from_order.update(supplementary)

        # noinspection PyTypeChecker
        trade_order_report = TradeOrderReport(
            timestamp=timestamp,
            deal_uuid=deal_uuid,
            action_order_uuid=action_order_id,
            id_from_exchange=order.id,
            internal_id=order.internal_id,
            status=order.status,
            timestamp_open=order.timestamp_open,
            timestamp_closed=order.timestamp_closed,
            symbol=order.symbol,
            type=str(order.type),
            side=order.side,
            amount=order.amount,
            init_price=order.init_price,
            price=order.price,
            start_currency=order.start_currency,
            dest_currency=order.dest_currency,
            fee=order.fee,
            trades=order.trades,
            fees=order.fees,
            precision_amount=order.precision_amount,
            price_precision=order.price_precision,
            filled=order.filled,
            remaining=order.remaining,
            cost=order.cost,
            info=order.info,
            amount_start=order.amount_start,
            amount_dest=order.amount_dest,
            update_requests_count=order.update_requests_count,
            filled_start_amount=order.filled_start_amount,
            filled_dest_amount=order.filled_dest_amount,
            supplementary=supplementary_from_order
        )

        return trade_order_report
