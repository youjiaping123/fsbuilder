"""LLM-backed requirement analysis."""

from __future__ import annotations

import json

from openai import OpenAI

from .errors import PlanValidationError
from .models import AssemblyPlan, validate_plan_data
from .prompting import load_prompt, strip_markdown_fences
from .settings import Settings


def analyze_requirement(requirement: str, settings: Settings) -> AssemblyPlan:
    cleaned_requirement = requirement.strip()
    if not cleaned_requirement:
        raise PlanValidationError("Requirement text must not be empty.")

    client = OpenAI(
        api_key=settings.require_api_key("analyze requirements"),
        base_url=settings.base_url or None,
    )
    response = client.chat.completions.create(
        model=settings.analyze_model,
        max_tokens=16384,
        messages=[
            {"role": "system", "content": load_prompt("analyze.txt")},
            {"role": "user", "content": cleaned_requirement},
        ],
    )
    content = response.choices[0].message.content or ""
    raw = strip_markdown_fences(content.strip())
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PlanValidationError(
            f"Analyzer returned invalid JSON.\nError: {exc}\n\nRaw output:\n{raw}"
        ) from exc
    return validate_plan_data(data)
