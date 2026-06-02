"""Programmatic checker for the skill-opt dogfood suite. Stdlib only."""
import json
import re
import sys
from pathlib import Path


def _lower(s):
    return str(s).strip().lower()


def score_task(task, response):
    """Score a single response against the task's check spec. Returns float [0.0, 1.0]."""
    resp = _lower(response)
    check = task["check"]
    ctype = check["type"]

    if ctype == "exact_lower":
        return 1.0 if resp == check["value"] else 0.0

    if ctype == "contains_any_lower":
        return 1.0 if any(p in resp for p in check["patterns"]) else 0.0

    if ctype == "contains_all_lower":
        hits = sum(1 for p in check["patterns"] if p in resp)
        return hits / len(check["patterns"])

    if ctype == "regex_lower":
        return 1.0 if re.search(check["pattern"], resp) else 0.0

    if ctype == "regex_all_lower":
        hits = sum(1 for p in check["patterns"] if re.search(p, resp))
        return hits / len(check["patterns"])

    if ctype == "starts_with_word_lower":
        first = resp.split()[0] if resp.split() else ""
        first = re.sub(r"[^a-z]", "", first)
        return 1.0 if first in check["patterns"] else 0.0

    if ctype == "starts_no_and_contains_any":
        first = resp.split()[0] if resp.split() else ""
        first = re.sub(r"[^a-z]", "", first)
        if first not in ("n", "no"):
            return 0.0
        return 1.0 if any(p in resp for p in check["patterns_after_no"]) else 0.5

    if ctype == "contains_all_lower_and_not_any":
        has_must = all(p in resp for p in check["must"])
        has_bad = any(p in resp for p in check["must_not"])
        if has_must and not has_bad:
            return 1.0
        if has_must and has_bad:
            return 0.5
        return 0.0

    raise ValueError(f"Unknown check type: {ctype}")


def score_batch(tasks, responses):
    """Score a batch of responses. Returns list of (task_id, score) tuples and mean."""
    results = []
    for task in tasks:
        tid = task["id"]
        resp = responses.get(tid, "")
        s = score_task(task, resp)
        results.append((tid, s))
    mean = sum(s for _, s in results) / len(results) if results else 0.0
    return results, mean


def main():
    """CLI: checker.py <tasks.json> <responses.json> [--verbose]"""
    tasks_file = sys.argv[1]
    resp_file = sys.argv[2]
    verbose = "--verbose" in sys.argv

    tasks = json.loads(Path(tasks_file).read_text())
    responses = json.loads(Path(resp_file).read_text())

    results, mean = score_batch(tasks, responses)
    if verbose:
        for tid, s in results:
            print(f"  {tid}: {s:.2f}")
    print(f"mean: {mean:.6f}")
    # Output JSON for ledger integration
    scores = [s for _, s in results]
    print(json.dumps({"scores": scores, "mean": mean, "per_task": {t: s for t, s in results}}))


if __name__ == "__main__":
    main()
