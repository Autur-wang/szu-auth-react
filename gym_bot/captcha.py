"""滑块验证码处理（独立模块，供外部调用）

注意：验证码处理已内置到 auth.py 的浏览器登录流程中。
本文件仅作为独立工具保留，方便单独测试验证码。

使用场景：
  - 单独测试滑块验证码是否能自动通过
  - 手动获取 Cookie（不走完整登录流程）

依赖：
  pip install playwright
  playwright install chromium
"""

import json
import logging
import time
from typing import Optional

from cookie_store import CookieStore
from runtime_paths import resolve_cookie_cache_path

logger = logging.getLogger(__name__)


def solve_slider_with_browser(
    login_url: str,
    username: str,
    password: str,
    headless: bool = False,
    timeout: int = 120,
) -> Optional[dict]:
    """
    用 Playwright 打开浏览器，手动或自动完成登录。
    返回 Cookie dict 或 None。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "需要安装 playwright:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
        return None

    mode = "headless" if headless else "手动"
    logger.info(f"启动浏览器（{mode}模式）...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="zh-CN",
        )
        # 反检测
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = context.new_page()

        try:
            page.goto(login_url, wait_until="networkidle")
            page.fill("#username", username)
            page.fill("#password", password)

            if not headless:
                logger.info("=" * 50)
                logger.info("  请在浏览器中完成登录（验证码等）")
                logger.info(f"  超时时间: {timeout} 秒")
                logger.info("=" * 50)

            # 等待跳转离开登录页
            page.wait_for_url(
                lambda url: "authserver" not in url,
                timeout=timeout * 1000,
            )

            logger.info("✅ 登录成功，提取 Cookie")
            cookies = context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            # 保存缓存
            _save_browser_cookies(cookies)
            return cookie_dict

        except Exception as e:
            logger.error(f"浏览器登录失败: {e}")
            return None
        finally:
            browser.close()


def _save_browser_cookies(cookies: list):
    """保存为 auth.py 能读的格式"""
    cache_file = resolve_cookie_cache_path()
    formatted = [{
        "name": c["name"],
        "value": c["value"],
        "domain": c.get("domain", ""),
        "path": c.get("path", "/"),
    } for c in cookies]
    CookieStore(cache_file).save(formatted, saved_at=time.time())
    logger.info(f"Cookie 已保存到 {cache_file}")


if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    url = (
        "https://authserver.szu.edu.cn/authserver/login"
        "?service=https%3A%2F%2Fehall.szu.edu.cn%2Fqljfwapp%2Fsys%2FlwSzuCgyy%2Findex.do"
    )
    result = solve_slider_with_browser(
        login_url=url,
        username=os.environ.get("GYM_USERNAME", ""),
        password=os.environ.get("GYM_PASSWORD", ""),
        headless=False,
    )
    if result:
        print(f"\n✅ 拿到 {len(result)} 个 Cookie")
    else:
        print("\n❌ 失败")
