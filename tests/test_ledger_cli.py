import subprocess, sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "skill/scripts/ledger.py"

def _run(*args):
    return subprocess.run([sys.executable, str(LEDGER), *args],
                          capture_output=True, text=True, check=True).stdout.strip()

def test_cli_record_and_best(tmp_path):
    _run("record", "--run", str(tmp_path), "--iter", "0",
         "--version", "v0", "--split", "holdout", "--scores", "0.4,0.6")
    assert _run("best", "--run", str(tmp_path)) == "v0 0.500000"

def test_cli_gate(tmp_path):
    _run("record", "--run", str(tmp_path), "--iter", "0", "--version", "v0",
         "--split", "holdout", "--scores", "0.5")
    _run("record", "--run", str(tmp_path), "--iter", "1", "--version", "c1",
         "--split", "holdout", "--scores", "0.8")
    out = _run("gate", "--run", str(tmp_path), "--iter", "1", "--candidate", "c1")
    assert out.startswith("accept")

def test_cli_gate_reject(tmp_path):
    _run("record", "--run", str(tmp_path), "--iter", "0", "--version", "v0",
         "--split", "holdout", "--scores", "0.5")
    _run("record", "--run", str(tmp_path), "--iter", "1", "--version", "c1",
         "--split", "holdout", "--scores", "0.5")
    out = _run("gate", "--run", str(tmp_path), "--iter", "1", "--candidate", "c1")
    assert out == "reject v0 0.500000"

def test_cli_best_empty(tmp_path):
    assert _run("best", "--run", str(tmp_path)) == "None None"
