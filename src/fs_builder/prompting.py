"""Prompt resource loading and model-output cleanup."""

from __future__ import annotations

from importlib.resources import files


def load_prompt(name: str) -> str:
    return files("fs_builder.prompts").joinpath(name).read_text(encoding="utf-8")


def strip_markdown_fences(raw: str) -> str:
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner: list[str] = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                inner.append(line)
        return "\n".join(inner)
    return raw
