"""Execution-backed checker for hard-v2 suite.

Check types:
- exec_python: executes response as Python, validates output/exit code
- exec_ledger: runs ledger.py with extracted args, validates output
- json_schema: parses response as JSON, validates against schema
- token_limit: correct content + must be under N tokens (whitespace-split)
- exact_output: response must match expected output exactly (after strip/lower)
- multi_doc_synthesis: multiple required facts that come from different docs
- stateful_next_action: given fixture state, validates the correct next action
- regex_strict: full response must match a regex pattern
- composite: list of sub-checks, all must pass (AND logic, partial credit)

Stdlib + subprocess only.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = SUITE_DIR / "fixtures"
LEDGER_SCRIPT = SUITE_DIR.parents[1].parent / "skill" / "scripts" / "ledger.py"


def _lower(s):
    return str(s).strip().lower()


def _token_count(s):
    """Whitespace-split token count."""
    return len(s.split())


def _extract_json(resp):
    """Try to extract JSON from response (handles markdown code blocks)."""
    # Try raw parse first
    try:
        return json.loads(resp.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    # Try extracting from code block
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', resp, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass
    # Try finding {...} or [...]
    for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        m = re.search(pattern, resp)
        if m:
            try:
                return json.loads(m.group(0))
            except (json.JSONDecodeError, ValueError):
                pass
    return None


def _extract_command(resp):
    """Extract a shell command from response (handles code blocks, prefixes)."""
    # Check for code block
    m = re.search(r'```(?:bash|sh|shell)?\s*\n?(.*?)\n?```', resp, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Check for lines starting with $ or >
    for line in resp.strip().split('\n'):
        line = line.strip()
        if line.startswith('$ '):
            return line[2:]
        if line.startswith('> '):
            return line[2:]
    # Take the first non-empty line that looks like a command
    for line in resp.strip().split('\n'):
        line = line.strip()
        if line and (line.startswith('python') or line.startswith('ledger') or
                     line.startswith('./') or 'ledger.py' in line):
            return line
    return resp.strip().split('\n')[0].strip()


def score_one(check, response):
    """Score a single response against a check spec. Returns float [0.0, 1.0]."""
    resp = str(response).strip()
    resp_lower = _lower(response)
    ctype = check["type"]

    # === Execution-backed checks ===

    if ctype == "exec_python":
        """Execute response as Python code, validate stdout/exit code."""
        expected_output = check.get("expected_output", "").strip().lower()
        expected_contains = check.get("expected_contains", [])
        must_succeed = check.get("must_succeed", True)

        # Extract Python code from response
        code = resp
        m = re.search(r'```(?:python)?\s*\n?(.*?)\n?```', resp, re.DOTALL)
        if m:
            code = m.group(1)

        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=10,
                cwd=str(FIXTURES_DIR)
            )
            if must_succeed and result.returncode != 0:
                return 0.0

            output = result.stdout.strip().lower()
            score = 0.0

            if expected_output and output == expected_output:
                score = 1.0
            elif expected_contains:
                hits = sum(1 for p in expected_contains if p.lower() in output)
                score = hits / len(expected_contains)
            elif not expected_output and not expected_contains:
                # Just check it ran successfully
                score = 1.0 if result.returncode == 0 else 0.0

            return score
        except (subprocess.TimeoutExpired, Exception):
            return 0.0

    if ctype == "exec_ledger":
        """Extract ledger.py command from response, execute it, validate output."""
        fixture = check["fixture"]
        expected_output = check.get("expected_output", "").strip().lower()
        expected_contains = check.get("expected_contains", [])

        cmd_str = _extract_command(resp)
        # Rewrite to use fixture path
        fixture_path = str(FIXTURES_DIR / fixture)

        # Build the actual command
        # Replace any run path references with the fixture
        cmd_str = re.sub(r'--run\s+\S+', f'--run {fixture_path}', cmd_str)
        if '--run' not in cmd_str:
            cmd_str = cmd_str + f' --run {fixture_path}'

        # Ensure it calls ledger.py correctly
        if 'ledger.py' in cmd_str:
            # Extract subcommand and args
            parts = cmd_str.split()
            # Find ledger.py and take everything after
            try:
                idx = next(i for i, p in enumerate(parts) if 'ledger.py' in p)
                args = parts[idx+1:]
                full_cmd = [sys.executable, str(LEDGER_SCRIPT)] + args
            except StopIteration:
                return 0.0
        else:
            return 0.0

        try:
            result = subprocess.run(
                full_cmd, capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip().lower()

            if expected_output and expected_output in output:
                return 1.0
            elif expected_contains:
                hits = sum(1 for p in expected_contains if p.lower() in output)
                return hits / len(expected_contains)
            return 0.0
        except (subprocess.TimeoutExpired, Exception) as e:
            return 0.0

    # === JSON schema checks ===

    if ctype == "json_schema":
        """Parse response as JSON and validate against a schema."""
        schema = check["schema"]  # {"required_keys": [...], "types": {...}, "constraints": {...}}
        parsed = _extract_json(resp)
        if parsed is None:
            return 0.0

        score_parts = []

        # Check required keys
        if "required_keys" in schema:
            keys = schema["required_keys"]
            if isinstance(parsed, dict):
                hits = sum(1 for k in keys if k in parsed)
                score_parts.append(hits / len(keys))
            elif isinstance(parsed, list) and len(parsed) > 0:
                # Check first element of array for required keys
                first = parsed[0] if isinstance(parsed[0], dict) else {}
                hits = sum(1 for k in keys if k in first)
                score_parts.append(hits / len(keys))
            else:
                score_parts.append(0.0)

        # Check types
        if "types" in schema and isinstance(parsed, dict):
            type_map = {"str": str, "int": int, "float": (int, float),
                        "bool": bool, "list": list, "dict": dict}
            type_checks = schema["types"]
            hits = 0
            total = len(type_checks)
            for key, expected_type in type_checks.items():
                if key in parsed:
                    if isinstance(parsed[key], type_map.get(expected_type, object)):
                        hits += 1
            score_parts.append(hits / total if total > 0 else 1.0)

        # Check value constraints
        if "values" in schema and isinstance(parsed, dict):
            val_checks = schema["values"]
            hits = 0
            total = len(val_checks)
            for key, expected in val_checks.items():
                if key in parsed:
                    actual = str(parsed[key]).lower()
                    if isinstance(expected, list):
                        if actual in [str(e).lower() for e in expected]:
                            hits += 1
                    elif str(expected).lower() == actual:
                        hits += 1
            score_parts.append(hits / total if total > 0 else 1.0)

        # Check array length
        if "min_items" in schema:
            if isinstance(parsed, list):
                score_parts.append(1.0 if len(parsed) >= schema["min_items"] else 0.0)
            elif isinstance(parsed, dict) and "tasks" in parsed:
                score_parts.append(1.0 if len(parsed["tasks"]) >= schema["min_items"] else 0.0)

        return sum(score_parts) / len(score_parts) if score_parts else 0.0

    # === Token limit checks ===

    if ctype == "token_limit":
        """Check correctness AND enforce token limit."""
        max_tokens = check["max_tokens"]
        correctness_check = check["correctness"]

        # Score correctness
        correctness_score = score_one(correctness_check, response)

        # Check length
        tokens = _token_count(resp)
        if tokens > max_tokens:
            # Penalty: linear decay from full score to 0 at 2x the limit
            over = tokens - max_tokens
            penalty = min(1.0, over / max_tokens)
            return correctness_score * (1.0 - penalty)

        return correctness_score

    # === Exact output checks ===

    if ctype == "exact_output":
        """Response must match expected exactly (after normalization)."""
        expected = check["expected"].strip().lower()
        normalize = check.get("normalize", "strip_lower")

        actual = resp_lower
        if normalize == "strip_lower":
            actual = resp_lower
        elif normalize == "first_line":
            actual = resp_lower.split('\n')[0].strip()
        elif normalize == "first_word":
            actual = resp_lower.split()[0] if resp_lower.split() else ""

        return 1.0 if actual == expected else 0.0

    # === Multi-document synthesis ===

    if ctype == "multi_doc_synthesis":
        """Must contain facts from multiple named sources."""
        requirements = check["requirements"]  # [{"source": "...", "patterns": [...]}]
        scores = []
        for req in requirements:
            patterns = req["patterns"]
            hits = sum(1 for p in patterns if p.lower() in resp_lower)
            scores.append(min(1.0, hits / max(1, req.get("min_hits", 1))))
        return sum(scores) / len(scores) if scores else 0.0

    # === Stateful next-action ===

    if ctype == "stateful_next_action":
        """Given fixture state, validate correct next action."""
        valid_actions = check["valid_actions"]  # list of acceptable action descriptions
        invalid_actions = check.get("invalid_actions", [])

        has_valid = any(v.lower() in resp_lower for v in valid_actions)
        has_invalid = any(v.lower() in resp_lower for v in invalid_actions)

        if has_valid and not has_invalid:
            return 1.0
        elif has_valid and has_invalid:
            return 0.5
        return 0.0

    # === Regex strict ===

    if ctype == "regex_strict":
        """Full response must match a regex (after strip)."""
        pattern = check["pattern"]
        flags = re.IGNORECASE if check.get("case_insensitive", True) else 0
        if re.fullmatch(pattern, resp.strip(), flags):
            return 1.0
        # Partial: check if it matches anywhere
        if re.search(pattern, resp.strip(), flags):
            return 0.5
        return 0.0

    # === Composite (AND logic with weights) ===

    if ctype == "composite":
        """Multiple sub-checks, all scored independently, weighted average."""
        criteria = check["criteria"]
        total_weight = sum(c.get("weight", 1.0) for c in criteria)
        score = 0.0
        for c in criteria:
            w = c.get("weight", 1.0)
            s = score_one(c["check"], response)
            score += s * w
        return score / total_weight if total_weight > 0 else 0.0

    # === Legacy contains checks (for simpler tasks) ===

    if ctype == "contains_all_lower":
        patterns = check["patterns"]
        hits = sum(1 for p in patterns if p in resp_lower)
        return hits / len(patterns)

    if ctype == "contains_any_lower":
        return 1.0 if any(p in resp_lower for p in check["patterns"]) else 0.0

    raise ValueError(f"Unknown check type: {ctype}")


def score_task(task, response):
    return score_one(task["check"], response)


def score_batch(tasks, responses):
    results = []
    for task in tasks:
        tid = task["id"]
        resp = responses.get(tid, "")
        s = score_task(task, resp)
        results.append((tid, s))
    mean = sum(s for _, s in results) / len(results) if results else 0.0
    return results, mean


def main():
    import sys as _sys
    tasks_file = _sys.argv[1]
    resp_file = _sys.argv[2]
    verbose = "--verbose" in _sys.argv

    tasks_data = json.loads(Path(tasks_file).read_text())
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
