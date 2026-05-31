import split

def test_split_is_deterministic():
    a = split.train_holdout("playground/data/tasks.json", holdout_fraction=0.3, seed=0)
    b = split.train_holdout("playground/data/tasks.json", holdout_fraction=0.3, seed=0)
    assert [t["id"] for t in a[0]] == [t["id"] for t in b[0]]
    assert [t["id"] for t in a[1]] == [t["id"] for t in b[1]]

def test_split_partitions_without_overlap():
    train, holdout = split.train_holdout("playground/data/tasks.json", 0.3, seed=0)
    ids_train = {t["id"] for t in train}
    ids_hold = {t["id"] for t in holdout}
    assert ids_train.isdisjoint(ids_hold)
    assert len(ids_train) + len(ids_hold) >= 18
    assert len(ids_hold) >= 1

def test_gold_scores_perfectly_against_itself():
    import checker
    fields, tasks = split.load("playground/data/tasks.json")
    for t in tasks:
        s, correct = checker.score_fields(t["gold"], t["gold"], fields)
        assert s == 1.0, f"{t['id']} gold not self-consistent: {correct}"
