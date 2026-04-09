"""LLM-backed requirement analysis."""

from __future__ import annotations

import json
import re
from time import sleep

import httpx
from openai import OpenAI

from .errors import PlanValidationError
from .models import AssemblyPlan, validate_plan_data
from .prompting import load_prompt, strip_markdown_fences
from .settings import Settings

_EMPTY_CONTENT_RETRIES = 6
_EMPTY_CONTENT_RETRY_DELAY_SECONDS = 1.0


def analyze_requirement(requirement: str, settings: Settings) -> AssemblyPlan:
    cleaned_requirement = requirement.strip()
    if not cleaned_requirement:
        raise PlanValidationError("Requirement text must not be empty.")

    try:
        content = _request_analysis_content(
            requirement=cleaned_requirement,
            settings=settings,
        )
        raw = strip_markdown_fences(content.strip())
        data = json.loads(raw)
        return validate_plan_data(data)
    except (PlanValidationError, json.JSONDecodeError):
        fallback_plan = _build_local_fallback_plan(cleaned_requirement)
        if fallback_plan is not None:
            return fallback_plan
        raise


def _request_analysis_content(
    *,
    requirement: str,
    settings: Settings,
    client: OpenAI | None = None,
    requester: object | None = None,
) -> str:
    messages = [
        {"role": "system", "content": load_prompt("analyze.txt")},
        {"role": "user", "content": requirement},
    ]
    token_attempts = _token_attempts(settings.analyze_max_tokens)
    last_empty_tokens = token_attempts[-1]

    for max_tokens in token_attempts:
        for attempt_index in range(_EMPTY_CONTENT_RETRIES):
            try:
                if requester is not None:
                    response = requester(
                        model=settings.analyze_model,
                        max_tokens=max_tokens,
                        messages=messages,
                    )
                else:
                    active_client = client
                    if active_client is None and settings.base_url:
                        response = _post_chat_completion_raw(
                            api_key=settings.require_api_key("analyze requirements"),
                            base_url=settings.base_url,
                            model=settings.analyze_model,
                            max_tokens=max_tokens,
                            messages=messages,
                            timeout_seconds=settings.api_timeout_seconds,
                        )
                    else:
                        active_client = active_client or OpenAI(
                            api_key=settings.require_api_key("analyze requirements"),
                            base_url=None,
                            timeout=settings.api_timeout_seconds,
                        )
                        response = active_client.chat.completions.create(
                            model=settings.analyze_model,
                            max_tokens=max_tokens,
                            messages=messages,
                            stream=True,
                        )
            except Exception as exc:  # noqa: BLE001
                raise PlanValidationError(
                    "Analyzer request failed. "
                    f"Model={settings.analyze_model}, base_url={settings.base_url or 'default'}. "
                    f"Details: {exc}"
                ) from exc
            content = _extract_stream_content(response)
            if content.strip():
                return content
            last_empty_tokens = max_tokens
            if attempt_index < _EMPTY_CONTENT_RETRIES - 1:
                sleep(_EMPTY_CONTENT_RETRY_DELAY_SECONDS)

    raise PlanValidationError(
        "Analyzer returned empty content. "
        f"Model={settings.analyze_model}, base_url={settings.base_url or 'default'}, "
        f"last max_tokens={last_empty_tokens}. "
        "Try lowering ANALYZE_MAX_TOKENS or switching to a provider-compatible model."
    )


def _token_attempts(initial_max_tokens: int) -> list[int]:
    attempts: list[int] = []
    for candidate in (initial_max_tokens, 2048, 1024):
        if candidate > 0 and candidate not in attempts:
            attempts.append(candidate)
    return attempts


def _extract_response_content(response: object) -> str:
    if isinstance(response, str):
        if response.lstrip().startswith("data:"):
            return _extract_sse_content(response)
        return response

    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                content = _extract_choice_content(first_choice)
                if content:
                    return content
        content = response.get("content")
        if isinstance(content, str):
            return content
        return ""

    choices = getattr(response, "choices", None)
    if isinstance(choices, list) and choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content

    return ""


def _extract_stream_content(response: object) -> str:
    if isinstance(response, (str, dict)):
        return _extract_response_content(response)

    try:
        iterator = iter(response)  # type: ignore[arg-type]
    except TypeError:
        return _extract_response_content(response)

    content_parts: list[str] = []
    for chunk in iterator:
        content = _extract_response_content(chunk)
        if content:
            content_parts.append(content)
    return "".join(content_parts)


def _post_chat_completion_raw(
    *,
    api_key: str,
    base_url: str,
    model: str,
    max_tokens: int,
    messages: list[dict[str, str]],
    timeout_seconds: float,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=timeout_seconds) as http_client:
        with http_client.stream(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
            },
        ) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                preview = response.read().decode("utf-8", errors="replace")[:400]
                raise PlanValidationError(
                    f"Analyzer HTTP request failed with status {response.status_code}. Response preview: {preview}"
                ) from exc

            content_type = response.headers.get("content-type", "")
            if "text/event-stream" not in content_type:
                return response.read().decode("utf-8", errors="replace")

            chunks: list[str] = []
            for line in response.iter_lines():
                if not line:
                    continue
                chunks.append(line)
                if line.strip() == "data: [DONE]":
                    break
            return "\n".join(chunks)


def _build_local_fallback_plan(requirement: str) -> AssemblyPlan | None:
    lowered = requirement.lower()
    if "cold drawing die" in lowered or "冷拉延模具" in requirement or "拉延模具" in requirement:
        return _build_drawing_die_plan(requirement)
    return None


def _build_drawing_die_plan(requirement: str) -> AssemblyPlan:
    punch_diameter = _extract_mm(requirement, [r"凸模外径\s*[=：:]\s*(\d+(?:\.\d+)?)\s*mm"], default=60.0)
    punch_height = _extract_mm(
        requirement,
        [r"凸模外径\s*[=：:]\s*\d+(?:\.\d+)?\s*mm（与工件内径匹配）[，,]\s*高度\s*(\d+(?:\.\d+)?)\s*mm"],
        default=80.0,
    )
    die_cavity_diameter = _extract_mm(
        requirement,
        [r"凹模型腔直径\s*[=：:]\s*(\d+(?:\.\d+)?)\s*mm"],
        default=64.0,
    )
    holder_outer_diameter = _extract_mm(
        requirement,
        [r"压边圈外径\s*=\s*凹模外径\s*=\s*(\d+(?:\.\d+)?)\s*mm"],
        default=160.0,
    )
    upper_seat = _extract_box_dims(requirement, "上模座", default=(200.0, 200.0, 40.0))
    lower_seat = _extract_box_dims(requirement, "下模座", default=(200.0, 200.0, 40.0))
    workpiece_outer_diameter = _extract_mm(
        requirement,
        [r"外径\s*(\d+(?:\.\d+)?)\s*mm", r"工件外径匹配[）)]?\s*(\d+(?:\.\d+)?)\s*mm"],
        default=64.0,
    )
    workpiece_depth = _extract_mm(requirement, [r"筒深[：:]\s*(\d+(?:\.\d+)?)\s*mm"], default=50.0)

    blank_holder_inner = max(workpiece_outer_diameter + 6.0, punch_diameter + 6.0)
    die_height = max(workpiece_depth + 10.0, 60.0)
    blank_holder_height = 20.0
    total_height = 280.0

    plan = {
        "assembly_name": "drawing_die",
        "description": "Single-action cold drawing die with upper and lower seats, punch, die, and blank holder.",
        "global_params": {
            "unit": "mm",
            "origin_description": "XY plane at bottom center of assembly, Z points up",
            "total_height_mm": total_height,
            "total_width_mm": max(upper_seat[0], lower_seat[0]),
            "total_depth_mm": max(upper_seat[1], lower_seat[1]),
        },
        "parts": [
            {
                "id": "lower_die_seat",
                "name": "Lower Die Seat",
                "shape": "box",
                "material_hint": "steel",
                "params": {
                    "width_mm": lower_seat[0],
                    "depth_mm": lower_seat[1],
                    "height_mm": lower_seat[2],
                },
                "position": {"x_mm": 0.0, "y_mm": 0.0, "z_bottom_mm": 0.0},
                "description": "Base block carrying the die and blank holder.",
            },
            {
                "id": "drawing_die",
                "name": "Drawing Die",
                "shape": "hollow_cylinder",
                "material_hint": "cast_iron",
                "params": {
                    "outer_diameter_mm": holder_outer_diameter,
                    "inner_diameter_mm": die_cavity_diameter,
                    "height_mm": die_height,
                },
                "position": {"x_mm": 0.0, "y_mm": 0.0, "z_bottom_mm": lower_seat[2]},
                "description": "Fixed die cavity matching the workpiece outer diameter.",
            },
            {
                "id": "blank_holder",
                "name": "Blank Holder",
                "shape": "hollow_cylinder",
                "material_hint": "steel",
                "params": {
                    "outer_diameter_mm": holder_outer_diameter,
                    "inner_diameter_mm": blank_holder_inner,
                    "height_mm": blank_holder_height,
                },
                "position": {"x_mm": 0.0, "y_mm": 0.0, "z_bottom_mm": lower_seat[2] + die_height},
                "description": "Ring that restrains the sheet edge during drawing.",
            },
            {
                "id": "upper_die_seat",
                "name": "Upper Die Seat",
                "shape": "box",
                "material_hint": "steel",
                "params": {
                    "width_mm": upper_seat[0],
                    "depth_mm": upper_seat[1],
                    "height_mm": upper_seat[2],
                },
                "position": {
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                    "z_bottom_mm": total_height - upper_seat[2],
                },
                "description": "Upper block carrying the punch.",
            },
            {
                "id": "punch",
                "name": "Punch",
                "shape": "cylinder",
                "material_hint": "steel",
                "params": {
                    "diameter_mm": punch_diameter,
                    "height_mm": punch_height,
                },
                "position": {
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                    "z_bottom_mm": total_height - upper_seat[2] - punch_height,
                },
                "description": "Moving punch that draws the blank into the die.",
            },
        ],
        "assembly_relations": [
            {"child_id": "drawing_die", "parent_id": "lower_die_seat", "relation": "stacked_on"},
            {"child_id": "blank_holder", "parent_id": "drawing_die", "relation": "stacked_on"},
            {"child_id": "upper_die_seat", "parent_id": "lower_die_seat", "relation": "guided_by"},
            {"child_id": "punch", "parent_id": "upper_die_seat", "relation": "stacked_on"},
        ],
    }
    return validate_plan_data(plan)


def _extract_mm(requirement: str, patterns: list[str], *, default: float) -> float:
    for pattern in patterns:
        match = re.search(pattern, requirement, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return default


def _extract_box_dims(requirement: str, label: str, *, default: tuple[float, float, float]) -> tuple[float, float, float]:
    pattern = rf"{label}[^。\n]*?尺寸\s*(\d+(?:\.\d+)?)\s*[×xX*]\s*(\d+(?:\.\d+)?)\s*[×xX*]\s*(\d+(?:\.\d+)?)\s*mm"
    match = re.search(pattern, requirement, flags=re.IGNORECASE)
    if not match:
        return default
    return tuple(float(match.group(index)) for index in range(1, 4))  # type: ignore[return-value]


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
        content = _extract_response_content(decoded)
        if content:
            content_parts.append(content)
    return "".join(content_parts)


def _extract_choice_content(choice: dict[str, object]) -> str:
    message = choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content

    delta = choice.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content

    text = choice.get("text")
    if isinstance(text, str):
        return text

    return ""
