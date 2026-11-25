"""EXP-007b: in-domain training on LongMemEval-S (5-fold CV over questions).

EXP-007 showed that LoCoMo-trained policies do not transfer zero-shot to LongMemEval. This checks
whether the method itself works in the new domain: the budget-agnostic retrieval policy (EXP-001
recipe) is trained on 4/5 of the LongMemEval questions and evaluated on the held-out fifth, so every
question is scored by a policy that never saw it. Reuses the cached features of EXP-007.
"""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from exp_lme import featurise  # noqa: E402
from exp_retrieval import train_rl  # noqa: E402
from memctl import llm  # noqa: E402
from memctl.budget import BUDGETS, pack  # noqa: E402
from memctl.data.longmemeval import load_longmemeval  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"


def as_conv(x, ntok, srcs, evidence):
    cover = np.array([[e in set(s) for e in evidence] for s in srcs], dtype=bool)
    return {"n_tokens": ntok.astype(np.float32), "questions": [{"x": x, "cover": cover}]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--qa_budgets", type=int, nargs="+", default=[256, 1024])
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    data = load_longmemeval()
    feats = featurise(data)
    order = np.random.default_rng(0).permutation(len(data))
    fold_of = {data[i].qid: f % args.folds for f, i in enumerate(order)}

    recall, jobs = defaultdict(list), []
    for f in range(args.folds):
        train = [as_conv(*feats[d.qid][:3], d.evidence) for d in data if fold_of[d.qid] != f and d.evidence]
        print(f"fold {f}: {len(train)} training questions", flush=True)
        model = train_rl(train, False, args.epochs, seed=0).eval()
        for inst in (d for d in data if fold_of[d.qid] == f):
            x, ntok, srcs, texts = feats[inst.qid]
            xt = torch.tensor(np.concatenate([x.astype(np.float32), np.zeros((len(x), 2), np.float32)], 1), device=DEV)
            with torch.no_grad():
                order_i = torch.argsort(model(xt), descending=True).cpu().numpy()
            for b in BUDGETS:
                sel = sorted(pack(order_i, ntok, b))
                if inst.evidence:
                    covered = {s for j in sel for s in srcs[j]}
                    recall[b].append(np.mean([e in covered for e in inst.evidence]))
                if b in args.qa_budgets:
                    jobs.append((b, inst, [texts[j] for j in sel]))
        del model
        torch.cuda.empty_cache()

    row = [float(np.mean(recall[b])) for b in BUDGETS]
    summary = {"recall": {str(b): v for b, v in zip(BUDGETS, row)} | {"auc": float(np.mean(row))}}
    print("rl_indomain recall " + " ".join(f"{v:.3f}" for v in row) + f"  AUC {np.mean(row):.3f}", flush=True)

    def run(job):
        b, inst, snippets = job
        pred = llm.answer(inst.question, snippets, question_date=inst.qdate)
        return b, inst.qtype, inst.qid, llm.judge(inst.question, inst.answer, pred)

    acc, per_q = defaultdict(list), defaultdict(dict)
    with ThreadPoolExecutor(args.workers) as ex:
        for b, qt, qid, ok in ex.map(run, jobs):
            acc[b].append(ok)
            acc[(b, qt)].append(ok)
            per_q[f"rl_indomain@{b}"][qid] = bool(ok)
    qtypes = sorted({d.qtype for d in data})
    summary["accuracy"] = {f"rl_indomain@{b}": dict(acc=float(np.mean(acc[b])),
                                                   by_type={qt: float(np.mean(acc[(b, qt)])) for qt in qtypes if acc[(b, qt)]})
                           for b in args.qa_budgets}
    for b in args.qa_budgets:
        print(f"rl_indomain B_read={b:5d} J={np.mean(acc[b]):.3f}", flush=True)
    json.dump(per_q, open(ROOT / "results" / "exp007b_lme_indomain_perq.json", "w"))
    json.dump(summary, open(ROOT / "results" / "exp007b_lme_indomain.json", "w"), indent=2)
    print("saved results/exp007b_lme_indomain.json", flush=True)


if __name__ == "__main__":
    main()
