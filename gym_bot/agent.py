"""Agent 模式 — 全自动每日预约

状态机：
  IDLE → COOKIE_CHECK → COOKIE_REFRESH → PRE_BOOK_WAIT → BOOKING → POST_BOOKING → NOTIFY → IDLE

时间线（以 11:00 唤醒为例）：
  11:00  检查/刷新 Cookie（headless 自动登录）
  11:00  如需验证码 → 通知用户（Electron 弹窗 / webhook）
  12:15  再次验证 Cookie 有效性
  12:29  测速 + 查询场地 + 构造请求
  12:30  预发抢票
  12:30  后处理（同行人 + 支付）
  12:31  通知结果
  次日循环

用法：
  python3 agent.py           # 前台运行
  python3 agent.py --oneshot  # 跑一次就退出（适合 cron）

Electron 集成：
  Electron spawn 这个进程，读 .agent_state.json 显示状态
  当 needs_human_login=true 时，Electron 自动弹登录窗口
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

from auth_service import AuthService
from config import AppConfig
import notify
from observability import configure_logging, emit_event
from policy_engine import PolicyEngine
from post_booking_service import PostBookingService
from state_repository import AgentStateRepository
from task_service import TaskService

configure_logging("agent")
logger = logging.getLogger("agent")


class AgentDaemon:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.state_repo = AgentStateRepository()
        self.state = self.state_repo.load()
        self.session = None
        self.auth_service = AuthService(cfg)
        self.policy = PolicyEngine()
        self.task_service = TaskService(cfg, policy=self.policy)

    # ─── 主循环 ─────────────────────────────────────────

    def run(self, oneshot: bool = False):
        logger.info("Agent 启动")
        emit_event("agent.started", oneshot=oneshot)

        # macOS 防休眠：caffeinate 绑定当前 PID，进程退出自动解除
        caffeinate = None
        if not oneshot and sys.platform == "darwin":
            try:
                caffeinate = subprocess.Popen(
                    ["caffeinate", "-i", "-s", "-w", str(os.getpid())]
                )
                logger.info(f"防休眠已启用 (caffeinate pid={caffeinate.pid})")
            except FileNotFoundError:
                logger.warning("caffeinate 不可用，跳过防休眠")

        try:
            while True:
                try:
                    self._daily_cycle()
                except Exception as e:
                    logger.error(f"Agent 异常: {e}")
                    emit_event("agent.exception", level="error", error=str(e))
                    self.state.add_error(str(e))
                    self.state.consecutive_failures += 1
                    self._save_state()

                if oneshot:
                    logger.info("单次模式，退出")
                    emit_event("agent.stopped", reason="oneshot")
                    break

                self._sleep_until_tomorrow()
        finally:
            if caffeinate:
                caffeinate.terminate()
                logger.info("防休眠已释放")
            emit_event("agent.stopped", reason="loop_exit")

    def _daily_cycle(self):
        today = datetime.now().strftime("%Y-%m-%d")
        booking_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        if self.policy.should_skip_booking_date(self.cfg, booking_date):
            logger.info(f"命中跳过规则，跳过 {booking_date}")
            emit_event("agent.booking.skipped", booking_date=booking_date, reason="policy_skip")
            return

        # 防止重复预约
        if self.policy.is_duplicate_booking(self.state, booking_date):
            logger.info(f"今天已预约过 {booking_date}，跳过")
            emit_event("agent.booking.skipped", booking_date=booking_date, reason="duplicate")
            return

        self.state.reset_today(today)
        self.state.phase = "cookie_check"
        self._save_state()
        emit_event("agent.phase.changed", phase="cookie_check", booking_date=booking_date)
        logger.info(f"开始今日周期: 预约 {booking_date}")

        # ── Phase 1: Cookie ──
        if not self._ensure_cookie():
            self._fail_today(
                "❌ Cookie 获取失败，今日无法预约",
                increment_failure=True,
            )
            return

        self.state.today_status = "cookie_ok"
        self.state.phase = "waiting"
        self._save_state()
        emit_event("agent.phase.changed", phase="waiting", booking_date=booking_date)

        # ── Phase 2: 等到 12:15 再验证 ──
        self._wait_for_time(self.cfg.agent.cookie_check_time)

        if not self._verify_cookie():
            logger.warning("12:15 Cookie 失效，紧急刷新...")
            if not self._ensure_cookie():
                self._fail_today("❌ Cookie 紧急刷新失败")
                return

        query_task = self.task_service.run(
            "booking.query",
            payload={"date": booking_date},
            trigger_source="agent",
            metadata={"phase": "prebook_query"},
            runtime_context={"session": self.session},
        )
        if query_task.status != "succeeded":
            self.state.add_error(query_task.error or "场地查询失败")
            self._fail_today(
                f"❌ {booking_date} 场地查询失败: {query_task.error or 'unknown'}",
                increment_failure=False,
            )
            return
        venue_count = int((query_task.result or {}).get("venue_count", 0))
        if venue_count <= 0:
            self.state.add_error("没有可用场地")
            self._fail_today(
                f"❌ {booking_date} 没有可用场地",
                increment_failure=False,
            )
            return
        logger.info(f"找到 {venue_count} 个可用场地")

        # ── Phase 4: 抢票 ──
        self.state.phase = "booking"
        self._save_state()
        emit_event("agent.phase.changed", phase="booking", booking_date=booking_date)

        run_task = self.task_service.run(
            "booking.run",
            payload={"date": booking_date},
            trigger_source="agent",
            metadata={"phase": "booking"},
            runtime_context={"session": self.session},
        )
        if run_task.status != "succeeded":
            self._fail_today(
                run_task.error or f"❌ {booking_date} 预约失败",
                increment_failure=True,
            )
            return

        run_result = run_task.result or {}
        msg = run_result.get("message", f"✅ {booking_date} 预约成功")
        logger.info(msg)

        self.state.today_status = "booked"
        self.state.last_booking_date = booking_date
        self.state.last_booking_result = run_result.get("result", "")
        self.state.consecutive_failures = 0

        # ── Phase 5: 后处理 ──
        self.state.phase = "post_booking"
        self._save_state()
        emit_event("agent.phase.changed", phase="post_booking", booking_date=booking_date)

        post_booking_service = PostBookingService(self.cfg, self.session)
        if post_booking_service.is_enabled():
            try:
                pb = post_booking_service.run(headless=True)
                msg = PostBookingService.append_details(msg, pb)
            except Exception as e:
                logger.error(f"后处理异常: {e}")
                msg += f"\n⚠️ 后处理失败: {e}"

        # ── Phase 6: 通知 ──
        self.state.phase = "idle"
        self._save_state()
        emit_event("agent.phase.changed", phase="idle", booking_date=booking_date)
        notify.send(self.cfg.notify.webhook_url, msg)
        logger.info("今日周期完成")
        emit_event("agent.cycle.succeeded", booking_date=booking_date, result=self.state.last_booking_result)

    # ─── Cookie 管理（分层策略）────────────────────────

    def _ensure_cookie(self) -> bool:
        """
        分层获取 Cookie：
          Tier 1: 缓存有效 → 直接用
          Tier 2: Headless 自动登录（无验证码时能过）
          Tier 3: 通知用户手动登录，轮询等待
        """
        cookie_task = self.task_service.run(
            "auth.ensure_cookie",
            trigger_source="agent",
            metadata={"phase": "cookie_check"},
            runtime_context={"auth_service": self.auth_service},
        )
        if cookie_task.status == "succeeded":
            self.session = self.auth_service.session
            if (cookie_task.result or {}).get("source") == "headless":
                self.state.last_cookie_refresh = time.time()
                self._save_state()
            logger.info((cookie_task.result or {}).get("message", "Cookie 就绪"))
            emit_event(
                "agent.cookie.ready",
                source=(cookie_task.result or {}).get("source", "unknown"),
            )
            return True

        # Tier 3: 请求人工介入
        logger.warning("需要人工登录（验证码）")
        emit_event("agent.cookie.human_required", level="warning")
        self.state.needs_human_login = True
        self._save_state()
        notify.send(
            self.cfg.notify.webhook_url,
            "⚠️ 需要手动登录！请打开 App 或访问 Cookie 服务完成登录"
        )

        # 轮询等 Cookie 到达（最多等到 12:25）
        deadline = self._today_time(self.cfg.booking.open_time) - timedelta(minutes=5)
        while datetime.now() < deadline:
            time.sleep(10)
            self._save_state()  # heartbeat
            if self._verify_cookie():
                logger.info("收到有效 Cookie！")
                emit_event("agent.cookie.received_after_human")
                self.state.needs_human_login = False
                self._save_state()
                return True

        logger.error("等待超时，未收到有效 Cookie")
        emit_event("agent.cookie.timeout", level="error")
        self.state.needs_human_login = False
        self._save_state()
        return False

    def _verify_cookie(self) -> bool:
        """验证当前 Cookie 是否有效"""
        if self.auth_service.has_valid_cached_session():
            self.session = self.auth_service.session
            return True
        return False

    def _fail_today(self, message: str, increment_failure: bool = False):
        self.state.today_status = "failed"
        self.state.phase = "failed"
        if increment_failure:
            self.state.consecutive_failures += 1
        self._save_state()
        notify.send(self.cfg.notify.webhook_url, message)
        emit_event(
            "agent.cycle.failed",
            level="error",
            message=message,
            consecutive_failures=self.state.consecutive_failures,
        )

    def _save_state(self, heartbeat: bool = True):
        self.state_repo.save(self.state, heartbeat=heartbeat)

    # ─── 时间工具 ───────────────────────────────────────

    def _today_time(self, time_str: str) -> datetime:
        today = datetime.now().strftime("%Y-%m-%d")
        return datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M:%S")

    def _wait_for_time(self, time_str: str):
        target = self._today_time(time_str)
        now = datetime.now()
        if now >= target:
            return
        secs = (target - now).total_seconds()
        logger.info(f"等待到 {time_str}（{secs:.0f} 秒）")
        # 每 60 秒发一次 heartbeat
        while datetime.now() < target:
            self._save_state()
            remaining = (target - datetime.now()).total_seconds()
            time.sleep(min(remaining, 60))

    def _sleep_until_tomorrow(self):
        """睡到明天的 wake_time"""
        tomorrow = datetime.now() + timedelta(days=1)
        wake = datetime.strptime(
            f"{tomorrow.strftime('%Y-%m-%d')} {self.cfg.agent.wake_time}",
            "%Y-%m-%d %H:%M:%S",
        )
        secs = (wake - datetime.now()).total_seconds()
        if secs < 0:
            secs = 0
        logger.info(f"下次唤醒: {wake}（{secs / 3600:.1f} 小时后）")
        self.state.phase = "idle"
        self._save_state()

        while datetime.now() < wake:
            self._save_state()
            remaining = (wake - datetime.now()).total_seconds()
            time.sleep(min(remaining, 300))  # 每 5 分钟 heartbeat


# ─── 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    cfg = AppConfig.load()

    if not cfg.user.username or not cfg.user.password:
        logger.error("请先配置账号密码")
        sys.exit(1)

    daemon = AgentDaemon(cfg)
    daemon.run(oneshot="--oneshot" in sys.argv)
