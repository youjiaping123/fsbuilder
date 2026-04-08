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


def load_project_env() -> None:
    """Load the nearest .env file without overriding explicit environment vars."""
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path, override=False)


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str | None
    analyze_model: str
    generate_model: str
    concurrency: int
    output_dir: Path

    @classmethod
    def from_sources(
        cls,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        analyze_model: str | None = None,
        generate_model: str | None = None,
        concurrency: int | None = None,
        output_dir: Path | str | None = None,
    ) -> "Settings":
        load_project_env()
        resolved_concurrency = concurrency or 4
        if resolved_concurrency < 1:
            raise ConfigError("Concurrency must be at least 1.")

        env_base_url = os.environ.get("OPENAI_BASE_URL") or None
        return cls(
            api_key=api_key or os.environ.get("OPENAI_API_KEY") or None,
            base_url=base_url or env_base_url,
            analyze_model=analyze_model or os.environ.get("ANALYZE_MODEL", DEFAULT_ANALYZE_MODEL),
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
