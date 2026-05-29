# Leaftide Tea Co. — Knowledge Answering System

A small AI assistant that answers questions about Leaftide Tea Co.
It knows only what you put in the knowledge files — it will not invent facts,
make health claims, or answer questions outside its domain.

---

## What this system does

- Answers questions about Leaftide's teas, prices, brewing, and orders
- Retrieves the most relevant facts from a plain-text knowledge file
- Enforces three strict rules (defined in an editable file, not in code)
- Declines gracefully when a question breaks a rule or falls outside its knowledge

---

## Requirements

- Python 3.10 or newer
- A Groq API key or OpenAI API key
- Internet access for the first run (downloads a small ~90 MB embedding model)

---

## Setup — step by step

### 1. Download or clone the project

```
git clone <your-repo-url>
cd leaftide-qa
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This may take a minute. It installs the OpenAI-compatible SDK and a small local
embedding model. The model itself (~90 MB) downloads on first run.

### 4. Set your LLM provider

Create a file named `.env` in the project root:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk-your-key-here
GROQ_MODEL=llama-3.1-8b-instant
```

To use OpenAI instead, set:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5.4-mini
```

---

## Running the system

### Run the three worked examples (required for the assessment)

```bash
python main.py --examples
```

This runs three back-to-back demonstrations:
1. A straight factual answer (pricing)
2. An answer grounded in retrieved facts (brewing instructions)
3. A correct decline (health claim — Rule 2 fires)

### Start an interactive session

```bash
python main.py
```

Type any question and press Enter. Type `quit` to exit.

### Use a different knowledge directory

```bash
python main.py --knowledge path/to/other/knowledge
```

---

## Editing the knowledge base

All knowledge lives in the `knowledge/` folder. You do not need to touch any code.

### `knowledge/knowledge.md` — the facts

Each line starting with `- ` is one fact the assistant may use.
Add, edit, or delete bullet points freely.

```markdown
- Leaftide Tea Co. was founded in 2018 in Darjeeling, India.
- We currently offer six teas: Darjeeling First Flush, ...
```

**Do not invent facts.** If a fact is not in this file, the assistant will decline
rather than guess.

### `knowledge/tone.md` — the voice

Describes how the assistant should sound. Edit the bullet points under
"Voice" and "Style Rules" to change the personality.

### `knowledge/rules.md` — the limits

Defines what the assistant must never do. Each `## RULE N` block has:

- A plain-English description of the rule
- A `Decline message:` — the exact words shown to the user when the rule fires
- `Trigger signals:` — keywords and phrases that activate the rule

To add a new rule, copy an existing `## RULE N` block, increment the number,
and fill in the three fields. No code changes needed.

---

## Using as a callable tool (Task C)

Another program can call the assistant directly:

```python
from src.tool import answer

result = answer(
    query="How do I brew Jasmine Silver Needle?",
    knowledge_dir="knowledge",    # point to any knowledge folder
)

print(result["answer"])
print(result["declined"])     # True if a rule fired
print(result["sources"])      # which facts were used
```

To support a completely different domain, create a new folder with the same
three files (`knowledge.md`, `tone.md`, `rules.md`) and pass its path.
No code changes are needed.

---

## Project structure

```
leaftide-qa/
│
├── knowledge/              ← edit these freely, no coding needed
│   ├── knowledge.md        ← brand facts (one bullet = one fact)
│   ├── tone.md             ← voice and style guide
│   └── rules.md            ← three "never" rules with decline messages
│
├── src/
│   ├── loader.py           ← reads and parses the knowledge files
│   ├── embedder.py         ← converts facts to vectors for search
│   ├── retriever.py        ← finds the most relevant facts for a query
│   ├── rules_checker.py    ← enforces rules before any LLM call
│   ├── answerer.py         ← builds the prompt and calls the LLM
│   └── tool.py             ← clean callable interface (Task C)
│
├── main.py                 ← run this to start the assistant
├── requirements.txt        ← pip dependencies
├── README.md               ← this file
└── design_notes.md         ← design decisions and trade-offs
```

---

## Troubleshooting

**`GROQ_API_KEY` or `OPENAI_API_KEY` not set**
The system will print a clear error. See Step 4 above.

**Slow on first run**
Normal — the embedding model (~90 MB) is downloading. Subsequent runs are fast.

**"No facts found" error**
Check that every line in `knowledge.md` that contains a fact starts with `- `.

**The assistant declined something it should have answered**
Check `rules.md` — a trigger signal may be too broad. Narrow it or remove it.
