"""Budget-conditioned ranking policy trained with ranking RL (after KVP, Moschella et al. 2026).

The scorer maps per-item features (optionally including budget features) to a logit. A Plackett-Luce
distribution over permutations is sampled in parallel with Gumbel-sort; the first `top_m` positions of
each sampled permutation are packed into the budget and scored by a task reward. Gradients use
REINFORCE with a leave-one-out baseline across the K samples of the same query.
"""

from __future__ import annotations

import torch
from torch import nn


class Scorer(nn.Module):
    def __init__(self, n_features: int, hidden: int = 128, context: bool = True):
        super().__init__()
        self.context = context
        d_in = n_features * (2 if context else 1)
        self.net = nn.Sequential(
            nn.Linear(d_in, hidden), nn.GELU(), nn.Linear(hidden, hidden), nn.GELU(), nn.Linear(hidden, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: [N, F] features of all candidate items for one query -> [N] logits.
        With `context`, each item also sees the mean feature vector of the candidate set (a cheap
        permutation-invariant summary of what else is in memory)."""
        if self.context:
            x = torch.cat([x, x.mean(0, keepdim=True).expand_as(x)], dim=-1)
        return self.net(x).squeeze(-1)


def gumbel_rank(logits: torch.Tensor, k: int) -> torch.Tensor:
    """K sampled permutations [K, N] from Plackett-Luce(logits)."""
    g = -torch.log(-torch.log(torch.rand(k, logits.shape[0], device=logits.device).clamp_min(1e-10)))
    return torch.argsort(logits.detach() + g, dim=-1, descending=True)


def pl_log_prob(logits: torch.Tensor, perms: torch.Tensor, top_m: int) -> torch.Tensor:
    """log P(first top_m positions of each permutation) under Plackett-Luce. perms: [K, N] -> [K]."""
    s = logits[perms]  # [K, N]
    # log-sum-exp of the suffix starting at each position
    suffix = torch.logcumsumexp(s.flip(-1), dim=-1).flip(-1)
    m = min(top_m, s.shape[1])
    return (s[:, :m] - suffix[:, :m]).sum(-1)


def reinforce_loo(rewards: torch.Tensor, logp: torch.Tensor) -> torch.Tensor:
    """REINFORCE with leave-one-out baseline. rewards, logp: [K]."""
    k = rewards.shape[0]
    baseline = (rewards.sum() - rewards) / (k - 1)
    return -((rewards - baseline).detach() * logp).mean()
