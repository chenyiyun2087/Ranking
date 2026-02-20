from pool_replay_engine.src.datastore import store
import json

# Load config
with open("pool_replay_engine/config/nvda-concept.json") as f:
    cfg = json.load(f)

# Get data store
ds = store.DataStore(cfg["db"]["read_uri"], cfg["db"]["write_uri"])

# Check which scores are available
print("Loading scores from database...")
date = "20260213"

# Get a sample stock with data
scores = ds.load_dws_scores_daily(["300502.SZ", "603912.SH"], date)
print(f"Found {len(scores)} rows")
for row in scores:
    print(f"Stock: {row['ts_code']}")
    print(f"  momentum_score: {row.get('momentum_score')} (type: {type(row.get('momentum_score'))})")
    print(f"  technical_score: {row.get('technical_score')} (type: {type(row.get('technical_score'))})")
    print(f"  capital_score: {row.get('capital_score')} (type: {type(row.get('capital_score'))})")
    print(f"  chip_score: {row.get('chip_score')} (type: {type(row.get('chip_score'))})")
    print()
