from __future__ import annotations


def add_flow_features(flow_rows: list[dict], price_rows: list[dict]) -> list[dict]:
    amount_map = {(r["ts_code"], r["trade_date"]): r.get("amount", 0) for r in price_rows}
    by_code: dict[str, list[dict]] = {}
    for r in flow_rows:
        by_code.setdefault(r["ts_code"], []).append(dict(r))
    out = []
    for code, series in by_code.items():
        series.sort(key=lambda x: x["trade_date"])
        for i, r in enumerate(series):
            r["flow_1d"] = r.get("net_inflow", 0)
            r["flow_3d"] = sum(x.get("net_inflow", 0) for x in series[max(0, i - 2): i + 1])
            r["flow_5d"] = sum(x.get("net_inflow", 0) for x in series[max(0, i - 4): i + 1])
            amount = amount_map.get((code, r["trade_date"]), 0) or 1
            r["flow_ratio"] = r.get("net_inflow", 0) / amount
            amount3 = sum(amount_map.get((code, x["trade_date"]), 0) for x in series[max(0, i - 2): i + 1]) or 1
            r["flow_ratio_3d"] = r["flow_3d"] / amount3
            out.append(r)
    return out
