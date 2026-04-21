"""Runtime path resolution for config, cookie cache, and agent state."""

import os
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
LEGACY_ROOT = MODULE_DIR


def _resolve_path(raw: str | Path | None, default: Path) -> Path:
    if raw is None or raw == "":
        return default
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


RUNTIME_DIR = _resolve_path(
    os.environ.get("GYM_RUNTIME_DIR"),
    PROJECT_ROOT / "runtime",
)
LOG_DIR = _resolve_path(
    os.environ.get("GYM_LOG_DIR"),
    RUNTIME_DIR / "logs",
)
CONFIG_FILE = _resolve_path(
    os.environ.get("GYM_CONFIG_PATH"),
    RUNTIME_DIR / "config.yaml",
)
COOKIE_CACHE_FILE = _resolve_path(
    os.environ.get("GYM_COOKIE_CACHE_PATH"),
    RUNTIME_DIR / "cookie_cache.json",
)
AGENT_STATE_FILE = _resolve_path(
    os.environ.get("GYM_AGENT_STATE_PATH"),
    RUNTIME_DIR / "agent_state.json",
)
TASKS_FILE = _resolve_path(
    os.environ.get("GYM_TASKS_PATH"),
    RUNTIME_DIR / "tasks.json",
)

LEGACY_CONFIG_FILE = LEGACY_ROOT / "config.yaml"
LEGACY_COOKIE_CACHE_FILE = LEGACY_ROOT / ".cookie_cache.json"
LEGACY_AGENT_STATE_FILE = LEGACY_ROOT / ".agent_state.json"


def ensure_runtime_dirs():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def resolve_config_path(path: str | Path | None = None) -> Path:
    if path:
        return _resolve_path(path, CONFIG_FILE)
    if CONFIG_FILE.exists():
        return CONFIG_FILE
    if LEGACY_CONFIG_FILE.exists():
        return LEGACY_CONFIG_FILE
    return CONFIG_FILE


def resolve_cookie_cache_path() -> Path:
    if COOKIE_CACHE_FILE.exists():
        return COOKIE_CACHE_FILE
    if LEGACY_COOKIE_CACHE_FILE.exists():
        return LEGACY_COOKIE_CACHE_FILE
    return COOKIE_CACHE_FILE


def resolve_agent_state_path() -> Path:
    if AGENT_STATE_FILE.exists():
        return AGENT_STATE_FILE
    if LEGACY_AGENT_STATE_FILE.exists():
        return LEGACY_AGENT_STATE_FILE
    return AGENT_STATE_FILE


def resolve_tasks_path() -> Path:
    return TASKS_FILE
