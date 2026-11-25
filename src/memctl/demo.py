"""Live demo of budgeted memory:  python -m memctl.demo   (add --interactive to ask your own questions)

A short scripted chat between Alice and Bob is streamed into two memories with the SAME storage budget:
  heuristic  redundancy-aware eviction + hybrid (dense + BM25) retrieval
  learned    the learned retention and retrieval policies
Then the same questions are asked at a tight and a loose read budget, and the evidence each memory hands to
the LLM is shown. The conversation is written for illustration and was not used to train the policies; it shows
how the library behaves, it is not a benchmark (see the report for the measured results).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

# Keep the screen clean for presenting: no progress bars or library warnings (set MEMCTL_VERBOSE=1 to see them).
if not os.environ.get("MEMCTL_VERBOSE"):
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    for name in ("torch.distributed.elastic.multiprocessing.redirects", "transformers", "sentence_transformers"):
        logging.getLogger(name).setLevel(logging.ERROR)

from memctl import BudgetedMemory  # noqa: E402

BOLD, DIM, GREEN, RED, BLUE, END = "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[34m", "\033[0m"
if not sys.stdout.isatty():
    BOLD = DIM = GREEN = RED = BLUE = END = ""

STORE_BUDGET = 450  # tokens the memory may hold; the chat below is about 3x larger

# (date, [(speaker, text), ...]) — a few facts worth remembering buried in everyday chatter
SESSIONS = [
    (datetime(2026, 5, 3), [
        ("Alice", "Guess what, I adopted a puppy yesterday! His name is Max and he is a golden retriever."),
        ("Bob", "That is wonderful news, congratulations! Is he already house trained?"),
        ("Alice", "Not at all, he chewed through two cushions last night, but he is adorable."),
        ("Bob", "Send me a picture when you can. Anyway, I need coffee, long week at the office."),
        ("Alice", "Same here. The weather has been so grey lately, I hope it clears up soon."),
        ("Bob", "Me too. I watched a boring documentary about bridges last night."),
    ]),
    (datetime(2026, 5, 10), [
        ("Bob", "Reminder for the dinner party: I am allergic to peanuts, so please keep them out of anything I eat."),
        ("Alice", "Of course, no peanuts. I will make pasta instead, is that fine?"),
        ("Bob", "Pasta is perfect. What time should I come over on Saturday?"),
        ("Alice", "Around seven works. The traffic on the ring road is terrible these days though."),
        ("Bob", "I will take the train. I am also bringing a bottle of wine, maybe two."),
        ("Alice", "Great. Have you seen the new series everyone is talking about?"),
    ]),
    (datetime(2026, 5, 17), [
        ("Alice", "I got a job offer in Lisbon! I start there on the first of September."),
        ("Bob", "Congratulations, that is huge. Will you move for good?"),
        ("Alice", "Yes, Max and I are relocating, I already started looking at flats near the river."),
        ("Bob", "You will love the food there. The weather is much sunnier than here."),
        ("Alice", "Honestly I just hope the flat has a balcony. Max needs room to run."),
        ("Bob", "I will check my calendar to visit you in autumn."),
    ]),
    (datetime(2026, 5, 24), [
        ("Bob", "I signed up for the Porto marathon on the twelfth of October and I have started training."),
        ("Alice", "Impressive! How far did you run this morning?"),
        ("Bob", "Only eight kilometres, my knee hurt a little. The weather was grey and a bit windy."),
        ("Alice", "Take it slowly. I tried a new yoga class yesterday and I could barely walk."),
        ("Bob", "Ha, I know that feeling. Did you try the new bakery on the corner?"),
        ("Alice", "Yes, the bread is good but the coffee is really weak."),
    ]),
    (datetime(2026, 5, 31), [
        ("Alice", "My sister Clara is getting married in Seville in June, I am her maid of honour."),
        ("Bob", "How lovely. Are you giving a speech?"),
        ("Alice", "Yes, and I am terrified. I keep rewriting it every evening."),
        ("Bob", "You will do great. Is Max coming along?"),
        ("Alice", "No, my neighbour will look after him. Did you finish that documentary about bridges?"),
        ("Bob", "I gave up halfway. The coffee machine at work is broken again, by the way."),
    ]),
    (datetime(2026, 6, 7), [
        ("Bob", "The office is so quiet today, half the team is on holiday."),
        ("Alice", "Lucky them. I spent the whole weekend cleaning the flat."),
        ("Bob", "The weather forecast says rain all week, so I will stay in and watch films."),
        ("Alice", "I might do the same. Any recommendation for a good comedy?"),
        ("Bob", "Not really, everything I watched lately was mediocre. Let me know if you find something."),
        ("Alice", "Will do. I also need to buy new shoes, my old ones are falling apart."),
    ]),
]

QUESTIONS = [
    ("What is the name of Alice's dog?", "Max"),
    ("What is Bob allergic to?", "peanuts"),
    ("Where is Alice moving for her new job?", "Lisbon"),
    ("Which marathon is Bob running?", "Porto"),
    ("Where is Clara's wedding?", "Seville"),
]


def build(**kw) -> BudgetedMemory:
    mem = BudgetedMemory(store_budget=STORE_BUDGET, **kw)
    return mem


def stream(memories: dict[str, BudgetedMemory]) -> None:
    print(f"{BOLD}1. Streaming the conversation{END} (storage budget: {STORE_BUDGET} tokens per memory)\n")
    seen = 0
    for n, (date, turns) in enumerate(SESSIONS, 1):
        for speaker, text in turns:
            for m in memories.values():
                m.add(text, speaker=speaker, time=date)
            seen += len(text.split())
        for m in memories.values():
            m.end_session()
        row = "   ".join(f"{k}: {m.tokens:>3} tokens, {len(m):>2} items" for k, m in memories.items())
        print(f"  session {n}  ({date:%d %b})   {row}")
    print(f"\n  {DIM}Both memories stay within {STORE_BUDGET} tokens, so each had to forget. What did they keep?{END}\n")


def facts_kept(memories: dict[str, BudgetedMemory]) -> None:
    print(f"{BOLD}2. Which key facts survived forgetting?{END}\n")
    head = "".join(f"{k:>12}" for k in memories)
    print(f"  {'fact':<28}{head}")
    for q, gold in QUESTIONS:
        marks = ""
        for m in memories.values():
            ok = any(gold.lower() in it.text.lower() for it in m.store.items)
            word = "kept" if ok else "forgotten"
            marks += " " * (12 - len(word)) + (GREEN if ok else RED) + word + END
        print(f"  {gold:<28}{marks}")
    print()


def ask(memories: dict[str, BudgetedMemory], question: str, gold: str | None, budget: int, llm: bool) -> dict[str, bool]:
    print(f"  {BOLD}Q: {question}{END}   {DIM}(read budget {budget} tokens){END}")
    hits = {}
    for k, m in memories.items():
        ev = m.recall(question, read_budget=budget)
        hit = gold is not None and any(gold.lower() in e.lower() for e in ev)
        hits[k] = hit
        tag = f"{GREEN}answer present{END}" if hit else (f"{RED}answer missing{END}" if gold else "")
        print(f"    {BLUE}{k:<9}{END} {len(ev)} snippets, {sum(len(e.split()) for e in ev)} words  {tag}")
        for e in ev[:3]:
            print(f"      {DIM}{e[:110]}{END}")
        if llm and ev:
            from memctl import llm as L  # needs OPENAI_API_KEY; optional

            print(f"      {BOLD}LLM answer:{END} {L.answer(question, ev)}")
    print()
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--budgets", type=int, nargs="+", default=[64, 256], help="read budgets in tokens")
    ap.add_argument("--llm", action="store_true", help="also answer with an LLM (needs OPENAI_API_KEY)")
    ap.add_argument("--interactive", action="store_true", help="ask your own questions afterwards")
    args = ap.parse_args()

    print(f"\n{BOLD}memctl demo: learned memory control under a storage budget and a read budget{END}\n")
    memories = {"heuristic": build(retrieval="heuristic", retention="heuristic"), "learned": build()}
    stream(memories)
    facts_kept(memories)

    print(f"{BOLD}3. Asking questions at two read budgets{END}\n")
    score = {b: dict.fromkeys(memories, 0) for b in args.budgets}
    for b in args.budgets:
        for q, gold in QUESTIONS:
            for k, hit in ask(memories, q, gold, b, args.llm).items():
                score[b][k] += hit
    print(f"{BOLD}Answer present in the evidence, out of {len(QUESTIONS)}{END}")
    for b in args.budgets:
        print(f"  read budget {b:>4}: " + "   ".join(f"{k} {v}" for k, v in score[b].items()))
    print(f"\n{DIM}Illustrative run on a hand-written chat; measured results are in the report.{END}\n")

    if args.interactive:
        budget = args.budgets[0]
        print(f"Ask anything about the chat. '/budget N' changes the read budget (now {budget}); empty line quits.")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                break
            if line.startswith("/budget"):
                budget = int(line.split()[1])
                print(f"  read budget = {budget}")
                continue
            ask(memories, line, None, budget, args.llm)


if __name__ == "__main__":
    main()
