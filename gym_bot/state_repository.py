"""Persistence boundary for agent runtime state."""

import json
import time
from dataclasses import asdict
from pathlib import Path

import agent_state as agent_state_module
from agent_state import AgentState
from runtime_paths import ensure_runtime_dirs


class AgentStateRepository:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else agent_state_module.STATE_FILE

    def load(self) -> AgentState:
        if not self.path.exists():
            return AgentState()
        try:
            data = json.loads(self.path.read_text())
            known = {k for k in AgentState.__dataclass_fields__}
            return AgentState(**{k: v for k, v in data.items() if k in known})
        except Exception:
            return AgentState()

    def save(self, state: AgentState, heartbeat: bool = True) -> AgentState:
        if heartbeat:
            state.last_heartbeat = time.time()
        ensure_runtime_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(state), indent=2))
        return state
