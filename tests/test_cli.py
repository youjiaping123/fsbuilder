from __future__ import annotations

import json
from pathlib import Path

from fs_builder import cli
from fs_builder.generator import PartResult
from fs_builder.models import validate_plan_data
from fs_builder.plan_io import write_plan_file
from tests.test_models import make_plan_data


class DummyGenerator:
    def __init__(self, settings) -> None:
        self.settings = settings

    def generate(self, plan):
        return [
            PartResult(
                part_id=plan.parts[0].id,
                part_name=plan.parts[0].name,
                code="var body = 1;",
            )
        ]


def test_analyze_input_outputs_json(monkeypatch, tmp_path: Path, capsys) -> None:
    input_path = tmp_path / "requirement.txt"
    input_path.write_text("Design a simple box.", encoding="utf-8")
    plan = validate_plan_data(make_plan_data())
    monkeypatch.setattr(cli, "analyze_requirement", lambda requirement, settings: plan)

    code = cli.main(["analyze", "--input", str(input_path), "--api-key", "sk-test"])

    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["assembly_name"] == "demo_fixture"


def test_build_plan_skips_analysis_and_writes_outputs(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)
    monkeypatch.setattr(cli, "LegacyLLMGenerator", DummyGenerator)

    output_dir = tmp_path / "artifacts"
    code = cli.main(
        [
            "build",
            "--plan",
            str(plan_path),
            "--api-key",
            "sk-test",
            "--output-dir",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert (output_dir / "demo_fixture_plan.json").exists()
    assert (output_dir / "demo_fixture.fs").exists()
    assert "Plan saved:" in captured.out


def test_generate_requires_api_key(tmp_path: Path, capsys) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    code = cli.main(["generate", "--plan", str(plan_path)])

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
