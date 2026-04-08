"""Legacy LLM FeatureScript generator kept as a temporary compatibility layer."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from typing import Protocol, Sequence

from openai import AsyncOpenAI

from .models import AssemblyPlan, PartSpec
from .prompting import load_prompt, strip_markdown_fences
from .settings import Settings


@dataclass(frozen=True)
class PartResult:
    part_id: str
    part_name: str
    code: str
    error: str | None = None


class PartGenerator(Protocol):
    name: str

    def generate(self, plan: AssemblyPlan) -> list[PartResult]:
        """Generate one FeatureScript body per part."""


class LegacyLLMGenerator:
    """Temporary generator until deterministic FeatureScript templates replace it."""

    name = "legacy-llm"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._system_prompt = load_prompt("generate_legacy.txt")

    def generate(self, plan: AssemblyPlan) -> list[PartResult]:
        return asyncio.run(self._generate_all(plan))

    async def _generate_all(self, plan: AssemblyPlan) -> list[PartResult]:
        client = AsyncOpenAI(
            api_key=self.settings.require_api_key("generate FeatureScript"),
            base_url=self.settings.base_url or None,
        )
        semaphore = asyncio.Semaphore(self.settings.concurrency)
        tasks = [
            self._generate_one(
                client=client,
                part=part,
                global_params=plan.global_params.model_dump(),
                semaphore=semaphore,
            )
            for part in plan.parts
        ]
        return list(await asyncio.gather(*tasks))

    async def _generate_one(
        self,
        *,
        client: AsyncOpenAI,
        part: PartSpec,
        global_params: dict[str, object],
        semaphore: asyncio.Semaphore,
    ) -> PartResult:
        user_message = self._build_user_message(part, global_params)
        async with semaphore:
            try:
                response = await client.chat.completions.create(
                    model=self.settings.generate_model,
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
                content = response.choices[0].message.content or ""
                raw = strip_markdown_fences(content.strip())
                return PartResult(part_id=part.id, part_name=part.name, code=raw)
            except Exception as exc:  # noqa: BLE001
                return PartResult(
                    part_id=part.id,
                    part_name=part.name,
                    code="",
                    error=str(exc),
                )

    @staticmethod
    def _build_user_message(part: PartSpec, global_params: dict[str, object]) -> str:
        return (
            "Generate FeatureScript body code for the following part.\n\n"
            f"## Global Parameters\n```json\n{json.dumps(global_params, indent=2, ensure_ascii=False)}\n```\n\n"
            f"## This Part\n```json\n{json.dumps(part.model_dump(), indent=2, ensure_ascii=False)}\n```\n\n"
            "Remember:\n"
            f"- Use `id + \"{part.id}_\"` as the prefix for ALL operation IDs.\n"
            "- Keep all stored dimensions as plain millimeter numbers.\n"
            "- Apply `* millimeter` only at the point of use in FeatureScript.\n"
            "- Output ONLY FeatureScript statements. No function wrapper. No imports.\n"
        )


def count_failed_parts(results: Sequence[PartResult]) -> int:
    return sum(1 for result in results if result.error)
