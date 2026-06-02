"""Programmatic field-level extraction scorer. Stdlib only. Ground truth for the playground."""
import re
from datetime import date


def _norm(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return None
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            pass
    # Strip thousands separators and currency symbols so "$1,299.00" == 1299.0
    # (commas are assumed to be thousands separators, valid for monetary amounts).
    num = re.sub(r"[,$£€\s]", "", s)
    if re.match(r"^-?\d+(\.\d+)?$", num):
        return float(num)
    return s.lower()


def score_fields(pred, gold, fields):
    pred = pred if isinstance(pred, dict) else {}
    correct = {f: _norm(pred.get(f)) == _norm(gold.get(f)) for f in fields}
    score = sum(correct.values()) / len(fields) if fields else 0.0
    return score, correct
