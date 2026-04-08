"""Plan serialization helpers."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import PlanValidationError
from .models import AssemblyPlan, validate_plan_data


def load_plan_file(path: Path) -> AssemblyPlan:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanValidationError(f"Plan file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanValidationError(f"Plan file is not valid JSON: {path}\n{exc}") from exc
    return validate_plan_data(raw)


def write_plan_file(plan: AssemblyPlan, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.to_pretty_json(), encoding="utf-8")
