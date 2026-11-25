"""Mem0 baseline on LoCoMo, following Mem0's own evaluation harness (evaluation/src/memzero):
each session is added in 2-message batches (the session date is injected as Mem0's observation date,
because Mem0 OSS otherwise resolves relative dates against "today") for BOTH speakers' perspectives (user_id per speaker), with
the session timestamp as metadata; questions search both speakers' memories.

LLM = the same Azure gpt-4.1 deployment (via OPENAI_BASE_URL); embedder = the same local
BAAI/bge-base-en-v1.5 used by memctl, so retrieval quality differences come from Mem0's memory
construction, not from a different embedding model.

Phases:
  build  : construct Mem0 memories per conversation (skips conversations already built)
  search : retrieve top-50 memories per speaker for every question -> data/mem0/search.json
  qa     : answer + judge with memories packed into B_read tokens (and Mem0's native top-k)
"""

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")
os.environ.setdefault("MEM0_TELEMETRY", "False")

from memctl import llm  # noqa: E402
from memctl.data.locomo import CATEGORY_NAMES, load_locomo  # noqa: E402
from memctl.tokens import count_tokens  # noqa: E402

BASE = ROOT / "data" / "mem0"
_SESSION_DATE = threading.local()


def _patch_mem0_dates():
    """Mem0 OSS builds its extraction prompt with current_date/observation date defaulting to *today*
    (the platform-only `timestamp` arg is ignored). Inject the LoCoMo session date instead, so relative
    dates ("yesterday") resolve as they would for a live deployment at conversation time."""
    import mem0.memory.main as mm

    orig = mm.generate_additive_extraction_prompt
    if getattr(orig, "_patched", False):
        return

    def wrapped(*a, **kw):
        d = getattr(_SESSION_DATE, "value", None)
        if d:
            kw.setdefault("current_date", d)
            kw.setdefault("timestamp", d)
        return orig(*a, **kw)

    wrapped._patched = True
    mm.generate_additive_extraction_prompt = wrapped


def memory_for(sample_id: str):
    from mem0 import Memory

    _patch_mem0_dates()
    d = BASE / sample_id
    d.mkdir(parents=True, exist_ok=True)
    return Memory.from_config({
        "llm": {"provider": "openai", "config": {"model": os.environ["MEMCTL_EXTRACT"], "temperature": 0,
                                                  "max_tokens": 2000}},
        "embedder": {"provider": "huggingface", "config": {"model": "BAAI/bge-base-en-v1.5", "embedding_dims": 768}},
        "vector_store": {"provider": "qdrant", "config": {"collection_name": "m", "path": str(d / "qdrant"),
                                                          "embedding_model_dims": 768, "on_disk": True}},
        "history_db_path": str(d / "history.db"),
    })


def build(c):
    done = BASE / c.sample_id / "DONE"
    if done.exists():
        return c.sample_id, "cached"
    m = memory_for(c.sample_id)
    a, b = c.speakers
    skipped = 0
    for sess, t in zip(c.sessions, c.session_times):
        ts = t.strftime("%I:%M %p on %d %B, %Y")
        _SESSION_DATE.value = t.date().isoformat()
        for spk, uid in ((a, f"{a}_{c.sample_id}"), (b, f"{b}_{c.sample_id}")):
            msgs = [{"role": "user" if x.speaker == spk else "assistant", "content": f"{x.speaker}: {x.text}"}
                    for x in sess]
            for i in range(0, len(msgs), 2):
                try:
                    m.add(msgs[i:i + 2], user_id=uid, metadata={"timestamp": ts})
                except Exception as e:  # Azure content-filter false positives: skip the batch, count it
                    if "content_filter" not in str(e):
                        raise
                    skipped += 1
    done.write_text(f"ok skipped_batches={skipped}")
    return c.sample_id, f"built (skipped {skipped} filtered batches)"


def search(c, top_k=50):
    m = memory_for(c.sample_id)
    out = []
    for qa in c.qa:
        mems = []
        for spk in c.speakers:
            r = m.search(qa.question, top_k=top_k, filters={"user_id": f"{spk}_{c.sample_id}"}, threshold=0.0)
            for it in r.get("results", r) if isinstance(r, dict) else r:
                ts = (it.get("metadata") or {}).get("timestamp", "")
                mems.append(dict(text=f"[{ts}] {spk}: {it['memory']}", score=float(it.get("score", 0.0))))
        mems.sort(key=lambda x: -x["score"])
        out.append(dict(question=qa.question, answer=qa.answer, category=qa.category, memories=mems))
    return c.sample_id, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["build", "search", "qa"])
    ap.add_argument("--budgets", type=int, nargs="+", default=[256, 1024])
    ap.add_argument("--native_k", type=int, default=30, help="Mem0 eval default: top-30 per speaker")
    args = ap.parse_args()
    convs = load_locomo()

    if args.phase == "build":
        with ThreadPoolExecutor(5) as ex:
            for sid, status in ex.map(build, convs):
                print(sid, status, flush=True)
        return

    if args.phase == "search":
        res = dict(search(c) for c in convs)
        json.dump(res, open(BASE / "search.json", "w"))
        n_mem = {c.sample_id: len(res[c.sample_id][0]["memories"]) if res[c.sample_id] else 0 for c in convs}
        print("saved", BASE / "search.json", n_mem)
        return

    res = json.load(open(BASE / "search.json"))
    jobs = []
    for sid, qs in res.items():
        for q in qs:
            for b in args.budgets:
                sel, used = [], 0
                for mm in q["memories"]:
                    t = count_tokens(mm["text"])
                    if used + t > b:
                        break
                    sel.append(mm["text"])
                    used += t
                jobs.append((f"mem0@{b}", q, sel, used))
            native = [mm["text"] for mm in q["memories"][: 2 * args.native_k]]
            jobs.append(("mem0@native", q, native, sum(count_tokens(x) for x in native)))

    def run(job):
        name, q, sel, used = job
        return name, q["category"], used, llm.judge(q["question"], q["answer"], llm.answer(q["question"], sel))

    from collections import defaultdict
    acc, toks = defaultdict(list), defaultdict(list)
    with ThreadPoolExecutor(16) as ex:
        for name, cat, used, ok in ex.map(run, jobs):
            acc[name].append(ok)
            acc[(name, cat)].append(ok)
            toks[name].append(used)
    summary = {}
    for name in sorted(k for k in acc if isinstance(k, str)):
        cats = {CATEGORY_NAMES[c]: float(np.mean(acc[(name, c)])) for c in (1, 2, 3, 4) if acc[(name, c)]}
        summary[name] = dict(acc=float(np.mean(acc[name])), mean_evidence_tokens=float(np.mean(toks[name])), by_category=cats)
        print(f"{name:12s} J={np.mean(acc[name]):.3f} tokens/q={np.mean(toks[name]):.0f} "
              + " ".join(f"{k}={v:.3f}" for k, v in cats.items()))
    json.dump(summary, open(ROOT / "results" / "baseline_mem0.json", "w"), indent=2)


if __name__ == "__main__":
    main()
