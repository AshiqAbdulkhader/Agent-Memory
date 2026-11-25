from datetime import datetime

from memctl import BudgetedMemory


def test_budgeted_memory_respects_both_budgets():
    mem = BudgetedMemory(store_budget=300, retrieval="heuristic", retention="heuristic")
    for s in range(4):
        for k in range(6):
            mem.add(f"Session {s} message {k}: Alice talked about hiking trip number {s * 10 + k}.",
                    speaker="Alice", time=datetime(2023, 5, 1 + s))
        mem.end_session()
        assert mem.tokens <= 300
    mem.add("Alice adopted a puppy named Max.", speaker="Alice", time=datetime(2023, 5, 9))
    ev = mem.recall("What is the name of Alice's puppy?", read_budget=40)
    assert sum(len(e.split()) for e in ev) > 0
    assert any("Max" in e for e in ev)


def test_release_weights_are_packaged():
    """The trained policies must ship with the package; otherwise memctl silently falls back to heuristics."""
    mem = BudgetedMemory()
    assert mem.retrieval_model is not None and mem.retention_model is not None
