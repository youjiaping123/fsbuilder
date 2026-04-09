"""兼容层：分析逻辑已迁移到 `fs_builder.analysis`。"""

from __future__ import annotations

from .analysis import RequirementAnalyzer, analyze_requirement
from .analysis.fallbacks import match_demo_fallback
from .analysis.parsing import (
    _extract_sse_content as _extract_sse_content_impl,
)
from .analysis.parsing import (
    extract_choice_content,
    extract_response_content,
    extract_stream_content,
    token_attempts,
)
from .analysis.provider import request_analysis_content

__all__ = [
    "RequirementAnalyzer",
    "analyze_requirement",
]


def _build_local_fallback_plan(requirement: str):
    return match_demo_fallback(requirement)


def _token_attempts(initial_max_tokens: int):
    return token_attempts(initial_max_tokens)


def _extract_response_content(response: object):
    return extract_response_content(response)


def _extract_stream_content(response: object):
    return extract_stream_content(response)


def _extract_choice_content(choice: dict[str, object]):
    return extract_choice_content(choice)


def _request_analysis_content(**kwargs):
    return request_analysis_content(**kwargs)


def _extract_sse_content(raw_response: str):
    return _extract_sse_content_impl(raw_response)
