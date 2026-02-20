#!/usr/bin/env python3
import json
from pool_replay_engine.src.datastore.store import DataStore

cfg = json.load(open("pool_replay_engine/config/default.yaml"))
print(f"Raw config URI: {cfg['db']['read_uri']}")
print(f"URI repr: {repr(cfg['db']['read_uri'])}")

ds = DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])

print("\nTesting read URI parsing...")
read_config = ds._parse_mysql_uri(cfg["db"]["read_uri"])
print(f"Host: {read_config['host']}")
print(f"Port: {read_config['port']}")
print(f"User: {read_config['user']}")
print(f"Password: {read_config['password']}")
print(f"Password repr: {repr(read_config['password'])}")
print(f"Database: {read_config['database']}")

print("\nAttempting to connect...")
try:
    import pymysql
    conn = pymysql.connect(
        host=read_config["host"],
        port=read_config["port"],
        user=read_config["user"],
        password=read_config["password"],
        database=read_config["database"],
        charset=read_config["charset"]
    )
    print("✓ Connection successful!")
    conn.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
