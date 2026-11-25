// Mid-semester dissertation report (BITS ZG628T format) — generated with docx-js.
// Usage: node build_report.js  ->  ../MidSem_Report.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, ImageRun, TableOfContents, PageBreak, Footer, PageNumber,
  LevelFormat, TabStopType, TabStopPosition,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = path.join(ROOT, "report", "figures");
const FONT = "Times New Roman";
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1440;           // A4, 1-inch margins
const TEXT_W = PAGE_W - 2 * MARGIN;                              // 9026 DXA

const TITLE = "LEARNING TO REMEMBER: REINFORCEMENT-LEARNED MEMORY CONTROL FOR LLM AGENTS UNDER BOUNDED RESOURCES";

// ---------------------------------------------------------------- helpers
function runs(text, base = {}) {
  // **bold** and *italic* inline markup
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (text, opts = {}) => new Paragraph({
  children: runs(text, opts.run || {}), alignment: opts.align ?? AlignmentType.JUSTIFIED,
  spacing: { after: 120, line: opts.line ?? 360 }, ...opts.extra,
});
const PA = (text) => P(text, { line: 276, run: { size: 22 } });
const center = (text, size = 24, bold = false, after = 120) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after },
  children: [new TextRun({ text, size, bold })],
});
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun(text)] });
const H1c = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const bullet = (text, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level }, children: runs(text), alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 60, line: 320 },
});
const numbered = (text, ref = "numbers") => new Paragraph({
  numbering: { reference: ref, level: 0 }, children: runs(text), alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 60, line: 320 },
});
const blank = () => new Paragraph({ children: [] });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

let figN = 0, tabN = 0;
const figures = [], tables = [];
function figure(file, caption, widthIn = 6.2) {
  figN += 1;
  figures.push(`Figure ${figN}: ${caption}`);
  const buf = fs.readFileSync(path.join(FIG, file));
  // read PNG size to keep aspect ratio
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const wpx = widthIn * 96, hpx = wpx * h / w;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: hpx },
        altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: `Figure ${figN}: ${caption}`, italics: true, size: 20 })] }),
  ];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(caption, header, rows, widths, fontSize = 18) {
  tabN += 1;
  tables.push(`Table ${tabN}: ${caption}`);
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, isHead) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: isHead ? { fill: "D9E2F3", type: ShadingType.CLEAR } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: runs(String(t), { size: fontSize, bold: isHead || undefined }) })],
  });
  return [
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
      rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true)) }),
             ...rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, false)) }))] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 },
      children: [new TextRun({ text: `Table ${tabN}: ${caption}`, italics: true, size: 20 })] }),
  ];
}

// ---------------------------------------------------------------- title page (x2, as in the sample)
function titlePage() {
  return [
    new Paragraph({ spacing: { before: 200 }, children: [] }),
    center(TITLE, 30, true, 200),
    center("BITS SEZG628T: Dissertation", 26, true, 600),
    center("by", 24, false, 300),
    center("Muhammed Ashiq Abdul Khader", 26, true, 60),
    center("2024TM93594", 26, true, 600),
    center("Dissertation work carried out at", 24, false, 200),
    center("Daimler Truck Innovation Center India, Bangalore", 24, true, 600),
    center("Submitted in partial fulfilment of M.Tech Software Engineering", 24, false, 60),
    center("degree programme", 24, false, 600),
    center("Under the Supervision of", 24, false, 200),
    center("Phanikumar Pikkili", 24, true, 60),
    center("Senior Program Manager, Daimler Truck Innovation Center India, Bangalore", 24, false, 400),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [new ImageRun({
      type: "png", data: fs.readFileSync(path.join(ROOT, "report", "assets", "bits_logo.png")),
      transformation: { width: 105, height: 102 },
      altText: { title: "BITS Pilani logo", description: "BITS Pilani logo", name: "bits_logo" } })] }),
    center("BIRLA INSTITUTE OF TECHNOLOGY & SCIENCE", 28, true, 120),
    center("PILANI (RAJASTHAN)", 26, true, 300),
    center("September 2026", 24, false, 0),
  ];
}

// ---------------------------------------------------------------- abstract
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
function signatureBlock() {
  const col = (lines) => new TableCell({ borders: noBorders, width: { size: TEXT_W / 2, type: WidthType.DXA },
    children: lines.map((l) => new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: l, size: 22 })] })) });
  return new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [TEXT_W / 2, TEXT_W / 2],
    rows: [new TableRow({ children: [
      col(["Signature of the Student", "Name: Muhammed Ashiq Abdul Khader", "Date:", "Place: Bangalore"]),
      col(["Signature of the Supervisor", "Name: Phanikumar Pikkili", "Date:", "Place: Bangalore"]),
    ] })] });
}

const abstract = [
  H1("ABSTRACT"),
  PA("Large language model (LLM) agents need long-term memory to stay consistent across weeks of interaction, but every practical deployment is resource-bounded: the reader model has a limited effective context window, memory stores cost storage and search time, and every memory operation that calls an LLM costs tokens and latency. Existing memory systems (Mem0, Zep, A-MEM, LightMem, MemGPT and others) decide what to store, what to forget and what to retrieve with hand-designed heuristics or with prompted LLM calls, and none of them is trained to respect an explicit resource budget."),
  PA("This dissertation develops a **learned memory controller** that operates under two explicit, hard budgets: a storage budget **B_store** (tokens kept in memory) and a read budget **B_read** (evidence tokens given to the reader per question). Over a cheap hybrid memory substrate — raw conversation turns with provenance, compact LLM-extracted atomic facts, dense and BM25 indices and a keyword graph with Personalized PageRank — two small policies rank memory items: a query-free **retention policy** that decides what to forget when memory is full, and a **retrieval policy** that decides what evidence enters the reader's context. Both are trained with ranking reinforcement learning (Plackett–Luce sampling, REINFORCE with a leave-one-out baseline) on a reward averaged over all budgets, so a single policy serves every budget. The LLM itself stays frozen, and the policies train in minutes on a single consumer GPU."),
  PA("A literature survey of 35 primary papers shows that budget-aware memory became an active topic in 2026, but each existing method learns only one slice of the problem (retention, a consolidation operator, compute tiers or a summariser) or relies on hand-tuned routing rules. Results on the LoCoMo long-term conversational memory benchmark (1,535 questions, 5-fold cross-validation over conversations) are encouraging: learned retrieval packs 9.6% more gold evidence into the same read budget than the best heuristic; learned retention keeps 52% more future evidence than the best eviction heuristic under the same storage budget; the joint controller improves evidence that is both kept and retrieved by 65%; and in end-to-end question answering with a GPT-4.1 reader and judge, the budget-conditioned policy reaches 90.4% accuracy with only 1,024 evidence tokens — within one point of reading the entire conversation (91.3%, ~24K tokens). The remaining work re-runs published memory systems under the same budgets, extends evaluation to LongMemEval, and prepares an open-source release."),
  blank(),
  signatureBlock(),
];

// ---------------------------------------------------------------- contents + lists
function listPage() {
  return [
    new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun("CONTENTS")] }),
    new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
    blank(),
    new Paragraph({ spacing: { before: 240, after: 120 }, children: [new TextRun({ text: "LIST OF FIGURES", bold: true })] }),
    ...figures.map((f) => new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: f, size: 22 })] })),
    new Paragraph({ spacing: { before: 240, after: 120 }, children: [new TextRun({ text: "LIST OF TABLES", bold: true })] }),
    ...tables.map((t) => new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: t, size: 22 })] })),
  ];
}

// ---------------------------------------------------------------- body
function body() {
  const b = [];
  // 1
  b.push(H1("1. INTRODUCTION"));
  b.push(H2("1.1 Background and motivation"));
  b.push(P("An LLM on its own is stateless: once a conversation leaves its context window it is forgotten. Agent memory systems solve this by writing information from past interactions into an external store and retrieving the relevant parts when a new question arrives. Two observations motivate this work. First, simply putting the whole history into the prompt does not scale — histories grow without bound, cost grows with every token, and long-context models use distant or mid-context information unreliably. Second, the memory systems in use today make their decisions with fixed rules: similarity top-k retrieval, recency or importance scores, TTL expiry, or an LLM prompted to \"extract salient facts\" and \"decide whether to add, update or delete\". None of these rules is optimised for the end task, and none takes an explicit resource budget as input."));
  b.push(P("This project treats agent memory as a **control problem under bounded resources**: given a limit on how much can be stored and how much can be read per question, learn which memories to keep and which to show the reader so that answer quality is maximised."));
  b.push(H2("1.2 Objectives"));
  [
    "Survey vector, graph, hybrid and learned agent-memory systems, and budget-aware memory in particular, to locate a precise and defensible research gap.",
    "Formalise memory management with two hard budgets — storage (B_store) and read (B_read) — and design a hybrid memory substrate that is cheap to write.",
    "Design and train small learned policies for retention (forgetting) and retrieval (evidence selection) with reinforcement learning, keeping the LLM frozen so training fits a single consumer GPU.",
    "Evaluate against heuristic and published memory systems at **matched budgets** on LoCoMo (and later LongMemEval), reporting accuracy-versus-budget curves.",
    "Release the system as an open-source library that others can use.",
  ].forEach((t) => b.push(numbered(t)));
  b.push(H2("1.3 Scope of this mid-semester report"));
  b.push(P("This report covers the literature survey (Section 2), the problem formulation and architecture (Section 3), the implementation (Section 4), and the experiments completed so far (Section 5). Section 6 lists the remaining work with a timeline."));

  // 2
  b.push(H1("2. LITERATURE SURVEY"));
  b.push(P("Thirty-five primary papers were read in full for this survey (detailed notes are kept in the project repository). They fall into six groups."));
  b.push(H2("2.1 Memory systems with heuristic or prompted control"));
  b.push(P("*Generative Agents* (Park et al., 2023) introduced the memory stream with a retrieval score that adds recency, LLM-rated importance and embedding relevance with equal hand-set weights. *MemGPT* (Packer et al., 2023) treats the context window as a bounded resource managed like virtual memory, with a memory-pressure warning at 70% of the window. *Mem0* (Chhikara et al., 2025) extracts salient facts with an LLM and lets the LLM choose ADD/UPDATE/DELETE/NOOP per fact; its graph variant adds an entity graph. *Zep/Graphiti* (Rasmussen et al., 2025) maintains a bi-temporal knowledge graph. *A-MEM* (Xu et al., 2025) links Zettelkasten-style notes. Efficiency-oriented systems followed: *LightMem* (ICLR 2026) compresses and consolidates offline, *SimpleMem* adapts retrieval depth with a query-complexity classifier, *JustMem* routes queries with a hand rule over LLM-predicted flags under a fixed ten-card budget, *Zero-Mem* performs all memory operations without any LLM call, and *Jev-Mem* uses a small typed predictor with hand-set graph-expansion budgets. The common thread is that every adaptive decision is a hand-designed rule, not optimised against task reward and not conditioned on an external budget."));
  b.push(H2("2.2 Graph memory"));
  b.push(P("*HippoRAG* (NeurIPS 2024) runs Personalized PageRank over an OpenIE knowledge graph for single-step multi-hop retrieval. *MRAgent* (2026) lets an LLM traverse a cue–tag–content graph iteratively and reaches very high LoCoMo accuracy, but its graph only grows. A 2026 study of graph memory with *selective forgetting* found that graph-only memory was significantly worse than flat vector retrieval on LongMemEval because extraction loses verbatim detail, and pruned the graph with a hand-weighted importance score. Graphs therefore need provenance back to raw text, and they have no learned, budgeted maintenance."));
  b.push(H2("2.3 Reinforcement-learned memory managers"));
  b.push(P("*Memory-R1*, *Mem-α*, *AgeMem*, *MemAgent*, *Memory-R2*, *DeltaMem*, *VerMem* and *TrustMem* (2025–2026) fine-tune 3–14B-parameter LLMs with PPO/GRPO to issue memory operations. They consistently beat prompting and supervised fine-tuning, but treat the budget, if at all, as a soft length penalty fixed at training time, and all require multi-GPU fine-tuning. *MemSkill* and *MemCon* instead train small controllers (PPO over skill selection; a tabular bandit over memory operations) on top of a frozen LLM — the design pattern adopted in this work."));
  b.push(H2("2.4 Budget-aware memory (closest prior work)"));
  b.push(P("Table 1 summarises the ten closest papers. Each learns or fixes one slice of the problem. *OAS* shows that whether to retain or consolidate evidence reverses with budget pressure; *OSL-MR* learns retention under a hard storage budget but evaluates only evidence F1; *EMBER* trains a 7–14B writer with GRPO under a retained-token budget; *BudgetMem* (ICML 2026) routes compute tiers with PPO; *MemoryCPT* trains a summariser with a cost-aware GRPO reward."));
  b.push(...table("Budget-aware memory methods and what they learn", ["Work", "Budgeted resource", "Enforced", "What is learned"], [
    ["OAS (2607.17545)", "answer-time evidence tokens", "hard", "retain vs. consolidate (ridge)"],
    ["OSL-MR (2606.10616)", "stored tokens", "hard", "retention score (supervised MLP)"],
    ["EMBER (2606.05894)", "retained evidence tokens", "hard", "7–14B writer (GRPO)"],
    ["BudgetMem (2602.06025)", "extraction compute ($)", "soft λ", "tier router (PPO)"],
    ["MemoryCPT (2608.04843)", "$ per query", "soft α", "summariser (GRPO)"],
    ["JustMem (2609.19877)", "10 memory cards", "fixed", "nothing (hand router)"],
    ["SimpleMem (2601.02553)", "k ∈ [3, 20]", "heuristic", "nothing (heuristic classifier)"],
    ["Jev-Mem (2609.23986)", "graph expansion units", "hand-set", "typed predictor (no task reward)"],
    ["DeMem (2605.10870)", "K memory slots", "hard", "certified partition (bandit)"],
    ["**This work**", "**B_store + B_read**", "**hard, policy input**", "**joint retention + retrieval (ranking RL)**"],
  ], [2300, 2300, 1300, 3126]));
  b.push(H2("2.5 Learned eviction in adjacent systems"));
  b.push(P("Outside agent memory, learned eviction is well established. *KVP* (Apple, 2026) casts KV-cache eviction as ranking: if the optimal kept set at each budget is nested inside the next, one ranking is optimal for every budget, so a small policy can be trained once with an all-budgets reward. *Cold-RL* (2025) replaces NGINX's LRU with a 10K-parameter dueling DQN and gains 146% hit ratio under high cache pressure. Both show that small, offline-trained learned rankers beat hand-tuned eviction, mostly under tight budgets — a recipe not yet applied to semantic agent memory with end-task reward."));
  b.push(H2("2.6 Benchmarks and evaluation"));
  b.push(P("*LoCoMo* (ACL 2024) contains ten long multi-session conversations with 1,986 questions; standard practice evaluates the 1,540 non-adversarial questions with an LLM judge. *LongMemEval* (ICLR 2025) has 500 questions over ~115K-token histories. Published numbers are not comparable across papers — Mem0 on LoCoMo is reported at 66.9 by its authors and 61.7 in a later re-run — so all baselines must be re-run under one protocol. Budget–accuracy results should also state the retrieval regime (What Eviction Destroys, 2026)."));
  b.push(H2("2.7 Research gap"));
  [
    "No single policy jointly controls retention and retrieval under explicit hard budgets while being trained on end-task reward; existing budget-aware methods each learn one slice.",
    "No budget-conditioned policy for agent memory: most methods are trained for a single budget or cost weight.",
    "Hybrid graph + vector substrates have no learned, budgeted maintenance.",
    "Learned memory control normally requires RL fine-tuning of multi-billion-parameter LLMs; a small policy trainable on one consumer GPU is missing.",
    "Matched-budget comparisons against full memory systems are rare, and published numbers are inconsistent.",
  ].forEach((t) => b.push(bullet(t)));

  // 3
  b.push(H1("3. PROBLEM FORMULATION AND PROPOSED ARCHITECTURE"));
  b.push(H2("3.1 Problem formulation"));
  b.push(P("A conversation arrives as a stream of sessions. After each session the memory M holds items m (raw turns or extracted facts), each with a token cost c(m). The **storage constraint** is Σ c(m) ≤ B_store: when it is violated, a retention policy π_keep ranks items without seeing any future question and keeps the top-ranked prefix that fits. When a question q arrives, a retrieval policy π_read ranks the surviving items and the top-ranked prefix within the **read constraint** B_read is given, in chronological order, to a frozen reader LLM. The objective is the expected answer quality over questions and budgets. Retention is NP-hard even for one step (OSL-MR, DeMem), which motivates learned ranking policies."));
  b.push(P("Following KVP, if the optimal kept set at each budget is nested in the next, a single ranking is optimal for every budget. The policies are therefore trained to maximise the **area under the utility-versus-budget curve**, i.e. the mean reward over a grid of budgets. A budget-conditioned variant additionally receives the budget as an input feature, allowing the ranking to change with budget pressure."));
  b.push(H2("3.2 Architecture"));
  b.push(...figure("fig1_architecture.png", "Architecture of the budget-constrained learned memory controller"));
  b.push(P("**Write path (cheap).** Every turn is stored verbatim with its date, speaker and identifier (provenance). One LLM call per session extracts atomic facts with explicit subjects and absolute dates, each linked to its source turns. A local embedding model (BAAI/bge-base-en-v1.5), a BM25 index and a keyword graph (spaCy named entities and nouns, Personalized PageRank seeded by the question's keywords) are built without any LLM."));
  b.push(P("**Retrieval policy π_read.** For each (question, item) pair it sees 29 observable features: question type, item metadata, dense similarity and its within-memory z-score and percentile, BM25, PPR, keyword overlap weighted by inverse frequency, speaker match, neighbour and session context, and (for the conditioned variant) the budget. A two-layer MLP with a mean-pooled set context outputs a score."));
  b.push(P("**Retention policy π_keep.** It sees 15 query-free features: item metadata plus age, redundancy (maximum cosine similarity to other items), keyword novelty and speaker share. No gold evidence or answers are used at decision time (the observability rule of OSL-MR)."));
  b.push(P("**Training.** Scores define a Plackett–Luce distribution over rankings; K = 16 rankings per example are sampled in parallel with Gumbel-sort, packed at each budget, and rewarded; gradients use REINFORCE with a leave-one-out baseline. Retention is trained on memory snapshots after each session prefix and evaluated with true session-by-session streaming. Rewards used so far are evidence-based (fraction of gold evidence retained or packed), which needs no LLM calls; end-task answer accuracy is used for evaluation."));

  // 4
  b.push(H1("4. IMPLEMENTATION"));
  b.push(P("The system is implemented as a Python package, *memctl*, with unit tests for packing, reward computation and the Plackett–Luce estimator."));
  b.push(...table("Implementation components", ["Module", "Responsibility"], [
    ["data/locomo.py", "LoCoMo loader: sessions, dated turns, image captions, questions with gold evidence ids"],
    ["store.py", "hybrid substrate: items with provenance, dense and BM25 indices, keyword graph, Personalized PageRank"],
    ["features.py", "observable query, item, query–item and budget features"],
    ["policy.py", "MLP scorer, Gumbel-sort sampling, Plackett–Luce log-probability, REINFORCE-LOO"],
    ["retention.py", "query-free retention features, heuristic eviction baselines, streaming eviction"],
    ["baselines.py", "random, recency, dense, BM25, hybrid RRF, hybrid + PPR, Generative-Agents-style rankers"],
    ["llm.py", "reader, LLM judge (Mem0/LightMem protocol) and fact extraction with a deterministic on-disk cache"],
    ["scripts/", "feature precomputation, experiments EXP-001 to EXP-004, Mem0 baseline, paired significance tests"],
  ], [2400, 6626]));
  b.push(...table("Experimental environment", ["Item", "Setting"], [
    ["Compute", "WSL2 Ubuntu 22.04, NVIDIA RTX 3060 Laptop GPU (6 GB), 16 CPU threads"],
    ["Libraries", "PyTorch 2.6 (CUDA 12.4), sentence-transformers, rank-bm25, spaCy, NetworkX, tiktoken"],
    ["Embeddings", "BAAI/bge-base-en-v1.5 (local)"],
    ["LLM (reader, judge, fact extraction)", "GPT-4.1 via Azure OpenAI, temperature 0"],
    ["Benchmark", "LoCoMo, categories 1–4 (1,535 questions with valid evidence), 5-fold cross-validation over conversations"],
    ["Budgets", "B_read ∈ {64, …, 2048} tokens; B_store ∈ {1K, 2K, 4K, 8K} tokens (o200k tokenizer)"],
  ], [2800, 6226]));

  // 5
  b.push(H1("5. EXPERIMENTS AND RESULTS SO FAR"));
  b.push(P("All experiments use 5-fold cross-validation over the ten LoCoMo conversations: policies are trained on eight conversations and tested on the two held out, so every conversation is tested exactly once."));
  b.push(H2("5.1 Learned retrieval under a read budget (EXP-001, EXP-001b)"));
  b.push(P("Evidence recall is the fraction of a question's gold evidence turns included in the packed context. On a store of raw turns, the learned budget-agnostic ranker improves the area under the recall curve from 0.595 (best heuristic, hybrid + PPR) to 0.652; at 128 tokens recall rises from 0.443 to 0.512. On the hybrid store with LLM facts, compact facts raise recall at every budget, and reinforcement learning clearly beats pointwise supervised learning (0.820 vs 0.781) because overlapping facts and turns make the reward non-additive. With mixed item granularities, budget conditioning gives the best result (0.824)."));
  b.push(...figure("fig2_retrieval_recall.png", "Evidence recall versus read budget (5-fold cross-validation)"));
  b.push(...table("Evidence recall (area under the recall–budget curve)", ["Method", "Turns only", "Turns + facts"], [
    ["random", "0.027", "0.051"], ["BM25", "0.489", "0.666"], ["dense", "0.544", "0.802"],
    ["hybrid RRF", "0.574", "0.773"], ["hybrid + PPR", "0.595", "0.759"], ["supervised (BCE)", "0.651", "0.781"],
    ["RL, budget-agnostic", "**0.652**", "0.820"], ["RL, budget-conditioned", "0.611", "**0.824**"],
  ], [3400, 2800, 2826]));
  b.push(H2("5.2 Learned retention under a storage budget (EXP-002)"));
  b.push(P("Conversations are streamed session by session and evicted to B_store after each session. Retain-recall is the fraction of each question's gold evidence still in memory at the end. The learned retention policy keeps 52% more future evidence than the best heuristic (area 0.352 vs 0.231) and about 2.2 times as much as FIFO, consistently in all five folds. A hand-weighted importance score was worse than simple redundancy removal, echoing prior findings that generic importance is not the same as task utility."));
  b.push(...figure("fig3_retention.png", "Retain-recall versus storage budget under streaming eviction", 4.6));
  b.push(H2("5.3 Joint retention and retrieval (EXP-004)"));
  b.push(P("Combining both policies, evidence that is both kept under B_store and packed under B_read improves from 0.226 (best heuristic pair) to 0.374, a 65% relative gain. Most of the gain comes from learned retention; learned retrieval adds a further 2.5 points on top of it."));
  b.push(...figure("fig4_joint.png", "Joint evidence recall for combinations of retention and retrieval policies", 5.0));
  b.push(H2("5.4 End-to-end question answering (EXP-003, EXP-003b)"));
  b.push(P("The packed evidence is given to a GPT-4.1 reader, and a GPT-4.1 judge grades each answer with the Mem0/LightMem protocol. With only 256 evidence tokens on the raw-turn store (Table 5), the learned ranker answers 75.6% of questions correctly against 69.9% for hybrid + PPR and 64.8% for dense retrieval. On the hybrid store with facts, the budget-conditioned policy reaches 85.1% at 256 tokens and 90.4% at 1,024 tokens — within one point of the full-context reference (91.3%, ~24K tokens per question)."));
  b.push(...figure("fig5_qa.png", "LLM-judge accuracy at matched read budgets (GPT-4.1 reader and judge)"));
  b.push(...table("End-to-end LLM-judge accuracy on LoCoMo (GPT-4.1 reader and judge)", ["Store", "Method", "64", "128", "256", "1,024"], [
    ["turns", "dense", "–", "–", "0.648", "0.801"], ["turns", "hybrid + PPR", "–", "–", "0.699", "0.843"],
    ["turns", "learned (RL)", "–", "–", "**0.756**", "**0.865**"],
    ["turns + facts", "hybrid RRF", "0.636", "0.750", "0.816", "0.893"], ["turns + facts", "dense", "0.680", "0.778", "0.838", "0.892"],
    ["turns + facts", "learned, budget-agnostic", "0.689", "0.786", "0.843", "0.897"],
    ["turns + facts", "learned, budget-conditioned", "**0.697**", "**0.793**", "**0.852**", "**0.904**"],
    ["full conversation", "reference (~24K tokens)", "0.913", "0.913", "0.913", "0.913"],
  ], [1700, 2926, 1100, 1100, 1100, 1100]));
  b.push(P("Exact McNemar tests on the 1,524 paired questions show that, on the facts store, the budget-conditioned policy's gain over dense retrieval is significant at 64 and 128 tokens (+1.7 and +1.6 points, p ≈ 0.05) and borderline at 256 and 1,024 tokens (p = 0.06–0.08); its gain over hybrid RRF is significant at every budget up to 256 tokens (p < 0.001). The difference between the budget-conditioned and budget-agnostic variants is not significant at any budget."));
  b.push(H2("5.5 Discussion and limitations"));
  [
    "Gains from learning are largest under tight budgets, as predicted by prior work on budget pressure.",
    "Budget conditioning did not help on the raw-turn store but helped on the mixed turns + facts store, where the best mix of item granularities depends on the budget.",
    "On the facts store the end-to-end margin over dense retrieval is small (1–2 points) and only significant at the tightest budgets; the policies are still trained on an evidence-recall proxy, and training on answer-level reward is the main planned lever.",
    "Budget conditioning helps recall on mixed-granularity stores, but its end-to-end advantage over the budget-agnostic policy is not yet statistically significant.",
    "The reader and judge are GPT-4.1, stronger than the GPT-4o-mini used in most published papers, so absolute numbers are not comparable to papers; only within-table comparisons are.",
    "LoCoMo conversations fit inside GPT-4.1's context window, which makes full context a strong upper reference; longer histories (LongMemEval) are needed to show the practical value of budgets.",
    "Azure's content filter blocked a handful of calls (false positives on LoCoMo topics); they are counted as wrong answers and reported.",
  ].forEach((t) => b.push(bullet(t)));

  // 6
  b.push(H1("6. FUTURE PLAN"));
  b.push(...table("Work plan and status", ["Sl No", "Phase", "Start date – End date", "Work to be done", "Status"], [
    ["1", "Literature survey", "07 Jul 2026 – 24 Sep 2026", "Survey of 35 primary papers, gap analysis", "COMPLETED"],
    ["2", "Problem formulation and architecture", "01 Aug 2026 – 24 Sep 2026", "Budgets, substrate, policy and training design", "COMPLETED"],
    ["3", "Implementation (core)", "24 Sep 2026 – 26 Sep 2026", "memctl package, retrieval and retention policies, LLM layer", "COMPLETED"],
    ["4", "Initial experiments", "24 Sep 2026 – 27 Sep 2026", "EXP-001 to EXP-004 on LoCoMo", "COMPLETED"],
    ["5", "Baseline re-runs", "26 Sep 2026 – 06 Oct 2026", "Mem0, LightMem, Zero-Mem-style and JustMem-style systems at matched budgets; significance tests", "IN PROGRESS"],
    ["6", "Answer-level RL and joint QA", "07 Oct 2026 – 14 Oct 2026", "Train with LLM-judge reward; end-to-end QA for joint B_store × B_read control", "PENDING"],
    ["7", "Generalisation", "15 Oct 2026 – 21 Oct 2026", "LongMemEval-S evaluation; optional small-LLM (≤1.5B) manager extension", "PENDING"],
    ["8", "Open-source release", "20 Oct 2026 – 25 Oct 2026", "Library API, documentation, reproducible scripts", "PENDING"],
    ["9", "Dissertation review and submission", "26 Oct 2026 – 31 Oct 2026", "Final report, supervisor and examiner review", "PENDING"],
  ], [700, 1900, 2000, 3026, 1400], 17));

  // 7
  b.push(H1("7. ABBREVIATIONS"));
  b.push(...table("Abbreviations", ["Abbreviation", "Expansion"], [
    ["AUC", "Area Under the Curve"], ["BM25", "Best Matching 25 (lexical ranking function)"], ["B_read", "Read budget: evidence tokens given to the reader per question"],
    ["B_store", "Storage budget: tokens kept in memory"], ["FIFO", "First In, First Out"], ["GRPO", "Group Relative Policy Optimization"],
    ["KV", "Key–Value (attention cache)"], ["LLM", "Large Language Model"], ["LOO", "Leave-One-Out (baseline)"],
    ["MLP", "Multi-Layer Perceptron"], ["PPO", "Proximal Policy Optimization"], ["PPR", "Personalized PageRank"],
    ["QA", "Question Answering"], ["RAG", "Retrieval-Augmented Generation"], ["RL", "Reinforcement Learning"],
    ["RRF", "Reciprocal Rank Fusion"], ["TTL", "Time To Live"],
  ], [2400, 6626]));

  // 8
  b.push(H1("8. REFERENCES"));
  [
    "Park, J. S., et al. Generative Agents: Interactive Simulacra of Human Behavior. UIST 2023. arXiv:2304.03442.",
    "Packer, C., et al. MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560, 2023.",
    "Maharana, A., et al. Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo). ACL 2024. arXiv:2402.17753.",
    "Gutiérrez, B. J., et al. HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models. NeurIPS 2024. arXiv:2405.14831.",
    "Wu, D., et al. LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. ICLR 2025. arXiv:2410.10813.",
    "Rasmussen, P., et al. Zep: A Temporal Knowledge Graph Architecture for Agent Memory. arXiv:2501.13956, 2025.",
    "Xu, W., et al. A-MEM: Agentic Memory for LLM Agents. NeurIPS 2025. arXiv:2502.12110.",
    "Chhikara, P., et al. Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory. ECAI 2025. arXiv:2504.19413.",
    "Yu, H., et al. MemAgent: Reshaping Long-Context LLM with Multi-Conv RL-based Memory Agent. arXiv:2507.02259, 2025.",
    "Gupta, A., Bhayani, A. Cold-RL: Learning Cache Eviction with Offline Reinforcement Learning for NGINX. arXiv:2508.12485, 2025.",
    "Yan, S., et al. Memory-R1: Enhancing LLM Agents to Manage and Utilize Memories via Reinforcement Learning. arXiv:2508.19828, 2025.",
    "Wang, Y., et al. Mem-α: Learning Memory Construction via Reinforcement Learning. arXiv:2509.25911, 2025.",
    "Fang, J., et al. LightMem: Lightweight and Efficient Memory-Augmented Generation. ICLR 2026. arXiv:2510.18866.",
    "Yu, Y., et al. Agentic Memory: Unified Long-Term and Short-Term Memory Management for LLM Agents. arXiv:2601.01885, 2026.",
    "Liu, J., et al. SimpleMem: Efficient Lifelong Memory for LLM Agents. arXiv:2601.02553, 2026.",
    "Zhang, H., et al. MemSkill: Learning and Evolving Memory Skills for Self-Evolving Agents. arXiv:2602.02474, 2026.",
    "Zhang, H., et al. Learning Query-Aware Budget-Tier Routing for Runtime Agent Memory (BudgetMem). ICML 2026. arXiv:2602.06025.",
    "Moschella, L., Manduchi, L., Sener, O. Learning to Evict from Key-Value Cache. arXiv:2602.10238, 2026.",
    "Zhang, Q., et al. DeltaMem: Towards Agentic Memory Management via Reinforcement Learning. arXiv:2604.01560, 2026.",
    "Zou, M., et al. Remember the Decision, Not the Description: A Rate-Distortion Framework for Agent Memory. arXiv:2605.10870, 2026.",
    "Yan, S., et al. Memory-R2: Fair Credit Assignment for Long-Horizon Memory-Augmented LLM Agents. arXiv:2605.21768, 2026.",
    "Li, Y., Banerjee, S., Che, T. EMBER: Efficient Memory via Budgeted Evidence Retention for Long-Horizon Agents. arXiv:2606.05894, 2026.",
    "Ji, S., Li, Y., Hooi, B. Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents. arXiv:2606.06036, 2026.",
    "Kang, Q., et al. Learning What to Remember: Observability-Safe Memory Retention via Constrained Optimization. arXiv:2606.10616, 2026.",
    "Yang, T., et al. TrustMem: Learning Trustworthy Memory Consolidation for LLM Agents. arXiv:2606.25161, 2026.",
    "Jiang, E. H., et al. Memory as a Controlled Process: Learned Adaptive Memory Management for LLM Agents. arXiv:2607.13591, 2026.",
    "Kang, Q., et al. Retain or Consolidate? Budget-Dependent Operator Selection for Language Agent Memory. arXiv:2607.17545, 2026.",
    "Xiao, Y., et al. Zero-Mem: Zero-Token Memory Operations for LLM Agents. arXiv:2607.29377, 2026.",
    "Sun, X., et al. Verifiable Memory: Unified Memory Management with Local and Global Verifiers. arXiv:2608.03137, 2026.",
    "Lei, S., et al. MemoryCPT: An End-to-End Agent Memory Framework for Cost-Performance Trade-off. arXiv:2608.04843, 2026.",
    "Huang, W.-C., et al. Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents. arXiv:2608.15008, 2026.",
    "Rusu, T., Khanzadeh, S., Alalfi, M. Selective Forgetting: A Graph-Based Memory Framework for Long-Term LLM Agents. arXiv:2608.28978, 2026.",
    "Shen, C. What Eviction Destroys: A Restore-Counterfactual Audit of Forgetting in Agent Memory. arXiv:2609.08279, 2026.",
    "Chen, G., et al. JustMem: Just-Enough Memory Access for Long-Term Conversations. arXiv:2609.19877, 2026.",
    "Jiang, D., Li, Y., Li, B. Jev-Mem: System-One-Controlled Agentic Memory for Efficient AI Agents. arXiv:2609.23986, 2026.",
  ].forEach((t) => b.push(numbered(t, "refs")));
  return b;
}

// ---------------------------------------------------------------- assemble (body first so figure/table lists are known)
const bodyContent = body();
const doc = new Document({
  creator: "memctl",
  title: "Mid-semester dissertation report",
  styles: {
    default: { document: { run: { font: FONT, size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: FONT }, paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "refs", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "[%1]", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 540 } } } }] },
  ] },
  features: { updateFields: true },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }) },
    children: [...titlePage(), pageBreak(), ...titlePage(), ...abstract, ...listPage(), ...bodyContent],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "report", "MidSem_Report.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, `(${figN} figures, ${tabN} tables)`);
});
