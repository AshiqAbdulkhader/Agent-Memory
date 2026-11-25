"""Heuristic retrieval rankers (all consume the same feature matrix so they see identical information)."""

from __future__ import annotations

import numpy as np

from memctl.features import FEATURES

_F = {name: i for i, name in enumerate(FEATURES)}


def _rrf(*scores: np.ndarray, k: int = 60) -> np.ndarray:
    out = np.zeros_like(scores[0], dtype=np.float64)
    for s in scores:
        ranks = np.argsort(np.argsort(-s))
        out += 1.0 / (k + ranks + 1)
    return out


def score(name: str, x: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
    """Higher = retrieve first. x is the [N, F] feature matrix (budget columns may be present)."""
    c = lambda f: x[:, _F[f]]  # noqa: E731
    if name == "random":
        return (rng or np.random.default_rng(0)).random(len(x))
    if name == "recency":
        return c("i_pos") + 1e-3 * c("dense")
    if name == "dense":
        return c("dense")
    if name == "bm25":
        return c("bm25") + 1e-3 * c("dense")
    if name == "hybrid_rrf":  # dense + BM25 reciprocal-rank fusion (Zep/SimpleMem/MemoryCPT style)
        return _rrf(c("dense"), c("bm25"))
    if name == "hybrid_ppr":  # + Personalized PageRank over the keyword graph (HippoRAG/Zero-Mem style)
        return _rrf(c("dense"), c("bm25"), c("ppr"))
    if name == "ga_style":  # Generative Agents: normalised relevance + recency (no LLM importance)
        d = c("dense")
        d = (d - d.min()) / (d.max() - d.min() + 1e-6)
        return d + c("i_pos")
    raise ValueError(name)


BASELINES = ["random", "recency", "dense", "bm25", "hybrid_rrf", "hybrid_ppr", "ga_style"]
