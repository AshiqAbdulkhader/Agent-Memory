# Experiment Log

All experiments for the thesis are logged here in reverse-chronological order
(newest first). Use the template below for each new entry.

See [PLANS.md](PLANS.md) for phase status. Raw results: `results/*.json`; logs on legion
(`~/mtech-project/logs_*.txt`).

---

### EXP-009: RL-fine-tuned LLM selector (GRPO + LoRA, Qwen2.5-1.5B-Instruct) vs small policy

- **Date:** 2026-11-06. **Compute:** Colab A100-SXM4-40GB via google-colab-cli (76 min training); QA on legion.
- **Setup:** fold 0 (test convs 0-1, 231 questions x budgets 64/128/256; train convs 2-9, 1,304 questions, random budget).
  LLM sees top-30 hybrid-RRF candidates + token counts + budget, outputs ids; prefix-packed; reward = packed evidence
  recall (-0.2 if unparsable). TRL 1.17.1 GRPOTrainer, LoRA r=16 all proj, 400 steps, 8 gens x 4 prompts, lr 5e-5, beta 0.
- **Scripts:** `scripts/llm_selector_data.py`, `scripts/colab_grpo_selector.py`, `scripts/exp009_qa.py`.
- **Results:** `results/exp009_llm.json`, `exp009_llm_preds.jsonl`, `exp009_baselines.json`, `exp009_qa.json`, adapter in `results/exp009_adapter/`.

| Recall @64/128/256 | 64 | 128 | 256 |
|---|---|---|---|
| hybrid (candidate order) | .525 | .637 | .719 |
| LLM base | .258 | .388 | .467 |
| LLM GRPO | .538 | .671 | .738 |
| small policy, same candidates | .597 | .674 | .761 |
| small policy, whole memory | .604 | .679 | .770 |
| oracle over candidates | .825 | .867 | .867 |

Accuracy (gpt-4o-mini reader/judge, n=231): hybrid 70.6/77.9, LLM base 55.4/60.2, LLM GRPO 78.8/81.0,
policy 76.6/82.3 (@128/@256). McNemar GRPO vs hybrid p<.001 / .12; vs policy p=.53 / .71; vs base p<.001 both.

- **Observations:** the policy collapsed to near-deterministic outputs (frac_reward_zero_std -> ~1, completions hit the
  48-token cap); always lists candidate 1 first, 73% ascending order, i.e. close to hybrid order with skips.
- **Conclusion:** the RL-fine-tuned LLM ties the 24K-param policy on accuracy, below it on recall, at ~62,000x params and
  ~40x latency. Single fold/seed/size. Report Section 5.10.

---

### EXP-007 / 007b: LongMemEval-S — zero-shot transfer and in-domain training

- **Date**: 2026-11-06
- **Setup**: 500 questions, ~115K-token histories, messages chunked to ≤150 tokens (494,856 unique
  chunks), no LLM at write time; reader + judge gpt-4o-mini. 007: policies trained on all 10 LoCoMo
  conversations (raw turns), applied unchanged (`scripts/exp_lme.py`). 007b: budget-agnostic policy
  trained on LongMemEval with 5-fold CV over questions (`scripts/exp_lme_indomain.py`).
- **Results**:

  | method | recall AUC | R@256 | R@1024 | J@256 | J@1024 |
  |---|---|---|---|---|---|
  | dense | .531 | .484 | .779 | .492 | .678 |
  | bm25 | .510 | .520 | .725 | .490 | .626 |
  | hybrid RRF | .560 | .543 | .808 | .514 | .682 |
  | hybrid + PPR | .526 | .498 | .773 | .472 | .664 |
  | LoCoMo rl_agnostic (zero-shot) | .485 | .445 | .711 | .428 | .616 |
  | LoCoMo rl_cond (zero-shot) | .522 | .503 | .738 | .460 | .652 |
  | **LME rl_agnostic (5-fold CV)** | **.638** | **.661** | **.892** | **.564** | **.714** |

  McNemar in-domain vs hybrid RRF: @256 64 wins / 39 losses, p = .018; @1024 43/27, p = .072.
  vs dense: @256 p < .001; @1024 p = .057.
- **Conclusion**: LoCoMo weights do **not** transfer zero-shot (below every heuristic except BM25);
  the method does — trained in-domain it is the best retriever. Deployments should train on their own
  domain. Ops note: the first run stalled 10 h embedding with batch 256 on the 6 GB GPU (WSL shared
  memory spill); fp16 + batch 64 took ~1 h.

### EXP-008: Ablation of the retrieval policy + cost

- **Date**: 2026-11-05
- **Setup**: budget-agnostic RL retrieval policy, store with facts (gpt-4o-mini facts), 5-fold CV,
  one feature group removed at a time; single seed. `scripts/exp_ablation.py` →
  `results/exp008_ablation.json`.
- **Results** (evidence recall AUC): full .802; −set context .805; −graph .800; −BM25 .805;
  **−dense .725 (−.077)**; −question-type .804; linear scorer .806.
  Policy 24,193 params; ~283 s training per fold (RTX 3060); inference 7.5 ms mean / 13.7 ms p95 per query.
- **Conclusion**: only dense features are indispensable; other groups are mutually redundant
  (|Δ| < .005, within seed noise). Linear ≈ MLP → the gain comes from optimising the weighting for
  budgeted recall, not scorer capacity. Full-model AUC .802 here vs .820 in EXP-001b (different fact
  set: gpt-4o-mini 2,939 facts vs gpt-4.1 4,384).

### EXP-006: Full controller (learned retention + learned retrieval) end-to-end QA

- **Date**: 2026-11-05
- **Setup**: held-out conversations streamed with eviction at B_store ∈ {2K, 8K}, evidence packed at
  B_read ∈ {256, 1024}; reader + judge **gpt-4o-mini** (not comparable to gpt-4.1 tables);
  1,536 questions; `scripts/exp_joint_qa.py` → `results/exp006_joint_qa.json`.
- **Results** (judge accuracy):

  | B_store / B_read | FIFO + dense | redundancy + hybrid RRF | learned + learned |
  |---|---|---|---|
  | 2K / 256 | .143 | .303 | **.469** |
  | 2K / 1024 | .150 | .336 | **.469** |
  | 8K / 256 | .331 | .550 | **.774** |
  | 8K / 1024 | .355 | .611 | **.818** |

- **Conclusion**: +16.6 to +22.4 points over the best heuristic pair at every setting. At 2K store the
  read budget no longer matters for the learned controller — accuracy is bounded by what survived
  forgetting. ~21.5M prompt tokens.

### EXP-005: Mem0 baseline at matched read budgets

- **Date**: 2026-09-25
- **Setup**: official `mem0ai` 2.2.0 library, following Mem0's own LoCoMo harness (both speakers'
  perspectives, 2-message batches, session timestamp). Same Azure gpt-4.1 for Mem0's extraction, same
  local bge-base embedder, same reader/judge prompts as EXP-003. Mem0 OSS resolves relative dates
  against *today*; we inject the session date as its observation date (otherwise "yesterday" became
  2026). 1 batch (conv-44) skipped by Azure's content filter. Retrieval: top-50 per speaker, merged by
  score, packed to B_read; plus Mem0's native top-30/speaker. No training → all 1,540 questions (ours:
  1,535 with valid evidence under 5-fold CV).
- **Results** (J):

  | method | 64 | 128 | 256 | 1024 | native (~3.3K tok/q) |
  |---|---|---|---|---|---|
  | Mem0 | .403 | .606 | .718 | .863 | .907 |
  | ours: rl_cond on turns + facts | **.697** | **.793** | **.852** | **.904** | — |
  | full context (~24K tok) | | | | | .913 |

- **Conclusion**: at matched evidence budgets our controller beats Mem0 by +29.4 / +18.7 / +13.4 /
  +4.1 points. Mem0 only reaches our 1,024-token accuracy when given its default ~3.3K tokens (3.2×
  more). This is the first published system re-run in our harness; LightMem, Zero-Mem-style and
  JustMem-style are next. (Per-question McNemar not run yet: Mem0 script does not save per-question
  outputs; margins at ≤256 tokens are far outside noise.)

---

### EXP-003b: End-to-end QA on the hybrid substrate (turns + facts)

- **Date**: 2026-09-25 (rerun with 64/128 budgets and per-question outputs)
- **Setup**: as EXP-003, store = turns + 4,384 LLM facts (EXP-001b features); methods dense, hybrid
  RRF, rl_agnostic, rl_cond (both trained per fold); B_read ∈ {64, 128, 256, 1024}; gpt-4.1 reader +
  judge. 49,114 calls in total, 21.7M prompt tokens. 6 reader calls blocked by Azure's content filter
  (false positives; counted as wrong).
- **Results** (J):

  | method | J@64 | J@128 | J@256 | J@1024 |
  |---|---|---|---|---|
  | hybrid RRF | .636 | .750 | .816 | .893 |
  | dense | .680 | .778 | .838 | .892 |
  | rl_agnostic | .689 | .786 | .843 | .897 |
  | **rl_cond** | **.697** | **.793** | **.852** | **.904** |
  | full context (~24K tok) | .913 | | | |

- **Paired exact McNemar tests (rl_cond vs …, n = 1,524 paired questions)**:

  | budget | vs dense | vs hybrid RRF | vs rl_agnostic |
  |---|---|---|---|
  | 64 | +1.7, p = .048 | +6.1, p < .001 | +0.8, p = .31 |
  | 128 | +1.6, p = .050 | +4.2, p < .001 | +0.7, p = .43 |
  | 256 | +1.3, p = .064 | +3.4, p < .001 | +0.9, p = .22 |
  | 1024 | +1.1, p = .078 | +1.0, p = .15 | +0.6, p = .35 |

- **Conclusion**: the budget-conditioned learned ranker is best at every budget and reaches 99% of
  full-context accuracy with ~4% of its tokens at 1,024. On this substrate the gain over dense retrieval
  is small (1–2 points): significant at 64 and 128 tokens (p ≈ .05), borderline at 256/1024. The gain
  over hybrid RRF is large and significant at ≤ 256 tokens. **Budget conditioning vs budget-agnostic is
  not significant** — do not claim it. Current policies are trained on an evidence-recall proxy;
  training on answer-level reward (and joint retention) is the main lever for larger margins.

---

### EXP-001b: Retrieval ranking on the hybrid substrate (turns + LLM atomic facts)

- **Date**: 2026-09-25
- **Setup**: as EXP-001, but the store holds raw turns **plus 4,384 LLM-extracted atomic facts**
  (one gpt-4.1 call per session, 272 calls, 0.27M in / 0.17M out tokens ≈ $2; relative dates resolved to
  absolute; each fact keeps provenance = source dia_ids). A fact "covers" gold evidence iff it was
  extracted from that gold turn. 857–1,221 items per conversation.
- **Results** (evidence recall):

  | method | 64 | 128 | 256 | 512 | 1024 | 2048 | AUC |
  |---|---|---|---|---|---|---|---|
  | BM25 | .461 | .575 | .657 | .719 | .773 | .815 | .666 |
  | hybrid+PPR | .534 | .668 | .753 | .813 | .870 | .918 | .759 |
  | hybrid RRF | .572 | .681 | .763 | .820 | .884 | .919 | .773 |
  | sup_bce | .547 | .673 | .777 | .854 | .902 | .934 | .781 |
  | dense | .605 | .724 | .802 | .861 | .897 | .926 | .802 |
  | rl_agnostic | .630 | .747 | .823 | .873 | .910 | .939 | .820 |
  | **rl_cond** | **.640** | .746 | **.824** | **.880** | **.914** | .938 | **.824** |

- **Conclusion**: (1) Compact facts raise recall at every budget (dense AUC .544 → .802), especially at
  tight budgets (64 tokens: .209 → .605). (2) **RL now clearly beats supervised learning** (.820 vs
  .781): with overlapping granularities (a fact and its source turn cover the same evidence) the
  reward is no longer additive, and set-level RL learns to avoid spending budget on redundant items,
  which pointwise supervision cannot. (3) **Budget conditioning now helps slightly** (.824 vs .820,
  best at 64 and 512) — with mixed item granularities the best mix depends on the budget, as
  Retain-or-Consolidate [A2] predicts. Margins over dense are smaller than on turns (+2.2 AUC).
- **Caveat**: provenance-based coverage over-credits facts that lose detail; EXP-003b checks answers.

---

### EXP-003 (reference): Full-context reader

- **Date**: 2026-09-25 · gpt-4.1 reader + judge, entire conversation in context (~24K tokens/question,
  37.7M prompt tokens ≈ $76).
- **Result**: **J = 0.913** (multi-hop .894, temporal .872, open-domain .772, single-hop .951).
- **Note**: LoCoMo conversations (14–28K tokens) fit in gpt-4.1's context, so full context is a strong
  upper reference here (unlike LongMemEval-S ~115K or real multi-month histories). The learned ranker
  reaches 0.865 (95% of it) with 1,024 evidence tokens (~4% of the tokens).

---

### EXP-003: End-to-end QA accuracy at matched read budgets (LLM reader + judge)

- **Date**: 2026-09-25
- **Hypothesis**: the evidence-recall gains of the learned ranker (EXP-001) translate into higher
  answer accuracy at the same context-token budget.
- **Setup**: turn-level substrate, no storage limit; per question, rank with {dense, hybrid+PPR,
  learned rl_agnostic (trained per fold on training conversations)}, pack B_read ∈ {256, 1024} tokens,
  present snippets chronologically. Reader and judge: **Azure gpt-4.1** (only deployment available;
  temperature 0). Judge prompt = Mem0/LightMem CORRECT/WRONG protocol. LoCoMo cats 1–4 (1,535 Qs),
  5-fold CV. 18,420 calls, 10.56M prompt + 0.19M completion tokens (≈ $23).
- **Metric**: LLM-judge accuracy (J).
- **Results**:

  | retrieval | B_read | J | multi-hop | temporal | open-domain | single-hop |
  |---|---|---|---|---|---|---|
  | dense | 256 | .648 | .500 | .634 | .587 | .710 |
  | hybrid+PPR | 256 | .699 | .500 | .759 | .630 | .750 |
  | **learned** | **256** | **.756** | **.589** | **.766** | .620 | **.823** |
  | dense | 1024 | .801 | .734 | .791 | .663 | .843 |
  | hybrid+PPR | 1024 | .843 | .755 | .834 | .674 | .894 |
  | **learned** | **1024** | **.865** | **.766** | **.859** | **.696** | **.919** |

- **Conclusion**: at 256 tokens the learned ranker is +5.7 J over hybrid+PPR and +10.8 over dense; at
  1024 tokens +2.2 and +6.4. Gains are largest under tight budgets, as predicted. For context only (not
  comparable — different readers): JustMem reports 79.6 with GPT-4.1-mini at ~1.3K inference tokens/q;
  Mem0 66.9 with GPT-4o-mini. Our learned ranker reaches 75.6 with only 256 evidence tokens.
- **Caveats**: reader/judge are gpt-4.1, stronger than the gpt-4o-mini used by most published
  baselines → absolute numbers are not comparable to papers; only the within-table comparison is.
  Single run (temperature 0).
- **Next steps**: full-context reference; re-run Mem0 / LightMem / Zero-Mem-style / JustMem-style
  baselines under this harness; QA accuracy for the joint (B_store × B_read) controller; LLM facts.

---

### EXP-004: Joint retention × retrieval under (B_store, B_read)

- **Date**: 2026-09-25
- **Hypothesis**: combining the learned retention policy (EXP-002) and learned retrieval ranker
  (EXP-001) maximises evidence that is both kept in memory and packed into the reader's context, and
  the gains compose.
- **Setup**: per fold, train both policies on training conversations; on held-out conversations stream
  sessions with eviction at B_store ∈ {2K, 4K, 8K} tokens, then for each question recompute features on
  the surviving store, rank, and pack B_read ∈ {256, 1024} tokens. LoCoMo cats 1–4, 5-fold CV.
- **Metric**: joint evidence recall (gold evidence both retained and packed).
- **Results** (columns B_store/B_read):

  | retention + retrieval | 2K/256 | 2K/1024 | 4K/256 | 4K/1024 | 8K/256 | 8K/1024 | mean |
  |---|---|---|---|---|---|---|---|
  | FIFO + dense | .062 | .081 | .113 | .153 | .219 | .292 | .153 |
  | redundancy + hybrid-PPR (best heuristic pair) | .125 | .145 | .181 | .231 | .294 | .378 | .226 |
  | redundancy + learned | .133 | .148 | .210 | .241 | .339 | .400 | .245 |
  | learned + hybrid-PPR | .181 | .210 | .314 | .390 | .440 | .560 | .349 |
  | **learned + learned** | **.184** | **.213** | **.345** | **.400** | **.504** | **.598** | **.374** |

- **Conclusion**: the full learned controller is +65% relative (+14.8 points) over the best heuristic
  pair and 2.4× FIFO + dense. Gains compose: learned retention contributes most (+12.3 over redundancy
  with the same retriever), learned retrieval adds +2.5 on top of learned retention (+6.4 at 8K/256).
  The retrieval ranker was trained on full stores and still transfers to budget-pruned stores.
- **Next steps**: convert to answer accuracy (EXP-003-style reader + judge) at the same budget grid;
  train retrieval on pruned stores; consider a shared network for both heads.

---

### EXP-002: Learned retention (forgetting) under a storage budget vs heuristic eviction

- **Date**: 2026-09-24
- **Hypothesis**: a query-free learned retention ranking keeps more of the evidence that future
  questions will need than FIFO / random / redundancy-aware / hand-weighted importance eviction,
  under the same token storage budget.
- **Setup**:
  - Streaming: each conversation is ingested session by session; after each session, if memory exceeds
    B_store, items are ranked by a keep-score and the top-ranked prefix within B_store is kept.
  - Features (15, query-free): 9 item features + age, redundancy (max cosine to other items), key
    novelty, speaker share, (pressure, budget — zeroed: budget-agnostic ranking).
  - Training: episodes = snapshots after each session prefix of training conversations (~210–233 per
    fold); reward = mean over answerable questions of retained-evidence fraction, averaged over
    B_store ∈ {1024, 2048, 4096, 8192}; ranking RL as EXP-001, 15 epochs.
  - Baselines: FIFO (MemGPT-style sliding window), random, redundancy-aware (evict most similar first;
    Megagon audit), importance (Selective-Forgetting-style recency + key richness/idf + numbers).
  - LoCoMo cats 1–4, 5-fold CV over conversations; conversations are 14–28K tokens, so budgets keep
    ~4–50% of the history.
- **Metric**: Retain-Recall (EMBER) = fraction of each question's gold evidence still in memory at the end.
- **Results**:

  | method | 1024 | 2048 | 4096 | 8192 | AUC |
  |---|---|---|---|---|---|
  | FIFO | .037 | .085 | .169 | .341 | .158 |
  | random | .037 | .085 | .168 | .350 | .160 |
  | importance (heuristic) | .077 | .127 | .223 | .407 | .209 |
  | redundancy-aware | .081 | .150 | .252 | .441 | .231 |
  | **learned (ranking RL)** | **.121** | **.218** | **.424** | **.647** | **.352** |

- **Conclusion**: learned query-free retention is +52% relative (+12.1 AUC points) over the best
  heuristic and ~2.2× FIFO, consistently in all 5 folds, and trained on snapshots transfers to true
  streaming eviction. Hand-weighted "importance" is worse than simple redundancy removal, echoing
  OSL-MR's finding that generic importance ≠ task utility.
- **Next steps**: joint retention × retrieval (evidence both kept and packed under B_store × B_read);
  end-to-end QA accuracy; LLM facts as additional (cheap, compact) items the retention policy can prefer.

---

### EXP-001: Learned retrieval ranking vs heuristic rankers (evidence recall, no LLM)

- **Date**: 2026-09-24
- **Hypothesis**: a small ranking policy over observable (query, item) features, trained with
  KVP-style ranking RL, packs more gold evidence into a fixed read budget than dense / BM25 / hybrid /
  PPR / Generative-Agents-style heuristics. A budget-conditioned policy beats a budget-agnostic one.
- **Setup**:
  - Substrate: raw LoCoMo turns only (5,882 turns; 14–28K tokens per conversation), no LLM facts yet.
    Dense: BAAI/bge-base-en-v1.5 (local GPU). BM25. spaCy keyword graph + Personalized PageRank.
  - Features (29): 7 query-type, 9 item, 11 query–item (dense/BM25/PPR/key overlap/speaker/neighbour),
    2 budget. Scorer: 2-layer MLP (128) + mean-pooled set context.
  - RL: Plackett–Luce via Gumbel-sort, K=16 samples, REINFORCE-LOO, prefix log-prob top-64, Adam 3e-3,
    6 epochs. `rl_agnostic`: no budget input, reward = mean recall over budgets. `rl_cond`: budget
    input, reward = recall at each budget (all budgets per step). `sup_bce`: pointwise BCE on
    gold-evidence labels (pos_weight 50).
  - Read budgets B_read ∈ {64, 128, 256, 512, 1024, 2048} tokens (o200k), prefix packing.
  - Benchmark: LoCoMo cats 1–4 with valid evidence (1,535 Qs), **5-fold CV over conversations**.
- **Metric**: evidence recall of packed context (fraction of gold `dia_id`s included); AUC = mean over budgets.
- **Results**:

  | method | 64 | 128 | 256 | 512 | 1024 | 2048 | AUC |
  |---|---|---|---|---|---|---|---|
  | random | .000 | .006 | .008 | .022 | .039 | .090 | .027 |
  | recency | .004 | .014 | .018 | .024 | .064 | .106 | .038 |
  | GA-style (relevance+recency) | .079 | .147 | .207 | .278 | .339 | .415 | .244 |
  | BM25 | .200 | .368 | .480 | .556 | .629 | .700 | .489 |
  | dense | .209 | .379 | .517 | .624 | .722 | .812 | .544 |
  | hybrid RRF | .235 | .431 | .547 | .651 | .750 | .828 | .574 |
  | hybrid + PPR | .236 | .443 | .581 | .688 | .773 | .848 | .595 |
  | sup_bce | .270 | .497 | .650 | .757 | .832 | .898 | .651 |
  | **rl_agnostic** | **.277** | **.512** | **.652** | .757 | .824 | .890 | **.652** |
  | rl_cond | .236 | .458 | .597 | .711 | .799 | .866 | .611 |

  By category (AUC), rl_agnostic vs hybrid+PPR: multi-hop .423 vs .359, temporal .715 vs .673,
  open-domain .409 vs .360, single-hop .731 vs .670.
- **Conclusion**: learned ranking gives +5.7 AUC points over the best heuristic and +10.8 over dense,
  with the largest relative gains at tight budgets (+15.6% relative at 128 tokens). RL ≈ supervised
  here — expected, because evidence recall is additive per item (supervision is already aligned).
  **Budget conditioning hurt** (−4.1 AUC): a single budget-agnostic ranking is near-optimal for
  retrieval, consistent with the nested-optimal-set argument of KVP; the extra input mostly adds
  variance. Budget conditioning should be re-tested where the optimal action genuinely changes with
  budget (retention vs consolidation, Retain-or-Consolidate [A2]).
- **Next steps**: (1) end-to-end QA with GPT-4o-mini reader + LLM judge (needs OpenAI key); (2) RL
  with non-additive judge reward, where RL should beat supervision; (3) add LLM atomic facts to the
  substrate; (4) retention (EXP-002) and joint retention × retrieval.

---

## Template

### EXP-NNN: <short title>

- **Date**:
- **Hypothesis**: what we expect and why
- **Setup**:
  - Base LLM:
  - Memory backend(s) compared:
  - Resource budget (tokens / slots / latency):
  - Benchmark / dataset:
  - Baselines compared against:
- **Metrics**: (e.g., task success rate, recall@k, retrieval latency, tokens
  used, $ cost)
- **Results**: table or summary
- **Conclusion**: what we learned, did the hypothesis hold
- **Next steps**:

---
