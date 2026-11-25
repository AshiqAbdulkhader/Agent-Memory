"""Observable features for (query, memory item) pairs and query-free item features.

Observability rule (after OSL-MR): features use only what is available at decision time — the query
text, stored items and their metadata — never gold evidence or answers.
"""

from __future__ import annotations

import math
import re

import numpy as np

from memctl.store import MemoryStore, embed, extract_keys

_WHEN = re.compile(r"\b(when|what (year|month|date|day|time)|how long|since when|what date)\b", re.I)
_COUNT = re.compile(r"\bhow (many|much|often)\b", re.I)
_WHO = re.compile(r"\bwho\b", re.I)
_WHY = re.compile(r"\bwhy\b", re.I)
_LIST = re.compile(r"\b(what (are|were)|which|what (kinds?|types?)|what (activities|things|books|events))\b", re.I)
_WOULD = re.compile(r"\b(would|likely|might|could|probably)\b", re.I)
_NUM = re.compile(r"\d")
_DATEWORD = re.compile(
    r"\b(yesterday|last (week|month|year|weekend|night)|next (week|month|year)|ago|monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|"
    r"november|december|\d{4})\b",
    re.I,
)

QUERY_FEATURES = ["q_when", "q_count", "q_who", "q_why", "q_list", "q_would", "q_len"]
ITEM_FEATURES = ["i_len", "i_fact", "i_pos", "i_image", "i_num", "i_dateword", "i_nkeys", "i_keyidf", "i_question"]
PAIR_FEATURES = [
    "dense", "dense_z", "dense_pct", "bm25", "bm25_pct", "ppr", "key_overlap", "key_idf_overlap",
    "speaker_match", "nbr_dense", "sess_dense",
]
BUDGET_FEATURES = ["b_log", "tok_frac"]
FEATURES = QUERY_FEATURES + ITEM_FEATURES + PAIR_FEATURES + BUDGET_FEATURES
N_FEATURES = len(FEATURES)


def _pct(x: np.ndarray) -> np.ndarray:
    if len(x) <= 1:
        return np.ones_like(x)
    return (np.argsort(np.argsort(x)) / (len(x) - 1)).astype(np.float32)


def query_features(q: str) -> np.ndarray:
    return np.array(
        [bool(p.search(q)) for p in (_WHEN, _COUNT, _WHO, _WHY, _LIST, _WOULD)] + [math.log1p(len(q.split())) / 4],
        np.float32,
    )


def item_features(store: MemoryStore) -> np.ndarray:
    items = store.items
    n_sess = max((it.session for it in items), default=1)
    rows = []
    for it in items:
        idf = [math.log(1 + len(items) / (1 + store.key_degree(k))) for k in it.keys]
        rows.append(
            [
                math.log1p(it.n_tokens) / 5,
                it.kind == "fact",
                it.session / n_sess,
                "[shares a photo" in it.text,
                bool(_NUM.search(it.text)),
                bool(_DATEWORD.search(it.text.split("] ", 1)[-1])),
                math.log1p(len(it.keys)) / 3,
                (sum(idf) / len(idf) / 5) if idf else 0.0,
                "?" in it.text,
            ]
        )
    return np.asarray(rows, np.float32).reshape(len(items), len(ITEM_FEATURES))


def pair_features(store: MemoryStore, q: str, qvec: np.ndarray | None = None) -> np.ndarray:
    items = store.items
    n = len(items)
    if qvec is None:
        qvec = embed([q], query=True)[0]
    dense = store.dense_scores(qvec)
    bm25 = store.bm25_scores(q)
    qkeys = extract_keys([q])[0]
    ppr = store.ppr_scores(qkeys) * n
    ql = q.lower()
    # neighbour / session context: best dense score among adjacent items and within the same session
    nbr = np.zeros(n, np.float32)
    sess_best: dict[int, float] = {}
    for i, it in enumerate(items):
        sess_best[it.session] = max(sess_best.get(it.session, -1.0), float(dense[i]))
        for j in (i - 1, i + 1):
            if 0 <= j < n and items[j].session == it.session:
                nbr[i] = max(nbr[i], dense[j])
    rows = []
    for i, it in enumerate(items):
        shared = qkeys & it.keys
        rows.append(
            [
                len(shared),
                sum(math.log(1 + n / (1 + store.key_degree(k))) for k in shared) / 10,
                it.speaker.lower() in ql,
                nbr[i],
                sess_best[it.session],
            ]
        )
    extra = np.asarray(rows, np.float32).reshape(n, 5)
    z = (dense - dense.mean()) / (dense.std() + 1e-6)
    return np.column_stack(
        [
            dense,
            z / 3,
            _pct(dense),
            bm25 / (bm25.max() + 1e-6),
            _pct(bm25),
            np.log1p(ppr),
            np.log1p(extra[:, 0]),
            extra[:, 1],
            extra[:, 2],
            extra[:, 3],
            extra[:, 4],
        ]
    ).astype(np.float32)


def budget_features(store: MemoryStore, budget: int) -> np.ndarray:
    toks = np.array([it.n_tokens for it in store.items], np.float32)
    return np.column_stack([np.full(len(toks), math.log2(budget) / 12, np.float32), np.minimum(toks / budget, 1.0)])


def build_features(store: MemoryStore, q: str, base_item: np.ndarray | None = None) -> np.ndarray:
    """Budget-free features [N, F - 2]; budget columns are appended per budget by `with_budget`."""
    if base_item is None:
        base_item = item_features(store)
    qf = np.broadcast_to(query_features(q), (len(store), len(QUERY_FEATURES)))
    return np.concatenate([qf, base_item, pair_features(store, q)], axis=1)


def with_budget(x: np.ndarray, store: MemoryStore, budget: int) -> np.ndarray:
    return np.concatenate([x, budget_features(store, budget)], axis=1)
