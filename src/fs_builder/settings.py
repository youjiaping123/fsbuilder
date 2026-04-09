"""运行时配置与环境变量解析。"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from .errors import ConfigError
from .io.artifacts import featurescript_output_path, plan_output_path

DEFAULT_ANALYZE_MODEL = "gpt-4o"
DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_ANALYZE_MAX_TOKENS = 2048
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0


def load_project_env() -> Path | None:
    """显式加载最近的 `.env`，但不覆盖已经存在的环境变量。"""
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path, override=False)
        return Path(env_path)
    return None


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str | None
    api_timeout_seconds: float
    analyze_model: str
    analyze_max_tokens: int
    output_dir: Path

    @classmethod
    def from_sources(
        cls,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        api_timeout_seconds: float | None = None,
        analyze_model: str | None = None,
        analyze_max_tokens: int | None = None,
        output_dir: Path | str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> Settings:
        """只做值解析，不主动加载 `.env`，避免构造时产生隐式副作用。"""
        env = dict(os.environ if environ is None else environ)

        resolved_analyze_max_tokens = (
            analyze_max_tokens
            if analyze_max_tokens is not None
            else int(env.get("ANALYZE_MAX_TOKENS", DEFAULT_ANALYZE_MAX_TOKENS))
        )
        if resolved_analyze_max_tokens < 1:
            raise ConfigError("ANALYZE_MAX_TOKENS 必须大于等于 1。")
        resolved_api_timeout_seconds = (
            api_timeout_seconds
            if api_timeout_seconds is not None
            else float(env.get("OPENAI_TIMEOUT_SECONDS", DEFAULT_OPENAI_TIMEOUT_SECONDS))
        )
        if resolved_api_timeout_seconds <= 0:
            raise ConfigError("OPENAI_TIMEOUT_SECONDS 必须大于 0。")

        env_base_url = env.get("OPENAI_BASE_URL") or None
        return cls(
            api_key=api_key if api_key is not None else (env.get("OPENAI_API_KEY") or None),
            base_url=base_url if base_url is not None else env_base_url,
            api_timeout_seconds=float(resolved_api_timeout_seconds),
            analyze_model=(
                analyze_model
                if analyze_model is not None
                else env.get("ANALYZE_MODEL", DEFAULT_ANALYZE_MODEL)
            ),
            analyze_max_tokens=resolved_analyze_max_tokens,
            output_dir=Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR,
        )

    def require_api_key(self, action: str) -> str:
        if not self.api_key:
            raise ConfigError(
                f"执行 `{action}` 需要 OPENAI_API_KEY。"
                " 请在 `.env` 中设置，或通过 `--api-key` 传入。"
            )
        return self.api_key

    def plan_output_path(self, assembly_name: str) -> Path:
        return plan_output_path(self.output_dir, assembly_name)

    def featurescript_output_path(self, assembly_name: str) -> Path:
        return featurescript_output_path(self.output_dir, assembly_name)
