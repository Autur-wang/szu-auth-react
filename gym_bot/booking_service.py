"""Higher-level booking execution service."""

from dataclasses import dataclass

from booking import BookingClient
from config import AppConfig
from scheduler import measure_latency


@dataclass
class BookingRunResult:
    date: str
    venues: list
    result: object | None
    advance_ms: float
    message: str
    post_result: object | None = None


class BookingService:
    def __init__(self, cfg: AppConfig, session):
        self.cfg = cfg
        self.session = session
        self.client = BookingClient(
            session=session,
            username=cfg.user.username,
            real_name=cfg.user.real_name,
            phone=cfg.user.phone,
        )

    def resolve_target_date(self) -> str:
        date = self.cfg.booking.target_date
        if date == "auto":
            from datetime import datetime, timedelta

            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return date

    def measure_advance_ms(self) -> float:
        latency = measure_latency(self.session, self.cfg.booking.service_url)
        return latency + 10

    def query_preferred_venues(self, date: str) -> list:
        venues = self.client.query_all_hours(
            date=date,
            hours=self.cfg.booking.preferred_hours,
            sport_code=self.cfg.booking.sport_code,
            campus_code=self.cfg.booking.campus_code,
        )
        if self.cfg.booking.preferred_venue_names:
            venues = BookingClient.filter_by_venue_names(
                venues,
                self.cfg.booking.preferred_venue_names,
            )
        return venues

    def book_venues(self, venues: list, date: str, skip_wait: bool = False):
        advance_ms = self.measure_advance_ms()
        if not venues:
            return BookingRunResult(
                date=date,
                venues=[],
                result=None,
                advance_ms=advance_ms,
                message=f"❌ {date} 没有可用场地",
            )

        if skip_wait:
            result = self.client.book_concurrent(
                venues,
                max_workers=self.cfg.booking.concurrent_attempts,
                max_retries=self.cfg.booking.max_retries,
            )
        else:
            result = self.client.book_prefire(
                venues,
                open_time_str=self.cfg.booking.open_time,
                advance_ms=advance_ms,
                burst_count=10,
                burst_interval_ms=20,
            )

        if not result:
            return BookingRunResult(
                date=date,
                venues=venues,
                result=None,
                advance_ms=advance_ms,
                message=f"❌ {date} 预约失败",
            )

        return BookingRunResult(
            date=date,
            venues=venues,
            result=result,
            advance_ms=advance_ms,
            message=f"✅ 预约成功！{result.display} ({date})",
        )

    def run(self, skip_wait: bool = False):
        date = self.resolve_target_date()
        venues = self.query_preferred_venues(date)
        return self.book_venues(venues, date, skip_wait=skip_wait)

    def run_for_date(self, date: str, skip_wait: bool = False):
        venues = self.query_preferred_venues(date)
        return self.book_venues(venues, date, skip_wait=skip_wait)
