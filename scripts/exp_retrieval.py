"""EXP-001: learned budget-conditioned retrieval ranking vs heuristic rankers on LoCoMo (evidence recall).

5-fold cross-validation over conversations (2 test conversations per fold, all 10 covered once).
Variants:
  baselines   random, recency, dense, bm25, hybrid_rrf, hybrid_ppr, ga_style
  sup_bce     pointwise logistic regression on gold-evidence labels (OSL-MR-style supervised scorer)
  rl_agnostic ranking RL, no budget input, reward = mean recall over all budgets (KVP all-budgets AUC)
  rl_cond     ranking RL, budget as input, reward = recall at a sampled budget (budget-conditioned)
Metric: evidence recall of the packed context at each read budget, and its mean over budgets (AUC).
"""

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memctl.baselines import BASELINES, score  # noqa: E402
from memctl.budget import BUDGETS, evidence_recall, pack, recall_batch  # noqa: E402
from memctl.data.locomo import CATEGORY_NAMES  # noqa: E402
from memctl.features import N_FEATURES  # noqa: E402
from memctl.policy import Scorer, gumbel_rank, pl_log_prob, reinforce_loo  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"
NB = len(BUDGETS)


def budget_cols(ntok: np.ndarray, b: int) -> np.ndarray:
    return np.column_stack([np.full(len(ntok), np.log2(b) / 12, np.float32), np.minimum(ntok / b, 1.0)])


def samples(convs):
    for c in convs:
        for q in c["questions"]:
            yield c, q


def to_dev(c, q, budget_input: bool):
    x = q["x"].astype(np.float32)
    x = np.concatenate([x, np.zeros((len(x), 2), np.float32)], 1)  # budget columns filled per budget
    return (torch.tensor(x, device=DEV), torch.tensor(c["n_tokens"], device=DEV, dtype=torch.float32),
            torch.tensor(q["cover"], device=DEV))


def set_budget(x: torch.Tensor, ntok: torch.Tensor, b: int, on: bool) -> torch.Tensor:
    if not on:
        return x
    x = x.clone()
    x[:, -2] = float(np.log2(b) / 12)
    x[:, -1] = (ntok / b).clamp(max=1.0)
    return x


def train_rl(train, budget_input: bool, epochs: int, k: int = 16, top_m: int = 64, lr: float = 3e-3, seed: int = 0):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = Scorer(N_FEATURES).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    data = [to_dev(c, q, budget_input) for c, q in samples(train)]
    for ep in range(epochs):
        tot = 0.0
        for i in rng.permutation(len(data)):
            x, ntok, cover = data[i]
            if budget_input:
                # one conditioned policy per budget, all budgets every step (same signal volume as agnostic)
                loss, rs = 0.0, []
                for b in BUDGETS:
                    logits = model(set_budget(x, ntok, b, True))
                    perms = gumbel_rank(logits, k)
                    rb = recall_batch(perms, ntok, cover, b)
                    loss = loss + reinforce_loo(rb, pl_log_prob(logits, perms, top_m)) / NB
                    rs.append(rb)
                r = torch.stack(rs).mean(0)
            else:
                logits = model(x)
                perms = gumbel_rank(logits, k)
                r = torch.stack([recall_batch(perms, ntok, cover, b) for b in BUDGETS]).mean(0)
                loss = reinforce_loo(r, pl_log_prob(logits, perms, top_m))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += r.mean().item()
        print(f"  ep{ep} train reward {tot / len(data):.3f}", flush=True)
    return model


def train_sup(train, epochs: int, lr: float = 3e-3, seed: int = 0):
    torch.manual_seed(seed)
    model = Scorer(N_FEATURES).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    data = [to_dev(c, q, False) for c, q in samples(train)]
    rng = np.random.default_rng(seed)
    for _ in range(epochs):
        for i in rng.permutation(len(data)):
            x, _, cover = data[i]
            y = cover.any(-1).float()
            logits = model(x)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, y, pos_weight=torch.tensor(50.0, device=DEV))
            opt.zero_grad()
            loss.backward()
            opt.step()
    return model


def evaluate(test, rank_fn):
    """rank_fn(c, q, b) -> item order. Returns {budget: [recalls]}, per-category lists."""
    res = defaultdict(list)
    for c, q in samples(test):
        for b in BUDGETS:
            order = rank_fn(c, q, b)
            r = evidence_recall(pack(order, c["n_tokens"], b), q["cover"])
            res[b].append(r)
            res[(q["category"], b)].append(r)
    return res


def model_ranker(model, budget_input):
    @torch.no_grad()
    def f(c, q, b):
        x, ntok, _ = to_dev(c, q, budget_input)
        return torch.argsort(model(set_budget(x, ntok, b, budget_input)), descending=True).cpu().numpy()
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--features", default="locomo_turns.pkl")
    ap.add_argument("--out", default="exp001_retrieval.json")
    args = ap.parse_args()
    convs = pickle.load(open(ROOT / "data/features" / args.features, "rb"))
    folds = [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]
    allres = defaultdict(lambda: defaultdict(list))
    for fi, test_idx in enumerate(folds):
        test = [convs[i] for i in test_idx]
        train = [c for i, c in enumerate(convs) if i not in test_idx]
        print(f"fold {fi}: test {[c['sample_id'] for c in test]}", flush=True)
        rng = np.random.default_rng(fi)
        for name in BASELINES:
            res = evaluate(test, lambda c, q, b, n=name: np.argsort(-score(n, q["x"].astype(np.float32), rng)))
            for key, v in res.items():
                allres[name][key] += v
        for seed in range(args.seeds):
            variants = {
                "sup_bce": (train_sup(train, args.epochs, seed=seed), False),
                "rl_agnostic": (train_rl(train, False, args.epochs, seed=seed), False),
                "rl_cond": (train_rl(train, True, args.epochs, seed=seed), True),
            }
            for name, (m, bi) in variants.items():
                res = evaluate(test, model_ranker(m.eval(), bi))
                for key, v in res.items():
                    allres[name][key] += v
        for name in allres:
            print(f"  {name:12s} " + " ".join(f"{np.mean(allres[name][b]):.3f}" for b in BUDGETS), flush=True)

    summary = {}
    print("\nEvidence recall by read budget (tokens) — all 10 conversations, 5-fold CV")
    print(f"{'method':12s} " + " ".join(f"{b:>6d}" for b in BUDGETS) + "    AUC")
    for name, res in allres.items():
        row = [float(np.mean(res[b])) for b in BUDGETS]
        cats = {CATEGORY_NAMES[cat]: float(np.mean([np.mean(res[(cat, b)]) for b in BUDGETS])) for cat in (1, 2, 3, 4)}
        summary[name] = dict(recall=dict(zip(map(str, BUDGETS), row)), auc=float(np.mean(row)), by_category_auc=cats)
        print(f"{name:12s} " + " ".join(f"{r:6.3f}" for r in row) + f"  {np.mean(row):.3f}")
    print("\nAUC by category")
    for name, s in summary.items():
        print(f"{name:12s} " + " ".join(f"{k}={v:.3f}" for k, v in s["by_category_auc"].items()))
    out = ROOT / "results" / args.out
    out.parent.mkdir(exist_ok=True)
    json.dump(summary, open(out, "w"), indent=2)
    print("saved", out)


if __name__ == "__main__":
    main()
