"""配置加载 — 支持 YAML 文件 + 环境变量覆盖"""

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from runtime_paths import ensure_runtime_dirs, resolve_config_path


@dataclass
class UserConfig:
    username: str
    password: str
    real_name: str = ""
    phone: str = ""


@dataclass
class BookingConfig:
    service_url: str = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do"
    open_time: str = "12:30:00"     # 放票时间
    target_date: str = "auto"
    campus_code: str = "1"          # 1=粤海, 2=丽湖
    sport_code: str = "001"         # 001=羽毛球
    preferred_hours: list = field(default_factory=lambda: ["18-19", "19-20"])
    preferred_venue_names: list = field(default_factory=list)
    max_retries: int = 20
    concurrent_attempts: int = 5


@dataclass
class CompanionsConfig:
    ids: list = field(default_factory=list)


@dataclass
class PaymentConfig:
    password: str = ""
    auto_pay: bool = False          # 安全开关


@dataclass
class NotifyConfig:
    webhook_url: str = ""


@dataclass
class AgentConfig:
    enabled: bool = False
    wake_time: str = "11:00:00"            # 每日唤醒时间
    cookie_check_time: str = "12:15:00"    # 预约前 Cookie 复查
    retry_login_interval: int = 300        # 登录重试间隔（秒）
    max_login_attempts: int = 3
    skip_days: list = field(default_factory=list)    # ["saturday", "sunday"]
    skip_dates: list = field(default_factory=list)   # ["2026-04-01"]


@dataclass
class AppConfig:
    user: UserConfig
    booking: BookingConfig
    companions: CompanionsConfig
    payment: PaymentConfig
    notify: NotifyConfig
    agent: AgentConfig

    @classmethod
    def from_dict(cls, raw: dict | None) -> "AppConfig":
        raw = raw or {}
        user_raw = raw.get("user", {})
        booking_raw = raw.get("booking", {})
        companions_raw = raw.get("companions", {})
        payment_raw = raw.get("payment", {})
        notify_raw = raw.get("notify", {})
        return cls(
            user=UserConfig(
                username=user_raw.get("username", ""),
                password=user_raw.get("password", ""),
                real_name=user_raw.get("real_name", ""),
                phone=user_raw.get("phone", ""),
            ),
            booking=BookingConfig(
                **{
                    k: v
                    for k, v in booking_raw.items()
                    if k in BookingConfig.__dataclass_fields__
                }
            ),
            companions=CompanionsConfig(
                ids=companions_raw.get("ids", []),
            ),
            payment=PaymentConfig(
                password=payment_raw.get("password", ""),
                auto_pay=payment_raw.get("auto_pay", False),
            ),
            notify=NotifyConfig(
                webhook_url=notify_raw.get("webhook_url", ""),
            ),
            agent=AgentConfig(
                **{
                    k: v
                    for k, v in raw.get("agent", {}).items()
                    if k in AgentConfig.__dataclass_fields__
                }
            ),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path | None = None):
        target = resolve_config_path(path)
        ensure_runtime_dirs()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            yaml.safe_dump(
                self.to_dict(),
                sort_keys=False,
                allow_unicode=True,
            )
        )

    @classmethod
    def load(cls, path: str | None = None) -> "AppConfig":
        """加载配置：YAML 文件 + 环境变量覆盖"""
        raw = {}
        config_path = resolve_config_path(path)
        if config_path.exists():
            raw = yaml.safe_load(config_path.read_text()) or {}

        cfg = cls.from_dict(raw)
        cfg.user.username = os.environ.get("GYM_USERNAME", cfg.user.username)
        cfg.user.password = os.environ.get("GYM_PASSWORD", cfg.user.password)
        cfg.user.real_name = os.environ.get("GYM_USER_REAL_NAME", cfg.user.real_name)
        cfg.user.phone = os.environ.get("GYM_PHONE", cfg.user.phone)
        cfg.payment.password = os.environ.get(
            "GYM_PAYMENT_PASSWORD",
            cfg.payment.password,
        )
        cfg.notify.webhook_url = os.environ.get(
            "WEBHOOK_URL",
            cfg.notify.webhook_url,
        )
        return cfg
