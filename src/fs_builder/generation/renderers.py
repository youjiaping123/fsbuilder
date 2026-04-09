"""确定性 FeatureScript 渲染器注册表。"""

from __future__ import annotations

from collections.abc import Callable

from ..models import PartShape, PartSpec
from .errors import PartRenderError
from .helpers import millimeter_expr, point_expr, set_name_expr

Renderer = Callable[[PartSpec], str]


def render_part(part: PartSpec) -> str:
    renderer = _RENDERERS.get(part.shape)
    if renderer is None:
        raise PartRenderError(f"不支持的零件 shape：{part.shape}")
    return renderer(part)


def _render_box(part: PartSpec) -> str:
    width = part.params["width_mm"]
    depth = part.params["depth_mm"]
    height = part.params["height_mm"]
    x = part.position.x_mm
    y = part.position.y_mm
    z = part.position.z_bottom_mm

    lines = [
        f'fCuboid(context, id + "{part.id}_cuboid", {{',
        f'    "corner1" : {point_expr(x - width / 2, y - depth / 2, z)},',
        f'    "corner2" : {point_expr(x + width / 2, y + depth / 2, z + height)}',
        "});",
        set_name_expr(
            entity_query=f'qCreatedBy(id + "{part.id}_cuboid", EntityType.BODY)',
            value=part.name,
        ),
    ]
    return "\n".join(lines)


def _render_cylinder(part: PartSpec) -> str:
    diameter = part.params["diameter_mm"]
    height = part.params["height_mm"]
    x = part.position.x_mm
    y = part.position.y_mm
    bottom_z = part.position.z_bottom_mm
    top_z = bottom_z + height

    lines = [
        f"var radius = {millimeter_expr(diameter / 2)};",
        f'fCylinder(context, id + "{part.id}_cylinder", {{',
        f'    "bottomCenter" : {point_expr(x, y, bottom_z)},',
        f'    "topCenter" : {point_expr(x, y, top_z)},',
        '    "radius" : radius',
        "});",
        set_name_expr(
            entity_query=f'qCreatedBy(id + "{part.id}_cylinder", EntityType.BODY)',
            value=part.name,
        ),
    ]
    return "\n".join(lines)


def _render_hollow_cylinder(part: PartSpec) -> str:
    outer_diameter = part.params["outer_diameter_mm"]
    inner_diameter = part.params["inner_diameter_mm"]
    height = part.params["height_mm"]
    x = part.position.x_mm
    y = part.position.y_mm
    bottom_z = part.position.z_bottom_mm
    top_z = bottom_z + height

    lines = [
        f"var outerRadius = {millimeter_expr(outer_diameter / 2)};",
        f"var innerRadius = {millimeter_expr(inner_diameter / 2)};",
        f'fCylinder(context, id + "{part.id}_outer", {{',
        f'    "bottomCenter" : {point_expr(x, y, bottom_z)},',
        f'    "topCenter" : {point_expr(x, y, top_z)},',
        '    "radius" : outerRadius',
        "});",
        f'fCylinder(context, id + "{part.id}_inner", {{',
        f'    "bottomCenter" : {point_expr(x, y, bottom_z)},',
        f'    "topCenter" : {point_expr(x, y, top_z)},',
        '    "radius" : innerRadius',
        "});",
        f'opBoolean(context, id + "{part.id}_subtract", {{',
        f'    "tools" : qCreatedBy(id + "{part.id}_inner", EntityType.BODY),',
        f'    "targets" : qCreatedBy(id + "{part.id}_outer", EntityType.BODY),',
        '    "operationType" : BooleanOperationType.SUBTRACTION',
        "});",
        set_name_expr(
            entity_query=f'qCreatedBy(id + "{part.id}_outer", EntityType.BODY)',
            value=part.name,
        ),
    ]
    return "\n".join(lines)


def _render_tapered_cylinder(part: PartSpec) -> str:
    bottom_diameter = part.params["bottom_diameter_mm"]
    top_diameter = part.params["top_diameter_mm"]
    height = part.params["height_mm"]
    bottom_z = part.position.z_bottom_mm
    top_z = part.position.z_bottom_mm + height
    x = part.position.x_mm
    y = part.position.y_mm

    lines = [
        f"var bottomRadius = {millimeter_expr(bottom_diameter / 2)};",
        f"var topRadius = {millimeter_expr(top_diameter / 2)};",
        f'fCone(context, id + "{part.id}_cone", {{',
        f'    "bottomCenter" : {point_expr(x, y, bottom_z)},',
        f'    "topCenter" : {point_expr(x, y, top_z)},',
        '    "bottomRadius" : bottomRadius,',
        '    "topRadius" : topRadius',
        "});",
        set_name_expr(
            entity_query=f'qCreatedBy(id + "{part.id}_cone", EntityType.BODY)',
            value=part.name,
        ),
    ]
    return "\n".join(lines)


def _render_flange(part: PartSpec) -> str:
    flange_diameter = part.params["flange_diameter_mm"]
    flange_height = part.params["flange_height_mm"]
    shaft_diameter = part.params["shaft_diameter_mm"]
    shaft_height = part.params["shaft_height_mm"]
    union_id = f"{part.id}_union"
    flange_z = part.position.z_bottom_mm
    shaft_z = part.position.z_bottom_mm + flange_height
    x = part.position.x_mm
    y = part.position.y_mm

    lines = [
        f"var flangeRadius = {millimeter_expr(flange_diameter / 2)};",
        f"var shaftRadius = {millimeter_expr(shaft_diameter / 2)};",
        f'fCylinder(context, id + "{part.id}_flange", {{',
        f'    "bottomCenter" : {point_expr(x, y, flange_z)},',
        f'    "topCenter" : {point_expr(x, y, flange_z + flange_height)},',
        '    "radius" : flangeRadius',
        "});",
        f'fCylinder(context, id + "{part.id}_shaft", {{',
        f'    "bottomCenter" : {point_expr(x, y, shaft_z)},',
        f'    "topCenter" : {point_expr(x, y, shaft_z + shaft_height)},',
        '    "radius" : shaftRadius',
        "});",
        f'opBoolean(context, id + "{union_id}", {{',
        (
            f'    "tools" : qUnion([qCreatedBy(id + "{part.id}_flange", EntityType.BODY), '
            f'qCreatedBy(id + "{part.id}_shaft", EntityType.BODY)]),'
        ),
        '    "operationType" : BooleanOperationType.UNION',
        "});",
        set_name_expr(
            entity_query=f'qCreatedBy(id + "{part.id}_flange", EntityType.BODY)',
            value=part.name,
        ),
    ]
    return "\n".join(lines)


_RENDERERS: dict[PartShape, Renderer] = {
    "box": _render_box,
    "cylinder": _render_cylinder,
    "hollow_cylinder": _render_hollow_cylinder,
    "tapered_cylinder": _render_tapered_cylinder,
    "flange": _render_flange,
}
