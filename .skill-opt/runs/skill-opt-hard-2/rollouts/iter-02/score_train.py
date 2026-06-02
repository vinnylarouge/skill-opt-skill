import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from checker import score_task

RUN = os.path.join(os.path.dirname(__file__), '..', '..')
tasks_data = json.loads(open(os.path.join(RUN, 'tasks/train/tasks.json')).read())
tasks = {t['id']: t for t in tasks_data}

R = {}
R["x008"] = """```python
holdout_fraction = 0.4
total_tasks = 35
holdout = round(total_tasks * holdout_fraction)
train = total_tasks - holdout
print(f'holdout: {holdout}, train: {train}')
```"""

R["x009"] = """```python
import csv
with open('./fixtures/run-delta/ledger.csv', newline='') as f:
    reader = csv.DictReader(f)
    rows = [r for r in reader if r['kind'] == 'gate']
accepts = sum(1 for r in rows if r['decision'] == 'accept')
rejects = sum(1 for r in rows if r['decision'] == 'reject')
print(f'gates: {len(rows)}')
print(f'accepts: {accepts}')
print(f'rejects: {rejects}')
```"""

R["x012"] = """{
  "skill": "data-parser",
  "source": "proposed-ratified",
  "total": 15,
  "holdout_fraction": 0.3,
  "tasks": [
    {"id": "task-000", "group": "csv-parsing", "split": "train", "checker": "programmatic", "prompt": "Parse CSV row", "check": "json_field_presence"},
    {"id": "task-001", "group": "csv-parsing", "split": "train", "checker": "programmatic", "prompt": "Parse malformed CSV", "check": "json_field_presence"},
    {"id": "task-002", "group": "json-parsing", "split": "train", "checker": "programmatic", "prompt": "Extract numeric values", "check": "output == [1,2,3,4,5]"}
  ]
}"""

R["x013"] = """{
  "iter": 5,
  "decision": "reject",
  "delta": -0.03,
  "edit_ops": ["replace: updated procedure section", "add: new edge-case guard", "del: removed redundant validation"],
  "reason": "held-out score fell from 0.71 to 0.68",
  "evidence_needed": "at least 3 minibatches showing this failure pattern"
}"""

R["x014"] = '{"best_version": "c1", "best_score": 0.72}'

R["x016"] = "Each rollout subagent receives only the current skill text and the task prompt, with no other context passed."

for tid in ["x008","x009","x012","x013","x014","x016"]:
    s = score_task(tasks[tid], R[tid])
    print(f"  {tid}: {s:.3f}")

scores = [score_task(tasks[tid], R[tid]) for tid in ["x008","x009","x012","x013","x014","x016"]]
mean = sum(scores)/len(scores)
print(f"\ntrain mean: {mean:.6f}")
