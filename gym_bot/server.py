"""Local API server for config, auth status, and booking execution."""

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from auth_service import AuthService
from config import AppConfig
from runtime_paths import resolve_config_path
from task_service import TaskService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gym_server")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
            return
        if path == "/api/config":
            self._send_json({"ok": True, "data": AppConfig.load().to_dict()})
            return
        if path == "/api/auth/status":
            cfg = AppConfig.load()
            self._send_json({"ok": True, "data": AuthService(cfg).cookie_status()})
            return
        if path == "/api/tasks":
            cfg = AppConfig.load()
            try:
                limit = int(query.get("limit", ["20"])[0])
            except ValueError:
                limit = 20
            self._send_json({"ok": True, "data": TaskService(cfg).list_tasks(limit=limit)})
            return
        if path.startswith("/api/tasks/"):
            cfg = AppConfig.load()
            task_id = path.rsplit("/", 1)[-1]
            task = TaskService(cfg).get_task(task_id)
            if task is None:
                self._send_json({"ok": False, "error": "task not found"}, status=404)
                return
            self._send_json({"ok": True, "data": task})
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_json()
        if path == "/api/config":
            cfg = AppConfig.from_dict(body or {})
            cfg.save()
            self._send_json({"ok": True, "data": cfg.to_dict()})
            return
        if path == "/api/auth/login":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "auth.login",
                trigger_source="manual",
            )
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=200 if task.status == "succeeded" else 400,
            )
            return
        if path == "/api/auth/ensure-cookie":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "auth.ensure_cookie",
                trigger_source="manual",
            )
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=200 if task.status == "succeeded" else 400,
            )
            return
        if path == "/api/booking/query":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "booking.query",
                payload=body or {},
                trigger_source="manual",
            )
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=200 if task.status == "succeeded" else 400,
            )
            return
        if path == "/api/booking/run":
            cfg = AppConfig.load()
            task = TaskService(cfg).run(
                "booking.run",
                payload=body or {},
                trigger_source="manual",
            )
            self._send_json(
                {"ok": task.status == "succeeded", "data": task.to_dict()},
                status=200 if task.status == "succeeded" else 400,
            )
            return
        self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        if not raw:
            return None
        return json.loads(raw)

    def _send_json(self, payload, status: int = 200):
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
