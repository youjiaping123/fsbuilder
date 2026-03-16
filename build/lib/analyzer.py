"""
Step 1: Analyze natural language requirement → structured JSON design plan.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncGenerator

from openai import OpenAI, AsyncOpenAI


_PROMPT_PATH = Path(__file__).parent / "prompts" / "analyze.txt"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _strip_fences(raw: str) -> str:
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner, in_block = [], False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                inner.append(line)
        return "\n".join(inner)
    return raw


def analyze(
    requirement: str,
    *,
    model: str = "gpt-4o",
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict:
    """
    Call the AI to convert a natural language requirement into a structured
    design plan (dict). Raises ValueError if the response is not valid JSON.
    """
    client = OpenAI(
        api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        base_url=base_url or None,
    )
    system_prompt = _load_system_prompt()

    response = client.chat.completions.create(
        model=model,
        max_tokens=16384,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": requirement},
        ],
    )

    raw = _strip_fences(response.choices[0].message.content.strip())

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"AI returned invalid JSON.\nError: {e}\n\nRaw output:\n{raw}"
        ) from e

    _validate_plan(plan)
    return plan


async def analyze_stream(
    requirement: str,
    *,
    model: str = "gpt-4o",
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Async generator that streams text chunks from the AI as they arrive,
    then yields a final sentinel {"__done__": true, "plan": {...}} JSON string.
    Raises ValueError if the final accumulated text is not valid JSON.
    """
    client = AsyncOpenAI(
        api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        base_url=base_url or None,
    )
    system_prompt = _load_system_prompt()

    accumulated = []
    async with await client.chat.completions.create(
        model=model,
        max_tokens=16384,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": requirement},
        ],
    ) as stream:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                accumulated.append(delta)
                yield delta

    raw = _strip_fences("".join(accumulated).strip())
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"AI returned invalid JSON.\nError: {e}\n\nRaw output:\n{raw}"
        ) from e

    _validate_plan(plan)
    # Final sentinel carries the parsed plan
    yield json.dumps({"__done__": True, "plan": plan}, ensure_ascii=False)


def _validate_plan(plan: dict) -> None:
    """Light structural validation — fail fast before spending on generation."""
    required_top = {"assembly_name", "global_params", "parts", "assembly_relations"}
    missing = required_top - plan.keys()
    if missing:
        raise ValueError(f"Design plan missing keys: {missing}")

    if not plan["parts"]:
        raise ValueError("Design plan has no parts.")

    part_ids = set()
    for p in plan["parts"]:
        for field in ("id", "name", "shape", "params", "position"):
            if field not in p:
                raise ValueError(f"Part missing field '{field}': {p}")
        pid = p["id"]
        if pid in part_ids:
            raise ValueError(f"Duplicate part id: '{pid}'")
        part_ids.add(pid)
        for pos_field in ("x_mm", "y_mm", "z_bottom_mm"):
            if pos_field not in p["position"]:
                raise ValueError(f"Part '{pid}' position missing '{pos_field}'")
