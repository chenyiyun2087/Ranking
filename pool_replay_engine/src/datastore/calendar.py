from __future__ import annotations


def prev_trade_date(calendar: list[str], trade_date: str) -> str | None:
    if trade_date not in calendar:
        return None
    idx = calendar.index(trade_date)
    if idx <= 0:
        return None
    return calendar[idx - 1]
