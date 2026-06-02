"""Self-test the hard-v1 checker on gold-correct synthetic responses.

Validates:
1. Gold responses score >= 0.9 (ideally 1.0; some multi_criterion tasks may get 0.9+)
2. Adversarial junk responses score <= 0.1
3. Partial-credit calibration: medium responses score in [0.3, 0.7]
"""
import json
import sys
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_DIR / "scripts"))
from checker import score_one  # noqa: E402

SUITE = json.loads((SUITE_DIR / "suite.json").read_text())

# Gold responses: best-case answers that should score high
gold_resp = {
    "h000": "SETUP creates: config.yml, tasks/suite.json, tasks/train/ (15 tasks), tasks/holdout/ (10 tasks), skill/v0.md (snapshot). With holdout_fraction=0.4 and 25 tasks: holdout = round(25*0.4) = 10, train = 15. Recorded in ledger.csv: `ledger.py record --version v0 --split holdout` to establish baseline.",

    "h001": "ROLLOUT: 6 subagents dispatched (parallelism=4 means up to 4 concurrent, but 6 tasks total so 2 batches). Each writes rollouts/iter-01/task-NN/trajectory.md. SCORE: Main agent judges each trajectory → writes score.json per leaf. REFLECT: Main agent splits minibatch into SUCCESS/FAILURE sets, reflects separately. EDIT: edit_panel=2 means Optimizer proposes 2 candidates: candidates/iter-01/candidate-01.md and candidates/iter-01/candidate-02.md, each with edit.json. GATE: Holdout rollouts run for both candidates (fresh subagents). ledger.py gate picks best. MEMORY: Rejected candidate edits appended to memory/rejected-edits.md; accepted → skill/v1.md + current.md + memory/accepted-log.md.",

    "h002": "Before proposing a similar edit, the Optimizer MUST read memory/rejected-edits.md fully. The slow-update policy requires: 'Do not re-propose any rejected edit unless new evidence from at least 3 subsequent rollouts shows the failure pattern it was meant to fix.' Since only iter 3 has happened since rejection, that's only 1 minibatch — not enough. Need evidence from at least 3 minibatches showing this failure pattern.",

    "h003": "Sequence of ledger.py commands for iteration 2:\n1. `ledger.py record --run .skill-opt/runs/my-skill-1/ --iter 2 --version v1 --split train --scores <6 comma-sep scores>` (train eval of current best on minibatch)\n2. `ledger.py record --run .skill-opt/runs/my-skill-1/ --iter 2 --version c2 --split holdout --scores <holdout scores>` (candidate holdout eval)\n3. `ledger.py gate --run .skill-opt/runs/my-skill-1/ --iter 2 --candidate c2 --margin 0.0` (gate decision)",

    "h004": "After gate ACCEPTS c3 at iteration 3 (second acceptance, previous was c1→v1):\n1. ledger.csv: gate row already written by decide() with kind=gate, decision=accept\n2. candidates/iter-03/candidate.md → copied to skill/v2.md (second accepted = v2)\n3. skill/current.md updated with candidate content\n4. memory/accepted-log.md: append entry with held-out delta",

    "h005": "Early stopping fires AFTER iteration 5 completes. Counter logic: iter1=accept (counter=0), iter2=reject (counter=1), iter3=accept (counter resets to 0), iter4=reject (counter=1), iter5=reject (counter=2). With patience=2, counter reaches 2 after iter5, so early stopping fires. The counter resets to 0 on any accept.",

    "h006": "c1 was rejected because 0.85 does NOT beat best_so_far (v0 at 0.90). The gate requires candidate_mean > best_so_far + margin. With margin=0.0: 0.85 > 0.90 + 0.0 is FALSE. The comparison is strictly greater than, so c1 scores below the baseline and is rejected.",

    "h007": "This is impossible under correct gate logic. best() returns the max held-out mean across all accepted versions. If c1 was accepted with 0.60, best_so_far becomes 0.60. c2 at 0.62 > 0.60 → accept. c3 at 0.65 > 0.62 → accept. But c4 at 0.63 is NOT > best_so_far which is now 0.65. So c4 would be REJECTED, not accepted. If the report shows c4 accepted, there's a bug — either best() is not computing max correctly, or the version labels are mismatched causing best() to miss scores.",

    "h008": "Resume reads ledger.csv — finds no holdout eval rows for iter 3's candidate. Checks rollouts/ — finds candidates/iter-03/ exists with candidate.md and edit.json. Checks rollouts/iter-03/ for holdout rollouts — not found. Resume protocol step 3: 'If a candidate exists but no holdout rollouts: re-run gating.' So it dispatches holdout rollouts for the existing candidate, scores them, records in ledger, then runs gate decision.",

    "h009": "Two distinct root causes:\n1. Train-holdout distribution mismatch: The edits fix train-specific failure patterns that don't appear in holdout. Investigate: compare task types/difficulty between splits; ensure holdout is representative.\n2. Holdout ceiling/saturation: All holdout tasks may already score at maximum with the current skill, leaving no room for improvement regardless of train gains. Investigate: look at per-task holdout scores — if all are 1.0, the holdout is saturated and needs harder tasks.",

    "h010": "This is the fail-open failure mode. In ledger.py, best() calls accepted_versions() which always includes 'v0', then gets holdout_mean(v0). If v0's holdout eval row is missing, holdout_mean returns None. In best(), scored = [(v, s) for v, s in scored if s is not None] filters it out, returning (None, None). In decide(): best_score is None, so the condition 'cand is not None and (best_score is None or cand > best_score + margin)' evaluates to True — accepts unconditionally. The violated invariant: 'a holdout eval for v0 MUST be recorded via append_eval before the first decide() call.'",

    "h011": "The version-label convention states: 'Pass the SAME label to ledger.py record --version cN --split holdout and ledger.py gate --candidate cN — holdout_mean() looks up rows by exact version string, so a mismatch makes the gate find no scores.' The user recorded with 'C2' (uppercase) but queried gate with 'c2' (lowercase). holdout_mean() searches for rows where version=='c2' but the row has 'C2' — case-sensitive string match fails, returns None, and since cand is None, the gate rejects.",

    "h012": "```yaml\ntarget_skill: path/to/code-review/SKILL.md\nedit_references: false\nfeedback_source: user-suite\nfeedback_timing: autonomous\noutput_mode: overwrite\nmax_iterations: 20\nearly_stop_patience: 3\nedit_budget: {max_ops: 5, max_words: 150}\nminibatch_size: 6\nholdout_fraction: 0.3\ngate_margin: 0.0\nparallelism: serial\nedit_panel: 3\nvalidation_depth: self-contained\n```",

    "h013": "feedback_source should be `live` — real tasks become training data as the user works. feedback_timing should be `interactive` — user reviews each gate decision before it's applied. Live mode requires interactive feedback_timing because tasks arrive one at a time from real work, and the rolling-window holdout needs user ratings. Parallelism > 1 doesn't work well because live mode processes real tasks sequentially as they arrive — you can't fan out multiple subagents when the 'suite' is a single incoming real task. Also, live mode requires feedback_timing: interactive explicitly.",

    "h014": "Config keys that differ from defaults:\n  early_stop_patience: 5  (default is 3)\n  holdout_fraction: 0.4  (default is 0.3)\n  gate_margin: 0.05  (default is 0.0; positive margin = stricter acceptance)\nThe edit_budget is already conservative at default {max_ops: 3, max_words: 80} so no change needed unless they want even smaller.",

    "h015": "The MINIMUM valid config.yml requires only `target_skill` — it's the only field marked as '— (required)' with no default in the questionnaire table. Everything else has defaults: feedback_source defaults to proposed-ratified, feedback_timing to autonomous, output_mode to save-as-new, max_iterations to 12, early_stop_patience to 3, edit_budget to {max_ops: 3, max_words: 80}, minibatch_size to 6, holdout_fraction to 0.3, etc.",

    "h016": "The four validation_depth levels:\n- map-only: Cheapest. Only checks that edits don't break document structure.\n- self-contained: Default. Runs holdout rollouts with fresh subagents to validate the candidate scores higher.\n- verifiers-env: Additionally runs environment-specific verifiers (external tools, linters, etc.) on the candidate output.\n- full-ablation: Most expensive. Runs ablation study removing each edit individually to measure per-edit contribution. Compared to self-contained, full-ablation adds individual edit-removal experiments to determine which specific edits are responsible for gains.",

    "h017": "Gate decisions:\n- c2: best_so_far = max(v0=0.700, v1=0.750) = 0.750. c2=0.740 > 0.750 + 0.0? 0.740 > 0.750 is FALSE → REJECT.\n- c3: best_so_far still 0.750 (c2 was rejected). c3=0.760 > 0.750 + 0.0? 0.760 > 0.750 is TRUE → ACCEPT.",

    "h018": "With gate_margin=0.02:\n- c2: best_so_far = 0.750. c2=0.740 > 0.750 + 0.02 = 0.770? 0.740 > 0.770 is FALSE → REJECT.\n- c3: best_so_far still 0.750 (c2 rejected). c3=0.760 > 0.750 + 0.02 = 0.770? 0.760 > 0.770 is FALSE → REJECT.\nBoth rejected! The margin makes acceptance harder — c3 would need > 0.770 to pass.",

    "h019": "With edit_panel=3: gate all candidates, keep best. c2a=0.72, c2b=0.78, c2c=0.75. Best so far=0.74.\n- c2b has highest holdout (0.78) AND beats best_so_far (0.78 > 0.74) → ACCEPT c2b.\n- c2a (0.72) and c2c (0.75) are rejected even though c2c > best_so_far, because only the BEST candidate wins.\n- c2a's and c2c's edits are appended to memory/rejected-edits.md with their holdout scores.",

    "h020": "The gate function (decide()) already writes a kind=gate row to ledger.csv internally. If you also call `ledger.py record` for the same event, you'd get a duplicate row. But worse: `record` only writes kind=eval rows — it cannot set the decision field (accept/reject). So calling record would create a spurious kind=eval row that corrupts holdout_mean() calculations by doubling the score entry. The invariant: `record` writes kind=eval only; `gate` writes kind=gate only; never call both for the same logical event.",

    "h021": "best() returns (v1, 0.80). Yes, v2 is actually worse than v1 — it scored 0.75 vs v1's 0.80. best() computes max across ALL accepted versions' holdout means, so it picks v1. This means future candidates must beat 0.80 (not 0.75) to be accepted. The system correctly identifies v1 as the best even though v2 was accepted later.",

    "h022": "Ops count: 3 operations (replace + add + del) = 3. max_ops=3: PASSES.\nNet words: words_added = (40 - 15) + 30 = 55... wait. Let me recalculate. Replace: removes 15 words, adds 40 words. Add: adds 30 words. Del: removes 20 words. Total added = 40 + 30 = 70. Total removed = 15 + 20 = 35. Net = |70 - 35| = 35. max_words=80: 35 <= 80, PASSES. Both budget constraints satisfied.",

    "h023": "The optimizer should condense or combine the 4 operations into 3 or fewer that achieve the same semantic effect. For example, merge two related ops into a single replace operation. The edit budget is non-negotiable — the optimizer must find a way to express the change within the budget, potentially by combining ops into a larger single replace that captures the full intent.",

    "h024": "Words added = 20 (from replace: new sentence) + 45 (new paragraph) = 65. Words removed = 50 (old paragraph from replace). Net = |65 - 50| = |15| = 15. max_words=80: 15 <= 80 → PASSES.",

    "h025": "Yes, the optimizer CAN re-propose it. The evidence threshold is met: 'at least 3 subsequent rollouts showing the failure pattern.' Iters 3, 4, and 5 all showed the same failure — that's exactly 3 minibatches of new evidence since the rejection at iter 2. The edit.json must contain a rationale explaining why a retry is warranted, citing the accumulated evidence from the 3 subsequent rollouts that demonstrate the persistent failure pattern.",

    "h026": "In the three static modes (proposed-ratified, autonomous, user-suite), the holdout split is formed ONCE at init and stays fixed forever. In `live` mode, the split uses a rolling window: the most recent holdout_fraction of logged tasks form the current holdout, and earlier tasks become train. This means the holdout CHANGES over time as new real tasks arrive. The gate operates on whatever the current rolling holdout is, so the acceptance threshold shifts as new tasks enter the window.",

    "h027": "| Mechanism | Implementation | Deviation |\n| Rollout | Fresh subagent receives {skill text, task} → trajectory.md + score.json | Single-agent analogue: fresh subagent with only skill+task is closest to frozen target; eliminates self-grading |\n| Reflect | Minibatch split into SUCCESS/FAILURE; Optimizer hat reflects separately + reads rejected-edits.md | Paper is explicit about separate reflection — enforced, not optional |\n| Edit budget | max_ops + max_words per iteration; edit.json records ordered ops | Default {max_ops: 3, max_words: 80}; configurable |\n| Held-out Gate | scripts/ledger.py gate computes accept/reject deterministically from ledger.csv | Gate decision is deterministic arithmetic, never an LLM opinion |\n| Memory | memory/rejected-edits.md persists rejected candidates; slow-update policy requires accumulated evidence | Optimizer must consult before edits; established rules need multiple minibatches to overturn |",

    "h028": "Judge calibration computes Spearman rank correlation (ρ) between LLM-judge scores and programmatic scores on any task where both exist. Default threshold is ρ ≥ 0.7. If calibration FAILS (ρ < 0.7): inspect tasks where scores diverge most, revise the judge rubric to be more concrete, consider switching to user-suite mode with user-provided gold answers, and do not trust the optimization run's gains without passing calibration.",

    "h029": "Meeting summarizer rubric:\n\nFailure modes: (1) Missing action items, (2) Incorrect attribution of statements, (3) Summary longer than original, (4) Missing key decisions.\n\nHard constraints (0.0 if violated):\n- Must contain an 'Action Items' section\n- Must not exceed 30% of original word count\n- Must not attribute statements to wrong speakers\n\nSoft quality (0.0-1.0 gradient):\n- Captures main discussion themes (0.3)\n- Action items have owners and deadlines (0.2)\n- Writing is clear and concise (0.2)\n\nA 0.0 response would miss all action items and exceed length. A 1.0 response captures all decisions, correctly attributes all statements, lists action items with owners/deadlines, and is concise.\n\n3 failure modes minimum covered.",

    "h030": "At finalize, judge calibration runs: Spearman ρ between LLM-judge and programmatic scores on dual-scored tasks. If the judge is consistently 0.2 higher, the rank correlation may still be decent if the bias is uniform — but if it's inconsistent (some tasks +0.1, others +0.3), ρ will be low. If ρ < 0.7 threshold: calibration FAILS. This means we cannot trust the optimization gains — the LLM-judge may have guided the optimizer toward changes that score well with the judge but don't reflect real quality. The report should flag this and recommend switching to user-suite mode.",

    "h031": "Config key `edit_references: true` allows references/ to evolve during optimization. With validation_depth=self-contained, the candidate is evaluated as a complete skill packet. When an edit modifies references/loop.md, the candidate bundle includes the full modified SKILL.md + all references (including the edited one) — the rollout subagent receives the entire packet as its 'skill text'. The candidate.md represents the full bundle, not just the SKILL.md file.",

    "h032": "Every candidate from iter 2 onward is REJECTED. The gate requires strictly greater than best_so_far: candidate_mean > best_so_far + 0.0. Since best = 1.000 and candidates also score 1.000, the comparison 1.000 > 1.000 is FALSE (strict, not >=). The run never improves beyond v1. Early stopping fires after patience consecutive rejections. This is a problem because useful train-side edits can never pass the saturated holdout gate. The report should recommend: expand the holdout suite with harder tasks to create headroom for improvement.",

    "h033": "It FAILS the budget check. The net words calculation: words_removed = 200 (old section), words_added = 5 (new sentence). Net = |5 - 200| = 195. max_words=80: 195 > 80 → VIOLATES budget. Even though it's only 1 op (passes max_ops=3), the net words change far exceeds the limit. The edit budget prevents exactly this kind of catastrophic overwrite.",

    "h034": "The rollout subagent should not comply. The frozen-target discipline states that each rollout subagent receives exactly two inputs: the current skill text and the task prompt. Nothing else is passed to the subagent. The subagent has no access to memory/rejected-edits.md — it doesn't exist in its context. This is a contamination attempt: if the task tricks the subagent into using information beyond {skill, task}, it violates the frozen-target discipline that ensures evaluation integrity.",

    "h035": "The accepted version is NOT lost. The key insight is that `decide()` writes the kind=gate row (with decision=accept) to ledger.csv BEFORE returning — and skill/v3.md + current.md were also written before the crash. On resume: read ledger.csv, see the accept decision for c4, check that skill/v3.md exists (it does), detect that memory/accepted-log.md wasn't updated. Resume protocol step 4: 'If gating completed but no memory update: apply memory update.' The system completes the memory write and continues.",

    "h036": "When the FAILURE set is empty (all 6 tasks scored 1.0), Reflect has no failures to analyze. The Reflect phase can still analyze the SUCCESS set to identify what the skill is doing well (reinforce patterns). However, for the Edit phase: with no failures, there may be no signal for improvement on this minibatch. The optimizer might reasonably skip proposing an edit this iteration (produce no candidate). The next iteration samples different train tasks that may contain failures. This is fine — not every iteration needs to produce an edit.",

    "h037": "Failure modes for git-commit-message-writer:\n1. Wrong conventional-commit prefix (feat vs fix vs chore) — programmatic check: regex match against prefix enum\n2. Message too long (exceeds 72 char subject line) — programmatic check: len(first_line) <= 72\n3. Describes HOW not WHY (implementation details instead of intent) — LLM-judge: rubric scores intent vs implementation language\n4. Missing scope for breaking changes — programmatic check: contains 'BREAKING CHANGE' footer or '!' suffix when diff modifies public API\n\nHoldout split: stratify by failure mode — ensure each mode has at least 1 task in holdout so the gate tests all dimensions. With 30% holdout on 4 failure modes × 3 tasks each = 12 tasks → 4 holdout, 8 train.",

    "h038": "Before running optimization on a skill scoring 0.95:\n1. ADD HARDER TASKS to the suite: Current tasks are too easy — the skill barely has failure modes to exploit. Following rubrics.md, you need baseline accuracy around 40-60% for headroom. Add edge cases, adversarial inputs, and multi-step scenarios.\n2. IDENTIFY remaining failure modes: The 5% that fails — analyze those specific tasks. What pattern do they share? Design new tasks that stress that pattern.\n3. EXPAND the holdout: With only 5% failure rate, the holdout likely saturates at 1.0 immediately, preventing any candidate from being accepted. Need more holdout tasks covering the hard cases.\n4. Consider whether the skill is already good enough and optimization isn't needed.",

    "h039": "edit_panel=1 vs edit_panel=5 tradeoffs:\n- Compute cost: With serial execution, panel=5 means 5× the holdout rollouts per iteration (5 candidates × holdout_size tasks). Much slower per iteration.\n- Diversity: Panel=5 explores more of the edit space per iteration — better for finding good edits when the search space is large. Panel=1 relies on sequential refinement.\n- Early stopping risk: Panel=5 has 5 chances to beat holdout each round, so less likely to trigger early_stop_patience. Panel=1 might stop early even if a good edit exists in unexplored directions.\n- Memory pollution: Panel=5 adds up to 4 rejected edits to rejected-edits.md per iteration (4 losers). Over 12 iterations that's 48 rejected entries — makes the memory file noisy and harder for the optimizer to parse. Panel=1 adds at most 1 per iteration.",

    "h040": "Proposed schedule: Start with edit_budget={max_ops: 5, max_words: 150} for iterations 1-3 (exploration phase), then decay to {max_ops: 3, max_words: 80} for iterations 4-8 (refinement), then {max_ops: 2, max_words: 40} for iterations 9+ (polishing). Justification: Early iterations need aggressive exploration because the skill likely has obvious gaps that require substantial additions. Underfitting risk is high early — you need to add missing rules quickly. Later iterations risk catastrophic overwrites of rules that already work. Small edits preserve established gains while allowing fine-tuning. This mirrors learning rate decay: large steps early to escape bad basins, small steps late to converge.",

    "h041": "With 20 train tasks and minibatch_size=6: tasks per epoch = 20. Iterations per epoch = ceil(20/6) = 4 (first 3 batches use 6 tasks, 4th uses remaining 2... actually no, it's sequential without replacement). 20/6 = 3.33 iterations to exhaust one epoch. In 12 iterations: 12 / 3.33 = 3.6 complete epochs. The second epoch starts at iteration 4 (after sampling all 20 tasks in iters 1-3 with some spillover: iter1=6, iter2=6, iter3=6 uses 18, iter4 starts with remaining 2 + reshuffles for new epoch).",

    "h042": "This is classic judge drift in autonomous mode. The LLM-judge was generated without user validation of the rubric, and for a subjective task like poetry, the judge's scoring criteria likely don't match human preferences. Diagnosis: The programmatic checker cannot mechanically verify poetry quality (no ground truth), so the system relies entirely on the LLM-judge. With feedback_source=autonomous, there's no human check on the rubric's validity. The judge may reward structural patterns (rhyme, meter) that don't correlate with actual quality. Fix: Switch to user-suite or live mode where human judgment is the signal. Run judge calibration — it would likely fail since there's no programmatic ground truth to calibrate against.",

    "h043": "This reasoning is INCORRECT. The optimizer is overgeneralizing from specific rejections. Each rejected edit was rejected for its specific holdout performance, not because 'examples are bad.' The slow-update policy says edits need 'new evidence from ≥3 subsequent rollouts showing the failure pattern it was meant to fix' — this is per-edit, not per-category. Different example additions might have failed for different reasons: wrong examples, too many words, targeting the wrong failure mode, or simply holdout saturation. The optimizer should evaluate each potential edit on its own merits with fresh evidence.",

    "h044": "The exact expression in decide():\n```python\naccept = cand is not None and (best_score is None or cand > best_score + margin)\n```\nThe 'cand is not None' check comes first because holdout_mean() returns None if no holdout eval rows exist for that candidate version. This happens when: (a) the version label was mismatched (case sensitivity), (b) holdout rollouts weren't recorded yet, or (c) the candidate was never evaluated. Without this guard, comparing None > float would raise a TypeError."
}

# Partial-credit responses: answers that have some right elements but are incomplete or partially wrong
partial_resp = {
    "h000": "SETUP creates config.yml and tasks/train and holdout. The skill v0 is saved.",  # Missing counts, ledger
    "h006": "c1 was rejected because it scored lower than baseline.",  # Right conclusion but no arithmetic shown
    "h017": "c2 is rejected, c3 is accepted because it scores higher.",  # Right answer but no math
    "h032": "All candidates are rejected because they tie the best score.",  # Right but no explanation of problem/recommendation
}

# Worst-case junk
worst_resp = {tid: "I don't know the answer to this question." for tid in gold_resp}

by_id = {t["id"]: t for t in SUITE["tasks"]}


def run_tests():
    print("=" * 60)
    print("HARD-V1 SUITE SELFTEST")
    print("=" * 60)

    # Test gold responses
    print(f"\n--- Gold responses (target: >= 0.85) ---")
    gold_scores = []
    gold_failures = []
    for tid, resp in sorted(gold_resp.items()):
        if tid not in by_id:
            print(f"  SKIP {tid} (not in suite)")
            continue
        s = score_one(by_id[tid]["check"], resp)
        gold_scores.append(s)
        if s < 0.85:
            gold_failures.append((tid, s))

    gold_mean = sum(gold_scores) / len(gold_scores) if gold_scores else 0
    print(f"  Gold mean: {gold_mean:.3f}")
    print(f"  Gold pass (>=0.85): {len(gold_scores) - len(gold_failures)}/{len(gold_scores)}")
    for tid, s in gold_failures:
        print(f"    FAIL {tid}: {s:.3f}")
        # Show which criteria failed
        check = by_id[tid]["check"]
        if check["type"] == "multi_criterion":
            for i, c in enumerate(check["criteria"]):
                cs = score_one(c["check"], gold_resp[tid])
                if cs < 1.0:
                    print(f"      criterion[{i}] ({c['check']['type']}): {cs:.3f}")

    # Test worst-case responses
    print(f"\n--- Worst-case responses (target: <= 0.15) ---")
    worst_scores = []
    worst_leaks = []
    for tid, resp in sorted(worst_resp.items()):
        if tid not in by_id:
            continue
        s = score_one(by_id[tid]["check"], resp)
        worst_scores.append(s)
        if s > 0.15:
            worst_leaks.append((tid, s))

    worst_mean = sum(worst_scores) / len(worst_scores) if worst_scores else 0
    print(f"  Worst mean: {worst_mean:.3f}")
    print(f"  Worst clean (<=0.15): {len(worst_scores) - len(worst_leaks)}/{len(worst_scores)}")
    for tid, s in worst_leaks:
        print(f"    LEAK {tid}: {s:.3f}")

    # Test partial responses
    print(f"\n--- Partial responses (target: 0.3-0.7) ---")
    for tid, resp in sorted(partial_resp.items()):
        if tid not in by_id:
            continue
        s = score_one(by_id[tid]["check"], resp)
        status = "OK" if 0.25 <= s <= 0.75 else "MISCALIBRATED"
        print(f"  {tid}: {s:.3f} [{status}]")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"  Gold mean score:  {gold_mean:.3f} (target >= 0.90)")
    print(f"  Gold failures:    {len(gold_failures)}")
    print(f"  Worst mean score: {worst_mean:.3f} (target <= 0.10)")
    print(f"  Worst leaks:      {len(worst_leaks)}")
    print(f"{'=' * 60}")

    return len(gold_failures) == 0 and len(worst_leaks) == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
