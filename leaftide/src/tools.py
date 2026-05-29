"""
tool.py
-------
Task C — Callable tool wrapper.

Exposes a single clean function `answer()` that another program can invoke
without knowing anything about the internal pipeline.

How to support many knowledge sets without rewriting code
---------------------------------------------------------
The `knowledge_dir` parameter is the only thing that changes between domains.
Any team can create a new folder containing the same three files
(knowledge.md, tone.md, rules.md) and pass its path to `answer()` —
the pipeline loads, embeds, and answers entirely from that folder.
No code changes are needed: rules, tone, and facts are fully data-driven.
To serve multiple domains simultaneously, call `build_pipeline()` once per
directory and cache the returned pipeline object; each pipeline is independent.

Example
-------
    from src.tool import answer

    result = answer(
        query="How do I brew the Darjeeling First Flush?",
        knowledge_dir="knowledge",
    )
    print(result["answer"])
    # -> "The Darjeeling First Flush is best brewed at 90–95 °C for 3–4 minutes..."
"""

from __future__ import annotations
from pathlib import Path
from typing import TypedDict


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class AnswerResult(TypedDict):
    answer: str           # the response text shown to the user
    declined: bool        # True if a rule fired or retrieval was empty
    decline_reason: str   # which rule fired and why (empty string if not declined)
    sources: list[str]    # the knowledge chunks used to form the answer
    query: str            # the original query (for logging / tracing)


# ---------------------------------------------------------------------------
# Pipeline cache — avoids rebuilding the index on every call
# ---------------------------------------------------------------------------

_pipeline_cache: dict[str, tuple] = {}


def build_pipeline(knowledge_dir: str | Path):
    """
    Build (or retrieve from cache) the checker, retriever, and answerer
    for a given knowledge directory.

    Caching means repeated calls with the same directory are fast —
    the embedding index is built only once per process.
    """
    key = str(Path(knowledge_dir).resolve())
    if key in _pipeline_cache:
        return _pipeline_cache[key]

    from src.config import load_dotenv
    from src.loader import load_all
    from src.embedder import build_index
    from src.retriever import build_retriever
    from src.rules_checker import build_checker
    from src.answerer import build_answerer

    load_dotenv()

    chunks, tone, rules = load_all(Path(knowledge_dir))
    index     = build_index(chunks)
    retriever = build_retriever(index, top_k=3, min_score=0.25)
    checker   = build_checker(rules)
    answerer  = build_answerer(tone)

    pipeline = (checker, retriever, answerer)
    _pipeline_cache[key] = pipeline
    return pipeline


# ---------------------------------------------------------------------------
# Public callable interface
# ---------------------------------------------------------------------------

def answer(
    query: str,
    knowledge_dir: str | Path = "knowledge",
) -> AnswerResult:
    """
    Answer a query from a given knowledge directory.

    Parameters
    ----------
    query         : the user's question
    knowledge_dir : path to a folder containing knowledge.md, tone.md, rules.md

    Returns
    -------
    AnswerResult dict with keys: answer, declined, decline_reason, sources, query
    """
    checker, retriever, answerer = build_pipeline(knowledge_dir)

    # Rules check first
    check = checker.check(query)
    if not check.allowed:
        return AnswerResult(
            answer=check.decline_message,
            declined=True,
            decline_reason=f"{check.rule.id}: matched '{check.matched_signal}'",
            sources=[],
            query=query,
        )

    # Retrieve + answer
    retrieval = retriever.retrieve(query)
    ans = answerer.answer(query, retrieval)

    return AnswerResult(
        answer=ans.text,
        declined=ans.declined,
        decline_reason=ans.decline_reason,
        sources=ans.sources,
        query=query,
    )


# ---------------------------------------------------------------------------
# Smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json, sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    kdir = sys.argv[1] if len(sys.argv) > 1 else "knowledge"

    queries = [
        "How much does Darjeeling First Flush cost?",
        "Does green tea cure diabetes?",
        "What is the weather in Mumbai?",
    ]

    for q in queries:
        print(f"\nQuery : {q}")
        result = answer(q, knowledge_dir=kdir)
        print(json.dumps(result, indent=2))
