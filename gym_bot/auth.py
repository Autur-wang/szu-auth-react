"""深圳大学 CAS 统一认证

两种运行模式：
  本地：缓存 Cookie → 无效？弹浏览器 → 保存 Cookie
  云端：只读 Cookie 文件 → 无效就报错（Cookie 由本地推送）
"""

import json
import logging
import os
import time
from pathlib import Path

import requests

from cookie_store import CookieStore
from runtime_paths import COOKIE_CACHE_FILE as DEFAULT_COOKIE_CACHE_FILE

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class AuthError(Exception):
    """登录失败"""


class AuthClient:
    CAS_BASE = "https://authserver.szu.edu.cn/authserver"
    COOKIE_CACHE_FILE = DEFAULT_COOKIE_CACHE_FILE
    COOKIE_MAX_AGE = 7200  # 2 小时

    def __init__(self, service_url: str):
        self.service_url = service_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

    def login(self, username: str, password: str) -> requests.Session:
        """
        缓存优先 → 本地弹浏览器 → 云端直接报错。
        """
        # 1. 尝试缓存（本地和云端都走这条路）
        if self._load_cookies() and self._verify_session():
            logger.info("✅ 缓存 Cookie 有效")
            return self.session

        # 2. 云端模式：没有有效 Cookie 就直接报错
        if os.environ.get("GYM_CLOUD_MODE"):
            raise AuthError(
                "云端模式：Cookie 无效或过期！\n"
                "请在本地跑 python3 push_cookie.py 推送新 Cookie"
            )

        # 3. 本地模式：弹浏览器登录
        logger.info("Cookie 无效，弹出浏览器登录...")
        self._browser_login(username, password)
        return self.session

    # ─── 浏览器登录（仅本地）─────────────────────────────

    def _browser_login(self, username: str, password: str):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise AuthError(
                "需要安装 Playwright：\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

        login_url = f"{self.CAS_BASE}/login?service={self.service_url}"

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 720},
                locale="zh-CN",
            )
            context.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )
            page = context.new_page()

            try:
                page.goto(login_url, wait_until="networkidle", timeout=20000)
                page.fill("#username", username)
                page.fill("#password", password)

                try:
                    rm = page.query_selector("#rememberMe")
                    if rm and not rm.is_checked():
                        rm.click()
                except Exception:
                    pass

                if not self._has_captcha(page):
                    self._click_login(page)
                else:
                    logger.info("检测到验证码，请在浏览器中手动处理")

                page.wait_for_url(
                    lambda url: "authserver" not in url,
                    timeout=120000,
                )

                logger.info("✅ 登录成功")

                for c in context.cookies():
                    self.session.cookies.set(
                        c["name"], c["value"],
                        domain=c.get("domain", ""),
                        path=c.get("path", "/"),
                    )
                self._save_cookies()

            except Exception as e:
                try:
                    page.screenshot(path="debug_login_fail.png")
                except Exception:
                    pass
                raise AuthError(f"登录失败: {e}")
            finally:
                browser.close()

    def _has_captcha(self, page) -> bool:
        time.sleep(1)
        for sel in ["#sliderCaptchaDiv", ".slide-verify", ".captcha"]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return True
            except Exception:
                continue
        return False

    def _click_login(self, page):
        for sel in ["#login_submit", ".auth_login_btn",
                     "button[type='submit']", "input[type='submit']"]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    logger.info("已自动点击登录")
                    return
            except Exception:
                continue
        page.keyboard.press("Enter")

    # ─── Cookie 缓存 ───────────────────────────────────

    def _cookie_store(self) -> CookieStore:
        return CookieStore(path=Path(self.COOKIE_CACHE_FILE), max_age=self.COOKIE_MAX_AGE)

    def _save_cookies(self):
        cookies = [{"name": c.name, "value": c.value,
                     "domain": c.domain, "path": c.path}
                    for c in self.session.cookies]
        self._cookie_store().save(cookies, saved_at=time.time())
        logger.info(f"Cookie 已缓存（{len(cookies)} 个）")

    def _load_cookies(self) -> bool:
        data = self._cookie_store().load_fresh()
        if not data:
            status = self._cookie_store().status()
            if status["has_cookie"] and status["expired"]:
                logger.info(f"Cookie 过期（{status['age_minutes']:.0f} 分钟前）")
            return False
        try:
            for c in data["cookies"]:
                self.session.cookies.set(
                    c["name"], c["value"],
                    domain=c.get("domain", ""), path=c.get("path", "/"),
                )
            logger.info(f"加载缓存 Cookie（{len(data['cookies'])} 个）")
            return True
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            return False

    def get_cookie_status(self) -> dict:
        return self._cookie_store().status()

    def _verify_session(self) -> bool:
        try:
            resp = self.session.get(
                self.service_url, allow_redirects=False, timeout=5,
            )
            if resp.status_code == 302:
                loc = resp.headers.get("Location", "")
                if "authserver" in loc:
                    return False
            return resp.status_code == 200
        except Exception:
            return False
