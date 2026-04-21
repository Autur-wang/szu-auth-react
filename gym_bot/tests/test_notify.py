"""Tests for notify.py — webhook notification."""

import responses
import pytest

import notify


class TestNotifySend:
    """notify.send() webhook delivery."""

    def test_empty_url_skips_silently(self):
        # Should not raise
        notify.send("", "test message")
        notify.send(None, "test message")

    @responses.activate
    def test_successful_send(self):
        responses.post("https://hook.example.com/webhook", json={"ok": True})

        notify.send("https://hook.example.com/webhook", "booking success")

        assert len(responses.calls) == 1
        body = responses.calls[0].request.body
        assert b"booking success" in body

    @responses.activate
    def test_send_payload_format(self):
        responses.post("https://hook.example.com/webhook", json={"ok": True})

        notify.send("https://hook.example.com/webhook", "hello")

        import json
        payload = json.loads(responses.calls[0].request.body)
        assert payload["msg_type"] == "text"
        assert payload["content"]["text"] == "hello"

    @responses.activate
    def test_server_error_does_not_raise(self):
        responses.post("https://hook.example.com/webhook", status=500, body="error")

        # Should log warning but not raise
        notify.send("https://hook.example.com/webhook", "test")

    @responses.activate
    def test_network_error_does_not_raise(self):
        responses.post(
            "https://hook.example.com/webhook",
            body=ConnectionError("refused"),
        )

        # Should not raise
        notify.send("https://hook.example.com/webhook", "test")

    @responses.activate
    def test_unicode_message(self):
        import json
        responses.post("https://hook.example.com/webhook", json={"ok": True})

        notify.send("https://hook.example.com/webhook", "预约成功 羽毛球1号 18:00-19:00")

        raw = responses.calls[0].request.body
        payload = json.loads(raw)
        assert "预约成功" in payload["content"]["text"]
        assert "羽毛球1号" in payload["content"]["text"]
