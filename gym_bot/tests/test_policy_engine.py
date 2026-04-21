"""Tests for policy_engine.py — booking/date and concurrency rules."""

from datetime import datetime, timedelta

from config import AgentConfig, AppConfig, BookingConfig, CompanionsConfig, NotifyConfig, PaymentConfig, UserConfig
from policy_engine import PolicyEngine
from task_models import TaskRecord


def _cfg():
    return AppConfig(
        user=UserConfig(username="u", password="p"),
        booking=BookingConfig(),
        companions=CompanionsConfig(),
        payment=PaymentConfig(),
        notify=NotifyConfig(),
        agent=AgentConfig(),
    )


class _Repo:
    def __init__(self, running=None):
        self._running = running or []

    def find_running(self, command=None):
        if command is None:
            return self._running
        return [task for task in self._running if task.command == command]


class TestPolicyEngine:
    def test_skip_booking_date_from_skip_dates(self):
        cfg = _cfg()
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        cfg.agent.skip_dates = [tomorrow]

        assert PolicyEngine().should_skip_booking_date(cfg, tomorrow) is True

    def test_skip_booking_date_from_skip_days(self):
        cfg = _cfg()
        target = datetime.now() + timedelta(days=1)
        cfg.agent.skip_days = [target.strftime("%A").lower()]

        assert PolicyEngine().should_skip_booking_date(cfg, target.strftime("%Y-%m-%d")) is True

    def test_duplicate_booking(self):
        state = type("State", (), {"last_booking_date": "2026-04-30"})()

        assert PolicyEngine().is_duplicate_booking(state, "2026-04-30") is True

    def test_rejects_when_same_command_running(self):
        running = [TaskRecord.create("booking.run", "agent")]
        running[0].status = "running"
        decision = PolicyEngine().evaluate_task(_Repo(running), "booking.run")

        assert decision.allowed is False

