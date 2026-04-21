"""Shared fixtures for gym_bot tests."""

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tmp_config(tmp_path):
    """Create a minimal config.yaml in a temp dir."""
    config = tmp_path / "config.yaml"
    config.write_text(
        "user:\n"
        "  username: test_user\n"
        "  password: test_pass\n"
        "  real_name: Test\n"
        "  phone: '13800000000'\n"
        "booking:\n"
        "  service_url: https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do\n"
        "  open_time: '12:30:00'\n"
        "  target_date: auto\n"
        "  campus_code: '1'\n"
        "  sport_code: '001'\n"
        "  preferred_hours:\n"
        "    - '18-19'\n"
        "    - '19-20'\n"
        "  preferred_venue_names: []\n"
        "  max_retries: 3\n"
        "  concurrent_attempts: 2\n"
        "companions:\n"
        "  ids: []\n"
        "payment:\n"
        "  password: ''\n"
        "  auto_pay: false\n"
        "notify:\n"
        "  webhook_url: ''\n"
        "agent:\n"
        "  enabled: false\n"
        "  wake_time: '11:00:00'\n"
        "  cookie_check_time: '12:15:00'\n"
        "  retry_login_interval: 300\n"
        "  max_login_attempts: 3\n"
        "  skip_days: []\n"
        "  skip_dates: []\n"
    )
    return config


@pytest.fixture
def sample_venue():
    """A reusable Venue instance."""
    from booking import Venue

    return Venue(
        wid="abc123",
        name="羽毛球1号",
        venue_name="运动广场东馆羽毛球场",
        date="2026-04-08",
        begin_hour="18",
        end_hour="19",
        sport_code="001",
        campus_code="1",
    )
