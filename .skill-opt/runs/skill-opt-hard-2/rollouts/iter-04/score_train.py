import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from checker import score_task

RUN = os.path.join(os.path.dirname(__file__), '..', '..')
tasks_data = json.loads(open(os.path.join(RUN, 'tasks/train/tasks.json')).read())
tasks = {t['id']: t for t in tasks_data}

R = {}
R["x025"] = """Rubrics.md says tasks should cover a spectrum from easy (baseline should pass) to hard (headroom exists), aiming for baseline accuracy of approximately 40-60% so the optimizer has room to improve. The Loop section's minibatch_size (default 6) controls how many train tasks are sampled per iteration for rollout and reflection. These interact because the minibatch_size determines how many scored trajectories the Reflect phase sees each iteration -- if baseline accuracy is 40-60%, a minibatch of 6 will typically yield 2-4 failures and 2-4 successes, giving the Reflect phase meaningful signal in both the SUCCESS and FAILURE buckets."""

R["x026"] = """With edit_panel=3, there are 3 candidates to gate. The gate phase runs holdout rollouts for all K candidates. So with edit_panel=3, there are 3 holdout rollout sets. With parallelism=4, up to 4 concurrent subagents run at once. gate_margin=0.05 only affects the accept/reject threshold, not the number of rollouts."""

R["x027"] = """The current best version is c1 (on-disk: v1) with holdout score 0.750. Three iterations have completed (iter 1, 2, and 3). The patience counter is 2: iter 1 c1 accepted (patience=0), iter 2 c2 rejected (patience=1), iter 3 c3 rejected as tie (patience=2). With early_stop_patience=3, the run continues."""

R["x030"] = """```json
[
  {"op": "replace", "location": "Review Checklist bullet 1", "content": "Verify all function parameters have type annotations", "rationale": "Rollout failures show agent skips type-checking"},
  {"op": "add", "location": "after Output Format", "content": "Always include severity level for each finding", "rationale": "Failed tasks lacked severity ratings"}
]
```"""

R["x031"] = """Yes, a tie is a correct rejection. The gate formula is: accept = candidate_mean > best_so_far + gate_margin. This is strict inequality. With gate_margin=0.0, the condition is candidate_mean > best_so_far. A tie (equal) does not satisfy strict greater-than, so the gate correctly rejects. The document states 'strict; a tie is rejected.'"""

R["x032"] = """Run-beta has edit_panel=2 and 10 holdout tasks. In the GATE phase, holdout rollouts run for all K candidates. With edit_panel=2: 2 candidates * 10 holdout tasks = 20 total fresh subagent rollout sessions dispatched. parallelism=4 controls concurrency but not the total count."""

for tid in ["x025","x026","x027","x030","x031","x032"]:
    s = score_task(tasks[tid], R[tid])
    print(f"  {tid}: {s:.3f}")

scores = [score_task(tasks[tid], R[tid]) for tid in ["x025","x026","x027","x030","x031","x032"]]
print(f"\ntrain mean: {sum(scores)/len(scores):.6f}")
