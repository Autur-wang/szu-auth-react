"""精确定时器"""

import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def wait_until(target_time_str: str):
    """
    精确等待到今天的 target_time_str。
    策略：>2s sleep，最后 2s 忙循环。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    target = datetime.strptime(f"{today} {target_time_str}", "%Y-%m-%d %H:%M:%S")

    now = datetime.now()
    if now >= target:
        logger.info("已过目标时间，立即执行")
        return

    total_wait = (target - now).total_seconds()
    logger.info(f"等待 {total_wait:.0f} 秒，目标时间: {target_time_str}")

    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 2:
            break
        sleep_time = min(remaining - 2, 5)
        if remaining > 60 and int(remaining) % 30 == 0:
            logger.info(f"还剩 {remaining:.0f} 秒...")
        time.sleep(sleep_time)

    while datetime.now() < target:
        pass

    logger.info("⏰ 时间到！")


def measure_latency(session, url: str, times: int = 5) -> float:
    """
    测量到服务器的网络延迟（毫秒）。
    发几个轻量请求，取中位数。
    """
    latencies = []
    for _ in range(times):
        start = time.time()
        try:
            session.head(url, timeout=5)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        except Exception:
            pass
        time.sleep(0.1)

    if not latencies:
        logger.warning("测速失败，使用默认延迟 100ms")
        return 100.0

    latencies.sort()
    median = latencies[len(latencies) // 2]
    logger.info(f"网络延迟: {median:.0f}ms（测了 {len(latencies)} 次）")
    return median
