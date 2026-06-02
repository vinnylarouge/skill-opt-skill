"""Stratified train/holdout split for the hard-v1 suite. Stdlib only.

Picks holdout_fraction of tasks per group (rounded up), seed=42 deterministic.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parents[1]
SUITE = json.loads((SUITE_DIR / "suite.json").read_text())

random.seed(42)
by_group = defaultdict(list)
for t in SUITE["tasks"]:
    by_group[t["group"]].append(t)

holdout, train = [], []
hf = SUITE["holdout_fraction"]
for group, items in sorted(by_group.items()):
    items = sorted(items, key=lambda x: x["id"])
    random.shuffle(items)
    k = max(1, round(len(items) * hf))
    holdout += items[:k]
    train += items[k:]

holdout.sort(key=lambda x: x["id"])
train.sort(key=lambda x: x["id"])

# Write output
tasks_dir = SUITE_DIR / "tasks"
(tasks_dir / "holdout").mkdir(parents=True, exist_ok=True)
(tasks_dir / "train").mkdir(parents=True, exist_ok=True)
(tasks_dir / "holdout" / "tasks.json").write_text(json.dumps(holdout, indent=2))
(tasks_dir / "train" / "tasks.json").write_text(json.dumps(train, indent=2))

print(f"Suite: {SUITE['total']} tasks across {len(by_group)} groups")
print(f"Split: holdout={len(holdout)} train={len(train)} (fraction={hf})")
print(f"\nPer-group breakdown:")
for group in sorted(by_group):
    h = [t for t in holdout if t["group"] == group]
    tr = [t for t in train if t["group"] == group]
    print(f"  {group:12s}: {len(h)} holdout, {len(tr)} train")
print(f"\nHoldout IDs: {[t['id'] for t in holdout]}")
print(f"Train IDs: {[t['id'] for t in train]}")
