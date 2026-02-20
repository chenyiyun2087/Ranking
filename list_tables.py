#!/usr/bin/env python3
import json
import pymysql

cfg = json.load(open("pool_replay_engine/config/default.yaml"))

def parse_uri(uri):
    if uri.startswith("mysql://"):
        uri = uri[8:]
    creds, host_db = uri.rsplit("@", 1)
    user, password = creds.split(":", 1) if ":" in creds else (creds, "")
    host_port, database = host_db.rsplit("/", 1) if "/" in host_db else (host_db, "mysql")
    host, port = host_port.rsplit(":", 1) if ":" in host_port else (host_port, "3306")
    return {"host": host, "port": int(port), "user": user, "password": password, "database": database}

config = parse_uri(cfg["db"]["read_uri"])
conn = pymysql.connect(**config)

try:
    with conn.cursor() as cursor:
        # List all tables
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        print("All tables in tushare_stock:")
        for table in tables:
            print(f"  {table[0]}")
finally:
    conn.close()
