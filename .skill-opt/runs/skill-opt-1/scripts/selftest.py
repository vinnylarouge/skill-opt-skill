"""Self-test the checker on gold-correct synthetic responses."""
import json
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUN / "scripts"))
from checker import score_one  # noqa: E402

SUITE = json.loads((RUN / "tasks" / "suite.json").read_text())

# Best-case "perfect" responses crafted to satisfy each check.
gold_resp = {
    "t000": "autonomous",
    "t001": "user-suite",
    "t002": "0.3",
    "t003": "{max_ops: 3, max_words: 80}",
    "t004": "6",
    "t005": "3",
    "t006": "proposed-ratified, autonomous, user-suite, live",
    "t007": "candidates/iter-03/candidate.md",
    "t008": "ledger.csv",
    "t009": "memory/rejected-edits.md",
    "t010": "skill/v0.md",
    "t011": "skill/v(K+1).md and skill/current.md",
    "t012": "iter, kind, version, split, mean_score, n, decision",
    "t013": "rollout, score, reflect, edit, gate, memory",
    "t014": "N",
    "t015": "only the current skill text and the task",
    "t016": "success set and failure set",
    "t017": "N. The decision is deterministic arithmetic via ledger.py gate.",
    "t018": "N",
    "t019": "ask for a trimmed proposal",
    "t020": "memory/rejected-edits.md",
    "t021": "N",
    "t022": "false",
    "t023": "reject (strict tie)",
    "t024": "accept",
    "t025": "python skill/scripts/ledger.py gate --run .skill-opt/runs/foo-1/ --iter 2 --candidate c2",
    "t026": "eval and gate",
    "t027": "Otherwise best() returns None and the first candidate is accepted unconditionally (fail-open).",
    "t028": "Start iter 3",
    "t029": "Score the trajectory (run the judge / compute score.json).",
}

worst_resp = {tid: "I don't know." for tid in gold_resp}

by_id = {t["id"]: t for t in SUITE["tasks"]}

bad = []
for tid, resp in gold_resp.items():
    s = score_one(by_id[tid]["check"], resp)
    if s < 1.0:
        bad.append((tid, s, resp))

print(f"gold pass: {len(gold_resp) - len(bad)}/{len(gold_resp)}")
for tid, s, resp in bad:
    print(f"  FAIL gold {tid}={s} resp={resp!r}")

# Worst-case should score 0 across the board.
nonzero = []
for tid, resp in worst_resp.items():
    s = score_one(by_id[tid]["check"], resp)
    if s > 0:
        nonzero.append((tid, s))
print(f"worst-case zero: {len(worst_resp) - len(nonzero)}/{len(worst_resp)}")
for tid, s in nonzero:
    print(f"  LEAK worst {tid}={s}")
