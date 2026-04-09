"""CLI 使用的应用层编排。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..analysis import RequirementAnalyzer
from ..errors import CLIError
from ..generation import FeatureScriptGenerator, GenerationReport
from ..io.artifacts import write_text_artifact
from ..io.plans import load_plan_file, resolve_plan_output_path, write_plan_file
from ..models import AssemblyPlan
from ..settings import Settings


@dataclass(frozen=True)
class AnalyzeCommandResult:
    plan: AssemblyPlan
    output_path: Path | None


@dataclass(frozen=True)
class ValidatePlanCommandResult:
    plan: AssemblyPlan


@dataclass(frozen=True)
class GenerateCommandResult:
    output_path: Path
    report: GenerationReport


@dataclass(frozen=True)
class BuildCommandResult:
    plan_path: Path
    output_path: Path
    report: GenerationReport


def analyze_command(
    *,
    settings: Settings,
    requirement_text: str | None,
    input_path: Path | None,
    output_path: Path | None,
) -> AnalyzeCommandResult:
    requirement = read_requirement(requirement_text, input_path)
    plan = RequirementAnalyzer(settings).analyze(requirement)
    saved_output = None
    if output_path is not None:
        saved_output = write_plan_file(plan, output_path)
    return AnalyzeCommandResult(plan=plan, output_path=saved_output)


def validate_plan_command(plan_path: Path) -> ValidatePlanCommandResult:
    return ValidatePlanCommandResult(plan=load_plan_file(plan_path))


def generate_command(
    *,
    settings: Settings,
    plan_path: Path,
    output_path: Path | None,
) -> GenerateCommandResult:
    plan = load_plan_file(plan_path)
    report = FeatureScriptGenerator().generate_report(plan)
    target_output_path = write_text_artifact(
        report.merged_script,
        output_path or settings.featurescript_output_path(plan.assembly_name),
    )
    return GenerateCommandResult(output_path=target_output_path, report=report)


def build_command(
    *,
    settings: Settings,
    requirement_text: str | None,
    input_path: Path | None,
    plan_path: Path | None,
    output_path: Path | None,
    plan_output_path: Path | None,
) -> BuildCommandResult:
    if plan_path is not None:
        if requirement_text or input_path:
            raise CLIError("`--plan` 与需求文本/`--input` 不能同时使用。")
        plan = load_plan_file(plan_path)
    else:
        requirement = read_requirement(requirement_text, input_path)
        plan = RequirementAnalyzer(settings).analyze(requirement)

    resolved_plan_path = resolve_plan_output_path(
        output_dir=settings.output_dir,
        assembly_name=plan.assembly_name,
        output_path=plan_output_path,
    )
    write_plan_file(plan, resolved_plan_path)

    report = FeatureScriptGenerator().generate_report(plan)
    resolved_output_path = write_text_artifact(
        report.merged_script,
        output_path or settings.featurescript_output_path(plan.assembly_name),
    )
    return BuildCommandResult(
        plan_path=resolved_plan_path,
        output_path=resolved_output_path,
        report=report,
    )


def read_requirement(raw_requirement: str | None, input_path: Path | None) -> str:
    if raw_requirement and input_path:
        raise CLIError("请在内联需求文本和 `--input` 之间二选一。")
    if input_path is not None:
        try:
            requirement = input_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise CLIError(f"需求文件不存在：{input_path}") from exc
    else:
        requirement = (raw_requirement or "").strip()

    if not requirement:
        raise CLIError("缺少需求文本，请传入内联文本或 `--input FILE`。")
    return requirement
