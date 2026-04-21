"""Tests for agent_state.py — state persistence."""

import json
import time

import pytest

from agent_state import AgentState, STATE_FILE


@pytest.fixture(autouse=True)
def clean_state_file(tmp_path, monkeypatch):
    """Redirect STATE_FILE to tmp dir."""
    fake_path = tmp_path / ".agent_state.json"
    monkeypatch.setattr("agent_state.STATE_FILE", fake_path)
    yield fake_path


class TestAgentStateSave:
    """save() writes JSON to disk."""

    def test_save_creates_file(self, clean_state_file):
        state = AgentState()
        state.save()
        assert clean_state_file.exists()
        data = json.loads(clean_state_file.read_text())
        assert data["phase"] == "idle"

    def test_save_updates_heartbeat(self, clean_state_file):
        state = AgentState()
        before = time.time()
        state.save()
        after = time.time()
        data = json.loads(clean_state_file.read_text())
        assert before <= data["last_heartbeat"] <= after

    def test_save_preserves_all_fields(self, clean_state_file):
        state = AgentState(
            phase="booking",
            today_status="cookie_ok",
            today_date="2026-04-07",
            needs_human_login=True,
            consecutive_failures=2,
        )
        state.save()
        data = json.loads(clean_state_file.read_text())
        assert data["phase"] == "booking"
        assert data["today_status"] == "cookie_ok"
        assert data["needs_human_login"] is True
        assert data["consecutive_failures"] == 2


class TestAgentStateLoad:
    """load() reads from disk."""

    def test_load_returns_default_when_no_file(self, clean_state_file):
        state = AgentState.load()
        assert state.phase == "idle"
        assert state.today_status == "pending"

    def test_load_round_trip(self, clean_state_file):
        original = AgentState(phase="waiting", today_date="2026-04-07")
        original.save()
        loaded = AgentState.load()
        assert loaded.phase == "waiting"
        assert loaded.today_date == "2026-04-07"

    def test_load_ignores_unknown_fields(self, clean_state_file):
        clean_state_file.write_text(json.dumps({
            "phase": "idle",
            "today_status": "pending",
            "unknown_field": "should_be_ignored",
        }))
        state = AgentState.load()
        assert state.phase == "idle"
        assert not hasattr(state, "unknown_field")

    def test_load_handles_corrupt_json(self, clean_state_file):
        clean_state_file.write_text("not valid json{{{")
        state = AgentState.load()
        assert state.phase == "idle"  # fallback to default


class TestAgentStateErrors:
    """Error tracking."""

    def test_add_error(self):
        state = AgentState()
        state.add_error("connection timeout")
        assert len(state.errors) == 1
        assert "connection timeout" in state.errors[0]

    def test_errors_capped_at_20(self):
        state = AgentState()
        for i in range(25):
            state.add_error(f"error {i}")
        assert len(state.errors) == 20
        assert "error 24" in state.errors[-1]
        assert "error 4" not in str(state.errors[0])  # oldest trimmed

    def test_error_includes_timestamp(self):
        state = AgentState()
        state.add_error("test")
        assert ":" in state.errors[0]  # HH:MM:SS prefix


class TestAgentStateReset:
    """reset_today() clears daily state."""

    def test_reset_clears_status(self):
        state = AgentState(
            today_status="booked",
            needs_human_login=True,
            errors=["old error"],
        )
        state.reset_today("2026-04-08")
        assert state.today_date == "2026-04-08"
        assert state.today_status == "pending"
        assert state.needs_human_login is False
        assert state.errors == []

    def test_reset_preserves_booking_history(self):
        state = AgentState(
            last_booking_date="2026-04-07",
            last_booking_result="羽毛球1号",
            consecutive_failures=3,
        )
        state.reset_today("2026-04-08")
        # These should NOT be cleared by reset
        assert state.last_booking_date == "2026-04-07"
        assert state.consecutive_failures == 3
