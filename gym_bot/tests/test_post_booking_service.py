"""Tests for post_booking_service.py — post-booking orchestration helpers."""

from config import (
    AgentConfig,
    AppConfig,
    BookingConfig,
    CompanionsConfig,
    NotifyConfig,
    PaymentConfig,
    UserConfig,
)
from post_booking_service import PostBookingService
from post_booking import PostBookingResult


def _cfg():
    return AppConfig(
        user=UserConfig(username="u", password="p"),
        booking=BookingConfig(),
        companions=CompanionsConfig(),
        payment=PaymentConfig(),
        notify=NotifyConfig(),
        agent=AgentConfig(),
    )


class TestPostBookingService:
    def test_disabled_without_companions_or_payment(self):
        service = PostBookingService(_cfg(), session=None)

        assert service.is_enabled() is False

    def test_enabled_with_companions(self):
        cfg = _cfg()
        cfg.companions.ids = ["2023001"]
        service = PostBookingService(cfg, session=None)

        assert service.is_enabled() is True

    def test_append_details(self):
        result = PostBookingResult(
            companions_detail="成功 1/1",
            payment_detail="支付成功",
        )

        message = PostBookingService.append_details("✅ success", result)

        assert "同行人: 成功 1/1" in message
        assert "支付: 支付成功" in message
