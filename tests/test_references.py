import yaml
from pathlib import Path

def test_config_template_has_all_keys():
    cfg = yaml.safe_load(Path("skill/templates/config.yml").read_text())
    required = {"target_skill", "edit_references", "feedback_source", "feedback_timing",
               "output_mode", "max_iterations", "early_stop_patience", "edit_budget",
               "minibatch_size", "holdout_fraction", "checkpoint_every", "parallelism",
               "edit_panel", "validation_depth"}
    assert required.issubset(cfg.keys())

def test_fidelity_maps_all_five_mechanisms():
    body = Path("skill/references/fidelity.md").read_text().lower()
    for m in ["rollout", "reflect", "edit budget", "held-out", "memory"]:
        assert m in body

def test_feedback_sources_documents_four_modes():
    body = Path("skill/references/feedback-sources.md").read_text().lower()
    for m in ["proposed-ratified", "autonomous", "user-suite", "live"]:
        assert m in body
