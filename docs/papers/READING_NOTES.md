# Paper Reading Notes

Detailed per-paper notes feeding `docs/LITERATURE_SURVEY.md`. Each entry:
problem → method → budget/cost handling → benchmark numbers → relevance to
this thesis. "Read" = full text or full structured report (noted per entry).

Legend for relevance: ★★★ direct competitor / must-cite-and-beat,
★★ important design input, ★ background.

---

## A. Budget / cost-aware memory (closest to thesis)

### A1. JustMem: Just-Enough Memory Access for Long-Term Conversations — arXiv:2609.19877 (Sep 2026) ★★★
*Read: full text.*
- **Problem**: retrieve sufficient evidence without blowing up context; evidence can be local, distributed across sessions, or "fidelity-sensitive" (lost in compression).
- **Method**: session → atomic memory cards (subject, fact, event_date, status, kind; ~18 tok/card; 3,804 cards for LoCoMo) with provenance links to source turns. LLM planner (GPT-4.1-mini) predicts two binary demands per query → deterministic route: LOOKUP (top-k compact), COMPOSE (≤2 rewrites, union candidates, rerank, still top-10), REPLAY (recover provenance source turns). Qwen3-Rerank.
- **Budget**: fixed K=10 compact cards; tokens reported (construction K-tok, inference K-tok/query). Budget is *fixed*, not optimized; routing is prompted, not learned.
- **Results (GPT-4.1-mini, LLM-judge, matched config)**: LoCoMo 79.61 (LightMem 79.08, SimpleMem 76.55, A-Mem 67.91, MemoryOS 65.12, FullText 57.18, NaiveRAG 63.82); LongMemEval-S 83.40 (LightMem 76.44). Infer 1.33K tok/q on LoCoMo. LoCoMo-Plus cognitive 62.59.
- Key findings: global atomic top-10 beats session-level packing by +10.7 pts; query-guided broadening +9 pts on aggregation questions; adaptive source replay beats always-replay (83.4 vs 80.6) at 1/3 the tokens.
- **Relevance**: current strongest efficient system on LoCoMo w/ GPT-4.1-mini. Its routing is a hand rule over LLM-predicted flags → a *learned* budget-aware access policy is a natural improvement. Must be a baseline. Useful design: atomic cards + provenance + reranker.

### A2. Retain or Consolidate? Budget-Dependent Operator Selection — arXiv:2607.17545 (Jul 2026, Huawei Noah's Ark) ★★★
*Read: full text incl. supplementary.*
- **Problem**: under a token budget B, keep raw records (retention) or replace with generated consolidation (Merge / Abstract / Rewrite)? When and which?
- **Theory**: value of consolidation = coverage effect (evidence retention couldn't fit) + signed replacement effect (fidelity loss on evidence that fit). Predicts crossover with *relative* budget pressure.
- **Method — OAS**: offline evaluate all 4 actions; ridge regression per action on 11 pre-generation features (B/512, #constituents, token pressure, fit fraction, #sessions, embedding dispersion, mean pairwise cosine, query-type one-hot); argmax + held-out harm-calibrated threshold. MLP gave no gain over ridge.
- **Results**: LongMemEval budgets 32/64/128/256 tok: Abstract +48 pts at 32 tok, retention wins by 8–11 pts at 256. LoCoMo crossover at ~64 tok. Cross-note Abstract/Merge > local Rewrite. Direct OAS +51/+36/+12/0 pts over retention per budget. DeepSeek-V3.2 answer/judge; oracle gold evidence (controlled, not end-to-end).
- **Limitation (their words)**: isolates representation from retrieval; full-history variant does not beat strongest fixed policy; future work = jointly learn retrieval + consolidation + packing in persistent memory.
- **Relevance**: directly supports our thesis that the *optimal memory op depends on budget* → the budget must be in the policy's state. Their stated future work is essentially our project. Cite heavily; reuse their feature ideas (token pressure, fit fraction).

### A3. MemoryCPT: End-to-End Agent Memory for Cost-Performance Trade-off — arXiv:2608.04843 (Aug 2026, HKUST/Tencent, AAAI'27) ★★★
*Read: full text (main paper).*
- **Method**: (1) QAD: distill a modular teacher memory pipeline (segmenter, episode generator, merger, semantic extractor) into Qwen2.5-7B LoRA-A via SFT on reasoning traces. (2) QAR: RRF (dense Qwen3-Embedding + BM25) top-20 episodic + top-50 semantic → LoRA-B summarizer trained with **GRPO, reward = α·F1 + (1−α)·(1 − normalized $cost)**, α=0.8. Frozen Qwen3-14B answerer. Formulated as a one-step contextual bandit.
- **Metric**: Quality-per-Cost QPC = F1 / (USD×10⁴ per query), amortizing construction cost.
- **Results** (LoCoMo test = conv-49/50 only, 314 Qs; Qwen2.5-72B judge): Judge 0.755, F1 0.479, cost 4.31 vs BudgetMem 0.640/24.11, LightMem 0.755/19.80, Memory-R1 0.592/3.78.
- **Relevance**: first system with cost *in the RL reward*. But: cost is a soft penalty (no hard budget), only the summarizer is learned (write/evict are distilled heuristics), tiny test split, flat store (no graph). Compare on QPC too.

### A4. MemCon — Memory as a Controlled Process: Learned Adaptive Memory Management — arXiv:2607.13591 (Jul 2026, UCLA/UW) ★★★
*Read: full structured report.*
- **Method**: memory ops as MDP treated as contextual bandit. State = discretized task features (goal type, step phase, stuck flag, …) + memory features (size, plan available, learning phase) → few hundred states. Actions: RETRIEVE / PLANINJECT / RE-RETRIEVE / CONSOLIDATE / FORGET / NOOP × params (top-k, insight-k, hop). **Tabular UCB** Q-learning, Monte-Carlo terminal reward (success + λ·speed bonus − fail). Warm-start priors. Backend-agnostic wrapper (used over G-Memory).
- **Results**: ALFWorld/ScienceWorld/PDDL + TriviaQA/WebWalker/GAIA, 3 frameworks, 3 backbones; top in 9/18 (GPT-4.1-mini), 15/18 (Sonnet-4) cells; 5–20% fewer tokens.
- **Relevance**: validates "small learned controller over frozen LLM, no extra LLM calls" = our Stage-1 design. Differences: tabular/discrete, no explicit budget constraint, tasks are embodied agents not conversational QA, no LoCoMo.

### A5. OSL-MR — Learning What to Remember: Observability-Safe Memory Retention via Constrained Optimization — arXiv:2606.10616 (Jun 2026, HKUST/Huawei) ★★★
*Read: full structured report.*
- **Problem**: which memories to *keep* under a hard storage budget, over a long horizon (sequential, not per-query).
- **Formulation**: POMDP; state = (retained cache C_{t-1}, per-memory freshness Φ_t, history H_t); action = subset to keep s.t. Σ size ≤ B_t; evicted items recoverable only via costly reacquisition. Reward r_t = α_hit·token-weighted gold coverage + α_full·full-coverage − α_store·storage − α_miss·miss − α_reacq·reacq − α_stale·stale. Proves single-step version NP-hard.
- **Observability separation**: deployed policy uses only online features; gold evidence etc. only for offline supervision.
- **Method**: Mixed-Score heuristic (freshness, recency, query overlap, entity overlap, session/speaker flags, size penalty) → greedy knapsack. Learned: small MLP predicts per-memory *evidence membership* (weighted BCE vs. gold evidence), optionally with Mixed-Score as input prior; greedy fill by logit. BC-learner (imitate oracle-guided local search) is worse than direct evidence supervision.
- **Results**: evidence P/R/F1 + reward (NOT end-task QA accuracy). LoCoMo B=128: F1 .263 vs Mixed-Score .087, recency/GA < .03; GA-LLM importance ≠ evidence utility. Synthetic DP-solvable instances: myopic optimum has 31.5% gap under shifting demand; OSL-MR 10.1%, ≈ Lookahead-4.
- **Relevance**: closest formulation to our "slot/storage budget" eviction. Gaps: evaluates evidence F1 not answer accuracy; supervised proxy, not RL on task reward; flat notes, no graph; not compared to Mem0/Zep. We should adopt its observability separation and reward terms, and show end-task accuracy.

### A6. What Eviction Destroys: Restore-Counterfactual Audit of Forgetting — arXiv:2609.08279 (Sep 2026, Megagon; COLM'26 workshop) ★★
*Read: full text.*
- Instrument, not a system. Per-question restore of gold evidence → classify each oracle-answerable error as irreversible (evicted), recoverable (retained but not retrieved), residual (reader misuse).
- LongMemEval-S (470 Qs, ~102k tok histories), store budgets 80k/30k/8k, FIFO/random/redundancy/LLM-importance eviction, GPT-4o-mini reader+judge, BM25-lite top-60.
- Findings: destruction dominates (irr share .67–.73 at 80k, 1.00 at 8k); LLM-importance slightly better at 80k (.60); at matched accuracy no policy differs; residual errors are cross-session aggregation failures that shrink with a stronger reader. **Budget–accuracy frontiers aren't comparable unless retrieval regime is reported.**
- **Relevance**: evaluation methodology for our eviction policy — report irreversible/recoverable split; always state retrieval regime; tight budgets → retention matters more than retrieval. Code: github.com/megagonlabs/restore-counterfactual. Cites more budgeted-memory work: EMBER 2606.05894, DeMem 2605.10870, BudgetMem 2602.06025, WhenLoss 2605.24579, AgingBench 2605.26302.

### A7. BudgetMem — Learning Query-Aware Budget-Tier Routing for Runtime Agent Memory — arXiv:2602.06025 (Feb 2026, NTU/UIUC; ICML 2026) ★★★
*Read: full structured report.*
- **Setting**: runtime (query-time) memory extraction over retrieved chunks (Contriever top-5), not offline construction.
- **Pipeline**: Filter → {Entity, Temporal, Topic} extractors (parallel) → Summarizer. Every module exposes LOW/MID/HIGH tiers realized three ways: implementation (rules → BERT → LLM), reasoning (direct → CoT → reflection), capacity (3B → 8B/32B → 70B/80B).
- **Router**: shared lightweight policy; state = embedding of (query, module input, module id); action = tier; **PPO** with reward r = r_task + λ·α·r_cost, r_cost = 1 − clip(quantile-normalized $cost); α = std(r_task)/std(r_cost) reward-scale alignment (without it the router collapses to LOW).
- **Results**: LLaMA-3.3-70B / Qwen3-Next-80B; beats ReadAgent, MemoryBank, A-MEM, LangMem, Mem0, MemoryOS, LightMem on LoCoMo/LongMemEval/HotpotQA (e.g. LongMemEval judge 60.5 vs LightMem 48.5). Smooth λ-controlled Pareto frontiers; router overhead ~50 ms.
- **Relevance**: canonical "cost-aware RL router" baseline; controls *compute* budget (which model/tier), not memory *content/size*. Reward-scale alignment trick is directly reusable for our λ-weighted reward.

### A8. EMBER — Efficient Memory via Budgeted Evidence Retention — arXiv:2606.05894 (Jun 2026, UW-Madison/NVIDIA) ★★★
*Read: full text (main paper).*
- **Setting**: Budgeted Pre-Query Retention — write memory during ingestion without knowing the query; retained source-evidence tokens ≤ B_ret; read only from retained memory. New protocol LongMemEval-RR.
- **Method**: LLM writer (Qwen2.5-7B/14B) emits "answerability probes" per chunk → evidence capsules (verbatim source excerpt ≤256 tok + entity anchors + surface/intent retrieval keys + update mode insert/merge/overwrite/skip). Deterministic BudgetUpdate enforces B_ret. Reader retrieves top-10 capsules, selects, answers (GPT-4o reader).
- **Training**: GRPO (G=16), budget sampled from {512..8192} per rollout; reward R = Q·(α_Q + α_E·evidence survival + α_L·lookup rank + α_P·selection purity + α_W·valid writes) − λ_budget·overrun/B (answer-gated auxiliaries). Trained on RULER-HotpotQA, MuSiQue, 2Wiki — not on LongMemEval.
- **Results** @8192: F1 0.302 (14B) / 0.277 (7B) vs best budgeted baseline 0.177, Memory-R1 adapted 0.157, recency 0.083; oracle retention 0.450; full-log RAG 0.365.
- **Relevance**: strongest "learned write under hard token budget, trained on end-task reward". Heavy (7–14B RL); flat capsules, no graph; F1 not judge. Our differentiator must be elsewhere (lightweight policy, joint write/evict/retrieve, graph, matched-budget comparison to full systems).

### A9. DeMem — Remember the Decision, Not the Description: Rate-Distortion Framework for Agent Memory — arXiv:2605.10870 (May 2026, Fudan/CUHK/Monash/Meta) ★★★
*Read: full structured report.*
- **Theory**: memory-constrained contextual bandit; K runtime memory states; decision distortion; exact forgetting boundary (histories can share a state iff a common ε-optimal action exists); covering/packing bounds; optimal K-partition is NP-complete; regret Õ(√AKT) + compression + certification terms, near minimax.
- **Method**: K-slot memory (bounded textual summaries); query-aware router to slots; split a slot only when reward data *certify* a decision conflict (cannot-link graph + greedy coloring).
- **Results**: LoCoMo LLM-judge **0.911 (GPT-4o-mini) / 0.920 (GPT-4.1-mini)**; LongMemEval 0.853 / 0.896; beats FullContext, RAG, LangMem, Mem0, Zep, Nemori, EMem-G, Mnemis, MemSkill, MemAct. Descriptive similarity weakly predicts evidence compatibility on LoCoMo (Spearman 0.103, AUC 0.548). Splits fire on 4.6% of routing events, 85% precision. Human–judge κ=0.79.
- **Relevance**: current absolute-accuracy bar on LoCoMo (~91–92%). Supports "decision/utility-based, not similarity-based" memory. Our matched-budget claim must hold against numbers like these.

---

## B. RL-trained memory managers (LLM as policy)

### B1. Memory-R1 — arXiv:2508.19828 (Aug 2025, LMU/MCML et al.) ★★★
*Read: full structured report.*
- Two RL-finetuned LLM agents (LLaMA-3.1-8B, Qwen2.5-3/7/14B; PPO or GRPO via veRL on 4×H100): **Memory Manager** chooses ADD/UPDATE/DELETE/NOOP per extracted fact (+content); **Answer Agent** gets 60 RAG candidates, does "memory distillation" (select relevant) then answers.
- Reward: exact match of answer (Manager's reward via frozen Answer Agent). Only **152 LoCoMo QA pairs** for training. Beats MemoryOS by ~20–30% relative (F1/B1/J) on LoCoMo; zero-shot transfer to MSC, LongMemEval. RL > SFT on GPT-5 trajectories. EM reward better balanced than LLM-judge reward (judge reward → verbosity).
- **No budget term**; memory bank grows freely; retrieval is fixed top-60 similarity.
- **Relevance**: canonical RL-memory baseline; its train split (152 QAs) and LoCoMo protocol are reusable. Stage-2 of our plan (GRPO small LLM) ≈ Memory-R1 + budget.

### B2. AgeMem — Agentic Memory: Unified LTM/STM Management — arXiv:2601.01885 (Jan 2026, Alibaba/Wuhan) ★★
*Read: full structured report.*
- Memory ops as tools inside the agent's own policy: LTM ADD/UPDATE/DELETE, STM RETRIEVE/SUMMARY/FILTER. Three-stage trajectories (LTM construction → STM under distractors → integrated QA). **Step-wise GRPO** broadcasting terminal advantage to all steps.
- Reward = task (LLM judge) + context mgmt (compression efficiency, preventive summarization before overflow, info preservation) + memory mgmt (storage quality, maintenance, relevance) + penalties (overflow, too many turns).
- Qwen2.5-7B / Qwen3-4B; ALFWorld, SciWorld, PDDL, BabyAI, HotpotQA; +4.8 / +8.6 pts over Mem0 / A-Mem; RL adds ~8.5 pts; ~3–5% fewer prompt tokens.
- **Relevance**: context-overflow penalty is a *soft* budget; shows multi-term reward speeds convergence. Not evaluated on LoCoMo.

### B3. Mem-α — Learning Memory Construction via RL — arXiv:2509.25911 (Sep 2025, Anuttacon/UCSD/Stanford) ★★
*Read: full structured report.*
- Qwen3-4B trained with GRPO (no KL) to write into core (≤512 tok) / semantic / episodic memory via insert/update/delete tool calls, chunk by chunk.
- Reward = QA correctness of final memory via RAG + tool-format + **compression 1 − l_mem/l_input (β=0.05)** + LLM-judged memory-content validity (critical; γ=0 collapses).
- Trained on ≤30K-token instances, generalizes to 400K+ (MemoryAgentBench): avg 0.592 vs long-context 0.461, RAG 0.502, MemAgent 0.198, MEM1 0.071. RL-tuned 4B > GPT-4.1-mini with same framework (0.642 vs 0.517).
- **Relevance**: compression reward = soft storage budget; structured multi-type memory beats flat. Evaluation on MemoryAgentBench (not LoCoMo).

### B4. MemAgent — Multi-Conv RL-based Memory Agent — arXiv:2507.02259 (Jul 2025, ByteDance Seed/Tsinghua AIR) ★★
*Read: full structured report.*
- Long-document QA: read 5K-token chunks sequentially, **overwrite a fixed 1024-token memory** each step (O(N)); answer from memory only. Multi-Conv DAPO (GRPO variant), binary verifier reward, advantage from final conversation broadcast to all memory-update conversations. Qwen2.5-7B/14B, 8K window.
- RULER-HotpotQA: >71% accuracy at 3.5M tokens (<10% drop); LongBench-QA avg 51.0 (14B). Memory length 256–4096 fairly robust.
- **Relevance**: fixed-size memory = hard budget, learned overwrite. But single-query, query-visible (the question is known while reading) → not the persistent multi-query setting; EMBER shows it degrades badly when adapted pre-query (0.131 F1).

### B5. Memory-R2 — Fair Credit Assignment for Long-Horizon Memory Agents — arXiv:2605.21768 (May 2026, LMU/Huawei) ★★★
*Read: full structured report.*
- Shared Qwen2.5-7B backbone plays Fact Extractor + Memory Manager (INSERT/UPDATE/DELETE) chunk-wise across sessions. Problem: rollouts diverge in memory state → GRPO comparisons unfair ("reward contamination").
- **LoGo-GRPO**: global rollouts + local re-rollouts of one session from a shared anchor memory state; length-normalized step-level loss; curriculum 8→16→32 sessions (without it F1 collapses to 24).
- Reward: session-level QA F1 − **compression penalty** on memory tokens exceeding α·cumulative session tokens (λ_comp=0.3 best).
- LoCoMo (Qwen2.5-7B everywhere): **F1 50.60, B1 44.01, J 80.99** vs Memory-R1 F1 43.14. Trained on only 2 LoCoMo conversations. Transfers to LongMemEval, MSC, MemBench; 3B: F1 10.3→46.8.
- **Relevance**: SOTA RL memory manager on LoCoMo for open 7B; soft storage budget via penalty. The anchor-state re-rollout idea is a must for our Stage-2 GRPO; curriculum over #sessions.

### B6. MemSkill — Learning and Evolving Memory Skills — arXiv:2602.02474 (Feb 2026, NTU/UIUC) ★★★
*Read: full structured report.*
- **Controller** (small, trainable): embeds text span + retrieved memories (frozen embedder → MLP), scores each skill description with a shared scorer (variable-size skill bank), picks Top-K skills (Gumbel-Top-K). **PPO** on episode-level downstream QA reward. **Executor** = frozen LLM doing skill-conditioned extraction in one call per span (span-level, not per-turn). **Designer** LLM evolves the skill bank from clustered hard failure cases (refine + add skills; rollback snapshots).
- Initial skills INSERT/UPDATE/DELETE/SKIP; evolved LoCoMo skills e.g. "Capture Temporal Context", "Capture Activity Details".
- Best on LoCoMo & LongMemEval (F1, LLM-judge) vs Mem0, A-MEM, LangMem, MemoryOS, LightMem, etc.; transfers LLaMA→Qwen, LoCoMo→LongMemEval→HotpotQA; fewer LLM calls/tokens (span 512).
- **Relevance**: *closest architecture to our Stage 1* (small RL controller over frozen LLM executor). Differs: no budget in state/reward; controls extraction style, not retention/eviction/retrieval under budget. We can reuse the variable-action scorer design.

### B7. DeltaMem — Agentic Memory Management via RL — arXiv:2604.01560 (Apr 2026, Alibaba Tongyi/ZJU) ★★
*Read: full structured report.*
- Single-agent ReAct memory manager (add/update over atomic timestamped sentences) instead of multi-agent extract→retrieve→update pipelines (argued lossy).
- Synthesized persona data with **operation-level target memory states** (profile → 25 events → intra/inter-event memory evolution → dialogues). Reward = soft-F1 of a **memory-based Levenshtein distance** (optimal-transport alignment of predicted vs target memory state + keyword "lexical fidelity"), 0.8 weight, + format + retrieval rewards; GRPO.
- DeltaMem-8B-RL: LoCoMo LLM-judge **75.13**, F1 50.72 (> LightMem, Zep); HaluMem QA 66.43; PersonaMem 63.61. RL +4.1 judge. Retrieval queries/memory 0.13 vs Mem0 1.00.
- **Relevance**: dense state-based reward avoids sparse QA reward — an option for our Stage-2. No budget.

### B8. VerMem — Verifiable Memory: Unified Memory Management with Local and Global Verifiers — arXiv:2608.03137 (Aug 2026, SYSU/NTU/Tencent) ★★
*Read: full structured report.*
- State (task, LTM, **budgeted active context C_t**, episodic history H_t), 8,192-token policy input. Seven tools: Add/Update/Delete (LTM), Retrieve/Filter/SelectEpisode/Summarize (STM) + null.
- SFT warm-up (DeepSeek-V3.2 teacher) → 3-phase GRPO (LTM → STM → full). Credit = local verifier score per operation (frozen DeepSeek-V3.2; relevance/grounding/progress/fidelity) + global composite (task, evidence recall + coherence, terminal memory consistency, **efficiency = 1 − online cost, gated on task ≥ 0.5**) − constraint penalties.
- Qwen2.5-7B avg 48.01 over ALFWorld/SciWorld/PDDL/BabyAI/HotpotQA (+6.05 over AgeMem); reaches SR 40 at 20% fewer tokens than AgeMem; SR@2,500 tok 44.3.
- **Relevance**: success-gated efficiency reward is a good trick (don't reward cheapness when wrong). Token-budgeted SR@B metric = our matched-budget evaluation idea.

### B9. TrustMem — Learning Trustworthy Memory Consolidation — arXiv:2606.25161 (Jun 2026, Samsung/Notre Dame) ★
*Read: full structured report.*
- WRITE/REVISE/PRUNE per chunk; frozen-LLM transition verifier scores coverage / preservation / faithfulness. Rewards: task + efficiency (1 − |M|/Σ|c|) + action-exec + content-type + verifier; **TR-GRPO** = GRPO + DPO-style ranking between best/worst-verified transitions in the group.
- Mem-α val 66.3 (+4.4 over Mem-α); MemoryAgentBench 65.7 (+6.5); HaluMem extraction F1 69.45; omission 8.1%, corruption 0.14%, hallucination 0.01%.
- **Relevance**: memory *corruption* is a real failure mode of LLM-written memory — argues for keeping raw provenance (like JustMem/EMBER) in our design.

---

## C. Memory systems (heuristic / LLM-prompted control) — the products we must beat

### C1. Mem0 / Mem0ᵍ — arXiv:2504.19413 (Apr 2025, Mem0 Inc.; ECAI 2025) ★★★
*Read: full structured report.*
- **Extraction**: LLM (GPT-4o-mini) reads new message pair + async conversation summary + last m=10 messages → candidate facts. **Update**: for each fact retrieve s=10 similar memories; LLM tool call picks ADD/UPDATE/DELETE/NOOP. Dense vector DB.
- **Mem0ᵍ**: directed labeled entity graph (Neo4j); entity extractor + relationship generator LLMs; conflicting edges marked invalid (not deleted) for temporal reasoning; retrieval = entity-centric subgraph expansion + semantic triplet matching.
- **LoCoMo (GPT-4o-mini, LLM-judge, 10 runs)**: Mem0 66.88, Mem0ᵍ 68.44, full-context 72.90, best RAG ~61, Zep 66.0 (open-domain 76.6), LangMem 58.10, OpenAI memory 52.90, A-Mem 48.4. Temporal: Mem0ᵍ 58.13 best. Memory size: Mem0 ~7K tok/conv, Mem0ᵍ ~14K, **Zep >600K** (raw conv ~26K). p95 latency 1.44 s vs 17.1 s full-context (−91%).
- **Relevance**: *the* reference evaluation protocol (LoCoMo cats 1–4, GPT-4o-mini, J score, tokens + latency). Graph helps temporal, not multi-hop. No budget control — memory grows unboundedly.

### C2. Zep / Graphiti — Temporal Knowledge Graph Architecture for Agent Memory — arXiv:2501.13956 (Jan 2025, Zep AI) ★★★
*Read: full structured report.*
- Graphiti: bi-temporal KG with 3 tiers — episode subgraph (raw messages), semantic entity subgraph (entities + fact edges with validity intervals), community subgraph (label-propagation clusters with summaries). LLM extraction, entity resolution, edge invalidation on contradiction.
- Retrieval: cosine + BM25 + BFS over graph → rerank (RRF / MMR / node-distance / episode-mentions / cross-encoder) → context constructor.
- DMR 94.8% (gpt-4-turbo) vs MemGPT 93.4%; LongMemEval up to +18.5% accuracy, −90% latency vs full-context.
- **Relevance**: strongest open graph memory; our hybrid vector+graph substrate should borrow its temporal edge invalidation. Very large memory footprint (Mem0 measured 600K tokens on LoCoMo) → ideal foil for a *matched-budget* comparison.

### C3. A-MEM — Agentic Memory for LLM Agents — arXiv:2502.12110 (Feb 2025, Rutgers; NeurIPS 2025) ★★
*Read: full structured report.*
- Zettelkasten notes: content, timestamp, LLM keywords/tags/context, embedding, links. New note → top-k neighbors → LLM decides links → LLM "memory evolution" updates neighbors' attributes. Retrieval top-k + linked notes.
- LoCoMo (F1/BLEU; not J in original): big multi-hop gains; ~1.2K tokens per memory op (−85–93% vs LoCoMo/MemGPT). Later independent evals put it at J ≈ 48 (Mem0 paper) / 67.9 (JustMem, GPT-4.1-mini).
- **Relevance**: standard baseline; link graph = lightweight graph substrate idea. Very expensive construction (1.19M tokens on LoCoMo per JustMem).

### C4. LightMem — Lightweight and Efficient Memory-Augmented Generation — arXiv:2510.18866 (Oct 2025, ZJU; ICLR 2026) ★★★
*Read: full text (main paper, via PDF query of all main pages).*
- Atkinson–Shiffrin-inspired: (1) sensory memory: LLMLingua-2 token pre-compression (keep ratio r) + topic segmentation (attention local maxima ∩ embedding-similarity drops) with 512-token buffer; (2) topic-aware STM buffer (threshold th) → LLM summaries per topic, entry = {topic, emb(sum), user, model turns}; (3) LTM with **soft insert at test time + offline "sleep-time" parallel update** (only newer entries may update older; top-k similar update queues).
- **LoCoMo GPT-4o-mini ACC**: LightMem 72.99 (r=0.8, th=768) vs FullText 71.83, A-MEM 64.16, NaiveRAG 63.64, Mem0 61.69, MemoryOS 58.25, LangMem 57.20; ~85–100K construction tokens vs Mem0 1.69M; 30–40 API calls vs 1.6K. LongMemEval-S GPT-4o-mini 68.64 vs A-MEM 62.60, FullText 56.80. GPT-4o-mini judge; all-MiniLM-L6-v2 embeddings.
- **Relevance**: strongest cheap *construction*; code open (zjunlp/LightMem) → easy baseline. Note cross-paper inconsistency: Mem0 = 66.88 (own paper) vs 61.69 (here) → we must re-run all baselines under one protocol.

### C5. SimpleMem — Efficient Lifelong Memory for LLM Agents — arXiv:2601.02553 (Jan 2026, UNC/Berkeley/UCSC) ★★
*Read: full structured report.*
- (1) entropy-aware window filter (drop low-novelty windows) → atomic memory units with coreference resolution and absolute ISO timestamps; (2) multi-view index: dense (text-embedding-3-small) + BM25 + symbolic SQL metadata (LanceDB); background recursive consolidation of affinity clusters (semantic × temporal decay) into abstractions, originals archived; (3) **query-complexity classifier → dynamic k ∈ [3, 20]**.
- LoCoMo GPT-4.1-mini F1 43.24 vs Mem0 34.20; ~530–580 tokens/query (vs 16.9K full context, ~980 Mem0); construction 92.6 s/sample vs Mem0 1351 s. Ablation: w/o compression −56.7% temporal F1; w/o consolidation −31.3% multi-hop F1; w/o adaptive retrieval −19–27%.
- **Relevance**: *adaptive k via a heuristic classifier* — a learned budget-aware policy is a direct upgrade; timestamp normalization is essential for temporal questions.

---

## D. Graph memory

### D1. MRAgent — Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents — arXiv:2606.06036 (Jun 2026, NUS) ★★★
*Read: full structured report.*
- Heterogeneous **Cue–Tag–Content** graph: cues (keywords/entities) → associative tags (short relational summaries) → contents (episodes on a timeline / semantic facts); topic abstraction layer over episodes. Built by LLM distillation (pronoun + time normalization, segmentation, cue/tag extraction).
- **Active reconstruction**: iterative LLM loop — select traversal actions (cue→tag, (cue,tag)→content, content→new cues/tags), expand, LLM-route/prune candidates, LLM decides termination. Proof: active retrieval with budget T≥2 strictly more expressive than passive.
- LoCoMo LLM-judge **84.21 (Gemini-2.5-Flash) / 88.32 (Claude-Sonnet-4.5)** vs Mem0 68.31; LongMemEval +32% relative; 118K tokens/sample vs 245K (Mem0) – 3.27M (LangMem). Multi-hop evidence recall +30% over successive turns; deeper > wider retrieval.
- Limitation: memory graph static, grows monotonically (no consolidation/forgetting). **Relevance**: strong graph baseline; *traversal depth/breadth is a natural action for our budgeted controller*; their stated gap (no forgetting, unbounded growth) is ours to fill.

### D2. HippoRAG — Neurobiologically Inspired Long-Term Memory — arXiv:2405.14831 (May 2024, OSU/Stanford; NeurIPS 2024) ★★
*Read: full structured report.*
- LLM OpenIE → schemaless KG of noun-phrase nodes + relation edges; synonym edges via dense-encoder similarity > 0.8; node specificity (1/#passages, IDF-like). Query NER → seed nodes → **Personalized PageRank** → score passages via node→passage matrix. Single-step multi-hop retrieval.
- 2WikiMultiHopQA R@5 +20% over ColBERTv2; all-recall +38%; 10–30× cheaper, 6–13× faster than IRCoT online. Errors: NER 48%, OpenIE 28%, PPR 24%.
- **Relevance**: PPR over entity graph is a cheap, non-LLM graph retrieval primitive we can give the controller as an action (vs MRAgent's expensive LLM traversal).

### D3. Selective Forgetting: Graph-Based Memory Framework for Long-Term LLM Agents — arXiv:2608.28978 (Aug 2026, Toronto Metropolitan) ★★
*Read: full structured report.*
- Typed KG (9 node labels; access/recency metadata), GPT-4o-mini extraction, dedup (title index + cosine > 0.92), retrieval = cosine > 0.75 top-5 roots + 2-hop BFS ≤ 15 nodes. **Heuristic importance** = 0.35 recency (90-day half-life) + 0.25 log frequency + 0.20 log degree + 0.20 turn-age decay; prune < 0.10 every 400 turns.
- **Graph RAG < flat RAG on LongMemEval**: judge 0.454 vs 0.536, F1 .417 vs .468 (significant). Worst on single-session-assistant (0.607 vs 0.911, verbatim lost in extraction) and knowledge-update; only temporal improves. Forgetting cut nodes 9.8% / storage 9.5% with no significant accuracy change (judge .300 → .284).
- **Relevance**: key empirical caution — graph-only memory loses verbatim detail; hybrid must keep raw text/provenance. Their hand-weighted importance score is exactly what a learned eviction policy should replace; a 10% prune is a weak budget — we should test much tighter budgets.

---

## E. Benchmarks & evaluation methodology

### E1. LoCoMo — Evaluating Very Long-Term Conversational Memory of LLM Agents — arXiv:2402.17753 (Feb 2024, UNC/Snap; ACL 2024) ★★★
*Read: full structured report.*
- 10 released conversations (up to 35 sessions, ~300 turns, ~9K–26K tokens) between persona-driven LLM agents grounded in temporal event graphs, human-edited; image sharing. Tasks: QA (single-hop, multi-hop, temporal, open-domain/commonsense, adversarial), event summarization, multimodal dialogue generation.
- Findings: long-context and RAG help but trail humans; RAG over extracted *observations* beats raw dialogue or summaries; temporal and adversarial questions hardest.
- **Our protocol**: `locomo10.json`, 1,986 QA; category ids in file: 1=multi-hop(282), 2=temporal(321), 3=open-domain(96), 4=single-hop(841), 5=adversarial(446). Standard practice (Mem0, LightMem, JustMem): evaluate cats 1–4 = **1,540 Qs**, LLM-judge (J) + F1 + BLEU-1, GPT-4o-mini.

### E2. LongMemEval — Benchmarking Chat Assistants on Long-Term Interactive Memory — arXiv:2410.10813 (Oct 2024, UCLA/Tencent; ICLR 2025) ★★★
*Read: full structured report.*
- 500 human-curated questions, 5 abilities (information extraction user/assistant/preference, multi-session reasoning, knowledge update, temporal reasoning, abstention); needle-in-haystack histories: **S ≈ 115K tokens / ~50 sessions**, M ≈ 1.5M tokens / 500 sessions. GPT-4o judge (>97% human agreement).
- Commercial assistants drop 37–64%; long-context LLMs drop 30–60% vs oracle evidence.
- Unified framework: indexing (value, key) → retrieval (query) → reading. Findings: **round-level values best**; summaries/facts lose info (except multi-session aggregation); **fact-augmented keys** +9.4% recall, +5.4% QA; **time-aware query expansion** +6.8–11.3% temporal recall (needs strong LLM); **Chain-of-Note + JSON** reading; optimal retrieved-token budget depends on reader strength (8B saturates ~3K tokens, GPT-4o keeps improving past 20K).
- **Relevance**: second benchmark; its design findings are direct inputs to our substrate; "budget depends on reader" supports budget-conditioned policy.

### E3. Harness the Memory: Holistic Evaluation of Memory Substrates — arXiv:2608.15008 (Aug 2026, UIC/UW/McGill/MBZUAI/UCLA) ★★★
*Read: full structured report.*
- Landscape of 52 systems (2023–26): evaluations concentrate on LoCoMo/LongMemEval, mostly GPT backbones, efficiency rarely reported.
- Controlled harness: 11 substrates in 7 families (dense, BM25, gist index, evolving notes, **dual-level KG + vector**, hierarchical tree, distilled strategies, skill bundles, LoRA adapter, full context, episode re-prefill); Qwen3-8B/32B, Gemma-4-26B backbones; aux LLM GPT-4o-mini; 26 metrics; LoCoMo, MemoryAgentBench, ALFWorld, BigCodeBench-Hard.
- Findings: (1) **no substrate dominates**; graph+vector (M5) best on LoCoMo/LME-S but 10–100× slower, Pareto-dominated on agent tasks; (2) **retrieval breadth k helps QA but hurts agentic tasks** (attention dilution away from current observation); (3) structural substrates scale badly with history length; distilled substrates scale gracefully → "trade read breadth for write depth".
- **Relevance**: empirical case for an *adaptive, regime-aware, multi-substrate router* — i.e., our learned controller choosing substrate/k under budget. Mem0/Zep/MemGPT excluded as too costly.

---

## F. Efficient / LLM-free memory control

### F1. Zero-Mem — Zero-Token Memory Operations for LLM Agents — arXiv:2607.29377 (Jul 2026, PolyU/SWUFE/Jilin) ★★★
*Read: full structured report.*
- **No LLM calls for any memory operation**; only the final reader is an LLM. Keeps raw traces with provenance. Relational trace graph from spaCy NER (entity↔context co-occurrence edges + adjacency edges) + temporal hierarchy (turn / window / episode / local span). BM25 + BGE-M3 dense indices.
- Deterministic query profile (subjects, keywords, answer type, temporal cues) → routing weight ρ between graph view (entity activation + **Personalized PageRank**) and hierarchical coarse-to-fine view → fused ranking → evidence closure (graph bridges + neighbor turns) → deterministic calibration before/after the reader.
- LoCoMo (GPT-4o-mini) avg F1 +5.40 over GAM (best baseline), best on single-hop/temporal/open-domain; HotpotQA up to 448K tokens best; 0 memory tokens vs LightMem 0.87M; 57.6% lower memory latency (0.22 s/query). Top-K 10 best; graph+hierarchy both needed.
- **Relevance**: shows a *non-generative* hybrid graph+vector substrate is competitive and extremely cheap → attractive substrate for us (cheap to run on a 6 GB GPU, construction cost ≈ 0), onto which a learned controller replaces its deterministic routing ρ / k / closure rules.

### F2. Jev-Mem — System-One-Controlled Agentic Memory — arXiv:2609.23986 (Sep 2026, UT Dallas) ★★★
*Read: full structured report.*
- Memory control as typed, bounded predictions (scores/choices from a non-generative "System-One" model, Jev/TypeSafe AI) instead of LLM generation; LLM only for answering. Canonical nodes + 4 relational views (semantic, temporal, causal, entity) + vector + lexical index; keeps all raw observations.
- Retrieval as a control loop: view-relevance estimation, **graph-expansion budget (80 units) allocated across views**, beam 10, depth ≤ 8, ≤ 60 nodes; adaptive stopping on sufficiency / missing / contradiction scores.
- LoCoMo LLM-judge (GPT-4o-mini) **0.777** overall (incl. adversarial 0.962) vs MAGMA 0.700; construction 158 s vs Nemori 1,044 s; 0.93 s/query. No ablations, one benchmark, some table/text inconsistencies.
- **Relevance**: very close in spirit to our Stage 1 (cheap controller over multi-relational graph with explicit expansion budgets). But thresholds/budgets are hand-set, controller is not trained on end-task reward, budget not in the objective → our learned budget-conditioned policy is the delta.

---

## G. Learned eviction in systems (transferable techniques)

### G1. KVP — Learning to Evict from Key-Value Cache — arXiv:2602.10238 (Feb 2026, Apple) ★★★ (method donor)
*Read: full structured report.*
- KV eviction as **ranking**: if optimal kept-sets are nested across budgets (true for additive rewards), a single total order gives the optimal top-b set for every budget b → **one budget-agnostic policy**.
- Per-head small MLP (~650K params) scores tokens from (k, v, position) only (no query, no attention). Plackett–Luce stochastic ranking sampled in parallel via **Gumbel-Sort**; reward = negated normalized **area under the cost-vs-budget curve** (cost = future attention mass of evicted tokens); **REINFORCE with leave-one-out baseline**; fully offline from precomputed traces (<30 min for 112 agents on 8×H100).
- Beats StreamingLLM, KeyDiff, K-Norm, LagKV and matches/beats attention-based TOVA/SnapKV on RULER-4K/128K, OASST2, LongBench; RL beats supervised learning-to-rank (pointwise/pairwise/listwise/soft-sort).
- **Relevance (big)**: gives us a concrete, cheap, principled training recipe — a *budget-agnostic retention/retrieval ranker over memory records*, trained with an all-budgets AUC reward using end-task (QA) utility instead of attention. Directly bridges gap #4 (systems RL eviction ↔ agent memory).

### G2. Cold-RL — Learning Cache Eviction with Offline RL for NGINX — arXiv:2508.12485 (Aug 2025) ★★
*Read: full text.*
- On eviction, sample K coldest (LRU-tail) objects; 6 features (age, size, hit count, inter-arrival, TTL remaining, origin RTT); **dueling DQN (~10K params)** outputs victim bitmask; ONNX sidecar with **500 µs hard timeout → LRU fallback**. Trained offline by replaying access logs in a cache simulator; reward +1 if a retained object is hit again before TTL.
- Hit ratio under high pressure 0.354 vs ARC 0.144 (+146%), medium +15%, low ≈ tie; trap workload 0.421 vs LRU 0.056; p95 inference 342 µs; 3 months production, −23% origin traffic.
- **Relevance**: pattern for our controller — tiny model, cheap per-item features, candidate pre-filtering (score only the "tail"), offline training from logged traces/simulator, safe heuristic fallback; gains concentrate at tight budgets (same as Retain-or-Consolidate and Megagon audit).

---

## H. Foundational agent-memory architectures

### H1. MemGPT — Towards LLMs as Operating Systems — arXiv:2310.08560 (Oct 2023, UC Berkeley) ★★
*Read: full text (main paper).*
- Virtual context management: main context = system instructions + fixed-size working context + FIFO message queue (with recursive summary of evicted messages); external = recall storage (all messages) + archival storage (vector DB). LLM moves data via function calls; function chaining with heartbeat.
- Queue manager: **memory-pressure warning at 70% of context**, flush at 100% (evict ~50%, re-summarize). i.e., eviction trigger is a fixed threshold rule; *what* to save is decided by the prompted LLM.
- Doc QA accuracy flat as #docs grows; nested KV retrieval solved to 4 levels with GPT-4; MSC deep memory retrieval & conversation openers.
- **Relevance**: first to frame context as a bounded resource with explicit pressure signals — the "budget-in-state" idea in prompted form; our controller learns what MemGPT prompts for.

### H2. Generative Agents — Interactive Simulacra of Human Behavior — arXiv:2304.03442 (Apr 2023, Stanford/Google; UIST 2023) ★★
*Read: full text (architecture sections).*
- Memory stream of observations; retrieval score = α_rec·recency (exponential decay 0.995 per game-hour since last access) + α_imp·importance (LLM 1–10 poignancy rating at write time) + α_rel·relevance (embedding cosine), min-max normalized, **all α = 1**; top-ranked memories that fit the context window are included.
- Reflection triggered when summed importance of recent events > 150 (≈2–3×/day): LLM asks 3 salient questions over last 100 records → retrieves → writes cited insights (reflection trees).
- **Relevance**: the canonical hand-weighted scoring rule; OSL-MR shows GA-style importance ≠ evidence utility. Our learned scorer generalizes this (learned weights + budget-conditioning); GA features (recency, importance, relevance, access) are natural policy inputs.

---

## Reading log

- 2026-09-24: 35 papers read (A1–A9, B1–B9, C1–C5, D1–D3, E1–E3, F1–F2, G1–G2, H1–H2).
- Still worth reading for the thesis write-up (not blocking): MemOS 2507.03724, MemoryOS (EMNLP'25), GAM 2604.12285, SodaMem 2608.08055, RippleMem 2608.13334, LeanMem 2608.03463, MemForest 2609.08273, EdgeMem 2609.05553, CMI-Mem 2607.20553, Hindsight Memory-PRM 2608.29605, LIMBO 2609.14138, Compact-Memory 2609.04915, LoCoMo-Plus, MemoryBank 2305.10250, RecallM 2307.02738.
