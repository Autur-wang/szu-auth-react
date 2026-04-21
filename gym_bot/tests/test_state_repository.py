"""Tests for state_repository.py — agent state persistence boundary."""

from agent_state import AgentState
from state_repository import AgentStateRepository


class TestAgentStateRepository:
    def test_load_missing_returns_default(self, tmp_path):
        repo = AgentStateRepository(tmp_path / "agent_state.json")

        state = repo.load()

        assert isinstance(state, AgentState)
        assert state.phase == "idle"

    def test_save_and_load_round_trip(self, tmp_path):
        repo = AgentStateRepository(tmp_path / "agent_state.json")
        state = AgentState(phase="booking", today_status="cookie_ok")

        repo.save(state)
        loaded = repo.load()

        assert loaded.phase == "booking"
        assert loaded.today_status == "cookie_ok"

    def test_save_updates_heartbeat(self, tmp_path):
        repo = AgentStateRepository(tmp_path / "agent_state.json")
        state = AgentState()

        repo.save(state)

        assert state.last_heartbeat > 0
