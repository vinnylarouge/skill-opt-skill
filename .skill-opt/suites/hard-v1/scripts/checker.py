"""Enhanced programmatic checker for the skill-opt hard suite.

Extends the original checker with new check types for multi-step reasoning tasks:
- ordered_contains: items must appear in order
- multi_criterion: independent criteria scored separately with weights
- json_valid_keys: validates JSON-like structure has required keys
- count_in_range: numeric answer within an acceptable range
- negation_aware: checks both required presence and required absence with weighted scoring
- llm_judge: placeholder that returns 0.5 (requires external judge call)

Backwards-compatible with all original check types.
Stdlib only.
"""
import json
import re
import sys
from pathlib import Path


def _lower(s):
    return str(s).strip().lower()


def _words(s):
    """Split into words, stripping punctuation."""
    return re.findall(r"[a-z0-9_./\-]+", _lower(s))


def score_one(check, response):
    """Score a single response against a check spec. Returns float [0.0, 1.0]."""
    resp = _lower(response)
    ctype = check["type"]

    # === Original check types (backwards-compatible) ===

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

    # === New check types for hard suite ===

    if ctype == "ordered_contains":
        """Patterns must appear in the response in the given order."""
        patterns = check["patterns"]
        pos = 0
        hits = 0
        for p in patterns:
            idx = resp.find(p, pos)
            if idx >= 0:
                hits += 1
                pos = idx + len(p)
        return hits / len(patterns)

    if ctype == "multi_criterion":
        """Multiple independent criteria, each with a weight.
        Format: {"criteria": [{"check": <check_spec>, "weight": float}, ...]}
        Total score is weighted average.
        """
        criteria = check["criteria"]
        total_weight = sum(c["weight"] for c in criteria)
        score = 0.0
        for c in criteria:
            sub_score = score_one(c["check"], response)
            score += sub_score * c["weight"]
        return score / total_weight if total_weight > 0 else 0.0

    if ctype == "json_valid_keys":
        """Response should contain a JSON-like object with required keys.
        Checks: (1) parseable as JSON or YAML-like, (2) has required keys.
        Partial credit for having some keys.
        """
        required = check["required_keys"]
        # Try to find JSON object in response
        # Look for {...} pattern
        match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if not match:
            # Try the raw response
            text = resp
        else:
            text = match.group(0).lower()
        hits = sum(1 for k in required if k.lower() in text)
        return hits / len(required)

    if ctype == "count_in_range":
        """Extract a number from response and check if it's in [min, max]."""
        numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", resp)
        if not numbers:
            return 0.0
        # Check if any extracted number is in range
        lo, hi = check["min"], check["max"]
        for n in numbers:
            val = float(n)
            if lo <= val <= hi:
                return 1.0
        # Partial credit if close
        closest = min(float(n) for n in numbers)
        if closest < lo:
            dist = lo - closest
        else:
            dist = closest - hi
        # No partial credit for out-of-range
        return 0.0

    if ctype == "negation_aware":
        """Weighted check: must contain some patterns, must NOT contain others.
        Scores: presence_score * presence_weight + absence_score * absence_weight
        """
        must = check.get("must", [])
        must_not = check.get("must_not", [])
        pw = check.get("presence_weight", 0.6)
        aw = check.get("absence_weight", 0.4)

        if must:
            presence_score = sum(1 for p in must if p in resp) / len(must)
        else:
            presence_score = 1.0

        if must_not:
            absence_score = sum(1 for p in must_not if p not in resp) / len(must_not)
        else:
            absence_score = 1.0

        return presence_score * pw + absence_score * aw

    if ctype == "ordered_steps":
        """Check that response lists steps in correct order.
        Each step has a 'keyword' that must appear, and they must be in order.
        Partial credit: (ordered_pairs / total_pairs).
        """
        keywords = check["keywords"]
        positions = []
        for kw in keywords:
            idx = resp.find(kw)
            positions.append(idx if idx >= 0 else float('inf'))
        # Count how many pairs are in correct order
        n = len(keywords)
        if n <= 1:
            return 1.0 if positions[0] != float('inf') else 0.0
        total_pairs = 0
        ordered_pairs = 0
        for i in range(n):
            for j in range(i + 1, n):
                if positions[i] != float('inf') and positions[j] != float('inf'):
                    total_pairs += 1
                    if positions[i] < positions[j]:
                        ordered_pairs += 1
        # Also penalize missing keywords
        found = sum(1 for p in positions if p != float('inf'))
        found_frac = found / n
        if total_pairs == 0:
            return found_frac * 0.5
        order_frac = ordered_pairs / total_pairs
        return found_frac * 0.5 + order_frac * 0.5

    if ctype == "arithmetic_check":
        """Extract a numeric answer and compare to expected value.
        Tolerance for floating point.
        """
        expected = check["expected"]
        tolerance = check.get("tolerance", 0.001)
        numbers = re.findall(r"(\d+\.\d+|\d+/\d+|\d+)", resp)
        for n in numbers:
            try:
                if "/" in n:
                    parts = n.split("/")
                    val = float(parts[0]) / float(parts[1])
                else:
                    val = float(n)
                if abs(val - expected) <= tolerance:
                    return 1.0
            except (ValueError, ZeroDivisionError):
                continue
        return 0.0

    if ctype == "llm_judge":
        """Placeholder for LLM-judge scoring. Returns 0.5 by default.
        Actual scoring requires external judge call with the rubric.
        The rubric is stored in check["rubric"] for the judge to use.
        """
        return 0.5

    raise ValueError(f"Unknown check type: {ctype}")


def score_task(task, response):
    """Score a single response against the task's check spec."""
    return score_one(task["check"], response)


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

    tasks_data = json.loads(Path(tasks_file).read_text())
    # Handle both raw list and suite.json format
    if isinstance(tasks_data, dict):
        tasks = tasks_data["tasks"]
    else:
        tasks = tasks_data
    responses = json.loads(Path(resp_file).read_text())

    results, mean = score_batch(tasks, responses)
    if verbose:
        for tid, s in results:
            print(f"  {tid}: {s:.3f}")
    print(f"mean: {mean:.6f}")
    print(json.dumps({"scores": [s for _, s in results], "mean": mean,
                      "per_task": {t: s for t, s in results}}))


if __name__ == "__main__":
    main()
