import ztom

mongo_rep = ztom.MongoReporter("test", "offline")

mongo_rep.init_db("localhost", 27017, "db_test", "test_collection")

mongo_rep.set_indicator("test_field_int", 1)
mongo_rep.set_indicator("test_field_str", "Hi")
mongo_rep.set_indicator("test_field_dict", {"level1": {"sublevel1": {"key1": "value1", "key1": 7777}}})

result = mongo_rep.push_report()
print(result)

report = list()

report.append({"symbol": "ABC/XYZ", "amount": 1.11})
report.append({"symbol": "ABC2/XYZ2", "amount": 2.11})
report.append({"symbol": "ABC3/XYZ3", "amount": 3.11})
report.append({"symbol": "ABC4/XYZ4", "amount": 4.11})

result = mongo_rep.push_report(report)
print(result)











