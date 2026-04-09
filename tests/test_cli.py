from __future__ import annotations

import json
from pathlib import Path

from fs_builder import cli
from fs_builder.models import validate_plan_data
from fs_builder.plan_io import write_plan_file
from tests.test_models import make_plan_data


def test_analyze_input_outputs_json(monkeypatch, tmp_path: Path, capsys) -> None:
    input_path = tmp_path / "requirement.txt"
    input_path.write_text("Design a simple box.", encoding="utf-8")
    plan = validate_plan_data(make_plan_data())
    monkeypatch.setattr(cli, "analyze_requirement", lambda requirement, settings: plan)

    code = cli.main(["analyze", "--input", str(input_path)])

    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["assembly_name"] == "demo_fixture"


def test_build_plan_skips_analysis_and_writes_outputs(
    tmp_path: Path,
    capsys,
) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    output_dir = tmp_path / "artifacts"
    code = cli.main(
        [
            "build",
            "--plan",
            str(plan_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert (output_dir / "demo_fixture_plan.json").exists()
    assert (output_dir / "demo_fixture.fs").exists()
    assert "Plan saved:" in captured.out


def test_generate_uses_templates_without_api_key(tmp_path: Path, capsys) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    code = cli.main(["generate", "--plan", str(plan_path), "--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert "FeatureScript written:" in captured.out


def test_generate_legacy_requires_api_key(monkeypatch, tmp_path: Path, capsys) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)
    monkeypatch.setenv("OPENAI_API_KEY", "")

    code = cli.main(["generate", "--plan", str(plan_path), "--legacy"])

    captured = capsys.readouterr()
    assert code == 2
    assert "OPENAI_API_KEY is required" in captured.err


def test_validate_plan_command(tmp_path: Path, capsys) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    code = cli.main(["validate-plan", "--plan", str(plan_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert "Plan is valid: demo_fixture" in captured.out
