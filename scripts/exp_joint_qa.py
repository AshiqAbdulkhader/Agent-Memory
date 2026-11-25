"""EXP-006: the full controller end to end — streaming retention under B_store, then budgeted retrieval
under B_read, answered and judged by the LLM. Store = raw turns + LLM facts (provenance-linked).

Per fold (5-fold CV over conversations):
  * retention policy: ranking RL on session-prefix snapshots of the training conversations, reward =
    retained gold evidence (per evidence turn, so a fact and its source turn are not double-counted),
    averaged over the B_store grid;
  * retrieval policy: budget-conditioned ranking RL (EXP-001b recipe) on the training conversations;
  * test: stream each held-out conversation with eviction after every session, then rank/pack each
    question's evidence, answer with the reader LLM and grade with the judge.
Baselines: FIFO + dense, redundancy-aware + hybrid RRF (best heuristic pair in EXP-004).
"""

import argparse
import json
import pickle
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from exp_retrieval import train_rl  # noqa: E402
from precompute_locomo import FACTS, fact_items  # noqa: E402
from memctl import llm  # noqa: E402
from memctl.baselines import score  # noqa: E402
from memctl.budget import pack  # noqa: E402
from memctl.data.locomo import CATEGORY_NAMES, load_locomo  # noqa: E402
from memctl.features import build_features, item_features  # noqa: E402
from memctl.policy import Scorer, gumbel_rank, pl_log_prob, reinforce_loo  # noqa: E402
from memctl.retention import N_RET_FEATURES, heuristic_retention_score, retention_features  # noqa: E402
from memctl.store import MemoryStore, turns_to_items  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"
B_STORE = (2048, 8192)
B_READ = (256, 1024)
TRAIN_B_STORE = (1024, 2048, 4096, 8192)


def build_conv(c, facts):
    items = sorted(turns_to_items(c.turns) + fact_items(c, facts[c.sample_id]),
                   key=lambda it: (it.session, it.kind == "fact"))
    store = MemoryStore(items)  # keys + (cached) embeddings once
    return items, store.embeddings


def evidence_matrices(c, items, upto_session=None):
    """C[i, e] = item i covers evidence turn e; Q[e, j] = 1/|E_j| if e is gold evidence of question j."""
    qs = [q for q in c.qa if q.evidence and (upto_session is None or
          all(int(e[1:].split(":")[0]) <= upto_session for e in q.evidence))]
    ev = sorted({e for q in qs for e in q.evidence})
    col = {e: k for k, e in enumerate(ev)}
    C = np.zeros((len(items), len(ev)), np.float32)
    for i, it in enumerate(items):
        for s in it.sources:
            if s in col:
                C[i, col[s]] = 1.0
    Q = np.zeros((len(ev), len(qs)), np.float32)
    for j, q in enumerate(qs):
        for e in q.evidence:
            if e in col:
                Q[col[e], j] = 1.0 / len(q.evidence)
    return C, Q, qs


def retention_episodes(c, items, emb, min_q=3):
    eps = []
    n_sess = max(it.session for it in items)
    for s in range(1, n_sess + 1):
        n = sum(it.session <= s for it in items)
        sub_items = items[:n]
        C, Q, qs = evidence_matrices(c, sub_items, upto_session=s)
        if len(qs) < min_q:
            continue
        sub = MemoryStore.from_parts(sub_items, emb[:n])
        x = torch.tensor(retention_features(sub, s, 4096), device=DEV)
        x[:, -2:] = 0.0
        eps.append(dict(x=x, ntok=torch.tensor([it.n_tokens for it in sub_items], device=DEV, dtype=torch.float32),
                        C=torch.tensor(C, device=DEV), Q=torch.tensor(Q, device=DEV), total=sub.total_tokens))
    return eps


def train_retention(eps, epochs, k=16, lr=3e-3, seed=0):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = Scorer(N_RET_FEATURES).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for ep in range(epochs):
        tot = 0.0
        for i in rng.permutation(len(eps)):
            e = eps[i]
            budgets = [b for b in TRAIN_B_STORE if b < e["total"]]
            if not budgets:
                continue
            logits = model(e["x"])
            perms = gumbel_rank(logits, k)
            rs = []
            for b in budgets:
                csum = torch.cumsum(e["ntok"][perms], -1)
                keep = torch.zeros_like(perms, dtype=torch.float32).scatter_(1, perms, (csum <= b).float())
                covered = ((keep @ e["C"]) > 0).float()          # [K, E]
                rs.append((covered @ e["Q"]).mean(-1))           # [K] mean retained recall over questions
            r = torch.stack(rs).mean(0)
            loss = reinforce_loo(r, pl_log_prob(logits, perms, top_m=min(len(logits), 256)))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += r.mean().item()
        print(f"  retention ep{ep} reward {tot / max(len(eps), 1):.3f}", flush=True)
    return model


def stream(c, items, emb, keep_fn, b_store):
    by_sess = defaultdict(list)
    for i, it in enumerate(items):
        by_sess[it.session].append(i)
    kept: list[int] = []
    for s in sorted(by_sess):
        cur = kept + by_sess[s]
        store = MemoryStore.from_parts([items[i] for i in cur], emb[cur])
        if store.total_tokens > b_store:
            sc = keep_fn(store, s, b_store)
            order = np.argsort(-sc)
            ntok = np.array([items[i].n_tokens for i in cur])
            cur = [cur[j] for j in sorted(order[np.cumsum(ntok[order]) <= b_store].tolist())]
        kept = cur
    return MemoryStore.from_parts([items[i] for i in kept], emb[kept])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs_ret", type=int, default=12)
    ap.add_argument("--epochs_retr", type=int, default=6)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--no_llm", action="store_true", help="only joint evidence recall (no reader/judge calls)")
    args = ap.parse_args()

    convs = load_locomo()
    facts = json.load(open(FACTS))
    built = [build_conv(c, facts) for c in convs]
    feats = pickle.load(open(ROOT / "data/features/locomo_turnsfacts.pkl", "rb"))
    print("stores built", flush=True)
    folds = [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]
    combos = [("fifo", "dense"), ("redundancy", "hybrid_rrf"), ("learned", "learned")]
    recall = defaultdict(list)
    jobs = []  # (combo, b_store, b_read, sample_id, qa, snippets, mem_tokens)
    for fi, test_idx in enumerate(folds):
        print(f"fold {fi}", flush=True)
        eps = [e for i in range(len(convs)) if i not in test_idx for e in retention_episodes(convs[i], *built[i])]
        ret_model = train_retention(eps, args.epochs_ret, seed=fi).eval()
        retr_model = train_rl([f for i, f in enumerate(feats) if i not in test_idx], True, args.epochs_retr, seed=fi).eval()
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
        def rank(name, x, store, b_read):
            if name == "learned":
                toks = torch.tensor([it.n_tokens for it in store.items], device=DEV, dtype=torch.float32)
                xt = torch.tensor(np.concatenate([x, np.zeros((len(x), 2), np.float32)], 1), device=DEV)
                xt[:, -2] = float(np.log2(b_read) / 12)
                xt[:, -1] = (toks / b_read).clamp(max=1.0)
                return torch.argsort(retr_model(xt), descending=True).cpu().numpy()
            return np.argsort(-score(name, x))

        for i in test_idx:
            c = convs[i]
            items, emb = built[i]
            for b_store in B_STORE:
                for r_name, q_name in combos:
                    store = stream(c, items, emb, keep_fns[r_name], b_store)
                    base = item_features(store)
                    ntok = np.array([it.n_tokens for it in store.items])
                    for qa in c.qa:
                        if not qa.evidence:
                            continue
                        x = build_features(store, qa.question, base).astype(np.float32)
                        for b_read in B_READ:
                            sel = sorted(pack(rank(q_name, x, store, b_read), ntok, b_read))
                            covered = {s for j in sel for s in store.items[j].sources}
                            recall[(r_name, q_name, b_store, b_read)].append(np.mean([e in covered for e in qa.evidence]))
                            jobs.append(((r_name, q_name), b_store, b_read, c.sample_id, qa,
                                         [store.items[j].text for j in sel], store.total_tokens))
        for rr, qn in combos:
            print(f"  {rr}+{qn} recall " + " ".join(f"{np.mean(recall[(rr, qn, bs, br)]):.3f}"
                                                    for bs in B_STORE for br in B_READ), flush=True)

    summary = {"recall": {f"{r}+{q}@{bs}/{br}": float(np.mean(recall[(r, q, bs, br)]))
                          for r, q in combos for bs in B_STORE for br in B_READ}}
    if not args.no_llm:
        def run(job):
            combo, bs, br, sid, qa, snippets, _ = job
            ok = llm.judge(qa.question, qa.answer, llm.answer(qa.question, snippets))
            return combo, bs, br, qa.category, ok, f"{sid}|{qa.question}"

        acc, per_q = defaultdict(list), defaultdict(dict)
        print(f"{len(jobs)} reader+judge jobs", flush=True)
        with ThreadPoolExecutor(args.workers) as ex:
            for n, (combo, bs, br, cat, ok, key) in enumerate(ex.map(run, jobs)):
                name = f"{combo[0]}+{combo[1]}@{bs}/{br}"
                acc[name].append(ok)
                acc[(name, cat)].append(ok)
                per_q[name][key] = bool(ok)
                if n % 2000 == 0:
                    print(f"  {n}/{len(jobs)}", flush=True)
        summary["accuracy"] = {}
        print("\nLLM-judge accuracy, full controller (B_store/B_read)")
        for name in sorted(k for k in acc if isinstance(k, str)):
            cats = {CATEGORY_NAMES[c]: float(np.mean(acc[(name, c)])) for c in (1, 2, 3, 4) if acc[(name, c)]}
            summary["accuracy"][name] = dict(acc=float(np.mean(acc[name])), n=len(acc[name]), by_category=cats)
            print(f"{name:34s} J={np.mean(acc[name]):.3f}")
        summary["usage"] = dict(prompt_tokens=llm.USAGE.prompt_tokens, completion_tokens=llm.USAGE.completion_tokens,
                                content_filtered=llm.USAGE.filtered)
        json.dump(per_q, open(ROOT / "results" / "exp006_joint_qa_perq.json", "w"))
    json.dump(summary, open(ROOT / "results" / "exp006_joint_qa.json", "w"), indent=2)
    print("saved results/exp006_joint_qa.json")


if __name__ == "__main__":
    main()
