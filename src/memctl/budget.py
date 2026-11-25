"""Budgeted packing and evidence metrics.

Packing is prefix packing: walk the ranking and keep items while the running token total stays within
the budget (the first item that would overflow ends the selection). This matches the top-b semantics of
ranking-based eviction (KVP) and is vectorisable for RL training.
"""

from __future__ import annotations

import numpy as np
import torch

BUDGETS = (64, 128, 256, 512, 1024, 2048)


def pack(order: np.ndarray, n_tokens: np.ndarray, budget: int) -> np.ndarray:
    csum = np.cumsum(n_tokens[order])
    return order[csum <= budget]


def recall_batch(perms: torch.Tensor, n_tokens: torch.Tensor, cover: torch.Tensor, budget: int) -> torch.Tensor:
    """perms [K, N] item orders; n_tokens [N]; cover [N, E] bool -> evidence recall per permutation [K]."""
    csum = torch.cumsum(n_tokens[perms], dim=-1)
    keep = torch.zeros_like(perms, dtype=torch.float32).scatter_(1, perms, (csum <= budget).float())
    return ((keep @ cover.float()) > 0).float().mean(-1)


def evidence_recall(selected: np.ndarray, cover: np.ndarray) -> float:
    return float(cover[selected].any(0).mean()) if len(selected) else 0.0
