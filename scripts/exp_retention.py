"""EXP-002: learned retention (forgetting) under a storage budget vs heuristic eviction on LoCoMo.

Training: episodes = memory snapshots after each session prefix of the training conversations; the
policy ranks items (query-free features) and keeps the top-ranked prefix within B_store; reward = mean
over the snapshot's answerable questions of the fraction of their gold evidence retained, averaged over
the storage-budget grid (all-budgets AUC, KVP-style).
Evaluation: true streaming ingestion with eviction after every session on held-out conversations
(5-fold CV over conversations). Metric: Retain-Recall (EMBER) at each B_store.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memctl.data.locomo import load_locomo  # noqa: E402
from memctl.policy import Scorer, gumbel_rank, pl_log_prob, reinforce_loo  # noqa: E402
from memctl.retention import (N_RET_FEATURES, RETENTION_BASELINES, heuristic_retention_score,  # noqa: E402
                              retention_features)
from memctl.store import MemoryStore, turns_to_items  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"
B_STORE = (1024, 2048, 4096, 8192)


def build_conv(c):
    items = turns_to_items(c.turns)
    full = MemoryStore(items)  # computes keys + embeddings once
    emb = full.embeddings
    sess_end = np.cumsum([len(s) for s in c.sessions])
    return items, emb, sess_end


def episodes_for(c, items, emb, sess_end, min_q: int = 3):
    pos = {it.id: i for i, it in enumerate(items)}
    eps = []
    for s_idx, n in enumerate(sess_end, start=1):
        qs = [q for q in c.qa if q.evidence and all(e in pos and pos[e] < n for e in q.evidence)]
        if len(qs) < min_q:
            continue
        sub = MemoryStore.from_parts(items[:n], emb[:n])
        x = retention_features(sub, s_idx, 4096)
        cover = np.zeros((n, len(qs)), np.float32)  # cover[i, j] = share of question j's evidence held by item i
        for j, q in enumerate(qs):
            for e in q.evidence:
                cover[pos[e], j] += 1.0 / len(q.evidence)
        eps.append(dict(x=torch.tensor(x, device=DEV), ntok=torch.tensor([it.n_tokens for it in items[:n]],
                        device=DEV, dtype=torch.float32), cover=torch.tensor(cover, device=DEV), total=sub.total_tokens))
    return eps


def retained_recall(perms, ntok, cover, b):
    csum = torch.cumsum(ntok[perms], -1)
    keep = torch.zeros_like(perms, dtype=torch.float32).scatter_(1, perms, (csum <= b).float())
    return (keep @ cover).mean(-1)  # [K]


def train(eps, epochs, k=16, lr=3e-3, seed=0):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = Scorer(N_RET_FEATURES).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for ep in range(epochs):
        tot = 0.0
        for i in rng.permutation(len(eps)):
            e = eps[i]
            budgets = [b for b in B_STORE if b < e["total"]]
            if not budgets:
                continue
            x = e["x"].clone()
            x[:, -2:] = 0.0  # budget-agnostic ranking: drop pressure / budget columns
            logits = model(x)
            perms = gumbel_rank(logits, k)
            r = torch.stack([retained_recall(perms, e["ntok"], e["cover"], b) for b in budgets]).mean(0)
            loss = reinforce_loo(r, pl_log_prob(logits, perms, top_m=min(len(x), 256)))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += r.mean().item()
        print(f"  ep{ep} train retained-recall {tot / len(eps):.3f}", flush=True)
    return model


def eval_stream(c, items, emb, score_fn, b):
    by_id = {it.id: (it, emb[i]) for i, it in enumerate(items)}
    sessions = [[by_id[t.dia_id][0] for t in s] for s in c.sessions]
    # stream: reuse precomputed embeddings through from_parts to avoid re-embedding
    store = MemoryStore()
    for s_idx, sess in enumerate(sessions, start=1):
        cur = store.items + sess
        store = MemoryStore.from_parts(cur, np.stack([by_id[it.id][1] for it in cur]))
        if store.total_tokens > b:
            keep_scores = score_fn(store, s_idx, b)
            order = np.argsort(-keep_scores)
            ntok = np.array([it.n_tokens for it in store.items])
            keep = sorted(order[np.cumsum(ntok[order]) <= b].tolist())
            kept = [store.items[i] for i in keep]
            store = MemoryStore.from_parts(kept, np.stack([by_id[it.id][1] for it in kept]))
    kept_ids = {it.id for it in store.items}
    per_q = [np.mean([e in kept_ids for e in q.evidence]) for q in c.qa if q.evidence]
    per_cat = defaultdict(list)
    for q in c.qa:
        if q.evidence:
            per_cat[q.category].append(np.mean([e in kept_ids for e in q.evidence]))
    return per_q, per_cat, store.total_tokens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=15)
    args = ap.parse_args()
    convs = load_locomo()
    built = [build_conv(c) for c in convs]
    print("built stores", flush=True)
    folds = [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]
    res = defaultdict(lambda: defaultdict(list))
    for fi, test_idx in enumerate(folds):
        train_eps = [e for i, c in enumerate(convs) if i not in test_idx for e in episodes_for(c, *built[i])]
        print(f"fold {fi}: {len(train_eps)} training episodes", flush=True)
        model = train(train_eps, args.epochs, seed=fi).eval()

        @torch.no_grad()
        def learned(store, s_idx, b):
            x = torch.tensor(retention_features(store, s_idx, b), device=DEV)
            x[:, -2:] = 0.0
            return model(x).cpu().numpy()

        rng = np.random.default_rng(fi)
        methods = {n: (lambda store, s, b, n=n: heuristic_retention_score(n, retention_features(store, s, b), rng))
                   for n in RETENTION_BASELINES}
        methods["learned_rl"] = learned
        for i in test_idx:
            for b in B_STORE:
                for name, fn in methods.items():
                    per_q, _, _ = eval_stream(convs[i], *built[i][:2], fn, b)
                    res[name][b] += per_q
        for name in methods:
            print(f"  {name:12s} " + " ".join(f"{np.mean(res[name][b]):.3f}" for b in B_STORE), flush=True)

    print("\nRetain-Recall by storage budget (tokens), streaming eviction, 5-fold CV")
    print(f"{'method':12s} " + " ".join(f"{b:>6d}" for b in B_STORE) + "    AUC")
    summary = {}
    for name, r in res.items():
        row = [float(np.mean(r[b])) for b in B_STORE]
        summary[name] = dict(retain_recall=dict(zip(map(str, B_STORE), row)), auc=float(np.mean(row)))
        print(f"{name:12s} " + " ".join(f"{v:6.3f}" for v in row) + f"  {np.mean(row):.3f}")
    out = ROOT / "results" / "exp002_retention.json"
    out.parent.mkdir(exist_ok=True)
    json.dump(summary, open(out, "w"), indent=2)
    print("saved", out)


if __name__ == "__main__":
    main()
