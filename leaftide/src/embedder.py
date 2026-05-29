"""
embedder.py
-----------
Embeds knowledge chunks using a local sentence-transformers model
and stores them as a numpy matrix for fast cosine similarity search.

No external vector database is required — everything lives in memory.
The index is rebuilt each run (fast enough for ≤200 facts).
"""

from __future__ import annotations
import numpy as np
from pathlib import Path

# sentence-transformers is a lightweight local embedding model.
# It downloads ~90 MB on first use and runs fully offline after that.
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Model — one shared instance per process
# ---------------------------------------------------------------------------

_MODEL_NAME = "all-MiniLM-L6-v2"   # fast, small, good quality for retrieval
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[embedder] Loading model '{_MODEL_NAME}' (one-time download ~90 MB)...")
        _model = SentenceTransformer(_MODEL_NAME)
        print("[embedder] Model ready.")
    return _model


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

class KnowledgeIndex:
    """
    Holds the embedded knowledge base and exposes a search method.

    Attributes
    ----------
    chunks      : original text of each fact
    embeddings  : (N, D) float32 matrix, L2-normalised
    """

    def __init__(self, chunks: list[str]):
        if not chunks:
            raise ValueError("Cannot build an index from an empty chunk list.")

        model = _get_model()
        print(f"[embedder] Embedding {len(chunks)} chunks...")
        raw = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)

        # L2-normalise so dot product == cosine similarity
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)   # avoid division by zero

        self.chunks: list[str] = chunks
        self.embeddings: np.ndarray = (raw / norms).astype(np.float32)
        print(f"[embedder] Index built — {len(chunks)} facts, "
              f"embedding dim {self.embeddings.shape[1]}.")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """
        Return the top_k most relevant chunks for a query.

        Returns
        -------
        List of (chunk_text, similarity_score) tuples, highest score first.
        Score is cosine similarity in [−1, 1]; typical good matches are > 0.4.
        """
        model = _get_model()
        q_vec = model.encode([query], convert_to_numpy=True)[0]
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        scores: np.ndarray = self.embeddings @ q_vec.astype(np.float32)

        # Pick top_k indices (unsorted then sort)
        top_k = min(top_k, len(self.chunks))
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [(self.chunks[i], float(scores[i])) for i in top_indices]


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def build_index(chunks: list[str]) -> KnowledgeIndex:
    """Build and return a KnowledgeIndex from a list of fact strings."""
    return KnowledgeIndex(chunks)


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.loader import load_chunks

    kdir = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
    chunks = load_chunks(Path(kdir) / "knowledge.md")
    index = build_index(chunks)

    test_queries = [
        "What teas do you sell?",
        "How much does Darjeeling cost?",
        "How do I brew white tea?",
    ]

    for q in test_queries:
        print(f"\nQuery: {q}")
        results = index.search(q, top_k=3)
        for chunk, score in results:
            print(f"  [{score:.3f}] {chunk}")
