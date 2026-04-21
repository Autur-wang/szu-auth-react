"""本地登录 → 推送 Cookie 到云端

用法：
  python3 push_cookie.py

做的事：
  1. 弹浏览器让你登录
  2. 把 Cookie POST 到云端服务器

配置（环境变量或 config.yaml）：
  GYM_CLOUD_URL=http://your-server:9898
  GYM_COOKIE_TOKEN=gym_bot_secret
"""

import json
import logging
import os
import sys

import requests

from auth import AuthClient, AuthError
from config import AppConfig
from runtime_paths import resolve_config_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("push_cookie")


def get_cloud_config():
    """从环境变量或 config.yaml 获取云端地址"""
    url = os.environ.get("GYM_CLOUD_URL", "")
    token = os.environ.get("GYM_COOKIE_TOKEN", "gym_bot_secret")

    if not url:
        try:
            import yaml
            raw = yaml.safe_load(resolve_config_path().read_text()) or {}
            cloud = raw.get("cloud", {})
            url = cloud.get("url", "")
            token = cloud.get("token", token)
        except Exception:
            pass

    return url, token


def main():
    cfg = AppConfig.load()

    if not cfg.user.username or not cfg.user.password:
        logger.error("请设置账号密码")
        sys.exit(1)

    cloud_url, token = get_cloud_config()
    if not cloud_url:
        logger.error("请设置云端地址: export GYM_CLOUD_URL=http://your-server:9898")
        sys.exit(1)

    # 1. 弹浏览器登录
    auth = AuthClient(service_url=cfg.booking.service_url)
    try:
        auth._browser_login(cfg.user.username, cfg.user.password)
    except AuthError as e:
        logger.error(f"登录失败: {e}")
        sys.exit(1)

    # 2. 读取刚保存的 Cookie
    cookie_data = json.loads(auth.COOKIE_CACHE_FILE.read_text())
    cookies = cookie_data["cookies"]
    logger.info(f"拿到 {len(cookies)} 个 Cookie")

    # 3. POST 到云端
    push_url = f"{cloud_url.rstrip('/')}/cookie"
    logger.info(f"推送到: {push_url}")

    try:
        resp = requests.post(
            push_url,
            json={"cookies": cookies},
            headers={"X-Token": token},
            timeout=10,
        )
        if resp.ok:
            logger.info(f"✅ {resp.json().get('msg', '推送成功')}")
        else:
            logger.error(f"推送失败: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"推送失败: {e}")


if __name__ == "__main__":
    main()
