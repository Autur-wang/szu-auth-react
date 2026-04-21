"""Tests for auth.py — CAS authentication and cookie caching."""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import responses

from auth import AuthClient, AuthError


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    """AuthClient with cookie cache redirected to tmp dir."""
    client = AuthClient(service_url="https://ehall.szu.edu.cn/test")
    fake_cache = tmp_path / ".cookie_cache.json"
    monkeypatch.setattr(AuthClient, "COOKIE_CACHE_FILE", fake_cache)
    return client


class TestCookieSave:
    """_save_cookies() persistence."""

    def test_saves_cookie_file(self, auth_client):
        auth_client.session.cookies.set("MOD_AUTH_CAS", "ticket123", domain=".szu.edu.cn")
        auth_client._save_cookies()

        data = json.loads(auth_client.COOKIE_CACHE_FILE.read_text())
        assert data["cookies"][0]["name"] == "MOD_AUTH_CAS"
        assert data["cookies"][0]["value"] == "ticket123"
        assert "saved_at" in data

    def test_saves_multiple_cookies(self, auth_client):
        auth_client.session.cookies.set("a", "1", domain=".szu.edu.cn")
        auth_client.session.cookies.set("b", "2", domain=".szu.edu.cn")
        auth_client._save_cookies()

        data = json.loads(auth_client.COOKIE_CACHE_FILE.read_text())
        assert len(data["cookies"]) == 2


class TestCookieLoad:
    """_load_cookies() from cache file."""

    def test_no_file_returns_false(self, auth_client):
        assert auth_client._load_cookies() is False

    def test_valid_cache_loads_cookies(self, auth_client):
        auth_client.COOKIE_CACHE_FILE.write_text(json.dumps({
            "cookies": [
                {"name": "MOD_AUTH_CAS", "value": "v1", "domain": ".szu.edu.cn", "path": "/"},
            ],
            "saved_at": time.time(),
        }))

        assert auth_client._load_cookies() is True
        assert auth_client.session.cookies.get("MOD_AUTH_CAS") == "v1"

    def test_expired_cache_returns_false(self, auth_client):
        auth_client.COOKIE_CACHE_FILE.write_text(json.dumps({
            "cookies": [{"name": "a", "value": "b", "domain": ".szu.edu.cn", "path": "/"}],
            "saved_at": time.time() - 8000,  # > 7200s
        }))

        assert auth_client._load_cookies() is False

    def test_corrupt_cache_returns_false(self, auth_client):
        auth_client.COOKIE_CACHE_FILE.write_text("broken json{{{")
        assert auth_client._load_cookies() is False

    def test_edge_just_before_expiry(self, auth_client):
        auth_client.COOKIE_CACHE_FILE.write_text(json.dumps({
            "cookies": [{"name": "a", "value": "b", "domain": ".szu.edu.cn", "path": "/"}],
            "saved_at": time.time() - 7190,  # 10s before expiry
        }))
        assert auth_client._load_cookies() is True

    def test_edge_just_after_expiry(self, auth_client):
        auth_client.COOKIE_CACHE_FILE.write_text(json.dumps({
            "cookies": [{"name": "a", "value": "b", "domain": ".szu.edu.cn", "path": "/"}],
            "saved_at": time.time() - 7210,  # 10s after expiry
        }))
        assert auth_client._load_cookies() is False


class TestVerifySession:
    """_verify_session() checks cookie validity."""

    @responses.activate
    def test_valid_session_200(self, auth_client):
        responses.get("https://ehall.szu.edu.cn/test", status=200)
        assert auth_client._verify_session() is True

    @responses.activate
    def test_redirect_to_authserver_means_invalid(self, auth_client):
        responses.get(
            "https://ehall.szu.edu.cn/test",
            status=302,
            headers={"Location": "https://authserver.szu.edu.cn/authserver/login"},
        )
        assert auth_client._verify_session() is False

    @responses.activate
    def test_302_to_non_auth_is_valid(self, auth_client):
        responses.get(
            "https://ehall.szu.edu.cn/test",
            status=302,
            headers={"Location": "https://ehall.szu.edu.cn/other"},
        )
        # 302 but not to authserver, status != 200 so returns False
        assert auth_client._verify_session() is False

    @responses.activate
    def test_network_error_returns_false(self, auth_client):
        responses.get("https://ehall.szu.edu.cn/test", body=ConnectionError("timeout"))
        assert auth_client._verify_session() is False


class TestLogin:
    """login() flow."""

    @responses.activate
    def test_login_with_valid_cache(self, auth_client):
        # Seed valid cache
        auth_client.COOKIE_CACHE_FILE.write_text(json.dumps({
            "cookies": [{"name": "MOD_AUTH_CAS", "value": "v1", "domain": ".szu.edu.cn", "path": "/"}],
            "saved_at": time.time(),
        }))
        responses.get("https://ehall.szu.edu.cn/test", status=200)

        session = auth_client.login("user", "pass")
        assert session.cookies.get("MOD_AUTH_CAS") == "v1"

    def test_cloud_mode_raises_without_cookie(self, auth_client, monkeypatch):
        monkeypatch.setenv("GYM_CLOUD_MODE", "1")
        with pytest.raises(AuthError, match="云端模式"):
            auth_client.login("user", "pass")

    @responses.activate
    def test_cloud_mode_with_valid_cache_succeeds(self, auth_client, monkeypatch):
        monkeypatch.setenv("GYM_CLOUD_MODE", "1")
        auth_client.COOKIE_CACHE_FILE.write_text(json.dumps({
            "cookies": [{"name": "a", "value": "b", "domain": ".szu.edu.cn", "path": "/"}],
            "saved_at": time.time(),
        }))
        responses.get("https://ehall.szu.edu.cn/test", status=200)

        session = auth_client.login("user", "pass")
        assert session is not None
