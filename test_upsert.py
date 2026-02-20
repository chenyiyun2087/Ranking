#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, '/Users/chenyiyun/PycharmProjects/Ranking')

from pool_replay_engine.src.datastore.store import DataStore

cfg = json.load(open("pool_replay_engine/config/nvda-concept.json"))
ds = DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])

# Create test row
test_rows = [
    {
        "trade_date": "20260213",
        "pool_id": -1,
        "ts_code": "000001.SZ",
        "state": "WATCH",
        "action": "WATCH",
        "base_score": 50.0,
        "trigger_strength": 30.0,
        "pool_final_score": 65.0,
        "risk_flags": "{}",
        "key_levels": "{}",
        "reasons": "{}",
        "updated_at": "2026-02-20T12:00:00"
    }
]

print(f"Writing {len(test_rows)} rows...")
ds.upsert_pool_replay_daily(test_rows)
print("✓ Upsert completed")

# Verify
import pymysql
with ds._connect_write() as conn:
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT COUNT(*) FROM dws_pool_replay_daily WHERE ts_code = %s", ["000001.SZ"])
        result = cursor.fetchone()
        print(f"✓ Verify: {result['COUNT(*)']} rows found for 000001.SZ")
