import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from checker import score_task

RUN = os.path.join(os.path.dirname(__file__), '..', '..')
tasks_data = json.loads(open(os.path.join(RUN, 'tasks/train/tasks.json')).read())
tasks = {t['id']: t for t in tasks_data}

responses = {}

responses["x000"] = """```python
print('accept' if 0.82 > 0.79 + 0.02 else 'reject')
```"""

responses["x001"] = """```python
print('accept' if 0.81 > 0.79 + 0.02 else 'reject')
```"""

responses["x002"] = """```python
max_ops = 3
max_words = 80
edits = [{"added": 45, "removed": 20}, {"added": 30, "removed": 0}, {"added": 10, "removed": 15}]

ops_count = len(edits)
ops_pass = ops_count <= max_ops
print(f"ops: {'PASS' if ops_pass else 'FAIL'}")

words_added = sum(e["added"] for e in edits)
words_removed = sum(e["removed"] for e in edits)
net_words = abs(words_added - words_removed)
words_pass = net_words <= max_words
print(f"words: {'PASS' if words_pass else 'FAIL'}")
```"""

responses["x004"] = """```
scripts/ledger.py record --run-dir ./fixtures/run-alpha --version c3 --iter 3 --split holdout --scores 0.8 1.0 0.6 0.9 1.0 0.7
```"""

responses["x005"] = """```
scripts/ledger.py best --run-dir ./fixtures/run-alpha
```"""

responses["x006"] = """```python
total_train_tasks = 18
minibatch_size = 4
iterations = 15

total_tasks_consumed = iterations * minibatch_size
complete_epochs = total_tasks_consumed // total_train_tasks

print(float(complete_epochs))
```"""

for tid in ["x000", "x001", "x002", "x004", "x005", "x006"]:
    s = score_task(tasks[tid], responses[tid])
    print(f"  {tid}: {s:.3f}")

scores = [score_task(tasks[tid], responses[tid]) for tid in ["x000", "x001", "x002", "x004", "x005", "x006"]]
mean = sum(scores) / len(scores)
print(f"\ntrain mean: {mean:.6f}")

json.dump(responses, open(os.path.join(RUN, 'rollouts/iter-01/train_responses.json'), 'w'), indent=2)
