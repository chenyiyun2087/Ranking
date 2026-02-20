from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass
class DataStore:
    db_uri: str

    def __post_init__(self) -> None:
        self.db_path = self.db_uri.replace("sqlite:///", "")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _load_rows(self, sql: str, params: list | tuple = ()) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_trade_calendar(self, start_date: str, end_date: str) -> list[str]:
        rows = self._load_rows(
            "SELECT DISTINCT trade_date FROM dwd_stock_daily_standard WHERE trade_date BETWEEN ? AND ? ORDER BY trade_date",
            [start_date, end_date],
        )
        return [str(r["trade_date"]) for r in rows]

    def get_pool_members(self, pool_id: int, trade_date: str) -> list[str]:
        rows = self._load_rows(
            "SELECT ts_code FROM dwd_stock_pool_member WHERE pool_id=? AND start_date<=? AND (end_date IS NULL OR end_date>=?)",
            [pool_id, trade_date, trade_date],
        )
        return [r["ts_code"] for r in rows]

    def _load_by_universe(self, table: str, fields: str, universe: list[str], start: str | None = None, end: str | None = None, trade_date: str | None = None) -> list[dict]:
        if not universe:
            return []
        ph = ",".join("?" for _ in universe)
        sql = f"SELECT {fields} FROM {table} WHERE ts_code IN ({ph})"
        params: list = list(universe)
        if start and end:
            sql += " AND trade_date BETWEEN ? AND ?"
            params += [start, end]
        if trade_date:
            sql += " AND trade_date = ?"
            params += [trade_date]
        return self._load_rows(sql, params)

    def load_price_window(self, universe: list[str], start: str, end: str):
        return self._load_by_universe("dwd_stock_daily_standard", "trade_date, ts_code, open, high, low, close, vol, amount", universe, start=start, end=end)

    def load_label_daily(self, universe: list[str], trade_date: str):
        return self._load_by_universe("dwd_stock_label_daily", "ts_code, is_st, is_new, list_days, limit_pct, sw_industry_code, board", universe, trade_date=trade_date)

    def load_moneyflow_window(self, universe: list[str], start: str, end: str):
        return self._load_by_universe("ods_moneyflow", "trade_date, ts_code, net_inflow, big_net_inflow, mid_net_inflow, small_net_inflow", universe, start=start, end=end)

    def load_chip_daily(self, universe: list[str], trade_date: str):
        return self._load_by_universe("dwd_chip_stability", "ts_code, chip_stable_score, cost_dev", universe, trade_date=trade_date)

    def load_dws_scores_daily(self, universe: list[str], trade_date: str):
        if not universe:
            return []
        ph = ",".join("?" for _ in universe)
        sql = f"""
        SELECT m.ts_code, m.score AS momentum_score, t.score AS technical_score, c.score AS capital_score, ch.score AS chip_score
        FROM dws_momentum_score m
        LEFT JOIN dws_technical_score t ON m.ts_code=t.ts_code AND m.trade_date=t.trade_date
        LEFT JOIN dws_capital_score c ON m.ts_code=c.ts_code AND m.trade_date=c.trade_date
        LEFT JOIN dws_chip_score ch ON m.ts_code=ch.ts_code AND m.trade_date=ch.trade_date
        WHERE m.ts_code IN ({ph}) AND m.trade_date=?
        """
        return self._load_rows(sql, [*universe, trade_date])

    def load_prev_states(self, pool_id: int, prev_trade_date: str):
        rows = self._load_rows("SELECT ts_code,state FROM dws_pool_replay_daily WHERE pool_id=? AND trade_date=?", [pool_id, prev_trade_date])
        return {r["ts_code"]: r["state"] for r in rows}

    def upsert_pool_replay_daily(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS dws_pool_replay_daily (
                    trade_date TEXT,pool_id INTEGER,ts_code TEXT,state TEXT,action TEXT,
                    base_score REAL,trigger_strength REAL,pool_final_score REAL,risk_flags TEXT,
                    key_levels TEXT,reasons TEXT,updated_at TEXT,
                    PRIMARY KEY (trade_date,pool_id,ts_code))""")
            for r in rows:
                cols = ["trade_date","pool_id","ts_code","state","action","base_score","trigger_strength","pool_final_score","risk_flags","key_levels","reasons","updated_at"]
                vals = [r.get(c) for c in cols]
                conn.execute(f"INSERT OR REPLACE INTO dws_pool_replay_daily ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", vals)

    def upsert_pool_health_daily(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS dws_pool_health_daily (
                trade_date TEXT,pool_id INTEGER,n_total INTEGER,n_trigger INTEGER,n_setup INTEGER,n_hold INTEGER,
                n_weaken INTEGER,n_drop INTEGER,n_avoid INTEGER,up_ratio REAL,avg_ret_10 REAL,avg_base_score REAL,summary TEXT,
                PRIMARY KEY (trade_date,pool_id))""")
            for r in rows:
                cols = list(r.keys())
                conn.execute(f"INSERT OR REPLACE INTO dws_pool_health_daily ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", [r[c] for c in cols])
