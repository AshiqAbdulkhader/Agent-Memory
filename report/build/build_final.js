// Final dissertation report (BITS WILP SEZG628T) — two-pass build:
//   node build_final.js            -> ../Final_Report.docx (contents page numbers from toc_pages.json if present)
//   python3 finalize_toc.py        -> renders PDF, finds page numbers, writes toc_pages.json, rebuilds
const fs = require("fs");
const path = require("path");
const L = require("./final_lib.js");
const { D, P, center, blank, pageBreak, H1, H1front, H2, H3, bullet, numberedList, figure, table, code, tocLine,
  result, f3, pct, runs, setChapter } = L;
const { Paragraph, TextRun, AlignmentType, Table, TableRow, TableCell, WidthType, BorderStyle, ImageRun, Footer,
  PageNumber, NumberFormat, HeadingLevel } = D;

const TITLE = "LEARNING TO REMEMBER: REINFORCEMENT-LEARNED MEMORY CONTROL FOR LLM AGENTS UNDER BOUNDED RESOURCES";
const TITLE_CASE = "Learning to Remember: Reinforcement-Learned Memory Control for LLM Agents Under Bounded Resources";
const STUDENT = "Muhammed Ashiq Abdul Khader", ID = "2024TM93594", DISC = "M.Tech Software Engineering";
const ORG = "Daimler Truck Innovation Center India", LOC = "Bangalore";
const SUP = "Phanikumar Pikkili", SUP_DES = "Senior Program Manager";
const EXAM = "Sanoj Thampi", EXAM_DES = "Senior Solution Architect";
const MENTOR = process.env.MENTOR || "Naveen Kumar Laskari";
const MONTH = "November 2026";
const TOC = fs.existsSync(path.join(__dirname, "toc_pages.json")) ? JSON.parse(fs.readFileSync(path.join(__dirname, "toc_pages.json"))) : {};
const pg = (key) => TOC[key] ?? "";

// ------------------------------------------------------------------ results
const R = {
  e1: result("exp001_retrieval.json"), e1b: result("exp001b_retrieval_facts.json"), e2: result("exp002_retention.json"),
  e3: result("exp003_qa.json"), e3full: result("exp003_fullctx.json"), e3b: result("exp003b_qa_facts.json"),
  e4: result("exp004_joint.json"), mem0: result("baseline_mem0.json"), e6: result("exp006_joint_qa.json"),
  e7: result("exp007_lme.json"), e7b: result("exp007b_lme_indomain.json"), e8: result("exp008_ablation.json"), e9: result("exp009_llm.json"), e9b: result("exp009_baselines.json"), e9q: result("exp009_qa.json"),
};
const acc = (obj, k) => (obj && obj[k] ? obj[k].acc : undefined);

// ------------------------------------------------------------------ logo
const LOGO = fs.readFileSync(path.join(L.ROOT, "report", "assets", "bits_logo.png"));
const logo = (w = 100) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
  children: [new ImageRun({ type: "png", data: LOGO, transformation: { width: w, height: w * 146 / 150 },
    altText: { title: "BITS Pilani logo", description: "BITS Pilani logo", name: "bits_logo" } })] });

// ================================================================== FRONT MATTER
function cover() {  // Appendix A of the guidelines
  return [
    blank(600), center("A REPORT", 28, true, 120), center("ON", 26, true, 360), center(TITLE, 30, true, 600),
    center("BY", 26, true, 360),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [
      new TextRun({ text: STUDENT, bold: true, size: 26 }), new TextRun({ text: `          ID No.: ${ID}`, size: 26 })] }),
    blank(480), center("AT", 26, true, 360), center(`${ORG}, ${LOC}`, 26, true, 600), logo(110),
    center("BIRLA INSTITUTE OF TECHNOLOGY & SCIENCE, PILANI", 28, true, 240), center(MONTH, 26, false, 0),
  ];
}
function titlePage() {  // Appendix B
  return [
    pageBreak(), blank(400), center("A REPORT", 28, true, 120), center("ON", 26, true, 360), center(TITLE, 30, true, 600),
    center("BY", 26, true, 360),
    new Table({ width: { size: L.TEXT_W, type: WidthType.DXA }, columnWidths: [3360, 3360, 3360],
      rows: [new TableRow({ children: [STUDENT, `ID No.: ${ID}`, DISC].map((t) => new TableCell({
        borders: noBorders, width: { size: 3360, type: WidthType.DXA },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: t, bold: true, size: 24 })] })] })) })] }),
    blank(480), center("Prepared in partial fulfilment of the", 24, false, 60),
    center("WILP Dissertation Course (SEZG628T: Dissertation)", 24, true, 480),
    center("AT", 26, true, 360), center(`${ORG}, ${LOC}`, 26, true, 600), logo(100),
    center("BIRLA INSTITUTE OF TECHNOLOGY & SCIENCE, PILANI", 28, true, 240), center(MONTH, 26, false, 0),
  ];
}
const nb = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: nb, bottom: nb, left: nb, right: nb };
function twoCol(left, right) {
  const col = (lines) => new TableCell({ borders: noBorders, width: { size: L.TEXT_W / 2, type: WidthType.DXA },
    children: lines.map((l) => new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: l, size: 23 })] })) });
  return new Table({ width: { size: L.TEXT_W, type: WidthType.DXA }, columnWidths: [L.TEXT_W / 2, L.TEXT_W / 2],
    rows: [new TableRow({ children: [col(left), col(right)] })] });
}
function certificate() {
  return [
    H1front("CERTIFICATE"),
    P(`This is to certify that the Dissertation entitled **${TITLE_CASE}** and submitted by **${STUDENT}**, ID No. **${ID}**, in partial fulfilment of the requirements of **SEZG628T Dissertation**, embodies the work done under my supervision.`),
    blank(1200),
    twoCol([" "], ["Signature of the Supervisor", `Name: ${SUP}`, `Designation: ${SUP_DES}`, `Organization: ${ORG}, ${LOC}`, "Place: Bangalore", "Date:"]),
  ];
}
function acknowledgements() {
  return [
    H1front("ACKNOWLEDGEMENTS"),
    P(`I thank the leadership of ${ORG}, ${LOC}, for supporting this dissertation alongside my work and for providing an environment in which research on applied artificial intelligence is encouraged.`),
    P(`I am grateful to my supervisor, **${SUP}** (${SUP_DES}), for guidance throughout the project, for helping me frame the problem around real deployment constraints, and for careful reviews of the outline, the mid-semester report and this report. I also thank my additional examiner, **${EXAM}** (${EXAM_DES}), for reviewing the work and for helpful comments.`),
    P(`I thank my faculty mentor, **${MENTOR}**, and the WILP Division of BITS Pilani for the structure and support of the dissertation course.`),
    P("Finally, I thank the authors of the LoCoMo and LongMemEval benchmarks and of the open-source tools used in this work (PyTorch, sentence-transformers, spaCy, rank-bm25, NetworkX and Mem0), and my family for their patience during the long evenings this project required."),
    blank(600),
    new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: STUDENT, bold: true })] }),
    new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun(`ID No. ${ID}`)] }),
  ];
}
const ABSTRACT = "Long-term memory lets large language model (LLM) agents stay consistent across weeks of interaction, but every deployment is bounded: memory has a storage limit and the model can read only a limited amount of text per question. Existing systems decide what to keep and retrieve with hand-tuned rules or prompted LLM calls. This dissertation builds a memory controller that works under two explicit token budgets, one for storage and one for reading. Over a hybrid store of raw turns and LLM-extracted facts with dense, keyword and graph indices, two small policies rank memory items: one decides what to forget, the other what the reader sees. Both are trained with ranking reinforcement learning, train in minutes on a consumer GPU and call no LLM. On LoCoMo the controller answers 69.7% of questions with 64 evidence tokens, against 40.3% for Mem0, and 90.4% with 1,024 tokens, close to full context (91.3%). With both budgets enforced it is 17–22 points ahead of the best heuristics. The policies do not transfer zero-shot to LongMemEval, but retrained there they beat hybrid retrieval. An RL-fine-tuned 1.5B-parameter LLM matched but did not beat the controller. The system is released as an open-source library.";
function abstractSheet() {  // Appendix C
  const row = (k, v) => new Paragraph({ spacing: { after: 100, line: 300 }, children: [
    new TextRun({ text: `${k} `, bold: true, size: 22 }), new TextRun({ text: v, size: 22 })] });
  return [
    H1front("ABSTRACT"),
    center("BIRLA INSTITUTE OF TECHNOLOGY AND SCIENCE, PILANI (RAJASTHAN)", 22, true, 40), center("WILP Division", 22, true, 200),
    row("Organization:", `${ORG}`), row("Location:", LOC),
    row("Duration:", "07 July 2026 – November 2026 (approximately four months)"), row("Date of Start:", "07 July 2026"),
    row("Date of Submission:", MONTH),
    row("Title of the Project:", TITLE_CASE), row("ID No./Name of the student:", `${ID} / ${STUDENT}`),
    row("Name(s) and Designation(s) of Supervisor and Additional Examiner:", `${SUP}, ${SUP_DES}; ${EXAM}, ${EXAM_DES} (${ORG}, ${LOC})`),
    row("Name of the Faculty Mentor:", MENTOR),
    row("Key Words:", "LLM agents; long-term memory; reinforcement learning; learning to rank; retrieval-augmented generation; memory eviction; token budget; LoCoMo"),
    row("Project Areas:", "Artificial Intelligence; Machine Learning (Reinforcement Learning); Natural Language Processing; Information Retrieval"),
    new Paragraph({ spacing: { before: 120, after: 80 }, children: [new TextRun({ text: "Abstract:", bold: true, size: 22 })] }),
    P(ABSTRACT, { line: 276, run: { size: 22 } }),
    blank(360),
    twoCol(["Signature of Student", `Name: ${STUDENT}`, "Date:"], ["Signature of Supervisor", `Name: ${SUP}`, "Date:"]),
  ];
}

// ================================================================== CHAPTERS
function ch1() {
  setChapter(1);
  return [
    H1("CHAPTER 1: INTRODUCTION"),
    H2("1.1 Background"),
    P("Large language models (LLMs) answer questions and carry out tasks from the text in their context window, but they keep nothing between calls. An assistant that has talked with a user for weeks can only remember what is written back into its prompt. Agent memory systems close this gap: they write information from past interactions into an external store and, when a new question arrives, retrieve the relevant parts and give them to the model [@genagents, memgpt, memorysurvey]."),
    P("Putting the entire history into the prompt does not scale. Histories grow without bound, cost grows with every token, latency grows with context length, and long-context models use information in the middle of long inputs unreliably [@lostmiddle]. Practical systems therefore keep a separate memory store and select what to show the model. Today these selections are made by fixed rules — similarity top-k retrieval, recency or importance scores, time-to-live expiry — or by prompting an LLM to extract salient facts and decide whether to add, update or delete them [@mem0, zep, amem]. None of these rules is optimised for the downstream task, and none of them takes an explicit resource budget as an input."),
    H2("1.2 Problem Statement"),
    P("This dissertation treats agent memory as a **control problem under bounded resources**. Two budgets are made explicit: a **storage budget** *B_store*, the number of tokens the memory may hold, and a **read budget** *B_read*, the number of evidence tokens given to the model for each question. The research question is:"),
    P("*Given fixed storage and read budgets, can a small learned policy decide what to keep and what to read better than hand-tuned rules and existing memory systems?*", { align: AlignmentType.CENTER }),
    H2("1.3 Objectives"),
    ...numberedList([
      "Survey vector, graph, hybrid and learned agent-memory systems, with emphasis on budget-aware memory, and identify a precise research gap.",
      "Formulate memory management with two hard token budgets and design a hybrid memory store that is cheap to write.",
      "Design and train small learned policies for retention (forgetting) and retrieval (evidence selection) with reinforcement learning, keeping the LLM frozen so that training fits on one consumer GPU.",
      "Evaluate the policies against heuristic rules and a published memory system (Mem0) at **matched budgets**, on LoCoMo and LongMemEval, with paired significance tests.",
      "Release the system as an open-source library.",
    ]),
    H2("1.4 Scope and Limitations"),
    P("The work concerns conversational long-term memory for question answering. The reader LLM is used as a fixed component; the learned policies control which memories exist and which are shown to it. For comparison, a small LLM was also fine-tuned with RL to make the same read-time selection (Section 5.10); fine-tuning an LLM as a full memory manager that writes and edits memories was out of scope. Evaluation uses two public benchmarks and an LLM judge; human evaluation was out of scope. LLM access was limited to a cloud API with a small budget, which shaped the choice of models (Section 5.1)."),
    H2("1.5 Methodology"),
    P("The work followed five phases: (1) a literature survey of 35 primary papers; (2) problem formulation and architecture design; (3) implementation of the memory store, features, policies and evaluation harness as a Python package; (4) experiments under five-fold cross-validation with matched budgets, re-running baselines in one harness and testing significance with paired exact McNemar tests [@mcnemar]; and (5) packaging and documentation. Architecture decisions were taken with the supervisor at each phase and recorded in the project plan."),
    H2("1.6 Contributions"),
    ...numberedList([
      "A **joint, budget-aware memory controller**: one family of small ranking policies that decides both what to keep (under *B_store*) and what to read (under *B_read*).",
      "A **lightweight training recipe** adapted from learned KV-cache eviction [@kvp]: Plackett–Luce ranking policies trained with REINFORCE and a leave-one-out baseline on a reward averaged over all budgets, so one policy serves every budget. No LLM is called inside the policy, and training runs in minutes on a 6 GB GPU.",
      "A **matched-budget evaluation**: baselines (including Mem0) re-run in one harness with the same reader, judge and budgets, with paired significance tests and accuracy-versus-budget curves.",
      "An **open-source library** (memctl) with a two-line API for budgeted agent memory.",
    ]),
    H2("1.7 Organization of the Report"),
    P("Chapter 2 surveys related work. Chapter 3 formulates the problem and describes the system design. Chapter 4 describes the implementation. Chapter 5 reports the experiments and results. Chapter 6 discusses the findings and their limitations, and Chapter 7 concludes with recommendations and future work. Appendices list features, prompts, hyperparameters and reproduction steps."),
  ];
}

function ch2() {
  setChapter(2);
  return [
    H1("CHAPTER 2: LITERATURE SURVEY"),
    P("Thirty-five primary papers were read in full for this survey. This chapter summarises them by approach and closes with the gaps that motivate the work."),
    H2("2.1 A Taxonomy of Agent Memory"),
    P("Every memory system makes four decisions: what to **write** (raw text, extracted facts, summaries or graph triples), how to **maintain** the store (update, consolidate or forget), what to **read** for a question, and **who controls** these decisions (fixed rules, a prompted LLM, an RL-fine-tuned LLM or a small learned policy). A fifth axis, central to this work, is how the system treats **resource budgets**: ignored, reported after the fact, penalised softly in a reward, or enforced as hard constraints."),
    H2("2.2 Memory Systems with Heuristic or Prompted Control"),
    P("*Generative Agents* [@genagents] introduced the memory stream with a retrieval score that adds recency, LLM-rated importance and embedding relevance with equal hand-set weights, and periodic reflection. *MemGPT* [@memgpt] treats the context window like virtual memory: a warning is raised when the prompt reaches 70% of the window, and the LLM itself decides what to page out. *Mem0* [@mem0] extracts salient facts with an LLM and lets the LLM choose ADD, UPDATE, DELETE or NOOP for each fact; its graph variant adds an entity graph. *Zep* [@zep] maintains a bi-temporal knowledge graph with episode, entity and community layers, and *A-MEM* [@amem] links Zettelkasten-style notes."),
    P("A second generation targets efficiency. *LightMem* [@lightmem] compresses input with a small model and consolidates memory offline. *SimpleMem* [@simplemem] chooses between 3 and 20 retrieved items with a query-complexity classifier. *JustMem* [@justmem] routes each question to one of three access modes with a hand rule over LLM-predicted flags, under a fixed budget of ten memory cards. *Zero-Mem* [@zeromem] performs every memory operation without an LLM call, using a named-entity graph with Personalized PageRank. *Jev-Mem* [@jevmem] uses a small typed predictor with hand-set graph-expansion budgets. In all of these, every adaptive decision is a hand-designed rule: it is not optimised against task reward and it does not take a budget as input."),
    H2("2.3 Graph Memory"),
    P("*HippoRAG* [@hipporag] builds an OpenIE knowledge graph and runs Personalized PageRank [@ppr] from the question's entities, achieving multi-hop retrieval in a single step. *MRAgent* [@mragent] lets an LLM traverse a cue–tag–content graph iteratively and reaches high LoCoMo accuracy, but its graph only grows. A study of graph memory with selective forgetting [@selforget] found that graph-only memory was significantly worse than flat vector retrieval on LongMemEval, because extraction loses verbatim detail; it pruned the graph with a hand-weighted importance score. Graphs therefore need provenance back to the raw text, and they lack learned, budgeted maintenance. A controlled comparison of memory substrates [@harness] found that no single substrate dominates and that the best retrieval breadth differs between question answering and agentic tasks."),
    H2("2.4 Reinforcement-Learned Memory Managers"),
    P("A large recent body of work fine-tunes LLMs with reinforcement learning to issue memory operations: *Memory-R1* [@memoryr1], *Mem-α* [@memalpha], *AgeMem* [@agemem], *MemAgent* [@memagent], *Memory-R2* [@memoryr2], *DeltaMem* [@deltamem], *VerMem* [@vermem] and *TrustMem* [@trustmem]. They use PPO [@ppo] or GRPO [@grpo] on models with 3 to 14 billion parameters and consistently beat prompting and supervised fine-tuning. When they consider resources at all, they add a soft penalty on memory length or cost, fixed at training time, and all require multi-GPU fine-tuning."),
    H2("2.5 Lightweight Learned Controllers"),
    P("A smaller line trains compact controllers on top of a frozen LLM. *MemSkill* [@memskill] trains a small PPO controller that selects memory-extraction skills for a frozen executor. *MemCon* [@memcon] chooses among memory operations with a tabular bandit. *DeMem* [@demem] organises memory into a fixed number of slots refined by statistically certified splits. These controllers add no LLM calls at inference and transfer across backbones; this dissertation adopts the same pattern."),
    H2("2.6 Budget-Aware Memory"),
    P("Table 2.1 summarises the closest prior work. Each method learns or fixes one part of the problem. *OAS* [@oas] shows that whether to keep raw evidence or replace it by a summary reverses with budget pressure. *OSL-MR* [@oslmr] learns retention under a hard storage budget but evaluates only evidence overlap, not answers. *EMBER* [@ember] trains a 7–14B writer with GRPO under a retained-token budget. *BudgetMem* [@budgetmem] routes compute tiers with PPO, and *MemoryCPT* [@memorycpt] trains a summariser with a cost-aware reward."),
    ...table("Budget-aware memory methods and what they learn", ["Work", "Budgeted resource", "How enforced", "What is learned"], [
      ["OAS [@oas]", "evidence tokens at answer time", "hard", "keep vs. consolidate (ridge regression)"],
      ["OSL-MR [@oslmr]", "stored tokens", "hard", "retention score (supervised MLP)"],
      ["EMBER [@ember]", "retained evidence tokens", "hard", "7–14B writer (GRPO)"],
      ["BudgetMem [@budgetmem]", "extraction compute (cost)", "soft weight", "tier router (PPO)"],
      ["MemoryCPT [@memorycpt]", "cost per query", "soft weight", "summariser (GRPO)"],
      ["JustMem [@justmem]", "10 memory cards", "fixed", "nothing (hand router)"],
      ["SimpleMem [@simplemem]", "3 to 20 items", "heuristic", "nothing (classifier)"],
      ["DeMem [@demem]", "K memory slots", "hard", "certified partition (bandit)"],
      ["**This work**", "**storage and read tokens**", "**hard**", "**joint retention + retrieval (ranking RL)**"],
    ], [2200, 2400, 1500, 3980]),
    H2("2.7 Learned Eviction in Adjacent Systems"),
    P("Outside agent memory, learned eviction is well established. *KVP* [@kvp] casts KV-cache eviction as ranking: when the best kept set at each budget is contained in the best kept set at the next, one ranking is optimal for every budget, so a small policy can be trained once with a reward averaged over budgets. *Cold-RL* [@coldrl] replaces the LRU policy of the NGINX web cache with a 10,000-parameter Q-network and more than doubles the hit ratio under high cache pressure. Both show that small, offline-trained rankers beat hand-tuned eviction, with most of the gain under tight budgets."),
    H2("2.8 Benchmarks and Evaluation Practice"),
    P("*LoCoMo* [@locomo] contains ten long conversations between two people (up to 35 sessions, about 26,000 tokens) with 1,986 questions; standard practice evaluates the 1,540 non-adversarial questions with an LLM judge. *LongMemEval* [@longmemeval] has 500 questions over user–assistant histories of about 115,000 tokens and tests extraction, multi-session reasoning, knowledge updates, temporal reasoning and abstention. Two cautions shape the evaluation in this report: published numbers are not comparable across papers (Mem0 on LoCoMo is reported at 66.9 by its authors and 61.7 in a later re-run [@mem0, lightmem]), and budget–accuracy results should state the retrieval regime [@evict]."),
    H2("2.9 Research Gaps"),
    ...numberedList([
      "No single policy jointly controls retention and retrieval under explicit hard budgets while being trained on task reward; existing budget-aware methods each learn one part.",
      "No budget-agnostic or budget-conditioned policy exists for agent memory; most methods are trained for a single budget or cost weight.",
      "Hybrid graph and vector stores have no learned, budgeted maintenance.",
      "Learned memory control usually requires reinforcement learning on multi-billion-parameter LLMs; a small policy trainable on one consumer GPU is missing.",
      "Matched-budget comparisons against complete memory systems are rare, and published numbers are inconsistent.",
    ]),
  ];
}

function ch3() {
  setChapter(3);
  return [
    H1("CHAPTER 3: PROBLEM FORMULATION AND SYSTEM DESIGN"),
    H2("3.1 Setting and Notation"),
    P("A conversation arrives as a sequence of sessions. After each session the memory *M* holds items *m* — raw conversation turns or extracted facts — each with a token cost *c(m)* and a provenance set *src(m)* of the original turns it came from. Questions arrive later; each question *q* has an answer and, for evaluation, a set of gold evidence turns *E(q)*."),
    H2("3.2 Budgets and Objective"),
    P("**Storage constraint.** After each session, if Σ *c(m)* > *B_store*, a retention policy π_keep ranks the items using only information available at that time (it never sees future questions) and the highest-ranked prefix that fits is kept. **Read constraint.** For a question *q*, a retrieval policy π_read ranks the surviving items and the highest-ranked prefix within *B_read* tokens is given, in chronological order, to a frozen reader LLM. The objective is the expected answer accuracy over questions and over a range of budgets. Evidence recall — the fraction of *E(q)* covered by the selected items — is used as a cheap training reward."),
    H2("3.3 Why Ranking"),
    P("Choosing the best subset of items under a token budget is a knapsack-type problem and is NP-hard even for one step [@oslmr, demem]. Following KVP [@kvp], the problem is cast as ranking: a policy assigns each item a score, and the budget simply decides how far down the ranking to read. If the best kept set at each budget is contained in the best kept set at every larger budget, a single ranking is optimal for all budgets. The policy can therefore be trained once on the **area under the reward-versus-budget curve** — the mean reward over a grid of budgets — rather than once per budget. A **budget-conditioned** variant also receives the budget as an input feature, so the ranking can change when budgets are tight."),
    H2("3.4 Architecture"),
    ...figure("fig1_architecture.png", "Architecture of the budget-constrained learned memory controller"),
    P("Figure 3.1 shows the system. The **write path** stores every turn verbatim with its date, speaker and identifier, and optionally makes one LLM call per session to extract atomic facts, each linked to its source turns. Indices are built without any LLM. The **retention policy** removes items when memory exceeds *B_store*. The **retrieval policy** fills *B_read* for each question. Both policies are small neural networks trained offline."),
    H2("3.5 Memory Store"),
    P("The store keeps three complementary views of every item: a dense embedding from a local model (BAAI/bge-base-en-v1.5 [@bge]), a BM25 keyword index [@bm25], and a keyword graph linking items to the named entities and nouns they mention (extracted with spaCy [@spacy]). For a question, Personalized PageRank [@ppr] is run on this graph from the question's keywords, giving a graph-proximity score for every item. Keeping raw turns with provenance avoids the loss of verbatim detail observed for graph-only memory [@selforget]."),
    H2("3.6 Retrieval Policy"),
    P("For each question–item pair the retrieval policy sees 29 observable features (Appendix A): seven question-type indicators, nine item features (length, type, position, presence of numbers and dates), eleven question–item features (dense similarity and its z-score and percentile within memory, BM25 score and percentile, PageRank score, keyword overlap weighted by rarity, speaker match, and the best similarity among neighbouring turns and within the same session) and two budget features. A two-layer perceptron with 128 hidden units scores each item; it also receives the mean feature vector of all candidates, a cheap summary of what else is in memory."),
    H2("3.7 Retention Policy"),
    P("The retention policy sees 15 query-free features: the item features plus age, redundancy (the highest cosine similarity to any other item), keyword novelty and speaker share. Following the observability rule of OSL-MR [@oslmr], no gold evidence or answer is used at decision time; gold evidence is used only to compute the training reward."),
    H2("3.8 Training Algorithm"),
    P("The scores define a Plackett–Luce distribution over rankings [@plackett]. For each training example *K* = 16 rankings are sampled in parallel by adding Gumbel noise to the scores and sorting [@gumbel]. Each sampled ranking is packed at every budget in the grid and rewarded; the reward of a ranking is its mean over budgets. Gradients use REINFORCE [@williams] with a leave-one-out baseline [@rloo]: the advantage of each sample is its reward minus the mean reward of the other samples. The log-probability of a ranking is computed over its first 64 positions. Retention is trained on memory snapshots taken after each session of the training conversations and evaluated with true session-by-session streaming. The pseudo-code is:"),
    ...code([
      "for each epoch:",
      "  for each training question (or memory snapshot):",
      "    s      = MLP(features)                      # one score per item",
      "    perms  = argsort(s + Gumbel noise) x K      # K sampled rankings",
      "    r_k    = mean over budgets b of reward(pack(perm_k, b))",
      "    adv_k  = r_k - mean(r_j for j != k)         # leave-one-out baseline",
      "    loss   = - mean_k adv_k * log P_PL(top-64 of perm_k | s)",
      "    Adam step on loss",
    ]),
    H2("3.9 Key Design Decisions"),
    ...table("Design decisions and rationale", ["Decision", "Choice", "Rationale"], [
      ["Policy size", "2-layer MLP (~11K parameters)", "trains on a 6 GB GPU in minutes; no LLM call at inference"],
      ["Training signal", "ranking RL, reward averaged over budgets", "one policy for all budgets; handles redundant items (non-additive reward)"],
      ["Budgets", "hard storage and read token limits", "matches deployment constraints; enables matched-budget comparison"],
      ["Store", "raw turns + facts + dense/BM25/graph indices", "keeps verbatim detail while enabling compact evidence"],
      ["Reader", "frozen LLM via API", "isolates the effect of memory control from the reader"],
      ["Evaluation", "5-fold cross-validation over conversations", "every conversation is tested once on a policy that never saw it"],
    ], [1900, 3200, 4980]),
  ];
}

function ch4() {
  setChapter(4);
  return [
    H1("CHAPTER 4: IMPLEMENTATION"),
    H2("4.1 Software Architecture"),
    P("The system is implemented as a Python package, *memctl*, organised as shown in Table 4.1. Experiments are scripts on top of the package, and every result is written to a JSON file so that tables and figures in this report are generated directly from them."),
    ...table("Modules of the memctl package", ["Module", "Responsibility"], [
      ["data/locomo.py, data/longmemeval.py", "benchmark loaders: sessions, dated turns, questions, gold evidence"],
      ["store.py", "memory items with provenance; dense, BM25 and keyword-graph indices; Personalized PageRank"],
      ["features.py", "observable question, item, question–item and budget features"],
      ["policy.py", "MLP scorer, Gumbel sampling, Plackett–Luce log-probability, REINFORCE with leave-one-out baseline"],
      ["retention.py", "query-free retention features, heuristic eviction rules, streaming eviction"],
      ["baselines.py", "random, recency, dense, BM25, hybrid fusion, hybrid + PageRank, Generative-Agents-style rankers"],
      ["llm.py", "reader, LLM judge and fact extraction with on-disk cache, spend guard and content-filter handling"],
      ["api.py", "public BudgetedMemory class"],
    ], [3400, 6680]),
    H2("4.2 Environment"),
    ...table("Experimental environment", ["Item", "Setting"], [
      ["Hardware", "laptop GPU: NVIDIA RTX 3060 (6 GB), 16 CPU threads; orchestration from an Apple M4 laptop"],
      ["Operating system", "Ubuntu under Windows Subsystem for Linux 2"],
      ["Libraries", "PyTorch 2.6 (CUDA 12.4), sentence-transformers, rank-bm25, spaCy 3.8, NetworkX, tiktoken, OpenAI SDK, mem0ai 2.2"],
      ["Embedding model", "BAAI/bge-base-en-v1.5 (local)"],
      ["LLMs", "GPT-4.1 (Azure, Sep 2026 runs) and GPT-4o-mini (OpenAI, Nov 2026 runs); temperature 0"],
      ["Tokeniser for budgets", "o200k (the GPT-4o / GPT-4.1 tokeniser)"],
    ], [2600, 7480]),
    H2("4.3 Data Pipeline"),
    P("For LoCoMo, each turn becomes an item rendered as \"[date] speaker: text\"; shared photos are represented by their captions. Facts are extracted with one LLM call per session using the prompt in Appendix B; relative dates are converted to absolute ones and each fact keeps the identifiers of its source turns. For LongMemEval, messages longer than 150 tokens are split into sentence-aligned chunks so that one long message cannot exhaust a small read budget. Features for every question are precomputed once and cached."),
    H2("4.4 LLM Layer"),
    P("All LLM calls go through one module with three safeguards. A deterministic on-disk cache keyed by the full request makes reruns free and results reproducible. A spend guard estimates the cost of every uncached call and stops a run that would exceed a configured limit. Calls blocked by a provider's content filter are recorded and counted as wrong answers rather than crashing the run; such false positives occurred on a handful of LoCoMo conversations."),
    H2("4.5 Open-Source Interface"),
    P("The library exposes a two-line interface. Memory is written turn by turn; forgetting runs at session boundaries; recall returns the best evidence within a read budget, ready to place in any LLM prompt:"),
    ...code([
      "from memctl import BudgetedMemory",
      "mem = BudgetedMemory(store_budget=8192)            # tokens kept in memory",
      "mem.add(\"I adopted a puppy named Max\", speaker=\"Alice\", time=t)",
      "mem.end_session()                                  # retention runs here",
      "evidence = mem.recall(\"What is Alice's dog called?\", read_budget=256)",
    ]),
    H2("4.6 Testing"),
    P("Unit tests cover the evidence parser, date handling, packing within budgets, the agreement between vectorised and reference recall computations, the Plackett–Luce probabilities (which must sum to one over all permutations), the direction of the REINFORCE gradient, and the public API's guarantee that memory never exceeds its storage budget."),
  ];
}

function ch5() {
  setChapter(5);
  const out = [H1("CHAPTER 5: EXPERIMENTS AND RESULTS")];
  out.push(H2("5.1 Experimental Protocol"));
  out.push(P("All LoCoMo experiments use five-fold cross-validation over the ten conversations: policies are trained on eight conversations and tested on the remaining two, so every conversation is tested once by a policy that never saw it. The 1,535 non-adversarial questions with valid evidence are used. Read budgets range from 64 to 2,048 tokens and storage budgets from 1,024 to 8,192 tokens. Answers are graded by an LLM judge with the protocol used by Mem0 and LightMem [@mem0, lightmem]."));
  out.push(P("Two reader models were used. Experiments run in September 2026 used **GPT-4.1** on Azure as reader and judge. In November 2026 the Azure resource was no longer available and the remaining experiments used **GPT-4o-mini** through the OpenAI API under a fixed budget. Each experiment compares methods only under the same reader, so the conclusions do not depend on the change; absolute numbers from the two settings should not be compared with each other."));

  // 5.2 retrieval
  out.push(H2("5.2 Learned Retrieval under a Read Budget"));
  const r1 = R.e1, r1b = R.e1b;
  out.push(P(`Evidence recall measures the fraction of a question's gold evidence turns that end up in the packed context. On a store of raw turns, the learned budget-agnostic ranker raises the area under the recall curve from ${f3(r1?.hybrid_ppr?.auc)} (best heuristic, hybrid retrieval with PageRank) to ${f3(r1?.rl_agnostic?.auc)}. On the store with extracted facts, recall rises at every budget, and reinforcement learning clearly beats pointwise supervised learning (${f3(r1b?.rl_agnostic?.auc)} against ${f3(r1b?.sup_bce?.auc)}): a fact and its source turn cover the same evidence, so the reward is not additive and a set-level objective helps. With mixed item types, the budget-conditioned policy is best (${f3(r1b?.rl_cond?.auc)}).`));
  out.push(...figure("fig2_retrieval_recall.png", "Evidence recall versus read budget (five-fold cross-validation)"));
  const names = [["random", "random"], ["bm25", "BM25"], ["dense", "dense"], ["hybrid_rrf", "hybrid (RRF)"], ["hybrid_ppr", "hybrid + PageRank"],
    ["sup_bce", "supervised (BCE)"], ["rl_agnostic", "RL, budget-agnostic"], ["rl_cond", "RL, budget-conditioned"]];
  out.push(...table("Evidence recall (area under the recall–budget curve)", ["Method", "Turns only", "Turns + facts"],
    names.map(([k, n]) => [n, f3(r1?.[k]?.auc), f3(r1b?.[k]?.auc)]), [3800, 3000, 3280]));

  // 5.3 retention
  out.push(H2("5.3 Learned Retention under a Storage Budget"));
  const r2 = R.e2;
  out.push(P(`Conversations are streamed session by session and evicted to *B_store* after every session. Retain-recall is the fraction of each question's gold evidence still in memory at the end. The learned retention policy keeps ${f3(r2?.learned_rl?.auc)} of future evidence on average across budgets, against ${f3(r2?.redundancy?.auc)} for the best heuristic (redundancy-aware eviction) and ${f3(r2?.fifo?.auc)} for first-in-first-out — a 52% relative improvement, consistent in all five folds. The hand-weighted importance score was worse than simple redundancy removal (${f3(r2?.importance?.auc)}), echoing the finding that generic importance is not the same as task utility [@oslmr].`));
  out.push(...figure("fig3_retention.png", "Retain-recall versus storage budget under streaming eviction", 5.0));

  // 5.4 joint recall
  out.push(H2("5.4 Joint Retention and Retrieval"));
  const r4 = R.e4;
  out.push(P(`Combining the two policies, evidence that is both kept under *B_store* and packed under *B_read* rises from ${f3(r4?.["redundancy+hybrid_ppr"]?.mean)} for the best heuristic pair to ${f3(r4?.["learned+learned"]?.mean)}, a 65% relative gain (Figure 5.3). Most of the gain comes from learned retention; learned retrieval adds a further improvement on top of it.`));
  out.push(...figure("fig4_joint.png", "Joint evidence recall for combinations of retention and retrieval policies", 5.4));

  // 5.5 QA (gpt-4.1)
  out.push(H2("5.5 End-to-End Question Answering (GPT-4.1 Reader)"));
  const e3 = R.e3, e3b = R.e3b, full = acc(R.e3full, "full_context@0");
  out.push(P(`The packed evidence is given to the reader and each answer is graded by the judge. On the raw-turn store with 256 evidence tokens, the learned ranker answers ${pct(acc(e3, "rl_agnostic@256"))}% of questions correctly, against ${pct(acc(e3, "hybrid_ppr@256"))}% for hybrid retrieval with PageRank and ${pct(acc(e3, "dense@256"))}% for dense retrieval. On the store with facts, the budget-conditioned policy is best at every budget and reaches ${pct(acc(e3b, "rl_cond@1024"))}% with 1,024 tokens, close to the ${pct(full)}% obtained by reading the entire conversation (about 24,000 tokens per question).`));
  out.push(...table("LLM-judge accuracy (%) with a GPT-4.1 reader and judge", ["Store / method", "64", "128", "256", "1,024"], [
    ...[["dense", "turns: dense"], ["hybrid_ppr", "turns: hybrid + PageRank"], ["rl_agnostic", "turns: learned"]].map(([k, n]) =>
      [n, pct(acc(e3, `${k}@64`)), pct(acc(e3, `${k}@128`)), pct(acc(e3, `${k}@256`)), pct(acc(e3, `${k}@1024`))]),
    ...[["hybrid_rrf", "facts: hybrid (RRF)"], ["dense", "facts: dense"], ["rl_agnostic", "facts: learned, budget-agnostic"], ["rl_cond", "facts: learned, budget-conditioned"]].map(([k, n]) =>
      [n, pct(acc(e3b, `${k}@64`)), pct(acc(e3b, `${k}@128`)), pct(acc(e3b, `${k}@256`)), pct(acc(e3b, `${k}@1024`))]),
    ["full conversation (~24K tokens)", pct(full), pct(full), pct(full), pct(full)],
  ], [3900, 1545, 1545, 1545, 1545]));
  out.push(...figure("fig5_qa.png", "LLM-judge accuracy at matched read budgets (GPT-4.1 reader and judge)"));
  out.push(P("Paired exact McNemar tests on 1,524 questions (Table 5.3) show that on the store with facts the learned policy's gain over dense retrieval is significant at 64 and 128 tokens and borderline at 256 and 1,024 tokens, while its gain over hybrid fusion is significant at every budget up to 256 tokens. The difference between the budget-conditioned and budget-agnostic variants is not significant at any budget."));
  out.push(...table("Paired exact McNemar tests: budget-conditioned learned policy against alternatives (store with facts)", ["Budget", "vs. dense", "vs. hybrid (RRF)", "vs. budget-agnostic"], [
    ["64", "+1.7 pts, p = 0.048", "+6.1 pts, p < 0.001", "+0.8 pts, p = 0.31"],
    ["128", "+1.6 pts, p = 0.050", "+4.2 pts, p < 0.001", "+0.7 pts, p = 0.43"],
    ["256", "+1.3 pts, p = 0.064", "+3.4 pts, p < 0.001", "+0.9 pts, p = 0.22"],
    ["1,024", "+1.1 pts, p = 0.078", "+1.0 pts, p = 0.15", "+0.6 pts, p = 0.35"],
  ], [1600, 2800, 2800, 2880]));

  // 5.6 Mem0
  out.push(H2("5.6 Comparison with Mem0"));
  const m0 = R.mem0;
  out.push(P(`Mem0 [@mem0] was re-run with its official library inside the same harness: the same GPT-4.1 model for its memory extraction, the same local embedding model, and the same reader, judge and budgets. Mem0's open-source version resolves relative dates against the current date, so the session date was supplied as its observation date. At matched budgets the learned controller is far ahead, especially when budgets are tight (Table 5.4). Mem0 needs its default of about 3,300 tokens per question to reach the accuracy the learned controller achieves with 1,024 tokens.`));
  out.push(...table("Mem0 against the learned controller at matched read budgets (GPT-4.1 reader and judge)", ["Evidence budget", "Mem0 (%)", "Learned controller (%)", "Difference"], [
    ...[64, 128, 256, 1024].map((b) => { const a = acc(m0, `mem0@${b}`), c = acc(e3b, `rl_cond@${b}`);
      return [`${b} tokens`, pct(a), pct(c), a !== undefined && c !== undefined ? `+${(100 * (c - a)).toFixed(1)} pts` : "–"]; }),
    ["Mem0 default (~3,300 tokens)", pct(acc(m0, "mem0@native")), "–", "–"],
  ], [3300, 2200, 2700, 1880]));

  // 5.7 full controller (gpt-4o-mini)
  out.push(H2("5.7 Full Controller: Storage and Read Budgets Together"));
  const e6 = R.e6;
  if (e6 && e6.accuracy) {
    const A = (k) => e6.accuracy[k]?.acc;
    const rows = [];
    for (const bs of [2048, 8192]) for (const br of [256, 1024]) {
      rows.push([`${bs / 1024}K / ${br}`, pct(A(`fifo+dense@${bs}/${br}`)), pct(A(`redundancy+hybrid_rrf@${bs}/${br}`)), pct(A(`learned+learned@${bs}/${br}`))]);
    }
    const best = (bs, br) => (100 * (A(`learned+learned@${bs}/${br}`) - A(`redundancy+hybrid_rrf@${bs}/${br}`))).toFixed(1);
    out.push(P(`This experiment runs the complete controller end to end with GPT-4o-mini as reader and judge: each held-out conversation is streamed with forgetting at *B_store*, then each question's evidence is packed at *B_read*. The learned controller is compared with first-in-first-out memory plus dense retrieval and with the best heuristic pair from Section 5.4 (redundancy-aware eviction plus hybrid fusion). Under the tightest setting (2K tokens of memory, 256 tokens read) the learned controller is ${best(2048, 256)} points ahead of the best heuristic pair; with 8K tokens of memory and 1,024 read it is ${best(8192, 1024)} points ahead (Table 5.5).`));
    out.push(...table("Full controller accuracy (%) under storage / read budgets (GPT-4o-mini reader and judge)", ["B_store / B_read", "FIFO + dense", "redundancy + hybrid", "learned + learned"], rows, [2600, 2400, 2600, 2480]));
    out.push(P(`With 2K tokens of memory the learned controller scores the same at both read budgets (${pct(A("learned+learned@2048/256"))}%): almost everything it kept already fits in 256 read tokens, so accuracy is limited by what survived forgetting, not by retrieval. With 8K tokens of memory the read budget matters again. FIFO memory is the weakest at every setting because it discards early sessions that many questions refer to. The GPT-4o-mini numbers are lower than the GPT-4.1 numbers of Section 5.5 and must not be compared with them directly; comparisons are only valid within one table.`));
    out.push(...figure("fig6_full_controller.png", "Accuracy of the full controller under storage and read budgets (GPT-4o-mini)", 5.6));
  } else {
    out.push(P("(Results of the full-controller experiment are being generated and will be inserted here.)"));
  }

  // 5.8 LongMemEval
  out.push(H2("5.8 Transfer to LongMemEval"));
  const e7 = R.e7, e7b = R.e7b;
  if (e7 && e7.accuracy) {
    const rec = e7.recall;
    const A = (k) => e7.accuracy?.[k]?.acc;
    out.push(P(`To test generalisation, the retrieval policies trained on all ten LoCoMo conversations were first applied without any retraining to the 500 questions of LongMemEval-S [@longmemeval], whose histories are about 115,000 tokens of user–assistant task dialogue rather than conversations between friends. Messages were split into chunks of at most 150 tokens; no LLM was used to build memory, and GPT-4o-mini was reader and judge. The policies were then retrained on LongMemEval itself with 5-fold cross-validation over questions, so that every question is still answered by a policy that never saw it (Table 5.6).`));
    const rows = [["dense", "dense"], ["bm25", "BM25"], ["hybrid_rrf", "hybrid (RRF)"], ["hybrid_ppr", "hybrid + PageRank"], ["rl_agnostic", "learned on LoCoMo (zero-shot)"], ["rl_cond", "learned on LoCoMo, budget-conditioned"]]
      .map(([k, n]) => [n, f3(rec?.[k]?.auc), f3(rec?.[k]?.["256"]), f3(rec?.[k]?.["1024"]), pct(A(`${k}@256`)), pct(A(`${k}@1024`))]);
    if (e7b) rows.push(["learned on LongMemEval (5-fold CV)", f3(e7b.recall.auc), f3(e7b.recall["256"]), f3(e7b.recall["1024"]),
      pct(e7b.accuracy?.["rl_indomain@256"]?.acc), pct(e7b.accuracy?.["rl_indomain@1024"]?.acc)]);
    out.push(...table("LongMemEval-S: evidence recall and accuracy (%) of heuristic and learned retrieval (GPT-4o-mini reader and judge)",
      ["Method", "Recall AUC", "Recall @256", "Recall @1,024", "Acc. @256", "Acc. @1,024"], rows, [3000, 1200, 1200, 1300, 1600, 1780]));
    const hy = rec.hybrid_rrf;
    out.push(P(`**Zero-shot transfer fails.** The LoCoMo-trained policies are below hybrid fusion on LongMemEval (recall AUC ${f3(rec.rl_agnostic.auc)} and ${f3(rec.rl_cond.auc)} against ${f3(hy.auc)}; accuracy at 1,024 tokens ${pct(A("rl_agnostic@1024"))}% and ${pct(A("rl_cond@1024"))}% against ${pct(A("hybrid_rrf@1024"))}%). A likely reason is that the policies learned feature weightings that suit short persona chat between two named speakers (speaker, photo and item-length features carry signal there) and that do not hold for long assistant answers in task-oriented chat; this explanation was not tested separately.`));
    if (e7b) {
      const m = e7b.mcnemar || {};
      const sig = (b) => m[b] ? ` (paired McNemar p ${m[b].p < 0.001 ? "< 0.001" : "= " + m[b].p.toFixed(3)})` : "";
      out.push(P(`**Training in the new domain works.** Trained on LongMemEval questions, the same method raises recall AUC from ${f3(hy.auc)} to ${f3(e7b.recall.auc)} and recall at 1,024 tokens from ${f3(hy["1024"])} to ${f3(e7b.recall["1024"])}. Accuracy rises to ${pct(e7b.accuracy["rl_indomain@256"].acc)}% at 256 tokens${sig("256")} and ${pct(e7b.accuracy["rl_indomain@1024"].acc)}% at 1,024 tokens${sig("1024")}, against ${pct(A("hybrid_rrf@256"))}% and ${pct(A("hybrid_rrf@1024"))}% for hybrid fusion. The gain is significant at 256 tokens and borderline at 1,024 tokens. The learning method generalises; a particular set of trained weights does not. In practice a deployment should train, or at least fine-tune, the policy on its own interaction logs — which is cheap, since training needs only evidence labels and a few minutes on one GPU.`));
    }
  } else {
    out.push(P("(Results of the LongMemEval transfer experiment are being generated and will be inserted here.)"));
  }

  // 5.9 ablation and cost
  out.push(H2("5.9 Ablations and Cost"));
  const e8 = R.e8;
  if (e8) {
    const ab = e8.ablation;
    const lab = { full: "full model", no_context: "without set context", no_graph: "without graph features", no_lexical: "without BM25 features",
      no_dense: "without dense features", no_query_type: "without question-type features", linear: "linear scorer instead of MLP" };
    out.push(P(`Table 5.7 removes one feature group at a time from the budget-agnostic retrieval policy on the store with facts. The policy has ${e8.policy_params.toLocaleString("en-US")} parameters, trains in about ${Math.round(e8.train_seconds_per_fold.full)} seconds per fold on the 6 GB GPU, and ranks a question's memory in ${e8.inference_ms_per_query.mean.toFixed(1)} ms on average (95th percentile ${e8.inference_ms_per_query.p95.toFixed(1)} ms) — negligible next to an LLM call.`));
    out.push(...table("Ablation of the retrieval policy (evidence recall AUC, store with facts)", ["Variant", "Recall AUC", "Change vs. full"],
      Object.keys(lab).filter((k) => ab[k]).map((k) => [lab[k], f3(ab[k].auc), k === "full" ? "–" : (ab[k].auc - ab.full.auc >= 0 ? "+" : "") + (ab[k].auc - ab.full.auc).toFixed(3)]),
      [4600, 2700, 2780]));
    out.push(P(`Only the dense-similarity features are indispensable: removing them costs ${(ab.full.auc - ab.no_dense.auc).toFixed(3)} AUC. Every other group changes the AUC by less than 0.005, which is within the run-to-run variation of a single training seed, so these groups are largely redundant with one another rather than useless — the lexical, graph and keyword-overlap signals each recover much of what the others provide. A linear scorer matches the MLP, which indicates that the gain over the hand-tuned fusions of Section 5.1 comes mainly from optimising the feature weighting directly for budgeted evidence recall, not from the capacity of the scorer. For deployment this is a useful result: a linear policy over a handful of cheap features is enough.`));
  } else {
    out.push(P("(Results of the ablation study are being generated and will be inserted here.)"));
  }

  // 5.10 RL-fine-tuned LLM selector
  out.push(H2("5.10 Comparison with an RL-Fine-Tuned LLM Selector"));
  const e9 = R.e9, e9b = R.e9b, e9q = R.e9q;
  if (e9 && e9b) {
    const size = e9.model.includes("1.5B") ? "1.5-billion" : e9.model.includes("0.5B") ? "0.5-billion" : "small";
    out.push(P(`Recent memory systems fine-tune an LLM with reinforcement learning to make memory decisions [@memoryr1, memagent]. To compare this approach with the small policy directly, a ${size}-parameter instruction-tuned LLM (${e9.model.split("/").pop()}) was fine-tuned with Group Relative Policy Optimisation (GRPO) [@grpo] and low-rank adapters (LoRA, rank 16) [@lora] to perform the same budgeted selection. For each question it is shown the ${e9b.K} highest-ranked candidates of hybrid retrieval with their token counts and the read budget, and replies with candidate identifiers in priority order; these are packed in its order until the budget is full. The reward is the evidence recall of the packed set, the same signal the small policy is trained on, so no LLM judge is needed during training. Training used conversations 3–10 and testing conversations 1–2 (the first fold of the cross-validation); the model generated ${e9.gens} answers per question and was trained for ${e9.steps} steps on one ${e9.gpu.replace("NVIDIA ", "")} GPU in Google Colab (${Math.round(e9.train_seconds / 60)} minutes).`));
    const B = ["64", "128", "256"];
    const rr = (m) => B.map((b) => f3(e9b.recall[m]?.[b]));
    out.push(...table("Evidence recall of the LLM selector and the small policy on the same test questions",
      ["Method", "64", "128", "256"], [
        ["hybrid retrieval (candidate order)", ...rr("hybrid_top")],
        ["LLM selector, before RL", ...B.map((b) => f3(e9.base[b]?.recall))],
        ["LLM selector, after GRPO", ...B.map((b) => f3(e9.grpo[b]?.recall))],
        ["small policy, same candidates", ...rr("policy_cand")],
        ["small policy, whole memory", ...rr("policy_full")],
        ["best possible choice of candidates", ...rr("oracle_cand")],
      ], [4400, 1900, 1900, 1880]));
    if (e9q) {
      const A = (k) => pct(e9q.accuracy[k]);
      out.push(...table("Answer accuracy (%) of the LLM selector and the small policy (GPT-4o-mini reader and judge)",
        ["Method", "128 tokens", "256 tokens"], [
          ["hybrid retrieval", A("hybrid_top@128"), A("hybrid_top@256")],
          ["LLM selector, before RL", A("llm_base@128"), A("llm_base@256")],
          ["LLM selector, after GRPO", A("llm_grpo@128"), A("llm_grpo@256")],
          ["small policy, whole memory", A("policy_full@128"), A("policy_full@256")],
        ], [4800, 2640, 2640]));
    }
    out.push(...table("Cost of the two learned selectors", ["", "Small policy", "RL-fine-tuned LLM"], [
      ["Parameters (trained)", `${(R.e8?.policy_params ?? 24193).toLocaleString("en-US")} (all)`, `${size === "1.5-billion" ? "1.5 B (18.5 M LoRA)" : "0.5 B (LoRA)"}`],
      ["Training hardware and time", `RTX 3060 6 GB, about ${Math.round((R.e8?.train_seconds_per_fold?.full ?? 283) / 60)} minutes`, `${e9.gpu.replace("NVIDIA ", "")}, ${Math.round(e9.train_seconds / 60)} minutes`],
      ["Selection time per question", `${(R.e8?.inference_ms_per_query?.mean ?? 7.5).toFixed(1)} ms`, `${Math.round(e9.eval_ms_per_query.grpo)} ms (batches of 16)`],
    ], [3200, 3200, 3680]));
    const g = e9.grpo, b0 = e9.base, pc = e9b.recall.policy_cand, mq = e9q?.mcnemar ?? {};
    const pv = (k) => { const p = mq[k]?.p; return p == null ? "n/a" : p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(2)}`; };
    const ratioP = Math.round(1.5e9 / (R.e8?.policy_params ?? 24193) / 1000) * 1000, ratioT = Math.round(e9.eval_ms_per_query.grpo / (R.e8?.inference_ms_per_query?.mean ?? 7.5));
    out.push(P(`Reinforcement learning changed the LLM's behaviour substantially. Evidence recall at 64 tokens rose from ${f3(b0["64"].recall)} to ${f3(g["64"].recall)}, and answer accuracy at 128 tokens from ${pct(e9q.accuracy["llm_base@128"])}% to ${pct(e9q.accuracy["llm_grpo@128"])}% (${mq["llm_grpo_vs_llm_base@128"].wins} questions gained, ${mq["llm_grpo_vs_llm_base@128"].losses} lost, ${pv("llm_grpo_vs_llm_base@128")}). The strategy it learned is simple, however. It always lists candidate 1 first and, for 73% of questions, lists the candidates in their original order with seven or eight of them left out; its selection stays close to the hybrid order it is shown. Its outputs also became almost deterministic: late in training nearly every group of ${e9.gens} samples received identical rewards, which leaves GRPO no learning signal.`));
    out.push(P(`The LLM's evidence recall is above hybrid retrieval at every budget but below the small policy re-ranking the same candidates (${f3(g["64"].recall)} against ${f3(pc["64"])} at 64 tokens). On answer accuracy it beats hybrid retrieval at 128 tokens (${pct(e9q.accuracy["llm_grpo@128"])}% against ${pct(e9q.accuracy["hybrid_top@128"])}%, ${pv("llm_grpo_vs_hybrid_top@128")}; at 256 tokens ${pv("llm_grpo_vs_hybrid_top@256")}) and is statistically indistinguishable from the small policy (${pv("llm_grpo_vs_policy_full@128")} at 128 tokens, ${pv("llm_grpo_vs_policy_full@256")} at 256). With the same reward, a 1.5-billion-parameter LLM therefore reaches about the same end-to-end quality as a 24K-parameter policy, but needs about ${ratioP.toLocaleString("en-US")} times as many parameters, a datacentre GPU for training, and about ${ratioT} times as long per question. This is one fold, one seed and one model size, and longer training, larger sample groups or an entropy bonus might help the LLM. The result supports the use of a lightweight learned policy for budgeted selection over a given set of candidates. An LLM may still be the better choice for decisions that require reading and rewriting memory content, such as writing or merging memories, which is left to future work.`));
  } else {
    out.push(P("(Results of the LLM fine-tuning comparison are being generated and will be inserted here.)"));
  }
  return out;
}

function ch6() {
  setChapter(6);
  return [
    H1("CHAPTER 6: DISCUSSION"),
    H2("6.1 Main Findings"),
    ...numberedList([
      "**Learning helps most when budgets are tight.** Gains over heuristics are largest at 64–256 read tokens and at small storage budgets, in line with prior findings on budget pressure [@oas, coldrl].",
      "**Forgetting matters more than retrieval under storage pressure.** In the joint experiment most of the gain came from learned retention: evidence that has been evicted cannot be recovered by any retriever, as the eviction audit of [@evict] also observed.",
      "**Reinforcement learning matters when items overlap.** On raw turns, RL and supervised learning were tied because the reward is additive; with facts and their source turns in the same store, RL was clearly better because it learns not to spend budget on redundant items.",
      "**Compact facts are the cheapest way to raise accuracy at small budgets,** but they must keep provenance to the raw text, which the learned policy can fall back on.",
      "**Complete memory systems are token-hungry.** Mem0 needed about three times as many evidence tokens to match the learned controller.",
      "**The gains hold end to end with both budgets enforced.** Streaming each conversation with learned forgetting and then reading with the learned ranker was 17 to 22 points more accurate than the best heuristic pair at every storage and read budget tested (Section 5.7).",
      "**The method generalises; trained weights do not.** Policies trained on LoCoMo were below hybrid retrieval on LongMemEval, but the same method trained on LongMemEval questions beat it by 5 points at 256 tokens. Policies should be trained on the target domain (Section 5.8).",
      "**A fine-tuned LLM is not needed for budgeted selection.** A 1.5-billion-parameter LLM trained with GRPO on the same reward reached the same answer accuracy as the 24K-parameter policy (no significant difference), at about 60,000 times the parameters and 40 times the selection time (Section 5.10).",
      "**The scorer can be very simple.** In the ablation only the dense-similarity features were indispensable and a linear scorer matched the MLP: the benefit comes from optimising the weighting for the budgeted objective, not from model capacity.",
    ]),
    H2("6.2 Unexpected Results and Discrepancies"),
    ...numberedList([
      "Budget conditioning did not help on the raw-turn store (it reduced recall) and its end-to-end advantage on the facts store was not statistically significant. The budget-agnostic ranking suggested by the nested-set argument of KVP [@kvp] is already close to optimal for retrieval; budget conditioning is kept as an option but not claimed as a contribution.",
      "On the store with facts, the gain over plain dense retrieval is small (one to two points) and significant only at the tightest budgets. The policies are trained on evidence recall rather than answer accuracy; training on answer-level reward is the main lever for larger gains.",
      "Fact extraction depends on the LLM: GPT-4.1 produced 4,384 facts and GPT-4o-mini 2,939 for the same sessions, which changes the store between the September and November experiments. Results are therefore only compared within the same setting.",
      "A provider content filter blocked a few calls (false positives on LoCoMo topics). They were counted as wrong answers for every method affected.",
    ]),
    H2("6.3 Threats to Validity"),
    P("**LLM judge.** Accuracy is graded by an LLM using a lenient protocol shared with prior work; human agreement was not measured in this project. **Benchmark size.** LoCoMo has ten conversations; cross-validation uses all of them, but confidence intervals remain wide for small categories such as open-domain questions. **Reader strength.** LoCoMo conversations fit inside GPT-4.1's context window, which makes full context a strong upper reference; LongMemEval histories (about 115,000 tokens) show the practical value of budgets better, but they were evaluated only with GPT-4o-mini, a single training seed and without re-running Mem0. **Comparability.** Published numbers were not mixed with ours; every baseline in the tables was run in the same harness."),
  ];
}

function ch7() {
  setChapter(7);
  return [
    H1("CHAPTER 7: CONCLUSIONS AND RECOMMENDATIONS"),
    H2("7.1 Conclusions"),
    P("This dissertation set out to answer whether a small learned policy can decide what an LLM agent keeps and what it reads, under explicit token budgets, better than hand-tuned rules and existing memory systems. The answer is yes. A pair of small ranking policies, trained with ranking reinforcement learning on a reward averaged over budgets, kept 52% more future evidence than the best eviction heuristic, and together with learned retrieval kept-and-read 65% more evidence than the best heuristic pair. In end-to-end question answering the learned controller answered 69.7% of LoCoMo questions with only 64 evidence tokens, against 40.3% for Mem0 at the same budget, and reached 90.4% with 1,024 tokens, close to the 91.3% obtained by reading every conversation in full. With both budgets enforced at once, the complete controller was 17 to 22 points more accurate than the best heuristic pair. On LongMemEval the trained weights did not transfer from LoCoMo, but retraining the policy in that domain again beat the best heuristic, so the method — not one set of weights — is the contribution. A 1.5-billion-parameter LLM fine-tuned with reinforcement learning on the same reward matched the small policy's answer accuracy but did not exceed it, at tens of thousands of times its size. The policies are small enough to train in minutes on a laptop GPU and add no LLM calls to the memory."),
    H2("7.2 Recommendations"),
    ...numberedList([
      "Systems that deploy agent memory should treat storage and read limits as explicit inputs and report accuracy against budget, not at a single operating point.",
      "Memory should keep raw text with provenance alongside compact facts, so that a policy can trade compactness against fidelity.",
      "Eviction deserves as much attention as retrieval: when memory is bounded, what is forgotten cannot be recovered.",
      "Evaluations should re-run baselines in one harness with the same reader, judge and budgets, and use paired significance tests.",
    ]),
    H2("7.3 Future Work"),
    ...numberedList([
      "Study domain adaptation: fine-tune a LoCoMo-trained policy on a small number of labelled questions from a new domain, or learn from implicit signals in interaction logs instead of gold evidence labels.",
      "Train the policies on answer-level reward (LLM-judge correctness) rather than evidence recall, with caching to keep the cost manageable.",
      "Add learned consolidation actions (merge or summarise) whose value depends on budget pressure [@oas].",
      "Extend the RL-fine-tuned LLM of Section 5.10 from read-time selection to full memory management (writing, updating and merging memories, as in Memory-R1 [@memoryr1]) under the same budgets, and test whether an entropy bonus or larger sample groups avoid the output collapse observed there.",
      "Re-run further published systems (LightMem, Zero-Mem, JustMem) at matched budgets and extend evaluation to agentic tasks.",
      "Grow the open-source library: persistence, multi-user memory and integrations with agent frameworks.",
    ]),
  ];
}

// ================================================================== BACK MATTER
function references() {
  const { citeOrder, REFS } = L;
  return [
    H1("REFERENCES"),
    ...citeOrder.map((k, i) => new Paragraph({ spacing: { after: 100, line: 300 }, indent: { left: 600, hanging: 600 },
      alignment: AlignmentType.LEFT, children: [new TextRun({ text: `${i + 1}.\t${REFS[k]}`, size: 22 })] })),
  ];
}
function appendices() {
  const F = require("./final_features.js");
  return [
    H1("APPENDIX A: POLICY FEATURES"),
    ...(setChapter("A"), []),
    ...table("Retrieval policy features (29)", ["Group", "Feature", "Description"], F.retrieval, [1700, 2300, 6080], 18),
    ...table("Retention policy features (15)", ["Group", "Feature", "Description"], F.retention, [1700, 2300, 6080], 18),
    H1("APPENDIX B: PROMPTS"),
    ...(setChapter("B"), []),
    P("**Reader (system prompt).**", { line: 300 }),
    ...code(F.readerPrompt),
    P("**Judge prompt** (Mem0 / LightMem protocol, abridged).", { line: 300 }),
    ...code(F.judgePrompt),
    P("**Fact extraction prompt** (one call per session).", { line: 300 }),
    ...code(F.extractPrompt),
    H1("APPENDIX C: HYPERPARAMETERS"),
    ...(setChapter("C"), []),
    ...table("Training hyperparameters", ["Parameter", "Value"], F.hyper, [5000, 5080], 19),
    H1("APPENDIX D: REPRODUCING THE EXPERIMENTS"),
    ...(setChapter("D"), []),
    P("All experiments are scripts in the project repository and write their results to the results directory. With an OpenAI-compatible key in the .env file, the full pipeline is:", { line: 360 }),
    ...code([
      "uv sync",
      "uv run python scripts/precompute_locomo.py              # turn features",
      "uv run python scripts/extract_facts.py                  # one LLM call per session",
      "uv run python scripts/precompute_locomo.py --facts      # turn + fact features",
      "uv run python scripts/exp_retrieval.py                  # Section 5.2",
      "uv run python scripts/exp_retention.py                  # Section 5.3",
      "uv run python scripts/exp_joint.py                      # Section 5.4",
      "uv run python scripts/exp_qa.py --features locomo_turnsfacts.pkl \\",
      "        --methods dense hybrid_rrf rl_agnostic rl_cond --budgets 64 128 256 1024",
      "uv run python scripts/baseline_mem0.py build|search|qa   # Section 5.6",
      "uv run python scripts/exp_joint_qa.py                   # Section 5.7",
      "uv run python scripts/exp_lme.py                        # Section 5.8",
      "uv run python scripts/exp_lme_indomain.py               # Section 5.8 (in-domain)",
      "uv run python scripts/exp_ablation.py                   # Section 5.9",
      "uv run python scripts/llm_selector_data.py              # Section 5.10 data",
      "python scripts/colab_grpo_selector.py --steps 400 --lr 5e-5   # on a Colab GPU",
      "uv run python scripts/exp009_qa.py                      # Section 5.10 accuracy",
      "uv run python scripts/paired_test.py results/<file>_perq.json A@b B@b",
    ]),
  ];
}
function glossary() {
  const G = require("./final_features.js").glossary;
  return [H1("GLOSSARY"), ...(setChapter("G"), []), ...table("Glossary of terms", ["Term", "Meaning"], G, [2600, 7480], 19)];
}
function abbreviations() {
  const A = require("./final_features.js").abbreviations;
  return [H1front("LIST OF ABBREVIATIONS"), ...A.map(([a, b]) => new Paragraph({ spacing: { after: 40, line: 300 },
    tabStops: [{ type: D.TabStopType.LEFT, position: 2200 }], children: [new TextRun({ text: a, bold: true }), new TextRun(`\t${b}`)] }))];
}
function checklist() {
  const items = require("./final_features.js").checklist;
  const cell = (t, w, bold) => new TableCell({ borders: { top: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "808080" }, left: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "808080" } }, width: { size: w, type: WidthType.DXA },
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: t.split("\n").map((l) => new Paragraph({ spacing: { after: 20 }, children: [new TextRun({ text: l, size: 20, bold })] })) });
  return [
    H1front("CHECKLIST OF ITEMS FOR THE FINAL DISSERTATION REPORT"),
    P("This checklist is to be attached as the last page of the final report. This checklist is to be duly completed, verified and signed by the student.", { line: 300 }),
    new Table({ width: { size: L.TEXT_W, type: WidthType.DXA }, columnWidths: [700, 8180, 1200],
      rows: items.map(([n, q, a]) => new TableRow({ cantSplit: true, children: [cell(n, 700), cell(q, 8180), cell(a, 1200)] })) }),
    blank(200),
    P("**Declaration by Student:** I certify that I have properly verified all the items in this checklist and ensure that the report is in proper format as specified in the course handout.", { line: 300 }),
    blank(300),
    twoCol(["Place: Bangalore", "Date:"], ["Signature of the Student", `Name: ${STUDENT}`, `ID No.: ${ID}`]),
  ];
}

// ================================================================== CONTENTS / LISTS (static, page numbers from pass 1)
function contents(bodyHeadings) {
  const out = [H1front("TABLE OF CONTENTS")];
  for (const h of bodyHeadings) {
    if (h.text === "TABLE OF CONTENTS") continue;
    const indent = h.level <= 1 ? 0 : h.level === 2 ? 400 : 800;
    out.push(tocLine(h.text, pg(`h:${h.text}`), indent, h.level <= 1));
  }
  return out;
}
function listOf(title, items, prefix) {
  return [H1front(title), ...items.map((it) => tocLine(`${it.label}: ${it.caption}`, pg(`${prefix}:${it.label}`), 0))];
}

// ================================================================== ASSEMBLE
// Build body first (assigns figure/table numbers and citation order), then front matter lists.
const bodyCh = [...ch1(), ...ch2(), ...ch3(), ...ch4(), ...ch5(), ...ch6(), ...ch7()];
const backMatter = [...references(), ...appendices(), ...glossary(), ...checklist()];
const bodyHeadings = L.headings.slice();
L.headings.length = 0;
const frontA = [...certificate(), ...acknowledgements(), ...abstractSheet()];
const frontHeads = L.headings.slice();
const listsFig = L.figures.slice(), listsTab = L.tables.slice();
const front = [...frontA, ...contents([...frontHeads,
    { level: 0, text: "LIST OF FIGURES" }, { level: 0, text: "LIST OF TABLES" }, { level: 0, text: "LIST OF ABBREVIATIONS" }, ...bodyHeadings]),
  ...listOf("LIST OF FIGURES", listsFig, "f"), ...listOf("LIST OF TABLES", listsTab, "t"), ...abbreviations()];

const footer = (fmt) => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], size: 21 })] })] });
const pageProps = (extra = {}) => ({ page: { size: { width: L.PAGE_W, height: L.PAGE_H },
  margin: { top: L.MARGIN, right: L.MARGIN, bottom: L.MARGIN, left: L.MARGIN }, ...extra } });

const doc = new D.Document({
  creator: STUDENT, title: TITLE_CASE, description: "BITS WILP SEZG628T final dissertation report",
  styles: {
    default: { document: { run: { font: L.FONT, size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: L.FONT }, paragraph: { spacing: { before: 120, after: 320 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: L.FONT }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, italics: true, font: L.FONT }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: L.numberingConfigs },
  sections: [
    { properties: pageProps(), children: [...cover(), ...titlePage()] },                                   // unnumbered
    { properties: pageProps({ pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } }),         // i, ii, ...
      footers: { default: footer() }, children: front },
    { properties: pageProps({ pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } }),              // 1, 2, ...
      footers: { default: footer() }, children: [...bodyCh, ...backMatter] },
  ],
});

// write heading/figure/table keys for the TOC pass
fs.writeFileSync(path.join(__dirname, "toc_keys.json"), JSON.stringify({
  headings: [...frontHeads, ...bodyHeadings, { level: 0, text: "LIST OF FIGURES" }, { level: 0, text: "LIST OF TABLES" },
    { level: 0, text: "LIST OF ABBREVIATIONS" }].map((h) => h.text),
  figures: listsFig.map((f) => f.label), tables: listsTab.map((t) => t.label),
}, null, 1));
D.Packer.toBuffer(doc).then((buf) => {
  const out = path.join(L.ROOT, "report", "Final_Report.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, `| ${listsFig.length} figures, ${listsTab.length} tables, ${L.citeOrder.length} references`);
});
