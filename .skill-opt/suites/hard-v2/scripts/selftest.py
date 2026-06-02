"""Self-test for hard-v2 checker with gold, junk, and partial responses."""
import json
import sys
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_DIR / "scripts"))
from checker import score_one

SUITE = json.loads((SUITE_DIR / "suite.json").read_text())
by_id = {t["id"]: t for t in SUITE["tasks"]}

# Gold responses — these should score >= 0.85
gold = {
    "x000": "print('accept' if 0.82 > 0.79 + 0.02 else 'reject')",
    "x001": "print('accept' if 0.81 > 0.79 + 0.02 else 'reject')",
    "x002": """
edits = [{'added':45,'removed':20},{'added':30,'removed':0},{'added':10,'removed':15}]
ops = len(edits)
added = sum(e['added'] for e in edits)
removed = sum(e['removed'] for e in edits)
net = abs(added - removed)
print(f'ops: {"PASS" if ops <= 3 else "FAIL"}')
print(f'words: {"PASS" if net <= 80 else "FAIL"}')
""",
    "x003": """
edits = [{'added':60,'removed':5},{'added':40,'removed':0},{'added':25,'removed':10}]
added = sum(e['added'] for e in edits)
removed = sum(e['removed'] for e in edits)
net = abs(added - removed)
print(f'{net}')
print('FAIL' if net > 80 else 'PASS')
""",
    "x004": "python ledger.py record --run ./fixtures/run-alpha --iter 3 --version c3 --split holdout --scores 0.8,1.0,0.6,0.9,1.0,0.7",
    "x005": "python ledger.py best --run ./fixtures/run-alpha",
    "x006": "print(15 * 4 / 18)",
    "x007": """
history = ['accept','reject','reject','accept','reject','reject','reject']
counter = 0
patience = 3
for i, decision in enumerate(history, 1):
    if decision == 'accept':
        counter = 0
    else:
        counter += 1
    if counter >= patience:
        print(i)
        break
""",
    "x008": """
import math
holdout = round(35 * 0.4)
train = 35 - holdout
print(f'holdout: {holdout}, train: {train}')
""",
    "x009": """
import csv
from io import StringIO
data = open('./run-delta/ledger.csv').read()
reader = csv.DictReader(StringIO(data))
gates = [r for r in reader if r['kind'] == 'gate']
accepts = [r for r in gates if r['decision'] == 'accept']
rejects = [r for r in gates if r['decision'] == 'reject']
print(f'gates: {len(gates)}')
print(f'accepts: {len(accepts)}')
print(f'rejects: {len(rejects)}')
""",
    "x010": '{"target_skill": "my-agent/SKILL.md", "feedback_source": "user-suite", "max_iterations": 20, "edit_budget": {"max_ops": 5, "max_words": 120}, "holdout_fraction": 0.35, "edit_references": false, "feedback_timing": "autonomous", "output_mode": "save-as-new", "early_stop_patience": 3, "minibatch_size": 6, "gate_margin": 0.0, "parallelism": "serial", "edit_panel": 1, "validation_depth": "self-contained"}',
    "x011": '[{"op": "replace", "location": "introduction paragraph", "content": "Configure according to the project requirements", "rationale": "Replace generic default advice with specific guidance"}, {"op": "add", "location": "after introduction section", "content": "Always validate inputs before processing.", "rationale": "Add input validation rule for robustness"}]',
    "x012": '{"skill": "data-parser", "source": "proposed-ratified", "holdout_fraction": 0.3, "total": 15, "tasks": [{"id": "t000", "group": "format", "prompt": "Parse this CSV with headers", "check": {"type": "contains_all_lower", "patterns": ["header", "row"]}}, {"id": "t001", "group": "edge", "prompt": "Handle empty input", "check": {"type": "contains_all_lower", "patterns": ["empty", "error"]}}, {"id": "t002", "group": "format", "prompt": "Parse JSON with nested arrays", "check": {"type": "contains_all_lower", "patterns": ["array", "nested"]}}]}',
    "x013": '{"iter": 5, "decision": "reject", "delta": -0.04, "edit_ops": [{"op": "replace", "summary": "Changed intro wording"}, {"op": "add", "summary": "Added example section"}], "reason": "held-out score fell from 0.82 to 0.78", "evidence_needed": "at least 3 minibatches showing the intro confusion pattern"}',
    "x014": '{"best_version": "c1", "best_score": 0.72}',
    "x015": "Requires candidate to beat the current best score by more than the margin.",
    "x016": "Each rollout subagent receives only the skill text and the task prompt.",
    "x017": "rollout, reflect, edit, gate, memory",
    "x018": "iter, kind, version, split, mean_score, n, decision",
    "x019": "Otherwise best() returns None and the first candidate is accepted unconditionally (fail-open).",
    "x020": "catastrophic overwrites of rules that work.",
    "x021": "proposed-ratified, autonomous, user-suite, live",
    "x022": "6",
    "x023": "The slow-update mechanism is implemented via memory/rejected-edits.md. The SkillOpt paper calls this 'memory' — it tracks rejected edits and maintains plasticity through slow updates. The threshold for re-proposing is at least 3 subsequent rollouts showing the failure pattern. Rubrics.md notes programmatic checkers are deterministic, trustworthy, and serve as ground truth for judge calibration — they have no judge drift unlike LLM judges.",
    "x024": "The paper defines Held-out Gate as 'candidate skill kept only if it improves held-out selection performance — never gate on train.' It's implemented via scripts/ledger.py gate doing deterministic arithmetic on ledger.csv. The user-suite feedback source provides the strongest signal because it uses programmatic checkers with gold answers. At finalize, Spearman rho (ρ) is computed with threshold 0.7 to validate the judge via calibration.",
    "x025": "Rubrics.md says tasks should aim for baseline accuracy 40-60% so there's headroom, covering the spectrum from easy (baseline should pass) to hard. They must exercise identified failure modes. From the SKILL.md Loop: during Reflect, the minibatch is split into SUCCESS and FAILURE sets, reflected on separately. If all tasks succeed, the failure set is empty and there's no signal for improvement.",
    "x026": "With edit_panel=3, the Optimizer proposes 3 candidates (candidate-01, candidate-02, candidate-03). Gate runs holdout rollouts for all K candidates in parallel (up to 4 concurrent subagents). Each subagent writes to a unique leaf path — no collisions. The gate keeps the candidate with the highest holdout mean, but only if it beats best_so_far by strictly more than 0.05 (the gate_margin). Remaining candidates are rejected and logged to memory.",
    "x027": "Based on run-alpha's ledger: (1) Current best is c1 with score 0.750000. (2) Two non-improving rounds since last accept: iter 2 rejected, iter 3 rejected. (3) Yes, the next non-improving round (iter 4) will trigger early stop since patience=3 and counter will hit 3.",
    "x028": "The resume protocol detects that a candidate exists at candidates/iter-02/ but no holdout eval rows exist for iter 2 in ledger.csv. Per step 3: 'If a candidate exists but no holdout rollouts: re-run gating.' The next action is to dispatch holdout rollouts for c2, then call ledger.py record --version c2 --split holdout, then ledger.py gate --iter 2 --candidate c2.",
    "x029": "Yes, the run should stop. The holdout has been at 1.000000 for 3 consecutive rejected rounds (iters 2, 3, 4). With early_stop_patience=3, the counter has reached 3. The holdout is saturated — ties at 1.0 are rejected under the strict gate, so no candidate can ever improve.",
    "x030": "The arithmetic: candidate=0.670, best_so_far=0.625, margin=0.05. Check: 0.670 > 0.625 + 0.05 = 0.675? Answer: 0.670 > 0.675 is FALSE. So the candidate is REJECTED — it does not beat the best by strictly more than the margin.",
    "x031": "The slow-update policy requires evidence from at least 3 subsequent rollouts. The iter-02 edit was rejected at iter 2. Subsequent rollouts are iter 3 (current). That's only 1 rollout since rejection. Need 2 more (iters 4 and 5) showing the failure pattern before re-proposing at iter 5 earliest.",
    "x032": "print(2 * 10)",
    "x033": "Yes, these are consistent — both describe the same strict > comparison. The exact operator is > (strictly greater than), NOT >=. This means a tie (candidate equals best_so_far + margin) is rejected. The strict inequality ensures only genuine improvements are accepted.",
    "x034": "The word 'consecutive' is critical. The counter resets to 0 on any accept. So: iter 1 reject → counter=1, iter 2 accept → counter=0 (reset), iter 3 reject → counter=1. After iter 3, patience counter is 1.",
    "x035": "These do not conflict — they describe the same thing. 'Current skill text' and 'task prompt' are the two inputs. When edit_references=true, the 'skill text' includes the full packet (SKILL.md + references/ bundled together). The subagent still receives exactly two things: the entire skill bundle as one text, and the task.",
    "x036": "No contradiction. record is called to write kind=eval rows (scoring data for train or holdout). gate is called ONLY for the accept/reject decision (writes kind=gate row). record handles eval scoring; gate handles decisions. The note warns against calling record FOR A GATE DECISION — that would create a spurious eval row.",
    "x037": "With margin=0.0, the comparison is: candidate > best_so_far + 0.0, which simplifies to candidate > best_so_far. When candidate EQUALS best_so_far, the comparison is strictly greater than (>) not >=. So a tie is rejected. Any improvement, no matter how small, suffices — but exact equality does not.",
    "x038": "They are different naming schemes. Ledger labels use cN (c1, c2, c3...) — one per iteration attempt. Skill file names use vK (v1, v2, v3...) — one per ACCEPTANCE. So c1 accepted → v1, c2 rejected (no file), c3 accepted → v2. The mapping is: vK = the Kth accepted candidate, named independently of its ledger label cN.",
    "x039": """
def decide(cand_score, best_score, margin):
    accept = cand_score is not None and (best_score is None or cand_score > best_score + margin)
    return 'accept' if accept else 'reject'

print(decide(0.85, None, 0.0))
print(decide(None, 0.7, 0.0))
""",
    "x040": """
import csv
from io import StringIO

data = '''iter,kind,version,split,mean_score,n,decision
0,eval,v0,holdout,0.600000,8,
1,eval,c1,holdout,0.700000,8,
1,gate,c1,holdout,0.700000,,accept
2,eval,c2,holdout,0.650000,8,
2,gate,c2,holdout,0.650000,,reject'''

rows = list(csv.DictReader(StringIO(data)))
accepted = ['v0'] + [r['version'] for r in rows if r['kind'] == 'gate' and r['decision'] == 'accept']
best_v, best_s = None, -1
for v in accepted:
    for r in rows:
        if r['kind'] == 'eval' and r['version'] == v and r['split'] == 'holdout':
            s = float(r['mean_score'])
            if s > best_s:
                best_v, best_s = v, s
print(f'{best_v} {best_s}')
""",
    "x041": '{"iter": 2, "kind": "eval", "version": "c2", "split": "holdout", "mean_score": 0.834, "n": 12, "decision": ""}',
    "x042": '{"rho": 0.63, "n": 18, "threshold": 0.70, "status": "FAIL"}',
    "x043": "Edit budget limits changes per iteration like a learning rate prevents overly large weight updates, to prevent catastrophic overwrites of working rules.",
    "x044": "Append the rejected edit's ops, failure reason, and iteration to memory/rejected-edits.md.",
    "x045": "In live mode, sequential sampling without replacement doesn't apply because there's no pre-built suite. Tasks arrive as real work — the rolling window determines which logged tasks form the current holdout, with earlier tasks becoming train. Tasks are processed one at a time as they arrive.",
    "x046": "python ledger.py gate --run ./fixtures/run-gamma --iter 2 --candidate c2 --margin 0.0",
    "x047": "Even if rejected due to holdout saturation (a tie), the edit is still recorded in rejected-edits.md and still known-bad. The slow-update policy doesn't distinguish WHY an edit was rejected — it requires 3 subsequent minibatches showing the failure pattern before re-proposing. The edit cannot be retried immediately regardless of the rejection reason.",
    "x048": """
ops = [{'op':'replace','added':25,'removed':10},{'op':'add','added':35,'removed':0},{'op':'replace','added':20,'removed':30}]
num_ops = len(ops)
words_added = sum(o['added'] for o in ops)
words_removed = sum(o['removed'] for o in ops)
net_words = abs(words_added - words_removed)
ops_pass = num_ops <= 3
words_pass = net_words <= 80
print(f'num_ops: {num_ops}')
print(f'words_added: {words_added}')
print(f'words_removed: {words_removed}')
print(f'net_words: {net_words}')
print(f'ops_pass: {str(ops_pass).lower()}')
print(f'words_pass: {str(words_pass).lower()}')
""",
    "x049": "No, the iter-02 rejected edit cannot be re-proposed yet at iter 4. The rejection was at iter 2, and 'subsequent' means AFTER the rejection. Only iter 3's train eval is subsequent — that's 1 minibatch. Need at least 3 subsequent rollouts showing the failure pattern. Must wait until iters 3, 4, 5 all show it (earliest re-proposal at iter 5 or 6).",
    "x050": "Calibration fails: rho=0.55 is below the 0.70 threshold. Actions: (1) inspect tasks where judge and programmatic scores diverge most, (2) revise the judge rubric to be more concrete, (3) consider switching to user-suite mode with user-provided gold answers. Since autonomous mode has no user validation of the rubric and higher risk of judge drift, the optimization gains cannot be trusted without passing calibration.",
    "x051": """
import csv
from io import StringIO

data = open('./run-alpha/ledger.csv').read()
rows = list(csv.DictReader(StringIO(data)))

accepted = ['v0'] + [r['version'] for r in rows if r['kind'] == 'gate' and r['decision'] == 'accept']
best_score = -1
best_version = None
for v in accepted:
    for r in rows:
        if r['kind'] == 'eval' and r['version'] == v and r['split'] == 'holdout':
            s = float(r['mean_score'])
            if s > best_score:
                best_score = s
                best_version = v

candidate_mean = 0.76
margin = 0.0
if candidate_mean > best_score + margin:
    print(f'accept (0.76 > {best_score} + {margin} = {best_score + margin})')
else:
    print(f'reject (0.76 not > {best_score} + {margin} = {best_score + margin})')
"""
}

# Junk responses
junk = {tid: "I don't know." for tid in gold}

# Partial responses (should score 0.3-0.7)
partial = {
    "x000": "accept",  # Right answer but not executable Python
    "x010": '{"target_skill": "my-agent/SKILL.md", "feedback_source": "user-suite"}',  # Missing most keys
    "x027": "The best version is c1. There have been some rejections.",  # Partial info
    "x034": "The counter is about consecutive rejections. After iter 3 it would be 1.",  # Missing 'resets'
}


def run_tests():
    print("=" * 60)
    print("HARD-V2 SUITE SELFTEST")
    print("=" * 60)

    # Gold
    print(f"\n--- Gold responses (target: >= 0.80) ---")
    gold_scores = []
    gold_failures = []
    for tid in sorted(gold):
        if tid not in by_id:
            print(f"  SKIP {tid} (not in suite)")
            continue
        task = by_id[tid]
        s = score_one(task["check"], gold[tid])
        gold_scores.append((tid, s))
        if s < 0.80:
            gold_failures.append((tid, s))

    gold_mean = sum(s for _, s in gold_scores) / len(gold_scores)
    print(f"  Gold mean: {gold_mean:.3f}")
    print(f"  Gold pass (>=0.80): {len(gold_scores) - len(gold_failures)}/{len(gold_scores)}")
    if gold_failures:
        for tid, s in sorted(gold_failures, key=lambda x: x[1]):
            print(f"    FAIL {tid}: {s:.3f}")

    # Junk
    print(f"\n--- Junk responses (target: <= 0.15) ---")
    junk_scores = []
    junk_leaks = []
    for tid in sorted(junk):
        if tid not in by_id:
            continue
        task = by_id[tid]
        s = score_one(task["check"], junk[tid])
        junk_scores.append((tid, s))
        if s > 0.15:
            junk_leaks.append((tid, s))

    junk_mean = sum(s for _, s in junk_scores) / len(junk_scores)
    print(f"  Junk mean: {junk_mean:.3f}")
    print(f"  Junk clean (<=0.15): {len(junk_scores) - len(junk_leaks)}/{len(junk_scores)}")
    if junk_leaks:
        for tid, s in sorted(junk_leaks, key=lambda x: -x[1]):
            print(f"    LEAK {tid}: {s:.3f}")

    # Partial
    print(f"\n--- Partial responses ---")
    for tid in sorted(partial):
        if tid not in by_id:
            continue
        task = by_id[tid]
        s = score_one(task["check"], partial[tid])
        status = "OK" if 0.2 <= s <= 0.8 else "MISCAL"
        print(f"  {tid}: {s:.3f} [{status}]")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"  Gold mean:  {gold_mean:.3f} (target >= 0.85)")
    print(f"  Gold fails: {len(gold_failures)}")
    print(f"  Junk mean:  {junk_mean:.3f} (target <= 0.10)")
    print(f"  Junk leaks: {len(junk_leaks)}")

    # Per-group gold breakdown
    print(f"\n  Per-group gold mean:")
    from collections import defaultdict
    by_group = defaultdict(list)
    for tid, s in gold_scores:
        g = by_id[tid]["group"]
        by_group[g].append(s)
    for g in sorted(by_group):
        gm = sum(by_group[g]) / len(by_group[g])
        print(f"    {g:10s}: {gm:.3f} ({len(by_group[g])} tasks)")

    print(f"{'=' * 60}")
    return len(gold_failures) <= 5 and len(junk_leaks) <= 3


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
