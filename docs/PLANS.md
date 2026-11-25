# Project Plan / Roadmap

**Thesis**: Learning to Remember: Reinforcement-Learned Memory Control for LLM Agents Under Bounded Resources

Last updated: 2026-09-24

**Target end date: 31 Oct 2026** (compressed timeline — see phase dates below)

## Guiding goal

Build the best vector + graph + memory system for LLM agents, where the
core novelty is a **learned (RL) controller** that decides, under a hard
resource budget (context tokens, memory slot count, retrieval latency):
- what to write to memory
- what to retrieve for a given query/turn
- what to consolidate/summarize
- what to evict/forget

...rather than relying on fixed heuristics (recency, top-k cosine similarity,
TTL, LRU) as nearly every existing product/paper does today.

## Phases

### Phase 0 — Project setup ✅ (2026-08-07)
- Repo scaffolded (`docs/`, `src/`, `.gitignore`, README)
- Git initialized, remote `origin` set to
  `https://github.com/AshiqAbdulkhader/Agent-Memory.git`
  (⚠️ remote returned 404 as of 2026-08-07 — repo needs to be created on
  GitHub before first push, or confirm it's private)

### Phase 1 — Literature survey ✅ (v2 done 2026-09-24: 35 papers read, see docs/LITERATURE_SURVEY.md)
- Survey vector DB memory (Pinecone, Weaviate, Milvus, Chroma, Qdrant)
- Survey graph/GraphRAG memory (Microsoft GraphRAG, Neo4j, HippoRAG)
- Survey hybrid agent-memory products (Mem0, Zep, LangChain/LangGraph memory)
- Survey academic agent-memory architectures (MemGPT/Letta, A-MEM,
  MemoryBank, RecallM, Generative Agents)
- Survey RL for memory control under bounded resources (learned cache
  eviction, KV-cache compression, bounded rationality, budget-constrained RAG)
- Produce comparison table + gap analysis → `docs/LITERATURE_SURVEY.md`
- Output: identify the precise gap the thesis fills and a candidate problem
  formulation (state/action/reward for the RL memory controller)

### Phase 2 — Problem formulation & baseline reproduction (01 Aug 2026 – 20 Aug 2026)
- Formalize the memory-control problem as an MDP/POMDP: state (query,
  current memory contents, budget remaining), action space (store/retrieve/
  summarize/evict), reward (task success, cost, latency)
- Pick 1-2 benchmark tasks (e.g., long-horizon conversational QA, multi-session
  agent tasks — LoCoMo, LongMemEval, or similar) to evaluate against
- Reproduce 1-2 baseline systems (e.g., Mem0 or a simple vector+summarization
  baseline) on the chosen benchmark to get reference numbers

### Phase 3 — Architecture design (21 Aug 2026 – 10 Sep 2026)
- Design the hybrid vector+graph memory substrate
- Design the RL controller (policy representation, training algorithm —
  candidates: PPO, DQN for discrete evict/keep decisions, or a learned
  scoring function trained via RL-from-task-reward)
- Define the bounded-resource budget formalism (token budget, slot budget,
  latency budget)

### Phase 4 — Implementation (11 Sep 2026 – 05 Oct 2026)
- Build memory substrate (`src/memory/`)
- Build RL controller + training loop (`src/rl/`)
- Integration with an agent loop / LLM

### Phase 5 — Evaluation & Writing (06 Oct 2026 – 31 Oct 2026)
- Benchmark against Phase 1 systems under matched resource budgets
- Ablations: learned vs heuristic eviction, vector-only vs vector+graph,
  budget sensitivity curves
- Fill BITS abstract/outline doc, thesis chapters, defense prep

## Decisions (confirmed with user)

| Date | Decision | Choice |
|---|---|---|
| 2026-09-24 | LLM for extraction / answering / judge | **OpenAI models via Azure OpenAI (changed 2026-09-25)** (gpt-4o-mini class) — matches backbone of published Mem0/Zep/A-MEM numbers |
| 2026-09-24 | RL controller form | **Both, staged**: (1) small policy net over a frozen LLM first; (2) QLoRA-GRPO fine-tuned small LLM (≤1.5B) memory manager as an extension if time allows |
| 2026-09-24 | Primary benchmark | **LoCoMo first**, LongMemEval later |
| 2026-09-24 | Win claim | **Best LLM-judge accuracy at a matched memory/context-token budget** vs. Mem0, Zep, A-MEM etc., plus accuracy-vs-budget Pareto curve |
| 2026-09-24 | Compute | Code edited on Mac, synced to `ashiq@legion-wsl:~/mtech-project` (WSL2 Ubuntu, RTX 3060 6 GB) for all runs |
| 2026-09-24 | Novelty claim | **One budget-conditioned policy that jointly controls retention (write/evict under a storage budget) and retrieval (what enters the reader under a context budget)**, trained on end-task reward, over a hybrid graph+vector store; evaluated vs re-run baselines at matched budgets with Pareto curves |
| 2026-09-24 | Substrate | **Hybrid, cheap write**: raw turns with provenance + LLM atomic facts (≤1 gpt-4o-mini call/session) + spaCy-NER entity graph (no LLM) + dense & BM25 indices |
| 2026-09-24 | Budgets | **Hard: B_read (evidence tokens per query) + B_store (tokens kept in memory)**, both policy inputs; latency/$ reported, not constrained |
| 2026-09-24 | RL recipe (Stage 1) | **KVP-style ranking RL**: small scorer over item features + budget, Plackett–Luce via Gumbel-sort, REINFORCE with leave-one-out baseline, reward = area under the utility-vs-budget curve (one policy for all budgets) |

## Open decisions (ask user before settling)

- Which baselines to re-run ourselves vs. cite (proposal: re-run Mem0, LightMem, Zero-Mem-style, JustMem-style, full-context, naive RAG; cite Zep/MemGPT/Memory-R2/DeMem)
- Stage-2 LLM manager details (model size, what it controls)

## Log

- **2026-08-07**: Repo initialized, docs scaffolded, literature survey started.
- **2026-09-24**: Mid-sem report sample (BITS ZG628T format) added to repo.
  Project moving from the M4 Mac (16 GB, no GPU) to `legion` (Windows GPU
  laptop on Tailscale) for implementation/training.
  **Handoff — next steps agreed with user:**
  1. Implement ~half the work, then write the mid-sem report in the sample's
     structure (title page ×2, abstract + signatures, contents, chapters,
     future-plan table, abbreviations).
  2. Literature survey must be strong: read **≥30 related papers in full**
     (current survey is mostly abstract/secondary-source level).
  3. **Ask the user before any architecture decision.** (First four decisions
     now settled — see Decisions table.)
  4. Implement and test locally; end goal: beat the best current memory system
     on a benchmark and release as a usable open-source project.
  - Moved: project now at `ashiq@legion-wsl:~/mtech-project` (Tailscale SSH
    into WSL; Windows OpenSSH on legion was broken). `uv` installed there.
- **2026-09-24**: Literature survey v2 — 35 papers read in full (notes in
  docs/papers/READING_NOTES.md). Key finding: budget-aware learned memory became
  a crowded area in 2026 (EMBER, OSL-MR, OAS, BudgetMem, MemoryCPT, MemCon,
  DeMem, JustMem, Jev-Mem, Zero-Mem); gap narrowed to a *joint,
  budget-conditioned, lightweight* policy over a hybrid substrate with matched-
  budget evaluation. Architecture decisions recorded above. LoCoMo downloaded to
  legion (`data/locomo/data/locomo10.json`, 1,986 QA; cats 1–4 = 1,540).
- **2026-09-25**: Phase 4 implementation started early. `memctl` package (store, features, ranking-RL
  policy, retention, LLM layer) + EXP-001..004 done (see EXPERIMENTS.md). Headline so far: learned
  controller +65% joint evidence recall over best heuristic pair (EXP-004); +5.7 J at 256 tokens in
  end-to-end QA with gpt-4.1 (EXP-003). LLM provider switched to Azure (only gpt-4.1 deployed).
- **2026-09-25**: Mid-sem report drafted (report/, generated) and submitted version stored in
  report/submitted/. Mem0 re-run under our harness (EXP-005): our controller +13.4 J at 256 tokens,
  +4.1 at 1,024; Mem0 needs ~3.3K tokens to match our 1,024-token accuracy.
- **2026-11-06**: EXP-009 done (GRPO-fine-tuned Qwen2.5-1.5B selector on Colab A100): ties the small policy on QA accuracy, below it on recall; added as report Section 5.10. Memory-manager LLM variant deferred to the OSS release.
- **2026-11-05/06**: Final-semester work. Compute moved to the Ubuntu-26.04 WSL distro on legion;
  LLM switched to OpenAI gpt-4o-mini (Azure key revoked) — Nov results kept in separate tables from
  the Sep gpt-4.1 results. EXP-006 full controller (+16.6 to +22.4 J over best heuristic pair),
  EXP-007/007b LongMemEval (zero-shot transfer fails; in-domain training beats hybrid RRF, p = .018
  at 256 tokens), EXP-008 ablation (only dense features indispensable; linear ≈ MLP). Release
  weights trained (`src/memctl/weights/`), 8 tests pass. Final report generated
  (report/Final_Report.docx, report/render_final/Final_Report.pdf). API spend ≈ $4.3 of $10.
  Pending user decisions: LICENSE choice and public GitHub release.
