"""
loader.py
---------
Reads the three knowledge files and returns:
  - chunks : list of individual fact strings (from knowledge.md)
  - tone   : full tone guide as a single string (for the system prompt)
  - rules  : list of parsed Rule objects (for the rules checker)
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    id: str                        # e.g. "RULE 1"
    title: str                     # e.g. "No invented facts"
    description: str               # full plain-English description
    decline_message: str           # the exact message to show the user
    trigger_signals: list[str]     # keywords / phrases to match against


# ---------------------------------------------------------------------------
# Knowledge chunks
# ---------------------------------------------------------------------------

def load_chunks(knowledge_path: Path) -> list[str]:
    """
    Parse knowledge.md and return one chunk per bullet point.
    Blank lines, headings, and HTML comments are ignored.
    Each chunk is a clean, standalone sentence.
    """
    text = knowledge_path.read_text(encoding="utf-8")
    chunks = []

    for line in text.splitlines():
        line = line.strip()
        # Keep only bullet lines (start with "- ")
        if line.startswith("- "):
            fact = line[2:].strip()
            if fact:
                chunks.append(fact)

    if not chunks:
        raise ValueError(f"No facts found in {knowledge_path}. "
                         "Check that each fact starts with '- '.")
    return chunks


# ---------------------------------------------------------------------------
# Tone guide
# ---------------------------------------------------------------------------

def load_tone(tone_path: Path) -> str:
    """
    Return the full tone.md content as a single string,
    stripping HTML comments and blank section headers for cleanliness.
    """
    text = tone_path.read_text(encoding="utf-8")

    # Remove HTML comments (<!-- ... -->)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Remove markdown headings (keep the body text)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue          # drop heading lines
        if stripped == "":
            continue          # drop blank lines
        lines.append(stripped)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def load_rules(rules_path: Path) -> list[Rule]:
    """
    Parse rules.md and return a list of Rule objects.

    Expected format per rule block:
        ## RULE N — Title
        **Never ...**
        <description paragraphs>
        Decline message: "..."
        Trigger signals:
        - word or phrase
        - ...
    """
    text = rules_path.read_text(encoding="utf-8")
    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    rules: list[Rule] = []

    # Split on rule headings  ## RULE N ...
    blocks = re.split(r"(?m)^## (RULE \d+.*?)$", text)
    # blocks = [preamble, "RULE 1 — ...", body1, "RULE 2 — ...", body2, ...]

    it = iter(blocks)
    next(it)   # skip preamble

    for header in it:
        body = next(it, "")

        # Rule id and title from header e.g. "RULE 1 — No invented facts"
        m = re.match(r"(RULE \d+)\s*[—-]\s*(.+)", header.strip())
        if not m:
            continue
        rule_id = m.group(1).strip()
        title = m.group(2).strip()

        # Decline message
        dm_match = re.search(
            r'Decline message:\s*["\u201c](.+?)["\u201d]',
            body, re.DOTALL
        )
        decline_message = dm_match.group(1).strip() if dm_match else ""

        # Description: everything between the **Never...** line and "Decline message:"
        desc_match = re.search(
            r"\*\*Never .+?\*\*\s*\n(.*?)Decline message:",
            body, re.DOTALL
        )
        description = desc_match.group(1).strip() if desc_match else ""

        # Trigger signals: bullet lines after "Trigger signals:"
        triggers: list[str] = []
        trigger_section = re.search(
            r"Trigger signals:\s*\n(.*?)(?=\n---|\Z)",
            body, re.DOTALL
        )
        if trigger_section:
            for line in trigger_section.group(1).splitlines():
                line = line.strip().lstrip("-").strip()
                if line:
                    # split comma-separated entries on the same line
                    for part in line.split(","):
                        part = part.strip()
                        if part:
                            triggers.append(part.lower())

        rules.append(Rule(
            id=rule_id,
            title=title,
            description=description,
            decline_message=decline_message,
            trigger_signals=triggers,
        ))

    if not rules:
        raise ValueError(f"No rules found in {rules_path}. "
                         "Check that each rule starts with '## RULE N — Title'.")
    return rules


# ---------------------------------------------------------------------------
# Convenience: load everything at once
# ---------------------------------------------------------------------------

def load_all(knowledge_dir: str | Path) -> tuple[list[str], str, list[Rule]]:
    """
    Load chunks, tone, and rules from a knowledge directory.
    Returns (chunks, tone_text, rules).
    """
    base = Path(knowledge_dir)
    chunks = load_chunks(base / "knowledge.md")
    tone   = load_tone(base / "tone.md")
    rules  = load_rules(base / "rules.md")
    return chunks, tone, rules


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    kdir = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
    chunks, tone, rules = load_all(kdir)

    print(f"\n=== Chunks ({len(chunks)}) ===")
    for i, c in enumerate(chunks, 1):
        print(f"  {i:02d}. {c}")

    print(f"\n=== Tone (first 200 chars) ===")
    print(" ", tone[:200])

    print(f"\n=== Rules ({len(rules)}) ===")
    for r in rules:
        print(f"  [{r.id}] {r.title}")
        print(f"       Decline: {r.decline_message[:60]}...")
        print(f"       Triggers ({len(r.trigger_signals)}): "
              f"{r.trigger_signals[:4]} ...")
