"""
Compatibility wrapper for callers that import `src.tool`.

The implementation lives in `src.tools`; this module keeps the documented
single-tool import path working without duplicating pipeline logic.
"""

from src.tools import AnswerResult, answer, build_pipeline

__all__ = ["AnswerResult", "answer", "build_pipeline"]
