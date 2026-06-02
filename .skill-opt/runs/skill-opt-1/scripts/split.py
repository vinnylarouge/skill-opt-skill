"""Stratified train/holdout split for dogfood suite. Stdlib only.

Picks holdout_fraction of tasks per group (rounded up), seed=1337 deterministic.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

RUN = Path(__file__).resolve().parents[1]
SUITE = json.loads((RUN / "tasks" / "suite.json").read_text())

random.seed(1337)
by_group = defaultdict(list)
for t in SUITE["tasks"]:
    by_group[t["group"]].append(t)

holdout, train = [], []
hf = SUITE["holdout_fraction"]
for group, items in by_group.items():
    items = sorted(items, key=lambda x: x["id"])
    random.shuffle(items)
    k = max(1, round(len(items) * hf))
    holdout += items[:k]
    train += items[k:]

holdout.sort(key=lambda x: x["id"])
train.sort(key=lambda x: x["id"])

(RUN / "tasks" / "holdout" / "tasks.json").write_text(json.dumps(holdout, indent=2))
(RUN / "tasks" / "train" / "tasks.json").write_text(json.dumps(train, indent=2))
print(f"holdout={len(holdout)} train={len(train)}")
print("holdout ids:", [t["id"] for t in holdout])
print("train ids:", [t["id"] for t in train])
