"""Service wrapper for optional post-booking browser actions."""

from post_booking import run_post_booking


class PostBookingService:
    def __init__(self, cfg, session):
        self.cfg = cfg
        self.session = session

    def is_enabled(self) -> bool:
        return bool(
            self.cfg.companions.ids
            or (self.cfg.payment.auto_pay and self.cfg.payment.password)
        )

    def run(self, headless: bool = True, debug_pause: bool = False):
        if not self.is_enabled():
            return None
        return run_post_booking(
            session=self.session,
            companion_ids=self.cfg.companions.ids or [],
            payment_password=(
                self.cfg.payment.password if self.cfg.payment.auto_pay else ""
            ),
            headless=headless,
            debug_pause=debug_pause,
        )

    @staticmethod
    def append_details(message: str, result) -> str:
        if not result:
            return message
        if result.companions_detail:
            message += f"\n同行人: {result.companions_detail}"
        if result.payment_detail:
            message += f"\n支付: {result.payment_detail}"
        return message
