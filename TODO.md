# SZU Sports Suite TODO

本清单基于当前仓库现状编写，目标是把仓库收敛成一套真正可交付的“深圳大学体育场自动预约软件”：

- React：统一控制台 UI
- Python：预约核心、Agent、Cookie、支付
- Electron：桌面壳、登录窗口、系统通知

---

## 1. 交付目标

### 1.1 MVP 交付标准

- 用户可以在桌面端或本地 Web UI 中填写配置
- 用户可以触发 CAS 登录并保存有效 Cookie
- 用户可以执行“立即抢票”
- 用户可以启动和停止每日 Agent
- 用户可以查看状态、日志、最近预约结果
- 前端、服务层、桌面壳只保留一套主流程，不再维护双份 UI

### 1.2 当前现状

- 根目录 React 应用仍是演示型登录页
- `docs/szu-booking/` 是静态原型，不参与真实运行
- `gym_bot/` 已具备预约、Agent、Cookie、支付、测试能力
- `gym_bot/app/` 维护了一套独立 Electron UI，后续应降级为桌面壳

---

## 2. 目标架构

### 2.1 最终结构

```text
.
├── apps/
│   └── web/                 # React 控制台
├── docs/szu-booking/        # 静态原型和文档，仅参考
├── gym_bot/
│   ├── server.py            # 新增，本地 API 服务入口
│   ├── services/            # 新增，业务服务层
│   ├── models/              # 新增，请求/响应/配置模型
│   ├── runtime/             # 新增，运行时数据
│   ├── auth.py              # 复用或迁移
│   ├── booking.py           # 复用或迁移
│   ├── agent.py             # 复用或迁移
│   ├── post_booking.py      # 复用或迁移
│   └── app/                 # Electron 壳
└── TODO.md
```

### 2.2 运行链路

1. React 控制台发起 API 请求
2. `gym_bot/server.py` 处理配置、登录、抢票、Agent、日志
3. Electron 只负责启动服务、展示前端、弹登录窗口、发系统通知
4. `docs/szu-booking/` 保留为产品设计与流程原型，不接入正式运行

---

## 3. 按文件拆分

以下按“现有文件修改”和“新增文件创建”拆分。

### 3.1 Workspace 前端文件

| 文件 | 操作 | 目标 | 详细任务 | 完成标准 |
| --- | --- | --- | --- | --- |
| `apps/web/src/App.jsx` | 重构 | 从演示登录页改成控制台壳 | 删除本地 `localStorage` 伪注册登录逻辑；改为页面容器和全局状态入口；接入 API；增加导航和错误边界 | 页面启动后展示 Dashboard，不再出现“注册/忘记密码”演示链路 |
| `apps/web/src/main.jsx` | 修改 | 注入全局样式和应用上下文 | 接入 router 或 view state；注入 query client/store；接入全局 toast | 前端状态和接口层统一初始化 |
| `apps/web/src/styles/apple-skin.css` | 精简/重构 | 从“登录页皮肤”改为“控制台主题” | 保留可复用变量；新增布局、卡片、表单、日志、状态标签、空态样式 | 控制台各页面样式统一 |
| `apps/web/package.json` | 修改 | 补前端运行依赖 | 视选型新增 `react-router-dom`、`zustand` 或等价轻量状态库 | `npm install` 后前端可正常启动 |
| `apps/web/vite.config.mjs` | 修改 | 配置开发代理 | 将 `/api` 代理到本地 Python 服务，例如 `http://127.0.0.1:8787` | 前端开发环境可直接调后端 |
| `package.json` | 修改 | 维护 workspace 入口 | 统一根脚本、workspace、跨应用运行方式 | 根仓库作为工程化入口可用 |
| `README.md` | 更新 | 与最终使用方式一致 | 改为“前端控制台 + Python 服务 + Electron”说明；补启动顺序 | 文档不再描述演示型登录页为主流程 |

### 3.2 前端新增文件

| 文件 | 操作 | 目标 | 详细任务 | 完成标准 |
| --- | --- | --- | --- | --- |
| `apps/web/src/api/client.js` | 新增 | 统一 API 请求层 | 封装 `GET/POST`、错误处理、超时处理 | 所有页面都经由此文件发请求 |
| `apps/web/src/api/endpoints.js` | 新增 | 统一接口路径常量 | 收口 `/api/config`、`/api/status` 等路径 | 无页面内硬编码接口地址 |
| `apps/web/src/pages/Dashboard.jsx` | 新增 | 展示总览状态 | 显示 Cookie、Agent、最近预约结果、系统状态 | 刷新后可拉取状态 |
| `apps/web/src/pages/Config.jsx` | 新增 | 编辑配置 | 展示账号、时段、场馆、支付、Webhook 配置 | 保存后后端配置更新 |
| `apps/web/src/pages/Booking.jsx` | 新增 | 控制手动任务 | 提供立即抢、定时抢、调试查询、停止任务 | 任务状态能实时刷新 |
| `apps/web/src/pages/Agent.jsx` | 新增 | 控制每日 Agent | 启动、停止、显示阶段、今日状态 | Agent 状态变化可见 |
| `apps/web/src/pages/Login.jsx` | 新增 | 管理登录和 Cookie | 触发浏览器登录，展示 Cookie 年龄和有效性 | 登录后状态正确变化 |
| `apps/web/src/pages/Logs.jsx` | 新增 | 查看日志 | 展示实时日志、错误高亮、清空视图 | 可以看到 booking/agent/auth 输出 |
| `apps/web/src/components/Layout.jsx` | 新增 | 控制台主布局 | 顶栏、侧栏、主内容区、状态条 | 所有页面共享布局 |
| `apps/web/src/components/StatusCard.jsx` | 新增 | 状态卡片组件 | 展示标签、值、说明、刷新按钮 | 多页面复用 |
| `apps/web/src/components/ConfigForm.jsx` | 新增 | 配置表单组件 | 表单字段拆分、校验、序列化 | `Config.jsx` 只负责数据流 |
| `apps/web/src/components/LogPanel.jsx` | 新增 | 日志面板 | 支持自动滚动、级别高亮、来源筛选 | 日志显示稳定 |
| `apps/web/src/store/appStore.js` | 新增 | 全局状态管理 | 存放配置、状态、任务、日志缓存 | 页面切换不丢状态 |
| `apps/web/src/utils/format.js` | 新增 | 格式化工具 | 格式化时间、状态、错误信息 | 页面不直接拼接格式化逻辑 |
| `apps/web/src/utils/validators.js` | 新增 | 表单校验工具 | 校验学号、手机号、时段、URL | 配置提交前有前端校验 |

### 3.3 Python 服务层文件

| 文件 | 操作 | 目标 | 详细任务 | 完成标准 |
| --- | --- | --- | --- | --- |
| `gym_bot/main.py` | 修改 | 降级为 CLI 入口 | 保留 CLI 能力；内部改调用 service 层而不是直接堆流程 | CLI 和 API 共用同一业务逻辑 |
| `gym_bot/auth.py` | 修改/抽取 | 保留认证底层能力 | 将 Cookie 读写路径改为 runtime；抽公共函数给 service 调用 | 登录逻辑可复用 |
| `gym_bot/booking.py` | 修改/抽取 | 保留预约底层能力 | 暴露无副作用的查询/抢票方法；减少脚本耦合 | API 可直接调用 |
| `gym_bot/post_booking.py` | 修改 | 保留后处理能力 | 将同行人和支付结果结构化返回；统一异常信息 | 前端可读出详细结果 |
| `gym_bot/agent.py` | 修改 | 保留 Agent 状态机 | 改为接受 service/context 依赖；状态文件迁到 runtime | 可由 API 启停 |
| `gym_bot/agent_state.py` | 修改 | 状态文件统一落盘 | 路径改到 `runtime/agent_state.json`；增加字段向前兼容 | 多进程读取稳定 |
| `gym_bot/config.py` | 修改 | 配置源统一 | 支持 `runtime/config.yaml`、模板配置、环境变量覆盖 | API 保存后 CLI/Agent 同步生效 |
| `gym_bot/cookie_server.py` | 修改 | 作为高级功能保留 | 路径改到 runtime；接口结构和主服务对齐 | 可选功能可单独运行 |
| `gym_bot/notify.py` | 修改 | 统一通知出口 | 返回发送结果；支持关闭通知时静默 | 前端可显示通知是否发送成功 |
| `gym_bot/scheduler.py` | 修改 | 定时逻辑下沉 | 把工具函数保持纯函数化 | 便于 service 调用和测试 |
| `gym_bot/requirements.txt` | 修改 | 补服务依赖 | 新增 `fastapi`、`uvicorn` 或对应服务依赖 | 服务可启动 |

### 3.4 Python 新增文件

| 文件 | 操作 | 目标 | 详细任务 | 完成标准 |
| --- | --- | --- | --- | --- |
| `gym_bot/server.py` | 新增 | 本地 API 服务入口 | 启动 Web 服务、注册路由、日志配置 | `python server.py` 可启动服务 |
| `gym_bot/services/runtime_service.py` | 新增 | 运行时目录管理 | 初始化 `runtime/`、日志目录、配置文件 | 首次启动自动建目录 |
| `gym_bot/services/config_service.py` | 新增 | 配置读写服务 | 加载、保存、校验配置 | API 和 CLI 共用 |
| `gym_bot/services/auth_service.py` | 新增 | 登录服务 | 浏览器登录、Cookie 校验、Cookie 状态查询 | 登录接口可用 |
| `gym_bot/services/booking_service.py` | 新增 | 抢票服务 | 查询、立即抢、正常抢、调试查询、停止任务 | 任务生命周期可控 |
| `gym_bot/services/agent_service.py` | 新增 | Agent 管理服务 | 启动、停止、查询状态、单实例保护 | 不会重复起多个 Agent |
| `gym_bot/services/log_service.py` | 新增 | 日志服务 | 读取日志、流式输出、历史截断 | 前端可实时展示日志 |
| `gym_bot/services/process_service.py` | 新增 | 子任务管理 | 统一管理 booking/agent 子进程或线程 | 服务层不直接散落 `subprocess` |
| `gym_bot/models/config_models.py` | 新增 | 配置模型 | 用 dataclass 或 pydantic 定义请求/响应模型 | 配置校验集中 |
| `gym_bot/models/api_models.py` | 新增 | API 响应模型 | 统一 `ok/data/error` 结构 | 所有接口返回一致 |
| `gym_bot/models/state_models.py` | 新增 | 任务状态模型 | 定义 booking/agent/runtime 状态 | 前端状态枚举稳定 |
| `gym_bot/tests/test_server.py` | 新增 | 服务入口测试 | 服务健康检查、路由注册 | 基础 API 可测 |
| `gym_bot/tests/test_config_service.py` | 新增 | 配置服务测试 | 保存、加载、校验失败分支 | 配置读写安全 |
| `gym_bot/tests/test_booking_service.py` | 新增 | 抢票服务测试 | run/stop/state 流程 | 任务状态可回归 |
| `gym_bot/tests/test_agent_service.py` | 新增 | Agent 服务测试 | start/stop/state 流程 | 单实例逻辑可回归 |
| `gym_bot/tests/test_log_service.py` | 新增 | 日志服务测试 | latest/stream/history | 日志接口可回归 |

### 3.5 Electron 文件

| 文件 | 操作 | 目标 | 详细任务 | 完成标准 |
| --- | --- | --- | --- | --- |
| `gym_bot/app/main.js` | 重构 | 从“独立 UI + Python 进程管理”改成“桌面壳” | 启动 Python 服务；开发模式加载 Vite；生产模式加载前端构建产物；保留登录窗口和通知 | Electron 不再直接维护业务界面 |
| `gym_bot/app/preload.js` | 修改 | 收口桌面能力 | 仅暴露打开登录窗、获取本地运行状态、系统通知等能力 | 前端不直接访问 Node 能力 |
| `gym_bot/app/index.html` | 弱化/移除 | 不再作为正式 UI | 开发阶段可保留占位页；生产主流程不再加载此文件 | React 成为唯一 UI |
| `gym_bot/app/package.json` | 修改 | 补桌面壳脚本 | 增加 dev/build/start 配置；补对 React 构建的集成脚本 | Electron 启动顺畅 |

### 3.6 运维和仓库文件

| 文件 | 操作 | 目标 | 详细任务 | 完成标准 |
| --- | --- | --- | --- | --- |
| `.gitignore` | 修改 | 忽略运行态和缓存 | 加入 `gym_bot/runtime/`、日志、构建缓存、桌面打包产物 | 仓库不再提交运行时垃圾文件 |
| `TODO.md` | 持续更新 | 作为执行看板 | 每完成一个阶段同步勾选和备注 | 始终反映项目真实进度 |
| `gym_bot/README.md` | 更新 | 面向服务化架构 | 补 API、runtime、Electron 壳说明 | 子项目文档与现状一致 |
| 新增 `gym_bot/runtime/.gitkeep` | 新增 | 保留目录结构 | 确保运行时目录存在 | 首次使用路径稳定 |

---

## 4. 按接口拆分

接口分为三层：HTTP API、Electron IPC、内部服务接口。

### 4.1 HTTP API 设计

统一响应格式：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

失败格式：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "CONFIG_INVALID",
    "message": "学号不能为空"
  }
}
```

#### 4.1.1 健康检查与运行时

| 方法 | 路径 | 功能 | 请求体 | 返回 | 负责文件 |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/api/health` | 健康检查 | 无 | 服务版本、时间、运行状态 | `gym_bot/server.py` |
| `GET` | `/api/status` | 获取总状态 | 无 | Cookie、Agent、Booking、最近结果 | `gym_bot/services/runtime_service.py` |
| `GET` | `/api/runtime/info` | 获取运行时目录信息 | 无 | config 路径、log 路径、是否初始化 | `gym_bot/services/runtime_service.py` |

#### 4.1.2 配置接口

| 方法 | 路径 | 功能 | 请求体 | 返回 | 负责文件 |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/api/config` | 获取配置 | 无 | 全量配置 | `gym_bot/services/config_service.py` |
| `POST` | `/api/config` | 保存配置 | 全量配置对象 | 保存后的配置 | `gym_bot/services/config_service.py` |
| `POST` | `/api/config/validate` | 校验配置 | 全量配置对象 | 校验结果、错误列表 | `gym_bot/services/config_service.py` |
| `POST` | `/api/config/reset` | 恢复默认模板 | 无 | 默认配置 | `gym_bot/services/config_service.py` |

#### 4.1.3 登录与 Cookie 接口

| 方法 | 路径 | 功能 | 请求体 | 返回 | 负责文件 |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/api/auth/status` | 获取登录状态 | 无 | `has_cookie`、`expired`、`age_minutes` | `gym_bot/services/auth_service.py` |
| `POST` | `/api/auth/login/browser` | 启动浏览器登录 | 可选账号信息 | `started`、登录提示信息 | `gym_bot/services/auth_service.py` |
| `POST` | `/api/auth/login/headless` | 触发无头登录 | 账号密码 | 登录结果 | `gym_bot/services/auth_service.py` |
| `POST` | `/api/auth/logout` | 清除 Cookie | 无 | 清除结果 | `gym_bot/services/auth_service.py` |
| `POST` | `/api/auth/refresh-cookie` | 刷新 Cookie | 无 | 刷新结果 | `gym_bot/services/auth_service.py` |

#### 4.1.4 抢票接口

| 方法 | 路径 | 功能 | 请求体 | 返回 | 负责文件 |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/api/booking/run` | 启动一次 booking 任务 | `mode=now/normal/debug` | 任务 ID、状态 | `gym_bot/services/booking_service.py` |
| `POST` | `/api/booking/stop` | 停止 booking 任务 | 无 | 停止结果 | `gym_bot/services/booking_service.py` |
| `GET` | `/api/booking/state` | 查询任务状态 | 无 | 当前状态、模式、开始时间 | `gym_bot/services/booking_service.py` |
| `GET` | `/api/booking/result` | 查询最近结果 | 无 | 最近成功或失败详情 | `gym_bot/services/booking_service.py` |
| `POST` | `/api/booking/query` | 手动查询场地 | 日期、时段、校区 | 场地列表 | `gym_bot/services/booking_service.py` |

#### 4.1.5 Agent 接口

| 方法 | 路径 | 功能 | 请求体 | 返回 | 负责文件 |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/api/agent/start` | 启动 Agent | 可选 `oneshot` | 启动结果 | `gym_bot/services/agent_service.py` |
| `POST` | `/api/agent/stop` | 停止 Agent | 无 | 停止结果 | `gym_bot/services/agent_service.py` |
| `GET` | `/api/agent/state` | 查询 Agent 状态 | 无 | phase、today_status、errors | `gym_bot/services/agent_service.py` |
| `POST` | `/api/agent/run-once` | 执行单轮周期 | 无 | 执行结果 | `gym_bot/services/agent_service.py` |

#### 4.1.6 日志接口

| 方法 | 路径 | 功能 | 请求体 | 返回 | 负责文件 |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/api/logs/latest` | 获取最新日志 | `source`、`lines` | 文本或结构化日志 | `gym_bot/services/log_service.py` |
| `GET` | `/api/logs/history` | 获取历史日志 | `source`、`date` | 日志列表 | `gym_bot/services/log_service.py` |
| `GET` | `/api/logs/stream` | 日志流 | `source` | SSE 或 WebSocket 流 | `gym_bot/services/log_service.py` |

### 4.2 Electron IPC 接口

这些接口只保留桌面特有能力，不承载业务主流程。

| IPC 名称 | 功能 | 请求参数 | 返回 | 负责文件 |
| --- | --- | --- | --- | --- |
| `desktop:open-login-window` | 打开 CAS 登录窗口 | 无 | `ok` | `gym_bot/app/main.js` |
| `desktop:notify` | 发送系统通知 | `title/body` | `ok` | `gym_bot/app/main.js` |
| `desktop:get-runtime-paths` | 返回本地 runtime 路径 | 无 | 目录路径 | `gym_bot/app/main.js` |
| `desktop:get-app-version` | 返回桌面壳版本 | 无 | 版本号 | `gym_bot/app/main.js` |

### 4.3 前端调用接口映射

| 页面 | 调用接口 | 目的 |
| --- | --- | --- |
| `Dashboard.jsx` | `/api/status`、`/api/agent/state`、`/api/auth/status` | 拉总览状态 |
| `Config.jsx` | `/api/config`、`/api/config/validate` | 配置读取和保存 |
| `Booking.jsx` | `/api/booking/run`、`/api/booking/stop`、`/api/booking/state`、`/api/booking/result` | 手动任务控制 |
| `Agent.jsx` | `/api/agent/start`、`/api/agent/stop`、`/api/agent/state` | Agent 控制 |
| `Login.jsx` | `/api/auth/status`、`/api/auth/login/browser`、`desktop:open-login-window` | 登录与 Cookie 管理 |
| `Logs.jsx` | `/api/logs/latest`、`/api/logs/stream` | 日志展示 |

### 4.4 内部服务接口

| 服务 | 核心方法 | 目的 |
| --- | --- | --- |
| `ConfigService` | `load_config()`、`save_config()`、`validate_config()` | 配置管理 |
| `AuthService` | `get_cookie_status()`、`browser_login()`、`refresh_cookie()` | 登录与 Cookie |
| `BookingService` | `run(mode)`、`stop()`、`state()`、`result()`、`query()` | 抢票任务 |
| `AgentService` | `start()`、`stop()`、`state()`、`run_once()` | Agent 生命周期 |
| `LogService` | `tail()`、`history()`、`stream()` | 日志管理 |
| `RuntimeService` | `ensure_runtime()`、`paths()`、`system_status()` | 运行时目录与总状态 |

---

## 5. 按每一天开发任务拆分

以下按 14 个工作日拆分。默认每天有明确产出、可验收。

### Day 1

- 建立 `gym_bot/runtime/` 目录规范
- 调整 `auth.py`、`agent_state.py`、`config.py` 的路径来源
- 更新 `.gitignore`
- 建立 `config.example.yaml`

交付物：

- runtime 目录可初始化
- 配置和状态不再写到源码根目录

### Day 2

- 新建 `gym_bot/server.py`
- 选定服务框架并接入基础路由
- 实现 `/api/health`
- 实现统一响应格式和错误处理中间件

交付物：

- 本地服务可启动
- 浏览器访问 `/api/health` 返回正常

### Day 3

- 新建 `runtime_service.py`
- 新建 `config_service.py`
- 实现 `/api/config`
- 实现 `/api/config/validate`
- 编写 `test_config_service.py`

交付物：

- 配置可通过 API 读取、校验、保存

### Day 4

- 新建 `auth_service.py`
- 接入现有 `auth.py`
- 实现 `/api/auth/status`
- 实现 `/api/auth/login/browser`
- 实现 `/api/auth/logout`

交付物：

- 前端可获取 Cookie 状态
- 服务能触发登录流程

### Day 5

- 新建 `booking_service.py`
- 抽取 `main.py` 中 booking 流程
- 实现 `/api/booking/run`
- 实现 `/api/booking/state`
- 实现 `/api/booking/stop`
- 编写 `test_booking_service.py`

交付物：

- 服务层能控制一次 booking 任务生命周期

### Day 6

- 新建 `agent_service.py`
- 抽取 `agent.py` 中启动、停止、状态查询
- 实现 `/api/agent/start`
- 实现 `/api/agent/stop`
- 实现 `/api/agent/state`
- 编写 `test_agent_service.py`

交付物：

- Agent 可通过 API 启停
- 单实例保护生效

### Day 7

- 新建 `log_service.py`
- 规划日志输出到 runtime/logs
- 实现 `/api/logs/latest`
- 实现 `/api/logs/history`
- 编写 `test_log_service.py`

交付物：

- 能从服务拿到 booking/agent/auth 日志

### Day 8

- 前端新建 `apps/web/src/api/`
- 新建 `apps/web/src/store/`
- 重构 `apps/web/src/App.jsx` 为控制台壳
- 新建 `Layout.jsx`
- 建立基础导航

交付物：

- 前端能显示控制台布局，不再是演示登录页

### Day 9

- 完成 `Dashboard.jsx`
- 完成 `Login.jsx`
- 接入 `/api/status`、`/api/auth/status`
- 增加全局 toast/error 展示

交付物：

- 首页可看到运行状态和登录状态

### Day 10

- 完成 `Config.jsx`
- 完成 `ConfigForm.jsx`
- 接入 `/api/config`
- 实现前端字段校验

交付物：

- 前端可读取和保存配置

### Day 11

- 完成 `Booking.jsx`
- 接入 `/api/booking/run`、`/api/booking/state`、`/api/booking/stop`
- 完成 `Logs.jsx`
- 完成 `LogPanel.jsx`

交付物：

- 前端可发起立即抢票并看到日志

### Day 12

- 完成 `Agent.jsx`
- 接入 `/api/agent/start`、`/api/agent/stop`、`/api/agent/state`
- 补状态标签、阶段解释、错误展示

交付物：

- 前端可控制每日 Agent

### Day 13

- 重构 `gym_bot/app/main.js`
- Electron 改为加载 React dev server 或构建产物
- 缩减 `preload.js` 暴露能力
- 保留登录窗口和系统通知

交付物：

- Electron 打开的是 React 控制台

### Day 14

- 联调整套链路
- 回归 Python 测试
- 跑前端 build
- 跑 Electron dev 模式
- 更新 `README.md`、`gym_bot/README.md`

交付物：

- Web 控制台、Python 服务、Electron 壳三者联通
- 文档和运行方式与代码一致

---

## 6. 验收清单

### 6.1 功能验收

- 可以保存配置
- 可以查看 Cookie 是否有效
- 可以触发登录
- 可以立即抢票
- 可以停止 booking 任务
- 可以启动和停止 Agent
- 可以查看最新日志
- Electron 可以正常加载控制台

### 6.2 技术验收

- Python 测试全部通过
- 新增服务层测试通过
- 前端 `npm run build` 通过
- Electron 开发模式可启动
- 仓库不提交运行时 Cookie、状态、日志、缓存文件

### 6.3 交付验收

- 用户不需要手动改源码目录里的 YAML
- 用户不需要同时打开两套 UI
- 所有主流程都能从控制台完成

---

## 7. 风险和提前处理项

| 风险 | 描述 | 处理方式 |
| --- | --- | --- |
| CAS 登录有验证码 | headless 登录不一定稳定 | 保留人工登录窗口作为兜底 |
| 后处理 DOM 易变 | `post_booking.py` 依赖页面结构 | 增加 `--post-debug` 和选择器集中管理 |
| 多进程状态不一致 | Agent、booking、服务可能并发 | 统一走 service 层和 runtime 文件 |
| UI 双轨维护 | React 和 Electron 各写一套界面会失控 | Electron 只保留桌面壳，不保留业务页面 |
| 配置明文风险 | 密码和支付密码不安全 | 先通过 ignore + runtime 控制，后续再做 keychain |

---

## 8. 执行顺序建议

1. 先做服务层，再改前端
2. 先让 React 控制台接通 HTTP API，再动 Electron
3. Electron 最后接 React，不要先重写桌面端
4. 每个阶段完成后立刻补测试和文档

---

## 9. 当前执行状态

- [ ] Day 1 未开始
- [ ] Day 2 未开始
- [ ] Day 3 未开始
- [ ] Day 4 未开始
- [ ] Day 5 未开始
- [ ] Day 6 未开始
- [ ] Day 7 未开始
- [ ] Day 8 未开始
- [ ] Day 9 未开始
- [ ] Day 10 未开始
- [ ] Day 11 未开始
- [ ] Day 12 未开始
- [ ] Day 13 未开始
- [ ] Day 14 未开始
