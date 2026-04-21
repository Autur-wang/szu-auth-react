"""Tests for agent.py — AgentDaemon lifecycle."""

import json
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from agent import AgentDaemon
from agent_state import AgentState
from config import (
    AppConfig, UserConfig, BookingConfig,
    CompanionsConfig, PaymentConfig, NotifyConfig, AgentConfig,
)


@pytest.fixture
def cfg():
    """Minimal AppConfig for agent tests."""
    return AppConfig(
        user=UserConfig(username="2023001", password="pass", real_name="Test", phone="138"),
        booking=BookingConfig(
            open_time="12:30:00",
            preferred_hours=["18-19"],
            campus_code="1",
            sport_code="001",
            max_retries=2,
            concurrent_attempts=2,
        ),
        companions=CompanionsConfig(),
        payment=PaymentConfig(),
        notify=NotifyConfig(webhook_url=""),
        agent=AgentConfig(
            wake_time="11:00:00",
            cookie_check_time="12:15:00",
        ),
    )


@pytest.fixture(autouse=True)
def tmp_state(tmp_path, monkeypatch):
    """Redirect agent state file to tmp."""
    fake_path = tmp_path / ".agent_state.json"
    monkeypatch.setattr("agent_state.STATE_FILE", fake_path)
    return fake_path


class TestAgentInit:
    """AgentDaemon initialization."""

    def test_creates_with_config(self, cfg):
        daemon = AgentDaemon(cfg)
        assert daemon.cfg is cfg
        assert daemon.session is None
        assert daemon.state.phase == "idle"


class TestAgentOneshot:
    """Agent --oneshot mode runs once."""

    @patch.object(AgentDaemon, "_daily_cycle")
    def test_oneshot_runs_once(self, mock_cycle, cfg):
        daemon = AgentDaemon(cfg)
        daemon.run(oneshot=True)
        mock_cycle.assert_called_once()

    @patch.object(AgentDaemon, "_daily_cycle", side_effect=Exception("test error"))
    def test_oneshot_handles_exception(self, mock_cycle, cfg):
        daemon = AgentDaemon(cfg)
        daemon.run(oneshot=True)
        assert daemon.state.consecutive_failures == 1
        assert len(daemon.state.errors) == 1


class TestAgentCaffeinate:
    """Agent caffeinate integration (macOS only)."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    @patch.object(AgentDaemon, "_daily_cycle")
    @patch.object(AgentDaemon, "_sleep_until_tomorrow")
    def test_caffeinate_not_started_in_oneshot(self, mock_sleep, mock_cycle, cfg):
        with patch("subprocess.Popen") as mock_popen:
            daemon = AgentDaemon(cfg)
            daemon.run(oneshot=True)
            mock_popen.assert_not_called()


class TestEnsureCookie:
    """_ensure_cookie() three-tier strategy."""

    def test_tier1_valid_cache(self, cfg):
        daemon = AgentDaemon(cfg)
        fake_task = type("Task", (), {"status": "succeeded", "result": {"source": "cache"}})()
        with patch.object(daemon.task_service, "run", return_value=fake_task):
            assert daemon._ensure_cookie() is True

    def test_tier2_headless_login(self, cfg):
        daemon = AgentDaemon(cfg)
        fake_task = type("Task", (), {"status": "succeeded", "result": {"source": "headless"}})()
        with patch.object(daemon.task_service, "run", return_value=fake_task):
            assert daemon._ensure_cookie() is True

    def test_tier3_needs_human_login(self, cfg):
        daemon = AgentDaemon(cfg)

        verify_results = iter([False, True])
        failed_task = type("Task", (), {"status": "failed", "result": None})()

        with patch.object(daemon.task_service, "run", return_value=failed_task), \
             patch.object(daemon, "_verify_cookie", side_effect=lambda: next(verify_results)), \
             patch("notify.send"), \
             patch.object(daemon, "_today_time",
                          return_value=datetime.now() + timedelta(minutes=30)):
            assert daemon._ensure_cookie() is True
            assert daemon.state.needs_human_login is False

    def test_tier3_timeout(self, cfg):
        daemon = AgentDaemon(cfg)
        failed_task = type("Task", (), {"status": "failed", "result": None})()

        with patch.object(daemon.task_service, "run", return_value=failed_task), \
             patch.object(daemon, "_verify_cookie", return_value=False), \
             patch("notify.send"), \
             patch.object(daemon, "_today_time",
                          return_value=datetime.now() - timedelta(minutes=1)), \
             patch("time.sleep"):
            assert daemon._ensure_cookie() is False


class TestDailyCycle:
    """_daily_cycle() state transitions."""

    def test_skips_already_booked_date(self, cfg, tmp_state):
        daemon = AgentDaemon(cfg)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        daemon.state.last_booking_date = tomorrow

        daemon._daily_cycle()
        # Should return early without changing phase
        assert daemon.state.phase == "idle"

    def test_skips_configured_skip_date(self, cfg, tmp_state):
        daemon = AgentDaemon(cfg)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        daemon.cfg.agent.skip_dates = [tomorrow]

        daemon._daily_cycle()

        assert daemon.state.phase == "idle"
        assert daemon.state.today_date == ""

    def test_skips_configured_skip_day(self, cfg, tmp_state):
        daemon = AgentDaemon(cfg)
        tomorrow = datetime.now() + timedelta(days=1)
        daemon.cfg.agent.skip_days = [tomorrow.strftime("%A").lower()]

        daemon._daily_cycle()

        assert daemon.state.phase == "idle"
        assert daemon.state.today_date == ""

    @patch("notify.send")
    def test_cookie_failure_sets_failed(self, mock_notify, cfg, tmp_state):
        daemon = AgentDaemon(cfg)
        with patch.object(daemon, "_ensure_cookie", return_value=False):
            daemon._daily_cycle()

        assert daemon.state.today_status == "failed"
        assert daemon.state.phase == "failed"
        assert daemon.state.consecutive_failures == 1


class TestTimeHelpers:
    """Time utility methods."""

    def test_today_time(self, cfg):
        daemon = AgentDaemon(cfg)
        result = daemon._today_time("12:30:00")
        today = datetime.now().strftime("%Y-%m-%d")
        expected = datetime.strptime(f"{today} 12:30:00", "%Y-%m-%d %H:%M:%S")
        assert result == expected

    def test_wait_for_time_past(self, cfg):
        daemon = AgentDaemon(cfg)
        past = (datetime.now() - timedelta(hours=1)).strftime("%H:%M:%S")
        start = time.time()
        daemon._wait_for_time(past)
        assert time.time() - start < 1.0
