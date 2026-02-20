#!/usr/bin/env python3
import json
import pymysql

cfg = json.load(open("pool_replay_engine/config/default.yaml"))

# Parse the read URI
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
        # Check columns of dwd_stock_daily_standard
        print("=== dwd_stock_daily_standard ===")
        cursor.execute("DESCRIBE dwd_stock_daily_standard;")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]} ({col[1]})")
        
        # Check columns of dwd_stock_label_daily
        print("\n=== dwd_stock_label_daily ===")
        cursor.execute("DESCRIBE dwd_stock_label_daily;")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]} ({col[1]})")
            
        # Check columns of ods_moneyflow
        print("\n=== ods_moneyflow ===")
        cursor.execute("DESCRIBE ods_moneyflow;")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]} ({col[1]})")
            
        # Check columns of dwd_chip_stability
        print("\n=== dwd_chip_stability ===")
        cursor.execute("DESCRIBE dwd_chip_stability;")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]} ({col[1]})")
finally:
    conn.close()
