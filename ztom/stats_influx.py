from influxdb import InfluxDBClient


class StatsInflux:

    def __init__(self, host, port, database, measurement):

        self.host = host  # "13.231.173.161"
        self.port = port  # 8086
        self.database = database  # "dev"

        self.measurement = measurement  # "deals_results"

        self.client = InfluxDBClient(host=self.host, port=self.port, database=self.database)

        self.tags = list()  # list of tags from the deal info dict

    def set_tags(self, tags: list):
        self.tags = tags

    def extract_tags_and_fields(self, deal_row:dict):
        tags = dict()
        fields = dict()

        for i in deal_row:
            if i in self.tags:
                tags[i] = deal_row[i]
            else:
                fields[i] = deal_row[i]

        return {"tags": tags, "fields": fields}

    # time should be a datetime type
    def write_deal_info(self, deal_row: dict, time=None):

        updtmsg = dict()

        updtmsg["measurement"] = self.measurement

        stats_data = self.extract_tags_and_fields(deal_row)

        updtmsg["tags"] = stats_data["tags"]
        updtmsg["fields"] = stats_data["fields"]

        if time is not None:
            updtmsg["time"] = time

        self.client.write_points([updtmsg], protocol="json")

    def push_fields(self, fields: dict, time=None):

        updtmsg = dict()

        updtmsg["measurement"] = self.measurement

        #stats_data = self.extract_tags_and_fields(deal_row)

        updtmsg["tags"] = self.tags
        updtmsg["fields"] = fields

        if time is not None:
            updtmsg["time"] = time

        return self.client.write_points([updtmsg], protocol="json")

