import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from checker import score_task

RUN = os.path.join(os.path.dirname(__file__), '..', '..')
tasks_data = json.loads(open(os.path.join(RUN, 'tasks/holdout/tasks.json')).read())
tasks = {t['id']: t for t in tasks_data}

# Actual subagent responses (verbatim from fresh subagent dispatch)
responses = {}

responses["x003"] = """```python
max_ops = 3
max_words = 80
edits = [{"added": 60, "removed": 5}, {"added": 40, "removed": 0}, {"added": 25, "removed": 10}]

total_added = sum(e["added"] for e in edits)
total_removed = sum(e["removed"] for e in edits)
net_words = abs(total_added - total_removed)

num_ops = len(edits)

ops_ok = num_ops <= max_ops
words_ok = net_words <= max_words

passed = ops_ok and words_ok
print(f"Net word count: {net_words}")
print("PASS" if passed else "FAIL")
```"""

responses["x007"] = """```python
gate_history = ['accept', 'reject', 'reject', 'accept', 'reject', 'reject', 'reject']
early_stop_patience = 3

no_improvement_counter = 0

for i, decision in enumerate(gate_history, start=1):
    if decision == 'accept':
        no_improvement_counter = 0
    else:
        no_improvement_counter += 1

    if no_improvement_counter >= early_stop_patience:
        print(f"Early stop fires at iteration {i}")
        break
```"""

responses["x010"] = """{
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

responses["x011"] = """```json
[
  {
    "op": "replace",
    "location": "sentence 'Use default settings'",
    "content": "Configure according to the project requirements",
    "rationale": "Replace generic default-settings instruction with explicit guidance to configure per project requirements"
  },
  {
    "op": "add",
    "location": "after the introduction section",
    "content": "Always validate inputs before processing.",
    "rationale": "Add input validation guidance as a new paragraph following the introduction"
  }
]
```"""

responses["x015"] = "Sets the minimum held-out score improvement required to accept a candidate edit."

responses["x018"] = "iter, kind, version, split, mean_score, n, decision"

responses["x019"] = "Without the v0 baseline, best() returns None, so the first candidate is accepted unconditionally -- a fail-open gate."

responses["x028"] = """The resume protocol should re-run gating for candidate c2. Specifically: first run holdout rollouts for the candidate at candidates/iter-02/candidate.md over the holdout tasks, then score each rollout and call ledger.py record --version c2 --split holdout to record the holdout evaluation, then call ledger.py gate --candidate c2 --iter 2 to get the deterministic accept/reject decision."""

responses["x029"] = """Yes, the run should stop. The patience counter value is 3. Iterations 2, 3, and 4 were all rejected as ties (holdout saturated at 1.000000 and the strict gate rejects ties since candidate cannot improve beyond perfect score). Three consecutive non-improving gated rounds equals early_stop_patience=3, so early stop fires."""

responses["x036"] = """There is no contradiction. The record command and gate command serve different purposes and write different row types. record is called during SCORE phase to write kind=eval rows for train or holdout evaluation scores. gate is called during GATE phase to write kind=gate decision rows (accept/reject). The key distinction: record only writes eval rows and cannot set the decision field; gate writes its own row with the decision. So 'ledger.py record --split train' records training scores as eval rows, while 'ledger.py gate' computes and writes the gate decision row separately."""

responses["x038"] = """No, v(K+1) is not the same as the cN label. They are different and named independently. The ledger labels (cN) follow iteration numbering: c1 for iteration 1's candidate, c2 for iteration 2's, etc. The on-disk skill file labels (vK) follow sequential acceptance count: v0 is baseline, v1 is after the first acceptance, v2 after the second, etc. For example, if c1 is accepted and c2 is rejected and c3 is accepted: c1 maps to v1, c3 maps to v2. The version label c2 never gets a vK file because it was rejected."""

responses["x039"] = """```python
def decide(cand_score, best_score, margin):
    if best_score is None:
        print("accept")
        return
    if cand_score is None:
        print("reject")
        return
    if cand_score > best_score + margin:
        print("accept")
    else:
        print("reject")

decide(0.85, None, 0.0)
decide(None, 0.7, 0.0)
```"""

responses["x045"] = """No, "sequential sampling without replacement within each epoch" is not applicable in live mode. The Minibatch Sampling strategy described in loop.md assumes a fixed, pre-built pool of tasks in tasks/train/. Sequential sampling without replacement within each epoch means you shuffle the finite train set, draw minibatch_size tasks one by one until exhausted, then reshuffle and start a new epoch. In live mode, as described in feedback-sources.md, there is no pre-built suite. Tasks are the real tasks the user performs with the skill during a work session, and each real task is logged as it arrives. The train pool grows over time. What replaces it is arrival-order accumulation and a rolling window for the held-out split: the most recent holdout_fraction of logged tasks form the current holdout, and earlier tasks become train."""

responses["x048"] = """```python
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

responses["x050"] = """No, calibration does not pass. The threshold from rubrics.md is rho >= 0.7, and rho=0.55 is below this threshold. This is particularly concerning because autonomous mode from feedback-sources.md has higher risk of judge drift since there is no user validation of the rubric. Specific actions from rubrics.md: Inspect tasks where judge and programmatic scores diverge most, revise the judge rubric to be more concrete, consider switching to user-suite mode with user-provided gold answers. The optimization gains should not be trusted. Rubrics.md explicitly states: 'Do not trust the optimization run's gains without passing calibration.'"""

# Score all
results = {}
for tid in sorted(responses.keys()):
    s = score_task(tasks[tid], responses[tid])
    results[tid] = s
    print(f"  {tid}: {s:.3f}")

scores = list(results.values())
mean = sum(scores) / len(scores)
print(f"\nmean: {mean:.6f}")
print(f"passed: {sum(1 for s in scores if s >= 1.0)}/{len(scores)}")
print(f"partial: {sum(1 for s in scores if 0 < s < 1.0)}/{len(scores)}")
print(f"failed: {sum(1 for s in scores if s == 0.0)}/{len(scores)}")

# Save results
json.dump({"scores": results, "mean": mean}, 
          open(os.path.join(RUN, 'rollouts/iter-00/holdout_scores.json'), 'w'), indent=2)
# Save responses
json.dump(responses, 
          open(os.path.join(RUN, 'rollouts/iter-00/holdout_responses.json'), 'w'), indent=2)
