# Loop Mechanics — Detailed Reference

This document covers the mechanics that SKILL.md summarizes: phase details, defaults,
edit-budget enforcement, gate margin, memory/slow-update policy, parallelism, and edit_panel.

---

## Defaults Table

| Field | Default | Range / Notes |
|---|---|---|
| `max_iterations` | 12 | Hard ceiling; early-stop usually fires first |
| `early_stop_patience` | 3 | Stop after K consecutive gated rounds with no improvement |
| `edit_budget.max_ops` | 3 | Max add/del/replace operations per iteration |
| `edit_budget.max_words` | 80 | Max net words changed per iteration |
| `minibatch_size` | 6 | Tasks sampled from train per iteration (without replacement per epoch) |
| `holdout_fraction` | 0.3 | Fraction of total suite held for gating; fixed at init |
| `checkpoint_every` | 1 | Every iteration is checkpointed; this controls accepted-log summary writes |
| `parallelism` | `serial` | `serial` = one-man-play; integer N = up to N concurrent subagents |
| `edit_panel` | 1 | Candidates proposed per round; gate all, keep best on holdout |
| `gate_margin` | 0.0 | Config key: the agent passes its value to `ledger.py gate --margin` (NOT auto-read by the script); candidate must beat best_so_far by strictly more than this margin |
| `validation_depth` | `self-contained` | `map-only` \| `self-contained` \| `verifiers-env` \| `full-ablation` |

---

## Minibatch Sampling

- Sample `minibatch_size` tasks from `tasks/train/` each iteration.
- Use sequential sampling without replacement within each epoch (shuffle at epoch boundary).
- Record which tasks were sampled in `rollouts/iter-NN/` so resume skips already-scored tasks.

---

## Edit-Budget Enforcement

The edit budget is the **textual learning rate** — it prevents catastrophic overwrites of rules that work.

**Enforcement:**
1. The Optimizer hat proposes edits as an ordered list in `candidates/iter-NN/edit.json`.
   Format: `[{"op": "add"|"del"|"replace", "location": "...", "content": "...", "rationale": "..."}]`
2. Count: `len(ops) <= max_ops`. If exceeded, ask for a trimmed proposal.
3. Net words: `|words_added - words_removed| <= max_words`. If exceeded, ask for condensation.
4. Apply ops in order to produce `candidates/iter-NN/candidate.md`.

**Never** apply edits directly to `skill/current.md` — always go through the candidate/gate cycle.

---

## Gate Margin and Decision

`scripts/ledger.py gate` reads `ledger.csv` and computes:

```
candidate_mean = mean(holdout scores for current iter)
best_so_far    = max held-out mean across all accepted versions (computed by ledger.py best(), NOT a stored column)
accept         = candidate_mean > best_so_far + gate_margin   # strict; a tie is rejected
```

Output: `accept` or `reject`. This is deterministic — no LLM involved in the decision.

> Invariant: the v0 baseline holdout eval MUST be recorded during SETUP (`ledger.py record --version v0 --split holdout`) before the first `gate` call. Otherwise best() returns None and the first candidate is accepted unconditionally (fail-open).

> Version-label convention (load-bearing): the baseline ledger label is `v0`; the candidate at iteration N is labelled `cN` (c1, c2, ...). Pass the SAME label to `ledger.py record --version cN --split holdout` and `ledger.py gate --candidate cN` — `holdout_mean()` looks up rows by exact version string, so a mismatch makes the gate find no scores. On-disk skill files (skill/v0.md, skill/v1.md, ...) are named independently of these ledger labels.

On accept/reject: `ledger.py gate` has ALREADY written the kind=gate decision row. Do not call `record` for the decision — `record` only writes kind=eval rows and cannot set the decision field. On accept, also save the candidate to skill/v(K+1).md and update current.md; on reject, append the reason to memory/rejected-edits.md.

On `accept`:
- Copy `candidates/iter-NN/candidate.md` → `skill/v(K+1).md` and `skill/current.md`.
- Append to `memory/accepted-log.md` with held-out delta.

On `reject`:
- Append to `memory/rejected-edits.md`: the edit.json, failure reason (score delta), and iteration.
- Increment no-improvement counter; check against `early_stop_patience`.

---

## Memory and Slow-Update Policy

**rejected-edits.md** is an append-only log. Each entry:
```
## Iter NN — REJECTED (delta: -0.03)
Edit ops: [summary of edit.json]
Reason: held-out score fell from 0.71 to 0.68
Evidence needed to retry: at least 3 minibatches showing this failure pattern
```

**Before every Edit phase:**
1. Read `memory/rejected-edits.md` fully.
2. Do not re-propose any rejected edit unless new evidence from ≥3 subsequent rollouts shows the failure pattern it was meant to fix.
3. Accumulated evidence across multiple minibatches is required to overturn established rules — one bad minibatch is not enough.

**Slow-update discipline:** The Optimizer hat must explain in `edit.json` why a retry is warranted if proposing something similar to a rejected edit.

---

## Parallelism

**`serial`** (default): the one-man-play. Main agent executes all phases sequentially.

**`parallelism: N`** (integer): fan out rollouts and holdout-gating to up to N concurrent subagents.
- Each subagent writes to a unique leaf: `rollouts/iter-NN/task-MM/`. No collisions.
- Main agent dispatches subagents, then aggregates results when all leaves are written.
- No code or layout changes between serial and parallel modes — only who writes the files.
- Resume logic is the same: read `ledger.csv`; skip any leaf that already has `score.json`.

---

## edit_panel (Multi-Candidate Gating)

`edit_panel: K` proposes K candidates per round. Default is 1 (single candidate).

With `edit_panel: K > 1`:
1. Optimizer hat proposes K different candidates, each in `candidates/iter-NN/candidate-JJ.md`.
2. Gate runs holdout rollouts for **all K candidates** (in parallel if `parallelism > 1`).
3. Keep the candidate with the highest holdout mean (if it beats best_so_far); reject the rest.
4. All rejected candidates' edits are appended to `memory/rejected-edits.md`.

Useful for thoroughness runs where computational budget is available and diversity of proposals
is desirable.

---

## Resume Protocol

Re-invoke `skill-opt` on an existing run directory:

1. Read `ledger.csv` to find the last completed iteration and phase.
2. Find the first incomplete leaf in `rollouts/` (no `score.json`) — resume from there.
3. If a candidate exists but no holdout rollouts: re-run gating.
4. If gating completed but no memory update: apply memory update.
5. Continue loop from the next iteration.

Every phase appends to `ledger.csv` before proceeding — a crash mid-phase leaves the row incomplete,
which the resume logic detects.
