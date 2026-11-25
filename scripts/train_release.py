"""Train the released policies on all 10 LoCoMo conversations and save them to src/memctl/weights/.

retrieval.pt: budget-conditioned ranking policy on the turns + facts substrate (EXP-001b recipe)
retention.pt: query-free retention policy on turns + facts session snapshots (EXP-006 recipe)
"""

import json
import pickle
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from exp_joint_qa import build_conv, retention_episodes, train_retention  # noqa: E402
from exp_retrieval import train_rl  # noqa: E402
from precompute_locomo import FACTS  # noqa: E402
from memctl.data.locomo import load_locomo  # noqa: E402

OUT = ROOT / "src" / "memctl" / "weights"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    feats = pickle.load(open(ROOT / "data/features/locomo_turnsfacts.pkl", "rb"))
    retr = train_rl(feats, True, 6, seed=0).cpu().eval()
    torch.save(retr.state_dict(), OUT / "retrieval.pt")
    convs, facts = load_locomo(), json.load(open(FACTS))
    eps = [e for c in convs for e in retention_episodes(c, *build_conv(c, facts))]
    ret = train_retention(eps, 12, seed=0).cpu().eval()
    torch.save(ret.state_dict(), OUT / "retention.pt")
    print("saved", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
