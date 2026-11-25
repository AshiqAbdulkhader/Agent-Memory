"""EXP-008: ablations and cost of the learned retrieval policy (no LLM calls).

Variants of the budget-agnostic ranking policy on the turns + facts substrate (EXP-001b setup),
5-fold CV over conversations, metric = evidence-recall AUC over read budgets:
  full            all 29 features, set context
  no_context      no mean-pooled set context
  no_graph        drop Personalized PageRank and keyword-overlap features
  no_lexical      drop BM25 features
  no_dense        drop dense-embedding features (incl. neighbour/session context)
  no_query_type   drop the 7 question-type features
  linear          linear scorer instead of the 2-layer MLP
Also measures training time per fold and policy inference latency per query.
"""

import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import exp_retrieval as er  # noqa: E402
from memctl.budget import BUDGETS  # noqa: E402
from memctl.features import FEATURES, N_FEATURES  # noqa: E402
from memctl.policy import Scorer  # noqa: E402

GROUPS = {
    "no_graph": ["ppr", "key_overlap", "key_idf_overlap"],
    "no_lexical": ["bm25", "bm25_pct"],
    "no_dense": ["dense", "dense_z", "dense_pct", "nbr_dense", "sess_dense"],
    "no_query_type": ["q_when", "q_count", "q_who", "q_why", "q_list", "q_would", "q_len"],
}


class Linear(torch.nn.Module):
    def __init__(self, n):
        super().__init__()
        self.lin = torch.nn.Linear(n, 1)

    def forward(self, x):
        return self.lin(x).squeeze(-1)


def masked(feats, cols):
    idx = [FEATURES.index(c) for c in cols]
    out = []
    for c in feats:
        c2 = dict(c)
        c2["questions"] = []
        for q in c["questions"]:
            q2 = dict(q)
            x = q["x"].copy()
            x[:, idx] = 0
            q2["x"] = x
            c2["questions"].append(q2)
        out.append(c2)
    return out


def main():
    feats = pickle.load(open(ROOT / "data/features/locomo_turnsfacts.pkl", "rb"))
    folds = [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]
    variants = ["full", "no_context", *GROUPS, "linear"]
    res, train_s, infer_ms = {}, {}, []
    orig_scorer = er.Scorer
    for v in variants:
        data = masked(feats, GROUPS[v]) if v in GROUPS else feats
        if v == "no_context":
            er.Scorer = lambda n: Scorer(n, context=False)
        elif v == "linear":
            er.Scorer = lambda n: Linear(n)
        else:
            er.Scorer = orig_scorer
        recalls = {b: [] for b in BUDGETS}
        t_total = 0.0
        for test_idx in folds:
            train = [c for i, c in enumerate(data) if i not in test_idx]
            test = [data[i] for i in test_idx]
            t0 = time.time()
            model = er.train_rl(train, False, 6, seed=0).eval()
            t_total += time.time() - t0
            ranker = er.model_ranker(model, False)
            r = er.evaluate(test, ranker)
            for b in BUDGETS:
                recalls[b] += r[b]
            if v == "full":
                for c, q in list(er.samples(test))[:200]:
                    t0 = time.perf_counter()
                    ranker(c, q, 256)
                    infer_ms.append((time.perf_counter() - t0) * 1000)
        row = [float(np.mean(recalls[b])) for b in BUDGETS]
        res[v] = dict(recall=dict(zip(map(str, BUDGETS), row)), auc=float(np.mean(row)))
        train_s[v] = t_total / len(folds)
        print(f"{v:14s} AUC={np.mean(row):.3f}  " + " ".join(f"{x:.3f}" for x in row)
              + f"   train {train_s[v]:.0f}s/fold", flush=True)
    er.Scorer = orig_scorer
    n_params = sum(p.numel() for p in Scorer(N_FEATURES).parameters())
    out = dict(ablation=res, train_seconds_per_fold=train_s, policy_params=n_params,
               inference_ms_per_query=dict(mean=float(np.mean(infer_ms)), p95=float(np.percentile(infer_ms, 95)),
                                           device=er.DEV))
    print(json.dumps(out["inference_ms_per_query"]), "params", n_params)
    json.dump(out, open(ROOT / "results" / "exp008_ablation.json", "w"), indent=2)
    print("saved results/exp008_ablation.json")


if __name__ == "__main__":
    main()
