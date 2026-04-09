from __future__ import annotations

import json
from pathlib import Path

import pytest

from fs_builder import cli
from fs_builder.models import validate_plan_data
from fs_builder.plan_io import write_plan_file
from tests.test_models import make_plan_data


def test_analyze_input_outputs_json(monkeypatch, tmp_path: Path, capsys) -> None:
    input_path = tmp_path / "requirement.txt"
    input_path.write_text("Design a simple box.", encoding="utf-8")
    plan = validate_plan_data(make_plan_data())
    monkeypatch.setattr(
        cli,
        "analyze_command",
        lambda **kwargs: type("Result", (), {"plan": plan, "output_path": None})(),
    )

    code = cli.main(["analyze", "--input", str(input_path)])

    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["assembly_name"] == "demo_fixture"


def test_build_plan_skips_analysis_and_writes_outputs(tmp_path: Path, capsys) -> None:
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
    assert "Plan 已写入：" in captured.out
    assert "FeatureScript 已写入：" in captured.out


def test_generate_uses_templates_without_api_key(tmp_path: Path, capsys) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    code = cli.main(["generate", "--plan", str(plan_path), "--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert "FeatureScript 已写入：" in captured.out
    assert "零件生成结果：" in captured.out


def test_validate_plan_command(tmp_path: Path, capsys) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    code = cli.main(["validate-plan", "--plan", str(plan_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert "Plan 校验通过：demo_fixture" in captured.out


def test_legacy_option_is_rejected_by_parser(tmp_path: Path, capsys) -> None:
    plan = validate_plan_data(make_plan_data())
    plan_path = tmp_path / "demo_plan.json"
    write_plan_file(plan, plan_path)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["generate", "--plan", str(plan_path), "--legacy"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "unrecognized arguments: --legacy" in captured.err


def test_serve_command_starts_web_ui(monkeypatch, capsys) -> None:
    calls: list[tuple[str, int]] = []

    monkeypatch.setattr(
        cli,
        "serve_web_ui",
        lambda settings, *, host, port: calls.append((host, port)),
    )

    code = cli.main(["serve", "--host", "0.0.0.0", "--port", "9000"])

    captured = capsys.readouterr()
    assert code == 0
    assert calls == [("0.0.0.0", 9000)]
    assert "http://127.0.0.1:9000" in captured.out
