"""Local API server for config, auth status, and booking execution."""

import json
import logging
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from auth_service import AuthService
from config import AppConfig
from observability import (
    configure_logging,
    emit_event,
    read_recent_events,
    reset_context,
    request_id_var,
    set_request_context,
)
from runtime_paths import resolve_config_path
from task_service import TaskService


configure_logging("gym_server")
logger = logging.getLogger("gym_server")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request(self._do_get_inner)

    def do_POST(self):
        self._handle_request(self._do_post_inner)

    def _handle_request(self, handler):
        request_id = uuid.uuid4().hex[:12]
        started = time.time()
        token = set_request_context(request_id)
        status = 200
        path = urlparse(self.path).path
        emit_event("api.request.started", request_id=request_id, method=self.command, path=path)
        try:
            status = handler()
        except Exception as exc:
            status = 500
            logger.exception("request failed: %s", exc)
            emit_event(
                "api.request.error",
                level="error",
                request_id=request_id,
                method=self.command,
                path=path,
                status=500,
                error=str(exc),
            )
            self._send_json({"ok": False, "error": "internal server error", "request_id": request_id}, status=500)
        finally:
            emit_event(
                "api.request.finished",
                request_id=request_id,
                method=self.command,
                path=path,
                status=status,
                duration_ms=round((time.time() - started) * 1000, 2),
            )
            reset_context(token)

    def _do_get_inner(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/api/status":
            cfg = AppConfig.load()
            auth = AuthService(cfg)
            tasks = TaskService(cfg)
            self._send_json(
                {
                    "ok": True,
                    "data": {
                        "config_path": str(resolve_config_path()),
                        "auth": auth.cookie_status(),
                        "latest_task": tasks.latest_task(),
                    },
                }
            )
            return 200
        if path == "/api/config":
            self._send_json({"ok": True, "data": AppConfig.load().to_dict()})
            return 200
        if path == "/api/auth/status":
            cfg = AppConfig.load()
            self._send_json({"ok": True, "data": AuthService(cfg).cookie_status()})
            return 200
        if path == "/api/tasks":
            cfg = AppConfig.load()
            try:
                limit = int(query.get("limit", ["20"])[0])
            except ValueError:
                limit = 20
            self._send_json({"ok": True, "data": TaskService(cfg).list_tasks(limit=limit)})
            return 200
        if path.startswith("/api/tasks/"):
            cfg = AppConfig.load()
            task_id = path.rsplit("/", 1)[-1]
            task = TaskService(cfg).get_task(task_id)
            if task is None:
                self._send_json({"ok": False, "error": "task not found"}, status=404)
                return 404
            self._send_json({"ok": True, "data": task})
            return 200
        if path == "/api/observability/events":
            try:
                limit = int(query.get("limit", ["200"])[0])
            except ValueError:
                limit = 200
            self._send_json({"ok": True, "data": read_recent_events(limit=limit)})
            return 200
        self.send_error(404)
        return 404

    def _do_post_inner(self):
        path = urlparse(self.path).path
        body = self._read_json()
        if path == "/api/config":
            cfg = AppConfig.from_dict(body or {})
            cfg.save()
            self._send_json({"ok": True, "data": cfg.to_dict()})
            return 200
        if path == "/api/auth/login":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "auth.login",
                trigger_source="manual",
            )
            status = 200 if task.status == "succeeded" else 400
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=status,
            )
            return status
        if path == "/api/auth/ensure-cookie":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "auth.ensure_cookie",
                trigger_source="manual",
            )
            status = 200 if task.status == "succeeded" else 400
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=status,
            )
            return status
        if path == "/api/booking/query":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "booking.query",
                payload=body or {},
                trigger_source="manual",
            )
            status = 200 if task.status == "succeeded" else 400
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=status,
            )
            return status
        if path == "/api/booking/run":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "booking.run",
                payload=body or {},
                trigger_source="manual",
            )
            status = 200 if task.status == "succeeded" else 400
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=status,
            )
            return status
        self.send_error(404)
        return 404

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        if not raw:
            return None
        return json.loads(raw)

    def _send_json(self, payload, status: int = 200):
        if isinstance(payload, dict) and "request_id" not in payload:
            rid = request_id_var.get()
            if rid:
                payload = {**payload, "request_id": rid}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())


def serve(host: str = "127.0.0.1", port: int = 8787):
    server = ThreadingHTTPServer((host, port), Handler)
    logger.info("Server listening on http://%s:%s", host, port)
    server.serve_forever()


if __name__ == "__main__":
    serve()
