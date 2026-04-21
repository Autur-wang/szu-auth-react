"""Tests for cookie_server.py — HTTP endpoints."""

import json
import threading
import time
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from cookie_server import Handler, save_cookies, verify_and_supplement, COOKIE_FILE


@pytest.fixture(autouse=True)
def tmp_cookie_file(tmp_path, monkeypatch):
    """Redirect COOKIE_FILE to tmp dir."""
    fake_path = tmp_path / ".cookie_cache.json"
    monkeypatch.setattr("cookie_server.COOKIE_FILE", fake_path)
    return fake_path


class TestSaveCookies:
    """save_cookies() file persistence."""

    def test_saves_to_file(self, tmp_cookie_file):
        cookies = [{"name": "a", "value": "1", "domain": ".szu.edu.cn", "path": "/"}]
        save_cookies(cookies)

        data = json.loads(tmp_cookie_file.read_text())
        assert len(data["cookies"]) == 1
        assert data["cookies"][0]["name"] == "a"
        assert "saved_at" in data

    def test_empty_cookies(self, tmp_cookie_file):
        save_cookies([])
        data = json.loads(tmp_cookie_file.read_text())
        assert data["cookies"] == []


class TestVerifyAndSupplement:
    """verify_and_supplement() cookie validation."""

    @responses.activate
    def test_valid_cookies_saved(self, tmp_cookie_file):
        responses.get(
            "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do",
            status=200,
        )

        cookies = [{"name": "MOD_AUTH_CAS", "value": "ticket", "domain": ".szu.edu.cn"}]
        result = verify_and_supplement(cookies)

        assert result["ok"] is True
        assert tmp_cookie_file.exists()

    @responses.activate
    def test_invalid_cookies_redirect_to_auth(self, tmp_cookie_file):
        responses.get(
            "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do",
            status=302,
            headers={"Location": "https://authserver.szu.edu.cn/authserver/login"},
        )

        cookies = [{"name": "bad", "value": "cookie"}]
        result = verify_and_supplement(cookies)

        assert result["ok"] is False
        assert "无效" in result["msg"]

    @responses.activate
    def test_network_error_still_saves(self, tmp_cookie_file):
        responses.get(
            "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do",
            body=ConnectionError("timeout"),
        )

        cookies = [{"name": "a", "value": "b"}]
        result = verify_and_supplement(cookies)

        assert result["ok"] is True
        assert "未验证" in result["msg"]
        assert tmp_cookie_file.exists()


class TestHandlerGetStatus:
    """Handler._get_status() internal method."""

    def test_no_cookie_file(self, tmp_cookie_file):
        h = Handler.__new__(Handler)
        status = h._get_status()
        assert status["has_cookie"] is False
        assert status["expired"] is True

    def test_valid_cookie_file(self, tmp_cookie_file):
        tmp_cookie_file.write_text(json.dumps({
            "cookies": [{"name": "a", "value": "b"}],
            "saved_at": time.time(),
        }))

        h = Handler.__new__(Handler)
        status = h._get_status()
        assert status["has_cookie"] is True
        assert status["expired"] is False
        assert status["count"] == 1

    def test_expired_cookie(self, tmp_cookie_file):
        tmp_cookie_file.write_text(json.dumps({
            "cookies": [{"name": "a", "value": "b"}],
            "saved_at": time.time() - 8000,
        }))

        h = Handler.__new__(Handler)
        status = h._get_status()
        assert status["has_cookie"] is True
        assert status["expired"] is True

    def test_corrupt_file(self, tmp_cookie_file):
        tmp_cookie_file.write_text("not json")

        h = Handler.__new__(Handler)
        status = h._get_status()
        assert status["has_cookie"] is False
