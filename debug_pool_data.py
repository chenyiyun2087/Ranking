#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, '/Users/chenyiyun/PycharmProjects/Ranking')

from pool_replay_engine.src.datastore.store import DataStore
from pool_replay_engine.src.datastore.pool import load_pool_file
from pool_replay_engine.src.datastore.calendar import prev_trade_date
from pool_replay_engine.src.features.price import add_price_features
from pool_replay_engine.src.features.flow import add_flow_features
from pool_replay_engine.src.features.chip import add_chip_features
from pool_replay_engine.src.datastore.adapters import normalize_label
from pool_replay_engine.src.signals.filters import apply_hard_filters

def _index(rows, key):
    return {r[key]: r for r in rows}

cfg = json.load(open("pool_replay_engine/config/nvda-concept.json"))
ds = DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])

# Load pool
universe = [r["ts_code"] for r in load_pool_file("pool_NVDA-CONCEPT.csv")]
print(f"✓ Loaded {len(universe)} stocks from pool")

# Get trade calendar
date = "20260213"
cal = ds.get_trade_calendar("19900101", date)
start = cal[max(0, len(cal) - cfg["window"]["lookback_days"])] if cal else date

# Load price data
price = add_price_features(ds.load_price_window(universe, start, date), cfg["trigger"]["breakout_lookback"])
today = [r for r in price if str(r.get("trade_date")) == date]
print(f"✓ Got {len(today)} stocks with price data for {date}")

# Load labels
labels = _index(normalize_label(ds.load_label_daily(universe, date)), "ts_code")
print(f"✓ Got {len(labels)} stocks with labels")

# Load flow
flow_today = _index([r for r in add_flow_features(ds.load_moneyflow_window(universe, start, date), price) if str(r.get("trade_date")) == date], "ts_code")
print(f"✓ Got {len(flow_today)} stocks with flow data")

# Load chip
chip = _index(add_chip_features(ds.load_chip_daily(universe, date)), "ts_code")
print(f"✓ Got {len(chip)} stocks with chip data")

# Load scores
score = _index(ds.load_dws_scores_daily(universe, date), "ts_code")
print(f"✓ Got {len(score)} stocks with scores")

# Combine data
rows = []
for r in today:
    x = dict(r)
    x.update(labels.get(r["ts_code"], {}))
    x.update(flow_today.get(r["ts_code"], {}))
    x.update(chip.get(r["ts_code"], {}))
    x.update(score.get(r["ts_code"], {}))
    rows.append(x)

print(f"✓ Combined {len(rows)} rows")

# Apply hard filters
filtered_rows = apply_hard_filters(rows, cfg["filters"])
print(f"✓ After hard filters: {len(filtered_rows)} stocks passed")

if filtered_rows:
    print(f"Sample filtered row: {filtered_rows[0]}")
else:
    print("❌ No stocks passed hard filters!")
    # Check first row to see what caused the filter
    if rows:
        sample = rows[0]
        print(f"\nSample unfiltered row data:")
        print(f"  avoid: {sample.get('avoid')}")
        print(f"  is_st: {sample.get('is_st')}")
        print(f"  is_new: {sample.get('is_new')}")
        print(f"  vol: {sample.get('vol')}")
        print(f"  amount: {sample.get('amount')}")
        print(f"  risk_flags: {sample.get('risk_flags')}")

