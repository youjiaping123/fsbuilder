"""兼容层：合并逻辑已迁移到 `fs_builder.generation.merge`。"""

from __future__ import annotations

from .generation.merge import merge_featurescript

__all__ = ["merge_featurescript"]
