"""Stratified train/holdout split for hard-v2 suite."""
import json
import random
from collections import defaultdict
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parents[1]
SUITE = json.loads((SUITE_DIR / "suite.json").read_text())

random.seed(7331)
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

(SUITE_DIR / "tasks" / "holdout").mkdir(parents=True, exist_ok=True)
(SUITE_DIR / "tasks" / "train").mkdir(parents=True, exist_ok=True)
(SUITE_DIR / "tasks" / "holdout" / "tasks.json").write_text(json.dumps(holdout, indent=2))
(SUITE_DIR / "tasks" / "train" / "tasks.json").write_text(json.dumps(train, indent=2))

print(f"Suite: {SUITE['total']} tasks across {len(by_group)} groups")
print(f"Split: holdout={len(holdout)} train={len(train)}")
for group in sorted(by_group):
    h = sum(1 for t in holdout if t["group"] == group)
    tr = sum(1 for t in train if t["group"] == group)
    print(f"  {group:10s}: {h} holdout, {tr} train")
