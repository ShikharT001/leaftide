"""
retriever.py
------------
Wraps KnowledgeIndex.search() with a minimum-score threshold and
returns clean RetrievalResult objects ready for the answerer to use.

Design choice: retrieval is kept as a separate module (not folded into
embedder.py) so it can be swapped for a different backend — e.g. a real
vector DB like ChromaDB — without touching any other file.
"""

from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embedder import KnowledgeIndex


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    chunks: list[str]        # retrieved fact strings, best-first
    scores: list[float]      # corresponding cosine similarity scores
    query:  str              # original query (for logging / debugging)

    def as_context(self) -> str:
        """
        Format retrieved chunks as a numbered context block
        ready to be injected into an LLM prompt.
        """
        if not self.chunks:
            return "(No relevant facts retrieved.)"
        lines = [f"{i+1}. {chunk}" for i, chunk in enumerate(self.chunks)]
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return len(self.chunks) == 0


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class Retriever:
    """
    Performs similarity search over a KnowledgeIndex.

    Parameters
    ----------
    index         : a built KnowledgeIndex
    top_k         : maximum number of chunks to return (default 3)
    min_score     : chunks with cosine similarity below this are dropped (default 0.25)
                    Keeps retrieval honest — low scores mean the query has
                    no real match in the knowledge base.
    """

    def __init__(
        self,
        index: KnowledgeIndex,
        top_k: int = 3,
        min_score: float = 0.25,
    ):
        self.index = index
        self.top_k = top_k
        self.min_score = min_score

    def retrieve(self, query: str) -> RetrievalResult:
        """
        Search the index and return a RetrievalResult.
        Chunks below min_score are filtered out.
        """
        raw = self.index.search(query, top_k=self.top_k)

        chunks, scores = [], []
        for chunk, score in raw:
            if score >= self.min_score:
                chunks.append(chunk)
                scores.append(score)

        return RetrievalResult(chunks=chunks, scores=scores, query=query)


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def build_retriever(
    index: KnowledgeIndex,
    top_k: int = 3,
    min_score: float = 0.25,
) -> Retriever:
    return Retriever(index, top_k=top_k, min_score=min_score)


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from src.loader import load_chunks
    from src.embedder import build_index

    kdir = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
    chunks = load_chunks(Path(kdir) / "knowledge.md")
    index = build_index(chunks)
    retriever = build_retriever(index)

    queries = [
        "What teas do you sell?",
        "How much does Darjeeling First Flush cost?",
        "How do I brew white tea?",
        "Do you ship internationally?",
    ]

    for q in queries:
        result = retriever.retrieve(q)
        print(f"\nQuery : {q}")
        if result.is_empty():
            print("  (no relevant chunks above threshold)")
        else:
            for chunk, score in zip(result.chunks, result.scores):
                print(f"  [{score:.3f}] {chunk}")
