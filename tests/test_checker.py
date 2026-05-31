import checker

FIELDS = ["name", "date", "amount", "note"]

def test_exact_match_scores_one():
    gold = {"name": "Acme", "date": "2026-01-03", "amount": 99.5, "note": None}
    pred = {"name": "Acme", "date": "2026-01-03", "amount": 99.5, "note": None}
    score, _ = checker.score_fields(pred, gold, FIELDS)
    assert score == 1.0

def test_one_wrong_of_four():
    gold = {"name": "Acme", "date": "2026-01-03", "amount": 99.5, "note": None}
    pred = {"name": "Acme", "date": "2026-01-03", "amount": 12.0, "note": None}
    score, correct = checker.score_fields(pred, gold, FIELDS)
    assert score == 0.75 and correct["amount"] is False

def test_date_normalization():
    score, _ = checker.score_fields({"date": "2026-1-3"}, {"date": "2026-01-03"}, ["date"])
    assert score == 1.0

def test_currency_and_commas_normalized():
    score, _ = checker.score_fields({"amount": "$1,299.00"}, {"amount": 1299.0}, ["amount"])
    assert score == 1.0

def test_null_for_missing():
    score, _ = checker.score_fields({}, {"note": None}, ["note"])
    assert score == 1.0
