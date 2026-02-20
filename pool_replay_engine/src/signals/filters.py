from __future__ import annotations

import json


def apply_hard_filters(rows: list[dict], cfg: dict) -> list[dict]:
    out = []
    for row in rows:
        flags = {}
        if row.get("is_st", 0) == 1:
            flags["st"] = 1
        if row.get("list_days", 9999) < cfg["new_stock_days"]:
            flags["new"] = 1
        if row.get("vol", 0) <= 0 or row.get("amount", 0) <= 0:
            flags["halt"] = 1
        if row.get("high") == row.get("low"):
            flags["one_price"] = 1
        if row.get("amount", 0) < cfg["min_amount"]:
            flags["illiquid"] = 1
        new_row = dict(row)
        new_row["risk_flags"] = json.dumps(flags, ensure_ascii=False)
        new_row["avoid"] = 1 if flags else 0
        out.append(new_row)
    return out
