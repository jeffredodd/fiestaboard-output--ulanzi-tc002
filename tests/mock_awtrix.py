"""A stand-in Ulanzi TC002 running AWTRIX NG on loopback, for tests.

It answers the three routes the plugin uses the way the AWTRIX NG HTTP API
documents them, records every request, and can misbehave on purpose:

- ``GET /api/v1/device``: the device state (``boardType``, ``uid``,
  ``uptimeSeconds``, ``currentApp``, ...);
- ``PUT /api/v1/apps/pushed/{name}``: stores the app (it joins the rotation);
- ``PUT /api/v1/apps/active``: makes a stored app current, ``404`` otherwise.

``mode``: ``"ok"`` (default), ``"http_500"``, ``"garbage"`` (200, not JSON),
``"other_json"`` (200, JSON that is not AWTRIX NG), ``"hang"`` (never
answers, until :meth:`stop`). ``fail_paths`` makes requests whose path starts
with one of them answer 500. ``board_type`` is what ``boardType`` says.
``password`` set makes every route answer 401 without that Basic Auth.
:meth:`restart` drops every pushed app and starts the uptime again.

``on_request`` (``fn(method, path, body, index)``) runs before the answer, so
a test can fire a cancel token after the k-th push.

Only the standard library; binds 127.0.0.1 on a free port.
"""

from __future__ import annotations

import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

PUSHED = "/api/v1/apps/pushed/"
ACTIVE = "/api/v1/apps/active"
DEVICE = "/api/v1/device"


class MockAwtrix:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, Any]] = []
        self.mode = "ok"
        self.fail_paths: tuple[str, ...] = ()
        self.board_type = "tc002"
        self.password: str | None = None
        self.on_request: Callable[[str, str, Any, int], None] | None = None
        #: Pushed apps by name (as stored, case kept) -> last body.
        self.apps: dict[str, Any] = {}
        self.current_app = "Time"
        self._booted = time.monotonic()
        self.uptime_offset = 1000.0
        self._release = threading.Event()
        self._lock = threading.Lock()
        mock = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # quiet
                pass

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = {"_unparsed": raw.decode("latin-1")}
                status, answer = mock._answer(self.command, self.path, body, self.headers.get("Authorization"))
                if status is None:
                    mock._release.wait(30)
                    return
                payload = answer if isinstance(answer, bytes) else json.dumps(answer).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_PUT = do_POST = do_DELETE = _handle  # noqa: N815 - http.server API

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    # --- lifecycle -----------------------------------------------------------------------

    def start(self) -> MockAwtrix:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._release.set()
        self.server.shutdown()
        self.server.server_close()

    @property
    def host(self) -> str:
        host, port = self.server.server_address[:2]
        return f"{host}:{port}"

    def restart(self) -> None:
        """A power cycle: pushed apps gone, uptime from zero, the clock's own app current."""
        with self._lock:
            self.apps = {}
            self.current_app = "Time"
            self._booted = time.monotonic()
            self.uptime_offset = 0.0

    # --- what the clock saw ----------------------------------------------------------------

    def uptime(self) -> int:
        return int(self.uptime_offset + time.monotonic() - self._booted)

    def calls(self) -> list[tuple[str, str]]:
        return [(method, path) for method, path, _ in self.requests]

    def pushes(self) -> list[Any]:
        return [body for method, path, body in self.requests if method == "PUT" and path.startswith(PUSHED)]

    def switches(self) -> list[Any]:
        return [body for method, path, body in self.requests if method == "PUT" and path == ACTIVE]

    @staticmethod
    def bitmap(body: Any) -> bytes:
        """The RGB888 one push draws."""
        command = body["layout"]["regions"][0]["draw"][0]
        assert command[0] == "bitmap"
        return base64.b64decode(command[5])

    def clear(self) -> None:
        with self._lock:
            self.requests = []

    # --- behaviour -------------------------------------------------------------------------

    def _answer(self, method: str, path: str, body: Any, authorization: str | None) -> tuple[int | None, Any]:
        with self._lock:
            index = len(self.requests)
            self.requests.append((method, path, body))
        if self.on_request is not None:
            self.on_request(method, path, body, index)
        if self.mode == "hang":
            return None, None
        if self.password is not None:
            expected = "Basic " + base64.b64encode(f"admin:{self.password}".encode()).decode()
            if authorization != expected:
                return 401, {"error": {"code": "unauthorized", "message": "authentication required"}}
        if self.mode == "http_500" or any(path.startswith(p) for p in self.fail_paths):
            return 500, {"error": {"code": "internalError", "message": "internal"}}
        if self.mode == "garbage":
            return 200, b"<html>not a clock</html>"
        if self.mode == "other_json":
            return 200, {"status": "some other device"}
        if method == "GET" and path == DEVICE:
            return 200, {
                "version": "1.2.2",
                "uid": "a4cf12ab34cd",
                "boardType": self.board_type,
                "hostname": "awtrixng-ab34cd",
                "uptimeSeconds": self.uptime(),
                "currentApp": self.current_app,
            }
        if method == "PUT" and path.startswith(PUSHED):
            if not isinstance(body, dict) or not body:
                return 422, {"error": {"code": "validationFailed", "message": "a JSON body is required"}}
            with self._lock:
                self.apps[path[len(PUSHED) :]] = body
            return 200, {"ok": True}
        if method == "PUT" and path == ACTIVE:
            name = (body or {}).get("name", "")
            match = next((app for app in self.apps if app.lower() == str(name).lower()), None)
            if match is None:
                return 404, {"error": {"code": "notFound", "message": "app not found"}}
            self.current_app = match
            return 200, {"ok": True}
        return 404, {"error": {"code": "notFound", "message": "unknown route"}}
