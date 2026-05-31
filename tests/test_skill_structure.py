import yaml
from pathlib import Path

SKILL = Path("skill/SKILL.md")

def _frontmatter(p):
    return yaml.safe_load(p.read_text().split("---")[1])

def test_skill_frontmatter_valid():
    fm = _frontmatter(SKILL)
    assert fm["name"] == "skill-opt"
    assert "optimiz" in fm["description"].lower() or "optimis" in fm["description"].lower()

def test_skill_documents_the_five_phases():
    body = SKILL.read_text().lower()
    for phase in ["rollout", "reflect", "edit", "gate", "memory"]:
        assert phase in body, f"missing phase: {phase}"

def test_skill_references_exist():
    body = SKILL.read_text()
    for ref in ["references/loop.md", "references/fidelity.md",
                "references/feedback-sources.md", "references/rubrics.md"]:
        assert ref in body, f"SKILL.md must point to {ref}"
