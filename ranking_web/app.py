from __future__ import annotations

import atexit
import csv
import io
import os
from pathlib import Path
from typing import Any

from flask import Flask, flash, redirect, render_template, request, url_for

from ranking_web.scheduler import ScoreTaskScheduler
from ranking_web.services import (
    PROJECT_ROOT,
    UserInputError,
    ensure_pool_source,
    list_pool_files,
    load_csv_rows,
    load_score_tables,
    normalize_trade_date,
    parse_codes,
    parse_health_summary,
    parse_pool_id,
    replace_pool_file,
    resolve_config_path,
    resolve_pool_file,
    run_scoring,
    update_pool_file,
)


_scheduler_singleton: ScoreTaskScheduler | None = None


def get_scheduler() -> ScoreTaskScheduler:
    global _scheduler_singleton
    if _scheduler_singleton is None:
        state_file = PROJECT_ROOT / "web_data" / "scheduler_state.json"
        _scheduler_singleton = ScoreTaskScheduler(state_file=state_file)
        atexit.register(_scheduler_singleton.shutdown)
    return _scheduler_singleton


def _load_codes_from_upload(file_storage: Any) -> list[str]:
    if file_storage is None or not file_storage.filename:
        return []

    raw_bytes = file_storage.read()
    text = raw_bytes.decode("utf-8-sig", errors="ignore")
    if not text.strip():
        return []

    try:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames and "ts_code" in reader.fieldnames:
            codes = [row.get("ts_code", "").strip().upper() for row in reader if row.get("ts_code", "").strip()]
            return parse_codes("\n".join(codes))
    except csv.Error:
        pass

    return parse_codes(text)


def _build_dashboard_context() -> dict[str, Any]:
    score_tables = load_score_tables(limit=12)
    health = parse_health_summary()
    pool_files = list_pool_files()
    return {
        "health": health,
        "score_tables": score_tables,
        "pool_files": pool_files,
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("RANKING_WEB_SECRET", "ranking-web-local-secret")
    # Start background scheduler at app boot so timed jobs work without opening scheduler page.
    get_scheduler()

    @app.route("/")
    def dashboard() -> str:
        ctx = _build_dashboard_context()
        return render_template("dashboard.html", **ctx)

    @app.route("/run-score", methods=["POST"])
    def run_score() -> Any:
        try:
            trade_date = normalize_trade_date(request.form.get("trade_date"))
            pool_id = parse_pool_id(request.form.get("pool_id"))
            pool_file = resolve_pool_file(request.form.get("pool_file"))
            config_path = resolve_config_path(request.form.get("config_path"))
            ensure_pool_source(pool_id, pool_file)
            result = run_scoring(trade_date=trade_date, pool_id=pool_id, pool_file=pool_file, config_path=config_path)
            summary = result["summary"]
            flash(
                f"Scoring finished for {trade_date}. trigger={summary['n_trigger']}, setup={summary['n_setup']}, weaken={summary['n_weaken']}",
                "success",
            )
        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")
        return redirect(url_for("dashboard"))

    @app.route("/scheduler")
    def scheduler_page() -> str:
        scheduler = get_scheduler()
        tasks = scheduler.list_tasks()
        history = scheduler.list_history(limit=100)
        pool_files = list_pool_files()
        return render_template("scheduler.html", tasks=tasks, history=history, pool_files=pool_files)

    @app.route("/scheduler/create", methods=["POST"])
    def scheduler_create() -> Any:
        scheduler = get_scheduler()
        payload = {
            "name": request.form.get("name"),
            "hour": request.form.get("hour"),
            "minute": request.form.get("minute"),
            "day_of_week": request.form.get("day_of_week"),
            "trade_date_mode": request.form.get("trade_date_mode"),
            "fixed_trade_date": request.form.get("fixed_trade_date"),
            "pool_id": request.form.get("pool_id"),
            "pool_file": request.form.get("pool_file"),
            "config_path": request.form.get("config_path"),
        }
        try:
            task = scheduler.create_task(payload)
            flash(f"Task created: {task['name']}", "success")
        except UserInputError as exc:
            flash(str(exc), "error")
        except Exception as exc:  # noqa: BLE001
            flash(f"Failed to create task: {exc}", "error")
        return redirect(url_for("scheduler_page"))

    @app.route("/scheduler/<task_id>/toggle", methods=["POST"])
    def scheduler_toggle(task_id: str) -> Any:
        scheduler = get_scheduler()
        try:
            task = scheduler.toggle_task(task_id)
            state_text = "enabled" if task["enabled"] else "paused"
            flash(f"Task {task['name']} is now {state_text}", "success")
        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")
        return redirect(url_for("scheduler_page"))

    @app.route("/scheduler/<task_id>/delete", methods=["POST"])
    def scheduler_delete(task_id: str) -> Any:
        scheduler = get_scheduler()
        try:
            scheduler.delete_task(task_id)
            flash("Task deleted", "success")
        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")
        return redirect(url_for("scheduler_page"))

    @app.route("/scheduler/<task_id>/run", methods=["POST"])
    def scheduler_run(task_id: str) -> Any:
        scheduler = get_scheduler()
        date_override = request.form.get("trade_date_override")
        try:
            scheduler.run_now(task_id=task_id, trade_date_override=date_override, trigger="manual")
            flash("Task started in background", "success")
        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")
        return redirect(url_for("scheduler_page"))

    @app.route("/pool")
    def pool_page() -> str:
        pool_files = list_pool_files()
        selected = request.args.get("file") or (pool_files[0] if pool_files else "")

        headers: list[str] = []
        rows: list[dict[str, str]] = []
        total = 0
        if selected:
            selected_path = resolve_pool_file(selected)
            if selected_path is not None:
                headers, rows, total = load_csv_rows(selected_path, limit=200)

        return render_template(
            "pool.html",
            pool_files=pool_files,
            selected=selected,
            headers=headers,
            rows=rows,
            total=total,
        )

    @app.route("/pool/update", methods=["POST"])
    def pool_update() -> Any:
        target_file = request.form.get("target_file")
        action = (request.form.get("action") or "update").strip().lower()

        try:
            pool_path = resolve_pool_file(target_file)
            if pool_path is None:
                raise UserInputError("Please choose a pool file")

            add_codes = parse_codes(request.form.get("add_codes"))
            remove_codes = parse_codes(request.form.get("remove_codes"))
            upload_codes = _load_codes_from_upload(request.files.get("upload_file"))

            if action == "replace":
                if not upload_codes and not add_codes:
                    raise UserInputError("Replace mode needs upload file or code list")
                result = replace_pool_file(pool_path, upload_codes if upload_codes else add_codes)
                flash(f"Pool replaced. total={result['total']}", "success")
            else:
                result = update_pool_file(pool_path, add_codes=add_codes + upload_codes, remove_codes=remove_codes)
                flash(
                    f"Pool updated. total={result['total']} added={result['added']} removed={result['removed']}",
                    "success",
                )
        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")

        return redirect(url_for("pool_page", file=target_file))

    @app.route("/scores")
    def scores_page() -> str:
        table = (request.args.get("table") or "candidate").strip().lower()
        score_tables = load_score_tables(limit=500)
        if table not in score_tables:
            table = "candidate"
        health = parse_health_summary()
        return render_template("scores.html", score_tables=score_tables, active_table=table, health=health)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8050, debug=False)
