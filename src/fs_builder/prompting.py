"""兼容层：资源读取已迁移到 `fs_builder.io.resources`。"""

from __future__ import annotations

from .io.resources import load_prompt, strip_markdown_fences

__all__ = ["load_prompt", "strip_markdown_fences"]
