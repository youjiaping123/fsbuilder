from __future__ import annotations

from pathlib import Path

import pytest

from fs_builder.application import use_cases
from fs_builder.errors import CLIError
from fs_builder.models import validate_plan_data
from fs_builder.plan_io import write_plan_file
from fs_builder.settings import Settings
from tests.test_models import make_plan_data


def _settings(tmp_path: Path) -> Settings:
    return Settings.from_sources(output_dir=tmp_path)


def test_analyze_command_writes_output(monkeypatch, tmp_path: Path) -> None:
    plan = validate_plan_data(make_plan_data())
    monkeypatch.setattr(use_cases.RequirementAnalyzer, "analyze", lambda self, requirement: plan)

    result = use_cases.analyze_command(
        settings=_settings(tmp_path),
        requirement_text="Design a simple block.",
        input_path=None,
        output_path=tmp_path / "saved_plan.json",
    )

    assert result.output_path == tmp_path / "saved_plan.json"
    assert result.output_path.exists()


def test_generate_command_writes_featurescript(tmp_path: Path) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    result = use_cases.generate_command(
        settings=_settings(tmp_path),
        plan_path=plan_path,
        output_path=None,
    )

    assert result.output_path == tmp_path / "demo_fixture.fs"
    assert result.output_path.exists()
    assert result.report.total_parts == 2


def test_build_command_with_plan_skips_analysis(monkeypatch, tmp_path: Path) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)
    monkeypatch.setattr(
        use_cases.RequirementAnalyzer,
        "analyze",
        lambda self, requirement: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    result = use_cases.build_command(
        settings=_settings(tmp_path),
        requirement_text=None,
        input_path=None,
        plan_path=plan_path,
        output_path=None,
        plan_output_path=None,
    )

    assert result.plan_path == tmp_path / "demo_fixture_plan.json"
    assert result.output_path == tmp_path / "demo_fixture.fs"
    assert result.plan_path.exists()
    assert result.output_path.exists()


def test_build_command_rejects_plan_and_requirement_together(tmp_path: Path) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    with pytest.raises(CLIError, match="不能同时使用"):
        use_cases.build_command(
            settings=_settings(tmp_path),
            requirement_text="Design a simple block.",
            input_path=None,
            plan_path=plan_path,
            output_path=None,
            plan_output_path=None,
        )
