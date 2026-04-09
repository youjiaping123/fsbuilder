"""强类型 plan schema。"""

from __future__ import annotations

from math import isfinite
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .errors import PlanValidationError

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
PartShape = Literal["box", "cylinder", "hollow_cylinder", "tapered_cylinder", "flange"]
MaterialHint = Literal["steel", "cast_iron", "carbide", "general"]
RelationType = Literal["stacked_on", "press_fit_into", "bolted_to", "guided_by"]

_SHAPE_PARAM_KEYS: dict[str, tuple[str, ...]] = {
    "box": ("width_mm", "depth_mm", "height_mm"),
    "cylinder": ("diameter_mm", "height_mm"),
    "hollow_cylinder": ("outer_diameter_mm", "inner_diameter_mm", "height_mm"),
    "tapered_cylinder": ("top_diameter_mm", "bottom_diameter_mm", "height_mm"),
    "flange": (
        "flange_diameter_mm",
        "flange_height_mm",
        "shaft_diameter_mm",
        "shaft_height_mm",
    ),
}


class StrictModel(BaseModel):
    """统一禁止额外字段，并在字符串字段上自动裁剪空白。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GlobalParams(StrictModel):
    unit: Literal["mm"]
    origin_description: str = Field(min_length=1)
    total_height_mm: float = Field(gt=0)
    total_width_mm: float = Field(gt=0)
    total_depth_mm: float = Field(gt=0)


class PositionSpec(StrictModel):
    x_mm: float
    y_mm: float
    z_bottom_mm: float

    @field_validator("x_mm", "y_mm", "z_bottom_mm")
    @classmethod
    def finite_coordinates(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("Position values must be finite numbers.")
        return value


class PartSpec(StrictModel):
    id: Identifier
    name: str = Field(min_length=1)
    shape: PartShape
    material_hint: MaterialHint
    params: dict[str, float]
    position: PositionSpec
    description: str = Field(min_length=1)

    @field_validator("params")
    @classmethod
    def params_not_empty(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("params must not be empty.")
        for key, numeric_value in value.items():
            if not isfinite(float(numeric_value)):
                raise ValueError(f"Parameter '{key}' must be a finite number.")
        return value

    @model_validator(mode="after")
    def validate_shape_params(self) -> PartSpec:
        expected_keys = set(_SHAPE_PARAM_KEYS[self.shape])
        actual_keys = set(self.params)
        if actual_keys != expected_keys:
            raise ValueError(
                f"Shape '{self.shape}' expects params {sorted(expected_keys)}, "
                f"got {sorted(actual_keys)}."
            )

        for key in expected_keys:
            if self.params[key] <= 0:
                raise ValueError(f"Parameter '{key}' must be > 0.")

        if self.shape == "hollow_cylinder":
            if self.params["outer_diameter_mm"] <= self.params["inner_diameter_mm"]:
                raise ValueError("outer_diameter_mm must be greater than inner_diameter_mm.")

        if self.shape == "flange":
            if self.params["flange_diameter_mm"] <= self.params["shaft_diameter_mm"]:
                raise ValueError("flange_diameter_mm must be greater than shaft_diameter_mm.")

        return self


class AssemblyRelation(StrictModel):
    child_id: Identifier
    parent_id: Identifier
    relation: RelationType

    @model_validator(mode="after")
    def not_self_reference(self) -> AssemblyRelation:
        if self.child_id == self.parent_id:
            raise ValueError("child_id and parent_id must be different.")
        return self


class AssemblyPlan(StrictModel):
    assembly_name: Identifier
    description: str = Field(min_length=1)
    global_params: GlobalParams
    parts: list[PartSpec] = Field(min_length=1)
    assembly_relations: list[AssemblyRelation]

    @model_validator(mode="after")
    def validate_cross_references(self) -> AssemblyPlan:
        part_ids = [part.id for part in self.parts]
        duplicate_ids = _find_duplicates(part_ids)
        if duplicate_ids:
            raise ValueError(f"Duplicate part ids: {sorted(duplicate_ids)}")

        known_ids = set(part_ids)
        for relation in self.assembly_relations:
            if relation.child_id not in known_ids:
                raise ValueError(f"Relation child_id '{relation.child_id}' does not exist.")
            if relation.parent_id not in known_ids:
                raise ValueError(f"Relation parent_id '{relation.parent_id}' does not exist.")
        return self

    def to_pretty_json(self) -> str:
        return self.model_dump_json(indent=2)


def validate_plan_data(data: object) -> AssemblyPlan:
    try:
        return AssemblyPlan.model_validate(data)
    except ValidationError as exc:
        raise PlanValidationError(str(exc)) from exc


def _find_duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates
