# skill-opt dogfood run report — skill-opt-1

**Target:** `skill/SKILL.md` (skill-opt's own SKILL.md + references) · **Feedback source:** autonomous (programmatic checker = ground truth) · **Dogfood run** (3 iterations, holdout=10, train=20, 30 tasks total)

## Result

- **Baseline (v0) held-out:** 0.900
- **Best (v1 = accepted c1) held-out:** 1.000 (**+0.100**)
- **Accepted edits:** 1 (iter 1: frozen-target reword + plain-string note)
- **Rejected edits:** 1 (iter 2: kind-enum docs + stronger no-backtick; holdout saturated)
- **Stop reason:** early_stop (patience=2/2 after iter 2 reject + iter 3 no-signal)

## Held-out trajectory (from ledger.csv)

| iter | candidate | held-out mean | gate | best after |
|---|---|---|---|---|
| 0 | v0 (baseline) | 0.900 | — | v0 0.900 |
| 1 | c1 | 1.000 | **accept** | c1 1.000 |
| 2 | c2 | 1.000 | **reject** (tie) | c1 1.000 |
| 3 | — (no edit) | — | — (early stop) | c1 1.000 |

## Per-task holdout gains (v0 → v1)

| task | group | v0 | v1 | delta |
|---|---|---|---|---|
| t000 | config | 0.00 | 1.00 | **+1.00** |
| t005 | config | 1.00 | 1.00 | 0.00 |
| t007 | layout | 1.00 | 1.00 | 0.00 |
| t010 | layout | 1.00 | 1.00 | 0.00 |
| t016 | phases | 1.00 | 1.00 | 0.00 |
| t018 | discipline | 1.00 | 1.00 | 0.00 |
| t021 | discipline | 1.00 | 1.00 | 0.00 |
| t023 | gate | 1.00 | 1.00 | 0.00 |
| t024 | gate | 1.00 | 1.00 | 0.00 |
| t029 | resume | 1.00 | 1.00 | 0.00 |

## Accepted edits

```
iter1: accept c1 -> v1 (holdout 0.90 -> 1.00)
  Edit 1: [replace] Frozen-target discipline bullet
    Old: "receives only `{skill text, task}`; no contamination, no self-grading."
    New: "receives exactly two inputs: the current skill text and the task prompt. Nothing else is passed to the subagent."
    Rationale: Agent elaborated on exclusions ("conversation history") triggering must_not check. Positive framing discourages open-ended exclusion lists.

  Edit 2: [replace] Added plain-string note after questionnaire table
    Old: (none — line read "See references/feedback-sources.md...")
    New: "Values above are plain strings (e.g. autonomous, not code-fenced). See references/..."
    Rationale: Agent wrapped feedback_source value in backticks because table values use code formatting. Note steers toward plain-text responses.
```

## Rejected edits (held-out gate discipline)

```
iter2: REJECT c2 (holdout 1.000, ties best c1 1.000; strict gate).
  Edit 1: Added kind/split enum docs to ledger.csv layout comment
  Edit 2: Strengthened no-backtick note to "never backtick-wrapped"
  Both edits fix real TRAIN failures (t001 exact_lower backtick, t026 wrong kind values)
  but holdout is saturated at 1.000 — no room for improvement.
  Signal: expand holdout suite with tasks testing kind-enum knowledge and exact-match formatting.
```

## Train failure analysis across iterations

| iter | minibatch | mean | failures | root cause |
|---|---|---|---|---|
| 1 | t002,t012,t013,t015,t017,t025 | 0.917 | t015 (0.50) | Agent listed exclusions ("conversation history") in frozen-target answer |
| 2 | t001,t009,t014,t019,t020,t026 | 0.667 | t001 (0.00), t026 (0.00) | t001: backtick formatting (exact_lower); t026: confused kind/split column values |
| 3 | t003,t004,t006,t008,t011,t022 | 1.000 | none | All tasks passed with current v1 skill |

## Output

Best version **v1** saved (save-as-new) to `skill/v1.md` in the run directory. Original SKILL.md untouched; `skill/v0.md` backup retained.

## Diff (v0 → v1)

```diff
-See `references/feedback-sources.md` for how each `feedback_source` builds the task suite.
+Values above are plain strings (e.g. autonomous, not code-fenced). See `references/feedback-sources.md` for how each `feedback_source` builds the task suite.

-- **Frozen target via fresh subagent** — each rollout subagent receives only `{skill text, task}`; no
--  contamination, no self-grading.
+- **Frozen target via fresh subagent** — each rollout subagent receives exactly two inputs: the current
+  skill text and the task prompt. Nothing else is passed to the subagent.
```

## Observations and recommendations

1. **Holdout saturation.** The 30-task suite (10 holdout) saturated at iteration 1. Most tasks are short-answer factual recall from tables — the baseline SKILL.md already communicates this well (v0 holdout = 0.900). Recommendation: add harder procedural tasks (multi-step scenarios, config generation, failure diagnosis) to create more headroom.

2. **Checker limitations.** The `exact_lower` and `contains_all_lower_and_not_any` checkers are sensitive to formatting artifacts and negation phrasing that don't reflect real quality differences. Mixed programmatic + LLM-judge scoring would be more robust for a meta-skill like skill-opt.

3. **Undocumented `kind` enum.** The iter-2 train failure (t026) revealed a real documentation gap: the SKILL.md documents ledger.csv column names but not the enum values for `kind` (eval | gate). The rejected edit that would fix this couldn't pass the saturated holdout — a larger holdout covering this scenario would let it through.

4. **Backtick leakage.** The questionnaire table uses backtick formatting for values, causing agents to echo that formatting in responses. The v1 "plain strings" note helped (fixed t000) but agents still occasionally format with backticks (t001 in iter 2). The stronger "never backtick-wrapped" version in the rejected c2 edit would help further.

5. **The meta-circularity worked.** Skill-opt successfully optimized its own SKILL.md — the same loop that optimized the playground extraction skill (0.70 → 1.00) also improved the meta-skill itself (0.90 → 1.00). The optimization identified real documentation quality issues (positive vs negative framing, formatting leakage) and proposed targeted fixes.
