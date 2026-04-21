"""Cookie cache persistence helpers."""

import json
import time
from dataclasses import dataclass
from pathlib import Path

from runtime_paths import COOKIE_CACHE_FILE, ensure_runtime_dirs


@dataclass
class CookieStore:
    path: Path = COOKIE_CACHE_FILE
    max_age: int = 7200

    def save(self, cookies: list, saved_at: float | None = None):
        ensure_runtime_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cookies": cookies,
            "saved_at": saved_at if saved_at is not None else time.time(),
        }
        self.path.write_text(json.dumps(payload, indent=2))

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return None

    def load_fresh(self) -> dict | None:
        data = self.load()
        if not data:
            return None
        age = time.time() - data.get("saved_at", 0)
        if age > self.max_age:
            return None
        return data

    def status(self) -> dict:
        data = self.load()
        if not data:
            return {
                "has_cookie": False,
                "expired": True,
                "count": 0,
                "age_minutes": 0,
            }

        age = max(time.time() - data.get("saved_at", 0), 0)
        cookies = data.get("cookies", [])
        return {
            "has_cookie": True,
            "expired": age > self.max_age,
            "count": len(cookies),
            "age_minutes": round(age / 60),
        }
