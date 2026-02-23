#!/usr/bin/env python3
"""Debug script to check why 7 stocks are not detected as TRIGGER"""

import json
from pool_replay_engine.src.datastore.adapters import normalize_label
from pool_replay_engine.src.datastore.store import DataStore
from pool_replay_engine.src.features.chip import add_chip_features
from pool_replay_engine.src.features.flow import add_flow_features
from pool_replay_engine.src.features.price import add_price_features
from pool_replay_engine.src.signals.filters import apply_hard_filters
from pool_replay_engine.src.signals.trigger import compute_triggers

# 那7个应该是TRIGGER的股票
trigger_stocks = [
    '688017.SH', '002812.SZ', '000628.SZ', '002008.SZ', 
    '000738.SZ', '002655.SZ', '002169.SZ'
]

def _load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    cfg = _load_cfg("pool_replay_engine/config/default.yaml")
    ds = DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])
    
    # Load data for these 7 stocks
    date = '20260213'
    start = '20251120'  # Roughly 60 days back
    
    print(f"Loading data for {len(trigger_stocks)} stocks from {start} to {date}")
    
    price = add_price_features(ds.load_price_window(trigger_stocks, start, date), cfg["trigger"]["breakout_lookback"])
    today = [r for r in price if str(r["trade_date"]) == date]
    
    print(f"\nLoaded {len(today)} records for {date}")
    
    labels = {r["ts_code"]: r for r in normalize_label(ds.load_label_daily(trigger_stocks, date))}
    flow_today = {r["ts_code"]: r for r in [r for r in add_flow_features(ds.load_moneyflow_window(trigger_stocks, start, date), price) if str(r["trade_date"]) == date]}
    chip = {r["ts_code"]: r for r in add_chip_features(ds.load_chip_daily(trigger_stocks, date))}
    
    rows = []
    for r in today:
        x = dict(r)
        x.update(labels.get(r["ts_code"], {}))
        x.update(flow_today.get(r["ts_code"], {}))
        x.update(chip.get(r["ts_code"], {}))
        rows.append(x)
    
    print(f"Before hard filters: {len(rows)} rows")
    rows = apply_hard_filters(rows, cfg["filters"])
    print(f"After hard filters: {len(rows)} rows")
    
    rows = compute_triggers(rows, cfg["trigger"])
    
    print(f"\n{'='*120}")
    print("Trigger Analysis for 7 stocks:")
    print(f"{'='*120}")
    
    for row in rows:
        ts_code = row["ts_code"]
        close = row.get("close", 0)
        high_60 = row.get("high_60", 0)
        vol_ratio = row.get("vol_ratio", 0)
        flow_3d = row.get("flow_3d", 0)
        is_breakout = row.get("is_breakout", False)
        
        print(f"\n{ts_code}:")
        print(f"  close={close:.2f}, high_60={high_60:.2f} -> close >= high_60? {close >= high_60}")
        print(f"  vol_ratio={vol_ratio:.2f} -> vol_ratio >= 1.5? {vol_ratio >= 1.5}")
        print(f"  flow_3d={flow_3d:,.0f} -> flow_3d > 0? {flow_3d > 0}")
        print(f"  is_breakout={is_breakout} {'✅ TRIGGER' if is_breakout else '❌'}")

if __name__ == "__main__":
    main()
