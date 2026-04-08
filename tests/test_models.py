from __future__ import annotations

import pytest

from fs_builder.errors import PlanValidationError
from fs_builder.models import validate_plan_data


def make_plan_data() -> dict:
    return {
        "assembly_name": "demo_fixture",
        "description": "Simple demo fixture.",
        "global_params": {
            "unit": "mm",
            "origin_description": "XY plane at bottom center of assembly, Z points up",
            "total_height_mm": 80,
            "total_width_mm": 120,
            "total_depth_mm": 90,
        },
        "parts": [
            {
                "id": "base_block",
                "name": "Base Block",
                "shape": "box",
                "material_hint": "steel",
                "params": {
                    "width_mm": 120,
                    "depth_mm": 90,
                    "height_mm": 20,
                },
                "position": {
                    "x_mm": 0,
                    "y_mm": 0,
                    "z_bottom_mm": 0,
                },
                "description": "Main support block.",
            },
            {
                "id": "center_boss",
                "name": "Center Boss",
                "shape": "cylinder",
                "material_hint": "steel",
                "params": {
                    "diameter_mm": 30,
                    "height_mm": 60,
                },
                "position": {
                    "x_mm": 0,
                    "y_mm": 0,
                    "z_bottom_mm": 20,
                },
                "description": "Raised cylinder.",
            },
        ],
        "assembly_relations": [
            {
                "child_id": "center_boss",
                "parent_id": "base_block",
                "relation": "stacked_on",
            }
        ],
    }


def test_valid_plan_passes() -> None:
    plan = validate_plan_data(make_plan_data())
    assert plan.assembly_name == "demo_fixture"
    assert len(plan.parts) == 2


def test_invalid_assembly_name_fails() -> None:
    data = make_plan_data()
    data["assembly_name"] = "../bad"
    with pytest.raises(PlanValidationError):
        validate_plan_data(data)


def test_duplicate_part_ids_fail() -> None:
    data = make_plan_data()
    data["parts"][1]["id"] = "base_block"
    with pytest.raises(PlanValidationError):
        validate_plan_data(data)


def test_unsupported_shape_fails() -> None:
    data = make_plan_data()
    data["parts"][0]["shape"] = "plate"
    with pytest.raises(PlanValidationError):
        validate_plan_data(data)
