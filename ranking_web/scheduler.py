from __future__ import annotations

import json
import threading
import time
import uuid
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ranking_web.services import (
    DEFAULT_CONFIG,
    UserInputError,
    format_path_for_storage,
    normalize_trade_date,
    parse_pool_id,
    resolve_config_path,
    resolve_pool_file,
    run_scoring,
)


class ScoreTaskScheduler:
    """Lightweight in-process scheduler.

    Uses a background loop that checks enabled tasks every few seconds and triggers
    matching jobs at minute granularity.
    """

    _DOW_MAP = {
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.tasks: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self._jobs: dict[str, dict[str, Any]] = {}
        self._last_fired: dict[str, str] = {}
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self.running = False

        self._load_state()
        self._sync_jobs()
        self._start_worker()

    def shutdown(self) -> None:
        self.running = False
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=1.0)

    def _start_worker(self) -> None:
        if self.running:
            return
        self.running = True
        self._worker = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._worker.start()

    def _load_state(self) -> None:
        if not self.state_file.exists():
            self._save_state()
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        self.tasks = [self._normalize_task(t) for t in data.get("tasks", [])]
        self.history = data.get("history", [])[:200]

    def _save_state(self) -> None:
        payload = {"tasks": self.tasks, "history": self.history[:200]}
        self.state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _normalize_task(self, task: dict[str, Any]) -> dict[str, Any]:
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        out = {
            "id": task.get("id") or uuid.uuid4().hex[:10],
            "name": task.get("name") or "Scoring Task",
            "hour": int(task.get("hour", 18)),
            "minute": int(task.get("minute", 0)),
            "day_of_week": task.get("day_of_week") or "mon-fri",
            "trade_date_mode": task.get("trade_date_mode") or "today",
            "fixed_trade_date": task.get("fixed_trade_date") or "",
            "pool_id": task.get("pool_id"),
            "pool_file": task.get("pool_file") or "",
            "config_path": task.get("config_path") or format_path_for_storage(DEFAULT_CONFIG),
            "enabled": bool(task.get("enabled", True)),
            "created_at": task.get("created_at") or now_text,
            "updated_at": task.get("updated_at") or now_text,
            "last_run_at": task.get("last_run_at") or "",
            "last_status": task.get("last_status") or "",
            "last_message": task.get("last_message") or "",
            "last_duration_sec": task.get("last_duration_sec") or 0,
        }
        return out

    def _sync_jobs(self) -> None:
        self._jobs = {}
        for task in self.tasks:
            if task.get("enabled"):
                self._schedule_task(task)

    @staticmethod
    def _job_id(task_id: str) -> str:
        return f"score_task_{task_id}"

    @classmethod
    def _parse_day_of_week(cls, expr: str) -> set[int] | None:
        expression = expr.strip().lower()
        if expression == "*":
            return None

        def parse_one(token: str) -> int:
            t = token.strip().lower()
            if t in cls._DOW_MAP:
                return cls._DOW_MAP[t]
            if t.isdigit():
                v = int(t)
                if 0 <= v <= 6:
                    return v
            raise ValueError(f"invalid day token: {token}")

        result: set[int] = set()
        for part in expression.split(","):
            p = part.strip()
            if not p:
                continue
            if "-" in p:
                left, right = p.split("-", 1)
                a = parse_one(left)
                b = parse_one(right)
                if a <= b:
                    for item in range(a, b + 1):
                        result.add(item)
                else:
                    for item in range(a, 7):
                        result.add(item)
                    for item in range(0, b + 1):
                        result.add(item)
            else:
                result.add(parse_one(p))

        if not result:
            raise ValueError("empty day_of_week")
        return result

    @classmethod
    def _cron_match(cls, task: dict[str, Any], dt: datetime) -> bool:
        if dt.hour != int(task["hour"]) or dt.minute != int(task["minute"]):
            return False
        allowed = cls._parse_day_of_week(str(task["day_of_week"]))
        if allowed is None:
            return True
        return dt.weekday() in allowed

    @classmethod
    def _next_run_time(cls, task: dict[str, Any], now: datetime | None = None) -> datetime | None:
        if not task.get("enabled"):
            return None
        base = (now or datetime.now().astimezone()).replace(second=0, microsecond=0) + timedelta(minutes=1)
        # Search up to 30 days ahead at minute granularity.
        for _ in range(30 * 24 * 60):
            if cls._cron_match(task, base):
                return base
            base += timedelta(minutes=1)
        return None

    def _schedule_task(self, task: dict[str, Any]) -> None:
        self._jobs[self._job_id(task["id"])] = {
            "task_id": task["id"],
        }

    def _remove_job(self, task_id: str) -> None:
        self._jobs.pop(self._job_id(task_id), None)

    def _scheduler_loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now().astimezone()
            key = now.strftime("%Y%m%d%H%M")
            with self.lock:
                current_tasks = [deepcopy(t) for t in self.tasks if t.get("enabled")]

            for task in current_tasks:
                try:
                    if self._cron_match(task, now):
                        job_id = self._job_id(task["id"])
                        if self._last_fired.get(job_id) != key:
                            self._last_fired[job_id] = key
                            self.run_now(task_id=task["id"], trigger="scheduled")
                except Exception:
                    # Keep scheduler loop alive even if one task is malformed.
                    continue

            time.sleep(5)

    def _find_task(self, task_id: str) -> dict[str, Any] | None:
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = deepcopy(self.tasks)
        for row in rows:
            next_run = self._next_run_time(row)
            row["next_run_at"] = next_run.astimezone().strftime("%Y-%m-%d %H:%M:%S") if next_run else ""
        return sorted(rows, key=lambda x: (x.get("enabled", False), x.get("created_at", "")), reverse=True)

    def list_history(self, limit: int = 80) -> list[dict[str, Any]]:
        with self.lock:
            return deepcopy(self.history[:limit])

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = (payload.get("name") or "Scoring Task").strip()
        if not name:
            raise UserInputError("Task name cannot be empty")

        hour = int(payload.get("hour", 18))
        minute = int(payload.get("minute", 0))
        if hour < 0 or hour > 23:
            raise UserInputError("hour must be in [0, 23]")
        if minute < 0 or minute > 59:
            raise UserInputError("minute must be in [0, 59]")

        day_of_week = (payload.get("day_of_week") or "mon-fri").strip().lower()
        try:
            self._parse_day_of_week(day_of_week)
        except ValueError as exc:
            raise UserInputError(f"Invalid day_of_week: {day_of_week}") from exc

        trade_date_mode = (payload.get("trade_date_mode") or "today").strip().lower()
        if trade_date_mode not in {"today", "fixed"}:
            raise UserInputError("trade_date_mode must be today or fixed")

        fixed_trade_date = ""
        if trade_date_mode == "fixed":
            fixed_trade_date = normalize_trade_date(payload.get("fixed_trade_date"))

        pool_id = parse_pool_id(payload.get("pool_id"))
        pool_file = resolve_pool_file(payload.get("pool_file"))
        if pool_id is None and pool_file is None:
            raise UserInputError("Please provide pool_id or pool_file")

        config_path = resolve_config_path(payload.get("config_path"))
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task = {
            "id": uuid.uuid4().hex[:10],
            "name": name,
            "hour": hour,
            "minute": minute,
            "day_of_week": day_of_week,
            "trade_date_mode": trade_date_mode,
            "fixed_trade_date": fixed_trade_date,
            "pool_id": pool_id,
            "pool_file": pool_file.name if pool_file else "",
            "config_path": format_path_for_storage(config_path),
            "enabled": True,
            "created_at": now_text,
            "updated_at": now_text,
            "last_run_at": "",
            "last_status": "",
            "last_message": "",
            "last_duration_sec": 0,
        }
        with self.lock:
            self.tasks.append(task)
            self._save_state()
            self._schedule_task(task)
        return deepcopy(task)

    def toggle_task(self, task_id: str) -> dict[str, Any]:
        with self.lock:
            task = self._find_task(task_id)
            if task is None:
                raise UserInputError("Task not found")
            task["enabled"] = not task["enabled"]
            task["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if task["enabled"]:
                self._schedule_task(task)
            else:
                self._remove_job(task_id)
            self._save_state()
            updated = deepcopy(task)
        return updated

    def delete_task(self, task_id: str) -> None:
        with self.lock:
            before = len(self.tasks)
            self.tasks = [t for t in self.tasks if t["id"] != task_id]
            if len(self.tasks) == before:
                raise UserInputError("Task not found")
            self._save_state()
        self._remove_job(task_id)

    def run_now(self, task_id: str, trigger: str = "manual", trade_date_override: str | None = None) -> None:
        with self.lock:
            task = self._find_task(task_id)
            if task is None:
                raise UserInputError("Task not found")
        thread = threading.Thread(
            target=self._execute_task,
            kwargs={"task_id": task_id, "trigger": trigger, "trade_date_override": trade_date_override},
            daemon=True,
        )
        thread.start()

    def _determine_trade_date(self, task: dict[str, Any], trade_date_override: str | None) -> str:
        if trade_date_override and trade_date_override.strip():
            return normalize_trade_date(trade_date_override)
        if task.get("trade_date_mode") == "fixed":
            return normalize_trade_date(task.get("fixed_trade_date"))
        return date.today().strftime("%Y%m%d")

    def _execute_task(self, task_id: str, trigger: str, trade_date_override: str | None) -> None:
        with self.lock:
            current_task = deepcopy(self._find_task(task_id))
        if current_task is None:
            return

        started = datetime.now()
        status = "SUCCESS"
        message = ""
        run_date = ""

        try:
            run_date = self._determine_trade_date(current_task, trade_date_override)
            pool_file = resolve_pool_file(current_task.get("pool_file")) if current_task.get("pool_file") else None
            config_path = resolve_config_path(current_task.get("config_path"))
            run_scoring(
                trade_date=run_date,
                pool_id=current_task.get("pool_id"),
                pool_file=pool_file,
                config_path=config_path,
            )
            message = f"Completed scoring for {run_date}"
        except Exception as exc:  # noqa: BLE001
            status = "FAILED"
            message = str(exc)

        finished = datetime.now()
        duration = round((finished - started).total_seconds(), 2)
        history_row = {
            "task_id": task_id,
            "task_name": current_task.get("name"),
            "trigger": trigger,
            "trade_date": run_date,
            "status": status,
            "message": message,
            "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": finished.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_sec": duration,
        }

        with self.lock:
            task_ref = self._find_task(task_id)
            if task_ref is not None:
                task_ref["last_run_at"] = history_row["finished_at"]
                task_ref["last_status"] = status
                task_ref["last_message"] = message
                task_ref["last_duration_sec"] = duration
                task_ref["updated_at"] = history_row["finished_at"]
            self.history.insert(0, history_row)
            self.history = self.history[:200]
            self._save_state()
