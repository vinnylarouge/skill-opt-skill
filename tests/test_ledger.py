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
