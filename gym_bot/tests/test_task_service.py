"""Tests for task_service.py — command/task orchestration."""

from unittest.mock import patch

from config import AgentConfig, AppConfig, BookingConfig, CompanionsConfig, NotifyConfig, PaymentConfig, UserConfig
from task_repository import TaskRepository
from task_service import TaskService


def _cfg():
    return AppConfig(
        user=UserConfig(username="u", password="p", real_name="R", phone="1"),
        booking=BookingConfig(),
        companions=CompanionsConfig(),
        payment=PaymentConfig(),
        notify=NotifyConfig(),
        agent=AgentConfig(),
    )


class _FakeResult:
    display = "羽毛球1号"


class _FakeSession:
    def __init__(self):
        self.headers = {}


class TestTaskService:
    def test_auth_login_task_success(self, tmp_path):
        service = TaskService(_cfg(), repository=TaskRepository(tmp_path / "tasks.json"))
        with patch("task_service.AuthService.login_verified", return_value=object()), \
             patch("task_service.AuthService.cookie_status", return_value={"has_cookie": True}):
            task = service.run("auth.login")

        assert task.status == "succeeded"
        assert task.result["message"] == "登录成功"

    def test_auth_ensure_cookie_uses_cache(self, tmp_path):
        service = TaskService(_cfg(), repository=TaskRepository(tmp_path / "tasks.json"))
        with patch("task_service.AuthService.has_valid_cached_session", return_value=True), \
             patch("task_service.AuthService.cookie_status", return_value={"has_cookie": True}):
            task = service.run("auth.ensure_cookie")

        assert task.status == "succeeded"
        assert task.result["source"] == "cache"

    def test_auth_ensure_cookie_requires_human_when_both_fail(self, tmp_path):
        service = TaskService(_cfg(), repository=TaskRepository(tmp_path / "tasks.json"))
        with patch("task_service.AuthService.has_valid_cached_session", return_value=False), \
             patch("task_service.AuthService.try_headless_login", return_value=False):
            task = service.run("auth.ensure_cookie")

        assert task.status == "failed"
        assert "需要人工登录" in task.error

    def test_booking_query_task_success(self, tmp_path):
        service = TaskService(_cfg(), repository=TaskRepository(tmp_path / "tasks.json"))
        with patch("task_service.AuthService.login_verified", return_value=_FakeSession()), \
             patch("task_service.BookingService.resolve_target_date", return_value="2026-04-30"), \
             patch("task_service.BookingService.query_preferred_venues", return_value=[]):
            task = service.run("booking.query")

        assert task.status == "succeeded"
        assert task.result["date"] == "2026-04-30"

    def test_booking_run_task_success(self, tmp_path):
        service = TaskService(_cfg(), repository=TaskRepository(tmp_path / "tasks.json"))
        with patch("task_service.AuthService.login_verified", return_value=_FakeSession()), \
             patch("task_service.BookingService.resolve_target_date", return_value="2026-04-30"), \
             patch("task_service.BookingService.run_for_date") as mock_run:
            mock_run.return_value = type(
                "RunResult",
                (),
                {
                    "date": "2026-04-30",
                    "advance_ms": 25,
                    "venues": [object()],
                    "message": "✅ 预约成功！羽毛球1号 (2026-04-30)",
                    "result": _FakeResult(),
                },
            )()
            task = service.run("booking.run")

        assert task.status == "succeeded"
        assert task.result["result"] == "羽毛球1号"

    def test_booking_run_task_failed_when_no_success_result(self, tmp_path):
        service = TaskService(_cfg(), repository=TaskRepository(tmp_path / "tasks.json"))
        with patch("task_service.AuthService.login_verified", return_value=_FakeSession()), \
             patch("task_service.BookingService.resolve_target_date", return_value="2026-04-30"), \
             patch("task_service.BookingService.run_for_date") as mock_run:
            mock_run.return_value = type(
                "RunResult",
                (),
                {
                    "date": "2026-04-30",
                    "advance_ms": 25,
                    "venues": [],
                    "message": "❌ 2026-04-30 预约失败",
                    "result": None,
                },
            )()
            task = service.run("booking.run")

        assert task.status == "failed"
        assert "预约失败" in task.error
