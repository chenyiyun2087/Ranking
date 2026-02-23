from __future__ import annotations

import csv
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_CONFIG = PROJECT_ROOT / "pool_replay_engine" / "config" / "default.yaml"


class UserInputError(ValueError):
    """Raised when the UI submits invalid values."""


def normalize_trade_date(raw: str | None) -> str:
    if not raw or not raw.strip():
        return date.today().strftime("%Y%m%d")
    cleaned = raw.strip().replace("-", "")
    if not re.fullmatch(r"\d{8}", cleaned):
        raise UserInputError("trade_date must be in YYYYMMDD format")
    datetime.strptime(cleaned, "%Y%m%d")
    return cleaned


def list_pool_files() -> list[str]:
    files = [p.name for p in PROJECT_ROOT.glob("pool*.csv") if p.is_file()]
    return sorted(files)


def resolve_pool_file(file_name: str | None) -> Path | None:
    if not file_name:
        return None
    file_name = file_name.strip()
    if not file_name:
        return None
    candidate = PROJECT_ROOT / file_name
    if candidate.name not in list_pool_files() or not candidate.exists():
        raise UserInputError(f"Pool file not found: {file_name}")
    return candidate


def resolve_config_path(path_text: str | None) -> Path:
    if not path_text or not path_text.strip():
        return DEFAULT_CONFIG
    candidate = (PROJECT_ROOT / path_text.strip()).resolve()
    if not candidate.exists():
        raise UserInputError(f"Config file not found: {path_text}")
    return candidate


def format_path_for_storage(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def parse_pool_id(raw: str | None) -> int | None:
    if not raw or not raw.strip():
        return None
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise UserInputError("pool_id must be an integer") from exc


def ensure_pool_source(pool_id: int | None, pool_file: Path | None) -> None:
    if pool_id is None and pool_file is None:
        raise UserInputError("Please provide pool_id or pool_file")


def load_csv_rows(path: Path, limit: int | None = None) -> tuple[list[str], list[dict[str, str]], int]:
    if not path.exists():
        return [], [], 0
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    total = 0
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        for row in reader:
            total += 1
            if limit is None or len(rows) < limit:
                rows.append(row)
    return headers, rows, total


def load_score_tables(limit: int = 300) -> dict[str, Any]:
    table_map = {
        "battle": OUTPUT_DIR / "pool_battle_pool.csv",
        "candidate": OUTPUT_DIR / "pool_candidate_pool.csv",
        "hold": OUTPUT_DIR / "pool_hold_watch.csv",
        "risk": OUTPUT_DIR / "pool_risk_list.csv",
    }
    tables: dict[str, Any] = {}
    for key, file_path in table_map.items():
        headers, rows, total = load_csv_rows(file_path, limit=limit)
        tables[key] = {
            "headers": headers,
            "rows": rows,
            "total": total,
            "file": file_path.name,
        }
    return tables


def latest_report_file() -> Path | None:
    reports = sorted(OUTPUT_DIR.glob("report_pool_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


def parse_health_summary() -> dict[str, Any]:
    default = {
        "n_trigger": 0,
        "n_setup": 0,
        "n_hold": 0,
        "n_weaken": 0,
        "n_drop": 0,
        "n_avoid": 0,
        "up_ratio": 0.0,
        "report_name": "",
        "report_mtime": "",
    }
    report = latest_report_file()
    if report is None:
        return default

    text = report.read_text(encoding="utf-8")
    line_match = re.search(
        r"n_trigger=(\d+)\s+n_setup=(\d+)\s+n_hold=(\d+)\s+n_weaken=(\d+)\s+n_drop=(\d+)\s+n_avoid=(\d+)",
        text,
    )
    ratio_match = re.search(r"up_ratio=([0-9.]+)%", text)

    if line_match:
        default.update(
            {
                "n_trigger": int(line_match.group(1)),
                "n_setup": int(line_match.group(2)),
                "n_hold": int(line_match.group(3)),
                "n_weaken": int(line_match.group(4)),
                "n_drop": int(line_match.group(5)),
                "n_avoid": int(line_match.group(6)),
            }
        )
    if ratio_match:
        default["up_ratio"] = float(ratio_match.group(1))

    default["report_name"] = report.name
    default["report_mtime"] = datetime.fromtimestamp(report.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return default


def parse_codes(raw_text: str | None) -> list[str]:
    if not raw_text:
        return []
    pieces = re.split(r"[\s,;\n\r\t]+", raw_text.strip())
    values = [p.strip().upper() for p in pieces if p.strip()]
    # keep order while deduplicating
    seen: set[str] = set()
    ordered: list[str] = []
    for item in values:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def read_pool_codes(pool_file: Path) -> list[str]:
    _, rows, _ = load_csv_rows(pool_file)
    return [r.get("ts_code", "").strip() for r in rows if r.get("ts_code", "").strip()]


def write_pool_codes(pool_file: Path, codes: list[str]) -> None:
    with pool_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ts_code"])
        for code in codes:
            writer.writerow([code])


def update_pool_file(pool_file: Path, add_codes: list[str], remove_codes: list[str]) -> dict[str, int]:
    current = read_pool_codes(pool_file)
    current_set = set(current)

    add_count = 0
    for code in add_codes:
        if code not in current_set:
            current.append(code)
            current_set.add(code)
            add_count += 1

    remove_set = set(remove_codes)
    before = len(current)
    current = [code for code in current if code not in remove_set]
    removed_count = before - len(current)

    write_pool_codes(pool_file, current)
    return {
        "total": len(current),
        "added": add_count,
        "removed": removed_count,
    }


def replace_pool_file(pool_file: Path, codes: list[str]) -> dict[str, int]:
    write_pool_codes(pool_file, codes)
    return {"total": len(codes), "added": len(codes), "removed": 0}


def run_scoring(trade_date: str, pool_id: int | None, pool_file: Path | None, config_path: Path) -> dict[str, Any]:
    ensure_pool_source(pool_id, pool_file)
    from pool_replay_engine.cli import run_daily

    run_daily(
        date=trade_date,
        pool_id=pool_id,
        pool_file=str(pool_file) if pool_file is not None else None,
        config=str(config_path),
    )

    summary = parse_health_summary()
    return {
        "trade_date": trade_date,
        "pool_id": pool_id,
        "pool_file": pool_file.name if pool_file else "",
        "summary": summary,
    }
