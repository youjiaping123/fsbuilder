"""Web UI HTTP 服务。"""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import urlparse

from ..errors import FSBuilderError
from ..settings import Settings
from .api import WebUIService


class WebUIHTTPServer(ThreadingHTTPServer):
    """带有应用服务实例的 HTTP 服务器。"""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        service: WebUIService,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.service = service


class WebUIRequestHandler(BaseHTTPRequestHandler):
    """静态资源与 API 路由处理。"""

    server: WebUIHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._serve_static_file("index.html", "text/html; charset=utf-8")
            return
        if path == "/assets/styles.css":
            self._serve_static_file("styles.css", "text/css; charset=utf-8")
            return
        if path == "/assets/app.js":
            self._serve_static_file("app.js", "application/javascript; charset=utf-8")
            return
        if path in {"/assets/favicon.svg", "/favicon.ico"}:
            self._serve_static_file("favicon.svg", "image/svg+xml")
            return
        if path == "/api/state":
            self._write_json(HTTPStatus.OK, self.server.service.get_state())
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "未找到请求的资源。"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json_body()
            if path == "/api/analyze":
                response = self.server.service.analyze(
                    str(payload.get("requirement", "")),
                    persist=bool(payload.get("persist", False)),
                )
                self._write_json(HTTPStatus.OK, response)
                return
            if path == "/api/generate":
                response = self.server.service.generate(
                    payload.get("plan"),
                    persist=bool(payload.get("persist", False)),
                )
                self._write_json(HTTPStatus.OK, response)
                return
            if path == "/api/build":
                response = self.server.service.build(
                    str(payload.get("requirement", "")),
                    plan_data=payload.get("plan"),
                    persist=bool(payload.get("persist", True)),
                )
                self._write_json(HTTPStatus.OK, response)
                return
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "未找到请求的 API。"})
        except FSBuilderError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except json.JSONDecodeError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": f"请求体不是合法 JSON：{exc}"})
        except Exception as exc:  # noqa: BLE001
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"服务内部错误：{exc}"})

    def log_message(self, format: str, *args: object) -> None:
        """静默访问日志，避免污染 CLI 输出。"""
        return None

    def _serve_static_file(self, name: str, content_type: str) -> None:
        asset = files("fs_builder.webui").joinpath("static", name)
        content = asset.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_json_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return {}
        length = int(raw_length)
        if length <= 0:
            return {}
        raw_body = self.rfile.read(length).decode("utf-8")
        parsed = json.loads(raw_body)
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("顶层必须是对象", raw_body, 0)
        return parsed

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_web_ui_server(settings: Settings, *, host: str, port: int) -> WebUIHTTPServer:
    return WebUIHTTPServer((host, port), WebUIRequestHandler, WebUIService(settings))


def serve_web_ui(settings: Settings, *, host: str = "127.0.0.1", port: int = 8000) -> None:
    with create_web_ui_server(settings, host=host, port=port) as server:
        server.serve_forever()
