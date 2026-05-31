# Task: {TASK_ID}

## Prompt

<!-- The full task prompt given to the agent (the only context it receives, along with the skill). -->

{TASK_PROMPT}

## Gold / Checks (optional)

<!-- If a programmatic checker applies, record the expected output or check spec here.
     Leave blank if using LLM-judge only. -->

```json
{
  "expected": {},
  "checks": []
}
```

## Rubric

<!-- Scoring criteria. Each criterion should be independently assessable. -->

| Criterion | Weight | Description |
|---|---|---|
| {CRITERION_1} | {WEIGHT_1} | {DESCRIPTION_1} |
| {CRITERION_2} | {WEIGHT_2} | {DESCRIPTION_2} |

**Score range:** 0.0 (complete failure) – 1.0 (fully correct)

**0.0 looks like:** {FAILURE_EXAMPLE}
**1.0 looks like:** {SUCCESS_EXAMPLE}
