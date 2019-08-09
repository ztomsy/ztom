import collections
import os
import csv

"""
Class allows creation of csv based data storage
Usage:
at the beginning create storage: 
>>> storage = tgk.DataStorage('./storage1')

register your data types:
>>> headers = ['leg1', 'leg2', ...]
>>> storage.register('Exchange', headers)

then save data:
>>> row = [leg1, leg2, ...]
>>> storage.save('Ticker', row)

at the end stop storage:
>>> storage.stop()
"""


class DataStorage:
    def __init__(self, folder):
        if not os.path.isdir(folder):
            os.mkdir(folder)

        self.folder = folder
        self.entities = collections.defaultdict(str)

    def register(self, type_name, headers, overwrite=True):
        # self.validate_not_exists(type_name)
        full_path = os.path.join(self.folder, type_name + ".csv")
        exists = False
        if os.path.exists(full_path) and not overwrite:
            file = open(full_path, "a", newline='')
            exists = True
        else:
            file = open(full_path, "w", newline='')

        writer = csv.writer(file)

        if not exists:
            writer.writerow(headers)

        self.entities[type_name] = {'file': file, 'writer': writer, 'headers': headers, "full_path":full_path}

    def save(self, type_name, row):
        self.validate_exists(type_name)
        # TODO: use named tuples
        self.entities[type_name]['writer'].writerow(row)
        self.entities[type_name]['file'].flush()  # TODO

    def save_all(self, type_name, rows):
        self.validate_exists(type_name)
        # TODO: use named tuples
        self.entities[type_name]['writer'].writerows(rows)
        self.entities[type_name]['file'].flush()  # TODO

    def validate_not_exists(self, type_name):
        if type_name in self.entities.keys():
            raise ValueError('Entity already exist: %s' % type_name)

    def validate_exists(self, type_name):
        if type_name not in self.entities.keys():
            raise ValueError('Entity don\'t exist: %s' % type_name)

    def stop(self):
        for type_name, entity in self.entities.items():
            self.entities[type_name]['file'].close()

    def path(self, type_name):
        return self.entities[type_name]['file'].name

    def save_dict(self, type_name, data):
        headers = self.entities[type_name]['headers']
        values = list(map(lambda k: data.get(k, ''), headers))
        self.save(type_name, values)

    def save_dict_all(self, type_name, array):
        for x in array: self.save_dict(type_name, x)





