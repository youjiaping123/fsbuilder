"""
Step 2: Concurrently generate FeatureScript code for each part in the design plan.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Awaitable

from openai import AsyncOpenAI


_PROMPT_PATH = Path(__file__).parent / "prompts" / "generate.txt"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


@dataclass
class PartResult:
    part_id: str
    part_name: str
    code: str
    error: str | None = None


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


async def _generate_one(
    client: AsyncOpenAI,
    system_prompt: str,
    part: dict,
    global_params: dict,
    model: str,
    semaphore: asyncio.Semaphore,
    on_part_done: Callable[[PartResult], Awaitable[None]] | None,
) -> PartResult:
    """Generate FeatureScript for a single part."""
    part_id = part["id"]
    part_name = part["name"]

    user_message = (
        "Generate FeatureScript body code for the following part.\n\n"
        f"## Global Parameters\n```json\n{json.dumps(global_params, indent=2, ensure_ascii=False)}\n```\n\n"
        f"## This Part\n```json\n{json.dumps(part, indent=2, ensure_ascii=False)}\n```\n\n"
        "Remember:\n"
        f"- Use `id + \"{part_id}_\"` as the prefix for ALL operation IDs.\n"
        "- Convert all mm values to meters (divide by 1000).\n"
        "- Output ONLY FeatureScript statements. No function wrapper. No imports.\n"
    )

    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = _strip_fences(response.choices[0].message.content.strip())
            result = PartResult(part_id=part_id, part_name=part_name, code=raw)

        except Exception as e:  # noqa: BLE001
            result = PartResult(
                part_id=part_id,
                part_name=part_name,
                code="",
                error=str(e),
            )

    if on_part_done is not None:
        await on_part_done(result)

    return result


async def _generate_all(
    plan: dict,
    model: str,
    max_concurrent: int,
    api_key: str | None,
    base_url: str | None,
    on_part_done: Callable[[PartResult], Awaitable[None]] | None,
) -> list[PartResult]:
    client = AsyncOpenAI(
        api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        base_url=base_url or None,
    )
    system_prompt = _load_system_prompt()
    global_params = plan["global_params"]
    semaphore = asyncio.Semaphore(max_concurrent)

    tasks = [
        _generate_one(client, system_prompt, part, global_params, model, semaphore, on_part_done)
        for part in plan["parts"]
    ]
    return await asyncio.gather(*tasks)


async def generate_async(
    plan: dict,
    *,
    model: str = "gpt-4o-mini",
    max_concurrent: int = 8,
    api_key: str | None = None,
    base_url: str | None = None,
    on_part_done: Callable[[PartResult], Awaitable[None]] | None = None,
) -> list[PartResult]:
    """Async version for use in async contexts (e.g., web server)."""
    return await _generate_all(
        plan,
        model=model,
        max_concurrent=max_concurrent,
        api_key=api_key,
        base_url=base_url,
        on_part_done=on_part_done,
    )


def generate(
    plan: dict,
    *,
    model: str = "gpt-4o-mini",
    max_concurrent: int = 8,
    api_key: str | None = None,
    base_url: str | None = None,
) -> list[PartResult]:
    """
    Concurrently generate FeatureScript for every part in the plan.
    Returns a list of PartResult in the same order as plan["parts"].
    """
    return asyncio.run(
        _generate_all(
            plan,
            model=model,
            max_concurrent=max_concurrent,
            api_key=api_key,
            base_url=base_url,
            on_part_done=None,
        )
    )
