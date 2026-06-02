"""Spearman rank correlation, stdlib only. Used to check the LLM-judge tracks ground truth."""


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((x - mb) ** 2 for x in b) ** 0.5
    if va == 0 or vb == 0:
        return 0.0
    return cov / (va * vb)


def spearman(a, b):
    if len(a) != len(b):
        raise ValueError(f"spearman requires equal-length sequences, got {len(a)} and {len(b)}")
    if len(a) == 0:
        raise ValueError("spearman requires non-empty sequences")
    return _pearson(_ranks(a), _ranks(b))
