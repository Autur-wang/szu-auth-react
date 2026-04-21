"""Tests for config.py — YAML loading + env var override."""

import os

import pytest

from config import AppConfig, UserConfig, BookingConfig, AgentConfig


class TestAppConfigLoad:
    """AppConfig.load() from YAML file."""

    def test_load_full_config(self, tmp_config):
        cfg = AppConfig.load(str(tmp_config))
        assert cfg.user.username == "test_user"
        assert cfg.user.password == "test_pass"
        assert cfg.user.real_name == "Test"
        assert cfg.user.phone == "13800000000"
        assert cfg.booking.campus_code == "1"
        assert cfg.booking.sport_code == "001"
        assert cfg.booking.preferred_hours == ["18-19", "19-20"]
        assert cfg.booking.max_retries == 3

    def test_load_missing_file_returns_defaults(self, tmp_path):
        cfg = AppConfig.load(str(tmp_path / "nonexistent.yaml"))
        assert cfg.user.username == ""
        assert cfg.user.password == ""
        assert cfg.booking.open_time == "12:30:00"
        assert cfg.booking.campus_code == "1"

    def test_load_empty_file(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        cfg = AppConfig.load(str(empty))
        assert cfg.user.username == ""

    def test_load_partial_config(self, tmp_path):
        partial = tmp_path / "partial.yaml"
        partial.write_text("user:\n  username: only_user\n  password: only_pass\n")
        cfg = AppConfig.load(str(partial))
        assert cfg.user.username == "only_user"
        assert cfg.booking.open_time == "12:30:00"  # default
        assert cfg.companions.ids == []

    def test_unknown_booking_fields_ignored(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "user:\n  username: u\n  password: p\n"
            "booking:\n  campus_code: '2'\n  unknown_field: xyz\n"
        )
        cfg = AppConfig.load(str(cfg_file))
        assert cfg.booking.campus_code == "2"
        assert not hasattr(cfg.booking, "unknown_field")

    def test_save_round_trip(self, tmp_config, tmp_path):
        cfg = AppConfig.load(str(tmp_config))
        target = tmp_path / "runtime-config.yaml"

        cfg.save(target)

        loaded = AppConfig.load(str(target))
        assert loaded.user.username == "test_user"
        assert loaded.booking.preferred_hours == ["18-19", "19-20"]


class TestEnvVarOverride:
    """Environment variables take precedence over YAML."""

    def test_username_from_env(self, tmp_config, monkeypatch):
        monkeypatch.setenv("GYM_USERNAME", "env_user")
        cfg = AppConfig.load(str(tmp_config))
        assert cfg.user.username == "env_user"

    def test_password_from_env(self, tmp_config, monkeypatch):
        monkeypatch.setenv("GYM_PASSWORD", "env_pass")
        cfg = AppConfig.load(str(tmp_config))
        assert cfg.user.password == "env_pass"

    def test_real_name_from_env(self, tmp_config, monkeypatch):
        monkeypatch.setenv("GYM_USER_REAL_NAME", "Env Name")
        cfg = AppConfig.load(str(tmp_config))
        assert cfg.user.real_name == "Env Name"

    def test_phone_from_env(self, tmp_config, monkeypatch):
        monkeypatch.setenv("GYM_PHONE", "13900000000")
        cfg = AppConfig.load(str(tmp_config))
        assert cfg.user.phone == "13900000000"

    def test_payment_password_from_env(self, tmp_config, monkeypatch):
        monkeypatch.setenv("GYM_PAYMENT_PASSWORD", "pay123")
        cfg = AppConfig.load(str(tmp_config))
        assert cfg.payment.password == "pay123"

    def test_webhook_url_from_env(self, tmp_config, monkeypatch):
        monkeypatch.setenv("WEBHOOK_URL", "https://hook.example.com")
        cfg = AppConfig.load(str(tmp_config))
        assert cfg.notify.webhook_url == "https://hook.example.com"

    def test_env_overrides_yaml_value(self, tmp_config, monkeypatch):
        monkeypatch.setenv("GYM_USERNAME", "env_wins")
        cfg = AppConfig.load(str(tmp_config))
        # YAML has "test_user", env should win
        assert cfg.user.username == "env_wins"


class TestAgentConfig:
    """AgentConfig defaults and loading."""

    def test_defaults(self):
        ac = AgentConfig()
        assert ac.enabled is False
        assert ac.wake_time == "11:00:00"
        assert ac.skip_days == []
        assert ac.max_login_attempts == 3

    def test_load_from_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "user:\n  username: u\n  password: p\n"
            "agent:\n  enabled: true\n  wake_time: '10:00:00'\n"
            "  skip_days: ['saturday']\n"
        )
        cfg = AppConfig.load(str(cfg_file))
        assert cfg.agent.enabled is True
        assert cfg.agent.wake_time == "10:00:00"
        assert cfg.agent.skip_days == ["saturday"]


class TestBookingConfig:
    """BookingConfig defaults."""

    def test_defaults(self):
        bc = BookingConfig()
        assert bc.service_url == "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do"
        assert bc.open_time == "12:30:00"
        assert bc.target_date == "auto"
        assert bc.max_retries == 20
        assert bc.concurrent_attempts == 5
