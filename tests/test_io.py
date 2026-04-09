from __future__ import annotations

from pathlib import Path

import pytest

from fs_builder.errors import PlanValidationError
from fs_builder.io.plans import load_plan_file, resolve_plan_output_path, write_plan_file
from fs_builder.io.resources import strip_markdown_fences
from fs_builder.models import validate_plan_data
from tests.test_models import make_plan_data


def test_load_plan_file_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PlanValidationError, match="Plan 文件不存在"):
        load_plan_file(tmp_path / "missing.json")


def test_load_plan_file_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(PlanValidationError, match="Plan 文件不是合法 JSON"):
        load_plan_file(path)


def test_write_plan_file_round_trip(tmp_path: Path) -> None:
    plan = validate_plan_data(make_plan_data())
    path = tmp_path / "plan.json"

    written = write_plan_file(plan, path)
    loaded = load_plan_file(path)

    assert written == path
    assert loaded.assembly_name == "demo_fixture"


def test_strip_markdown_fences_extracts_inner_content() -> None:
    assert strip_markdown_fences('```json\n{"ok":true}\n```') == '{"ok":true}'


def test_resolve_plan_output_path_uses_default_when_output_absent(tmp_path: Path) -> None:
    path = resolve_plan_output_path(
        output_dir=tmp_path,
        assembly_name="demo_fixture",
        output_path=None,
    )

    assert path == tmp_path / "demo_fixture_plan.json"
