# skill-opt run report — extract-fields-1

**Target:** `playground/seed-skill/SKILL.md` · **Feedback source:** user-suite (programmatic checker = ground truth) · **Scaled proof run** (3 iterations, holdout=4, parallelism=4)

## Result

- **Baseline (v0) held-out:** 0.700
- **Best (v2 = accepted c2) held-out:** 1.000  (**+0.300**)
- **Accepted edits:** 2 (date-ISO, currency-code) · **Rejected:** 1 (note-null)
- **Judge calibration:** Spearman ρ = 0.868 (n=16) between LLM-judge (gold-blind) and programmatic ground truth — judge is well-calibrated.

## Held-out trajectory (from ledger.csv)

| iter | candidate | held-out mean | gate | best after |
|---|---|---|---|---|
| 0 | v0 (baseline) | 0.700 | — | v0 0.700 |
| 1 | c1 | 0.750 | **accept** | c1 0.750 |
| 2 | c2 | 1.000 | **accept** | c2 1.000 |
| 3 | c3 | 1.000 | **reject** | c2 1.000 |

## Per-task held-out gains (v0 → best c2)

| task | text (abbrev) | v0 | best |
|---|---|---|---|
| t010 | LexCorp statement 2026-9-2 £415.50 — retai… | 0.80 | 1.00 |
| t014 | Sterling Cooper paid £1,080.00 on 28 Feb 2… | 0.60 | 1.00 |
| t016 | Vandelay Industries billed $499.99 on Oct … | 0.60 | 1.00 |
| t018 | Initech (2nd invoice) €900 on 2026-4-15, r… | 0.80 | 1.00 |

## Accepted edits
```
iter1: accept c1 -> v1 (holdout 0.70 -> 0.75); added date-ISO rule
iter2: accept c2 -> v2 (holdout 0.75 -> 1.00); added currency-code rule
```
## Rejected edits (held-out gate discipline)
```
iter3: REJECT c3 (holdout 1.00, ties best c2 1.00; strict gate). note-null rule helps TRAIN but holdout has no absent-note tasks to validate it -> not accepted. Signal: enlarge holdout to capture note-null cases. patience=1.
```
## Output

Best version **v2** saved (save-as-new) to `playground/seed-skill-opt/SKILL.md`. Original seed skill untouched; `skill/v0.md` backup retained in run dir.

## Note on the rejected edit

The iter-3 `note-null` edit is correct on *training* data (snippets like "No memo.") but the 4-task holdout has no absent-note cases, so it could not improve held-out score and was rejected (strict gate). This is the held-out discipline working as designed; it also flags that a larger holdout would capture note-null cases and let that edit through.
