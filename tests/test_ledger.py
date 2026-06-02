import pytest
import ledger

def test_append_eval_then_holdout_mean(tmp_path):
    run = tmp_path
    ledger.append_eval(run, iter=0, version="v0", split="holdout", scores=[0.4, 0.6, 0.5])
    assert abs(ledger.holdout_mean(run, "v0") - 0.5) < 1e-9

def test_holdout_mean_missing_returns_none(tmp_path):
    assert ledger.holdout_mean(tmp_path, "v0") is None

def test_latest_eval_wins(tmp_path):
    run = tmp_path
    ledger.append_eval(run, 0, "v0", "holdout", [0.2])
    ledger.append_eval(run, 5, "v0", "holdout", [0.9])
    assert abs(ledger.holdout_mean(run, "v0") - 0.9) < 1e-9

def test_best_with_only_baseline(tmp_path):
    ledger.append_eval(tmp_path, 0, "v0", "holdout", [0.5])
    assert ledger.best(tmp_path) == ("v0", 0.5)

def test_accepted_versions_starts_with_v0(tmp_path):
    assert ledger.accepted_versions(tmp_path) == ["v0"]

def _setup_v0(run, score):
    ledger.append_eval(run, 0, "v0", "holdout", [score])

def test_decide_accepts_when_candidate_beats_best(tmp_path):
    _setup_v0(tmp_path, 0.5)
    ledger.append_eval(tmp_path, 1, "c1", "holdout", [0.7])
    outcome, version, score = ledger.decide(tmp_path, 1, "c1", margin=0.0)
    assert outcome == "accept" and version == "c1" and abs(score - 0.7) < 1e-9

def test_decide_rejects_when_candidate_not_better(tmp_path):
    _setup_v0(tmp_path, 0.5)
    ledger.append_eval(tmp_path, 1, "c1", "holdout", [0.5])  # tie -> reject
    outcome, version, score = ledger.decide(tmp_path, 1, "c1", margin=0.0)
    assert outcome == "reject" and version == "v0" and abs(score - 0.5) < 1e-9

def test_margin_must_be_exceeded(tmp_path):
    _setup_v0(tmp_path, 0.5)
    ledger.append_eval(tmp_path, 1, "c1", "holdout", [0.54])
    outcome, _, _ = ledger.decide(tmp_path, 1, "c1", margin=0.05)
    assert outcome == "reject"

def test_accepted_candidate_becomes_eligible_best(tmp_path):
    _setup_v0(tmp_path, 0.5)
    ledger.append_eval(tmp_path, 1, "c1", "holdout", [0.7])
    ledger.decide(tmp_path, 1, "c1", margin=0.0)
    assert ledger.best(tmp_path) == ("c1", 0.7)

def test_append_eval_empty_scores_raises(tmp_path):
    with pytest.raises(ValueError):
        ledger.append_eval(tmp_path, 0, "v0", "holdout", [])
