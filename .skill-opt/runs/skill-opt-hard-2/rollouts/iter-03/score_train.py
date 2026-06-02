import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from checker import score_task

RUN = os.path.join(os.path.dirname(__file__), '..', '..')
tasks_data = json.loads(open(os.path.join(RUN, 'tasks/train/tasks.json')).read())
tasks = {t['id']: t for t in tasks_data}

R = {}
R["x017"] = "Rollout, Reflect, Edit budget, Held-out Gate, Memory"
R["x020"] = "The edit budget prevents catastrophic overwrites of working rules."
R["x021"] = "proposed-ratified, autonomous, user-suite, live"
R["x022"] = "6"
R["x023"] = """The slow-update mechanism is implemented in memory/rejected-edits.md and enforced during the Memory phase of the loop, with detailed policy specified in references/loop.md. The paper calls this mechanism 'Memory' -- specifically the slow-update component of rejected-edit memory, which prevents overfitting while maintaining plasticity. In practice: rejected-edits.md is an append-only log. Before every Edit phase, the Optimizer must read this log fully. A rejected edit cannot be re-proposed unless new evidence from at least 3 subsequent rollouts/minibatches shows the failure pattern it was meant to fix. Established rules require accumulated evidence across multiple minibatches to be overturned -- one bad minibatch is never enough."""
R["x024"] = """The paper defines the Held-out Gate as: 'Candidate skill kept only if it improves held-out selection performance. Never gate on train.' In skill-opt it is implemented by running ROLLOUT(candidate) over tasks/holdout/ using fresh subagents, then scripts/ledger.py gate computes accept/reject via deterministic arithmetic on ledger.csv (candidate_mean > best_so_far + gate_margin). The gate decision itself is never made by an LLM. For holdout eval scoring by feedback_source mode: user-suite uses programmatic scoring as primary (strongest signal), proposed-ratified uses programmatic checker if derivable from rubric otherwise LLM-judge, autonomous uses LLM-judge (programmatic where derivable), live uses direct user scoring (pass/fail or 0-5)."""

for tid in ["x017","x020","x021","x022","x023","x024"]:
    s = score_task(tasks[tid], R[tid])
    print(f"  {tid}: {s:.3f}")

scores = [score_task(tasks[tid], R[tid]) for tid in ["x017","x020","x021","x022","x023","x024"]]
print(f"\ntrain mean: {sum(scores)/len(scores):.6f}")
