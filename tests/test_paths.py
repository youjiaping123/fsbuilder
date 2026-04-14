from __future__ import annotations

from pathlib import Path

from fs_builder.io.artifacts import featurescript_output_path, plan_output_path, safe_slug


def test_safe_slug_normalizes_unsafe_values() -> None:
    assert safe_slug("../../Outside Plan") == "outside_plan"


def test_plan_output_path_stays_in_output_dir(tmp_path: Path) -> None:
    path = plan_output_path(tmp_path, "../../outside")
    assert path == tmp_path / "outside_plan.json"


def test_featurescript_output_path_stays_in_output_dir(tmp_path: Path) -> None:
    path = featurescript_output_path(tmp_path, "../demo")
    assert path == tmp_path / "demo.fs"
