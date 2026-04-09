"""内置 demo fallback 计划。"""

from __future__ import annotations

import re

from ..models import AssemblyPlan, validate_plan_data


def match_demo_fallback(requirement: str) -> AssemblyPlan | None:
    """仅为仓库内置演示样例提供 fallback，避免把兜底逻辑扩散到通用需求。"""
    lowered = requirement.lower()
    if "cold drawing die" in lowered or "冷拉延模具" in requirement or "拉延模具" in requirement:
        return _build_drawing_die_plan(requirement)
    return None


def _build_drawing_die_plan(requirement: str) -> AssemblyPlan:
    punch_diameter = _extract_mm(
        requirement,
        [r"凸模外径\s*[=：:]\s*(\d+(?:\.\d+)?)\s*mm"],
        default=60.0,
    )
    punch_height = _extract_mm(
        requirement,
        [
            r"凸模外径\s*[=：:]\s*\d+(?:\.\d+)?\s*mm（与工件内径匹配）[，,]\s*高度\s*(\d+(?:\.\d+)?)\s*mm"
        ],
        default=80.0,
    )
    die_cavity_diameter = _extract_mm(
        requirement,
        [r"凹模型腔直径\s*[=：:]\s*(\d+(?:\.\d+)?)\s*mm"],
        default=64.0,
    )
    holder_outer_diameter = _extract_mm(
        requirement,
        [r"压边圈外径\s*=\s*凹模外径\s*=\s*(\d+(?:\.\d+)?)\s*mm"],
        default=160.0,
    )
    upper_seat = _extract_box_dims(requirement, "上模座", default=(200.0, 200.0, 40.0))
    lower_seat = _extract_box_dims(requirement, "下模座", default=(200.0, 200.0, 40.0))
    workpiece_outer_diameter = _extract_mm(
        requirement,
        [r"外径\s*(\d+(?:\.\d+)?)\s*mm", r"工件外径匹配[）)]?\s*(\d+(?:\.\d+)?)\s*mm"],
        default=64.0,
    )
    workpiece_depth = _extract_mm(requirement, [r"筒深[：:]\s*(\d+(?:\.\d+)?)\s*mm"], default=50.0)

    blank_holder_inner = max(workpiece_outer_diameter + 6.0, punch_diameter + 6.0)
    die_height = max(workpiece_depth + 10.0, 60.0)
    blank_holder_height = 20.0
    total_height = 280.0

    plan = {
        "assembly_name": "drawing_die",
        "description": (
            "Single-action cold drawing die with upper and lower seats, punch, die, "
            "and blank holder."
        ),
        "global_params": {
            "unit": "mm",
            "origin_description": "XY plane at bottom center of assembly, Z points up",
            "total_height_mm": total_height,
            "total_width_mm": max(upper_seat[0], lower_seat[0]),
            "total_depth_mm": max(upper_seat[1], lower_seat[1]),
        },
        "parts": [
            {
                "id": "lower_die_seat",
                "name": "Lower Die Seat",
                "shape": "box",
                "material_hint": "steel",
                "params": {
                    "width_mm": lower_seat[0],
                    "depth_mm": lower_seat[1],
                    "height_mm": lower_seat[2],
                },
                "position": {"x_mm": 0.0, "y_mm": 0.0, "z_bottom_mm": 0.0},
                "description": "Base block carrying the die and blank holder.",
            },
            {
                "id": "drawing_die",
                "name": "Drawing Die",
                "shape": "hollow_cylinder",
                "material_hint": "cast_iron",
                "params": {
                    "outer_diameter_mm": holder_outer_diameter,
                    "inner_diameter_mm": die_cavity_diameter,
                    "height_mm": die_height,
                },
                "position": {"x_mm": 0.0, "y_mm": 0.0, "z_bottom_mm": lower_seat[2]},
                "description": "Fixed die cavity matching the workpiece outer diameter.",
            },
            {
                "id": "blank_holder",
                "name": "Blank Holder",
                "shape": "hollow_cylinder",
                "material_hint": "steel",
                "params": {
                    "outer_diameter_mm": holder_outer_diameter,
                    "inner_diameter_mm": blank_holder_inner,
                    "height_mm": blank_holder_height,
                },
                "position": {"x_mm": 0.0, "y_mm": 0.0, "z_bottom_mm": lower_seat[2] + die_height},
                "description": "Ring that restrains the sheet edge during drawing.",
            },
            {
                "id": "upper_die_seat",
                "name": "Upper Die Seat",
                "shape": "box",
                "material_hint": "steel",
                "params": {
                    "width_mm": upper_seat[0],
                    "depth_mm": upper_seat[1],
                    "height_mm": upper_seat[2],
                },
                "position": {
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                    "z_bottom_mm": total_height - upper_seat[2],
                },
                "description": "Upper block carrying the punch.",
            },
            {
                "id": "punch",
                "name": "Punch",
                "shape": "cylinder",
                "material_hint": "steel",
                "params": {
                    "diameter_mm": punch_diameter,
                    "height_mm": punch_height,
                },
                "position": {
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                    "z_bottom_mm": total_height - upper_seat[2] - punch_height,
                },
                "description": "Moving punch that draws the blank into the die.",
            },
        ],
        "assembly_relations": [
            {"child_id": "drawing_die", "parent_id": "lower_die_seat", "relation": "stacked_on"},
            {"child_id": "blank_holder", "parent_id": "drawing_die", "relation": "stacked_on"},
            {"child_id": "upper_die_seat", "parent_id": "lower_die_seat", "relation": "guided_by"},
            {"child_id": "punch", "parent_id": "upper_die_seat", "relation": "stacked_on"},
        ],
    }
    return validate_plan_data(plan)


def _extract_mm(requirement: str, patterns: list[str], *, default: float) -> float:
    for pattern in patterns:
        match = re.search(pattern, requirement, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return default


def _extract_box_dims(
    requirement: str,
    label: str,
    *,
    default: tuple[float, float, float],
) -> tuple[float, float, float]:
    pattern = (
        rf"{label}[^。\n]*?尺寸\s*(\d+(?:\.\d+)?)\s*[×xX*]\s*(\d+(?:\.\d+)?)\s*[×xX*]\s*"
        rf"(\d+(?:\.\d+)?)\s*mm"
    )
    match = re.search(pattern, requirement, flags=re.IGNORECASE)
    if not match:
        return default
    return (
        float(match.group(1)),
        float(match.group(2)),
        float(match.group(3)),
    )
