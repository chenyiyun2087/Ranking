from pool_replay_engine.src.signals.filters import apply_hard_filters


def test_avoid_filters():
    rows = [
        {"is_st": 1, "list_days": 200, "vol": 100, "amount": 1e8, "high": 10, "low": 9},
        {"is_st": 0, "list_days": 20, "vol": 100, "amount": 1e8, "high": 10, "low": 9},
        {"is_st": 0, "list_days": 200, "vol": 0, "amount": 0, "high": 10, "low": 10},
    ]
    out = apply_hard_filters(rows, {"new_stock_days": 60, "min_amount": 50000000})
    assert [r["avoid"] for r in out] == [1, 1, 1]
