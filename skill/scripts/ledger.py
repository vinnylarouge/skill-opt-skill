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
    if not scores:
        raise ValueError("append_eval: scores must be non-empty")
    mean = sum(scores) / len(scores)
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
    """Accepted skill versions, baseline-first. Always includes "v0".

    Invariant (enforced by the optimization loop's SETUP phase): a holdout eval
    for "v0" MUST be recorded via append_eval before the first decide() call.
    Otherwise best() has no baseline score and the gate accepts the first
    candidate unconditionally (fail-open).
    """
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
    shown = f"{cand:.6f}" if cand is not None else ""
    _append(run_dir, {"iter": iter, "kind": "gate", "version": candidate_version,
                      "split": "holdout", "mean_score": shown, "n": "",
                      "decision": "accept" if accept else "reject"})
    if accept:
        return ("accept", candidate_version, cand)
    return ("reject", best_version, best_score)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="skill-opt deterministic ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record")
    for a in ("--run", "--version", "--split", "--scores"):
        r.add_argument(a, required=True)
    r.add_argument("--iter", type=int, required=True)

    g = sub.add_parser("gate")
    g.add_argument("--run", required=True)
    g.add_argument("--iter", type=int, required=True)
    g.add_argument("--candidate", required=True)
    g.add_argument("--margin", type=float, default=0.0)

    b = sub.add_parser("best")
    b.add_argument("--run", required=True)

    args = ap.parse_args()
    if args.cmd == "record":
        scores = [float(x) for x in args.scores.split(",") if x != ""]
        print(f"{append_eval(args.run, args.iter, args.version, args.split, scores):.6f}")
    elif args.cmd == "gate":
        outcome, version, score = decide(args.run, args.iter, args.candidate, args.margin)
        score_str = f"{score:.6f}" if score is not None else "None"
        print(f"{outcome} {version} {score_str}")
    elif args.cmd == "best":
        v, s = best(args.run)
        s_str = f"{s:.6f}" if s is not None else "None"
        print(f"{v} {s_str}")


if __name__ == "__main__":
    main()
