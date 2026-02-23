from __future__ import annotations


def next_state(row: dict, prev_state: str, weaken_vol_ratio: float, setup_threshold: float = 15) -> str:
    if row.get("avoid", 0) == 1:
        return "AVOID"
    if row.get("close", 0) < row.get("ma60", 0) and prev_state == "WEAKEN":
        return "DROP"
    if (row.get("close", 0) < row.get("ma20", 0) and row.get("vol_ratio", 0) > weaken_vol_ratio) or row.get("flow_3d", 0) < 0:
        return "WEAKEN"
    if prev_state == "SETUP" and row.get("is_trigger", False):
        return "TRIGGER"
    if prev_state == "TRIGGER" and row.get("close", 0) >= row.get("ma20", 0) and row.get("flow_3d", 0) >= 0:
        return "HOLD"
    if row.get("close", 0) > row.get("ma60", 0) and row.get("ma20_slope", 0) > 0 and row.get("base_score", 0) >= setup_threshold:
        # Check if we can jump directly to TRIGGER (for same-day state transitions)
        if row.get("is_trigger", False):
            return "TRIGGER"
        return "SETUP"
    return "WATCH"


def state_to_action(state: str, is_pullback: bool = False) -> str:
    if state == "TRIGGER":
        return "BUY_READY"
    if state == "HOLD" and is_pullback:
        return "ADD"
    if state == "HOLD":
        return "HOLD"
    if state == "WEAKEN":
        return "REDUCE"
    if state == "DROP":
        return "SELL"
    if state == "AVOID":
        return "AVOID"
    return "WATCH"


def apply_state_machine(rows: list[dict], prev_states: dict[str, str], weaken_vol_ratio: float, setup_threshold: float = 15) -> list[dict]:
    print(f"[DEBUG] apply_state_machine called with {len(rows)} rows")
    out = []
    try:
        for row in rows:
            prev = prev_states.get(row["ts_code"], "WATCH")
            state = next_state(row, prev, weaken_vol_ratio, setup_threshold)
            n = dict(row)
            n["prev_state"] = prev
            n["state"] = state
            n["action"] = state_to_action(state, bool(row.get("is_pullback", False)))
            out.append(n)
        print(f"[DEBUG] apply_state_machine returning {len(out)} rows")
    except Exception as e:
        print(f"[DEBUG] apply_state_machine error: {e}")
        import traceback
        traceback.print_exc()
        raise
    return out
