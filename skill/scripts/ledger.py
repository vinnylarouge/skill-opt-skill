"""Deterministic score ledger + gate decision for skill-opt. Stdlib only."""
import csv
from pathlib import Path

FIELDS = ["iter", "kind", "version", "split", "mean_score", "n", "decision"]


def _path(run_dir):
    return Path(run_dir) / "ledger.csv"


def _read(run_dir):
    p = _path(run_dir)
    if not p.exists():
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def _append(run_dir, row):
    p = _path(run_dir)
    is_new = not p.exists()
    with p.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            w.writeheader()
        w.writerow(row)


def append_eval(run_dir, iter, version, split, scores):
    scores = list(scores)
    mean = sum(scores) / len(scores) if scores else 0.0
    _append(run_dir, {"iter": iter, "kind": "eval", "version": version,
                      "split": split, "mean_score": f"{mean:.6f}",
                      "n": len(scores), "decision": ""})
    return mean


def holdout_mean(run_dir, version):
    rows = [r for r in _read(run_dir)
            if r["kind"] == "eval" and r["version"] == version and r["split"] == "holdout"]
    if not rows:
        return None
    return float(rows[-1]["mean_score"])


def accepted_versions(run_dir):
    accepted = ["v0"]
    for r in _read(run_dir):
        if r["kind"] == "gate" and r["decision"] == "accept":
            accepted.append(r["version"])
    return accepted


def best(run_dir):
    scored = [(v, holdout_mean(run_dir, v)) for v in accepted_versions(run_dir)]
    scored = [(v, s) for v, s in scored if s is not None]
    if not scored:
        return (None, None)
    return max(scored, key=lambda t: t[1])


def decide(run_dir, iter, candidate_version, margin=0.0):
    cand = holdout_mean(run_dir, candidate_version)
    best_version, best_score = best(run_dir)
    accept = cand is not None and (best_score is None or cand > best_score + margin)
    shown = cand if cand is not None else 0.0
    _append(run_dir, {"iter": iter, "kind": "gate", "version": candidate_version,
                      "split": "holdout", "mean_score": f"{shown:.6f}", "n": "",
                      "decision": "accept" if accept else "reject"})
    if accept:
        return ("accept", candidate_version, cand)
    return ("reject", best_version, best_score)
