"""EXP-003: end-to-end LoCoMo QA accuracy (LLM judge) at matched read budgets.

For each held-out question (5-fold CV over conversations): rank memory items with a method, pack the
top items into B_read tokens, answer with the reader LLM (gpt-4o-mini), grade with the Mem0/LightMem
judge prompt. Also runs the full-context reference (whole conversation, no budget).

Requires OPENAI_API_KEY in .env. All calls are cached under data/cache/llm.
"""

import argparse
import json
import pickle
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from exp_retrieval import model_ranker, samples, train_rl  # noqa: E402
from memctl import llm  # noqa: E402
from memctl.baselines import score  # noqa: E402
from memctl.budget import pack  # noqa: E402
from memctl.data.locomo import CATEGORY_NAMES, load_locomo  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budgets", type=int, nargs="+", default=[256, 1024])
    ap.add_argument("--methods", nargs="*", default=["dense", "hybrid_ppr", "rl_agnostic"])
    ap.add_argument("--full_context", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="questions per conversation (0 = all), for smoke tests")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", default="")
    ap.add_argument("--features", default="locomo_turns.pkl")
    args = ap.parse_args()

    feats = pickle.load(open(ROOT / "data/features" / args.features, "rb"))
    convs = load_locomo()
    texts = {c.sample_id: {t.dia_id: t.render() for t in c.turns} for c in convs}
    full_ctx = {c.sample_id: "\n".join(t.render() for t in c.turns) for c in convs}
    if args.limit:
        for f in feats:
            f["questions"] = f["questions"][: args.limit]

    jobs = []  # (method, budget, conv, question, snippets)
    folds = [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]
    for fi, test_idx in enumerate(folds):
        test = [feats[i] for i in test_idx]
        train = [c for i, c in enumerate(feats) if i not in test_idx]
        rankers = {}
        for m in args.methods:
            if m == "rl_agnostic":
                rankers[m] = model_ranker(train_rl(train, False, 6, seed=0).eval(), False)
            elif m == "rl_cond":
                rankers[m] = model_ranker(train_rl(train, True, 6, seed=0).eval(), True)
            else:
                rankers[m] = lambda c, q, b, m=m: np.argsort(-score(m, q["x"].astype(np.float32)))
        for c, q in samples(test):
            for m, rank in rankers.items():
                for b in args.budgets:
                    sel = sorted(pack(rank(c, q, b), c["n_tokens"], b))  # chronological order for the reader
                    jobs.append((m, b, c["sample_id"], q, [c["item_texts"][i] if "item_texts" in c else texts[c["sample_id"]][c["item_ids"][i]] for i in sel]))
            if args.full_context:
                jobs.append(("full_context", 0, c["sample_id"], q, [full_ctx[c["sample_id"]]]))

    def run(job):
        m, b, sid, q, snippets = job
        pred = llm.answer(q["q"], snippets)
        return m, b, q["category"], llm.judge(q["q"], q["answer"], pred), f"{sid}|{q['q']}"

    print(f"{len(jobs)} reader+judge jobs", flush=True)
    res = defaultdict(list)
    per_q = defaultdict(dict)  # "method@budget" -> {question key: correct}
    with ThreadPoolExecutor(args.workers) as ex:
        for i, (m, b, cat, ok, qkey) in enumerate(ex.map(run, jobs)):
            per_q[f"{m}@{b}"][qkey] = bool(ok)
            res[(m, b)].append(ok)
            res[(m, b, cat)].append(ok)
            if i % 500 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    summary = {}
    print(f"\nLLM-judge accuracy (reader={llm.READER_MODEL}, judge={llm.JUDGE_MODEL}), LoCoMo cats 1-4, 5-fold CV")
    for key in sorted(k for k in res if len(k) == 2):
        m, b = key
        cats = {CATEGORY_NAMES[c]: float(np.mean(res[(m, b, c)])) for c in (1, 2, 3, 4) if res[(m, b, c)]}
        summary[f"{m}@{b}"] = dict(acc=float(np.mean(res[key])), n=len(res[key]), by_category=cats)
        print(f"{m:14s} B_read={b:5d}  J={np.mean(res[key]):.3f}  " + " ".join(f"{k}={v:.3f}" for k, v in cats.items()))
    summary["models"] = dict(reader=llm.READER_MODEL, judge=llm.JUDGE_MODEL)
    summary["usage"] = dict(calls=llm.USAGE.calls, prompt_tokens=llm.USAGE.prompt_tokens,
                            completion_tokens=llm.USAGE.completion_tokens, by_role=llm.USAGE.by_role,
                            content_filtered=llm.USAGE.filtered)
    print("usage", summary["usage"])
    out = ROOT / "results" / (args.out or "exp003_qa.json")
    json.dump(summary, open(out, "w"), indent=2)
    json.dump(per_q, open(out.with_name(out.stem + "_perq.json"), "w"))
    print("saved", out)


if __name__ == "__main__":
    main()
