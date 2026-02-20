from __future__ import annotations


def normalize_label(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        n = dict(r)
        n.setdefault("is_st", 0)
        n.setdefault("is_new", 0)
        n.setdefault("list_days", 9999)
        n.setdefault("limit_pct", 10)
        n.setdefault("sw_industry_code", "")
        n.setdefault("board", "")
        out.append(n)
    return out
