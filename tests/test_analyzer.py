from __future__ import annotations

from dataclasses import dataclass

from fs_builder import analyzer
from fs_builder.errors import PlanValidationError
from fs_builder.models import AssemblyPlan
from fs_builder.settings import Settings


@dataclass
class _FakeMessage:
    content: str | None


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeResponse:
    choices: list[_FakeChoice]


class _FakeCompletions:
    def __init__(self, contents: list[str | None]) -> None:
        self.contents = list(contents)
        self.calls: list[int] = []

    def create(self, *, model, max_tokens, messages, stream=False):  # noqa: ANN001
        self.calls.append(max_tokens)
        content = self.contents.pop(0)
        return _FakeResponse(choices=[_FakeChoice(message=_FakeMessage(content=content))])


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(self, contents: list[str | None]) -> None:
        self.chat = _FakeChat(_FakeCompletions(contents))


class _FailingCompletions:
    def create(self, *, model, max_tokens, messages, stream=False):  # noqa: ANN001
        raise RuntimeError("network down")


class _FailingClient:
    def __init__(self) -> None:
        self.chat = _FakeChat(_FailingCompletions())


def _settings() -> Settings:
    return Settings.from_sources(
        api_key="sk-test",
        base_url="https://example.invalid/v1",
        analyze_model="gpt-test",
        analyze_max_tokens=8192,
        output_dir="output",
    )


def test_token_attempts_fall_back_to_provider_safe_values() -> None:
    assert analyzer._token_attempts(16384) == [16384, 2048, 1024]
    assert analyzer._token_attempts(2048) == [2048, 1024]


def test_request_analysis_content_retries_after_empty_response() -> None:
    fake_client = _FakeClient(["", "{\"assembly_name\":\"ok\"}"])
    settings = _settings()

    content = analyzer._request_analysis_content(
        client=fake_client,
        requirement="demo",
        settings=settings,
    )

    assert content == "{\"assembly_name\":\"ok\"}"
    assert fake_client.chat.completions.calls == [8192, 8192]


def test_request_analysis_content_wraps_provider_errors() -> None:
    settings = _settings()

    try:
        analyzer._request_analysis_content(
            client=_FailingClient(),
            requirement="demo",
            settings=settings,
        )
    except PlanValidationError as exc:
        assert "Analyzer request failed." in str(exc)
        assert "network down" in str(exc)
    else:
        raise AssertionError("Expected analyzer request failure")


def test_request_analysis_content_supports_raw_sse_requester() -> None:
    settings = _settings()

    content = analyzer._request_analysis_content(
        requirement="demo",
        settings=settings,
        requester=lambda **_: "\n".join(
            [
                'data: {"choices":[{"delta":{"content":"{"}}]}',
                'data: {"choices":[{"delta":{"content":"\\"assembly_name\\":\\"ok\\"}"}}]}',
                "data: [DONE]",
            ]
        ),
    )

    assert content == '{"assembly_name":"ok"}'


def test_extract_response_content_supports_string_payload() -> None:
    assert analyzer._extract_response_content("{\"assembly_name\":\"ok\"}") == "{\"assembly_name\":\"ok\"}"


def test_extract_response_content_supports_sse_payload() -> None:
    payload = "\n".join(
        [
            'data: {"choices":[{"delta":{"content":"{"}}]}',
            'data: {"choices":[{"delta":{"content":"\\"assembly_name\\":\\"ok\\"}"}}]}',
            "data: [DONE]",
        ]
    )
    assert analyzer._extract_response_content(payload) == '{"assembly_name":"ok"}'


def test_extract_stream_content_joins_stream_deltas() -> None:
    chunks = [
        {"choices": [{"delta": {"content": "{"}}]},
        {"choices": [{"delta": {"content": '"assembly_name":"ok"'}}]},
        {"choices": [{"delta": {"content": "}"}}]},
    ]

    assert analyzer._extract_stream_content(chunks) == '{"assembly_name":"ok"}'


def test_analyze_requirement_uses_retry_and_returns_plan(monkeypatch) -> None:
    fake_client = _FakeClient(
        [
            "",
            """
            {
              "assembly_name": "demo_fixture",
              "description": "Simple demo fixture.",
              "global_params": {
                "unit": "mm",
                "origin_description": "XY plane at bottom center of assembly, Z points up",
                "total_height_mm": 80,
                "total_width_mm": 120,
                "total_depth_mm": 90
              },
              "parts": [
                {
                  "id": "base_block",
                  "name": "Base Block",
                  "shape": "box",
                  "material_hint": "steel",
                  "params": {
                    "width_mm": 120,
                    "depth_mm": 90,
                    "height_mm": 20
                  },
                  "position": {
                    "x_mm": 0,
                    "y_mm": 0,
                    "z_bottom_mm": 0
                  },
                  "description": "Main support block."
                }
              ],
              "assembly_relations": []
            }
            """,
        ]
    )
    monkeypatch.setattr(analyzer, "OpenAI", lambda **kwargs: fake_client)
    settings = Settings(
        api_key="sk-test",
        base_url=None,
        api_timeout_seconds=30.0,
        analyze_model="gpt-test",
        analyze_max_tokens=8192,
        generate_model="gpt-test",
        concurrency=4,
        output_dir="output",
    )

    plan = analyzer.analyze_requirement("Design a simple block.", settings)

    assert isinstance(plan, AssemblyPlan)
    assert plan.assembly_name == "demo_fixture"
    assert fake_client.chat.completions.calls == [8192, 8192]


def test_analyze_requirement_falls_back_to_local_drawing_die_plan(monkeypatch) -> None:
    monkeypatch.setattr(
        analyzer,
        "_request_analysis_content",
        lambda **kwargs: (_ for _ in ()).throw(PlanValidationError("upstream empty")),
    )
    settings = Settings(
        api_key=None,
        base_url="https://example.invalid/v1",
        api_timeout_seconds=30.0,
        analyze_model="gpt-test",
        analyze_max_tokens=2048,
        generate_model="gpt-test",
        concurrency=4,
        output_dir="output",
    )

    plan = analyzer.analyze_requirement(
        "设计一个冷拉延模具（Cold Drawing Die），只建五个主件。上模座尺寸 200×200×40 mm，下模座尺寸 200×200×40 mm。"
        "压边圈外径 = 凹模外径 = 160 mm。凹模型腔直径 = 64 mm。凸模外径 = 60 mm，高度 80 mm。",
        settings,
    )

    assert plan.assembly_name == "drawing_die"
    assert len(plan.parts) == 5
    assert {part.id for part in plan.parts} == {
        "lower_die_seat",
        "drawing_die",
        "blank_holder",
        "upper_die_seat",
        "punch",
    }
