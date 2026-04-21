"""Tests for server.py request handling and observability endpoints."""

import io
import json

from observability import reset_context, set_request_context
from server import Handler


class TestHandlerSendJson:
    def test_send_json_includes_request_id_from_context(self):
        h = Handler.__new__(Handler)
        h.wfile = io.BytesIO()
        h.send_response = lambda *_args, **_kwargs: None
        h.send_header = lambda *_args, **_kwargs: None
        h.end_headers = lambda *_args, **_kwargs: None

        token = set_request_context("req-123")
        try:
            h._send_json({"ok": True})
        finally:
            reset_context(token)

        payload = json.loads(h.wfile.getvalue().decode("utf-8"))
        assert payload["ok"] is True
        assert payload["request_id"] == "req-123"


class TestHandlerGetInner:
    def test_get_observability_events_endpoint(self, monkeypatch):
        h = Handler.__new__(Handler)
        h.path = "/api/observability/events?limit=2"
        captured: dict = {}

        monkeypatch.setattr("server.read_recent_events", lambda limit=200: [{"event": "e1"}, {"event": "e2"}])
        h._send_json = lambda payload, status=200: captured.update({"payload": payload, "status": status})

        status = h._do_get_inner()
        assert status == 200
        assert captured["status"] == 200
        assert captured["payload"]["ok"] is True
        assert captured["payload"]["data"] == [{"event": "e1"}, {"event": "e2"}]

    def test_handle_request_exception_returns_500(self):
        h = Handler.__new__(Handler)
        h.path = "/api/boom"
        h.command = "GET"
        captured: dict = {}
        h._send_json = lambda payload, status=200: captured.update({"payload": payload, "status": status})

        h._handle_request(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

        assert captured["status"] == 500
        assert captured["payload"]["ok"] is False
        assert captured["payload"]["error"] == "internal server error"
        assert captured["payload"]["request_id"]
