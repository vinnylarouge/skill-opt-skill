"""Build a run directory from the hard-v1 suite, ready for skill-opt execution.

Usage: python scripts/build_packet.py [--run-name NAME]

Creates .skill-opt/runs/<NAME>/ with:
  - config.yml (dogfood config pointing at skill/SKILL.md)
  - tasks/suite.json, tasks/train/tasks.json, tasks/holdout/tasks.json
  - scripts/checker.py (copied from this suite)
  - skill/v0.md (snapshot of current SKILL.md + references)
"""
import argparse
import json
import shutil
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SUITE_DIR.parents[1].parent  # .skill-opt/suites/hard-v1 → project root
RUNS_DIR = PROJECT_ROOT / ".skill-opt" / "runs"


def build(run_name: str):
    run_dir = RUNS_DIR / run_name
    if run_dir.exists():
        print(f"ERROR: {run_dir} already exists. Choose a different name.")
        return

    # Create structure
    for d in ["tasks/train", "tasks/holdout", "skill", "scripts",
              "rollouts", "candidates", "memory"]:
        (run_dir / d).mkdir(parents=True)

    # Copy suite and splits
    shutil.copy2(SUITE_DIR / "suite.json", run_dir / "tasks" / "suite.json")
    shutil.copy2(SUITE_DIR / "tasks" / "train" / "tasks.json",
                 run_dir / "tasks" / "train" / "tasks.json")
    shutil.copy2(SUITE_DIR / "tasks" / "holdout" / "tasks.json",
                 run_dir / "tasks" / "holdout" / "tasks.json")

    # Copy checker
    shutil.copy2(SUITE_DIR / "scripts" / "checker.py", run_dir / "scripts" / "checker.py")
    shutil.copy2(SUITE_DIR / "scripts" / "selftest.py", run_dir / "scripts" / "selftest.py")
    shutil.copy2(SUITE_DIR / "scripts" / "split.py", run_dir / "scripts" / "split.py")

    # Snapshot skill/v0.md — concatenate SKILL.md + references
    skill_dir = PROJECT_ROOT / "skill"
    skill_md = (skill_dir / "SKILL.md").read_text()
    refs_content = []
    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        for ref_file in sorted(refs_dir.glob("*.md")):
            refs_content.append(f"\n\n---\n# [Reference: {ref_file.name}]\n\n")
            refs_content.append(ref_file.read_text())

    v0_content = skill_md + "".join(refs_content)
    (run_dir / "skill" / "v0.md").write_text(v0_content)
    (run_dir / "skill" / "current.md").write_text(v0_content)

    # Write config.yml
    config = f"""target_skill: skill/SKILL.md
edit_references: true
feedback_source: autonomous
feedback_timing: autonomous
output_mode: save-as-new
max_iterations: 6
early_stop_patience: 3
edit_budget: {{max_ops: 3, max_words: 80}}
minibatch_size: 6
holdout_fraction: 0.3
gate_margin: 0.0
checkpoint_every: 1
parallelism: 6
edit_panel: 1
validation_depth: self-contained
# Suite: hard-v1 ({json.loads((SUITE_DIR / 'suite.json').read_text())['total']} tasks, {len(json.loads((run_dir / 'tasks/holdout/tasks.json').read_text()))} holdout)
"""
    (run_dir / "config.yml").write_text(config)

    # Initialize empty memory files
    (run_dir / "memory" / "rejected-edits.md").write_text("# Rejected Edits\n\n")
    (run_dir / "memory" / "accepted-log.md").write_text("# Accepted Edits Log\n\n")

    print(f"Built run directory: {run_dir}")
    print(f"  Suite: {SUITE_DIR / 'suite.json'}")
    print(f"  Tasks: 45 total ({len(json.loads((run_dir / 'tasks/train/tasks.json').read_text()))} train, {len(json.loads((run_dir / 'tasks/holdout/tasks.json').read_text()))} holdout)")
    print(f"  Skill snapshot: {run_dir / 'skill/v0.md'}")
    print(f"\nTo start: invoke skill-opt on {run_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", default="skill-opt-hard-1",
                    help="Name for the run directory")
    args = ap.parse_args()
    build(args.run_name)
