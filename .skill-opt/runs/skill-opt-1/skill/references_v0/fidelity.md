# Fidelity Map — SkillOpt Mechanism Correspondence

This table is the theoretical ground truth for `skill-opt`. Every SkillOpt mechanism
is mapped to the file or step that implements it here. Deviations are explicitly justified.

| SkillOpt Mechanism | Paper Definition | Implementation in skill-opt | File / Step | Deviation / Justification |
|---|---|---|---|---|
| **Rollout** | Target model executes tasks with current skill; records scored trajectories. | Fresh subagent receives only `{current skill text, task}` → writes `trajectory.md` + `score.json`. Scored rollout every iteration. | `rollouts/iter-NN/task-MM/trajectory.md`, `score.json` | Single-agent analogue: fresh subagent with only skill+task context is the closest approximation to a truly frozen target. Eliminates self-grading. |
| **Reflect** | Optimizer analyzes success and failure minibatches **separately** to find reusable procedures. | Minibatch split into SUCCESS set and FAILURE set; Optimizer hat reflects on each separately before proposing any edit. Also reads `memory/rejected-edits.md`. | Reflect phase in the loop; `memory/rejected-edits.md` | Paper is explicit about separate reflection — this is enforced, not optional. |
| **Edit budget** | Bounded add/delete/replace ops; "an edit budget functions as a textual learning rate, preventing useful rules from being overwritten." | Each iteration caps at `edit_budget.max_ops` operations and `edit_budget.max_words` net words changed. The `edit.json` records ordered ops with rationale. | `candidates/iter-NN/edit.json`; enforced by the Edit phase | Default `{max_ops: 3, max_words: 80}`. Configurable. Prevents catastrophic overwrites. |
| **Held-out Gate** | Candidate skill kept only if it improves held-out selection performance. Never gate on train. | `ROLLOUT(candidate)` over `tasks/holdout/` (fresh subagents); `scripts/ledger.py gate` computes accept/reject from `ledger.csv` arithmetic. Accepted → `skill/v(K+1).md`; rejected → `memory/rejected-edits.md`. | `scripts/ledger.py gate`; `ledger.csv` | Gate decision is **deterministic arithmetic**, never an LLM opinion. Only trajectory scoring may use an LLM-judge. |
| **Memory** (rejected-edit memory + slow updates) | Tracks rejected edits; applies slow updates, preventing overfitting while maintaining plasticity. | `memory/rejected-edits.md` persists all rejected candidates with failure reasons. Optimizer **must** consult it before proposing edits. Established rules require accumulated evidence (multiple minibatches) to be overturned — one minibatch cannot rewrite everything. | `memory/rejected-edits.md`; Memory phase in loop | "Slow updates" enforced by discipline: the Optimizer hat is instructed not to re-propose a rejected edit without new evidence from multiple subsequent rollouts. |

## Coverage Verification

All five mechanisms are present: rollout, reflect, edit budget, held-out gate, memory.

The `scripts/ledger.py gate` subcommand implements the gate decision deterministically (via the internal `decide()` function).
The frozen target is implemented via the fresh-subagent discipline described in SKILL.md.

## References

- Microsoft SkillOpt paper: https://microsoft.github.io/SkillOpt/
- `scripts/ledger.py` — gate arithmetic implementation
- `references/loop.md` — phase mechanics and slow-update policy detail
