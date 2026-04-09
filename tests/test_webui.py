from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from fs_builder.analysis import RequirementAnalyzer
from fs_builder.models import validate_plan_data
from fs_builder.settings import Settings
from fs_builder.webui.api import WebUIService
from tests.test_models import make_plan_data


def _settings(tmp_path: Path) -> Settings:
    return Settings.from_sources(output_dir=tmp_path)


def test_webui_state_exposes_supported_shapes(tmp_path: Path) -> None:
    payload = WebUIService(_settings(tmp_path)).get_state()

    assert payload["app_name"] == "fs-builder Web UI"
    assert payload["output_dir"] == str(tmp_path)
    assert "box" in payload["supported_shapes"]


def test_webui_analyze_returns_plan_and_optional_plan_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    plan = validate_plan_data(make_plan_data())
    monkeypatch.setattr(RequirementAnalyzer, "analyze", lambda self, requirement: plan)

    payload = WebUIService(_settings(tmp_path)).analyze("Design a simple fixture.", persist=True)

    assert payload["plan"]["assembly_name"] == "demo_fixture"
    assert payload["summary"]["part_count"] == 2
    assert payload["artifacts"]["plan_path"] == str(tmp_path / "demo_fixture_plan.json")
    assert (tmp_path / "demo_fixture_plan.json").exists()


def test_webui_generate_returns_featurescript_and_output_file(tmp_path: Path) -> None:
    payload = WebUIService(_settings(tmp_path)).generate(make_plan_data(), persist=True)

    assert "FeatureScript 2399;" in payload["featurescript"]
    assert payload["artifacts"]["featurescript_path"] == str(tmp_path / "demo_fixture.fs")
    assert (tmp_path / "demo_fixture.fs").exists()


def test_webui_build_runs_full_flow(monkeypatch, tmp_path: Path) -> None:
    plan = validate_plan_data(make_plan_data())
    monkeypatch.setattr(RequirementAnalyzer, "analyze", lambda self, requirement: plan)

    payload = WebUIService(_settings(tmp_path)).build("Design a simple fixture.", persist=True)

    assert payload["summary"]["assembly_name"] == "demo_fixture"
    assert payload["artifacts"]["plan_path"] == str(tmp_path / "demo_fixture_plan.json")
    assert payload["artifacts"]["featurescript_path"] == str(tmp_path / "demo_fixture.fs")
    assert (tmp_path / "demo_fixture_plan.json").exists()
    assert (tmp_path / "demo_fixture.fs").exists()


def test_webui_assets_are_packaged() -> None:
    index_html = (
        files("fs_builder.webui").joinpath("static", "index.html").read_text(encoding="utf-8")
    )
    app_js = files("fs_builder.webui").joinpath("static", "app.js").read_text(encoding="utf-8")
    favicon = (
        files("fs_builder.webui").joinpath("static", "favicon.svg").read_text(encoding="utf-8")
    )

    assert "Feature Studio Workspace" in index_html
    assert "/assets/favicon.svg" in index_html
    assert "runBuild" in app_js
    assert "<svg" in favicon
