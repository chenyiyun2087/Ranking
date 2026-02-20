from pool_replay_engine.src.signals.scoring import compute_base_score


def test_scoring_ordering():
    rows = [
        {"momentum_score": 70, "technical_score": 70, "capital_score": 70, "chip_score": 70, "trigger_strength": 90},
        {"momentum_score": 70, "technical_score": 70, "capital_score": 70, "chip_score": 70, "trigger_strength": 0},
    ]
    base = compute_base_score(rows, {"momentum": 0.35, "technical": 0.30, "capital": 0.25, "chip": 0.10})
    final = [base[i] + 0.4 * rows[i]["trigger_strength"] for i in range(2)]
    assert final[0] > final[1]
