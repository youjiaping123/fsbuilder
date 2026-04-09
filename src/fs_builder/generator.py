"""FeatureScript generators."""

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


class TemplateGenerator:
    """Deterministic FeatureScript generator for the supported demo shapes."""

    name = "template"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    def generate(self, plan: AssemblyPlan) -> list[PartResult]:
        results: list[PartResult] = []
        for part in plan.parts:
            try:
                code = self._render_part(part)
                results.append(PartResult(part_id=part.id, part_name=part.name, code=code))
            except Exception as exc:  # noqa: BLE001
                results.append(
                    PartResult(
                        part_id=part.id,
                        part_name=part.name,
                        code="",
                        error=str(exc),
                    )
                )
        return results

    def _render_part(self, part: PartSpec) -> str:
        renderers = {
            "box": self._render_box,
            "cylinder": self._render_cylinder,
            "hollow_cylinder": self._render_hollow_cylinder,
            "tapered_cylinder": self._render_tapered_cylinder,
            "flange": self._render_flange,
        }
        renderer = renderers.get(part.shape)
        if renderer is None:
            raise ValueError(f"Unsupported shape for template generation: {part.shape}")
        return renderer(part)

    def _render_box(self, part: PartSpec) -> str:
        width = part.params["width_mm"]
        depth = part.params["depth_mm"]
        height = part.params["height_mm"]
        x = part.position.x_mm
        y = part.position.y_mm
        z = part.position.z_bottom_mm

        lines = [
            f'fCuboid(context, id + "{part.id}_cuboid", {{',
            f'    "corner1" : {_point_expr(x - width / 2, y - depth / 2, z)},',
            f'    "corner2" : {_point_expr(x + width / 2, y + depth / 2, z + height)}',
            "});",
            _set_name_expr(
                entity_query=f'qCreatedBy(id + "{part.id}_cuboid", EntityType.BODY)',
                value=part.name,
            ),
        ]
        return "\n".join(lines)

    def _render_cylinder(self, part: PartSpec) -> str:
        diameter = part.params["diameter_mm"]
        height = part.params["height_mm"]
        x = part.position.x_mm
        y = part.position.y_mm
        bottom_z = part.position.z_bottom_mm
        top_z = bottom_z + height

        lines = [
            f"var radius = {_mm(diameter / 2)};",
            f'fCylinder(context, id + "{part.id}_cylinder", {{',
            f'    "bottomCenter" : {_point_expr(x, y, bottom_z)},',
            f'    "topCenter" : {_point_expr(x, y, top_z)},',
            '    "radius" : radius',
            "});",
            _set_name_expr(
                entity_query=f'qCreatedBy(id + "{part.id}_cylinder", EntityType.BODY)',
                value=part.name,
            ),
        ]
        return "\n".join(lines)

    def _render_hollow_cylinder(self, part: PartSpec) -> str:
        outer_diameter = part.params["outer_diameter_mm"]
        inner_diameter = part.params["inner_diameter_mm"]
        height = part.params["height_mm"]
        x = part.position.x_mm
        y = part.position.y_mm
        bottom_z = part.position.z_bottom_mm
        top_z = bottom_z + height

        lines = [
            f"var outerRadius = {_mm(outer_diameter / 2)};",
            f"var innerRadius = {_mm(inner_diameter / 2)};",
            f'fCylinder(context, id + "{part.id}_outer", {{',
            f'    "bottomCenter" : {_point_expr(x, y, bottom_z)},',
            f'    "topCenter" : {_point_expr(x, y, top_z)},',
            '    "radius" : outerRadius',
            "});",
            f'fCylinder(context, id + "{part.id}_inner", {{',
            f'    "bottomCenter" : {_point_expr(x, y, bottom_z)},',
            f'    "topCenter" : {_point_expr(x, y, top_z)},',
            '    "radius" : innerRadius',
            "});",
            f'opBoolean(context, id + "{part.id}_subtract", {{',
            f'    "tools" : qCreatedBy(id + "{part.id}_inner", EntityType.BODY),',
            f'    "targets" : qCreatedBy(id + "{part.id}_outer", EntityType.BODY),',
            '    "operationType" : BooleanOperationType.SUBTRACTION',
            "});",
            _set_name_expr(
                entity_query=f'qCreatedBy(id + "{part.id}_outer", EntityType.BODY)',
                value=part.name,
            ),
        ]
        return "\n".join(lines)

    def _render_tapered_cylinder(self, part: PartSpec) -> str:
        bottom_diameter = part.params["bottom_diameter_mm"]
        top_diameter = part.params["top_diameter_mm"]
        height = part.params["height_mm"]
        bottom_z = part.position.z_bottom_mm
        top_z = part.position.z_bottom_mm + height
        x = part.position.x_mm
        y = part.position.y_mm

        lines = [
            f"var bottomRadius = {_mm(bottom_diameter / 2)};",
            f"var topRadius = {_mm(top_diameter / 2)};",
            f'fCone(context, id + "{part.id}_cone", {{',
            f'    "bottomCenter" : {_point_expr(x, y, bottom_z)},',
            f'    "topCenter" : {_point_expr(x, y, top_z)},',
            '    "bottomRadius" : bottomRadius,',
            '    "topRadius" : topRadius',
            "});",
            _set_name_expr(
                entity_query=f'qCreatedBy(id + "{part.id}_cone", EntityType.BODY)',
                value=part.name,
            ),
        ]
        return "\n".join(lines)

    def _render_flange(self, part: PartSpec) -> str:
        flange_diameter = part.params["flange_diameter_mm"]
        flange_height = part.params["flange_height_mm"]
        shaft_diameter = part.params["shaft_diameter_mm"]
        shaft_height = part.params["shaft_height_mm"]
        union_id = f"{part.id}_union"
        flange_z = part.position.z_bottom_mm
        shaft_z = part.position.z_bottom_mm + flange_height
        x = part.position.x_mm
        y = part.position.y_mm

        lines = [
            f"var flangeRadius = {_mm(flange_diameter / 2)};",
            f"var shaftRadius = {_mm(shaft_diameter / 2)};",
            f'fCylinder(context, id + "{part.id}_flange", {{',
            f'    "bottomCenter" : {_point_expr(x, y, flange_z)},',
            f'    "topCenter" : {_point_expr(x, y, flange_z + flange_height)},',
            '    "radius" : flangeRadius',
            "});",
            f'fCylinder(context, id + "{part.id}_shaft", {{',
            f'    "bottomCenter" : {_point_expr(x, y, shaft_z)},',
            f'    "topCenter" : {_point_expr(x, y, shaft_z + shaft_height)},',
            '    "radius" : shaftRadius',
            "});",
            f'opBoolean(context, id + "{union_id}", {{',
            f'    "tools" : qUnion([qCreatedBy(id + "{part.id}_flange", EntityType.BODY), qCreatedBy(id + "{part.id}_shaft", EntityType.BODY)]),',
            '    "operationType" : BooleanOperationType.UNION',
            "});",
            _set_name_expr(
                entity_query=f'qCreatedBy(id + "{part.id}_flange", EntityType.BODY)',
                value=part.name,
            ),
        ]
        return "\n".join(lines)


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
            timeout=self.settings.api_timeout_seconds,
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


def build_generator(settings: Settings, *, legacy: bool = False) -> PartGenerator:
    if legacy:
        return LegacyLLMGenerator(settings)
    return TemplateGenerator(settings)


def _fmt(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _mm(value: float) -> str:
    return f"{_fmt(value)} * millimeter"


def _plane_expr(x_mm: float, y_mm: float, z_mm: float) -> str:
    return f"plane(vector({_fmt(x_mm)}, {_fmt(y_mm)}, {_fmt(z_mm)}) * millimeter, Z_DIRECTION)"


def _point_expr(x_mm: float, y_mm: float, z_mm: float) -> str:
    return f"vector({_fmt(x_mm)}, {_fmt(y_mm)}, {_fmt(z_mm)}) * millimeter"


def _set_name_expr(*, entity_query: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "setProperty(context, { "
        f'"entities" : {entity_query}, '
        '"propertyType" : PropertyType.NAME, '
        f'"value" : "{escaped}" '
        "});"
    )
