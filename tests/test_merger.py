from __future__ import annotations

from fs_builder.generation import PartResult
from fs_builder.generation.merge import merge_featurescript
from fs_builder.models import validate_plan_data
from tests.test_models import make_plan_data


def test_merge_keeps_order_and_embeds_errors() -> None:
    plan = validate_plan_data(make_plan_data())
    results = [
        PartResult(part_id="base_block", part_name="Base Block", code="var base = 1;"),
        PartResult(
            part_id="center_boss",
            part_name="Center Boss",
            code="",
            error="mock failure",
        ),
    ]

    merged = merge_featurescript(plan, results)

    assert "Base Block (base_block)" in merged
    assert "var base = 1;" in merged
    assert "Part 'center_boss' failed: mock failure" in merged
    assert merged.index("// ── Base Block (base_block)") < merged.index(
        "// [ERROR] Part 'center_boss' (Center Boss) failed to generate:"
    )
