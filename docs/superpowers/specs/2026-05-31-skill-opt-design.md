# skill-opt — Design Spec

**Date:** 2026-05-31
**Status:** Approved design, pending spec review → implementation plan
**Author:** Vincent (with Claude)
**Project home:** `~/Desktop/tinkering/skill-opt/`
**Install target:** `~/.claude/skills/skill-opt/`

---

## 1. Summary

`skill-opt` is a meta-skill that **optimizes other agent skills**. It ports Microsoft Research's
[SkillOpt](https://microsoft.github.io/SkillOpt/) — which treats "a compact natural-language skill
document as the trainable state of a frozen language agent" and improves it through a five-phase loop
— into a single agent skill.

The encoding trick (the "one-man-play"): SkillOpt's four roles (frozen **Target**, **Optimizer**,
**Gate**, **Memory**) and five phases (Rollout → Reflect → Edit → Gate → Update-Memory) are realized
by **one agent switching hats**, using a **run directory of files** as the message bus between hats.
Because all state is on disk, the run is resumable and checkpointed for free, and any hat can be
delegated to a fresh subagent. The one-man-play is the *enabling backbone*, **not a constraint**:
wherever wall-clock matters we fan out to subagents (rollouts and gating are embarrassingly parallel).

## 2. Background: what SkillOpt does (and what we must stay faithful to)

| SkillOpt component | Definition (paper) | Our obligation |
|---|---|---|
| **Rollout** | "The target model executes tasks with the current skill and records scored trajectories." | Every iteration runs the *current* skill version on tasks and records a trajectory **with a score**. |
| **Reflect** | "The optimizer analyzes success and failure minibatches to find reusable procedures." | Reflect on success and failure sets **separately**, extract reusable procedures. |
| **Edit** | Bounded add/delete/replace ops; "an edit budget functions as a textual learning rate, preventing useful rules from being overwritten." | Edits are bounded by a configurable **edit budget** (ops or words/iter). |
| **Gate** | "The candidate skill is kept only if it improves held-out selection performance." | Accept a candidate **only** if it beats the current best on a **held-out** split. Never gate on train. |
| **Update Memory** | "Tracks rejected edits and applies slow updates, preventing overfitting while maintaining plasticity." | Keep a **rejected-edit memory** so bad edits are not re-proposed; accumulate evidence (slow updates) rather than letting one minibatch rewrite everything. |

**Roles:** Target (frozen, runs tasks) · Optimizer (proposes edits) · Skill Document (trainable
artifact) · Validation Set (held-out, decides acceptance). **Reported result:** 52/52 best-or-tied
across 7 target models × 6 benchmarks; avg gains 9.1%–24.9%.

The **fidelity map** (§10) makes this table a shipped, checkable artifact.

## 3. Goals / Non-goals

**Goals**
- Optimize an existing agent skill's `SKILL.md` against a scored task suite, model frozen.
- Faithful to SkillOpt's five mechanisms (rollout-with-score, separate reflect, edit budget,
  held-out gate, rejected memory + slow updates).
- A **painless up-front questionnaire** drives all knobs; sensible defaults; escape hatches to
  deeper/lighter modes.
- Resumable & checkpointed via on-disk run directory.
- Serial one-man-play by default; opt-in subagent fan-out for speed.
- **Ground truth**: a fidelity map (always) + a programmatic testbed (configurable depth) that proves
  real held-out gains and **validates that the LLM-judge tracks programmatic ground truth**.
- **Dogfood**: the skill can optimize its own `SKILL.md`.

**Non-goals (v1)**
- Fine-tuning model weights (out of scope by definition).
- A generic orchestrator template for arbitrary multi-agent systems (the one-man-play insight is
  applied here, not packaged as a separate product).
- Reproducing the paper's full 7×6 benchmark sweep.
- Optimizing arbitrary prompts/CLAUDE.md (that overlaps `empirical-prompt-tuning`; we stay focused on
  agent **skills**). The engine is general enough to extend later, but v1 targets skills.

## 4. Optimization target & feedback-source modes

The **trainable artifact** is a target skill's `SKILL.md` (plus its bundled references, treated as
part of the editable document if the user opts in). The optimization **signal** comes from one of four
sources, chosen at init ("what's our source of feedback?"):

1. **Agent-proposed, user-ratified** *(default)* — the agent reads the target skill, drafts a task
   suite + scoring rubric, the user approves/edits once, then the loop runs autonomously.
2. **Fully autonomous** — agent synthesizes tasks + rubric + judges itself, no user input.
3. **User-supplied suite** — user provides tasks and (ideally) gold outcomes / pass-fail checks.
4. **Live / online** — optimize against real tasks as the user works; score by real outcomes.

In all modes a **held-out split** is carved for gating (for mode 4, a rolling held-out window). Modes
2–4 reuse the same loop; only the Setup and Judge hats differ.

## 5. Architecture

### 5.1 The run directory — the message bus

```
.skill-opt/runs/<target-skill>-<n>/
  config.yml                 # all questionnaire answers (the run's full configuration)
  skill/
    v0.md  v1.md  v2.md ...   # every ACCEPTED version; v0 = unmodified baseline
    current.md                # copy of the current best version (a copy, not a symlink, for portability)
  tasks/
    train/    task-000.md ... # each: prompt + optional gold/checks + rubric
    holdout/  task-000.md ... # the gate set; never used for reflection/editing
    suite.json               # manifest: ids, split, source mode, checker refs
  rollouts/
    iter-00/task-000/trajectory.md  score.json   # one (sub)agent writes each leaf
    iter-00/task-001/...
  candidates/
    iter-01/candidate.md  edit.json              # edit.json = ordered add/del/replace ops + rationale
  memory/
    rejected-edits.md         # each rejected edit + why it failed the gate (slow-update memory)
    accepted-log.md           # chronicle of accepted edits + held-out deltas
  ledger.csv                  # SOURCE OF TRUTH: iter, split, mean_score, n, decision, best_so_far
  report.md                   # final: baseline→best diff, per-task gains, judge-calibration summary
```

Each subagent owns a unique leaf path → parallel writes never collide. The orchestrator (main agent)
reads results back. Re-invoking `skill-opt` on an existing run resumes from `ledger.csv`.

### 5.2 The five hats and the loop

```
SETUP (once):
  run questionnaire -> config.yml
  build/ingest task suite -> tasks/train, tasks/holdout, tasks/suite.json
  snapshot baseline -> skill/v0.md
  ROLLOUT(v0) over holdout -> baseline held-out score in ledger.csv

LOOP iter = 1..max (stop early on K-no-improvement or user stop):
  # --- ROLLOUT (Target hat) ---
  minibatch = sample(tasks/train)
  for task in minibatch:                       # serial OR fan-out subagents
      fresh subagent given ONLY {current skill text, task}  # frozen, uncontaminated target
        -> rollouts/iter-NN/task-MM/trajectory.md
  # --- SCORE (Judge hat) ---
  for each trajectory: judge vs rubric/checks  # programmatic if available, else LLM-judge subagent
        -> score.json
  # --- REFLECT + EDIT (Optimizer hat) ---
  split minibatch into SUCCESS and FAILURE sets; reflect on each SEPARATELY
  read memory/rejected-edits.md                # avoid re-proposing known-bad edits
  propose bounded ops within EDIT BUDGET -> candidates/iter-NN/{candidate.md, edit.json}
  # --- GATE (Gate hat) ---
  ROLLOUT(candidate) over tasks/holdout        # fresh subagents again
  ledger.py compares candidate held-out mean vs best_so_far    # DETERMINISTIC decision
  if improved:  accept -> skill/v(K+1).md; update current; append accepted-log.md
  else:         reject -> append memory/rejected-edits.md (with the failure reason)
  # --- UPDATE MEMORY (slow updates) ---
  decay/accumulate evidence; never let one minibatch rewrite established rules

FINALIZE:
  emit per output-mode (overwrite original w/ v0 backup, or save-as-new <skill>-opt/)
  write report.md (diff, gains, judge-calibration result)
```

### 5.3 Key disciplines (faithfulness mechanics)

- **Frozen target via fresh subagent.** Each rollout runs in a subagent whose only context is the
  skill text + the task. This is the closest single-agent analogue to the paper's frozen target, and
  it eliminates target/optimizer contamination ("grading its own homework"). It is also the unit of
  parallelism. (Reuses `empirical-prompt-tuning`'s **unbiased executor** discipline.)
- **Edit budget = textual learning rate.** Config caps ops/iter (e.g. ≤3 add/del/replace) and/or net
  words changed. Prevents catastrophic overwrites of useful rules.
- **Held-out gate, deterministic.** `scripts/ledger.py` computes the accept/reject decision from the
  numbers in `ledger.csv` (mean held-out score vs. best-so-far, with a configurable margin). The
  *decision* is arithmetic, not an LLM opinion — only the per-trajectory scoring may use a judge.
- **Rejected-edit memory + slow updates.** Rejected candidates and their failure reasons persist;
  the Optimizer must consult them. Established rules require accumulated evidence to be overturned.

### 5.4 The one bit of code: `scripts/ledger.py`

A tiny, dependency-light Python helper (ships in the skill) that: appends rows to `ledger.csv`,
aggregates per-iteration scores, and emits the gate decision (`accept`/`reject` + best-so-far). Keeps
the gate reproducible. Everything else is prose convention driven by the agent.

## 6. Up-front questionnaire (config.yml schema)

Asked once at init; written to `config.yml`. Fields (with defaults):

| Field | Choices / type | Default |
|---|---|---|
| `target_skill` | path to a `SKILL.md` (or skill dir) | — (required) |
| `edit_references` | bool — also edit the skill's `references/`? | `false` |
| `feedback_source` | `proposed-ratified` \| `autonomous` \| `user-suite` \| `live` | `proposed-ratified` |
| `feedback_timing` | `autonomous` \| `interactive` (pause at each gate for approve/reject/comment; comment feeds Reflect) | `autonomous` |
| `output_mode` | `overwrite` (keep v0 backup) \| `save-as-new` (`<skill>-opt/`) | `save-as-new` |
| `max_iterations` | int | `12` |
| `early_stop_patience` | int (stop after K gated rounds w/o improvement) | `3` |
| `edit_budget` | `{max_ops, max_words}` per iteration | `{3, 80}` |
| `minibatch_size` | int | `6` |
| `holdout_fraction` | float | `0.3` |
| `checkpoint_every` | int (iterations) | `1` (run dir is always a checkpoint) |
| `parallelism` | `serial` \| int fan-out width | `serial` |
| `edit_panel` | int candidates/round (keep best on holdout) | `1` |
| `validation_depth` | `map-only` \| `self-contained` \| `verifiers-env` \| `full-ablation` | `self-contained` |

`validation_depth` is the in-skill version of the ground-truth menu (§10): the user picks how much
empirical proof to run, defaulting to the self-contained testbed.

## 7. Parallelism model

`parallelism: serial` is the literal one-man-play. `parallelism: N` dispatches rollouts and
holdout-gating as up to N concurrent subagents, each writing its own `iter-NN/task-MM/` leaf. No code
or layout changes between modes — only *who* writes the files. `edit_panel: K>1` proposes K candidates
per round and gates them in parallel, keeping the best (a judge-panel pattern, for thoroughness runs).

## 8. Output, checkpoints, resume

- **Checkpoint** = the run dir itself; `checkpoint_every` controls how often a tagged summary is
  written to `accepted-log.md`. **Resume** = re-invoke on an existing run; the agent reads
  `ledger.csv` and continues from the last completed phase.
- **Finalize** writes the best version per `output_mode`: `overwrite` replaces the target `SKILL.md`
  (with `v0.md` preserved as backup in the run dir); `save-as-new` writes a sibling skill dir
  `<skill>-opt/` so the original is untouched. Always emits `report.md`.

## 9. Dogfooding

Because the skill optimizes agent skills and *is* one, self-optimization is just `config.yml`
pointing `target_skill` at `skill-opt`'s own `SKILL.md`. This is the first real acceptance test: the
loop must produce **gated** (held-out-validated) gains on itself.

## 10. Ground truth & validation

Two layers; the second's depth is `config.yml.validation_depth`.

**Theoretical — fidelity map** (`references/fidelity.md`, always ships): the §2 table as a checkable
artifact — every SkillOpt mechanism mapped to where it lives in our skill, with any deviation
explicitly justified.

**Empirical — the playground** (`~/Desktop/tinkering/skill-opt/playground/`, separate from the
installed skill so `~/.claude/skills/skill-opt/` stays clean):

- **`self-contained`** *(default)*: a deliberately-weak seed skill + a **structured-extraction** task
  suite (messy text → JSON with specific fields; **programmatic** field-level checker — no judge in
  the loop), split train/holdout. The wins come from procedural rules the optimizer must discover
  (ISO date normalization, null-for-missing, currency handling) that live in the skill doc and are
  followed by a frozen target — i.e. genuinely "skill-like," with tunable headroom.
  **Two acceptance checks:**
  1. **Gains are real:** baseline→optimized **held-out** programmatic score climbs.
  2. **Judge calibration:** the LLM-judge's scores **track** the programmatic scores (rank
     correlation above a threshold). *This is the load-bearing check* — it's what licenses trusting
     the LLM-judge on real skills where no programmatic checker exists.
- **`verifiers-env`**: implement the testbed as a verifiers environment, reusing the Prime/verifiers
  stack and `prime eval`. Strongest "in a similar manner they did" fidelity (their benchmarks were
  objective-scored environments); adds a toolchain dependency.
- **`full-ablation`**: self-contained testbed **plus** an ablation (gate off / edit-budget unbounded /
  memory off) to empirically reproduce the paper's claim that those three components are load-bearing.
- **`map-only`**: theoretical validation only; defer the playground.

## 11. Relationship to existing skills

- **`empirical-prompt-tuning`** — sibling. Same spirit (unbiased executor + two-sided eval + iterate).
  `skill-opt` is the heavier, **gated/held-out** optimizer specialized for skills, with an edit budget
  and rejected memory. We **reuse its unbiased-executor discipline** for the Target hat rather than
  reinvent it.
- **`write-a-skill` / `skill-creator`** — complementary. They **create** skills; `skill-opt`
  **optimizes** existing ones.
- **`retrospective-codify`** — complementary. It codifies one-shot learnings into rules; `skill-opt`
  does iterative, measured, gated optimization.

## 12. Skill on disk

```
~/.claude/skills/skill-opt/
  SKILL.md                    # lean: the loop, the hats, the disciplines, the questionnaire
  references/
    fidelity.md               # the SkillOpt mechanism-correspondence map (ground truth, theory)
    loop.md                   # detailed phase mechanics (edit budget, gate margin, memory)
    feedback-sources.md       # the 4 signal modes + how Setup/Judge differ per mode
    rubrics.md                # how to draft task suites + scoring rubrics
  templates/
    config.yml                # questionnaire template w/ defaults + comments
    task.md  ledger.csv  report.md
  scripts/
    ledger.py                 # deterministic score aggregation + gate decision
```
Progressive disclosure: `SKILL.md` stays lean; mechanics live in `references/`.

## 13. Build sequence

1. **Skill skeleton** — `SKILL.md` + `references/` + `templates/` + `scripts/ledger.py`; run-dir
   convention; questionnaire.
2. **Fidelity map** — write `references/fidelity.md` (theory ground truth) alongside the skill so
   mechanism and documentation stay in lockstep.
3. **Playground (self-contained)** — weak seed skill + extraction suite + programmatic checker +
   train/holdout in `~/Desktop/tinkering/skill-opt/playground/`.
4. **First real run** — optimize the weak seed skill; confirm held-out gains + judge calibration.
5. **Dogfood** — optimize `skill-opt`'s own `SKILL.md`; confirm gated gains.
6. **(Optional)** `verifiers-env` and/or `full-ablation` depths.

## 14. Risks & open questions

- **No headroom / saturated baseline.** Mitigate by tuning testbed difficulty so baseline ≈ 40–60%.
- **Judge drift in the no-ground-truth case.** Directly addressed by the calibration check (§10);
  if calibration is weak, prefer programmatic/user-supplied checks (modes 3) for that skill.
- **Cost.** Rollouts × tasks × iterations × gating can be many subagent calls. Mitigations: small
  `minibatch_size`, `early_stop_patience`, serial default, explicit budget surfaced at init.
- **Editing references vs SKILL.md.** v1 defaults to editing `SKILL.md` only (`edit_references:false`).
- **Resume correctness.** `ledger.csv` is the single source of truth; every phase appends before
  proceeding so a crash resumes cleanly.

## 15. Acceptance criteria

- [ ] `skill-opt` installed; init questionnaire produces a valid `config.yml`.
- [ ] A full loop runs on the playground seed skill and **improves held-out programmatic score** over
      baseline, with the decision made by `ledger.py` (not an LLM).
- [ ] **Judge calibration** check passes on the playground (LLM-judge tracks programmatic ground truth).
- [ ] `references/fidelity.md` maps all five SkillOpt mechanisms with justified deviations.
- [ ] A run can be **interrupted and resumed** from `ledger.csv` with no double-work.
- [ ] **Dogfood**: optimizing `skill-opt`'s own `SKILL.md` yields a gated improvement.
- [ ] `save-as-new` and `overwrite` output modes both work; `v0` backup preserved.
