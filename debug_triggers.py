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
from pool_replay_engine.src.signals.trigger import compute_trigger_strength, compute_triggers

def _index(rows, key):
    return {r[key]: r for r in rows}

cfg = json.load(open("pool_replay_engine/config/nvda-concept.json"))
ds = DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])

# Load pool
universe = [r["ts_code"] for r in load_pool_file("pool_NVDA-CONCEPT.csv")]

# Get trade calendar
date = "20260213"
cal = ds.get_trade_calendar("19900101", date)
start = cal[max(0, len(cal) - cfg["window"]["lookback_days"])] if cal else date

# Load and prepare data
price = add_price_features(ds.load_price_window(universe, start, date), cfg["trigger"]["breakout_lookback"])
today = [r for r in price if str(r.get("trade_date")) == date]
labels = _index(normalize_label(ds.load_label_daily(universe, date)), "ts_code")
flow_today = _index([r for r in add_flow_features(ds.load_moneyflow_window(universe, start, date), price) if str(r.get("trade_date")) == date], "ts_code")
chip = _index(add_chip_features(ds.load_chip_daily(universe, date)), "ts_code")
score = _index(ds.load_dws_scores_daily(universe, date), "ts_code")

rows = []
for r in today:
    x = dict(r)
    x.update(labels.get(r["ts_code"], {}))
    x.update(flow_today.get(r["ts_code"], {}))
    x.update(chip.get(r["ts_code"], {}))
    x.update(score.get(r["ts_code"], {}))
    rows.append(x)

rows = apply_hard_filters(rows, cfg["filters"])
print(f"✓ After hard filters: {len(rows)} stocks")

# Apply triggers
rows = compute_triggers(rows, cfg["trigger"])
trigger_count = sum(1 for r in rows if r.get("is_trigger"))
print(f"✓ After trigger detection: {trigger_count} stocks with triggers")

# Compute strength
strengths = compute_trigger_strength(rows)
print(f"✓ Trigger strengths computed: {len(strengths)} values")

for i, row in enumerate(rows[:3]):
    print(f"  Stock {row['ts_code']}: is_trigger={row.get('is_trigger')}, trigger_type={row.get('trigger_type')}, strength={strengths[i]}")

# Check if rows are empty before writing
print(f"\nFinal rows to write: {len(rows)}")
if rows:
    print(f"Sample row: {rows[0]['ts_code']}")
