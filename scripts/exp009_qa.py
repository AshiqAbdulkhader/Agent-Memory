"""EXP-009 QA: answer accuracy (gpt-4o-mini reader + judge) for the LLM selector vs our policy.

Uses the same test questions (fold-0 conversations 0-1) and budgets as scripts/llm_selector_data.py.
Methods: hybrid_top (candidate order), policy_full (our RL policy over the whole memory), llm_base and
llm_grpo (selections from results/exp009_llm_preds.jsonl). Writes results/exp009_qa.json.
"""

import json
import pickle
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from exp_retrieval import train_rl  # noqa: E402
from llm_selector_data import TEST  # noqa: E402
from memctl import llm  # noqa: E402
from memctl.budget import pack  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"
BUDGETS = [128, 256]


def mcnemar(a, b):
    n01 = sum(1 for q in a if a[q] and not b[q])
    n10 = sum(1 for q in a if b[q] and not a[q])
    n, k = n01 + n10, min(n01, n10)
    return dict(wins=n01, losses=n10, p=min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0)


def main():
    convs = pickle.load(open(ROOT / "data/features/locomo_turnsfacts.pkl", "rb"))
    policy = train_rl([c for i, c in enumerate(convs) if i not in TEST], False, 6, seed=0).eval()
    rows = {(r["qid"], r["budget"]): r for r in map(json.loads, open(ROOT / "data/llm_selector/test.jsonl"))}
    preds = defaultdict(dict)
    for p in map(json.loads, open(ROOT / "results/exp009_llm_preds.jsonl")):
        preds[f"llm_{p['model']}"][(p["qid"], p["budget"])] = p["ids"]

    jobs = []
    for (qid, b), r in rows.items():
        if b not in BUDGETS:
            continue
        sid, qi = qid.rsplit(":", 1)
        c = next(c for c in convs if c["sample_id"] == sid)
        ntok = np.asarray(c["n_tokens"])
        x = c["questions"][int(qi)]["x"]
        xt = torch.tensor(np.concatenate([x.astype(np.float32), np.zeros((len(x), 2), np.float32)], 1), device=DEV)
        with torch.no_grad():
            order = torch.argsort(policy(xt), descending=True).cpu().numpy()
        sel = {"hybrid_top": pack(np.asarray(r["item_idx"]), ntok, b), "policy_full": pack(order, ntok, b)}
        for m, d in preds.items():
            sel[m] = pack(np.asarray([r["item_idx"][i] for i in d[(qid, b)]], dtype=int), ntok, b)
        for m, s in sel.items():
            jobs.append((m, b, qid, r, [c["item_texts"][j] for j in sorted(s)]))

    def run(job):
        m, b, qid, r, snippets = job
        return m, b, qid, llm.judge(r["question"], r["answer"], llm.answer(r["question"], snippets))

    acc = defaultdict(dict)
    with ThreadPoolExecutor(8) as ex:
        for m, b, qid, ok in ex.map(run, jobs):
            acc[f"{m}@{b}"][qid] = bool(ok)
    out = {"accuracy": {k: float(np.mean(list(v.values()))) for k, v in acc.items()}, "n": len(acc["hybrid_top@256"]),
           "mcnemar": {f"llm_grpo_vs_{m}@{b}": mcnemar(acc[f"llm_grpo@{b}"], acc[f"{m}@{b}"])
                       for m in ["hybrid_top", "policy_full", "llm_base"] for b in BUDGETS if f"llm_grpo@{b}" in acc}}
    for k, v in sorted(out["accuracy"].items()):
        print(f"{k:22s} {v:.3f}")
    print(json.dumps(out["mcnemar"], indent=1))
    json.dump(out, open(ROOT / "results/exp009_qa.json", "w"), indent=2)


if __name__ == "__main__":
    main()
