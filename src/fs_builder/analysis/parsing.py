"""分析模型输出解析。"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, cast

from ..io.resources import strip_markdown_fences
from .errors import AnalysisOutputParseError


def token_attempts(initial_max_tokens: int) -> list[int]:
    """优先保留用户配置，再回退到兼容性更好的 token 档位。"""
    attempts: list[int] = []
    for candidate in (initial_max_tokens, 2048, 1024):
        if candidate > 0 and candidate not in attempts:
            attempts.append(candidate)
    return attempts


def parse_analysis_payload(content: str) -> object:
    cleaned = strip_markdown_fences(content.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AnalysisOutputParseError(f"分析模型返回的内容不是有效 JSON：{exc}") from exc


def extract_response_content(response: object) -> str:
    if isinstance(response, str):
        if response.lstrip().startswith("data:"):
            return _extract_sse_content(response)
        return response

    if isinstance(response, Mapping):
        raw_choices = response.get("choices")
        if isinstance(raw_choices, list) and raw_choices:
            first_choice = raw_choices[0]
            if isinstance(first_choice, Mapping):
                extracted = extract_choice_content(first_choice)
                if extracted:
                    return extracted
        raw_content = response.get("content")
        if isinstance(raw_content, str):
            return raw_content
        return ""

    choices = getattr(response, "choices", None)
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        raw_content = getattr(message, "content", None)
        if isinstance(raw_content, str):
            return raw_content

    return ""


def extract_stream_content(response: object) -> str:
    if isinstance(response, (str, Mapping)):
        return extract_response_content(response)

    if not hasattr(response, "__iter__"):
        return extract_response_content(response)
    iterator = iter(cast(Iterable[object], response))

    content_parts: list[str] = []
    for chunk in iterator:
        content = extract_response_content(chunk)
        if content:
            content_parts.append(content)
    return "".join(content_parts)


def extract_choice_content(choice: Mapping[str, Any]) -> str:
    message = choice.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if isinstance(content, str):
            return content

    delta = choice.get("delta")
    if isinstance(delta, Mapping):
        content = delta.get("content")
        if isinstance(content, str):
            return content

    text = choice.get("text")
    if isinstance(text, str):
        return text

    return ""


def _extract_sse_content(raw_response: str) -> str:
    content_parts: list[str] = []
    for line in raw_response.splitlines():
        stripped = line.strip()
        if not stripped.startswith("data:"):
            continue
        payload = stripped[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        content = extract_response_content(decoded)
        if content:
            content_parts.append(content)
    return "".join(content_parts)
