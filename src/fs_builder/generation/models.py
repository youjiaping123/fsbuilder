"""生成结果模型。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

PartErrorKind = Literal["render_error", "system_error"]


@dataclass(frozen=True)
class PartResult:
    part_id: str
    part_name: str
    code: str
    error: str | None = None
    error_kind: PartErrorKind | None = None

    @classmethod
    def success(cls, *, part_id: str, part_name: str, code: str) -> PartResult:
        return cls(part_id=part_id, part_name=part_name, code=code)

    @classmethod
    def failure(
        cls,
        *,
        part_id: str,
        part_name: str,
        error: str,
        error_kind: PartErrorKind,
    ) -> PartResult:
        return cls(
            part_id=part_id,
            part_name=part_name,
            code="",
            error=error,
            error_kind=error_kind,
        )


@dataclass(frozen=True)
class GenerationReport:
    merged_script: str
    part_results: list[PartResult]
    generator_name: str = "template"

    @property
    def total_parts(self) -> int:
        return len(self.part_results)

    @property
    def failed_parts(self) -> int:
        return count_failed_parts(self.part_results)

    @property
    def succeeded_parts(self) -> int:
        return self.total_parts - self.failed_parts


def count_failed_parts(results: Sequence[PartResult]) -> int:
    return sum(1 for result in results if result.error)
