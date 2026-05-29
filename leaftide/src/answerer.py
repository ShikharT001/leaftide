"""
answerer.py
-----------
Assembles the final prompt from tone + retrieved facts + query,
calls the configured LLM provider, and returns a structured Answer.

Design decisions:
  1. The system prompt is built entirely from editable files (tone.md +
     knowledge chunks). No personality or rules are hardcoded here.
  2. Rule 1 (no invented facts) has a second enforcement line here:
     if retrieval returns nothing relevant, the answerer declines rather
     than letting the LLM hallucinate.
  3. The LLM is explicitly told what it may and may not say via the
     system prompt; grounding is enforced by instruction, not just hope.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from openai import OpenAI, OpenAIError

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

if TYPE_CHECKING:
    from src.retriever import RetrievalResult

from src.config import (
    get_groq_api_key,
    get_groq_model,
    get_llm_provider,
    get_openai_api_key,
    get_openai_model,
)


GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# ---------------------------------------------------------------------------
# Answer type
# ---------------------------------------------------------------------------

@dataclass
class Answer:
    text: str                        # the response shown to the user
    declined: bool = False           # True if a rule or empty retrieval fired
    decline_reason: str = ""         # human-readable reason (for logging)
    sources: list[str] = field(default_factory=list)  # chunks used as context
    query: str = ""

    def display(self) -> str:
        """Pretty-print for the CLI."""
        if self.declined:
            return (
                f"[DECLINED] {self.decline_reason}\n\n"
                f"{self.text}"
            )
        if self.sources:
            source_block = "\n".join(f"  - {s}" for s in self.sources)
            return f"{self.text}\n\n[Sources used]\n{source_block}"
        return self.text


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATE = """\
You are the customer assistant for Leaftide Tea Co., a small Indian artisan tea brand.

TONE AND STYLE
--------------
{tone}

STRICT RULES - YOU MUST FOLLOW THESE WITHOUT EXCEPTION
------------------------------------------------------
1. Answer ONLY using the facts provided in the KNOWLEDGE section below.
   Do not invent, assume, or extrapolate any information not explicitly stated there.
2. If the KNOWLEDGE section does not contain enough information to answer the question,
   say exactly: "I don't have that information in our knowledge base - for the most
   accurate answer, please reach out to us at hello@leaftide.in."
3. Do not make health, medicinal, or therapeutic claims about any tea or ingredient.
4. Do not answer questions unrelated to Leaftide's products, brewing, pricing, or orders.
5. Do not use bullet points. Write in warm, natural prose sentences.
6. Keep your answer to two to four sentences unless brewing instructions require more.

KNOWLEDGE (retrieved facts - use only these)
--------------------------------------------
{context}
"""


def _build_system_prompt(tone: str, context: str) -> str:
    return _SYSTEM_TEMPLATE.format(tone=tone.strip(), context=context.strip())


def _response_text(response: Any) -> str:
    """
    Extract text from OpenAI SDK response objects.

    Newer SDKs expose `output_text`; the fallback keeps this usable if the
    response object shape changes slightly across SDK versions.
    """
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))

    return "\n".join(parts).strip()


def _chat_response_text(response: Any) -> str:
    if not getattr(response, "choices", None):
        return ""

    message = getattr(response.choices[0], "message", None)
    content = getattr(message, "content", None)
    return str(content).strip() if content else ""


# ---------------------------------------------------------------------------
# Answerer
# ---------------------------------------------------------------------------

class Answerer:
    """
    Calls the configured LLM provider with a grounded, rules-bound prompt.

    Parameters
    ----------
    tone        : full tone guide string from tone.md
    model       : model ID for the configured provider
    max_tokens  : max output tokens for the response
    provider    : "openai" or "groq"
    """

    def __init__(
        self,
        tone: str,
        model: str | None = None,
        max_tokens: int = 300,
        provider: str | None = None,
    ):
        self.tone = tone
        self.max_tokens = max_tokens
        self.provider = (provider or get_llm_provider()).strip().lower()
        self.model = model or self._default_model()
        self._client = self._build_client()

    def _default_model(self) -> str:
        if self.provider == "groq":
            return get_groq_model()
        return get_openai_model()

    def _build_client(self) -> OpenAI:
        if self.provider == "groq":
            return OpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
        if self.provider == "openai":
            return OpenAI(api_key=get_openai_api_key())
        raise ValueError("Unsupported LLM_PROVIDER. Use 'openai' or 'groq'.")

    def answer(self, query: str, retrieval: RetrievalResult) -> Answer:
        """
        Generate an answer grounded in retrieved facts.

        Second-line Rule 1 enforcement: if retrieval is empty (no relevant
        facts found above threshold), decline rather than call the LLM.
        """
        if retrieval.is_empty():
            print("[ANSWERER] No relevant chunks retrieved - declining (Rule 1 second line).")
            decline_text = (
                "I don't have that information in our knowledge base - "
                "for the most accurate answer, please reach out to us at hello@leaftide.in."
            )
            return Answer(
                text=decline_text,
                declined=True,
                decline_reason="No relevant facts in knowledge base (Rule 1)",
                sources=[],
                query=query,
            )

        context = retrieval.as_context()
        system_prompt = _build_system_prompt(self.tone, context)

        print(
            f"[ANSWERER] Calling {self.provider}:{self.model} "
            f"with {len(retrieval.chunks)} retrieved chunk(s)..."
        )

        try:
            response_text = self._call_model(system_prompt, query)
        except OpenAIError as exc:
            raise RuntimeError(
                f"{self.provider.title()} request failed. Check your API key, "
                "model access, quota, and provider dashboard settings."
            ) from exc

        if not response_text:
            raise RuntimeError(f"{self.provider.title()} response did not contain any text output.")

        return Answer(
            text=response_text,
            declined=False,
            sources=retrieval.chunks,
            query=query,
        )

    def _call_model(self, system_prompt: str, query: str) -> str:
        if self.provider == "groq":
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                max_tokens=self.max_tokens,
            )
            return _chat_response_text(response)

        response = self._client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=query,
            max_output_tokens=self.max_tokens,
        )
        return _response_text(response)


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def build_answerer(tone: str, **kwargs) -> Answerer:
    return Answerer(tone, **kwargs)


# ---------------------------------------------------------------------------
# Quick smoke-test (requires provider API key in environment)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from src.loader import load_all
    from src.embedder import build_index
    from src.retriever import build_retriever

    kdir = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
    chunks, tone, rules = load_all(kdir)
    index = build_index(chunks)
    retriever = build_retriever(index)
    answerer = build_answerer(tone)

    queries = [
        "What teas do you sell?",
        "How do I brew Jasmine Silver Needle?",
    ]

    for q in queries:
        print(f"\n{'='*55}")
        print(f"Query: {q}")
        print("=" * 55)
        retrieval = retriever.retrieve(q)
        answer = answerer.answer(q, retrieval)
        print(answer.display())
