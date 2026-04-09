"""兼容层：生成逻辑已迁移到 `fs_builder.generation`。"""

from __future__ import annotations

from .generation import (
    FeatureScriptGenerator,
    GenerationReport,
    PartResult,
    TemplateGenerator,
    build_generator,
    count_failed_parts,
)

__all__ = [
    "FeatureScriptGenerator",
    "GenerationReport",
    "PartResult",
    "TemplateGenerator",
    "build_generator",
    "count_failed_parts",
]
