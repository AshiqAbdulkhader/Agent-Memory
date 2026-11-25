"""EXP-009 data: budgeted memory selection as an LLM task (for GRPO fine-tuning on Colab).

Fold 0 of the LoCoMo 5-fold CV (test = conversations 0-1, train = 2-9), store = turns + facts.
For every question the K highest hybrid-RRF candidates are listed with their token counts; the LLM
must reply with candidate ids, which are packed in its order until the read budget is full. Reward =
evidence recall of the packed set (all gold evidence in the denominator, so candidates that miss
evidence cap the reward, identically for every method).

Also computes the comparison points on the same test questions and budgets:
  hybrid_top   hybrid-RRF order packed (= the candidate order the LLM sees)
  policy_cand  our budget-agnostic RL policy re-ranking the same K candidates
  policy_full  our policy over the whole memory (its normal setting)
Writes data/llm_selector/{train,test}.jsonl and results/exp009_baselines.json.
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from exp_retrieval import train_rl  # noqa: E402
from memctl.baselines import score  # noqa: E402
from memctl.budget import pack  # noqa: E402

K = 30
TEST = [0, 1]
EVAL_BUDGETS = [64, 128, 256]
DEV = "cuda" if torch.cuda.is_available() else "cpu"
OUT = ROOT / "data" / "llm_selector"


def recall_of(sel, cover):
    return float(cover[sel].any(0).mean()) if len(sel) else 0.0


def main():
    convs = pickle.load(open(ROOT / "data/features/locomo_turnsfacts.pkl", "rb"))
    train_c = [c for i, c in enumerate(convs) if i not in TEST]
    test_c = [convs[i] for i in TEST]
    OUT.mkdir(parents=True, exist_ok=True)

    policy = train_rl(train_c, False, 6, seed=0).eval()

    def policy_scores(x):
        xt = torch.tensor(np.concatenate([x.astype(np.float32), np.zeros((len(x), 2), np.float32)], 1), device=DEV)
        with torch.no_grad():
            return policy(xt).cpu().numpy()

    rng = np.random.default_rng(0)
    base = {m: {b: [] for b in EVAL_BUDGETS} for m in ["hybrid_top", "policy_cand", "policy_full", "oracle_cand"]}
    for split, cs in [("train", train_c), ("test", test_c)]:
        rows = []
        for c in cs:
            ntok = np.asarray(c["n_tokens"])
            for qi, q in enumerate(c["questions"]):
                cover = np.asarray(q["cover"], bool)
                if cover.shape[1] == 0:
                    continue
                x = q["x"]
                cand = np.argsort(-score("hybrid_rrf", x.astype(np.float32)))[:K]
                row = dict(qid=f"{c['sample_id']}:{qi}", question=q["q"], answer=q["answer"], category=q["category"],
                           texts=[c["item_texts"][j] for j in cand], ntok=[int(ntok[j]) for j in cand],
                           cover=[[int(e) for e in np.flatnonzero(cover[j])] for j in cand], n_evidence=int(cover.shape[1]),
                           item_idx=[int(j) for j in cand])
                if split == "train":
                    row["budget"] = int(rng.choice(EVAL_BUDGETS))
                    rows.append(row)
                    continue
                ps = policy_scores(x)
                for b in EVAL_BUDGETS:
                    rows.append(dict(row, budget=b))
                    base["hybrid_top"][b].append(recall_of(pack(cand, ntok, b), cover))
                    base["policy_cand"][b].append(recall_of(pack(cand[np.argsort(-ps[cand])], ntok, b), cover))
                    base["policy_full"][b].append(recall_of(pack(np.argsort(-ps), ntok, b), cover))
                    # oracle over candidates: evidence-covering candidates first, shortest first
                    useful = cover[cand].any(1)
                    order = cand[np.lexsort((ntok[cand], ~useful))]
                    base["oracle_cand"][b].append(recall_of(pack(order, ntok, b), cover))
        with open(OUT / f"{split}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"{split}: {len(rows)} rows", flush=True)

    summary = {m: {str(b): float(np.mean(v)) for b, v in d.items()} for m, d in base.items()}
    for m, d in summary.items():
        print(f"{m:12s} " + " ".join(f"{d[str(b)]:.3f}" for b in EVAL_BUDGETS), flush=True)
    json.dump(dict(K=K, test_convs=TEST, budgets=EVAL_BUDGETS, recall=summary),
              open(ROOT / "results" / "exp009_baselines.json", "w"), indent=2)


if __name__ == "__main__":
    main()
