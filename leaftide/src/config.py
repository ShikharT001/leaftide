"""
config.py
---------
Small environment loader for local development.

The app accepts normal environment variables first, then fills in missing
values from a `.env` file in the project root. This keeps production behavior
simple while making Windows local setup painless.
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip().lstrip("\ufeff")
    if not line or line.startswith("#") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")

    if not key:
        return None
    return key, value


def load_dotenv(path: str | Path | None = None) -> None:
    """
    Load missing environment variables from a `.env` file.

    Existing OS-level variables are left untouched, so deployment settings or
    shell-provided values always win over local file values.
    """
    candidates = [Path(path)] if path else [Path.cwd() / ".env", PROJECT_ROOT / ".env"]
    seen: set[Path] = set()

    for candidate in candidates:
        env_path = candidate.resolve()
        if env_path in seen or not env_path.exists():
            continue
        seen.add(env_path)

        for line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)


def get_openai_api_key() -> str | None:
    load_dotenv()
    return os.environ.get("OPENAI_API_KEY")


def get_openai_model(default: str = "gpt-5.4-mini") -> str:
    load_dotenv()
    return os.environ.get("OPENAI_MODEL", default)


def get_llm_provider(default: str = "openai") -> str:
    load_dotenv()
    provider = os.environ.get("LLM_PROVIDER")
    if provider:
        return provider.strip().lower()

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if os.environ.get("GROQ_API_KEY") or openai_key.startswith("gsk_"):
        return "groq"
    return default


def get_groq_api_key() -> str | None:
    load_dotenv()
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        return groq_key

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key.startswith("gsk_"):
        return openai_key
    return None


def get_groq_model(default: str = "llama-3.1-8b-instant") -> str:
    load_dotenv()
    return os.environ.get("GROQ_MODEL", default)
