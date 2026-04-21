"""
深大体育馆自动预约

用法：
  export GYM_USERNAME=学号 GYM_PASSWORD=密码
  export GYM_USER_REAL_NAME=姓名 GYM_PHONE=手机号
  python main.py              # 等到 12:30 自动抢
  python main.py --now        # 立即抢（不等 12:30）
  python main.py --debug      # 只查询不预约
  python main.py --agent      # Agent 模式（全自动每日循环）

第一次跑会弹浏览器让你登录，之后 2 小时内直接用缓存 Cookie。
"""

import logging
import sys

from auth import AuthError
from auth_service import AuthService
from booking_service import BookingService
from config import AppConfig
import notify
from post_booking_service import PostBookingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gym_bot")


def main():
    # Agent 模式
    if "--agent" in sys.argv:
        cfg = AppConfig.load()
        from agent import AgentDaemon
        daemon = AgentDaemon(cfg)
        daemon.run(oneshot="--oneshot" in sys.argv)
        return

    debug_mode = "--debug" in sys.argv
    skip_wait = "--now" in sys.argv
    post_debug = "--post-debug" in sys.argv

    # 1. 加载配置
    cfg = AppConfig.load()

    if not cfg.user.username or not cfg.user.password:
        logger.error("请设置账号密码（环境变量或 config.yaml）")
        sys.exit(1)

    campus_name = "粤海" if cfg.booking.campus_code == "1" else "丽湖"
    logger.info(f"用户: {cfg.user.username} | 校区: {campus_name}")

    # 2. 登录（缓存优先，失败弹浏览器）
    try:
        session = AuthService(cfg).login_verified()
    except AuthError as e:
        logger.error(f"登录失败: {e}")
        notify.send(cfg.notify.webhook_url, f"❌ 登录失败: {e}")
        sys.exit(1)

    # 3. 预约服务
    booking_service = BookingService(cfg, session)
    date = booking_service.resolve_target_date()
    logger.info(f"目标日期: {date} | 放票: {cfg.booking.open_time}")

    # 4. 调试模式
    if debug_mode:
        logger.info("=== 调试模式：只查询 ===")
        import json
        client = booking_service.client
        for hr in cfg.booking.preferred_hours:
            parts = hr.split("-")
            if len(parts) == 2:
                raw = client.debug_query_raw(date, parts[0], parts[1])
                print(json.dumps(raw, ensure_ascii=False, indent=2)[:3000])
        return

    # 5. 提前查询场地（12:30 前就能查到明天有哪些场地）
    venues = booking_service.query_preferred_venues(date)
    if not venues:
        msg = f"❌ {date} 没有可用场地"
        logger.warning(msg)
        notify.send(cfg.notify.webhook_url, msg)
        sys.exit(1)
    logger.info(f"找到 {len(venues)} 个可用场地")
    for v in venues[:10]:
        logger.info(f"  → {v.display}")

    # 6. 抢票
    if skip_wait:
        logger.info("跳过等待，直接抢（--now）")
    run_result = booking_service.book_venues(venues, date, skip_wait=skip_wait)
    if not run_result.result:
        msg = run_result.message
        logger.warning(msg)
        notify.send(cfg.notify.webhook_url, msg)
        sys.exit(1)

    msg = run_result.message
    logger.info(msg)

    # 9. 后处理（同行人 + 支付）
    post_booking_service = PostBookingService(cfg, session)
    if post_booking_service.is_enabled():
        pb = post_booking_service.run(
            headless=not post_debug,
            debug_pause=post_debug,
        )
        msg = PostBookingService.append_details(msg, pb)
    else:
        msg += "\n⚠️ 请及时前往支付"

    notify.send(cfg.notify.webhook_url, msg)


if __name__ == "__main__":
    main()
