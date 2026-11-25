# Literature Survey

**Thesis**: Learning to Remember: Reinforcement-Learned Memory Control for LLM Agents Under Bounded Resources

Last updated: 2026-09-24 · Status: v2 (35 papers read in full; per-paper notes in
[`papers/READING_NOTES.md`](papers/READING_NOTES.md), cited below as [A1], [B5], … )

> v1 (2026-08-07) was written mostly from abstracts and secondary sources. v2 is a
> rewrite after reading 35 primary papers. The most important change: **between
> Feb and Sep 2026 a cluster of budget-aware and learned-memory-control papers
> appeared** (BudgetMem, EMBER, OSL-MR, OAS, MemoryCPT, MemCon, DeMem, JustMem,
> Jev-Mem, Zero-Mem). The v1 claim that "no system treats the resource budget as
> part of the decision problem" is no longer true and has been replaced by a
> narrower, defensible gap statement (§9).

---

## 1. Introduction and scope

"Agent memory" is the machinery that lets a stateless LLM persist, organise and
selectively recall information across turns, sessions and tasks. Every practical
deployment is resource-bounded: the reader LLM has a finite (and, in practice,
much smaller *effective*) context window [E2], each memory operation that calls
an LLM costs tokens, money and latency [C1, C4, F1], and stores that grow without
bound degrade retrieval and cost more to search [D3, E3].

A memory system therefore makes four recurring decisions:

1. **Write** — what to extract/store from new interaction, and in what form
   (raw turn, atomic fact, summary, graph triple).
2. **Maintain** — update, consolidate, or **evict/forget** stored items, usually
   under some storage constraint.
3. **Read** — for a query, what to retrieve, how broadly/deeply, and how much of
   it to put in the reader's context.
4. **Control** — *who* makes decisions 1–3: fixed heuristics, a prompted LLM, an
   RL-fine-tuned LLM, or a small learned policy.

This survey covers (§3) benchmarks and evaluation methodology, (§4) memory
systems whose control is heuristic or LLM-prompted, (§5) graph memory, (§6)
learned memory control (RL-trained LLM managers and lightweight learned
controllers), (§7) budget-aware memory, (§8) learned eviction in adjacent systems
domains, then gives a comparison table (§9.1), reported LoCoMo results (§9.2), the
gap analysis (§10) and candidate thesis framings (§11).

---

## 2. Taxonomy

We classify each system on six axes (used in the comparison table, §9.1):

| Axis | Values |
|---|---|
| **Substrate** | raw log / turns · atomic facts or cards · summaries / hierarchy · entity/knowledge graph · hybrid graph + vector (+ BM25) · fixed-size text memory · KV cache |
| **Write policy** | log everything · LLM extraction (prompted) · learned (RL-fine-tuned LLM or small policy) · non-generative (NER/embeddings only) |
| **Forgetting / eviction** | none (unbounded) · heuristic (recency/decay/importance/TTL) · LLM-decided DELETE · learned under a hard budget |
| **Read policy** | fixed top-k similarity · hybrid rerank · graph traversal (BFS/PPR) · iterative LLM-driven retrieval · learned/adaptive k or route |
| **Controller** | heuristic · prompted LLM · RL-fine-tuned LLM (PPO/GRPO) · small learned policy (MLP/bandit/ridge) |
| **Budget treatment** | none · reported only (tokens/latency as outcome) · soft penalty in reward · **hard constraint enforced** · budget as policy input (budget-conditioned) |

---

## 3. Benchmarks and evaluation methodology

**LoCoMo** [E1] — 10 released multi-session conversations (up to 35 sessions,
~9K–26K tokens each) between persona-driven agents grounded in event graphs,
1,986 QA pairs. In `locomo10.json` the categories are 1 = multi-hop (282),
2 = temporal (321), 3 = open-domain (96), 4 = single-hop (841), 5 = adversarial
(446). The de-facto protocol (Mem0 [C1], LightMem [C4], JustMem [A1]) evaluates
**categories 1–4 (1,540 questions)** with an LLM judge (GPT-4o-mini) plus token F1
and BLEU-1, and reports memory tokens and latency.

**LongMemEval** [E2] — 500 human-curated questions testing information extraction
(user / assistant / preference), multi-session reasoning, knowledge updates,
temporal reasoning and abstention. *S* setting ≈ 115K tokens (~50 sessions), *M*
≈ 1.5M tokens. Long-context LLMs lose 30–60% vs. oracle evidence. Its design
study is directly useful to us: round-level values beat session or summary
values; fact-augmented keys add +9.4% recall; time-aware query expansion adds
+6.8–11.3% temporal recall; the reader's useful retrieved-token budget depends on
reader strength (an 8B reader saturates near 3K tokens, GPT-4o keeps improving
past 20K).

**Other benchmarks used in the literature**: LoCoMo-Plus (cognitive split) [A1],
LongMemEval-RR (budgeted pre-query retention) [A8], MemoryAgentBench [B3, E3],
HaluMem and PersonaMem [B7, B9], DMR [C2], agentic suites (ALFWorld, SciWorld,
PDDL, BabyAI, AppWorld, GAIA) [A4, B2, B8, B6].

**Methodological cautions established by the literature**

- *Cross-paper numbers are not comparable.* Mem0 on LoCoMo with GPT-4o-mini is
  66.9 in its own paper [C1] but 61.7 in LightMem's re-run [C4]; A-MEM ranges
  from 48.4 [C1] to 64.2 [C4] to 67.9 (GPT-4.1-mini) [A1]. Judges, prompts,
  backbones and category subsets differ. **We must re-run every baseline under
  one protocol.**
- *Budget–accuracy frontiers must report the retrieval regime* [A6]: with forced
  gold injection all eviction errors look "irreversible"; with top-k retrieval a
  share is retrieval failure. At tight budgets eviction damage dominates, so
  retention matters more than retrieval.
- *No substrate dominates* [E3]: graph + vector leads on LoCoMo/LongMemEval but is
  10–100× slower and loses on agentic tasks; retrieval breadth k helps QA but
  hurts agentic tasks (attention dilution).
- *Reader-utilisation errors* (gold evidence present, answer still wrong —
  mostly cross-session aggregation) persist and shrink with a stronger reader
  [A6, E2].

---

## 4. Memory systems with heuristic or LLM-prompted control

**Foundations.** *Generative Agents* [H2] introduced the memory stream with a
hand-weighted retrieval score (recency decay 0.995/hour + LLM-rated importance
1–10 + embedding relevance, all weights 1) and importance-triggered reflection.
*MemGPT* [H1] framed context as a bounded resource managed like OS virtual
memory: a memory-pressure warning at 70% of the window and a flush at 100% (evict
~50%, recursive summary), with a prompted LLM deciding what to page out.

**Production-style memory layers.**
- *Mem0 / Mem0ᵍ* [C1]: prompted extraction of salient facts + per-fact LLM tool
  call choosing ADD/UPDATE/DELETE/NOOP over the 10 most similar memories; the
  graph variant adds an entity graph (Neo4j) with invalidated rather than deleted
  edges. LoCoMo J 66.9 / 68.4 vs full context 72.9, ~7K / 14K memory tokens,
  p95 latency −91% vs full context. Graph helps temporal questions, not multi-hop.
- *Zep / Graphiti* [C2]: bi-temporal knowledge graph with episode, entity and
  community tiers, edge invalidation, and hybrid cosine + BM25 + BFS search with
  reranking. Strong on DMR/LongMemEval, but Mem0 measured **>600K memory tokens
  for ~26K-token LoCoMo conversations**.
- *A-MEM* [C3]: Zettelkasten notes with LLM-generated links and "memory
  evolution" of neighbours — expensive construction (~1.2M tokens on LoCoMo [A1]).

**Efficiency-oriented systems (2025–26).**
- *LightMem* [C4] (ICLR'26): LLMLingua-2 pre-compression, topic segmentation,
  topic-level STM summaries, soft inserts at test time, and offline "sleep-time"
  parallel consolidation. LoCoMo 73.0 (GPT-4o-mini) at ~1/20 of Mem0's
  construction tokens.
- *SimpleMem* [C5]: entropy filtering, atomic units with coreference and absolute
  timestamps, dense + BM25 + symbolic indices, recursive consolidation, and a
  **heuristic query-complexity classifier choosing k ∈ [3, 20]**; ~550 tokens per
  query.
- *JustMem* [A1]: ~18-token atomic cards with provenance; an LLM planner predicts
  two binary demands that a **hand rule** maps to LOOKUP / COMPOSE / REPLAY under
  a fixed K = 10 budget. LoCoMo 79.6 and LongMemEval-S 83.4 (GPT-4.1-mini) at
  1.3K inference tokens per query — currently the strongest *efficient* system.
- *Zero-Mem* [F1]: **zero LLM tokens for all memory operations** — raw traces
  with provenance, a spaCy-NER entity co-occurrence graph + PPR, a
  turn/window/episode hierarchy, deterministic routing between views, evidence
  closure and calibration. Best LoCoMo F1 among compared systems, 0.22 s/query.
- *Jev-Mem* [F2]: memory control via a non-generative typed predictor ("System
  One") over a four-view graph (semantic/temporal/causal/entity) with explicit
  graph-expansion budgets and adaptive stopping; LoCoMo J 0.777, construction
  158 s.

**Takeaway.** The strongest recent systems (JustMem, Zero-Mem, Jev-Mem,
SimpleMem) already make memory access *adaptive*, but every adaptive decision is
a **hand-designed rule or threshold** (k-range, routing flags, expansion budget,
stopping thresholds). None of these rules is optimised against end-task reward,
and none is conditioned on an externally imposed budget.

---

## 5. Graph memory

- *HippoRAG* [D2] (NeurIPS'24): OpenIE knowledge graph + synonym edges + node
  specificity; query entities seed **Personalized PageRank**, giving single-step
  multi-hop retrieval (+20% R@5 on 2Wiki; 10–30× cheaper than iterative RAG).
- *MRAgent* [D1]: Cue–Tag–Content graph with episodic, semantic and topic layers
  and an **LLM-driven iterative traversal** (select action → expand → route/prune
  → stop). LoCoMo J 84.2 (Gemini-2.5-Flash) / 88.3 (Claude-Sonnet-4.5). Proves
  active retrieval is strictly more expressive than passive for budget T ≥ 2.
  Limitation (stated): the graph only grows — no consolidation or forgetting.
- *Selective Forgetting* [D3]: typed KG with hand-weighted importance
  (recency/frequency/degree/age) pruning. Key negative result: **graph-only memory
  underperformed flat vector RAG on LongMemEval** (J 0.454 vs 0.536), losing
  verbatim assistant content and knowledge updates; it helped only temporal
  questions. Forgetting removed ~10% of nodes without significant loss.
- *Harness the Memory* [E3]: a dual-level graph + vector substrate was the most
  accurate on conversational QA but the slowest.

**Takeaway.** Graphs help relational and temporal reasoning but (i) must keep
verbatim, provenance-linked source text [D3, F1, A1]; (ii) grow without bound and
become costly [C1, D1, E3]; (iii) are pruned, if at all, by hand-weighted
scores [D3]. A budgeted, learned policy over a hybrid graph + vector substrate is
unexplored.

---

## 6. Learned memory control

### 6.1 RL-fine-tuned LLM memory managers

| System | Learned ops | Algorithm | Reward | Budget term |
|---|---|---|---|---|
| Memory-R1 [B1] | ADD/UPDATE/DELETE/NOOP + answer-time memory distillation | PPO / GRPO (3–14B) | answer exact match | none |
| Mem-α [B3] | insert/update/delete into core/semantic/episodic | GRPO (4B) | QA + format + **compression 1 − l_mem/l_in** + LLM-judged content | soft |
| AgeMem [B2] | 3 LTM + 3 STM tools | step-wise GRPO (4–7B) | task + context efficiency + memory quality − overflow penalty | soft |
| MemAgent [B4] | overwrite a fixed 1,024-token memory | multi-conv DAPO (7–14B) | answer verifier | **hard size, query-visible** |
| Memory-R2 [B5] | extractor + manager (shared 7B) | LoGo-GRPO + curriculum | session QA F1 − **compression penalty** | soft |
| DeltaMem [B7] | add/update (ReAct) | GRPO (4–8B) | state-transition soft-F1 vs synthetic target states | none |
| VerMem [B8] | 7 LTM/STM tools | SFT + 3-phase GRPO | local verifier + global (task, evidence, **efficiency gated on success**) | soft |
| TrustMem [B9] | WRITE/REVISE/PRUNE | TR-GRPO (GRPO + DPO ranking) | task + efficiency + verifier (coverage/preservation/faithfulness) | soft |
| MemoryCPT [A3] | query-aware summariser (write distilled by SFT) | GRPO (7B LoRA) | α·F1 + (1−α)·(1 − normalised $cost) | soft |
| EMBER [A8] | pre-query evidence capsules (insert/merge/overwrite/skip) | GRPO (7–14B) | answer-gated evidence chain − overrun penalty; **budget sampled per rollout** | **hard at eval, soft in training** |

Observations. (a) RL reliably beats prompting and SFT for memory operations
[B1, B3, B5]; a 4B RL-tuned model beat GPT-4.1-mini on the same framework [B3].
(b) Sparse QA rewards cause credit-assignment problems; fixes include
anchor-state re-rollouts [B5], dense state rewards [B7], verifiers [B8, B9] and
curricula [B2, B5, B8]. (c) The budget is almost always a **soft penalty** on
memory length or cost, fixed at training time. (d) All require multi-GPU RL
fine-tuning of 3–14B models — hard to reproduce on commodity hardware.

### 6.2 Lightweight learned controllers over a frozen LLM

- *MemSkill* [B6]: a small controller (frozen embedder + MLPs, shared scorer over
  a variable skill set) selects Top-K memory "skills" per span for a frozen
  executor LLM; trained with **PPO** on downstream QA; an LLM designer evolves
  the skill bank. Best on LoCoMo/LongMemEval among compared systems.
- *MemCon* [A4]: memory ops as a contextual bandit — **tabular UCB** over a few
  hundred discretised states chooses RETRIEVE / PLANINJECT / RE-RETRIEVE /
  CONSOLIDATE / FORGET / NOOP and their parameters; 5–20% fewer tokens.
- *OSL-MR* [A5]: an MLP ranks memories for retention under a hard storage budget
  (greedy knapsack), supervised by gold-evidence membership; observability-safe
  features only.
- *OAS* [A2]: ridge regression over 11 pre-generation features picks retain vs.
  Merge/Abstract/Rewrite per budget.
- *BudgetMem* [A7]: a shared lightweight **PPO router** picks LOW/MID/HIGH compute
  tiers per module.
- *DeMem* [A9]: K-slot memory refined by statistically certified splits (bandit
  theory with regret bounds); LoCoMo J 0.911 (GPT-4o-mini).

Small controllers are cheap to train, add no LLM calls at inference, and transfer
across backbones [A4, B6] — but none of them jointly controls retention *and*
retrieval under an explicit budget with end-task reward.

---

## 7. Budget-aware memory

This cluster is the closest prior work; each paper covers one slice of the
problem.

| Work | What is budgeted | Enforced how | What is learned | Evaluated on end-task accuracy vs. full memory systems? |
|---|---|---|---|---|
| OAS [A2] | answer-time evidence tokens (16–256) | hard | retain-vs-consolidate operator (ridge) | controlled, oracle evidence only |
| OSL-MR [A5] | stored memory tokens | hard (knapsack) | per-memory retention score (MLP, supervised) | **no** (evidence F1 only) |
| EMBER [A8] | retained source-evidence tokens (512–8K) | hard | 7–14B writer (GRPO) | F1 on LongMemEval-RR; not vs Mem0/Zep |
| BudgetMem [A7] | extraction compute ($) | soft (λ) | tier router (PPO) | yes (λ-frontiers) |
| MemoryCPT [A3] | $ per query | soft (α) | summariser (GRPO) | yes, 314-question test split |
| JustMem [A1] | K = 10 cards | fixed | nothing (hand router) | yes |
| SimpleMem [C5] | k ∈ [3, 20] | heuristic | nothing (heuristic classifier) | yes |
| Jev-Mem [F2] | graph-expansion units | hand-set | typed predictor (not trained on task reward) | yes |
| DeMem [A9] | K memory slots | hard | certified partition (bandit) | yes |
| Selective Forgetting [D3] | graph size | periodic prune | nothing (hand-weighted score) | yes (LongMemEval) |

Findings consistent across this cluster:
1. **The best memory operation depends on relative budget pressure** — e.g.
   consolidation helps by up to 48 points at tight budgets and hurts by 8–11 at
   loose ones [A2]; learned eviction gains concentrate at tight budgets [A5, G2].
2. **General "importance" ≠ task utility** [A5, A9, H2]: GA-style importance and
   descriptive similarity poorly predict which memories answer future questions
   (Spearman 0.10 on LoCoMo [A9]).
3. **Myopic retention is sub-optimal** under shifting demand (31.5% gap to the DP
   optimum) [A5].
4. Retention is NP-hard even single-step [A5, A9] → learned approximations.

---

## 8. Learned eviction in adjacent systems domains

- *KVP* [G1] (Apple): KV-cache eviction as **ranking**. If optimal kept-sets are
  nested across budgets (true for additive rewards), one ranking is optimal for
  every budget. Per-head MLPs score (k, v, position); Plackett–Luce policy via
  Gumbel-Sort; reward = normalised **area under the cost-vs-budget curve**;
  REINFORCE with leave-one-out baseline; fully offline. Beats heuristics and
  matches attention-based methods; RL beats supervised learning-to-rank.
- *Cold-RL* [G2]: dueling DQN (~10K params) evicts among the K coldest NGINX
  cache objects using 6 cheap features, 500 µs timeout with LRU fallback; +146%
  hit ratio under high pressure, ≈ tie at low pressure; trained offline from
  logs.
- Earlier learned caching (LeCaR/Cacheus, RLR, LRB) — see v1 references [13, 14].

These show that **small, offline-trained, budget-agnostic learned rankers beat
hand-tuned eviction**, with most of the gain under tight budgets. This recipe has
not been applied to semantic agent memory with end-task reward.

---

## 9. Comparison

### 9.1 System comparison table

| System | Substrate | Write | Forget / evict | Read | Controller | Budget | Open source |
|---|---|---|---|---|---|---|---|
| Generative Agents [H2] | memory stream + reflections | log all | none | weighted recency+importance+relevance | heuristic | context fit only | yes |
| MemGPT/Letta [H1] | working ctx + FIFO + recall/archival | LLM paging | FIFO flush at 100% | LLM function calls | prompted LLM | pressure threshold (70/100%) | yes |
| Mem0 / Mem0ᵍ [C1] | facts (+ entity graph) | LLM extract | LLM DELETE / invalidate | top-k (+ subgraph) | prompted LLM | reported only | yes |
| Zep/Graphiti [C2] | bi-temporal KG, 3 tiers | LLM extract | edge invalidation | cosine+BM25+BFS+rerank | prompted LLM | reported only | yes |
| A-MEM [C3] | linked notes | LLM notes + links | none | top-k + links | prompted LLM | none | yes |
| LightMem [C4] | topic summaries + turns | compress + LLM summary | sleep-time consolidation | top-k | heuristic + LLM | reported only | yes |
| SimpleMem [C5] | atomic units + multi-index | LLM extract | consolidation (archive) | hybrid, adaptive k | heuristic | heuristic k | yes |
| JustMem [A1] | atomic cards + provenance | LLM extract | none | planner → 3 routes | prompted LLM + rule | fixed K | — |
| Zero-Mem [F1] | raw traces + NER graph + hierarchy | none (non-generative) | none | PPR + hierarchy, rule routing | heuristic | fixed top-K | — |
| Jev-Mem [F2] | 4-view graph + vector + BM25 | typed predictor | consolidation | budgeted graph expansion | small model (not RL) | hand-set expansion budget | yes |
| HippoRAG [D2] | OpenIE KG | LLM OpenIE | none | PPR | heuristic | none | yes |
| MRAgent [D1] | Cue–Tag–Content graph | LLM distill | none | iterative LLM traversal | prompted LLM | turn limit | — |
| Memory-R1 [B1] | fact bank | RL LLM | RL DELETE | top-60 + RL distill | RL LLM | none | yes |
| Memory-R2 [B5] | fact bank | RL LLM | RL DELETE | top-k | RL LLM | soft penalty | — |
| MemSkill [B6] | memory bank | skill-conditioned LLM | skill-driven | top-k | small RL controller | none | yes |
| MemCon [A4] | backend-agnostic | backend | FORGET action | RETRIEVE params | tabular bandit | none (speed bonus) | — |
| OSL-MR [A5] | notes | log all | **learned, hard budget** | — | MLP (supervised) | hard storage | — |
| EMBER [A8] | evidence capsules | RL LLM (7–14B) | budget update | top-10 | RL LLM | hard retained tokens | — |
| BudgetMem [A7] | chunks → modules | runtime extraction | — | top-5 | PPO router | soft λ (compute) | yes |
| MemoryCPT [A3] | episodic + semantic | distilled 7B | merge | RRF + RL summary | RL LLM | soft α ($) | — |
| DeMem [A9] | K slots | router | certified split | slot read | bandit (theory) | hard K slots | — |
| **This thesis (target)** | **hybrid graph + vector + BM25 with raw provenance** | **cheap / non-generative + optional LLM** | **learned, hard budget** | **learned, budget-conditioned** | **small RL policy (Stage 1); RL LLM (Stage 2)** | **hard budget as policy input** | **planned** |

### 9.2 Reported LoCoMo results (as reported; *not* comparable across rows)

| System | Backbone | Metric | Score | Source |
|---|---|---|---|---|
| Full context | GPT-4o-mini | J | 72.9 / 71.8 | [C1] / [C4] |
| Mem0 / Mem0ᵍ | GPT-4o-mini | J | 66.9 / 68.4 | [C1] |
| Mem0 (re-run) | GPT-4o-mini | ACC | 61.7 | [C4] |
| Zep | GPT-4o-mini | J | 66.0 | [C1] |
| LightMem | GPT-4o-mini | ACC | 73.0 | [C4] |
| JustMem | GPT-4.1-mini | J | 79.6 | [A1] |
| Jev-Mem | GPT-4o-mini | J (incl. adversarial) | 77.7 | [F2] |
| DeltaMem-8B-RL | Qwen3-8B | J | 75.1 | [B7] |
| Memory-R2 | Qwen2.5-7B | J / F1 | 81.0 / 50.6 | [B5] |
| MRAgent | Gemini-2.5-Flash / Claude-Sonnet-4.5 | J | 84.2 / 88.3 | [D1] |
| DeMem | GPT-4o-mini / GPT-4.1-mini | J | 91.1 / 92.0 | [A9] |

Implication: absolute LoCoMo accuracy is saturating (85–92 with strong readers).
The confirmed thesis target — **best accuracy at a matched memory/context
budget, plus an accuracy-vs-budget Pareto curve** — is both more defensible and
more novel than chasing the absolute leaderboard.

---

## 10. Gap analysis (revised)

1. **No single policy jointly controls retention (write/evict) and retrieval
   (what enters the reader's context) under an explicit hard budget, trained on
   end-task reward.** Budget-aware works each learn one slice — retention scores
   supervised by evidence labels [A5], a consolidation operator [A2], a writer
   LLM [A8], compute tiers [A7], a summariser [A3] — or use hand rules [A1, C5,
   F2]. OAS's authors name joint learning of retrieval, consolidation and packing
   as future work [A2].
2. **No budget-conditioned (budget-agnostic) policy for agent memory.** Most
   methods are trained for one budget or one λ. EMBER samples budgets during
   training but uses a 14B RL writer [A8]. The KVP result — one ranking optimal
   for all budgets, trained with an all-budgets AUC reward [G1] — has not been
   carried over from KV caches to semantic memory records.
3. **Hybrid graph + vector substrates have no learned, budgeted maintenance.**
   Graph memories grow monotonically [D1] or are pruned by hand-weighted scores
   [D3]; graph-only memory loses verbatim detail [D3]. Cheap non-generative hybrid
   substrates exist [F1, F2] but their routing, k, expansion and stopping are hand
   rules.
4. **Heavy RL is the norm.** RL memory managers need multi-GPU fine-tuning of
   3–14B models [B1–B9, A3, A8]. A small policy trainable on a single consumer GPU
   that is competitive at matched budgets would be both practically useful and
   scientifically informative (how much of the gain needs an RL-tuned LLM?).
5. **Evaluation gap.** Published numbers are not comparable [C1, C4, A1]; matched-
   budget comparisons against full systems (Mem0, Zep, LightMem, JustMem) are
   rare; retrieval regime is seldom reported [A6]. A reproducible, matched-budget
   harness with Pareto curves is itself a contribution.

---

## 11. Candidate thesis framing (for discussion — architecture not yet fixed)

*A budget-conditioned learned memory controller for LLM agents.* Over a cheap
hybrid substrate (raw turns with provenance + atomic facts + entity graph +
dense/BM25 indices), a small policy receives the query, per-item features
(similarity, BM25, graph proximity/PPR, recency, access statistics, item size,
type) **and the budget**. It (i) ranks items for **retention** under a storage
budget and (ii) ranks and selects evidence for the **reader** under a context-
token budget, choosing retrieval breadth/depth. Train offline with RL on end-task
reward (KVP-style all-budgets objective or PPO), with a frozen OpenAI reader.
Stage 2 (extension): replace or augment the policy with a QLoRA-GRPO-tuned
≤ 1.5B LLM manager. Evaluate on LoCoMo (then LongMemEval) against re-run
baselines at matched budgets, with accuracy-vs-budget curves and the
irreversible/recoverable error decomposition [A6].

---

## 12. References

Primary papers read for v2 (IDs are arXiv unless noted; letters refer to
[`papers/READING_NOTES.md`](papers/READING_NOTES.md)):

- [A1] JustMem: Just-Enough Memory Access for Long-Term Conversations. 2609.19877
- [A2] Kang et al. Retain or Consolidate? Budget-Dependent Operator Selection for Language Agent Memory. 2607.17545
- [A3] Lei et al. MemoryCPT: An End-to-End Agent Memory Framework for Cost-Performance Trade-off. 2608.04843
- [A4] Jiang et al. Memory as a Controlled Process: Learned Adaptive Memory Management for LLM Agents (MemCon). 2607.13591
- [A5] Kang et al. Learning What to Remember: Observability-Safe Memory Retention via Constrained Optimization (OSL-MR). 2606.10616
- [A6] Shen. What Eviction Destroys: A Restore-Counterfactual Audit of Forgetting in Agent Memory. 2609.08279
- [A7] Zhang et al. Learning Query-Aware Budget-Tier Routing for Runtime Agent Memory (BudgetMem). 2602.06025 (ICML 2026)
- [A8] Li, Banerjee, Che. EMBER: Efficient Memory via Budgeted Evidence Retention for Long-Horizon Agents. 2606.05894
- [A9] Zou et al. Remember the Decision, Not the Description: A Rate-Distortion Framework for Agent Memory (DeMem). 2605.10870
- [B1] Yan et al. Memory-R1. 2508.19828
- [B2] Yu et al. Agentic Memory (AgeMem). 2601.01885
- [B3] Wang et al. Mem-α: Learning Memory Construction via Reinforcement Learning. 2509.25911
- [B4] Yu et al. MemAgent: Reshaping Long-Context LLM with Multi-Conv RL-based Memory Agent. 2507.02259
- [B5] Yan et al. Memory-R2: Fair Credit Assignment for Long-Horizon Memory-Augmented LLM Agents. 2605.21768
- [B6] Zhang et al. MemSkill: Learning and Evolving Memory Skills for Self-Evolving Agents. 2602.02474
- [B7] Zhang et al. DeltaMem: Towards Agentic Memory Management via Reinforcement Learning. 2604.01560
- [B8] Sun et al. Verifiable Memory (VerMem). 2608.03137
- [B9] Yang et al. TrustMem: Learning Trustworthy Memory Consolidation. 2606.25161
- [C1] Chhikara et al. Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory. 2504.19413 (ECAI 2025)
- [C2] Rasmussen et al. Zep: A Temporal Knowledge Graph Architecture for Agent Memory. 2501.13956
- [C3] Xu et al. A-MEM: Agentic Memory for LLM Agents. 2502.12110 (NeurIPS 2025)
- [C4] Fang et al. LightMem: Lightweight and Efficient Memory-Augmented Generation. 2510.18866 (ICLR 2026)
- [C5] Liu et al. SimpleMem: Efficient Lifelong Memory for LLM Agents. 2601.02553
- [D1] Ji, Li, Hooi. Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents (MRAgent). 2606.06036
- [D2] Gutiérrez et al. HippoRAG. 2405.14831 (NeurIPS 2024)
- [D3] Rusu, Khanzadeh, Alalfi. Selective Forgetting: A Graph-Based Memory Framework for Long-Term LLM Agents. 2608.28978
- [E1] Maharana et al. Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo). 2402.17753 (ACL 2024)
- [E2] Wu et al. LongMemEval. 2410.10813 (ICLR 2025)
- [E3] Huang et al. Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents. 2608.15008
- [F1] Xiao et al. Zero-Mem: Zero-Token Memory Operations for LLM Agents. 2607.29377
- [F2] Jiang, Li, Li. Jev-Mem: System-One-Controlled Agentic Memory for Efficient AI Agents. 2609.23986
- [G1] Moschella, Manduchi, Sener. Learning to Evict from Key-Value Cache (KVP). 2602.10238
- [G2] Gupta, Bhayani. Cold-RL: Learning Cache Eviction with Offline RL for NGINX. 2508.12485
- [H1] Packer et al. MemGPT: Towards LLMs as Operating Systems. 2310.08560
- [H2] Park et al. Generative Agents: Interactive Simulacra of Human Behavior. 2304.03442 (UIST 2023)

Background references carried over from v1 (not re-read for v2): MemoryBank
(2305.10250), RecallM (2307.02738), GraphRAG (Edge et al. 2024), LangMem, Neo4j
agent memory, Cacheus (FAST'21), RLR (AAAI), G-KV (2512.00504), resource-rational
analysis (Lieder & Griffiths), CORAG, surveys 2603.07670 / 2504.15965 /
2605.06716, vector DB comparisons.
