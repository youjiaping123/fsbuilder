from __future__ import annotations

import os
from pathlib import Path

import pytest

from fs_builder.errors import ConfigError
from fs_builder.settings import Settings, load_project_env


def test_load_project_env_respects_existing_environment(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=sk-file\nANALYZE_MODEL=file-model\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANALYZE_MODEL", "env-model")

    loaded = load_project_env()

    assert loaded == env_path
    assert os.environ["OPENAI_API_KEY"] == "sk-file"
    assert os.environ["ANALYZE_MODEL"] == "env-model"


def test_from_sources_prefers_explicit_values_over_environment() -> None:
    settings = Settings.from_sources(
        api_key="sk-explicit",
        base_url="https://override.invalid/v1",
        api_timeout_seconds=12.0,
        analyze_model="gpt-explicit",
        analyze_max_tokens=4096,
        output_dir="artifacts",
        environ={
            "OPENAI_API_KEY": "sk-env",
            "OPENAI_BASE_URL": "https://env.invalid/v1",
            "OPENAI_TIMEOUT_SECONDS": "30",
            "ANALYZE_MODEL": "gpt-env",
            "ANALYZE_MAX_TOKENS": "2048",
        },
    )

    assert settings.api_key == "sk-explicit"
    assert settings.base_url == "https://override.invalid/v1"
    assert settings.api_timeout_seconds == 12.0
    assert settings.analyze_model == "gpt-explicit"
    assert settings.analyze_max_tokens == 4096
    assert settings.output_dir == Path("artifacts")


def test_from_sources_rejects_invalid_timeout() -> None:
    with pytest.raises(ConfigError, match="OPENAI_TIMEOUT_SECONDS"):
        Settings.from_sources(api_timeout_seconds=0, output_dir="output")


def test_from_sources_rejects_invalid_analyze_max_tokens() -> None:
    with pytest.raises(ConfigError, match="ANALYZE_MAX_TOKENS"):
        Settings.from_sources(analyze_max_tokens=0, output_dir="output")
