---
name: skill-opt
description: "Use to optimize/improve an existing agent skill against scored tasks. Ports Microsoft SkillOpt: treats the target SKILL.md as a trainable document and improves it via a rollout→reflect→edit→gate→memory loop with a held-out gate, while keeping the model frozen. Trigger when the user wants to tune, harden, or measurably improve a skill."
---

# skill-opt

## What This Does

One agent switches hats: **Setup → Rollout → Score → Reflect → Edit → Gate → Memory**, then repeats.
The run directory `.skill-opt/runs/<skill>-<n>/` is the message bus — every phase reads/writes files
there, making runs resumable from any point. The one-man-play is the backbone, **not a constraint**:
when `parallelism > 1`, rollouts and gating fan out to fresh subagents.

## Up-Front Questionnaire

Ask the user these questions, then write `config.yml` from `templates/config.yml`:

| Knob | Default | Notes |
|---|---|---|
| `target_skill` | — (required) | path to SKILL.md or skill dir |
| `edit_references` | `false` | also edit `references/`? |
| `feedback_source` | `proposed-ratified` | `proposed-ratified` \| `autonomous` \| `user-suite` \| `live` |
| `feedback_timing` | `autonomous` | `autonomous` \| `interactive` (pause at each gate) |
| `output_mode` | `save-as-new` | `save-as-new` \| `overwrite` (keeps v0 backup) |
| `max_iterations` | `12` | hard ceiling on loop iterations |
| `early_stop_patience` | `3` | stop after K gated rounds with no improvement |
| `edit_budget` | `{max_ops: 3, max_words: 80}` | "textual learning rate" per iteration |
| `minibatch_size` | `6` | train tasks per iteration |
| `holdout_fraction` | `0.3` | fraction of suite held for gating |
| `checkpoint_every` | `1` | iterations between checkpoint summaries |
| `parallelism` | `serial` | `serial` \| integer fan-out width |
| `edit_panel` | `1` | candidates per round; gate all, keep best |
| `gate_margin` | `0.0` | held-out margin to accept; passed to `ledger.py gate --margin` |
| `validation_depth` | `self-contained` | `map-only` \| `self-contained` \| `verifiers-env` \| `full-ablation` |

Values above are plain strings — reply with raw text, never backtick-wrapped. See `references/feedback-sources.md` for how each `feedback_source` builds the task suite.

## The Loop

```
SETUP: questionnaire→config.yml; build/ingest suite→tasks/{train,holdout}; snapshot skill/v0.md;
       ROLLOUT(v0) over holdout → baseline via `scripts/ledger.py record`.
LOOP iter=1..max (early-stop after `early_stop_patience` non-improving gates, or user stop):
  ROLLOUT  : for each train-minibatch task, dispatch a FRESH SUBAGENT given ONLY {current skill text, task};
             write rollouts/iter-NN/task-MM/trajectory.md.
  SCORE    : judge each trajectory (programmatic if available else LLM-judge subagent) → score.json;
             `ledger.py record --split train`.
  REFLECT  : split minibatch into SUCCESS and FAILURE; reflect on each SEPARATELY; read memory/rejected-edits.md.
  EDIT     : propose bounded add/del/replace ops within edit_budget → candidates/iter-NN/{candidate.md,edit.json}.
  GATE     : ROLLOUT(candidate) over tasks/holdout (fresh subagents); `ledger.py record --split holdout`;
             `ledger.py gate` decides. accept→skill/v(K+1).md & update current.md; reject→append memory/rejected-edits.md.
  MEMORY   : slow update — established rules need accumulated evidence to be overturned.
FINALIZE : emit per output_mode (overwrite w/ v0 backup, or save-as-new <skill>-opt/); write report.md.
```

## Disciplines (Non-Negotiable)

- **Frozen target via fresh subagent** — each rollout subagent receives exactly two inputs: the current
  skill text and the task prompt. Nothing else is passed to the subagent.
- **Gate only on held-out** — never use train scores for acceptance decisions.
- **Deterministic gate decision** — `scripts/ledger.py gate` does arithmetic on `ledger.csv`; an LLM
  never decides accept/reject.
- **Edits bounded by `edit_budget`** — caps ops and net words per iteration (the "textual learning
  rate"); prevents catastrophic overwrites.
- **Consult `memory/rejected-edits.md` before every edit proposal** — do not re-propose known-bad
  edits without new evidence.

## Run Directory Layout

```
.skill-opt/runs/<skill>-<n>/
  config.yml
  skill/          v0.md  v1.md ...  current.md
  tasks/          train/  holdout/  suite.json
  rollouts/       iter-NN/task-MM/  trajectory.md  score.json
  candidates/     iter-NN/          candidate.md   edit.json
  memory/         rejected-edits.md  accepted-log.md
  ledger.csv      (source of truth; columns: iter, kind, version, split, mean_score, n, decision)
                  kind: eval | gate.  split: train | holdout.  decision: accept | reject | (empty).
  report.md
```

Each subagent writes to a unique leaf path — parallel writes never collide.

## Resume

Re-invoke on an existing run directory. Read `ledger.csv` to find the last completed phase, then
continue. No double-work: every phase appends to `ledger.csv` before proceeding.

## Reference Docs

- `references/loop.md` — phase mechanics, defaults, edit-budget enforcement, gate margin, memory/slow-update policy, parallelism and edit_panel
- `references/fidelity.md` — SkillOpt correspondence map (five mechanisms, any deviations justified)
- `references/feedback-sources.md` — the 4 signal modes: how Setup builds the suite and how Judge scores per mode
- `references/rubrics.md` — drafting task suites and scoring rubrics; programmatic vs LLM-judge; judge calibration



---

# Reference: feedback-sources.md

# Feedback Sources — The Four Signal Modes

`feedback_source` in `config.yml` controls how Setup builds the task suite and how Judge scores each trajectory. The held-out split is always carved before the loop begins.

---

## 1. `proposed-ratified` (default)

**Setup:** The agent reads the target skill and drafts a task suite + scoring rubric. It proposes the suite to the user, who approves or edits it once. The approved suite is written to `tasks/` and `tasks/suite.json`.

**Judge:** Programmatic checker if one can be derived from the rubric (e.g. field-presence checks, regex, JSON schema). Otherwise LLM-judge subagent scores each trajectory against the rubric. Judge calibration (ρ) runs at finalize: compare LLM-judge scores to programmatic scores on any task where both exist.

**Held-out split:** Formed from the full approved suite using `holdout_fraction` (default 0.3). The user does not influence the split.

**When to use:** Default. Balances autonomy (no repeated user input after approval) with user oversight (they ratify the suite once).

---

## 2. `autonomous`

**Setup:** Agent synthesizes tasks, rubric, and judge entirely without user input. Reads the target skill's stated purpose and derives tasks that exercise it.

**Judge:** LLM-judge subagent (programmatic checker where derivable). No user validation of the rubric.

**Held-out split:** Same as proposed-ratified — held-out carved at init.

**When to use:** Fully automated pipelines, dogfooding, rapid prototyping where user sign-off is not available. Higher risk of judge drift — rely on judge calibration check.

---

## 3. `user-suite`

**Setup:** User provides a file of tasks (and ideally gold outcomes or pass-fail checks). Agent reads the file, validates format, and imports into `tasks/`. Drafts a scoring rubric from task structure if not provided.

**Judge:** Programmatic checker using provided gold/checks if available — this is the strongest signal. Falls back to LLM-judge with the user-defined rubric.

**Held-out split:** Carved from the user-provided suite using `holdout_fraction`. If the user wants a specific holdout, they can supply a pre-split suite (two files: `train_tasks.md`, `holdout_tasks.md`).

**When to use:** When the user has existing evals, golden examples, or regression tests. Highest fidelity — programmatic ground truth licenses trusting the loop.

---

## 4. `live`

**Setup:** No pre-built suite. Tasks are the real tasks the user performs with the skill during a work session. Each real task is logged as it arrives.

**Judge:** Real outcome — did the task succeed? User rates each outcome (pass/fail or 0–5). This is the actual feedback signal.

**Held-out split:** Rolling window — the most recent `holdout_fraction` of logged tasks form the current holdout; earlier tasks are train. Gating happens on the rolling holdout.

**When to use:** When no synthetic suite is feasible, or when real-world alignment matters most. Slowest (one iteration per real-task batch). Requires `feedback_timing: interactive`.

---

## Choosing a Mode

| Situation | Recommended mode |
|---|---|
| Starting fresh, want low friction | `proposed-ratified` |
| Fully automated / CI pipeline | `autonomous` |
| Have existing test cases or gold answers | `user-suite` |
| Want to optimize against real work | `live` |

## Judge Calibration

Regardless of mode, run judge calibration at finalize: compute Spearman ρ between LLM-judge scores and programmatic scores on any task where both exist. If ρ is below threshold (configurable, default 0.7), flag the result — LLM-judge may not be tracking real quality for this skill.



---

# Reference: fidelity.md

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



---

# Reference: loop.md

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



---

# Reference: rubrics.md

# Rubrics — Drafting Task Suites and Scoring Rubrics

This reference covers how to build a task suite from a target skill's stated purpose,
when to use programmatic checkers vs LLM-judges, and how to calibrate the judge.

---

## Drafting a Task Suite

**Step 1: Identify the skill's purpose and failure modes.**
Read the target `SKILL.md`. What does it ask the agent to do? What would "wrong" look like?
List 3–5 concrete failure modes (e.g. wrong output format, missing edge case, ignoring a rule).

**Step 2: Generate tasks that exercise those failure modes.**
Each task is a realistic input + a clear success criterion. Tasks should:
- Be short enough that a fresh subagent can complete one in a single turn.
- Cover the spectrum from easy (baseline should pass) to hard (headroom exists).
- Aim for baseline accuracy ≈ 40–60% so the optimizer has room to improve.

**Step 3: Balance the suite.**
- Minimum 10 tasks recommended; 20–30 for reliable holdout statistics.
- Cover at least 3 distinct sub-scenarios (not all variations of the same type).
- Ensure holdout (30%) contains representative difficulty — stratify if needed.

**Step 4: Write suite.json.**
```json
{
  "skill": "target-skill-name",
  "source": "proposed-ratified",
  "total": 20,
  "holdout_fraction": 0.3,
  "tasks": [
    {"id": "task-000", "split": "train", "checker": "programmatic"},
    {"id": "task-001", "split": "holdout", "checker": "llm-judge"},
    ...
  ]
}
```

---

## When to Use a Programmatic Checker

Use a programmatic checker when the success criterion is **objective and mechanically verifiable**:

- JSON field presence and type: `"amount" in result and isinstance(result["amount"], float)`
- Format constraints: ISO 8601 date, currency code from a known set
- Range checks: score between 0 and 1
- Exact match after normalization: lowercase + strip

Programmatic checkers are always preferred. They are:
- Fast (no LLM call)
- Deterministic (same input → same score)
- Trustworthy (no judge drift)
- The ground truth for judge calibration

**How to write one:** A Python function `check(task, response) -> float [0.0–1.0]` that returns
a normalized score. Store in `playground/checker.py` or inline in `suite.json` as a check spec.

---

## When to Use an LLM-Judge

Use an LLM-judge when success criteria involve judgment, style, or correctness that cannot be
mechanically verified:

- Is the explanation clear and accurate?
- Does the response follow the skill's stated procedure?
- Is the tone appropriate?

**Judge prompt template:**
```
You are evaluating an agent response. Score it 0.0–1.0 against this rubric:

Task: {task_prompt}
Response: {trajectory}

Rubric:
{rubric_criteria}

Return ONLY a JSON object: {"score": <float>, "reason": "<one sentence>"}
```

**Judge discipline:**
- Use a fresh subagent for each trajectory — no accumulated context.
- Run judge in parallel with programmatic checker on any task where both are possible.
- Record both scores for calibration.

---

## Judge Calibration

**Goal:** Verify that the LLM-judge's scores track the programmatic ground truth.

**Method:** On any task where both a programmatic checker and LLM-judge ran, compute
Spearman rank correlation (ρ) between their scores across tasks.

**Threshold:** Default ρ ≥ 0.7. If below, the LLM-judge may not be reliable for this skill.

**Calibration output** (written to `report.md`):
```
Judge calibration: ρ = 0.83 (n=14 tasks with dual scores)
Status: PASS (threshold 0.70)
```

**If calibration fails:**
- Inspect tasks where judge and programmatic scores diverge most.
- Revise the judge rubric to be more concrete.
- Consider switching to `user-suite` mode with user-provided gold answers.
- Do not trust the optimization run's gains without passing calibration.

---

## Rubric Quality Checklist

Before finalizing a rubric, verify:
- [ ] Each criterion is independently scorable (not entangled with others)
- [ ] A human reading the rubric would score the same as the intended checker
- [ ] The rubric covers at least one criterion per identified failure mode
- [ ] Hard constraints (must/must-not) are separated from soft quality criteria
- [ ] The rubric specifies what a 0.0 score looks like, what a 1.0 score looks like
