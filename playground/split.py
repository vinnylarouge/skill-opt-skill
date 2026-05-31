"""Deterministic train/holdout split of a task suite. Stdlib only."""
import json
import random
from pathlib import Path


def load(path):
    data = json.loads(Path(path).read_text())
    return data["fields"], data["tasks"]


def train_holdout(path, holdout_fraction=0.3, seed=0):
    _fields, tasks = load(path)
    tasks = sorted(tasks, key=lambda t: t["id"])
    rng = random.Random(seed)
    order = tasks[:]
    rng.shuffle(order)
    n_hold = max(1, round(len(order) * holdout_fraction))
    holdout = sorted(order[:n_hold], key=lambda t: t["id"])
    train = sorted(order[n_hold:], key=lambda t: t["id"])
    if not train:
        raise ValueError(f"holdout_fraction={holdout_fraction} leaves no training tasks")
    return train, holdout
