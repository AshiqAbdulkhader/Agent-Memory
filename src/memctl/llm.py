"""OpenAI calls (reader, judge, fact extraction) with a deterministic on-disk cache and token accounting."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")  # source checkout; an installed package reads the process environment
# In a source checkout caches live under data/; an installed package uses the user cache directory.
DATA = ROOT / "data" if (ROOT / "pyproject.toml").exists() else Path(os.environ.get("MEMCTL_HOME", Path.home() / ".cache" / "memctl"))
CACHE = DATA / "cache" / "llm"

# Model names; on Azure these are *deployment* names.
READER_MODEL = os.environ.get("MEMCTL_READER", "gpt-4o-mini")
JUDGE_MODEL = os.environ.get("MEMCTL_JUDGE", "gpt-4o-mini")
EXTRACT_MODEL = os.environ.get("MEMCTL_EXTRACT", "gpt-4o-mini")
USE_AZURE = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    by_role: dict = field(default_factory=dict)
    filtered: dict = field(default_factory=dict)  # Azure content-filter refusals per role
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, role: str, p: int, c: int) -> None:
        with self._lock:
            self.calls += 1
            self.prompt_tokens += p
            self.completion_tokens += c
            r = self.by_role.setdefault(role, [0, 0, 0])
            r[0] += 1
            r[1] += p
            r[2] += c


USAGE = Usage()

# Spend guard: estimated $ of *uncached* calls in this process, persisted across runs in data/cache/spend.json.
PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4.1": (2.0, 8.0), "gpt-4.1-mini": (0.4, 1.6)}  # $ per 1M in/out
MAX_USD = float(os.environ.get("MEMCTL_MAX_USD", "0") or 0)  # 0 = no limit
_SPEND_FILE = DATA / "cache" / "spend.json"
_spend_lock = threading.Lock()


class BudgetExceeded(RuntimeError):
    pass


def _record_spend(model: str, p: int, c: int) -> None:
    pin, pout = PRICES.get(model, (2.0, 8.0))
    with _spend_lock:
        _SPEND_FILE.parent.mkdir(parents=True, exist_ok=True)
        total = json.loads(_SPEND_FILE.read_text())["usd"] if _SPEND_FILE.exists() else 0.0
        total += (p * pin + c * pout) / 1e6
        _SPEND_FILE.write_text(json.dumps({"usd": total}))
    if MAX_USD and total > MAX_USD:
        raise BudgetExceeded(f"estimated spend ${total:.2f} exceeds MEMCTL_MAX_USD=${MAX_USD}")


def spent_usd() -> float:
    return json.loads(_SPEND_FILE.read_text())["usd"] if _SPEND_FILE.exists() else 0.0
FILTERED = "<<CONTENT_FILTERED>>"  # counted as a wrong answer / failed grade; totals reported in results
_client = None


def _openai():
    global _client
    if _client is None:
        if USE_AZURE:
            from openai import AzureOpenAI

            # reads AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT from the environment
            _client = AzureOpenAI(api_version=os.environ.get("OPENAI_API_VERSION", "2024-10-21"), max_retries=8)
        else:
            from openai import OpenAI

            _client = OpenAI(max_retries=8)
    return _client


def chat(messages: list[dict], model: str, role: str, max_tokens: int = 300, json_mode: bool = False) -> str:
    """Temperature-0 chat completion, cached by (model, messages, json_mode). Usage is counted even on
    cache hits so reported costs reflect a cold run."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps([model, messages, json_mode, max_tokens]).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    rec = None
    if f.exists():
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError:  # partially written by a concurrent thread → treat as a miss
            rec = None
    if rec is None:
        kw = dict(model=model, messages=messages, temperature=0, max_tokens=max_tokens)
        if json_mode:
            kw["response_format"] = {"type": "json_object"}
        from openai import BadRequestError

        try:
            r = _openai().chat.completions.create(**kw)
            text = r.choices[0].message.content
            if r.choices[0].finish_reason == "content_filter":
                text = FILTERED
            rec = dict(text=text or "", p=r.usage.prompt_tokens, c=r.usage.completion_tokens)
            _record_spend(model, rec["p"], rec["c"])
        except BadRequestError as e:  # Azure content filter false positives (e.g. LGBTQ topics in LoCoMo)
            if "content_filter" not in str(e):
                raise
            rec = dict(text=FILTERED, p=0, c=0)
        tmp = f.with_suffix(f".{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(rec))
        os.replace(tmp, f)  # atomic: readers never see a partial file
    USAGE.add(role, rec["p"], rec["c"])
    if rec["text"] == FILTERED:
        with USAGE._lock:
            USAGE.filtered[role] = USAGE.filtered.get(role, 0) + 1
    return rec["text"]


# ------------------------------------------------------------------ reader

READER_SYSTEM = (
    "You answer questions about a long conversation between two people using ONLY the memory snippets "
    "provided. Each snippet starts with the date it was said. Resolve relative dates (e.g. 'last week', "
    "'yesterday') against the snippet's date and give absolute dates when asked 'when'. Answer concisely "
    "(a few words or one short sentence). If the snippets do not contain the answer, give your best guess "
    "from them rather than refusing."
)


def answer(question: str, snippets: list[str], question_date: str | None = None) -> str:
    mem = "\n".join(f"- {s}" for s in snippets) if snippets else "(no memory available)"
    date = f"Today's date: {question_date}\n" if question_date else ""  # None keeps LoCoMo cache keys unchanged
    return chat(
        [{"role": "system", "content": READER_SYSTEM},
         {"role": "user", "content": f"{date}Memory snippets:\n{mem}\n\nQuestion: {question}\nAnswer:"}],
        READER_MODEL, "reader", max_tokens=100,
    ).strip()


# ------------------------------------------------------------------ judge (Mem0 / LightMem protocol)

JUDGE_PROMPT = """Your task is to label an answer to a question as 'CORRECT' or 'WRONG'. You will be given:
(1) a question (posed by one user to another user),
(2) a 'gold' (ground truth) answer,
(3) a generated answer
which you will score as CORRECT/WRONG.

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
Question: Do you remember what I got the last time I went to Hawaii?
Gold answer: A shell necklace
The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it's time for the real question:
Question: {question}
Gold answer: {gold}
Generated answer: {pred}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

Just return the label CORRECT or WRONG in a json format with the key as "label"."""


def judge(question: str, gold: str, pred: str) -> bool:
    if pred == FILTERED:
        return False
    out = chat([{"role": "user", "content": JUDGE_PROMPT.format(question=question, gold=gold, pred=pred)}],
               JUDGE_MODEL, "judge", max_tokens=150, json_mode=True)
    if out == FILTERED:
        return False
    try:
        return json.loads(out).get("label", "").strip().upper() == "CORRECT"
    except json.JSONDecodeError:
        return "CORRECT" in out.upper() and "WRONG" not in out.upper()


# ------------------------------------------------------------------ write-time fact extraction (1 call / session)

EXTRACT_PROMPT = """Extract durable, answer-bearing facts from this conversation session as atomic memories.
Each memory must be one independently understandable statement with an explicit subject (use the person's
name, never "I"/"he"/"she"), and must preserve exact names, numbers, places, titles and dates. Convert
relative time expressions into absolute dates using the session date ({date}). Include events, plans,
preferences, possessions, relationships, and details of shared photos. Skip greetings and small talk.
For each memory list the ids of the turns it comes from.

Return JSON: {{"memories": [{{"fact": "...", "turns": ["D1:3", ...]}}, ...]}}

Session date: {date}
Session:
{turns}"""


def extract_facts(session_turns, date_str: str) -> list[dict]:
    body = "\n".join(f"[{t.dia_id}] {t.speaker}: {t.text}" for t in session_turns)
    out = chat([{"role": "user", "content": EXTRACT_PROMPT.format(date=date_str, turns=body)}],
               EXTRACT_MODEL, "extract", max_tokens=2000, json_mode=True)
    try:
        mems = json.loads(out).get("memories", [])
    except json.JSONDecodeError:
        return []
    valid = {t.dia_id for t in session_turns}
    return [dict(fact=m["fact"], turns=[d for d in m.get("turns", []) if d in valid])
            for m in mems if isinstance(m, dict) and m.get("fact")]
