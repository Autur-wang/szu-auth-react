"""Agent 持久化状态"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from runtime_paths import AGENT_STATE_FILE as DEFAULT_STATE_FILE, ensure_runtime_dirs


STATE_FILE = DEFAULT_STATE_FILE


@dataclass
class AgentState:
    phase: str = "idle"                # idle, cookie_check, waiting, booking, post_booking, failed
    today_status: str = "pending"      # pending, cookie_ok, booked, failed
    today_date: str = ""
    last_booking_date: str = ""
    last_booking_result: str = ""
    last_cookie_refresh: float = 0
    needs_human_login: bool = False    # Electron 监听这个字段弹登录窗口
    consecutive_failures: int = 0
    last_heartbeat: float = 0
    errors: List[str] = field(default_factory=list)

    def save(self):
        self.last_heartbeat = time.time()
        ensure_runtime_dirs()
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "AgentState":
        if not STATE_FILE.exists():
            return cls()
        try:
            data = json.loads(STATE_FILE.read_text())
            # 只取已知字段
            known = {k for k in cls.__dataclass_fields__}
            return cls(**{k: v for k, v in data.items() if k in known})
        except Exception:
            return cls()

    def add_error(self, msg: str):
        self.errors.append(f"{time.strftime('%H:%M:%S')} {msg}")
        self.errors = self.errors[-20:]  # 只保留最近 20 条

    def reset_today(self, date: str):
        self.today_date = date
        self.today_status = "pending"
        self.needs_human_login = False
        self.errors = []
