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
        for table in ["dws_momentum_score", "dws_technical_score", "dws_capital_score", "dws_chip_score"]:
            print(f"=== {table} ===")
            cursor.execute(f"DESCRIBE {table};")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[0]} ({col[1]})")
            print()
finally:
    conn.close()
