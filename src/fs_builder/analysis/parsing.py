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
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AnalysisOutputParseError(f"分析模型返回的内容不是有效 JSON：{exc}") from exc
    return _normalize_analysis_payload(parsed)


def extract_response_content(response: object) -> str:
    if isinstance(response, str):
        stripped = response.lstrip()
        if stripped.startswith("data:"):
            return _extract_sse_content(response)
        extracted = _extract_completion_payload_content(_try_parse_json(response))
        if extracted:
            return extracted
        return response

    if isinstance(response, Mapping):
        extracted = _extract_completion_payload_content(response)
        if extracted:
            return extracted
        return ""

    choices = getattr(response, "choices", None)
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        extracted = _extract_object_choice_content(first_choice)
        if extracted:
            return extracted

    extracted = _coerce_text_content(getattr(response, "content", None))
    if extracted:
        return extracted

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
        content = _coerce_text_content(message.get("content"))
        if content:
            return content

    delta = choice.get("delta")
    if isinstance(delta, Mapping):
        content = _coerce_text_content(delta.get("content"))
        if content:
            return content

    text = _coerce_text_content(choice.get("text"))
    if text:
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


def _normalize_analysis_payload(payload: object) -> object:
    """兼容供应商返回完整 completion envelope 的情况。"""
    extracted = _extract_completion_payload_content(payload)
    if not extracted:
        return payload

    normalized = strip_markdown_fences(extracted.strip())
    if not normalized:
        raise AnalysisOutputParseError("分析模型返回了 completion 响应，但 content 为空。")

    try:
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise AnalysisOutputParseError(f"分析模型的 message.content 不是有效 JSON：{exc}") from exc


def _extract_completion_payload_content(payload: object) -> str:
    if not isinstance(payload, Mapping):
        return ""

    raw_choices = payload.get("choices")
    if isinstance(raw_choices, list) and raw_choices:
        first_choice = raw_choices[0]
        if isinstance(first_choice, Mapping):
            return extract_choice_content(first_choice)

    return _coerce_text_content(payload.get("content"))


def _extract_object_choice_content(choice: object) -> str:
    message = getattr(choice, "message", None)
    content = _coerce_text_content(getattr(message, "content", None))
    if content:
        return content

    delta = getattr(choice, "delta", None)
    content = _coerce_text_content(getattr(delta, "content", None))
    if content:
        return content

    return _coerce_text_content(getattr(choice, "text", None))


def _coerce_text_content(value: object) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    return ""


def _try_parse_json(raw_content: str) -> object | None:
    stripped = raw_content.lstrip()
    if not stripped.startswith(("{", "[")):
        return None

    try:
        return cast(object, json.loads(raw_content))
    except json.JSONDecodeError:
        return None
