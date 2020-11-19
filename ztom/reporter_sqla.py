import json
import sqlalchemy
from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, func, TIMESTAMP, Float, JSON

from . import Reporter
from sqlalchemy.orm import sessionmaker

from .models._sqla_base import Base
from .models.deal import DealReport
from .models.trade_order import TradeOrderReport
from .models.remainings import Remainings

class SqlaReporter(Reporter):
    """
    reporter wrapper for SQLAlchemy
    """
    TABLES = [DealReport, TradeOrderReport, Remainings]

    def __init__(self, server_id, exchange_id):
        super().__init__(server_id, exchange_id)

        self.engine = None  # type:  sqlalchemy.engine.Engine
        self.metadata = None  # type: sqlalchemy.schema.MetaData
        self.Base = Base 
        self.Session = None
        self.session = None
        self.connection = None  # type: sqlalchemy.engine.Connection

    def init_db(self, connection_string: str, **kwargs):
        """

        :param connection_string:
        :param echo: boolean set to True to pass the echo to engine
        :return:
        """
        echo = kwargs["echo"] if "echo" in kwargs else False

        self.engine = sqlalchemy.create_engine(connection_string, echo=echo)
        self.connection = self.engine.connect()
        self.metadata = sqlalchemy.MetaData(self.engine)
        self.metadata.reflect()

        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def new_session(self):
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def create_tables(self):
        tables = list()

        for t in self.TABLES:
            if t.__tablename__ is not None and t.__tablename__ not in self.metadata.tables:
                tables.append(t.__table__)

        Base.metadata.create_all(self.engine, tables=tables)
        return tables


