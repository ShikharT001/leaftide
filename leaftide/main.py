"""
main.py
-------
CLI entry point for the Leaftide Tea Co. knowledge answering system.

Usage
-----
    # Run the three required worked examples
    python main.py --examples

    # Interactive Q&A session
    python main.py

    # Use a different knowledge directory
    python main.py --knowledge path/to/other/knowledge

Environment
-----------
    LLM_PROVIDER     openai or groq
    OPENAI_API_KEY   required when LLM_PROVIDER=openai
    GROQ_API_KEY     required when LLM_PROVIDER=groq
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from src.config import get_groq_api_key, get_llm_provider, get_openai_api_key, load_dotenv

# ---------------------------------------------------------------------------
# Startup checks — fail fast with clear messages
# ---------------------------------------------------------------------------

def _check_api_key() -> None:
    provider = get_llm_provider()
    if provider == "groq" and not get_groq_api_key():
        print("\n[ERROR] GROQ_API_KEY environment variable is not set.")
        print("        Add it to .env:")
        print("        GROQ_API_KEY=gsk_...")
        sys.exit(1)
    if provider == "openai" and not get_openai_api_key():
        print("\n[ERROR] OPENAI_API_KEY environment variable is not set.")
        print("        Add it to .env:")
        print("        OPENAI_API_KEY=sk-...")
        sys.exit(1)
    if provider not in {"openai", "groq"}:
        print(f"\n[ERROR] Unsupported LLM_PROVIDER: {provider}")
        print("        Use LLM_PROVIDER=openai or LLM_PROVIDER=groq")
        sys.exit(1)


def _check_knowledge_dir(kdir: Path) -> None:
    required = ["knowledge.md", "tone.md", "rules.md"]
    missing = [f for f in required if not (kdir / f).exists()]
    if missing:
        print(f"\n[ERROR] Missing files in '{kdir}': {missing}")
        print("        Check your knowledge directory is complete.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Pipeline bootstrap
# ---------------------------------------------------------------------------

def build_pipeline(knowledge_dir: str):
    """
    Load all knowledge files, build the embedding index,
    and return (checker, retriever, answerer) ready to use.
    """
    from src.loader import load_all
    from src.embedder import build_index
    from src.retriever import build_retriever
    from src.rules_checker import build_checker
    from src.answerer import build_answerer

    kdir = Path(knowledge_dir)
    _check_knowledge_dir(kdir)

    print(f"\n[SYSTEM] Loading knowledge from '{kdir}/'...")
    chunks, tone, rules = load_all(kdir)
    print(f"[SYSTEM] {len(chunks)} facts | {len(rules)} rules loaded.")

    index     = build_index(chunks)
    retriever = build_retriever(index, top_k=3, min_score=0.25)
    checker   = build_checker(rules)
    answerer  = build_answerer(tone)

    print("[SYSTEM] Pipeline ready.\n")
    return checker, retriever, answerer


# ---------------------------------------------------------------------------
# Core query handler
# ---------------------------------------------------------------------------

def handle_query(query: str, checker, retriever, answerer) -> None:
    """Run a single query through the full pipeline and print the result."""

    print(f"\n{'─' * 60}")
    print(f"  Query: {query}")
    print(f"{'─' * 60}")

    # Step 1 — Rules check (fires before anything else)
    check = checker.check(query)
    if not check.allowed:
        print(f"\n  {check.decline_message}\n")
        return

    # Step 2 — Retrieve relevant facts
    retrieval = retriever.retrieve(query)
    if retrieval.scores:
        top_score = retrieval.scores[0]
        print(f"[RETRIEVAL] {len(retrieval.chunks)} chunk(s) retrieved "
              f"(top score: {top_score:.3f})")

    # Step 3 — Generate grounded answer
    try:
        answer = answerer.answer(query, retrieval)
    except RuntimeError as exc:
        print(f"\n[ERROR] {exc}\n")
        return

    # Step 4 — Display
    print()
    print(answer.display())
    print()


# ---------------------------------------------------------------------------
# Three required worked examples
# ---------------------------------------------------------------------------

EXAMPLES = [
    {
        "label": "Example 1 — Straight factual answer",
        "description": (
            "A simple question about pricing. "
            "No retrieval ambiguity; the answer is a direct fact from knowledge.md."
        ),
        "query": "How much does Chamomile Calm cost?",
    },
    {
        "label": "Example 2 — Answer grounded in retrieved facts",
        "description": (
            "A brewing question. The system retrieves the relevant brewing "
            "instructions and grounds the answer in those specific facts."
        ),
        "query": "How should I brew the Jasmine Silver Needle?",
    },
    {
        "label": "Example 3 — Correct decline (Rule 2: health claim)",
        "description": (
            "A health-claim question. Rule 2 fires before retrieval or LLM "
            "are called. The decline message comes verbatim from rules.md."
        ),
        "query": "Does your chamomile tea help with anxiety and sleep problems?",
    },
]


def run_examples(checker, retriever, answerer) -> None:
    print("\n" + "=" * 60)
    print("  LEAFTIDE TEA CO. — THREE WORKED EXAMPLES")
    print("=" * 60)

    for i, ex in enumerate(EXAMPLES, 1):
        print(f"\n\n{'#' * 60}")
        print(f"  {ex['label']}")
        print(f"  {ex['description']}")
        print(f"{'#' * 60}")
        handle_query(ex["query"], checker, retriever, answerer)

    print("=" * 60)
    print("  END OF WORKED EXAMPLES")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def run_interactive(checker, retriever, answerer) -> None:
    print("\n" + "=" * 60)
    print("  LEAFTIDE TEA CO. — INTERACTIVE MODE")
    print("  Type your question and press Enter.")
    print("  Type 'quit' or press Ctrl-C to exit.")
    print("=" * 60)

    while True:
        try:
            query = input("\n  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye.\n")
            break

        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            print("\n  Goodbye.\n")
            break

        handle_query(query, checker, retriever, answerer)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Leaftide Tea Co. — Knowledge Answering System"
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Run the three required worked examples and exit.",
    )
    parser.add_argument(
        "--knowledge",
        default="knowledge",
        metavar="DIR",
        help="Path to the knowledge directory (default: ./knowledge)",
    )
    args = parser.parse_args()

    _check_api_key()

    checker, retriever, answerer = build_pipeline(args.knowledge)

    if args.examples:
        run_examples(checker, retriever, answerer)
    else:
        run_interactive(checker, retriever, answerer)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
