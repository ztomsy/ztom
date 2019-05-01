from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, func, TIMESTAMP, Float, JSON
from ztom.models._sqla_base import Base
from ztom.trade_orders import TradeOrder
import datetime
import copy
import pytz


class Tickers(Base):
    """
    abstracts tickers information
    """

    __tablename__ = "tickers"
    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True))
    exchange = Column(String(10))
    symbol = Column(String(10))
    ask = Column(Float)
    ask_quantity = Column(Float)
    bid = Column(Float)
    bid_quantity = Column(Float)

    @classmethod
    def from_single_ticker(cls, exchange, symbol: str, ticker: dict):
        return Tickers(
            timestamp=datetime.datetime.now(tz=pytz.timezone("UTC")),
            exchange = exchange,
            symbol=symbol,
            ask=ticker["ask"],
            ask_quantity=ticker["askVolume"],
            bid=ticker["bid"],
            bid_quantity=ticker["bidVolume"]
        )

    @staticmethod
    def bulk_list_from_tickers(exchange:str, tickers: dict):
        """
        creates the list of dicts for bulk instert
        connection.execute(addresses.insert(), [
        ...    {'user_id': 1, 'email_address' : 'jack@yahoo.com'},
        ...    {'user_id': 1, 'email_address' : 'jack@msn.com'},
        ...    {'user_id': 2, 'email_address' : 'www@www.org'},
        ...    {'user_id': 2, 'email_address' : 'wendy@aol.com'},
        ... ]) )
        :param tickers: dict of ccxt tickers where key is the symbol
        :return: list of dicts
        """
        timestamp = datetime.datetime.now(tz=pytz.timezone("UTC"))
        tickers_list = list()
        for s, t in tickers.items():
            t_dict = {
                "timestamp": timestamp,
                "exchange": exchange,
                "symbol": s,
                "ask": t["ask"],
                "ask_quantity": t["askVolume"],
                "bid": t["bid"],
                "bid_quantity": t["bidVolume"]
            }

            tickers_list.append(t_dict)
        return tickers_list










