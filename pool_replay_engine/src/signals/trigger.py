from __future__ import annotations


def compute_triggers(rows: list[dict], cfg: dict) -> list[dict]:
    out = []
    for row in rows:
        is_breakout = (
            row.get("close", 0) >= row.get("high_60", 0)
            and row.get("vol_ratio", 0) >= cfg["vol_ratio_min"]
            and row.get("flow_3d", 0) > 0
        )
        is_pullback = (
            row.get("recent_breakout", 0) >= 1
            and row.get("low", 0) <= float(row.get("ma20", 0)) * (1 + cfg["pullback_tol"])
            and row.get("close", 0) >= row.get("ma20", 0)
            and row.get("vol_ratio", 0) <= cfg["pullback_vol_ratio_max"]
            and row.get("flow_3d", 0) > 0
        )
        n = dict(row)
        n["is_breakout"] = is_breakout
        n["is_pullback"] = is_pullback
        n["is_trigger"] = is_breakout or is_pullback
        n["trigger_type"] = "breakout" if is_breakout else ("pullback" if is_pullback else "none")
        out.append(n)
    return out


def _pct_rank(values: list[float]) -> list[float]:
    pairs = sorted((v, i) for i, v in enumerate(values))
    n = len(values)
    ranks = [0.5] * n
    if n <= 1:
        return ranks
    for r, (_, i) in enumerate(pairs, start=1):
        ranks[i] = r / n
    return ranks


def compute_trigger_strength(rows: list[dict]) -> list[float]:
    s1 = _pct_rank([(r.get("close", 0) / (r.get("high_60", 1) or 1) - 1) for r in rows])
    s2 = _pct_rank([r.get("vol_ratio", 0) for r in rows])
    s3 = _pct_rank([r.get("flow_ratio_3d", 0) for r in rows])
    s4 = _pct_rank([r.get("close_pos", 0) for r in rows])
    s5 = _pct_rank([r.get("chip_stable_score", 0) for r in rows])
    return [100 * (0.25 * s1[i] + 0.25 * s2[i] + 0.25 * s3[i] + 0.15 * s4[i] + 0.10 * s5[i]) for i in range(len(rows))]
