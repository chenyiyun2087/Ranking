from __future__ import annotations

import os


def write_report(rows: list[dict], health_rows: list[dict], out_dir: str, pool_id: int, trade_date: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"report_pool_{pool_id}_{trade_date}.md")
    h = health_rows[0] if health_rows else {}
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Pool Replay Report pool={pool_id} date={trade_date}\n\n")
        f.write("## 池子健康度摘要\n")
        f.write(f"- n_trigger={h.get('n_trigger', 0)} n_setup={h.get('n_setup', 0)} n_hold={h.get('n_hold', 0)} n_weaken={h.get('n_weaken', 0)} n_drop={h.get('n_drop', 0)} n_avoid={h.get('n_avoid', 0)}\n")
        f.write(f"- up_ratio={h.get('up_ratio', 0):.2%}\n")
    return path
