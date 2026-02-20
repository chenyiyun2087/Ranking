import json
import sys
sys.path.insert(0, '/Users/chenyiyun/PycharmProjects/Ranking')

from pool_replay_engine.src.datastore.store import DataStore

cfg = json.load(open("pool_replay_engine/config/default.yaml"))
ds = DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])

print("Read URI config:")
print(ds._parse_mysql_uri(cfg["db"]["read_uri"]))
print("\nWrite URI config:")
print(ds._parse_mysql_uri(cfg["db"]["write_uri"]))
