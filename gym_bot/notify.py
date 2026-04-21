"""通知模块 — 支持飞书/企微 Webhook"""

import logging

import requests
from observability import emit_event

logger = logging.getLogger(__name__)


def send(webhook_url: str, message: str):
    """发送 Webhook 通知（飞书/企微通用格式）"""
    if not webhook_url:
        logger.debug("未配置 webhook_url，跳过通知")
        return

    try:
        emit_event("notify.send.started", webhook_url=webhook_url)
        resp = requests.post(
            webhook_url,
            json={
                "msg_type": "text",
                "content": {"text": message},
            },
            timeout=5,
        )
        if resp.ok:
            logger.info("通知发送成功")
            emit_event("notify.send.succeeded", webhook_url=webhook_url, status_code=resp.status_code)
        else:
            logger.warning(f"通知发送失败: {resp.status_code} {resp.text[:200]}")
            emit_event(
                "notify.send.failed",
                level="warning",
                webhook_url=webhook_url,
                status_code=resp.status_code,
                response_text=resp.text[:200],
            )
    except Exception as e:
        logger.warning(f"通知发送异常: {e}")
        emit_event("notify.send.error", level="error", webhook_url=webhook_url, error=str(e))
