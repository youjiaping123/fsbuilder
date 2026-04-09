"""Runtime settings and environment loading."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from .errors import ConfigError


DEFAULT_ANALYZE_MODEL = "gpt-4o"
DEFAULT_GENERATE_MODEL = "gpt-4o-mini"
DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_ANALYZE_MAX_TOKENS = 2048
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0


def load_project_env() -> None:
    """Load the nearest .env file without overriding explicit environment vars."""
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path, override=False)


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str | None
    api_timeout_seconds: float
    analyze_model: str
    analyze_max_tokens: int
    generate_model: str
    concurrency: int
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
        generate_model: str | None = None,
        concurrency: int | None = None,
        output_dir: Path | str | None = None,
    ) -> "Settings":
        load_project_env()
        resolved_concurrency = concurrency or 4
        if resolved_concurrency < 1:
            raise ConfigError("Concurrency must be at least 1.")
        resolved_analyze_max_tokens = analyze_max_tokens or int(
            os.environ.get("ANALYZE_MAX_TOKENS", DEFAULT_ANALYZE_MAX_TOKENS)
        )
        if resolved_analyze_max_tokens < 1:
            raise ConfigError("ANALYZE_MAX_TOKENS must be at least 1.")
        resolved_api_timeout_seconds = api_timeout_seconds or float(
            os.environ.get("OPENAI_TIMEOUT_SECONDS", DEFAULT_OPENAI_TIMEOUT_SECONDS)
        )
        if resolved_api_timeout_seconds <= 0:
            raise ConfigError("OPENAI_TIMEOUT_SECONDS must be greater than 0.")

        env_base_url = os.environ.get("OPENAI_BASE_URL") or None
        return cls(
            api_key=api_key or os.environ.get("OPENAI_API_KEY") or None,
            base_url=base_url or env_base_url,
            api_timeout_seconds=resolved_api_timeout_seconds,
            analyze_model=analyze_model or os.environ.get("ANALYZE_MODEL", DEFAULT_ANALYZE_MODEL),
            analyze_max_tokens=resolved_analyze_max_tokens,
            generate_model=generate_model or os.environ.get(
                "GENERATE_MODEL",
                DEFAULT_GENERATE_MODEL,
            ),
            concurrency=resolved_concurrency,
            output_dir=Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR,
        )

    def require_api_key(self, action: str) -> str:
        if not self.api_key:
            raise ConfigError(
                f"OPENAI_API_KEY is required to {action}. "
                "Set it in .env or pass --api-key."
            )
        return self.api_key
