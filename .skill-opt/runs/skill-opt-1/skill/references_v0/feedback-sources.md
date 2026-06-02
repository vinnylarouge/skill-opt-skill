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
