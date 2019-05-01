from datetime import datetime
import time
import collections

class Timer:

    def __init__(self):
        self.start_time = datetime.now()
        self.notches = []

        self.bucket_size = 0
        self.tokens = 0
        self.bucket_seconds = 0

        self.now = datetime.now()
        self.request_time = self.now
        self.timestamp_before_request = datetime(1, 1, 1, 1, 1, 0)

        self.max_requests_per_lap = int
        self.lap_time = int


    def notch(self, name):
        last = self.start_time if len(self.notches) == 0 else self.notches[-1]['time']
        self.notches.append({
            'name': name,
            'time': datetime.now(),
            'duration': (datetime.now() - last).total_seconds()
        })

    def check_timer(self):

        self.now = datetime.now()
        self.request_time = (self.now - self.timestamp_before_request).total_seconds()
        self.timestamp_before_request = self.now

        if 1 / self.request_time > self.max_requests_per_lap / self.lap_time:
            print("Pause for:", self.lap_time / self.max_requests_per_lap - self.request_time)
            time.sleep(self.lap_time / self.max_requests_per_lap - self.request_time)
            self.timestamp_before_request = datetime.now()


    # TODO change to use map
    def results(self):
        result = []
        for n in self.notches:
            result.append('%s: %s s ' % (n['name'],  (n['duration'])))

        return '| '.join(result)

    def results_dict(self):
        d = collections.OrderedDict()
        for i in self.notches:
            d[i["name"]] = i["duration"]
        return d

    def timestamps(self, notch_prefix: str = ""):
        """
        returns the dict of notches with timestamps: {<nothch_prefix><notch_name>:timestamp}
        :param notch_prefix: prefix of dict key , so the resulting key is: prefix + notch name
        :return: dict
        """
        d = collections.OrderedDict()
        for i in self.notches:
            d[notch_prefix + i["name"]] = i["time"].timestamp()
        return d


    def reset_notches(self):
        self.notches = list()
