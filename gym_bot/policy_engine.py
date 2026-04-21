"""Execution policies for booking dates and task concurrency."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""


class PolicyEngine:
    def should_skip_booking_date(self, cfg, booking_date: str) -> bool:
        skip_dates = {str(x) for x in cfg.agent.skip_dates}
        if booking_date in skip_dates:
            return True

        skip_days = {str(x).strip().lower() for x in cfg.agent.skip_days}
        if not skip_days:
            return False

        weekday = datetime.strptime(booking_date, "%Y-%m-%d").strftime("%A").lower()
        return weekday in skip_days

    def is_duplicate_booking(self, state, booking_date: str) -> bool:
        return state.last_booking_date == booking_date

    def evaluate_task(self, repository, command: str) -> PolicyDecision:
        running = repository.find_running(command=command)
        if running:
            return PolicyDecision(
                allowed=False,
                reason=f"{command} 已有执行中的任务",
            )
        return PolicyDecision(allowed=True)
