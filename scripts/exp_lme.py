"""EXP-007: zero-shot transfer to LongMemEval-S (500 questions, ~115K-token histories).

Retrieval policies are trained on all 10 LoCoMo conversations (raw-turn features, EXP-001 recipe) and
applied unchanged to LongMemEval-S, whose chats are user–assistant task dialogues rather than
persona chit-chat. Store = message chunks (≤150 tokens) with provenance; no LLM at write time.
Metrics: evidence recall at each read budget, and LLM-judge accuracy at B_read ∈ {256, 1024}.
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
from memctl import llm  # noqa: E402
from memctl.baselines import score  # noqa: E402
from memctl.budget import BUDGETS, pack  # noqa: E402
from memctl.data.longmemeval import load_longmemeval  # noqa: E402
from memctl.features import build_features, item_features  # noqa: E402
from memctl.store import MemoryStore  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"
METHODS = ["dense", "bm25", "hybrid_rrf", "hybrid_ppr", "rl_agnostic", "rl_cond"]


CACHE = ROOT / "data" / "features" / "lme_features.pkl"


def featurise(data):
    """Embed and key every unique chunk once (histories overlap heavily across questions), then build
    per-question features. Cached to data/features/lme_features.pkl so the LLM pass reuses them."""
    if CACHE.exists():
        cached = pickle.load(open(CACHE, "rb"))
        if all(inst.qid in cached for inst in data):
            return cached
    from memctl.store import _embedder, extract_keys

    texts = sorted({it.text for inst in data for it in inst.items})
    print(f"{len(texts)} unique chunks", flush=True)
    # fp16 + modest batches: batch 256 overflowed the 6 GB card and WSL spilled into shared memory (10 h stall).
    model = _embedder()
    if DEV == "cuda":
        model = model.half()
    emb = np.zeros((len(texts), 768), np.float16)
    step = 20000
    for s in range(0, len(texts), step):
        emb[s:s + step] = model.encode(texts[s:s + step], batch_size=64, normalize_embeddings=True,
                                       show_progress_bar=False).astype(np.float16)
        print(f"  embedded {min(s + step, len(texts))}/{len(texts)}", flush=True)
    emb = emb.astype(np.float32)
    print("embedded", flush=True)
    keys = extract_keys(texts, n_process=6)
    print("keyed", flush=True)
    idx = {t: i for i, t in enumerate(texts)}
    out = {}
    for n, inst in enumerate(data):
        rows = [idx[it.text] for it in inst.items]
        for it, r in zip(inst.items, rows):
            it.keys = keys[r]
        store = MemoryStore.from_parts(inst.items, emb[rows])
        x = build_features(store, inst.question, item_features(store)).astype(np.float16)
        out[inst.qid] = (x, np.array([it.n_tokens for it in inst.items]), [it.sources for it in inst.items],
                         [it.text for it in inst.items])
        if n % 50 == 0:
            print(f"  featurised {n}/{len(data)}", flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    pickle.dump(out, open(CACHE, "wb"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--qa_budgets", type=int, nargs="+", default=[256, 1024])
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--no_llm", action="store_true")
    args = ap.parse_args()

    locomo = pickle.load(open(ROOT / "data/features/locomo_turns.pkl", "rb"))
    models = {"rl_agnostic": (train_rl(locomo, False, 6, seed=0).eval(), False),
              "rl_cond": (train_rl(locomo, True, 6, seed=0).eval(), True)}
    data = load_longmemeval(limit=args.limit)
    print(f"{len(data)} LongMemEval instances", flush=True)
    feats = featurise(data)

    @torch.no_grad()
    def rank(m, x, ntok, b):
        if m in models:
            model, cond = models[m]
            xt = torch.tensor(np.concatenate([x.astype(np.float32), np.zeros((len(x), 2), np.float32)], 1), device=DEV)
            if cond:
                xt[:, -2] = float(np.log2(b) / 12)
                xt[:, -1] = torch.tensor(np.minimum(ntok / b, 1.0), device=DEV, dtype=torch.float32)
            return torch.argsort(model(xt), descending=True).cpu().numpy()
        return np.argsort(-score(m, x.astype(np.float32)))

    recall = defaultdict(list)
    jobs = []
    for n, inst in enumerate(data):
        x, ntok, srcs, texts = feats[inst.qid]
        for m in METHODS:
            for b in BUDGETS:
                sel = sorted(pack(rank(m, x, ntok, b), ntok, b))
                if inst.evidence:
                    covered = {s for j in sel for s in srcs[j]}
                    r = np.mean([e in covered for e in inst.evidence])
                    recall[(m, b)].append(r)
                    recall[(m, b, inst.qtype)].append(r)
                if b in args.qa_budgets:
                    jobs.append((m, b, inst, [texts[j] for j in sel]))

    summary = {"recall": {m: {str(b): float(np.mean(recall[(m, b)])) for b in BUDGETS} for m in METHODS}}
    print("\nEvidence recall on LongMemEval-S (non-abstention questions)")
    print(f"{'method':12s} " + " ".join(f"{b:>6d}" for b in BUDGETS) + "    AUC")
    for m in METHODS:
        row = [np.mean(recall[(m, b)]) for b in BUDGETS]
        summary["recall"][m]["auc"] = float(np.mean(row))
        print(f"{m:12s} " + " ".join(f"{v:6.3f}" for v in row) + f"  {np.mean(row):.3f}")

    if not args.no_llm:
        def run(job):
            m, b, inst, snippets = job
            pred = llm.answer(inst.question, snippets, question_date=inst.qdate)
            return m, b, inst.qtype, inst.qid, llm.judge(inst.question, inst.answer, pred)

        acc, per_q = defaultdict(list), defaultdict(dict)
        with ThreadPoolExecutor(args.workers) as ex:
            for m, b, qt, qid, ok in ex.map(run, jobs):
                acc[(m, b)].append(ok)
                acc[(m, b, qt)].append(ok)
                per_q[f"{m}@{b}"][qid] = bool(ok)
        summary["accuracy"] = {}
        print("\nLLM-judge accuracy on LongMemEval-S (all 500)")
        qtypes = sorted({inst.qtype for inst in data})
        for m in METHODS:
            for b in args.qa_budgets:
                by = {qt: float(np.mean(acc[(m, b, qt)])) for qt in qtypes if acc[(m, b, qt)]}
                summary["accuracy"][f"{m}@{b}"] = dict(acc=float(np.mean(acc[(m, b)])), by_type=by)
                print(f"{m:12s} B_read={b:5d} J={np.mean(acc[(m, b)]):.3f}")
        summary["usage"] = dict(prompt_tokens=llm.USAGE.prompt_tokens, content_filtered=llm.USAGE.filtered)
        json.dump(per_q, open(ROOT / "results" / "exp007_lme_perq.json", "w"))
    json.dump(summary, open(ROOT / "results" / "exp007_lme.json", "w"), indent=2)
    print("saved results/exp007_lme.json")


if __name__ == "__main__":
    main()
