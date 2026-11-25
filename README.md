# memctl — learned, budgeted memory for LLM agents

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11–3.12](https://img.shields.io/badge/python-3.11%E2%80%933.12-blue.svg)

LLM agents need long-term memory, but every deployment is bounded: memory has a storage limit, and the model
can read only so much per question. `memctl` gives an agent memory that respects **two explicit token budgets**:

- **`store_budget`**: tokens the memory may hold. When it is exceeded, a learned **retention policy** decides
  what to forget.
- **`read_budget`**: evidence tokens handed to the LLM per question. A learned **retrieval policy** decides
  which memories fill it.

Both policies are small scorers (24K parameters) trained with ranking reinforcement learning. No LLM call
happens inside the memory, ranking a question's memory takes about 7.5 ms, and training takes minutes on a
consumer GPU.

> Code for the M.Tech dissertation *Learning to Remember: Reinforcement-Learned Memory Control for LLM Agents
> Under Bounded Resources* (BITS Pilani, 2026). The report is in [`report/Final_Report.pdf`](report/Final_Report.pdf).

## Quick start

```bash
git clone https://github.com/AshiqAbdulkhader/Agent-Memory.git && cd Agent-Memory
uv sync                           # or: pip install -e .   (Python 3.11 or 3.12)
uv run memctl-demo                # short demo, no API key needed
```

The first run downloads the embedding model (`BAAI/bge-base-en-v1.5`, about 440 MB) and the spaCy model
`en_core_web_sm`. A GPU is optional.

```python
from datetime import datetime
from memctl import BudgetedMemory

mem = BudgetedMemory(store_budget=8192)               # tokens kept in memory

mem.add("I adopted a puppy named Max yesterday", speaker="Alice", time=datetime(2023, 5, 8))
mem.add("That's wonderful!", speaker="Bob", time=datetime(2023, 5, 8))
mem.end_session()                                     # forgetting runs at session boundaries

evidence = mem.recall("What is Alice's dog called?", read_budget=256)
prompt = "Memory:\n" + "\n".join(evidence) + "\n\nQuestion: What is Alice's dog called?"
# send `prompt` to any LLM
```

`BudgetedMemory(retrieval="heuristic", retention="heuristic")` switches to hybrid dense + BM25 retrieval and
redundancy-aware eviction, which is the best non-learned baseline.

## Demo

`uv run memctl-demo` streams a short Alice and Bob chat into two memories with the same 450-token storage
budget, one heuristic and one learned. It shows which key facts each memory forgot, then the evidence each hands
the LLM at a tight and a loose read budget. In the bundled run the learned memory keeps the Lisbon and Porto
facts that the heuristic forgets, and has the answer in its evidence for 5 of 5 questions against 3 of 5.

Add `--interactive` to ask your own questions (`/budget 32` changes the read budget). The chat is hand-written
and is an illustration, not a benchmark; the measured results are below.

## Results

All results use paired exact McNemar tests, and every baseline is re-run in the same harness with the same
reader, judge and budgets. Numbers from different reader models are never compared with each other.

**LoCoMo, 5-fold cross-validation by conversation, GPT-4.1 reader and judge** (accuracy):

| Evidence given to the reader | Mem0 | memctl |
|---|---|---|
| 64 tokens | 40.3% | **69.7%** |
| 128 tokens | 60.6% | **79.3%** |
| 256 tokens | 71.8% | **85.2%** |
| 1,024 tokens | 86.3% | **90.4%** |
| whole conversation (about 24K tokens) | 91.3% | |

- Learned retention keeps 52% more future evidence than the best eviction heuristic at the same storage budget;
  retention plus retrieval keep and read 65% more evidence than the best heuristic pair.
- Mem0 needs its default of about 3,300 tokens per question to match memctl at 1,024.
- With **both budgets enforced** (GPT-4o-mini reader), the full controller is 17 to 22 points more accurate than
  the best heuristic pair, for example 77.4% against 55.0% at 8K storage and 256 read tokens.

**What did not work, and what was learned**

- **Weights do not transfer across domains.** Policies trained on LoCoMo fall below hybrid retrieval on
  LongMemEval-S (61.6% against 68.2% at 1,024 tokens). Retrained on LongMemEval with cross-validation the same
  method beats it (71.4%, p = 0.072; at 256 tokens 56.4% against 51.4%, p = 0.018). Train on your own domain.
- **An RL-fine-tuned LLM is not better.** A 1.5B-parameter LLM trained with GRPO and LoRA on the same reward
  matches the 24K-parameter policy on accuracy (p = 0.53 and 0.71) at about 62,000 times the parameters and 40
  times the selection time. One fold, one seed, one model size.
- **Only dense similarity features are indispensable** in the ablation, and a linear scorer matches the MLP.

Full numbers, tables and caveats: [`report/Final_Report.pdf`](report/Final_Report.pdf) and the experiment log
[`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md). Raw outputs are in [`results/`](results/).

## How it works

1. **Write (cheap):** messages are stored verbatim with date, speaker and provenance. Optionally one LLM call per
   session extracts atomic facts (`scripts/extract_facts.py`). Embeddings, BM25 and a keyword graph with
   Personalized PageRank are built locally without any LLM.
2. **Retention:** query-free features (age, redundancy, keyword novelty, ...) go through a scorer and the
   highest-ranked items within `store_budget` are kept.
3. **Retrieval:** 29 query and item features (dense, BM25 and PageRank scores, keyword overlap, speaker, context,
   budget) go through a scorer and the highest-ranked items are packed into `read_budget`.
4. **Training:** items are ranked with a Plackett–Luce distribution (Gumbel sorting), packed to a budget, and the
   reward is gold-evidence recall averaged over budgets. REINFORCE with a leave-one-out baseline, so one ranking
   serves every budget and the policy learns not to spend budget on redundant items.

## Limitations

- Accuracy is graded by an LLM judge with the protocol of Mem0 and LightMem; there is no human evaluation.
- LoCoMo has ten conversations. The LongMemEval experiments use one reader, one training seed and no Mem0 re-run.
- Training needs gold evidence labels. Learning from answer correctness or interaction logs is future work.
- Trained weights are domain-specific (see above).

## Reproduce the experiments

Datasets are not bundled. Put LoCoMo at `data/locomo/data/locomo10.json`
(clone <https://github.com/snap-research/locomo> into `data/locomo`) and LongMemEval-S at
`data/longmemeval/longmemeval_s_cleaned.json`.

```bash
uv run python scripts/precompute_locomo.py            # turn-level features
uv run python scripts/extract_facts.py                # LLM facts (needs an OpenAI-compatible endpoint in .env)
uv run python scripts/precompute_locomo.py --facts
uv run python scripts/exp_retrieval.py                # retrieval recall (no LLM)
uv run python scripts/exp_retention.py                # retention recall (no LLM)
uv run python scripts/exp_joint.py                    # retention + retrieval
uv run python scripts/exp_qa.py --features locomo_turnsfacts.pkl \
        --methods dense hybrid_rrf rl_agnostic rl_cond --budgets 64 128 256 1024
uv run python scripts/exp_joint_qa.py                 # both budgets enforced, end to end
uv run python scripts/exp_lme.py                      # LongMemEval zero-shot transfer
uv run python scripts/exp_lme_indomain.py             # LongMemEval in-domain
uv run python scripts/exp_ablation.py                 # ablation and cost
uv run python scripts/train_release.py                # writes src/memctl/weights/*.pt
```

The LLM comparison runs on a Colab GPU: `scripts/llm_selector_data.py` builds the data,
`scripts/colab_grpo_selector.py` trains and evaluates, and `scripts/exp009_qa.py` scores accuracy. The 66 MB LoRA
adapter is not stored in git.

`.env` needs `OPENAI_API_KEY` (and `OPENAI_BASE_URL` for Azure or other OpenAI-compatible endpoints), plus
`MEMCTL_READER`, `MEMCTL_JUDGE` and `MEMCTL_EXTRACT` model names. Never commit it.

## Repository layout

- `src/memctl/`: library (store, features, policies, retention, LLM layer, `BudgetedMemory` API, demo) and the
  trained weights
- `scripts/`: experiments, the Mem0 baseline, training of the released weights, significance tests
- `docs/`: literature survey, plan, experiment log, paper notes
- `results/`: JSON results of every experiment
- `report/`: the dissertation and its build scripts

## Development

```bash
uv run pytest                 # includes a test that the trained weights are packaged
uv build                      # wheel and sdist in dist/ (weights included)
```

## License and citation

MIT, see [`LICENSE`](LICENSE). If you use this work, please cite:

> Muhammed Ashiq Abdul Khader. *Learning to Remember: Reinforcement-Learned Memory Control for LLM Agents Under
> Bounded Resources.* M.Tech dissertation, BITS Pilani, 2026.
