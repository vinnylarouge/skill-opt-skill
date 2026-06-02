"""Build a single-string skill packet (SKILL.md + references inlined) for rollout subagents.

Reads either:
  - current.md + references_vN/ from a versioned snapshot dir, OR
  - the live skill/ tree (default).

Writes to .skill-opt/runs/skill-opt-1/skill/packet_<label>.md
"""
import argparse
from pathlib import Path

RUN = Path(__file__).resolve().parents[1]

def build(skill_md: Path, refs_dir: Path) -> str:
    out = []
    out.append("=" * 78)
    out.append("SKILL.md")
    out.append("=" * 78)
    out.append(skill_md.read_text())
    if refs_dir.exists():
        for ref in sorted(refs_dir.glob("*.md")):
            out.append("\n" + "=" * 78)
            out.append(f"references/{ref.name}")
            out.append("=" * 78)
            out.append(ref.read_text())
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True, help="path to SKILL.md (e.g. skill/current.md)")
    ap.add_argument("--refs", required=True, help="path to references/ dir")
    ap.add_argument("--label", required=True, help="output label, e.g. v0 or c1")
    args = ap.parse_args()

    skill_md = Path(args.skill)
    refs_dir = Path(args.refs)
    packet = build(skill_md, refs_dir)
    out_path = RUN / "skill" / f"packet_{args.label}.md"
    out_path.write_text(packet)
    print(f"wrote {out_path} ({len(packet)} chars)")

if __name__ == "__main__":
    main()
