# Design Notes

## Three Biggest Design Decisions

---

### 1. Rules live entirely in `rules.md` — none are hardcoded

The most important structural choice was ensuring that every rule — its trigger
signals, its decline message, and its description — lives in an editable markdown
file rather than in Python code.

The `rules_checker.py` file reads `rules.md` at startup and builds its matching
logic from what it finds there. A non-technical editor can open `rules.md`, change
a decline message, add a trigger keyword, or add a fourth `## RULE 4` block, and
the system will pick it up on next run with zero code changes.

The alternative — hardcoding rule strings inside `rules_checker.py` — would have
been faster to write but would have coupled content decisions to code. Every time
a product manager wanted to soften a decline message or add a new restricted topic,
they would need a developer. Keeping rules in a file removes that dependency
entirely, which is also what the brief explicitly asked for.

The trade-off: the current rule-matching is keyword and regex based. A hardcoded
rules layer could use more sophisticated per-rule logic, but it would be harder
for a non-coder to inspect or trust.

---

### 2. Two-stage Rule 1 enforcement (rules checker + empty-retrieval check)

Rule 1 — "never invent a fact" — is enforced in two places deliberately.

The rules checker fires first and catches the most obvious signals: questions
about future plans, upcoming launches, subscriptions. These are structurally
out-of-scope regardless of what the knowledge base contains.

The second line of enforcement is in `answerer.py`: if the retrieval step returns
zero chunks above the similarity threshold, the answerer declines immediately
without calling the LLM. This catches the long tail — any question where the
knowledge base has nothing relevant, even if the query doesn't match obvious
Rule 1 keywords.

Without the second line, a question like "What is your return policy on opened
tins?" (not in the knowledge base) would pass the rules checker and reach the
LLM with an empty context block, giving the model a chance to hallucinate an
answer. The empty-retrieval check closes that gap.

The threshold (`min_score=0.25`) was chosen conservatively. A lower value risks
passing irrelevant chunks to the LLM; a higher value risks declining answerable
questions. With 24 facts and a well-scoped knowledge base, 0.25 proved to be
the right balance in testing.

---

### 3. Local embeddings over an API-based embedding service

The embedding model (`all-MiniLM-L6-v2` via `sentence-transformers`) runs
entirely on the local machine. No embedding API calls are made, which means:

- No second API key to manage
- No network latency on embedding queries
- No cost per embedding call
- The index rebuilds in under a second for 24 facts

The trade-off is a one-time ~90 MB download and a dependency on `torch`. For
a 20-fact knowledge base this is clearly the right call. At scale (tens of
thousands of facts), the calculus would change: a hosted embedding API plus a
persistent vector store like Pinecone or Weaviate would be more practical because
you would not want to rebuild the index on every process start.

For this assessment the local approach also makes the project easier for an
evaluator to run — one `pip install` and it works offline, with no second
service to configure.

---

## What I Would Change with More Time

**Persistent index** — currently the embedding index is rebuilt from scratch on
every run. For 24 facts this takes under a second, but storing the index to disk
(`numpy.save`) and only rebuilding when `knowledge.md` changes would make the
system production-ready without much effort.

**Semantic rule matching** — the current rules checker uses keyword and regex
matching, which is fast but brittle. A paraphrase like "will chamomile fix my
insomnia?" passes Rule 2 today because "fix" and "insomnia" are not in the
trigger list. Adding a small semantic similarity check against each rule's
description (using the same embedding model already in use) would close that
gap robustly.

**Rule 1 post-answer grounding check** — even with the empty-retrieval check,
the LLM could in principle ignore the "use only these facts" instruction for
a subtle out-of-scope question. A lightweight post-generation check — comparing
the answer against the retrieved chunks for factual overlap — would add a third
line of Rule 1 defence.

**Structured logging** — the current `print()` statements give visibility during
development and screen recording, but a proper logging setup (structured JSON
logs, log levels, request IDs) would be the right foundation for any production
deployment.

**Tests** — the smoke-tests in each module cover the happy path and obvious
decline cases. A proper test suite with `pytest` and mocked API calls would
give confidence that rule changes in `rules.md` do not silently break existing
behaviour.