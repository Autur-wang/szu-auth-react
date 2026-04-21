"""Tests for cookie_store.py — runtime cookie persistence helpers."""

import time

from cookie_store import CookieStore


class TestCookieStore:
    def test_save_and_load(self, tmp_path):
        store = CookieStore(tmp_path / "cookie_cache.json", max_age=7200)
        store.save([{"name": "a", "value": "1", "domain": ".szu.edu.cn", "path": "/"}])

        data = store.load()
        assert data is not None
        assert data["cookies"][0]["name"] == "a"

    def test_load_fresh_expired_returns_none(self, tmp_path):
        store = CookieStore(tmp_path / "cookie_cache.json", max_age=10)
        store.save([], saved_at=time.time() - 20)

        assert store.load_fresh() is None

    def test_status_reports_age_and_count(self, tmp_path):
        store = CookieStore(tmp_path / "cookie_cache.json", max_age=7200)
        store.save(
            [{"name": "a", "value": "1", "domain": ".szu.edu.cn", "path": "/"}],
            saved_at=time.time(),
        )

        status = store.status()
        assert status["has_cookie"] is True
        assert status["count"] == 1
        assert status["expired"] is False
