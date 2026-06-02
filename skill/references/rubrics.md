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
