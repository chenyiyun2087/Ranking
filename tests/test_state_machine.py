from pool_replay_engine.src.signals.state_machine import apply_state_machine


def test_state_transition():
    rows = [{
        "ts_code": "000001.SZ", "avoid": 0, "close": 10, "ma60": 9, "ma20": 9.5,
        "vol_ratio": 1.6, "flow_3d": 200, "is_trigger": True, "ma20_slope": 0.1,
        "base_score": 70, "is_pullback": False,
    }]
    out = apply_state_machine(rows, {"000001.SZ": "SETUP"}, weaken_vol_ratio=1.2)
    assert out[0]["state"] == "TRIGGER"
