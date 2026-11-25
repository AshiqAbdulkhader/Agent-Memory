import itertools
import math

import numpy as np
import torch

from memctl.budget import evidence_recall, pack, recall_batch
from memctl.data.locomo import parse_evidence, parse_time
from memctl.policy import gumbel_rank, pl_log_prob, reinforce_loo


def test_parse_evidence_handles_malformed_ids():
    assert parse_evidence(["D8:6; D9:17", "D:11:26", "D1:3"]) == ["D8:6", "D9:17", "D11:26", "D1:3"]


def test_parse_time():
    t = parse_time("1:56 pm on 8 May, 2023")
    assert (t.year, t.month, t.day, t.hour, t.minute) == (2023, 5, 8, 13, 56)


def test_pack_is_prefix_within_budget():
    ntok = np.array([10, 50, 5, 5])
    assert list(pack(np.array([0, 2, 1, 3]), ntok, 20)) == [0, 2]
    assert list(pack(np.array([1, 0]), ntok, 20)) == []


def test_recall_batch_matches_numpy():
    rng = np.random.default_rng(0)
    ntok = rng.integers(5, 40, 30)
    cover = np.zeros((30, 3), bool)
    cover[[4, 11, 20], [0, 1, 2]] = True
    perms = np.stack([rng.permutation(30) for _ in range(8)])
    got = recall_batch(torch.tensor(perms), torch.tensor(ntok, dtype=torch.float32), torch.tensor(cover), 100)
    want = [evidence_recall(pack(p, ntok, 100), cover) for p in perms]
    assert np.allclose(got.numpy(), want)


def test_plackett_luce_full_rank_probabilities_sum_to_one():
    logits = torch.tensor([0.3, -1.0, 2.0])
    perms = torch.tensor(list(itertools.permutations(range(3))))
    total = pl_log_prob(logits, perms, top_m=3).exp().sum().item()
    assert math.isclose(total, 1.0, rel_tol=1e-5)


def test_gumbel_rank_prefers_high_logits():
    torch.manual_seed(0)
    perms = gumbel_rank(torch.tensor([5.0, 0.0, -5.0]), 200)
    assert (perms[:, 0] == 0).float().mean() > 0.95


def test_reinforce_loo_pushes_toward_better_samples():
    logits = torch.zeros(4, requires_grad=True)
    perms = torch.tensor([[0, 1, 2, 3], [3, 2, 1, 0]])
    loss = reinforce_loo(torch.tensor([1.0, 0.0]), pl_log_prob(logits, perms, top_m=1))
    loss.backward()
    assert logits.grad[0] < 0 < logits.grad[3]  # gradient descent raises item 0, lowers item 3
