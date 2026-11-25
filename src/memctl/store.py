"""Hybrid memory substrate: raw turns (+ optional LLM facts) with provenance, dense + BM25 indices,
and an item-keyword graph for Personalized PageRank.

Everything here is non-generative; the only model used at write time is a local embedder and spaCy.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import networkx as nx
import numpy as np
from rank_bm25 import BM25Okapi

from memctl.tokens import count_tokens

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
EMBED_MODEL = "BAAI/bge-base-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@dataclass
class MemoryItem:
    id: str
    kind: str  # "turn" | "fact"
    text: str
    session: int
    time: datetime
    speaker: str
    sources: list[str]  # provenance: dia_ids this item came from
    n_tokens: int = 0
    keys: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        if not self.n_tokens:
            self.n_tokens = count_tokens(self.text)


# ---------------------------------------------------------------- models


@lru_cache(maxsize=1)
def _embedder():
    import torch
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL, device="cuda" if torch.cuda.is_available() else "cpu")


@lru_cache(maxsize=1)
def _nlp():
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError:  # model is not a PyPI dependency; fetch it on first use
        from spacy.cli import download

        download("en_core_web_sm")
        return spacy.load("en_core_web_sm")


def embed(texts: list[str], query: bool = False) -> np.ndarray:
    """L2-normalised embeddings with an on-disk cache keyed by text hash."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    prefix = QUERY_PREFIX if query else ""
    keys = [hashlib.sha1((EMBED_MODEL + prefix + t).encode()).hexdigest() for t in texts]
    out: list[np.ndarray | None] = [None] * len(texts)
    missing = []
    for i, k in enumerate(keys):
        f = CACHE_DIR / f"{k}.npy"
        if f.exists():
            out[i] = np.load(f)
        else:
            missing.append(i)
    if missing:
        vecs = _embedder().encode(
            [prefix + texts[i] for i in missing], batch_size=64, normalize_embeddings=True, show_progress_bar=False
        )
        for i, v in zip(missing, vecs):
            v = v.astype(np.float32)
            np.save(CACHE_DIR / f"{keys[i]}.npy", v)
            out[i] = v
    return np.stack(out) if out else np.zeros((0, 768), np.float32)


_STOP_KEYS = {"thing", "things", "lot", "time", "way", "day", "today", "yesterday", "week", "something", "anything"}


def extract_keys(texts: list[str], n_process: int = 1) -> list[frozenset[str]]:
    """Keyword keys for the item graph: named entities + proper/common noun lemmas (lower-cased)."""
    keys = []
    for doc in _nlp().pipe(texts, batch_size=128, n_process=n_process):
        k = {e.text.lower() for e in doc.ents if e.label_ not in {"CARDINAL", "ORDINAL"}}
        k |= {t.lemma_.lower() for t in doc if t.pos_ in {"PROPN", "NOUN"} and not t.is_stop and len(t) > 2}
        keys.append(frozenset(k - _STOP_KEYS))
    return keys


def tokenize_bm25(text: str) -> list[str]:
    return [w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(w) > 1]


# ---------------------------------------------------------------- store


class MemoryStore:
    """Ordered collection of MemoryItems with lazily (re)built indices."""

    def __init__(self, items: list[MemoryItem] | None = None):
        self.items: list[MemoryItem] = []
        self._emb = np.zeros((0, 768), np.float32)
        self._dirty = True
        if items:
            self.add(items)

    @classmethod
    def from_parts(cls, items: list[MemoryItem], emb: np.ndarray) -> "MemoryStore":
        """Build from items that already carry keys, with precomputed embeddings (no model calls)."""
        s = cls()
        s.items = list(items)
        s._emb = emb.astype(np.float32)
        return s

    def __len__(self) -> int:
        return len(self.items)

    @property
    def total_tokens(self) -> int:
        return sum(it.n_tokens for it in self.items)

    def add(self, items: list[MemoryItem]) -> None:
        if not items:
            return
        missing = [it for it in items if not it.keys]
        for it, k in zip(missing, extract_keys([it.text for it in missing])):
            it.keys = k
        self.items += items
        self._emb = np.concatenate([self._emb, embed([it.text for it in items])])
        self._dirty = True

    def remove(self, ids: set[str]) -> None:
        keep = [i for i, it in enumerate(self.items) if it.id not in ids]
        self.items = [self.items[i] for i in keep]
        self._emb = self._emb[keep]
        self._dirty = True

    # indices ----------------------------------------------------------
    def _build(self) -> None:
        if not self._dirty:
            return
        self._bm25 = BM25Okapi([tokenize_bm25(it.text) for it in self.items]) if self.items else None
        g = nx.Graph()
        for i, it in enumerate(self.items):
            g.add_node(("i", i))
            for k in it.keys:
                g.add_edge(("i", i), ("k", k))
        self._graph = g
        self._key_deg = {n[1]: g.degree(n) for n in g if n[0] == "k"}
        self._dirty = False

    @property
    def embeddings(self) -> np.ndarray:
        return self._emb

    def dense_scores(self, qvec: np.ndarray) -> np.ndarray:
        return self._emb @ qvec

    def bm25_scores(self, query: str) -> np.ndarray:
        self._build()
        if self._bm25 is None:
            return np.zeros(0)
        return np.asarray(self._bm25.get_scores(tokenize_bm25(query)), dtype=np.float32)

    def ppr_scores(self, qkeys: frozenset[str], alpha: float = 0.85) -> np.ndarray:
        """Personalized PageRank over the item-keyword graph seeded at the query's keys (HippoRAG-style,
        seeds weighted by inverse key degree)."""
        self._build()
        seeds = {("k", k): 1.0 / self._key_deg[k] for k in qkeys if k in self._key_deg}
        if not seeds:
            return np.zeros(len(self.items), np.float32)
        pr = nx.pagerank(self._graph, alpha=alpha, personalization=seeds, max_iter=50, tol=1e-5)
        return np.array([pr.get(("i", i), 0.0) for i in range(len(self.items))], np.float32)

    def key_degree(self, key: str) -> int:
        self._build()
        return self._key_deg.get(key, 0)


def turns_to_items(turns) -> list[MemoryItem]:
    return [MemoryItem(t.dia_id, "turn", t.render(), t.session, t.time, t.speaker, [t.dia_id]) for t in turns]
