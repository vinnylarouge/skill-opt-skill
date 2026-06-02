import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from checker import score_task

RUN = os.path.join(os.path.dirname(__file__), '..', '..')
tasks_data = json.loads(open(os.path.join(RUN, 'tasks/holdout/tasks.json')).read())
tasks = {t['id']: t for t in tasks_data}

R = {}

R["x003"] = """```python
max_ops = 3
max_words = 80
edits = [{"added": 60, "removed": 5}, {"added": 40, "removed": 0}, {"added": 25, "removed": 10}]
total_added = sum(e["added"] for e in edits)
total_removed = sum(e["removed"] for e in edits)
net_words = abs(total_added - total_removed)
result = "PASS" if net_words <= max_words else "FAIL"
print(f"{net_words} {result}")
```"""

R["x007"] = """```python
gate_history = ['accept','reject','reject','accept','reject','reject','reject']
early_stop_patience = 3
no_improvement = 0
for i, decision in enumerate(gate_history, start=1):
    if decision == 'accept':
        no_improvement = 0
    else:
        no_improvement += 1
    if no_improvement >= early_stop_patience:
        print(f"Early stop fires at iteration {i}")
        break
```"""

R["x010"] = """{
  "target_skill": "my-agent/SKILL.md",
  "edit_references": false,
  "feedback_source": "user-suite",
  "feedback_timing": "autonomous",
  "output_mode": "save-as-new",
  "max_iterations": 20,
  "early_stop_patience": 3,
  "edit_budget": {"max_ops": 5, "max_words": 120},
  "minibatch_size": 6,
  "holdout_fraction": 0.35,
  "checkpoint_every": 1,
  "parallelism": "serial",
  "edit_panel": 1,
  "gate_margin": 0.0,
  "validation_depth": "self-contained"
}"""

R["x011"] = """```json
[
  {
    "op": "replace",
    "location": "sentence 'Use default settings'",
    "content": "Configure according to the project requirements",
    "rationale": "The original phrasing was too vague"
  },
  {
    "op": "add",
    "location": "after the introduction section",
    "content": "Always validate inputs before processing.",
    "rationale": "Adding input validation guidance"
  }
]
```"""

R["x015"] = "Sets the minimum held-out score improvement required to accept a candidate."

R["x018"] = "iter, kind, version, split, mean_score, n, decision"

R["x019"] = "Without the v0 baseline, best() returns None, so the first candidate is accepted unconditionally -- a fail-open gate that bypasses held-out validation."

R["x028"] = """The resume protocol should re-run gating for candidate c2. Run holdout rollouts for the candidate at candidates/iter-02/candidate.md over holdout tasks, then record with ledger.py record --run <path> --iter 2 --version c2 --split holdout --scores <scores>, then call ledger.py gate --run <path> --iter 2 --candidate c2 --margin 0.0."""

R["x029"] = """Yes, the run should stop. The patience counter value is 3. Iterations 2, 3, and 4 were all rejected as ties (holdout saturated at 1.000000 and the strict gate rejects ties since candidate cannot improve). Three consecutive non-improving gated rounds equals early_stop_patience=3."""

R["x036"] = """There is no contradiction. record writes kind=eval rows for train or holdout evaluation scores. gate writes kind=gate decision rows. record is called during SCORE phase for train scores and during GATE phase for holdout eval scores. gate is called once per iteration after the holdout record call, computes the decision, and writes its own kind=gate row. You do not call record for the decision because gate already did that internally."""

R["x038"] = """No, v(K+1) is not the same as cN. They are different and named independently. cN follows iteration numbering: c1 for iteration 1, c2 for iteration 2, etc. v(K+1) follows sequential acceptance count: v0 is baseline, v1 is after the first acceptance, v2 after the second. If c1 is accepted and c2 is rejected and c3 is accepted: c1 maps to v1, c3 maps to v2."""

R["x039"] = """```python
def decide(cand_score, best_score, margin):
    if cand_score is None:
        return "reject"
    if best_score is None:
        return "accept"
    if cand_score > best_score + margin:
        return "accept"
    return "reject"

print(decide(0.85, None, 0.0))
print(decide(None, 0.7, 0.0))
```"""

R["x045"] = """No, "sequential sampling without replacement within each epoch" is not applicable in live mode. The Minibatch Sampling strategy assumes a fixed, pre-built pool of tasks. Sequential sampling without replacement within each epoch means you shuffle the finite train set, draw minibatch_size tasks until exhausted, then reshuffle. In live mode there is no pre-built suite. Tasks are real tasks logged as they arrive one at a time. What replaces it is a rolling window: the most recent holdout_fraction of logged tasks form the holdout, earlier tasks become train."""

R["x048"] = """```python
ops = [
    {'op': 'replace', 'added': 25, 'removed': 10},
    {'op': 'add', 'added': 35, 'removed': 0},
    {'op': 'replace', 'added': 20, 'removed': 30},
]
max_ops = 3
max_words = 80
num_ops = len(ops)
words_added = sum(o['added'] for o in ops)
words_removed = sum(o['removed'] for o in ops)
net_words = abs(words_added - words_removed)
ops_pass = num_ops <= max_ops
words_pass = net_words <= max_words
print(f"num_ops: {num_ops}")
print(f"words_added: {words_added}")
print(f"words_removed: {words_removed}")
print(f"net_words: {net_words}")
print(f"ops_pass: {ops_pass}")
print(f"words_pass: {words_pass}")
```"""

R["x050"] = """No, calibration does not pass. The threshold from rubrics.md is rho >= 0.7, and rho=0.55 is below this threshold. This is particularly concerning because autonomous mode from feedback-sources.md has higher risk of judge drift since there is no user validation of the rubric. Specific actions: inspect tasks where judge and programmatic scores diverge most, revise the judge rubric to be more concrete, consider switching to user-suite mode with user-provided gold answers. The optimization gains should not be trusted. Rubrics.md explicitly states: 'Do not trust the optimization run's gains without passing calibration.'"""

scores = {}
for tid in sorted(R.keys()):
    s = score_task(tasks[tid], R[tid])
    scores[tid] = s
    print(f"  {tid}: {s:.3f}")

vals = list(scores.values())
mean = sum(vals)/len(vals)
print(f"\nc1 holdout mean: {mean:.6f}")
print(f"passed: {sum(1 for s in vals if s >= 1.0)}/{len(vals)}")
print(f"partial: {sum(1 for s in vals if 0 < s < 1.0)}/{len(vals)}")
print(f"failed: {sum(1 for s in vals if s == 0.0)}/{len(vals)}")

json.dump({"scores": scores, "mean": mean}, 
          open(os.path.join(RUN, 'rollouts/iter-01/holdout_c1_scores.json'), 'w'), indent=2)
json.dump(R, open(os.path.join(RUN, 'rollouts/iter-01/holdout_c1_responses.json'), 'w'), indent=2)
