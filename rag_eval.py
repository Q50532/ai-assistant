"""Evaluate WorkHub's existing KB retriever with grounded retrieval labels.

Run inside the AI Assistant project directory after dependencies are installed:
    python rag_eval.py  (run with the project virtual environment)

This tests retrieval, NOT Gemini answer quality, authorization, or factual accuracy.
"""
from __future__ import annotations

import time
from kb_store import search_kb

# Gold document IDs refer to the existing WorkHub README-based knowledge index.
# Recheck these labels whenever README chunks are rebuilt or reordered.
CASES = [
    ("What Ticket status transitions does WorkHub allow?", "readme-4"),
    ("How does WorkHub cache Ticket details using Redis Cache Aside?", "readme-6"),
    ("How are Ticket status updates managed in database transactions?", "readme-7"),
    ("How does Spring Security protect user login and sessions?", "readme-5"),
    ("What REST endpoint retrieves a Ticket by ID?", "readme-10"),
    ("How does WorkHub organize its Controller Service and Mapper layers?", "readme-9"),
    ("What automated validation and service tests are described?", "readme-15"),
    ("What limitations remain for transaction tests and cache consistency?", "readme-17"),
    ("Where is the MySQL database connection configured?", "readme-12"),
    ("What technologies are used in WorkHub?", "readme-2"),
]


def main():
    hits_at_1 = 0
    hits_at_3 = 0
    total_seconds = 0.0
    print("KB retrieval evaluation (10 questions, top_k=3)")
    for index, (query, expected) in enumerate(CASES, 1):
        start = time.perf_counter()
        retrieved = search_kb(query, top_k=3)
        elapsed = time.perf_counter() - start
        total_seconds += elapsed
        ids = [item["id"] for item in retrieved]
        top_score = retrieved[0]["score"] if retrieved else None
        hit1 = bool(ids and ids[0] == expected)
        hit3 = expected in ids
        hits_at_1 += hit1
        hits_at_3 += hit3
        print(f"{index:02} {'PASS' if hit3 else 'MISS'}  gold={expected}  top3={ids}  top1_score={top_score}")
    n = len(CASES)
    print(f"\nHit@1: {hits_at_1}/{n} ({hits_at_1 / n:.0%})")
    print(f"Recall@3: {hits_at_3}/{n} ({hits_at_3 / n:.0%})")
    print(f"Avg retrieval latency: {total_seconds / n * 1000:.1f} ms (includes model initialization)")
    # Negative probe: the current retriever always returns top_k nearest chunks,
    # even for unrelated questions. These scores are diagnostic, not a cutoff.
    unrelated = "How do I bake a chocolate cake?"
    neg_hits = search_kb(unrelated, top_k=3)
    print("\nOut-of-domain probe:", unrelated)
    print("Top matches (not necessarily relevant):", [(x["id"], x["score"]) for x in neg_hits])
    print("Note: a similarity score alone does not prove that evidence supports an answer.")


if __name__ == "__main__":
    main()
