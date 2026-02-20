from __future__ import annotations

import csv


def load_pool_file(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and "ts_code" not in rows[0]:
        raise ValueError("pool file must include ts_code")
    return rows
