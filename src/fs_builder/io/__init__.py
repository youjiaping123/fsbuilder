"""I/O 与资源访问辅助模块。"""

from .artifacts import (
    ensure_output_dir,
    ensure_within_directory,
    featurescript_output_path,
    plan_output_path,
    safe_slug,
    write_text_artifact,
)
from .plans import load_plan_file, resolve_plan_output_path, write_plan_file
from .resources import load_prompt, strip_markdown_fences

__all__ = [
    "ensure_output_dir",
    "ensure_within_directory",
    "featurescript_output_path",
    "load_plan_file",
    "load_prompt",
    "plan_output_path",
    "resolve_plan_output_path",
    "safe_slug",
    "strip_markdown_fences",
    "write_plan_file",
    "write_text_artifact",
]
