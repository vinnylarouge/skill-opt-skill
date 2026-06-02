"""Programmatic scorer for the skill-opt dogfood suite. Stdlib only.

Each task's `check` is a small DSL spec. score() returns a float in [0,1].
"""
import json
import re
import sys
from pathlib import Path


def _first_token(s):
    """First word token (alnum) of response, lowercased."""
    m = re.search(r"[A-Za-z]+", s)
    return m.group(0).lower() if m else ""


def score_one(check, response):
    r = response.lower()
    t = check["type"]

    if t == "exact_lower":
        # Response must contain the exact value as a whole-word substring.
        v = check["value"].lower()
        return 1.0 if re.search(rf"\b{re.escape(v)}\b", r) else 0.0

    if t == "contains_any_lower":
        for p in check["patterns"]:
            if p.lower() in r:
                return 1.0
        return 0.0

    if t == "contains_all_lower":
        hits = sum(1 for p in check["patterns"] if p.lower() in r)
        total = len(check["patterns"])
        return hits / total if total else 0.0

    if t == "regex_lower":
        return 1.0 if re.search(check["pattern"], r) else 0.0

    if t == "regex_all_lower":
        hits = sum(1 for p in check["patterns"] if re.search(p, r))
        total = len(check["patterns"])
        return hits / total if total else 0.0

    if t == "starts_with_word_lower":
        tok = _first_token(r)
        return 1.0 if tok in [p.lower() for p in check["patterns"]] else 0.0

    if t == "contains_all_lower_and_not_any":
        must_hits = sum(1 for p in check["must"] if p.lower() in r)
        must_total = len(check["must"])
        must_score = must_hits / must_total if must_total else 0.0
        bad = any(p.lower() in r for p in check["must_not"])
        return must_score * (0.0 if bad else 1.0)

    if t == "starts_no_and_contains_any":
        tok = _first_token(r)
        starts_no = tok in {"n", "no"}
        has_reason = any(p.lower() in r for p in check["patterns_after_no"])
        if starts_no and has_reason:
            return 1.0
        if starts_no or has_reason:
            return 0.5
        return 0.0

    raise ValueError(f"unknown check type: {t}")


def main():
    if len(sys.argv) < 3:
        print("usage: checker.py <suite.json> <results.json> [--ids id1,id2,...]", file=sys.stderr)
        sys.exit(2)
    suite = json.loads(Path(sys.argv[1]).read_text())
    results = json.loads(Path(sys.argv[2]).read_text())
    ids_filter = None
    if len(sys.argv) >= 5 and sys.argv[3] == "--ids":
        ids_filter = set(sys.argv[4].split(","))

    by_id = {t["id"]: t for t in suite["tasks"]}
    scores = {}
    for r in results:
        tid = r["id"]
        if ids_filter is not None and tid not in ids_filter:
            continue
        task = by_id[tid]
        scores[tid] = round(score_one(task["check"], r["response"]), 4)

    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
