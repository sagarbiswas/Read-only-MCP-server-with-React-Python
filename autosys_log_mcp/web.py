"""HTTP API and static-file host for the AutoSys log search UI."""

from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from autosys_log_mcp.server import (
    DEFAULT_LOG_ROOT,
    MAX_RESULT_LIMIT,
    search_log_files,
)

WEB_ROOT = Path(
    os.environ.get(
        "AUTOSYS_WEB_ROOT",
        str(Path(__file__).resolve().parent.parent / "frontend" / "dist"),
    )
)
MAX_REQUEST_BYTES = 64 * 1024


class SearchRequestHandler(BaseHTTPRequestHandler):
    server_version = "AutoSysLogSearch/0.1"

    def do_GET(self) -> None:
        request_path = urlsplit(self.path).path
        if request_path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        self._serve_static_file(request_path)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/search":
            self._send_json(404, {"error": "Endpoint not found"})
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json(411, {"error": "Content-Length is required"})
            return
        try:
            request_size = int(content_length)
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if request_size < 0 or request_size > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Request body is too large"})
            return

        try:
            payload = json.loads(self.rfile.read(request_size))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Request body must be a JSON object"})
            return

        try:
            filters = self._parse_search_request(payload)
            result = search_log_files(
                os.environ.get("AUTOSYS_LOG_ROOT", DEFAULT_LOG_ROOT),
                **filters,
            )
        except (ValueError, FileNotFoundError) as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except PermissionError as exc:
            self._send_json(403, {"error": str(exc)})
            return
        except OSError as exc:
            self._send_json(500, {"error": f"Could not read AutoSys logs: {exc}"})
            return
        self._send_json(200, result)

    @staticmethod
    def _parse_search_request(payload: dict[str, Any]) -> dict[str, Any]:
        optional_strings = ("date", "job_name", "search_text")
        filters: dict[str, Any] = {}
        for key in optional_strings:
            value = payload.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
            value = value.strip() if value is not None else None
            if not value:
                value = None
            filters[key] = value

        case_sensitive = payload.get("case_sensitive", False)
        if not isinstance(case_sensitive, bool):
            raise ValueError("case_sensitive must be a boolean")

        max_results = payload.get("max_results", 100)
        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise ValueError("max_results must be an integer")
        if not 1 <= max_results <= MAX_RESULT_LIMIT:
            raise ValueError(f"max_results must be between 1 and {MAX_RESULT_LIMIT}")

        filters["case_sensitive"] = case_sensitive
        filters["max_results"] = max_results
        return filters

    def _serve_static_file(self, request_path: str) -> None:
        if not WEB_ROOT.is_dir():
            self._send_json(
                503,
                {"error": "UI build not found; run `npm run build` in frontend"},
            )
            return

        relative_path = unquote(request_path).lstrip("/") or "index.html"
        file_path = (WEB_ROOT / relative_path).resolve()
        if not file_path.is_relative_to(WEB_ROOT.resolve()) or not file_path.is_file():
            self._send_json(404, {"error": "File not found"})
            return

        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        super().log_message(format, *args)


def main() -> None:
    host = os.environ.get("AUTOSYS_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("AUTOSYS_WEB_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), SearchRequestHandler)
    print(f"AutoSys log UI/API listening at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
