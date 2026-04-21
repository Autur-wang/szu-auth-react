"""Higher-level authentication service boundary."""

import logging
import time

from auth import AuthClient, AuthError
from booking import BookingClient
from config import AppConfig


logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.client = AuthClient(service_url=cfg.booking.service_url)

    @property
    def session(self):
        return self.client.session

    def login(self):
        return self.client.login(self.cfg.user.username, self.cfg.user.password)

    def login_verified(self):
        session = self.login()
        booking_client = BookingClient(
            session=session,
            username=self.cfg.user.username,
            real_name=self.cfg.user.real_name,
            phone=self.cfg.user.phone,
        )
        if not booking_client.validate_session():
            raise AuthError("Session 无效，请检查登录状态")
        return session

    def cookie_status(self) -> dict:
        return self.client.get_cookie_status()

    def has_valid_cached_session(self) -> bool:
        return self.client._load_cookies() and self.client._verify_session()

    def try_headless_login(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright 未安装，跳过 headless 登录")
            return False

        login_url = f"{self.client.CAS_BASE}/login?service={self.client.service_url}"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(locale="zh-CN")
                context.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
                )
                page = context.new_page()

                page.goto(login_url, wait_until="networkidle", timeout=15000)
                page.fill("#username", self.cfg.user.username)
                page.fill("#password", self.cfg.user.password)

                time.sleep(1)
                for sel in ["#sliderCaptchaDiv", ".slide-verify", ".captcha"]:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            logger.info("检测到验证码，headless 无法处理")
                            browser.close()
                            return False
                    except Exception:
                        continue

                page.keyboard.press("Enter")
                try:
                    page.wait_for_url(
                        lambda url: "authserver" not in url,
                        timeout=15000,
                    )
                except Exception:
                    browser.close()
                    return False

                for c in context.cookies():
                    self.client.session.cookies.set(
                        c["name"],
                        c["value"],
                        domain=c.get("domain", ""),
                        path=c.get("path", "/"),
                    )
                self.client._save_cookies()

                browser.close()
                logger.info("Headless 登录成功")
                return True
        except Exception as exc:
            logger.warning(f"Headless 登录异常: {exc}")
            return False
