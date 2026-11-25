"""Public API: budgeted long-term memory for LLM agents.

    from memctl import BudgetedMemory

    mem = BudgetedMemory(store_budget=8192)            # tokens kept in memory
    mem.add("I adopted a puppy named Max", speaker="Alice", time=datetime(2023, 5, 7))
    mem.end_session()                                    # retention runs at session boundaries
    evidence = mem.recall("What is Alice's dog called?", read_budget=256)
    prompt = "\\n".join(evidence)                         # give to any LLM

Retention (what to forget when memory exceeds `store_budget`) and retrieval (what to put into the
`read_budget`) are small learned ranking policies (MLPs) trained with ranking RL on LoCoMo; no LLM call
is made inside the memory. Heuristic fallbacks are used if the weights are unavailable.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import torch

from memctl.baselines import score as heuristic_score
from memctl.budget import pack
from memctl.features import N_FEATURES, build_features, item_features
from memctl.policy import Scorer
from memctl.retention import N_RET_FEATURES, heuristic_retention_score, retention_features
from memctl.store import MemoryItem, MemoryStore

WEIGHTS = Path(__file__).resolve().parent / "weights"


def _load(name: str, n_features: int) -> Scorer | None:
    f = WEIGHTS / f"{name}.pt"
    if not f.exists():
        return None
    m = Scorer(n_features)
    m.load_state_dict(torch.load(f, map_location="cpu"))
    return m.eval()


class BudgetedMemory:
    def __init__(self, store_budget: int | None = 8192, retrieval: str = "learned", retention: str = "learned"):
        self.store_budget = store_budget
        self.store = MemoryStore()
        self._pending: list[MemoryItem] = []
        self._session = 0
        self._n = 0
        self.retrieval_model = _load("retrieval", N_FEATURES) if retrieval == "learned" else None
        self.retention_model = _load("retention", N_RET_FEATURES) if retention == "learned" else None

    # ------------------------------------------------------------ write
    def add(self, text: str, speaker: str = "user", time: datetime | None = None, kind: str = "turn",
            source_id: str | None = None) -> str:
        """Buffer one message (or fact) for the current session; returns its memory id."""
        time = time or datetime.now()
        self._n += 1
        mid = source_id or f"m{self._n}"
        rendered = f"[{time:%d %B %Y}] {speaker}: {text}" if kind == "turn" else f"[{time:%d %B %Y}] {text}"
        self._pending.append(MemoryItem(mid, kind, rendered, self._session + 1, time, speaker, [mid]))
        return mid

    def end_session(self) -> None:
        """Commit buffered items and, if over budget, evict the lowest-ranked items."""
        self._session += 1
        self.store.add(self._pending)
        self._pending = []
        if self.store_budget and self.store.total_tokens > self.store_budget:
            keep = self._keep_scores()
            order = np.argsort(-keep)
            ntok = np.array([it.n_tokens for it in self.store.items])
            kept = set(order[np.cumsum(ntok[order]) <= self.store_budget].tolist())
            self.store.remove({it.id for i, it in enumerate(self.store.items) if i not in kept})

    def _keep_scores(self) -> np.ndarray:
        x = retention_features(self.store, self._session, self.store_budget)
        if self.retention_model is None:
            return heuristic_retention_score("redundancy", x, np.random.default_rng(0))
        x[:, -2:] = 0.0
        with torch.no_grad():
            return self.retention_model(torch.tensor(x)).numpy()

    # ------------------------------------------------------------ read
    def recall(self, question: str, read_budget: int = 512) -> list[str]:
        """Evidence snippets (chronological) that fit in `read_budget` tokens."""
        if self._pending:
            self.end_session()
        if not len(self.store):
            return []
        x = build_features(self.store, question, item_features(self.store)).astype(np.float32)
        ntok = np.array([it.n_tokens for it in self.store.items])
        if self.retrieval_model is None:
            order = np.argsort(-heuristic_score("hybrid_rrf", x))
        else:
            xt = np.concatenate([x, np.zeros((len(x), 2), np.float32)], 1)
            xt[:, -2] = np.log2(read_budget) / 12
            xt[:, -1] = np.minimum(ntok / read_budget, 1.0)
            with torch.no_grad():
                order = torch.argsort(self.retrieval_model(torch.tensor(xt)), descending=True).numpy()
        return [self.store.items[i].text for i in sorted(pack(order, ntok, read_budget))]

    @property
    def tokens(self) -> int:
        return self.store.total_tokens

    def __len__(self) -> int:
        return len(self.store)
