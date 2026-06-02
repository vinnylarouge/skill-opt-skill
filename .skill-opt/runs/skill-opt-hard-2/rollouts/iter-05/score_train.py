import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from checker import score_task

RUN = os.path.join(os.path.dirname(__file__), '..', '..')
tasks_data = json.loads(open(os.path.join(RUN, 'tasks/train/tasks.json')).read())
tasks = {t['id']: t for t in tasks_data}

R = {}
R["x033"] = """The two descriptions are not fully consistent. The questionnaire table says: 'candidate must beat the best by at least this margin'. Loop.md Defaults Table says: 'candidate must beat best_so_far by strictly more than this margin'. 'at least' implies >= while 'strictly more than' implies >. The Gate Margin section clarifies with the formula: accept = candidate_mean > best_so_far + gate_margin (strict; a tie is rejected), confirming the strict/exclusive interpretation."""

R["x034"] = """Yes, 'consecutive' is an important distinction. The questionnaire says 'stop after K gated rounds with no improvement'. Loop.md says 'stop after K consecutive gated rounds with no improvement'. Without 'consecutive', a single intervening improvement would not reset the counter. Example: reject, reject, accept, reject, reject, reject. Without consecutive, you count all rejections (stopping at 3). With consecutive, the accept resets the counter to 0, so only the final 3 consecutive rejections trigger early stop. Without the consecutive requirement, the optimizer would stop prematurely."""

R["x035"] = """They express the same constraint but with different framing. The fidelity map says 'receives only {current skill text, task}'. The Disciplines section says 'each rollout subagent receives exactly two inputs: the current skill text and the task prompt. Nothing else is passed to the subagent.' The Disciplines version is more explicit: (1) says 'exactly two inputs' making the count explicit, (2) names the second input as 'the task prompt' rather than just 'task', (3) adds 'Nothing else is passed to the subagent' as an explicit exclusion clause. Substantively they describe the same constraint."""

R["x037"] = """There is no difference. With gate_margin=0.0, the formula is candidate_mean > best_so_far + 0.0, which simplifies to candidate_mean > best_so_far. The strict inequality (> rather than >=) means a tie is rejected. The gate_margin only becomes meaningful when set above 0.0, requiring the candidate to exceed best_so_far by more than the margin."""

R["x040"] = """```python
import csv
from io import StringIO

ledger_csv = 'iter,kind,version,split,mean_score,n,decision\\n0,eval,v0,holdout,0.65,10,\\n1,eval,c1,holdout,0.72,10,\\n1,gate,c1,holdout,0.72,,accept\\n2,eval,c2,holdout,0.68,10,\\n2,gate,c2,holdout,0.68,,accept'

reader = csv.DictReader(StringIO(ledger_csv))
rows = list(reader)

accepted_versions = {'v0'}
for row in rows:
    if row['kind'] == 'gate' and row['decision'] == 'accept':
        accepted_versions.add(row['version'])

best_version = None
best_score = float('-inf')
for row in rows:
    if row['kind'] == 'eval' and row['split'] == 'holdout' and row['version'] in accepted_versions:
        score = float(row['mean_score'])
        if score > best_score:
            best_score = score
            best_version = row['version']

print(f"Best version: {best_version}, Score: {best_score}")
```"""

R["x041"] = '{"iter": 2, "kind": "eval", "version": "c2", "split": "holdout", "mean_score": 0.85, "n": 10, "decision": ""}'

for tid in ["x033","x034","x035","x037","x040","x041"]:
    s = score_task(tasks[tid], R[tid])
    print(f"  {tid}: {s:.3f}")

scores = [score_task(tasks[tid], R[tid]) for tid in ["x033","x034","x035","x037","x040","x041"]]
print(f"\ntrain mean: {sum(scores)/len(scores):.6f}")
