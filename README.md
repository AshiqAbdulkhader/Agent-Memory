# memctl — learned, budgeted memory for LLM agents

*Learning to Remember: Reinforcement-Learned Memory Control for LLM Agents Under Bounded Resources*
(M.Tech dissertation, BITS Pilani, 2026).

LLM agents need long-term memory, but every deployment is bounded: memory has a storage limit and
the model can only read so much per question. `memctl` gives an agent memory that respects **two
explicit token budgets**:

- **`store_budget`** — tokens the memory may hold. When it is exceeded, a learned **retention policy**
  decides what to forget.
- **`read_budget`** — evidence tokens handed to the LLM per question. A learned **retrieval policy**
  decides which memories fill it.

Both policies are small MLPs trained with ranking reinforcement learning (Plackett–Luce sampling,
REINFORCE with a leave-one-out baseline, reward averaged over all budgets). No LLM call happens inside
the memory, and the policies train in minutes on a single consumer GPU.

## Results (LoCoMo, 5-fold cross-validation, GPT-4.1 reader and judge)

| Evidence given to the reader | Mem0 | memctl |
|---|---|---|
| 64 tokens | 40.3% | **69.7%** |
| 128 tokens | 60.6% | **79.3%** |
| 256 tokens | 71.8% | **85.2%** |
| 1,024 tokens | 86.3% | **90.4%** |
| whole conversation (~24K tokens) | 91.3% | |

- Learned retention keeps 52% more future evidence than the best eviction heuristic at the same
  storage budget; retention + retrieval together keep-and-read 65% more evidence than the best
  heuristic pair.
- Mem0 needs its default ~3.3K tokens per question to match memctl at 1,024 tokens.

Full experiment log: [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md). Literature survey (35 papers):
[`docs/LITERATURE_SURVEY.md`](docs/LITERATURE_SURVEY.md).

## Install

```bash
git clone <this repo> && cd <repo>
uv sync            # or: pip install -e .
```

Python 3.11–3.12. A GPU is optional (used for embeddings and training). The embedding model
(`BAAI/bge-base-en-v1.5`, about 440 MB) and the spaCy model `en_core_web_sm` are downloaded on first use.

## Demo

```bash
uv run memctl-demo                # or: python -m memctl.demo
uv run memctl-demo --interactive  # then ask your own questions; '/budget 128' changes the read budget
```

A short Alice/Bob chat is streamed into two memories with the same storage budget (heuristic and learned).
The demo shows what each memory forgot, then the evidence each hands to the LLM at a tight and a loose read
budget. The chat is hand-written for illustration and is not a benchmark. Add `--llm` to also answer with an
LLM (needs `OPENAI_API_KEY`).

## Use

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

`BudgetedMemory(retrieval="heuristic", retention="heuristic")` uses hybrid dense+BM25 retrieval and
redundancy-aware eviction instead of the learned policies.

## How it works

1. **Write (cheap):** messages are stored verbatim with date, speaker and provenance; optionally one
   LLM call per session extracts atomic facts (`scripts/extract_facts.py`). Local embeddings
   (`BAAI/bge-base-en-v1.5`), BM25 and a keyword graph with Personalized PageRank are built without
   any LLM.
2. **Retention:** query-free features (age, redundancy, keyword novelty, …) → MLP keep-score →
   keep the highest-ranked items within `store_budget`.
3. **Retrieval:** 29 query–item features (dense/BM25/PPR scores, keyword overlap, speaker, context,
   budget) → MLP score → pack the highest-ranked items within `read_budget`.

## Reproduce

```bash
uv run python scripts/precompute_locomo.py            # turn-level features
uv run python scripts/extract_facts.py                # LLM facts (needs an OpenAI-compatible endpoint in .env)
uv run python scripts/precompute_locomo.py --facts
uv run python scripts/exp_retrieval.py                # EXP-001 (no LLM)
uv run python scripts/exp_retention.py                # EXP-002 (no LLM)
uv run python scripts/exp_qa.py --features locomo_turnsfacts.pkl --methods dense hybrid_rrf rl_agnostic rl_cond
uv run python scripts/train_release.py                # writes src/memctl/weights/*.pt
```

`.env` needs `OPENAI_API_KEY` (and `OPENAI_BASE_URL` for Azure/other OpenAI-compatible endpoints),
plus `MEMCTL_READER`, `MEMCTL_JUDGE`, `MEMCTL_EXTRACT` model names.

## Repository layout

- `src/memctl/` — library: store, features, policies, retention, LLM layer, `BudgetedMemory` API
- `scripts/` — experiments, baselines (Mem0), training of released weights, significance tests
- `docs/` — literature survey, plan, experiment log, paper notes
- `results/` — JSON results of every experiment (the 66 MB LoRA adapter of EXP-009 is a release asset)
- `report/` — dissertation reports (generated)

## Build the package

```bash
uv build                      # dist/memctl-0.1.0-py3-none-any.whl and .tar.gz (trained weights included)
uv run pytest                 # includes a test that the weights are packaged
```

## License

MIT, see [`LICENSE`](LICENSE).

## Citation

Muhammed Ashiq Abdul Khader. *Learning to Remember: Reinforcement-Learned Memory Control for LLM
Agents Under Bounded Resources.* M.Tech dissertation, BITS Pilani, 2026.
