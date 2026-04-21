"""预约成功后的浏览器操作：添加同行人 + 自动支付

这两个功能没有 API 接口，必须通过浏览器页面操作完成。
使用 Playwright 打开浏览器，复用 requests 的 Cookie。

流程：
  requests 抢票成功
       ↓
  Cookie 转给 Playwright
       ↓
  打开预约管理页面
       ↓
  添加同行人（可选）
       ↓
  自动支付（可选）

依赖：
  pip install playwright
  playwright install chromium
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import List

import requests

logger = logging.getLogger(__name__)

BOOKING_URL = (
    "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do#/sportVenue"
)


@dataclass
class PostBookingResult:
    """后处理结果"""
    companions_added: bool = False
    companions_detail: str = ""
    payment_done: bool = False
    payment_detail: str = ""


def run_post_booking(
    session: requests.Session,
    companion_ids: List[str] = None,
    payment_password: str = "",
    headless: bool = False,
    timeout: int = 120,
    debug_pause: bool = False,
) -> PostBookingResult:
    """
    预约成功后的浏览器自动化操作。

    Args:
        session: 已登录的 requests.Session（Cookie 会转给浏览器）
        companion_ids: 同行人学号列表
        payment_password: 体育经费支付密码（空=不支付）
        headless: 是否无头模式
        timeout: 总超时时间（秒）
        debug_pause: 调试模式，会在关键步骤暂停让你看 DOM
    """
    result = PostBookingResult()

    if not companion_ids and not payment_password:
        logger.info("无同行人、无支付密码，跳过后处理")
        return result

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "需要 playwright:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
        result.companions_detail = "playwright 未安装"
        result.payment_detail = "playwright 未安装"
        return result

    logger.info("启动浏览器进行后处理...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()

        try:
            # ── 1. 转移 Cookie ──
            pw_cookies = _transfer_cookies(session)
            context.add_cookies(pw_cookies)
            logger.info(f"已转移 {len(pw_cookies)} 个 Cookie 到浏览器")

            page = context.new_page()

            # ── 2. 打开预约页面 ──
            logger.info("打开预约系统...")
            page.goto(BOOKING_URL, wait_until="networkidle", timeout=30000)
            time.sleep(2)  # SPA 加载需要额外时间

            if debug_pause:
                logger.info("调试暂停：请在浏览器中检查页面")
                page.pause()

            # ── 3. 导航到"我的预约"/"预约记录" ──
            _navigate_to_my_bookings(page)

            # ── 4. 添加同行人 ──
            if companion_ids:
                logger.info(f"添加同行人: {companion_ids}")
                try:
                    success_count = _add_companions(page, companion_ids)
                    result.companions_added = success_count == len(companion_ids)
                    result.companions_detail = f"成功 {success_count}/{len(companion_ids)}"
                    logger.info(f"同行人: {result.companions_detail}")
                except Exception as e:
                    result.companions_detail = f"失败: {e}"
                    logger.error(f"添加同行人失败: {e}")
                    _screenshot(page, "companions_error")

            # ── 5. 自动支付 ──
            if payment_password:
                logger.info("开始自动支付...")
                try:
                    ok = _perform_payment(page, payment_password)
                    result.payment_done = ok
                    result.payment_detail = "支付成功" if ok else "支付失败"
                    logger.info(f"支付: {result.payment_detail}")
                except Exception as e:
                    result.payment_detail = f"失败: {e}"
                    logger.error(f"自动支付失败: {e}")
                    _screenshot(page, "payment_error")

        except Exception as e:
            logger.error(f"浏览器后处理异常: {e}")
            try:
                _screenshot(page, "general_error")
            except Exception:
                pass
        finally:
            browser.close()

    return result


# ─── Cookie 转换 ────────────────────────────────────────


def _transfer_cookies(session: requests.Session) -> list:
    """将 requests.Session 的 Cookie 转为 Playwright 格式"""
    pw_cookies = []
    for cookie in session.cookies:
        pw_cookie = {
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain or ".szu.edu.cn",
            "path": cookie.path or "/",
        }
        pw_cookies.append(pw_cookie)
    return pw_cookies


# ─── 页面导航 ───────────────────────────────────────────


def _navigate_to_my_bookings(page):
    """
    导航到"我的预约"页面。

    ehall 体育馆系统是 SPA，可能需要点击标签切换。
    常见入口：页面上的"我的预约"/"预约记录"/"个人中心"标签。

    ⚠️ 选择器可能需要根据实际 DOM 调整。
    首次使用建议用 --post-debug 模式确认。
    """
    selectors_to_try = [
        "text=我的预约",
        "text=预约记录",
        "text=个人中心",
        "text=我的订单",
        "a:has-text('我的')",
        ".my-booking-tab",
    ]

    for selector in selectors_to_try:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=2000):
                el.click()
                page.wait_for_load_state("networkidle", timeout=10000)
                logger.info(f"导航成功: {selector}")
                return
        except Exception:
            continue

    # 尝试直接访问可能的 hash 路由
    logger.warning("找不到导航按钮，尝试直接访问 hash 路由...")
    for route in ["#/myBooking", "#/booking/list", "#/order"]:
        try:
            page.goto(
                f"https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do{route}",
                wait_until="networkidle",
                timeout=10000,
            )
            time.sleep(1)
            # 检查页面是否有预约记录内容
            if page.locator("text=未支付, text=已支付, text=待支付").count() > 0:
                logger.info(f"导航成功: {route}")
                return
        except Exception:
            continue

    logger.warning("⚠️ 无法自动导航到预约记录页面，请用 --post-debug 检查 DOM")


# ─── 添加同行人 ─────────────────────────────────────────


def _add_companions(page, companion_ids: List[str]) -> int:
    """
    为最新一条预约添加同行人。

    对应第三个项目 (Ticket_grabbing_system) 的 Add_companions()：
      1. 点击"同行人"标签
      2. 循环：点击"添加同行人" → 输入学号 → 查询 → 确定
      3. 关闭弹窗

    返回成功添加的人数。
    """
    success_count = 0

    # 点击"同行人"标签/按钮
    companion_tab = _find_and_click(page, [
        "text=同行人",
        "a:has-text('同行人')",
        "button:has-text('同行人')",
    ])
    if not companion_tab:
        logger.warning("找不到'同行人'入口")
        return 0

    time.sleep(1)

    for student_id in companion_ids:
        try:
            # 点击"添加同行人"按钮
            _find_and_click(page, [
                "text=添加同行人",
                "button:has-text('添加')",
            ])
            time.sleep(1)

            # 输入学号
            search_input = page.locator(
                "#searchId, "
                "input[placeholder*='学号'], "
                "input[placeholder*='卡号'], "
                "input[placeholder*='搜索']"
            ).first
            search_input.fill(student_id)

            # 点击查询（注意：原项目确认是 div 不是 button）
            _find_and_click(page, [
                "div:has-text('查询')",
                "text=查询",
                "button:has-text('查询')",
            ])
            time.sleep(1)

            # 点击确定
            _find_and_click(page, [
                "text=确定",
                "text=确认",
                "button:has-text('确')",
            ])
            time.sleep(1)

            success_count += 1
            logger.info(f"  ✅ 已添加同行人: {student_id}")

        except Exception as e:
            logger.warning(f"  ❌ 添加同行人 {student_id} 失败: {e}")

    # 关闭弹窗
    try:
        close_btn = page.locator(
            ".jqx-window-close-button, "
            ".el-dialog__close, "
            "button.close, "
            "[aria-label='Close']"
        ).first
        if close_btn.is_visible(timeout=2000):
            close_btn.click()
    except Exception:
        pass

    return success_count


# ─── 自动支付 ───────────────────────────────────────────


def _perform_payment(page, password: str) -> bool:
    """
    自动支付预约费用。

    对应第三个项目的 Pay()：
      1. 点击"未支付"标签
      2. 点击"(体育经费)支付"按钮
      3. 切换到支付窗口
      4. 点击"下一步"
      5. 虚拟键盘输入密码
      6. 确认支付

    返回是否成功。
    """
    # 1. 点击"未支付"标签
    _find_and_click(page, [
        "text=未支付",
        "text=待支付",
        "a:has-text('未支付')",
    ])
    time.sleep(1)

    # 2. 选择支付方式（优先体育经费）
    payment_clicked = _find_and_click(page, [
        "text=(体育经费)支付",
        "button:has-text('体育经费')",
        "text=体育经费",
    ])

    if not payment_clicked:
        # 备选：剩余金额支付（不需要密码）
        if _find_and_click(page, [
            "text=(剩余金额)支付",
            "button:has-text('剩余金额')",
        ]):
            logger.info("使用剩余金额支付（无需密码）")
            time.sleep(2)
            return True
        logger.warning("找不到支付按钮")
        return False

    # 3. 等待支付窗口加载（可能打开新窗口/Tab）
    logger.info("等待支付窗口...")
    time.sleep(8)

    # 检查是否打开了新窗口
    all_pages = page.context.pages
    if len(all_pages) > 1:
        page = all_pages[-1]  # 切换到最新的页面
        logger.info("切换到支付窗口")

    # 4. 点击"下一步"
    _find_and_click(page, [
        "#btnNext",
        "text=下一步",
        "button:has-text('下一步')",
    ])
    time.sleep(1)

    # 5. 点击密码输入框
    _find_and_click(page, [
        "#password",
        "input[type='password']",
        ".password-input",
    ])
    time.sleep(1)

    # 6. 虚拟键盘输入密码
    _click_virtual_keyboard(page, password)

    # 7. 确认支付
    _find_and_click(page, [
        "text=确认支付",
        "button:has-text('确认')",
        "#btnPay",
    ])
    time.sleep(3)

    # 8. 检查结果
    success = page.locator("text=支付成功, text=缴费成功").count() > 0
    if success:
        logger.info("✅ 支付成功")
    else:
        logger.warning("支付结果不确定，请手动确认")

    return success


def _click_virtual_keyboard(page, password: str):
    """
    在虚拟键盘上逐个点击数字。

    第三个项目使用: driver.find_element(By.CLASS_NAME, f"key-button.key-{digit}")
    我们用更通用的选择器策略。

    ⚠️ 部分支付系统会随机化键盘布局，
    因此必须读取按钮实际文本而不是假设固定位置。
    """
    for digit in password:
        selectors = [
            f".key-button.key-{digit}",                # 原项目的类名
            f"button.key-{digit}",
            f".keyboard-key:has-text('{digit}')",
            f".num-key:has-text('{digit}')",
            f".key-item:has-text('{digit}')",
            f"td:has-text('{digit}')",                  # 表格式键盘
        ]

        clicked = False
        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # 最后尝试：在所有按钮中找到文本匹配的
            try:
                all_buttons = page.locator("button, .key, td").all()
                for btn in all_buttons:
                    if btn.text_content().strip() == digit:
                        btn.click()
                        clicked = True
                        break
            except Exception:
                pass

        if not clicked:
            logger.warning(f"虚拟键盘找不到数字: {digit}")

        # 模拟人类输入间隔
        time.sleep(0.1 + random.random() * 0.15)


# ─── 工具函数 ───────────────────────────────────────────


def _find_and_click(page, selectors: list) -> bool:
    """尝试多个选择器，点击第一个可见的元素"""
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=2000):
                el.click()
                return True
        except Exception:
            continue
    return False


def _screenshot(page, name: str):
    """调试截图"""
    path = f"debug_{name}_{int(time.time())}.png"
    try:
        page.screenshot(path=path)
        logger.info(f"截图已保存: {path}")
    except Exception:
        pass
