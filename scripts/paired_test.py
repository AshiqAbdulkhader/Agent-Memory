"""Exact McNemar test between two methods on per-question correctness (results/*_perq.json)."""

import json
import sys
from math import comb


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def main(path: str, a: str, b: str):
    d = json.load(open(path))
    qa, qb = d[a], d[b]
    keys = sorted(set(qa) & set(qb))
    wins = sum(qa[k] and not qb[k] for k in keys)
    losses = sum(qb[k] and not qa[k] for k in keys)
    acc_a = sum(qa[k] for k in keys) / len(keys)
    acc_b = sum(qb[k] for k in keys) / len(keys)
    print(f"{a} {acc_a:.3f} vs {b} {acc_b:.3f} (n={len(keys)}): {a}-only correct {wins}, {b}-only {losses}, "
          f"exact McNemar p={mcnemar_exact(wins, losses):.4f}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
