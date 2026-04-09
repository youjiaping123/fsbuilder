"""Web UI 复用的应用服务。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, get_args

from ..analysis import RequirementAnalyzer
from ..errors import CLIError
from ..generation import FeatureScriptGenerator, GenerationReport
from ..io.artifacts import write_text_artifact
from ..io.plans import write_plan_file
from ..models import AssemblyPlan, PartShape, validate_plan_data
from ..settings import Settings


class WebUIService:
    """给 HTTP 层提供可直接调用的高层能力。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_state(self) -> dict[str, Any]:
        return {
            "app_name": "fs-builder Web UI",
            "supported_shapes": list(get_args(PartShape)),
            "output_dir": str(self.settings.output_dir),
            "has_api_key": bool(self.settings.api_key),
            "analyze_model": self.settings.analyze_model,
            "timestamp": _now_iso(),
        }

    def analyze(self, requirement: str, *, persist: bool = False) -> dict[str, Any]:
        cleaned_requirement = requirement.strip()
        if not cleaned_requirement:
            raise CLIError("需求文本不能为空。")

        plan = RequirementAnalyzer(self.settings).analyze(cleaned_requirement)
        plan_path = None
        logs = [
            "已执行需求分析。",
            f"识别到 {len(plan.parts)} 个零件和 {len(plan.assembly_relations)} 条装配关系。",
        ]
        if persist:
            plan_path = write_plan_file(plan, self.settings.plan_output_path(plan.assembly_name))
            logs.append(f"已写入 plan 文件：{plan_path}")

        return self._serialize_result(
            plan=plan,
            report=None,
            plan_path=plan_path,
            fs_path=None,
            logs=logs,
        )

    def generate(self, plan_data: object, *, persist: bool = False) -> dict[str, Any]:
        plan = validate_plan_data(plan_data)
        report = FeatureScriptGenerator().generate_report(plan)
        fs_path = None
        logs = [
            "已根据当前 plan 生成 FeatureScript。",
            (
                f"零件生成结果：{report.succeeded_parts}/{report.total_parts} 成功，"
                f"{report.failed_parts} 个失败。"
            ),
        ]
        if persist:
            fs_path = write_text_artifact(
                report.merged_script,
                self.settings.featurescript_output_path(plan.assembly_name),
            )
            logs.append(f"已写入 FeatureScript 文件：{fs_path}")

        return self._serialize_result(
            plan=plan,
            report=report,
            plan_path=None,
            fs_path=fs_path,
            logs=logs,
        )

    def build(self, requirement: str, *, persist: bool = True) -> dict[str, Any]:
        cleaned_requirement = requirement.strip()
        if not cleaned_requirement:
            raise CLIError("需求文本不能为空。")

        plan = RequirementAnalyzer(self.settings).analyze(cleaned_requirement)
        report = FeatureScriptGenerator().generate_report(plan)
        plan_path = None
        fs_path = None
        logs = [
            "已执行全流程构建。",
            f"分析阶段得到 {len(plan.parts)} 个零件。",
            (
                f"生成阶段完成：{report.succeeded_parts}/{report.total_parts} 成功，"
                f"{report.failed_parts} 个失败。"
            ),
        ]
        if persist:
            plan_path = write_plan_file(plan, self.settings.plan_output_path(plan.assembly_name))
            fs_path = write_text_artifact(
                report.merged_script,
                self.settings.featurescript_output_path(plan.assembly_name),
            )
            logs.append(f"已写入 plan 文件：{plan_path}")
            logs.append(f"已写入 FeatureScript 文件：{fs_path}")

        return self._serialize_result(
            plan=plan,
            report=report,
            plan_path=plan_path,
            fs_path=fs_path,
            logs=logs,
        )

    def _serialize_result(
        self,
        *,
        plan: AssemblyPlan,
        report: GenerationReport | None,
        plan_path: Path | None,
        fs_path: Path | None,
        logs: list[str],
    ) -> dict[str, Any]:
        error_by_part_id = {
            result.part_id: result.error
            for result in (report.part_results if report is not None else [])
            if result.error
        }
        validation_items = [
            {
                "level": "error",
                "title": f"零件 `{part_id}` 生成失败",
                "message": message,
            }
            for part_id, message in error_by_part_id.items()
        ]
        if not validation_items:
            validation_items.append(
                {
                    "level": "success",
                    "title": "校验通过",
                    "message": "当前 plan 与生成结果未发现阻断性问题。",
                }
            )

        return {
            "timestamp": _now_iso(),
            "plan": plan.model_dump(mode="json"),
            "parts": [
                {
                    "id": part.id,
                    "name": part.name,
                    "shape": part.shape,
                    "material_hint": part.material_hint,
                    "status": "error" if part.id in error_by_part_id else "stable",
                    "params": part.params,
                    "position": part.position.model_dump(mode="json"),
                    "description": part.description,
                }
                for part in plan.parts
            ],
            "relations": [relation.model_dump(mode="json") for relation in plan.assembly_relations],
            "featurescript": report.merged_script if report is not None else "",
            "validation": validation_items,
            "summary": {
                "assembly_name": plan.assembly_name,
                "description": plan.description,
                "part_count": len(plan.parts),
                "relation_count": len(plan.assembly_relations),
                "generator": report.generator_name if report is not None else None,
                "succeeded_parts": report.succeeded_parts if report is not None else None,
                "failed_parts": report.failed_parts if report is not None else None,
            },
            "artifacts": {
                "plan_path": str(plan_path) if plan_path is not None else None,
                "featurescript_path": str(fs_path) if fs_path is not None else None,
            },
            "logs": [{"time": _now_iso(), "message": message} for message in logs],
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
