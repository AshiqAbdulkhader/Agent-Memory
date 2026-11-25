"""Figures for the mid-sem report, generated from results/*.json."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 200})
C = {"ours": "#1f5aa6", "ours2": "#6aa2e0", "base": "#9a9a9a", "base2": "#c9a227", "base3": "#b5523b", "ref": "#333333"}


def load(name):
    p = R / name
    return json.load(open(p)) if p.exists() else None


def fig_architecture():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis("off")

    def box(x, y, w, h, text, fc="#eef3fb", ec="#1f5aa6", bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.6,
                fontweight="bold" if bold else "normal", wrap=True)

    def arrow(x1, y1, x2, y2, text=""):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11, lw=1.1, color="#444"))
        if text:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, text, ha="center", fontsize=7.5, color="#444")

    box(1, 34, 16, 12, "Conversation\nstream\n(sessions, turns)", fc="#f4f4f4", ec="#777")
    box(20, 40, 26, 9, "Write (cheap)\nraw turns + provenance\n+ 1 LLM call / session → facts", fc="#f4f4f4", ec="#777")
    box(22, 27, 22, 10, "Hybrid memory substrate\ndense (bge-base) · BM25\nkeyword graph + PPR", bold=False)
    box(50, 36, 22, 12, "Retention policy π_keep\n(query-free features)\nkeep top-ranked ≤ B_store", fc="#dde8f7", bold=True)
    box(50, 15, 22, 12, "Retrieval policy π_read\n(query–item features, budget)\npack top-ranked ≤ B_read", fc="#dde8f7", bold=True)
    box(78, 15, 20, 12, "Reader LLM\n(frozen, gpt-4.1)\n→ answer", fc="#f4f4f4", ec="#777")
    box(22, 5, 22, 9, "Query", fc="#f4f4f4", ec="#777")
    box(78, 36, 20, 12, "Training signal\nranking RL: Plackett–Luce,\nREINFORCE-LOO,\nreward = AUC over budgets", fc="#fff6df", ec="#c9a227")
    arrow(17, 41, 22, 44)
    arrow(33, 40, 33, 37)
    arrow(44, 33, 50, 41, "evict")
    arrow(61, 36, 61, 27, "kept items")
    arrow(44, 10, 55, 15)
    arrow(72, 21, 78, 21, "evidence")
    arrow(88, 36, 72, 43)
    arrow(88, 36, 72, 25)
    ax.text(50, 50.5, "Budgets B_store (tokens kept) and B_read (evidence tokens per query) are hard constraints",
            ha="center", fontsize=8.5, style="italic", color="#1f5aa6")
    fig.tight_layout()
    fig.savefig(OUT / "fig1_architecture.png")
    plt.close(fig)


def fig_retrieval_recall():
    a, b = load("exp001_retrieval.json"), load("exp001b_retrieval_facts.json")
    budgets = [64, 128, 256, 512, 1024, 2048]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, d, title in ((axes[0], a, "Store: raw turns"), (axes[1], b, "Store: turns + LLM facts")):
        for name, lab, col, ls in (("dense", "dense", C["base"], "-"), ("hybrid_ppr", "hybrid + PPR", C["base2"], "-"),
                                   ("sup_bce", "supervised (BCE)", C["base3"], "--"),
                                   ("rl_agnostic", "RL, budget-agnostic", C["ours2"], "-"),
                                   ("rl_cond", "RL, budget-conditioned", C["ours"], "-")):
            if d and name in d:
                ax.plot(budgets, [d[name]["recall"][str(x)] for x in budgets], ls, marker="o", ms=3.5, color=col,
                        label=lab, lw=2 if name.startswith("rl") else 1.4)
        ax.set_xscale("log", base=2)
        ax.set_xticks(budgets, [str(x) for x in budgets])
        ax.set_xlabel("read budget B_read (tokens)")
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("evidence recall")
    axes[1].legend(fontsize=7.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_retrieval_recall.png")
    plt.close(fig)


def fig_retention():
    d = load("exp002_retention.json")
    budgets = [1024, 2048, 4096, 8192]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for name, lab, col in (("fifo", "FIFO", C["base"]), ("random", "random", "#d0d0d0"),
                           ("importance", "importance heuristic", C["base3"]),
                           ("redundancy", "redundancy-aware", C["base2"]), ("learned_rl", "learned (RL)", C["ours"])):
        ax.plot(budgets, [d[name]["retain_recall"][str(b)] for b in budgets], marker="o", ms=3.5, color=col, label=lab,
                lw=2.2 if name == "learned_rl" else 1.4)
    ax.set_xscale("log", base=2)
    ax.set_xticks(budgets, ["1K", "2K", "4K", "8K"])
    ax.set_xlabel("storage budget B_store (tokens)")
    ax.set_ylabel("retain-recall")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_retention.png")
    plt.close(fig)


def fig_joint():
    d = load("exp004_joint.json")
    names = [("fifo+dense", "FIFO + dense"), ("redundancy+hybrid_ppr", "redundancy +\nhybrid-PPR"),
             ("redundancy+learned", "redundancy +\nlearned"), ("learned+hybrid_ppr", "learned +\nhybrid-PPR"),
             ("learned+learned", "learned +\nlearned")]
    vals = [d[k]["mean"] for k, _ in names]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    cols = [C["base"], C["base2"], C["ours2"], C["ours2"], C["ours"]]
    bars = ax.bar(range(len(vals)), vals, color=cols)
    for bb, v in zip(bars, vals):
        ax.text(bb.get_x() + bb.get_width() / 2, v + 0.006, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(vals)), [n for _, n in names], fontsize=8)
    ax.set_ylabel("joint evidence recall\n(mean over B_store × B_read)")
    fig.tight_layout()
    fig.savefig(OUT / "fig4_joint.png")
    plt.close(fig)


def fig_qa():
    turns, facts, full = load("exp003_qa.json"), load("exp003b_qa_facts.json"), load("exp003_fullctx.json")
    fig, ax = plt.subplots(figsize=(7, 3.4))
    groups = [("dense", "dense"), ("hybrid_ppr", "hybrid+PPR"), ("hybrid_rrf", "hybrid RRF"),
              ("rl_agnostic", "RL agnostic"), ("rl_cond", "RL conditioned")]
    x = 0
    ticks, labels = [], []
    for store, d, hatch in (("turns", turns, ""), ("facts", facts, "//")):
        for key, lab in groups:
            for b, alpha in ((256, 0.55), (1024, 1.0)):
                k = f"{key}@{b}"
                if d and k in d:
                    col = C["ours"] if key.startswith("rl") else C["base"]
                    ax.bar(x, d[k]["acc"], color=col, alpha=alpha, hatch=hatch, edgecolor="white")
                    ax.text(x, d[k]["acc"] + 0.005, f"{d[k]['acc']:.2f}", ha="center", fontsize=6.5, rotation=90)
                    ticks.append(x)
                    labels.append(f"{lab}\n{b}")
                    x += 1
        x += 0.8
    if full:
        ax.axhline(full["full_context@0"]["acc"], color=C["ref"], ls="--", lw=1)
        ax.text(0, full["full_context@0"]["acc"] + 0.008, "full context (~24K tokens)", fontsize=7.5)
    ax.set_xticks(ticks, labels, fontsize=6, rotation=90)
    ax.set_ylim(0.55, 1.0)
    ax.set_ylabel("LLM-judge accuracy")
    ax.set_title("left: raw-turn store · right (hatched): turns + facts   (light = 256, dark = 1024 tokens)", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig5_qa.png")
    plt.close(fig)


def fig_full_controller():
    d = load("exp006_joint_qa.json")
    if not d or "accuracy" not in d:
        return
    a = d["accuracy"]
    cfg = [(2048, 256), (2048, 1024), (8192, 256), (8192, 1024)]
    combos = [("fifo+dense", "FIFO + dense", C["base"]), ("redundancy+hybrid_rrf", "redundancy + hybrid", C["base2"]),
              ("learned+learned", "learned + learned", C["ours"])]
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    w = 0.26
    for j, (k, lab, col) in enumerate(combos):
        vals = [a.get(f"{k}@{bs}/{br}", {}).get("acc", 0) for bs, br in cfg]
        bars = ax.bar([i + (j - 1) * w for i in range(len(cfg))], vals, w, color=col, label=lab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{100 * v:.0f}", ha="center", fontsize=7)
    ax.set_xticks(range(len(cfg)), [f"B_store {bs // 1024}K\nB_read {br}" for bs, br in cfg], fontsize=8)
    ax.set_ylabel("LLM-judge accuracy")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "fig6_full_controller.png")
    plt.close(fig)


if __name__ == "__main__":
    fig_architecture()
    fig_retrieval_recall()
    fig_retention()
    fig_joint()
    fig_qa()
    fig_full_controller()
    print("figures in", OUT)
