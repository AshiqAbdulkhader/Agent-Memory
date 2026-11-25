"""Query-free retention features and streaming eviction under a storage budget B_store (tokens).

Retention is decided before any question is known (pre-query, as in EMBER/OSL-MR), so features are
query-free: item metadata plus how the item relates to the rest of memory (redundancy, key novelty).
"""

from __future__ import annotations

import math

import numpy as np

from memctl.features import item_features
from memctl.store import MemoryStore

RET_FEATURES = ["i_len", "i_fact", "i_pos", "i_image", "i_num", "i_dateword", "i_nkeys", "i_keyidf", "i_question",
                "age", "redundancy", "key_novel", "speaker_share", "pressure", "b_store_log"]
N_RET_FEATURES = len(RET_FEATURES)


def retention_features(store: MemoryStore, now_session: int, b_store: int) -> np.ndarray:
    items = store.items
    n = len(items)
    base = item_features(store)
    emb = store.embeddings
    sim = emb @ emb.T
    np.fill_diagonal(sim, -1.0)
    redundancy = sim.max(1) if n > 1 else np.zeros(n)
    novel = np.array([np.mean([store.key_degree(k) == 1 for k in it.keys]) if it.keys else 0.0 for it in items])
    spk = [it.speaker for it in items]
    share = np.array([spk.count(s) / n for s in spk])
    age = np.array([math.log1p(now_session - it.session) / 3 for it in items])
    pressure = min(store.total_tokens / b_store, 4.0) / 4
    extra = np.column_stack([age, redundancy, novel, share, np.full(n, pressure), np.full(n, math.log2(b_store) / 16)])
    return np.concatenate([base, extra], 1).astype(np.float32)


def heuristic_retention_score(name: str, x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Higher = keep. x = retention_features matrix."""
    f = {k: i for i, k in enumerate(RET_FEATURES)}
    if name == "fifo":  # keep most recent (MemGPT FIFO queue / sliding window)
        return x[:, f["i_pos"]] + 1e-3 * rng.random(len(x))
    if name == "random":
        return rng.random(len(x))
    if name == "redundancy":  # evict the most redundant first (Megagon audit's redundancy-aware policy)
        return -x[:, f["redundancy"]]
    if name == "importance":  # Selective-Forgetting-style hand-weighted importance: recency + key richness/idf
        return 0.35 * x[:, f["i_pos"]] + 0.25 * x[:, f["i_nkeys"]] + 0.2 * x[:, f["i_keyidf"]] + 0.2 * x[:, f["i_num"]]
    raise ValueError(name)


RETENTION_BASELINES = ["fifo", "random", "redundancy", "importance"]


def stream_with_eviction(sessions_items: list[list], b_store: int, score_fn) -> MemoryStore:
    """Ingest session by session; after each session evict lowest-scored items until within b_store.
    score_fn(store, now_session, b_store) -> np.ndarray of keep-scores."""
    store = MemoryStore()
    for s_idx, items in enumerate(sessions_items, start=1):
        store.add(items)
        if store.total_tokens > b_store:
            keep_scores = score_fn(store, s_idx, b_store)
            order = np.argsort(-keep_scores)
            ntok = np.array([it.n_tokens for it in store.items])
            keep = order[np.cumsum(ntok[order]) <= b_store]
            drop = {store.items[i].id for i in set(range(len(store))) - set(keep.tolist())}
            store.remove(drop)
    return store
