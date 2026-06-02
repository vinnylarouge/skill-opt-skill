# skill-opt Run Report

**Run:** {RUN_DIR}
**Target skill:** {TARGET_SKILL}
**Date:** {DATE}
**Iterations run:** {ITERATIONS_RUN} / {MAX_ITERATIONS}
**Stop reason:** {STOP_REASON}  <!-- early_stop | max_iterations | user_stop -->

---

## Baseline → Best

| Version | Held-out mean score | Delta |
|---|---|---|
| v0 (baseline) | {BASELINE_SCORE} | — |
| v{BEST_VERSION} (best) | {BEST_SCORE} | {DELTA} ({DELTA_PCT}%) |

**Diff summary** (v0 → v{BEST_VERSION}):

```diff
{SKILL_DIFF}
```

---

## Per-Task Gains (holdout)

| Task ID | v0 score | Best score | Delta |
|---|---|---|---|
| {TASK_ID} | {V0_SCORE} | {BEST_SCORE} | {DELTA} |

---

## Judge Calibration

| Metric | Value |
|---|---|
| Spearman rho (LLM-judge vs programmatic) | {RHO} |
| Tasks with dual scores | {N_DUAL} |
| Calibration threshold | {THRESHOLD} |
| Status | {PASS_FAIL} |

{CALIBRATION_NOTES}

---

## Accepted Edits Log Summary

| Iter | Held-out delta | Edit summary |
|---|---|---|
| {ITER} | {DELTA} | {EDIT_SUMMARY} |

---

## Rejected Edits Summary

Total rejected: {N_REJECTED}

Notable patterns in rejections:
- {REJECTION_PATTERN_1}
- {REJECTION_PATTERN_2}

---

## Output

**Mode:** {OUTPUT_MODE}
**Written to:** {OUTPUT_PATH}
**v0 backup:** {V0_BACKUP_PATH}
