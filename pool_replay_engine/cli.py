from __future__ import annotations

import argparse
import json
from datetime import datetime

from pool_replay_engine.src.datastore.adapters import normalize_label
from pool_replay_engine.src.datastore.calendar import prev_trade_date
from pool_replay_engine.src.datastore.pool import load_pool_file
from pool_replay_engine.src.datastore.store import DataStore
from pool_replay_engine.src.features.chip import add_chip_features
from pool_replay_engine.src.features.flow import add_flow_features
from pool_replay_engine.src.features.price import add_price_features
from pool_replay_engine.src.outputs.report_md import write_report
from pool_replay_engine.src.outputs.writer import build_health, write_lists
from pool_replay_engine.src.signals.filters import apply_hard_filters
from pool_replay_engine.src.signals.scoring import compute_base_score, compute_risk_penalty
from pool_replay_engine.src.signals.state_machine import apply_state_machine
from pool_replay_engine.src.signals.trigger import compute_trigger_strength, compute_triggers


def _load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _index(rows: list[dict], key: str) -> dict:
    return {r[key]: r for r in rows}


def run_daily(date: str, pool_id: int | None, pool_file: str | None, config: str) -> None:
    cfg = _load_cfg(config)
    ds = DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])
    universe = ds.get_pool_members(pool_id, date) if pool_id is not None else [r["ts_code"] for r in load_pool_file(pool_file)]

    cal = ds.get_trade_calendar("19900101", date)
    prev_date = prev_trade_date(cal, date)
    start = cal[max(0, len(cal) - cfg["window"]["lookback_days"])] if cal else date

    price = add_price_features(ds.load_price_window(universe, start, date), cfg["trigger"]["breakout_lookback"])
    today = [r for r in price if str(r["trade_date"]) == date]
    print(f"[DEBUG] Loaded price: {len(price)} records, today: {len(today)} records")
    labels = _index(normalize_label(ds.load_label_daily(universe, date)), "ts_code")
    flow_today = _index([r for r in add_flow_features(ds.load_moneyflow_window(universe, start, date), price) if str(r["trade_date"]) == date], "ts_code")
    chip = _index(add_chip_features(ds.load_chip_daily(universe, date)), "ts_code")
    score = _index(ds.load_dws_scores_daily(universe, date), "ts_code")
    print(f"[DEBUG] Loaded labels: {len(labels)}, flow: {len(flow_today)}, chip: {len(chip)}, score: {len(score)}")

    rows = []
    for r in today:
        x = dict(r)
        x.update(labels.get(r["ts_code"], {}))
        x.update(flow_today.get(r["ts_code"], {}))
        x.update(chip.get(r["ts_code"], {}))
        x.update(score.get(r["ts_code"], {}))
        rows.append(x)

    print(f"[DEBUG] Before hard filters: {len(rows)} rows")
    rows = apply_hard_filters(rows, cfg["filters"])
    print(f"[DEBUG] After hard filters: {len(rows)} rows")
    rows = compute_triggers(rows, cfg["trigger"])
    print(f"[DEBUG] After triggers: {len(rows)} rows")
    strengths = compute_trigger_strength(rows)
    print(f"[DEBUG] After trigger strength: {len(rows)} rows, {len(strengths)} strengths")
    bases = compute_base_score(rows, cfg["scoring"]["base_weights"])
    print(f"[DEBUG] After base score: {len(rows)} rows, {len(bases)} bases")
    for i, row in enumerate(rows):
        row["trigger_strength"] = strengths[i]
        row["base_score"] = bases[i]
    penalties = compute_risk_penalty(rows, cfg["risk"])
    print(f"[DEBUG] After risk penalty: {len(rows)} rows, {len(penalties)} penalties")
    for i, row in enumerate(rows):
        row["pool_final_score"] = max(0, min(100, row["base_score"] + cfg["scoring"]["trigger_bonus_weight"] * row["trigger_strength"] - penalties[i]))

    prev_states = ds.load_prev_states(pool_id, prev_date) if (pool_id is not None and prev_date) else {}
    setup_threshold = cfg["scoring"].get("setup_base_score_threshold", 15)
    rows = apply_state_machine(rows, prev_states, cfg["risk"]["weaken_break_ma20_vol_ratio"], setup_threshold)

    now = datetime.utcnow().isoformat()
    for row in rows:
        row["state"] = "AVOID" if row["avoid"] == 1 else row["state"]
        row["pool_id"] = int(pool_id) if pool_id is not None else -1
        row["trade_date"] = date
        row["updated_at"] = now
        row["key_levels"] = json.dumps({"ma20": float(row.get("ma20") or 0), "ma60": float(row.get("ma60") or 0), "high_60": float(row.get("high_60") or 0), "breakout_level": float(row.get("high_60") or 0)}, ensure_ascii=False)
        row["reasons"] = json.dumps({"trigger": row.get("trigger_type"), "flow_3d": float(row.get("flow_3d") or 0), "vol_ratio": float(row.get("vol_ratio") or 0)}, ensure_ascii=False)

    ds.upsert_pool_replay_daily(rows)
    health = build_health(rows, date, int(pool_id) if pool_id is not None else -1)
    ds.upsert_pool_health_daily(health)
    write_lists(rows, "output", cfg["pool"])
    write_report(rows, health, "output", int(pool_id) if pool_id is not None else -1, date)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run-daily")
    run.add_argument("--date", required=True)
    run.add_argument("--pool-id", type=int)
    run.add_argument("--pool-file")
    run.add_argument("--config", default="pool_replay_engine/config/default.yaml")
    args = parser.parse_args()
    if not args.pool_id and not args.pool_file:
        raise ValueError("pool-id or pool-file required")
    run_daily(args.date, args.pool_id, args.pool_file, args.config)


if __name__ == "__main__":
    main()
