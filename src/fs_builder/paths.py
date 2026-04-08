"""Safe path helpers for generated artifacts."""

from __future__ import annotations

import re
from pathlib import Path

from .errors import ConfigError


_NON_SLUG_RE = re.compile(r"[^a-z0-9_]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def safe_slug(value: str, *, default: str = "generated") -> str:
    candidate = value.strip().lower().replace("-", "_")
    candidate = _NON_SLUG_RE.sub("_", candidate)
    candidate = _MULTI_UNDERSCORE_RE.sub("_", candidate).strip("_")
    if not candidate:
        candidate = default
    if not candidate[0].isalpha():
        candidate = f"{default}_{candidate}"
    return candidate[:80]


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_within_directory(path: Path, directory: Path) -> Path:
    resolved_dir = directory.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_dir)
    except ValueError as exc:
        raise ConfigError(
            f"Resolved path '{resolved_path}' escapes output directory '{resolved_dir}'."
        ) from exc
    return resolved_path


def plan_output_path(output_dir: Path, assembly_name: str) -> Path:
    safe_name = safe_slug(assembly_name)
    path = ensure_output_dir(output_dir) / f"{safe_name}_plan.json"
    ensure_within_directory(path, output_dir)
    return path


def featurescript_output_path(output_dir: Path, assembly_name: str) -> Path:
    safe_name = safe_slug(assembly_name)
    path = ensure_output_dir(output_dir) / f"{safe_name}.fs"
    ensure_within_directory(path, output_dir)
    return path
