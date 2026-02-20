from __future__ import annotations

import csv
import os


def _write(path: str, rows: list[dict]) -> None:
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_lists(rows: list[dict], out_dir: str, cfg: dict) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    battle = sorted([r for r in rows if r["state"] == "TRIGGER"], key=lambda x: x["pool_final_score"], reverse=True)[: cfg["topk_battle"]]
    candidate = sorted([r for r in rows if r["state"] == "SETUP"], key=lambda x: x["pool_final_score"], reverse=True)[: cfg["topk_candidate"]]
    hold = sorted([r for r in rows if r["state"] == "HOLD"], key=lambda x: x["base_score"], reverse=True)[: cfg["topk_hold"]]
    risk = sorted([r for r in rows if r["state"] in {"WEAKEN", "DROP", "AVOID"}], key=lambda x: x["pool_final_score"])
    paths = {
        "battle": os.path.join(out_dir, "pool_battle_pool.csv"),
        "candidate": os.path.join(out_dir, "pool_candidate_pool.csv"),
        "hold": os.path.join(out_dir, "pool_hold_watch.csv"),
        "risk": os.path.join(out_dir, "pool_risk_list.csv"),
    }
    _write(paths["battle"], battle)
    _write(paths["candidate"], candidate)
    _write(paths["hold"], hold)
    _write(paths["risk"], risk)
    return paths


def build_health(rows: list[dict], trade_date: str, pool_id: int) -> list[dict]:
    total = len(rows) or 1
    health = {
        "trade_date": trade_date,
        "pool_id": pool_id,
        "n_total": len(rows),
        "n_trigger": sum(r["state"] == "TRIGGER" for r in rows),
        "n_setup": sum(r["state"] == "SETUP" for r in rows),
        "n_hold": sum(r["state"] == "HOLD" for r in rows),
        "n_weaken": sum(r["state"] == "WEAKEN" for r in rows),
        "n_drop": sum(r["state"] == "DROP" for r in rows),
        "n_avoid": sum(r["state"] == "AVOID" for r in rows),
        "up_ratio": sum((r.get("ret_10", 0) > 0) for r in rows) / total,
        "avg_ret_10": sum(r.get("ret_10", 0) for r in rows) / total,
        "avg_base_score": sum(r.get("base_score", 0) for r in rows) / total,
    }
    health["summary"] = f"trigger={health['n_trigger']} setup={health['n_setup']} weaken={health['n_weaken']}"
    return [health]
