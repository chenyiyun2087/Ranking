from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
import pymysql
from contextlib import contextmanager


@dataclass
class DataStore:
    read_uri: str  # MySQL URI for reading from tushare_stock
    write_uri: str  # MySQL URI for writing to ranking database

    def _parse_mysql_uri(self, uri: str) -> dict:
        """Parse MySQL URI: mysql://user:password@host:port/database"""
        if uri.startswith("mysql://"):
            uri = uri[8:]
        
        # Parse credentials and host
        if "@" in uri:
            creds, host_db = uri.rsplit("@", 1)
            if ":" in creds:
                user, password = creds.split(":", 1)
            else:
                user = creds
                password = ""
        else:
            user = "root"
            password = ""
            host_db = uri
        
        # Parse host and database
        if "/" in host_db:
            host_port, database = host_db.rsplit("/", 1)
        else:
            host_port = host_db
            database = "ranking"
        
        # Parse host and port
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 3306
        
        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4"
        }

    @contextmanager
    def _connect_read(self):
        """Connection to tushare_stock database"""
        config = self._parse_mysql_uri(self.read_uri)
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset=config["charset"]
        )
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _connect_write(self):
        """Connection to ranking database"""
        config = self._parse_mysql_uri(self.write_uri)
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset=config["charset"]
        )
        try:
            yield conn
        finally:
            conn.close()

    def _load_rows(self, sql: str, params: list | tuple = (), use_write_db: bool = False) -> list[dict]:
        """Load rows from database"""
        connect_ctx = self._connect_write() if use_write_db else self._connect_read()
        with connect_ctx as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def get_trade_calendar(self, start_date: str, end_date: str) -> list[str]:
        rows = self._load_rows(
            "SELECT DISTINCT trade_date FROM dwd_stock_daily_standard WHERE trade_date BETWEEN %s AND %s ORDER BY trade_date",
            [start_date, end_date],
        )
        return [str(r["trade_date"]) for r in rows]

    def get_pool_members(self, pool_id: int, trade_date: str) -> list[str]:
        rows = self._load_rows(
            "SELECT ts_code FROM dwd_stock_pool_member WHERE pool_id=%s AND start_date<=%s AND (end_date IS NULL OR end_date>=%s)",
            [pool_id, trade_date, trade_date],
        )
        return [r["ts_code"] for r in rows]

    def _load_by_universe(self, table: str, fields: str, universe: list[str], start: str | None = None, end: str | None = None, trade_date: str | None = None) -> list[dict]:
        if not universe:
            return []
        ph = ",".join("%s" for _ in universe)
        sql = f"SELECT {fields} FROM {table} WHERE ts_code IN ({ph})"
        params: list = list(universe)
        if start and end:
            sql += " AND trade_date BETWEEN %s AND %s"
            params += [start, end]
        if trade_date:
            sql += " AND trade_date = %s"
            params += [trade_date]
        return self._load_rows(sql, params)

    def load_price_window(self, universe: list[str], start: str, end: str):
        return self._load_by_universe("dwd_stock_daily_standard", "trade_date, ts_code, adj_open as open, adj_high as high, adj_low as low, adj_close as close, vol, amount", universe, start=start, end=end)

    def load_label_daily(self, universe: list[str], trade_date: str):
        return self._load_by_universe("dwd_stock_label_daily", "ts_code, is_st, is_new, limit_type, market, industry", universe, trade_date=trade_date)

    def load_moneyflow_window(self, universe: list[str], start: str, end: str):
        return self._load_by_universe("ods_moneyflow", "trade_date, ts_code, buy_lg_amount, sell_lg_amount, buy_md_amount, sell_md_amount, buy_sm_amount, sell_sm_amount, net_mf_amount", universe, start=start, end=end)

    def load_chip_daily(self, universe: list[str], trade_date: str):
        return self._load_by_universe("dwd_chip_stability", "ts_code, winner_rate as chip_stable_score, cost_deviation as cost_dev", universe, trade_date=trade_date)

    def load_dws_scores_daily(self, universe: list[str], trade_date: str):
        if not universe:
            return []
        ph = ",".join("%s" for _ in universe)
        sql = f"""
        SELECT m.ts_code, m.momentum_score, v.value_score, q.quality_score, t.technical_score, c.capital_score, ch.chip_score
        FROM dws_momentum_score m
        LEFT JOIN dws_value_score v ON m.ts_code=v.ts_code AND m.trade_date=v.trade_date
        LEFT JOIN dws_quality_score q ON m.ts_code=q.ts_code AND m.trade_date=q.trade_date
        LEFT JOIN dws_technical_score t ON m.ts_code=t.ts_code AND m.trade_date=t.trade_date
        LEFT JOIN dws_capital_score c ON m.ts_code=c.ts_code AND m.trade_date=c.trade_date
        LEFT JOIN dws_chip_score ch ON m.ts_code=ch.ts_code AND m.trade_date=ch.trade_date
        WHERE m.ts_code IN ({ph}) AND m.trade_date=%s
        """
        return self._load_rows(sql, [*universe, trade_date])

    def load_prev_states(self, pool_id: int, prev_trade_date: str):
        rows = self._load_rows("SELECT ts_code,state FROM dws_pool_replay_daily WHERE pool_id=%s AND trade_date=%s", [pool_id, prev_trade_date])
        return {r["ts_code"]: r["state"] for r in rows}

    def upsert_pool_replay_daily(self, rows: list[dict]) -> None:
        print(f"[DEBUG] upsert_pool_replay_daily called with {len(rows)} rows")
        with self._connect_write() as conn:
            with conn.cursor() as cursor:
                # Create table if not exists
                cursor.execute("""CREATE TABLE IF NOT EXISTS dws_pool_replay_daily (
                    trade_date VARCHAR(8),
                    pool_id INTEGER,
                    ts_code VARCHAR(20),
                    state VARCHAR(20),
                    action VARCHAR(20),
                    base_score FLOAT,
                    trigger_strength FLOAT,
                    pool_final_score FLOAT,
                    risk_flags TEXT,
                    key_levels TEXT,
                    reasons TEXT,
                    updated_at DATETIME,
                    PRIMARY KEY (trade_date, pool_id, ts_code)
                ) CHARSET=utf8mb4""")
                
                # Insert or replace rows
                if rows:
                    cols = ["trade_date", "pool_id", "ts_code", "state", "action", "base_score", 
                            "trigger_strength", "pool_final_score", "risk_flags", "key_levels", "reasons", "updated_at"]
                    insert_count = 0
                    for r in rows:
                        vals = [r.get(c) for c in cols]
                        placeholders = ", ".join(["%s"] * len(cols))
                        sql = f"INSERT INTO dws_pool_replay_daily ({', '.join(cols)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE "
                        sql += ", ".join([f"{c}=VALUES({c})" for c in cols if c != "trade_date" and c != "pool_id" and c != "ts_code"])
                        cursor.execute(sql, vals)
                        insert_count += 1
                    print(f"[DEBUG] Inserted {insert_count} rows")
            conn.commit()
            print(f"[DEBUG] Committed")

    def upsert_pool_health_daily(self, rows: list[dict]) -> None:
        with self._connect_write() as conn:
            with conn.cursor() as cursor:
                # Create table if not exists
                cursor.execute("""CREATE TABLE IF NOT EXISTS dws_pool_health_daily (
                    trade_date VARCHAR(8),
                    pool_id INTEGER,
                    n_total INTEGER,
                    n_trigger INTEGER,
                    n_setup INTEGER,
                    n_hold INTEGER,
                    n_weaken INTEGER,
                    n_drop INTEGER,
                    n_avoid INTEGER,
                    up_ratio FLOAT,
                    avg_ret_10 FLOAT,
                    avg_base_score FLOAT,
                    summary TEXT,
                    PRIMARY KEY (trade_date, pool_id)
                ) CHARSET=utf8mb4""")
                
                # Insert or replace rows
                if rows:
                    for r in rows:
                        cols = list(r.keys())
                        vals = [r[c] for c in cols]
                        placeholders = ", ".join(["%s"] * len(cols))
                        sql = f"INSERT INTO dws_pool_health_daily ({', '.join(cols)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE "
                        sql += ", ".join([f"{c}=VALUES({c})" for c in cols if c != "trade_date" and c != "pool_id"])
                        cursor.execute(sql, vals)
            conn.commit()
