"""分析模型调用适配层。"""

from __future__ import annotations

from collections.abc import Callable
from time import sleep
from typing import cast

import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from ..io.resources import load_prompt
from ..settings import Settings
from .errors import AnalysisEmptyResponseError, AnalysisRequestError
from .parsing import extract_stream_content, token_attempts

_EMPTY_CONTENT_RETRIES = 6
_EMPTY_CONTENT_RETRY_DELAY_SECONDS = 1.0

AnalysisRequester = Callable[..., object]


def request_analysis_content(
    *,
    requirement: str,
    settings: Settings,
    client: OpenAI | None = None,
    requester: AnalysisRequester | None = None,
) -> str:
    messages = cast(
        list[ChatCompletionMessageParam],
        [
            {"role": "system", "content": load_prompt("analyze.txt")},
            {"role": "user", "content": requirement},
        ],
    )
    max_token_attempts = token_attempts(settings.analyze_max_tokens)
    last_empty_tokens = max_token_attempts[-1]

    for max_tokens in max_token_attempts:
        for attempt_index in range(_EMPTY_CONTENT_RETRIES):
            response = _send_analysis_request(
                settings=settings,
                messages=messages,
                max_tokens=max_tokens,
                client=client,
                requester=requester,
            )
            content = extract_stream_content(response)
            if content.strip():
                return content
            last_empty_tokens = max_tokens
            if attempt_index < _EMPTY_CONTENT_RETRIES - 1:
                sleep(_EMPTY_CONTENT_RETRY_DELAY_SECONDS)

    raise AnalysisEmptyResponseError(
        "分析模型返回了空内容。"
        f" model={settings.analyze_model}, base_url={settings.base_url or 'default'},"
        f" 最后一次 max_tokens={last_empty_tokens}。"
        " 可尝试降低 ANALYZE_MAX_TOKENS 或切换兼容模型。"
    )


def _send_analysis_request(
    *,
    settings: Settings,
    messages: list[ChatCompletionMessageParam],
    max_tokens: int,
    client: OpenAI | None,
    requester: AnalysisRequester | None,
) -> object:
    try:
        if requester is not None:
            return requester(
                model=settings.analyze_model,
                max_tokens=max_tokens,
                messages=messages,
                stream=True,
            )
        if client is not None:
            return client.chat.completions.create(
                model=settings.analyze_model,
                max_tokens=max_tokens,
                messages=messages,
                stream=True,
            )
        if settings.base_url:
            return _post_chat_completion_raw(
                api_key=settings.require_api_key("分析需求"),
                base_url=settings.base_url,
                model=settings.analyze_model,
                max_tokens=max_tokens,
                messages=messages,
                timeout_seconds=settings.api_timeout_seconds,
            )
        sdk_client = OpenAI(
            api_key=settings.require_api_key("分析需求"),
            base_url=None,
            timeout=settings.api_timeout_seconds,
        )
        return sdk_client.chat.completions.create(
            model=settings.analyze_model,
            max_tokens=max_tokens,
            messages=messages,
            stream=True,
        )
    except AnalysisRequestError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AnalysisRequestError(
            "分析请求失败。"
            f" model={settings.analyze_model}, base_url={settings.base_url or 'default'}。"
            f" 详情：{exc}"
        ) from exc


def _post_chat_completion_raw(
    *,
    api_key: str,
    base_url: str,
    model: str,
    max_tokens: int,
    messages: list[ChatCompletionMessageParam],
    timeout_seconds: float,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=timeout_seconds) as http_client:
        with http_client.stream(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                preview = response.read().decode("utf-8", errors="replace")[:400]
                raise AnalysisRequestError(
                    f"分析接口返回 HTTP {response.status_code}，响应预览：{preview}"
                ) from exc

            content_type = response.headers.get("content-type", "")
            if "text/event-stream" not in content_type:
                return response.read().decode("utf-8", errors="replace")

            chunks: list[str] = []
            for line in response.iter_lines():
                if not line:
                    continue
                chunks.append(line)
                if line.strip() == "data: [DONE]":
                    break
            return "\n".join(chunks)
