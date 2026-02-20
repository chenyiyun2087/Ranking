from pool_replay_engine.src.signals.trigger import compute_triggers


def test_trigger_breakout():
    rows = [
        {"close": 10.0, "high_60": 10.0, "vol_ratio": 1.6, "flow_3d": 100, "recent_breakout": 0, "low": 9.8, "ma20": 9.9},
        {"close": 9.9, "high_60": 10.0, "vol_ratio": 2.0, "flow_3d": 100, "recent_breakout": 0, "low": 9.7, "ma20": 9.8},
    ]
    out = compute_triggers(rows, {"vol_ratio_min": 1.5, "pullback_tol": 0.01, "pullback_vol_ratio_max": 1.0})
    assert out[0]["is_breakout"] is True
    assert out[1]["is_breakout"] is False


def test_trigger_pullback():
    rows = [
        {"close": 10.0, "high_60": 10.5, "vol_ratio": 0.8, "flow_3d": 100, "recent_breakout": 1, "low": 9.95, "ma20": 9.9},
        {"close": 9.8, "high_60": 10.5, "vol_ratio": 0.8, "flow_3d": 100, "recent_breakout": 1, "low": 9.7, "ma20": 9.9},
    ]
    out = compute_triggers(rows, {"vol_ratio_min": 1.5, "pullback_tol": 0.01, "pullback_vol_ratio_max": 1.0})
    assert out[0]["is_pullback"] is True
    assert out[1]["is_pullback"] is False
