import calibration

def test_perfect_monotonic_is_one():
    assert abs(calibration.spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-9

def test_reversed_is_minus_one():
    assert abs(calibration.spearman([1, 2, 3, 4], [40, 30, 20, 10]) + 1.0) < 1e-9

def test_handles_ties():
    assert calibration.spearman([1, 2, 3], [5, 5, 5]) == 0.0
