from .stats_influx import StatsInflux
from pymongo import MongoClient, database, collection
from urllib.parse import quote_plus


class Reporter:

    def __init__(self, server_id, exchange_id):

        #self.session_uuid = session_uuid
        self.server_id = server_id
        self.exchange_id = exchange_id

        self.def_indicators = dict()  # definition indicators
        self.indicators = dict()

        self.def_indicators["server_id"] = self.server_id
        self.def_indicators["exchange_id"] = self.exchange_id
        # self.def_indicators["session_uuid"] = self.session_uuid

    def set_indicator(self, key, value):
        self.indicators[key] = value

    def init_db(self, host, port, database, measurement, user="", password=""):
        self.influx = StatsInflux(host, port, database, measurement)
        self.influx.set_tags(self.def_indicators)

    def push_to_influx(self):
        return self.influx.push_fields(self.indicators)


class MongoReporter(Reporter):

    def __init__(self, server_id: str, exchange_id: str):
        super().__init__(server_id, exchange_id)
        self.default_db = None  # type: database.Database
        self.default_collection = None # type:collection.Collection
        self.mongo_client = None # type: MongoClient

    def init_db(self, host: str = "localhost", port = None, default_data_base = "", default_collection ="" ):

        uri = host

        self.mongo_client = MongoClient(uri)
        self.default_db = self.mongo_client[default_data_base]
        self.default_collection = self.default_db[default_collection]

    def push_report(self, report=None, collection: str = None, data_base: str = None):

        _data_base = self.default_db if data_base is None else self.mongo_client[data_base]
        _collection = self.default_collection if collection is None else _data_base[collection]

        if report is not None:
            if isinstance(report, list):
                result = _collection.insert_many(report)
            else:
                result = _collection.insert_one(report)

        else:

            # for r in report:
            #     self.reporter.set_indicator(r, report[r])

            result = self.default_collection.insert_one(self.indicators)

        return result
















