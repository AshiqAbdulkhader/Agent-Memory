"""Write-time LLM fact extraction: one call per LoCoMo session -> data/facts/locomo_facts.json.

Each fact keeps provenance (the dia_ids it was extracted from), so fact items count as covering a
question's evidence exactly when they were derived from the gold turns.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memctl import llm  # noqa: E402
from memctl.data.locomo import load_locomo  # noqa: E402

OUT = ROOT / "data" / "facts" / "locomo_facts.json"


def main():
    convs = load_locomo()
    jobs = [(c.sample_id, i, s, c.session_times[i]) for c in convs for i, s in enumerate(c.sessions)]

    def run(job):
        sid, i, turns, t = job
        return sid, i, llm.extract_facts(turns, t.strftime("%d %B %Y"))

    out: dict = {}
    with ThreadPoolExecutor(8) as ex:
        for sid, i, facts in ex.map(run, jobs):
            out.setdefault(sid, {})[str(i)] = facts
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    n = sum(len(f) for c in out.values() for f in c.values())
    print(f"{n} facts from {len(jobs)} sessions; usage {llm.USAGE.by_role}")


if __name__ == "__main__":
    main()
