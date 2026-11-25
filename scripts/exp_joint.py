"""EXP-004: joint retention × retrieval under (B_store, B_read) — evidence that is both kept in memory
and packed into the reader's context.

Per fold: train the retention policy (EXP-002 recipe) and the retrieval policy (EXP-001 rl_agnostic)
on training conversations; on held-out conversations stream sessions with eviction at B_store, then
rank the surviving items for each question and pack B_read tokens. Metric: joint evidence recall.
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
sys.path.insert(0, str(ROOT / "scripts"))

from exp_retention import build_conv, episodes_for  # noqa: E402
from exp_retention import train as train_retention  # noqa: E402
from exp_retrieval import train_rl  # noqa: E402
from memctl.baselines import score  # noqa: E402
from memctl.budget import pack  # noqa: E402
from memctl.data.locomo import load_locomo  # noqa: E402
from memctl.features import build_features, item_features  # noqa: E402
from memctl.retention import heuristic_retention_score, retention_features  # noqa: E402
from memctl.store import MemoryStore  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"
B_STORE = (2048, 4096, 8192)
B_READ = (256, 1024)


def stream(c, items, emb, keep_fn, b_store):
    by_id = {it.id: i for i, it in enumerate(items)}
    kept: list = []
    for s_idx, sess in enumerate(c.sessions, start=1):
        cur = kept + [items[by_id[t.dia_id]] for t in sess]
        store = MemoryStore.from_parts(cur, emb[[by_id[it.id] for it in cur]])
        if store.total_tokens > b_store:
            sc = keep_fn(store, s_idx, b_store)
            order = np.argsort(-sc)
            ntok = np.array([it.n_tokens for it in cur])
            cur = [cur[i] for i in sorted(order[np.cumsum(ntok[order]) <= b_store].tolist())]
        kept = cur
    return MemoryStore.from_parts(kept, emb[[by_id[it.id] for it in kept]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs_ret", type=int, default=15)
    ap.add_argument("--epochs_retr", type=int, default=6)
    args = ap.parse_args()
    convs = load_locomo()
    built = [build_conv(c) for c in convs]
    feats = pickle.load(open(ROOT / "data/features/locomo_turns.pkl", "rb"))
    folds = [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]
    res = defaultdict(list)
    combos = [("fifo", "dense"), ("redundancy", "hybrid_ppr"), ("learned", "hybrid_ppr"),
              ("redundancy", "learned"), ("learned", "learned")]
    for fi, test_idx in enumerate(folds):
        print(f"fold {fi}", flush=True)
        eps = [e for i, c in enumerate(convs) if i not in test_idx for e in episodes_for(c, *built[i])]
        ret_model = train_retention(eps, args.epochs_ret, seed=fi).eval()
        retr_model = train_rl([f for i, f in enumerate(feats) if i not in test_idx], False, args.epochs_retr, seed=fi).eval()
        rng = np.random.default_rng(fi)

        @torch.no_grad()
        def keep_learned(store, s, b):
            x = torch.tensor(retention_features(store, s, b), device=DEV)
            x[:, -2:] = 0.0
            return ret_model(x).cpu().numpy()

        keep_fns = {"fifo": lambda st, s, b: heuristic_retention_score("fifo", retention_features(st, s, b), rng),
                    "redundancy": lambda st, s, b: heuristic_retention_score("redundancy", retention_features(st, s, b), rng),
                    "learned": keep_learned}

        @torch.no_grad()
        def rank(name, x):
            if name == "learned":
                xt = torch.tensor(np.concatenate([x, np.zeros((len(x), 2), np.float32)], 1), device=DEV)
                return torch.argsort(retr_model(xt), descending=True).cpu().numpy()
            return np.argsort(-score(name, x))

        for i in test_idx:
            c = convs[i]
            items, emb, _ = built[i]
            for b_store in B_STORE:
                stores = {k: stream(c, items, emb, keep_fns[k], b_store) for k in {r for r, _ in combos}}
                for r_name, store in stores.items():
                    base = item_features(store)
                    ids = [it.id for it in store.items]
                    ntok = np.array([it.n_tokens for it in store.items])
                    for qa in c.qa:
                        if not qa.evidence:
                            continue
                        x = build_features(store, qa.question, base).astype(np.float32)
                        for rr, q_name in combos:
                            if rr != r_name:
                                continue
                            order = rank(q_name, x)
                            for b_read in B_READ:
                                sel = {ids[j] for j in pack(order, ntok, b_read)}
                                res[(rr, q_name, b_store, b_read)].append(np.mean([e in sel for e in qa.evidence]))
        for rr, qn in combos:
            print(f"  {rr:10s}+{qn:10s} " + " ".join(
                f"{np.mean(res[(rr, qn, bs, br)]):.3f}" for bs in B_STORE for br in B_READ), flush=True)

    print("\nJoint evidence recall (kept AND packed); columns = (B_store, B_read)")
    hdr = " ".join(f"{bs // 1024}K/{br:<5d}" for bs in B_STORE for br in B_READ)
    print(f"{'retention + retrieval':22s} {hdr}   mean")
    summary = {}
    for rr, qn in combos:
        row = [float(np.mean(res[(rr, qn, bs, br)])) for bs in B_STORE for br in B_READ]
        summary[f"{rr}+{qn}"] = dict(zip([f"{bs}/{br}" for bs in B_STORE for br in B_READ], row), mean=float(np.mean(row)))
        print(f"{rr + '+' + qn:22s} " + " ".join(f"{v:9.3f}" for v in row) + f"   {np.mean(row):.3f}")
    json.dump(summary, open(ROOT / "results" / "exp004_joint.json", "w"), indent=2)
    print("saved results/exp004_joint.json")


if __name__ == "__main__":
    main()
