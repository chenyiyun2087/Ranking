from __future__ import annotations

import json


def compute_base_score(rows: list[dict], weights: dict) -> list[float]:
    result = []
    for row in rows:
        result.append(
            weights["momentum"] * row.get("momentum_score", 0)
            + weights["technical"] * row.get("technical_score", 0)
            + weights["capital"] * row.get("capital_score", 0)
            + weights["chip"] * row.get("chip_score", 0)
        )
    return result


def compute_risk_penalty(rows: list[dict], cfg: dict) -> list[float]:
    out = []
    for row in rows:
        penalty = 0.0
        if row.get("atr_pct", 0) > cfg["atr_pct_max"]:
            penalty += 10
        if row.get("cost_dev", 0) > cfg["high_cost_dev"]:
            penalty += 8
        if row.get("vol_ratio", 0) > 2 and row.get("close_pos", 1) < 0.4:
            penalty += 8
        flags = json.loads(row.get("risk_flags", "{}"))
        if flags.get("one_price") == 1:
            penalty += 20
        out.append(penalty)
    return out
