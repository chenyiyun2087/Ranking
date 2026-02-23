from __future__ import annotations

import json


def compute_base_score(rows: list[dict], weights: dict) -> list[float]:
    result = []
    for row in rows:
        result.append(
            weights.get("momentum", 0) * float(row.get("momentum_score") or 0)
            + weights.get("value", 0) * float(row.get("value_score") or 0)
            + weights.get("quality", 0) * float(row.get("quality_score") or 0)
            + weights.get("technical", 0) * float(row.get("technical_score") or 0)
            + weights.get("capital", 0) * float(row.get("capital_score") or 0)
            + weights.get("chip", 0) * float(row.get("chip_score") or 0)
        )
    return result


def compute_risk_penalty(rows: list[dict], cfg: dict) -> list[float]:
    out = []
    for row in rows:
        penalty = 0.0
        if float(row.get("atr_pct") or 0) > cfg["atr_pct_max"]:
            penalty += 10
        if float(row.get("cost_dev") or 0) > cfg["high_cost_dev"]:
            penalty += 8
        if float(row.get("vol_ratio") or 0) > 2 and float(row.get("close_pos") or 1) < 0.4:
            penalty += 8
        flags = json.loads(row.get("risk_flags", "{}"))
        if flags.get("one_price") == 1:
            penalty += 20
        out.append(penalty)
    return out
