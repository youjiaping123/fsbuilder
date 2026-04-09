"""生成服务编排。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import AssemblyPlan
from ..settings import Settings
from .errors import GenerationError
from .merge import merge_featurescript
from .models import GenerationReport, PartResult
from .renderers import render_part


class PartGenerator(Protocol):
    @property
    def name(self) -> str:
        """生成器名称。"""

    def generate(self, plan: AssemblyPlan) -> list[PartResult]:
        """为每个零件生成独立的 FeatureScript 片段。"""


@dataclass(frozen=True)
class FeatureScriptGenerator:
    """默认生成器，只走确定性模板。"""

    name: str = "template"

    def generate(self, plan: AssemblyPlan) -> list[PartResult]:
        results: list[PartResult] = []
        for part in plan.parts:
            try:
                code = render_part(part)
                results.append(PartResult.success(part_id=part.id, part_name=part.name, code=code))
            except GenerationError as exc:
                results.append(
                    PartResult.failure(
                        part_id=part.id,
                        part_name=part.name,
                        error=str(exc),
                        error_kind="render_error",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    PartResult.failure(
                        part_id=part.id,
                        part_name=part.name,
                        error=str(exc),
                        error_kind="system_error",
                    )
                )
        return results

    def generate_report(
        self,
        plan: AssemblyPlan,
        *,
        feature_name: str | None = None,
    ) -> GenerationReport:
        part_results = self.generate(plan)
        merged_script = merge_featurescript(plan, part_results, feature_name=feature_name)
        return GenerationReport(
            merged_script=merged_script,
            part_results=part_results,
            generator_name=self.name,
        )


class TemplateGenerator(FeatureScriptGenerator):
    """保留旧名称，避免外部导入在重构后直接断裂。"""


def build_generator(settings: Settings, *, legacy: bool = False) -> PartGenerator:
    """兼容旧接口，但不再支持 legacy 生成链路。"""
    del settings
    if legacy:
        raise GenerationError("`--legacy` 生成链路已移除，只保留确定性模板生成。")
    return TemplateGenerator()
