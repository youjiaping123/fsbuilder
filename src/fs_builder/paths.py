"""兼容层：路径辅助逻辑已迁移到 `fs_builder.io.artifacts`。"""

from __future__ import annotations

from .io.artifacts import (
    ensure_output_dir,
    ensure_within_directory,
    featurescript_output_path,
    plan_output_path,
    safe_slug,
)

__all__ = [
    "ensure_output_dir",
    "ensure_within_directory",
    "featurescript_output_path",
    "plan_output_path",
    "safe_slug",
]
