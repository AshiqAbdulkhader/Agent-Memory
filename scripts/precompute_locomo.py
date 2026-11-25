"""Build the turn-level memory store for each LoCoMo conversation and cache per-question features.

Output: data/features/locomo_turns.pkl — list of dicts per conversation:
  sample_id, item_ids, n_tokens[N], item_x[N, Fi], questions: [{q, answer, category, evidence,
  x[N, F-2], cover[N, |E|] (bool: item i contains evidence e)}]
"""

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memctl.data.locomo import load_locomo  # noqa: E402
from memctl.features import build_features, item_features  # noqa: E402
from memctl.store import MemoryItem, MemoryStore, turns_to_items  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "data" / "facts" / "locomo_facts.json"


def fact_items(c, facts: dict) -> list[MemoryItem]:
    """Fact items interleaved per session: [date] fact, provenance = source dia_ids."""
    out = []
    spk = {t.dia_id: t.speaker for t in c.turns}
    for i, t in enumerate(c.session_times):
        for k, f in enumerate(facts.get(str(i), [])):
            src = f["turns"] or []
            out.append(MemoryItem(f"F{i + 1}:{k}", "fact", f"[{t:%d %B %Y}] {f['fact']}", i + 1, t,
                                  spk.get(src[0], "") if src else "", src))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", action="store_true", help="add LLM atomic facts to the store")
    args = ap.parse_args()
    OUT = ROOT / "data" / "features" / ("locomo_turnsfacts.pkl" if args.facts else "locomo_turns.pkl")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    facts = json.load(open(FACTS)) if args.facts else {}
    convs = load_locomo()
    out = []
    t0 = time.time()
    for c in convs:
        items = turns_to_items(c.turns)
        if args.facts:  # order: each session's turns followed by its facts
            fi = fact_items(c, facts[c.sample_id])
            items = sorted(items + fi, key=lambda it: (it.session, it.kind == "fact"))
        store = MemoryStore(items)
        base = item_features(store)
        ids = [it.id for it in store.items]
        qs = []
        for qa in c.qa:
            turn_ids = {t.dia_id for t in c.turns}
            ev = [e for e in qa.evidence if e in turn_ids]
            if not ev:
                continue
            cover = np.array([[e in it.sources for e in ev] for it in store.items], bool)
            qs.append(dict(q=qa.question, answer=qa.answer, category=qa.category, evidence=ev,
                           x=build_features(store, qa.question, base).astype(np.float16), cover=cover))
        out.append(dict(sample_id=c.sample_id, item_ids=ids, n_tokens=np.array([it.n_tokens for it in store.items]),
                        item_texts=[it.text for it in store.items], item_x=base, questions=qs))
        print(f"{c.sample_id}: {len(ids)} items, {store.total_tokens} tokens, {len(qs)} questions "
              f"({time.time() - t0:.0f}s)", flush=True)
    pickle.dump(out, open(OUT, "wb"))
    print("saved", OUT)


if __name__ == "__main__":
    main()
