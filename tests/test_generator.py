from __future__ import annotations

from importlib.resources import files

from fs_builder.generator import TemplateGenerator
from fs_builder.models import validate_plan_data


def make_template_plan() -> dict:
    return {
        "assembly_name": "template_demo",
        "description": "Template generator coverage.",
        "global_params": {
            "unit": "mm",
            "origin_description": "XY plane at bottom center of assembly, Z points up",
            "total_height_mm": 160,
            "total_width_mm": 180,
            "total_depth_mm": 180,
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
            {
                "id": "guide_ring",
                "name": "Guide Ring",
                "shape": "hollow_cylinder",
                "material_hint": "steel",
                "params": {
                    "outer_diameter_mm": 70,
                    "inner_diameter_mm": 40,
                    "height_mm": 25,
                },
                "position": {
                    "x_mm": 45,
                    "y_mm": 0,
                    "z_bottom_mm": 20,
                },
                "description": "Outer guide ring.",
            },
            {
                "id": "tapered_post",
                "name": "Tapered Post",
                "shape": "tapered_cylinder",
                "material_hint": "steel",
                "params": {
                    "top_diameter_mm": 18,
                    "bottom_diameter_mm": 36,
                    "height_mm": 50,
                },
                "position": {
                    "x_mm": -45,
                    "y_mm": 0,
                    "z_bottom_mm": 20,
                },
                "description": "Simple tapered locator.",
            },
            {
                "id": "mounting_flange",
                "name": "Mounting Flange",
                "shape": "flange",
                "material_hint": "steel",
                "params": {
                    "flange_diameter_mm": 80,
                    "flange_height_mm": 12,
                    "shaft_diameter_mm": 35,
                    "shaft_height_mm": 40,
                },
                "position": {
                    "x_mm": 0,
                    "y_mm": 50,
                    "z_bottom_mm": 20,
                },
                "description": "Demo flange body.",
            },
        ],
        "assembly_relations": [],
    }


def test_template_generator_covers_all_supported_shapes() -> None:
    plan = validate_plan_data(make_template_plan())

    results = TemplateGenerator().generate(plan)

    assert len(results) == 5
    assert all(result.error is None for result in results)

    by_part = {result.part_id: result.code for result in results}
    assert "fCuboid" in by_part["base_block"]
    assert "corner1" in by_part["base_block"]
    assert "PropertyType.NAME" in by_part["base_block"]
    assert "fCylinder" in by_part["center_boss"]
    assert "bottomCenter" in by_part["center_boss"]
    assert '"value" : "Center Boss"' in by_part["center_boss"]
    assert "BooleanOperationType.SUBTRACTION" in by_part["guide_ring"]
    assert 'qCreatedBy(id + "guide_ring_inner", EntityType.BODY)' in by_part["guide_ring"]
    assert 'qCreatedBy(id + "guide_ring_outer", EntityType.BODY)' in by_part["guide_ring"]
    assert "fCone" in by_part["tapered_post"]
    assert "topRadius" in by_part["tapered_post"]
    assert "BooleanOperationType.UNION" in by_part["mounting_flange"]
    assert (
        'qCreatedBy(id + "mounting_flange_flange", EntityType.BODY)' in by_part["mounting_flange"]
    )
    assert '"value" : "Mounting Flange"' in by_part["mounting_flange"]


def test_reference_guide_is_packaged() -> None:
    content = (
        files("fs_builder.references")
        .joinpath("featurescript_guide.md")
        .read_text(encoding="utf-8")
    )

    assert "FeatureScript 使用教程" in content
    assert "defineFeature" in content
