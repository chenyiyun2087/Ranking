from __future__ import annotations


def add_price_features(rows: list[dict], breakout_lookback: int = 60) -> list[dict]:
    by_code: dict[str, list[dict]] = {}
    for r in rows:
        by_code.setdefault(r["ts_code"], []).append(dict(r))
    out: list[dict] = []
    for code, series in by_code.items():
        series.sort(key=lambda x: x["trade_date"])
        for i, r in enumerate(series):
            window20 = series[max(0, i - 19): i + 1]
            window60 = series[max(0, i - 59): i + 1]
            highs = [x["high"] for x in series[max(0, i - breakout_lookback + 1): i + 1]]
            r["ma20"] = sum(x["close"] for x in window20) / len(window20)
            r["ma60"] = sum(x["close"] for x in window60) / len(window60)
            r["high_60"] = max(highs)
            r["vol_ma20"] = sum(x["vol"] for x in window20) / len(window20)
            r["vol_ratio"] = (r["vol"] / r["vol_ma20"]) if r["vol_ma20"] else 0
            spread = (r["high"] - r["low"]) or 1
            r["close_pos"] = (r["close"] - r["low"]) / spread
            r["atr_pct"] = spread / (r["close"] or 1)
            r["ma20_slope"] = r["ma20"] - (series[i - 1].get("ma20", r["ma20"]) if i > 0 else r["ma20"])
            r["ret_10"] = (r["close"] / series[i - 10]["close"] - 1) if i >= 10 and series[i - 10]["close"] else 0
            recent = series[max(0, i - 9): i + 1]
            r["recent_breakout"] = 1 if any(x["close"] >= x.get("high_60", x["high"]) for x in recent) else 0
            out.append(r)
    return out
