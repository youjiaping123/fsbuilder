"""FeatureScript 模板辅助函数。"""

from __future__ import annotations


def format_number(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def millimeter_expr(value: float) -> str:
    return f"{format_number(value)} * millimeter"


def point_expr(x_mm: float, y_mm: float, z_mm: float) -> str:
    return (
        f"vector({format_number(x_mm)}, {format_number(y_mm)}, {format_number(z_mm)}) * millimeter"
    )


def set_name_expr(*, entity_query: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "setProperty(context, { "
        f'"entities" : {entity_query}, '
        '"propertyType" : PropertyType.NAME, '
        f'"value" : "{escaped}" '
        "});"
    )
