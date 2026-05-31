# skill-opt

A meta-skill that **optimizes other agent skills**. It ports Microsoft Research's
[SkillOpt](https://microsoft.github.io/SkillOpt/) into a single Claude Code skill: the target
`SKILL.md` is treated as a *trainable document* and improved against a scored task suite via a
**Rollout → Reflect → Edit → Gate → Memory** loop, while the model stays frozen.

The encoding trick is a **one-man-play**: SkillOpt's four roles (frozen Target, Optimizer, Gate,
Memory) are played by one agent switching hats over a **run directory of files** — so runs are
resumable and any hat can fan out to subagents when speed matters.

## Install

```bash
bash install.sh          # symlinks ./skill -> ~/.claude/skills/skill-opt
uv sync                  # dev env (pytest); shipped scripts are stdlib-only
uv run pytest -q         # 33 tests: ledger gate, checker, calibration, split, skill structure
```

The loader follows the symlink, so edits to `skill/` are live. Once installed, invoke it like any
skill (it triggers on "optimize / tune / harden / measurably improve a skill").

## How it works

A run lives entirely on disk in `.skill-opt/runs/<skill>-<n>/` (the message bus between hats):

```
config.yml   skill/v0.md v1.md … current.md   tasks/{train,holdout}/
rollouts/iter-NN/task-MM/   candidates/iter-NN/   memory/{rejected-edits,accepted-log}.md
ledger.csv   report.md
```

Non-negotiable disciplines (see `skill/SKILL.md`):
- **Frozen target via fresh subagent** — each rollout sees only `{skill text, task}` (no self-grading).
- **Gate only on held-out**, and the **accept/reject decision is arithmetic** (`skill/scripts/ledger.py`), never an LLM.
- **Edit budget** caps ops/words per iteration (the "textual learning rate").
- **Rejected-edit memory** is consulted before every edit.

Configuration is a painless up-front questionnaire (`skill/templates/config.yml`): `feedback_source`
(proposed-ratified ▸ autonomous ▸ user-suite ▸ live), `feedback_timing`, `output_mode`
(save-as-new ▸ overwrite), budgets, `parallelism`, and `validation_depth`.

## Ground truth

- **Theoretical:** `skill/references/fidelity.md` maps every SkillOpt mechanism to where it lives here.
- **Empirical:** `playground/` is a self-contained testbed — a deliberately-weak `seed-skill/` and a
  20-task structured-extraction suite (`data/tasks.json`) with a **programmatic** checker
  (`checker.py`) so any gain is ground truth, plus `calibration.py` (Spearman) to verify the
  LLM-judge tracks that ground truth.

### Proof run (committed under `.skill-opt/runs/extract-fields-1/`)

Optimizing the weak seed skill (feedback_source=user-suite, 3 iterations, holdout=4):

| iter | candidate | held-out | gate |
|---|---|---|---|
| 0 | v0 baseline | 0.700 | — |
| 1 | c1 (+date-ISO) | 0.750 | accept |
| 2 | c2 (+currency-code) | **1.000** | accept |
| 3 | c3 (+note-null) | 1.000 | reject (ties; not validated on holdout) |

- **Held-out gain: 0.700 → 1.000 (+0.30)**, decided by `ledger.py` arithmetic.
- **Judge calibration: Spearman ρ = 0.868** (n=16) between the gold-blind LLM-judge and the
  programmatic checker — the result that licenses trusting the judge on real, unverifiable skills.

Full write-up: `.skill-opt/runs/extract-fields-1/report.md`. Optimized skill:
`playground/seed-skill-opt/SKILL.md`.

## Status / deferred

Built, tested (33/33), installed, and validated by the scaled proof run above. Deferred (per the
plan's optional tail): the full-budget run, the **dogfood** run (optimizing skill-opt's own
`SKILL.md`), and the `verifiers-env` / `full-ablation` validation depths.

## Docs

- Design spec: `docs/superpowers/specs/2026-05-31-skill-opt-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-31-skill-opt.md`
