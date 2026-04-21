"""云端 Cookie 接收服务

用户操作：
  1. 手机/电脑正常打开 ehall 登录（验证码、二维码随便来）
  2. 登录成功后，点一下收藏夹里的书签
  3. Cookie 自动发到云端，完事

原理：
  书签是一段 JS，在 ehall.szu.edu.cn 页面上执行，
  能读到当前域名下的 Cookie（包括 JS 可见的），
  然后 POST 到我们的服务器。

  对于 httpOnly 的 Cookie（JS 读不到的），
  书签会额外发一个请求到 ehall 接口，
  把响应里的 Set-Cookie 也带过来。

  但最保险的方案是：书签触发后，服务端用拿到的部分 Cookie
  再访问一次 ehall，通过 302 跳转补全完整的 session Cookie。
"""

import json
import logging
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import requests

from cookie_store import CookieStore
from runtime_paths import COOKIE_CACHE_FILE as DEFAULT_COOKIE_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cookie_server")

COOKIE_FILE = DEFAULT_COOKIE_FILE
PORT = int(os.environ.get("GYM_COOKIE_PORT", "9898"))
TOKEN = os.environ.get("GYM_COOKIE_TOKEN", "gym_bot_secret")
SERVICE_URL = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do"


def save_cookies(cookies: list):
    CookieStore(COOKIE_FILE).save(cookies, saved_at=time.time())


def verify_and_supplement(cookies: list) -> dict:
    """
    用收到的 Cookie 访问 ehall，验证有效性。
    如果有效，返回补全后的完整 Cookie 列表。
    """
    session = requests.Session()
    for c in cookies:
        session.cookies.set(
            c["name"], c["value"],
            domain=c.get("domain", ".szu.edu.cn"),
            path=c.get("path", "/"),
        )

    try:
        resp = session.get(SERVICE_URL, allow_redirects=False, timeout=5)
        # 302 到 authserver = Cookie 无效
        if resp.status_code == 302 and "authserver" in resp.headers.get("Location", ""):
            return {"ok": False, "msg": "Cookie 无效（已过期或不完整）"}

        # 把 session 里所有 Cookie 导出（包括服务器新设置的）
        all_cookies = [{"name": c.name, "value": c.value,
                        "domain": c.domain, "path": c.path}
                       for c in session.cookies]
        save_cookies(all_cookies)
        return {"ok": True, "msg": f"收到 {len(all_cookies)} 个 Cookie", "count": len(all_cookies)}

    except Exception as e:
        # 验证失败但还是先存着
        save_cookies(cookies)
        return {"ok": True, "msg": f"已保存 {len(cookies)} 个 Cookie（未验证）", "count": len(cookies)}


# ─── 页面 ──────────────────────────────────────────────

def build_page():
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>深大体育馆 - Cookie</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 500px;
         margin: 30px auto; padding: 20px; line-height: 1.6; }}
  h2 {{ text-align: center; }}
  .status {{ padding: 12px; border-radius: 8px; text-align: center; margin: 15px 0; }}
  .ok {{ background: #f6ffed; border: 1px solid #b7eb8f; }}
  .warn {{ background: #fff7e6; border: 1px solid #ffd591; }}
  .none {{ background: #fff1f0; border: 1px solid #ffa39e; }}
  .step {{ background: #fafafa; padding: 15px; border-radius: 8px;
           margin: 12px 0; border: 1px solid #e8e8e8; }}
  .step h3 {{ margin: 0 0 8px 0; }}
  code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 14px; }}
  .bookmarklet {{ display: inline-block; padding: 10px 20px; background: #1890ff;
                  color: white !important; border-radius: 6px; text-decoration: none;
                  font-size: 16px; font-weight: bold; }}
  .bookmarklet:hover {{ background: #096dd9; }}
  a {{ color: #1890ff; }}
</style>
</head><body>

<h2>🏸 深大体育馆自动预约</h2>
<div id="status" class="status none">检查中...</div>

<div class="step">
  <h3>第一步：登录</h3>
  <p>用手机/电脑正常登录体育馆系统：</p>
  <a href="https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do" target="_blank">
    👉 点击打开体育馆预约系统
  </a>
  <p style="color:#999;font-size:13px;">验证码、二维码都可以正常处理</p>
</div>

<div class="step">
  <h3>第二步：发送 Cookie</h3>
  <p><b>方式 A（推荐）：</b>把下面的按钮拖到书签栏，登录成功后点一下：</p>
  <p style="text-align:center;">
    <a class="bookmarklet" href="javascript:void(fetch('{SERVER_URL}/cookie',{{method:'POST',headers:{{'Content-Type':'application/json','X-Token':'{TOKEN}'}},body:JSON.stringify({{cookies:document.cookie.split(';').map(c=>{{let[n,v]=c.trim().split('=');return{{name:n,value:v,domain:location.hostname,path:'/'}}}})}})}}).then(r=>r.json()).then(d=>alert(d.ok?'✅'+d.msg:'❌'+d.msg)).catch(e=>alert('失败:'+e)))">
      📤 发送Cookie
    </a>
  </p>
  <p style="color:#999;font-size:13px;">
    手机用户：长按上面的按钮 → 复制链接 → 添加到书签<br>
    登录体育馆后，打开这个书签即可
  </p>

  <p><b>方式 B：</b>登录成功后，在体育馆页面打开浏览器控制台（F12），粘贴执行：</p>
  <code style="display:block;padding:10px;font-size:12px;word-break:break-all;">
fetch('{SERVER_URL}/cookie',{{method:'POST',headers:{{'Content-Type':'application/json','X-Token':'{TOKEN}'}},body:JSON.stringify({{cookies:document.cookie.split(';').map(c=>{{let[n,v]=c.trim().split('=');return{{name:n,value:v,domain:location.hostname,path:'/'}}}})}})}}).then(r=>r.json()).then(d=>alert(JSON.stringify(d)))
  </code>
</div>

<div class="step">
  <h3>状态</h3>
  <div id="detail"></div>
</div>

<script>
let SERVER = '';  // 当前域名
fetch('/status').then(r=>r.json()).then(s => {{
  let el = document.getElementById('status');
  let detail = document.getElementById('detail');
  if (s.has_cookie && !s.expired) {{
    el.className = 'status ok';
    el.textContent = '✅ Cookie 有效（' + s.age_minutes + ' 分钟前）';
    detail.innerHTML = 'Cookie 数量: ' + s.count + '<br>12:30 会自动抢票，可以关闭页面了';
  }} else if (s.has_cookie) {{
    el.className = 'status warn';
    el.textContent = '⚠️ Cookie 已过期（' + s.age_minutes + ' 分钟前）';
    detail.innerHTML = '请重新登录并发送 Cookie';
  }} else {{
    el.className = 'status none';
    el.textContent = '❌ 还没有 Cookie';
    detail.innerHTML = '请按上面的步骤操作';
  }}
}});
</script>
</body></html>""".replace("{SERVER_URL}", SERVER_URL).replace("{TOKEN}", TOKEN)


# 服务器公网地址（书签里的 JS 要发请求到这个地址）
SERVER_URL = os.environ.get("GYM_SERVER_URL", f"http://localhost:{PORT}")


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send_html(build_page())
        elif path == "/status":
            self._send_json(self._get_status())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.split("?")[0] != "/cookie":
            self.send_error(404)
            return

        # 验证 token
        token = self.headers.get("X-Token", "")
        if token != TOKEN:
            self._send_json({"ok": False, "msg": "token 错误"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        cookies = body.get("cookies", [])

        if not cookies:
            self._send_json({"ok": False, "msg": "没有 Cookie"})
            return

        logger.info(f"收到 {len(cookies)} 个 Cookie，验证中...")
        result = verify_and_supplement(cookies)
        if result["ok"]:
            logger.info(f"✅ {result['msg']}")
        else:
            logger.warning(f"❌ {result['msg']}")

        # CORS 头（书签从 ehall 域名发请求到我们的服务器，需要跨域）
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Token")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_OPTIONS(self):
        """CORS 预检"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Token")
        self.end_headers()

    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_status(self):
        return CookieStore(COOKIE_FILE).status()

    def log_message(self, format, *args):
        pass


def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    logger.info(f"Cookie 服务启动: http://0.0.0.0:{PORT}")
    logger.info(f"公网地址: {SERVER_URL}")
    logger.info(f"Token: {TOKEN}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("停止")


if __name__ == "__main__":
    main()
