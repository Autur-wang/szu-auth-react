# gym-bot

深圳大学体育场馆自动预约工具。在每天 12:30 放票瞬间自动完成羽毛球场地抢票，支持多场馆并发、同行人添加、体育经费自动支付。

## 特性

- **Pre-fire 抢票**：测量网络延迟，提前发射请求，确保请求在 12:30:00 精确到达服务器
- **多轮 Burst**：10 轮并发冲击，每轮 20ms 间隔，所有候选场馆同时发送
- **三层认证**：Cookie 缓存 → 无头浏览器自动登录 → 人工登录兜底
- **Agent 模式**：全自动守护进程，每日定时唤醒、登录、抢票、支付，无需人工干预
- **同行人 & 自动支付**：Playwright 浏览器自动化完成后续操作
- **Electron GUI**：桌面客户端，配置管理 + 一键抢票 + Agent 控制面板
- **云端部署**：Cookie Server 支持远程推送认证信息
- **Webhook 通知**：飞书 / 企业微信推送预约结果

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 配置

编辑 `config.yaml`，填入学号、密码、偏好时段等信息。也可通过环境变量设置敏感字段：

```bash
export GYM_USERNAME="你的学号"
export GYM_PASSWORD="你的密码"
export GYM_USER_REAL_NAME="真实姓名"
export GYM_PHONE="手机号"
```

### 运行

```bash
# 等待 12:30 自动抢票
python main.py

# 立即抢票（测试用）
python main.py --now

# 仅查询可用场馆
python main.py --debug

# 全自动 Agent 模式
python main.py --agent
```

### Electron GUI

```bash
cd app
npm install
npm start
```

## 项目结构

```
├── main.py              # 入口
├── agent.py             # Agent 守护进程（6 阶段状态机）
├── agent_state.py       # Agent 状态持久化
├── auth.py              # CAS 认证（三层策略）
├── booking.py           # 场馆查询 + Pre-fire 并发抢票
├── post_booking.py      # 同行人添加 + 自动支付
├── cookie_server.py     # Cookie 接收服务（云端用）
├── push_cookie.py       # Cookie 推送工具
├── scheduler.py         # 精确时序控制
├── captcha.py           # 验证码处理
├── notify.py            # Webhook 通知
├── config.py            # 配置加载
├── config.yaml          # 配置模板
├── app/                 # Electron 桌面客户端
└── tests/               # 测试套件
```

## 配置说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `booking.open_time` | 放票时间 | `12:30:00` |
| `booking.target_date` | 目标日期，`auto` = 明天 | `auto` |
| `booking.campus_code` | 校区：`1` 粤海 / `2` 丽湖 | `1` |
| `booking.sport_code` | 运动项目：`001` 羽毛球 | `001` |
| `booking.preferred_hours` | 偏好时段列表 | `["18-19", "19-20", "20-21"]` |
| `booking.max_retries` | 单场馆最大重试次数 | `20` |
| `booking.concurrent_attempts` | 并发线程数 | `5` |
| `payment.auto_pay` | 自动支付开关 | `false` |
| `agent.enabled` | Agent 模式开关 | `false` |
| `agent.skip_days` | 跳过的星期 | `[]` |

## License

MIT
