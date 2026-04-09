"""Plan 文件 I/O。"""

from __future__ import annotations

import json
from pathlib import Path

from ..errors import PlanValidationError
from ..models import AssemblyPlan, validate_plan_data
from .artifacts import plan_output_path, write_text_artifact


def load_plan_file(path: Path) -> AssemblyPlan:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanValidationError(f"Plan 文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanValidationError(f"Plan 文件不是合法 JSON：{path}\n{exc}") from exc
    return validate_plan_data(raw)


def write_plan_file(plan: AssemblyPlan, path: Path) -> Path:
    return write_text_artifact(plan.to_pretty_json(), path)


def resolve_plan_output_path(
    *,
    output_dir: Path,
    assembly_name: str,
    output_path: Path | None,
) -> Path:
    if output_path is not None:
        return output_path
    return plan_output_path(output_dir, assembly_name)
