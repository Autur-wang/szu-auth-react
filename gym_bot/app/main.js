const { app, BrowserWindow, session, ipcMain, powerSaveBlocker } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const https = require("https");
const http = require("http");
const yaml = require("js-yaml");

// ─── 路径 ──────────────────────────────────────────────
const BOT_ROOT = path.join(__dirname, "..");
const REPO_ROOT = path.join(BOT_ROOT, "..");
const RUNTIME_DIR = process.env.GYM_RUNTIME_DIR || path.join(REPO_ROOT, "runtime");
const COOKIE_FILE =
  process.env.GYM_COOKIE_CACHE_PATH || path.join(RUNTIME_DIR, "cookie_cache.json");
const CONFIG_FILE =
  process.env.GYM_CONFIG_PATH ||
  (fs.existsSync(path.join(RUNTIME_DIR, "config.yaml"))
    ? path.join(RUNTIME_DIR, "config.yaml")
    : path.join(BOT_ROOT, "config.yaml"));
const AGENT_STATE_FILE =
  process.env.GYM_AGENT_STATE_PATH || path.join(RUNTIME_DIR, "agent_state.json");
const TASKS_FILE = process.env.GYM_TASKS_PATH || path.join(RUNTIME_DIR, "tasks.json");
const LOG_DIR = process.env.GYM_LOG_DIR || path.join(RUNTIME_DIR, "logs");
const RULES_FILE = process.env.GYM_RULES_PATH || path.join(RUNTIME_DIR, "booking_rules.json");

const SERVICE_URL =
  "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do";
const CAS_LOGIN_URL = `https://authserver.szu.edu.cn/authserver/login?service=${encodeURIComponent(SERVICE_URL)}`;

let mainWindow;
let loginWindow;
let pythonProc = null;
let agentProc = null;
let agentWatcher = null;
let sleepBlockId = null;

// ─── Python 路径 ───────────────────────────────────────
function getPythonPath() {
  const repoVenvPy = path.join(REPO_ROOT, "venv", "bin", "python3");
  if (fs.existsSync(repoVenvPy)) return repoVenvPy;
  const botVenvPy = path.join(BOT_ROOT, "venv", "bin", "python3");
  if (fs.existsSync(botVenvPy)) return botVenvPy;
  return "python3";
}

function ensureRuntimeDir() {
  fs.mkdirSync(RUNTIME_DIR, { recursive: true });
}

// ─── 主窗口 ────────────────────────────────────────────
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 700,
    height: 780,
    resizable: true,
    title: "深大体育馆自动预约",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, "index.html"));
  mainWindow.setMenuBarVisibility(false);
}

// ─── 登录窗口 ──────────────────────────────────────────
function openLoginWindow() {
  if (loginWindow) {
    loginWindow.focus();
    return;
  }
  loginWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    title: "深大统一认证登录",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  loginWindow.loadURL(CAS_LOGIN_URL);
  loginWindow.setMenuBarVisibility(false);

  loginWindow.webContents.on("did-navigate", (event, url) => {
    if (!url.includes("authserver")) {
      extractAndSaveCookies().then((result) => {
        mainWindow.webContents.send("login-result", result);
        setTimeout(() => {
          if (loginWindow && !loginWindow.isDestroyed()) loginWindow.close();
        }, 1500);
      });
    }
  });
  loginWindow.on("closed", () => (loginWindow = null));
}

// ─── Cookie 操作 ───────────────────────────────────────
async function extractAndSaveCookies() {
  try {
    ensureRuntimeDir();
    const allCookies = await session.defaultSession.cookies.get({});
    const szuCookies = allCookies
      .filter((c) => c.domain && c.domain.includes("szu.edu.cn"))
      .map((c) => ({
        name: c.name,
        value: c.value,
        domain: c.domain,
        path: c.path || "/",
      }));

    fs.writeFileSync(
      COOKIE_FILE,
      JSON.stringify(
        { cookies: szuCookies, saved_at: Date.now() / 1000 },
        null,
        2
      )
    );
    return { ok: true, msg: `保存了 ${szuCookies.length} 个 Cookie`, count: szuCookies.length };
  } catch (e) {
    return { ok: false, msg: e.message };
  }
}

function getCookieStatus() {
  if (!fs.existsSync(COOKIE_FILE))
    return { has_cookie: false, expired: true, count: 0, age_minutes: 0 };
  try {
    const data = JSON.parse(fs.readFileSync(COOKIE_FILE, "utf-8"));
    const age = Date.now() / 1000 - (data.saved_at || 0);
    return {
      has_cookie: true,
      count: (data.cookies || []).length,
      age_minutes: Math.round(age / 60),
      expired: age > 7200,
    };
  } catch {
    return { has_cookie: false, expired: true, count: 0, age_minutes: 0 };
  }
}

// ─── Config 读写 ───────────────────────────────────────
function loadConfig() {
  if (!fs.existsSync(CONFIG_FILE)) return {};
  return yaml.load(fs.readFileSync(CONFIG_FILE, "utf-8")) || {};
}

function saveConfig(cfg) {
  ensureRuntimeDir();
  fs.writeFileSync(CONFIG_FILE, yaml.dump(cfg, { lineWidth: -1 }));
  return { ok: true };
}

// ─── Python 进程管理 ──────────────────────────────────
function runPython(args) {
  if (pythonProc) return { ok: false, msg: "已有任务在运行" };

  const py = getPythonPath();
  const script = path.join(BOT_ROOT, "main.py");

  pythonProc = spawn(py, [script, ...args], {
    cwd: BOT_ROOT,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      GYM_RUNTIME_DIR: RUNTIME_DIR,
      GYM_CONFIG_PATH: CONFIG_FILE,
      GYM_COOKIE_CACHE_PATH: COOKIE_FILE,
      GYM_AGENT_STATE_PATH: AGENT_STATE_FILE,
    },
  });

  pythonProc.stdout.on("data", (d) =>
    mainWindow.webContents.send("py-stdout", d.toString())
  );
  pythonProc.stderr.on("data", (d) =>
    mainWindow.webContents.send("py-stderr", d.toString())
  );
  pythonProc.on("close", (code) => {
    mainWindow.webContents.send("py-exit", code);
    pythonProc = null;
  });

  return { ok: true };
}

function stopPython() {
  if (!pythonProc) return { ok: false, msg: "没有在运行" };
  pythonProc.kill("SIGTERM");
  pythonProc = null;
  return { ok: true };
}

// ─── 推送到云端 ────────────────────────────────────────
function pushToCloud(cloudUrl, token) {
  return new Promise((resolve) => {
    if (!fs.existsSync(COOKIE_FILE)) {
      resolve({ ok: false, msg: "本地没有 Cookie" });
      return;
    }
    const data = JSON.parse(fs.readFileSync(COOKIE_FILE, "utf-8"));
    const body = JSON.stringify({ cookies: data.cookies });
    const url = new URL("/cookie", cloudUrl);
    const mod = url.protocol === "https:" ? https : http;

    const req = mod.request(
      url,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Token": token || "gym_bot_secret",
          "Content-Length": Buffer.byteLength(body),
        },
        timeout: 10000,
      },
      (res) => {
        let rb = "";
        res.on("data", (c) => (rb += c));
        res.on("end", () => {
          try { resolve(JSON.parse(rb)); }
          catch { resolve({ ok: res.statusCode === 200, msg: `HTTP ${res.statusCode}` }); }
        });
      }
    );
    req.on("error", (e) => resolve({ ok: false, msg: e.message }));
    req.on("timeout", () => { req.destroy(); resolve({ ok: false, msg: "超时" }); });
    req.write(body);
    req.end();
  });
}

// ─── Agent 进程管理 ────────────────────────────────────
function startAgent() {
  if (agentProc) return { ok: false, msg: "Agent 已在运行" };

  // 阻止系统休眠
  if (sleepBlockId === null) {
    sleepBlockId = powerSaveBlocker.start("prevent-app-suspension");
    console.log(`防休眠已启用 (id=${sleepBlockId})`);
  }

  const py = getPythonPath();
  const script = path.join(BOT_ROOT, "main.py");

  agentProc = spawn(py, [script, "--agent"], {
    cwd: BOT_ROOT,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      GYM_RUNTIME_DIR: RUNTIME_DIR,
      GYM_CONFIG_PATH: CONFIG_FILE,
      GYM_COOKIE_CACHE_PATH: COOKIE_FILE,
      GYM_AGENT_STATE_PATH: AGENT_STATE_FILE,
    },
  });

  agentProc.stdout.on("data", (d) =>
    mainWindow.webContents.send("agent-stdout", d.toString())
  );
  agentProc.stderr.on("data", (d) =>
    mainWindow.webContents.send("agent-stderr", d.toString())
  );
  agentProc.on("close", (code) => {
    mainWindow.webContents.send("agent-exit", code);
    agentProc = null;
    // 释放防休眠
    if (sleepBlockId !== null) {
      powerSaveBlocker.stop(sleepBlockId);
      console.log("防休眠已释放");
      sleepBlockId = null;
    }
  });

  // 监听 .agent_state.json 变化，检测是否需要弹登录窗口
  startAgentWatcher();

  return { ok: true };
}

function stopAgent() {
  if (!agentProc) return { ok: false, msg: "Agent 未运行" };
  agentProc.kill("SIGTERM");
  agentProc = null;
  stopAgentWatcher();
  // 释放防休眠
  if (sleepBlockId !== null) {
    powerSaveBlocker.stop(sleepBlockId);
    console.log("防休眠已释放");
    sleepBlockId = null;
  }
  return { ok: true };
}

function getAgentState() {
  if (!fs.existsSync(AGENT_STATE_FILE))
    return { phase: "stopped", running: !!agentProc };
  try {
    const data = JSON.parse(fs.readFileSync(AGENT_STATE_FILE, "utf-8"));
    data.running = !!agentProc;
    return data;
  } catch {
    return { phase: "unknown", running: !!agentProc };
  }
}

function getTasks(limit = 30) {
  try {
    if (!fs.existsSync(TASKS_FILE)) return [];
    const data = JSON.parse(fs.readFileSync(TASKS_FILE, "utf-8"));
    const tasks = Array.isArray(data) ? data : [];
    return tasks.slice(-Math.max(1, Number(limit) || 30)).reverse();
  } catch {
    return [];
  }
}

function getEvents(limit = 200) {
  try {
    if (!fs.existsSync(LOG_DIR)) return [];
    const files = fs
      .readdirSync(LOG_DIR)
      .filter((name) => /^events-\d{8}\.jsonl$/.test(name))
      .sort();
    const lines = [];
    for (const name of files) {
      const pathName = path.join(LOG_DIR, name);
      const content = fs.readFileSync(pathName, "utf-8");
      for (const line of content.split("\n")) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          lines.push(JSON.parse(trimmed));
        } catch {}
      }
    }
    return lines.slice(-Math.max(1, Number(limit) || 200)).reverse();
  } catch {
    return [];
  }
}

function listRules() {
  try {
    if (!fs.existsSync(RULES_FILE)) return [];
    const data = JSON.parse(fs.readFileSync(RULES_FILE, "utf-8"));
    const rules = Array.isArray(data) ? data : [];
    return rules.sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));
  } catch {
    return [];
  }
}

function saveRules(rules) {
  ensureRuntimeDir();
  fs.writeFileSync(RULES_FILE, JSON.stringify(rules, null, 2));
}

function upsertRule(rule) {
  const now = Math.floor(Date.now() / 1000);
  const nextRule = {
    id: rule.id || `rule_${Date.now()}`,
    name: rule.name || "未命名规则",
    target_date: rule.target_date || "auto",
    preferred_hours: Array.isArray(rule.preferred_hours) ? rule.preferred_hours : [],
    preferred_venue_names: Array.isArray(rule.preferred_venue_names) ? rule.preferred_venue_names : [],
    max_retries: Number(rule.max_retries) || 20,
    concurrent_attempts: Number(rule.concurrent_attempts) || 5,
    active: !!rule.active,
    updated_at: now,
    created_at: Number(rule.created_at) || now,
  };
  const rules = listRules();
  const idx = rules.findIndex((x) => x.id === nextRule.id);
  if (idx >= 0) rules[idx] = { ...rules[idx], ...nextRule };
  else rules.push(nextRule);
  saveRules(rules);
  return { ok: true, rule: nextRule };
}

function deleteRule(ruleId) {
  const rules = listRules();
  const next = rules.filter((r) => r.id !== ruleId);
  saveRules(next);
  return { ok: true };
}

function activateRule(ruleId) {
  const rules = listRules();
  const target = rules.find((r) => r.id === ruleId);
  if (!target) return { ok: false, msg: "规则不存在" };
  const cfg = loadConfig();
  const nextCfg = {
    ...cfg,
    booking: {
      ...(cfg.booking || {}),
      target_date: target.target_date,
      preferred_hours: target.preferred_hours || [],
      preferred_venue_names: target.preferred_venue_names || [],
      max_retries: Number(target.max_retries) || 20,
      concurrent_attempts: Number(target.concurrent_attempts) || 5,
    },
  };
  saveConfig(nextCfg);

  const nextRules = rules.map((r) => ({
    ...r,
    active: r.id === ruleId,
    updated_at: r.id === ruleId ? Math.floor(Date.now() / 1000) : r.updated_at,
  }));
  saveRules(nextRules);
  return { ok: true, rule_id: ruleId };
}

function getBookingRecords(limit = 30) {
  const tasks = getTasks(1000);
  const records = tasks
    .filter((t) => t.command === "booking.run")
    .map((t) => ({
      id: t.id,
      status: t.status,
      date: t.result?.date || t.payload?.date || "-",
      message: t.result?.message || t.error || "-",
      result: t.result?.result || "",
      trigger_source: t.trigger_source || "",
      created_at: t.created_at || 0,
      finished_at: t.finished_at || 0,
    }))
    .slice(0, Math.max(1, Number(limit) || 30));
  return records;
}

function startAgentWatcher() {
  stopAgentWatcher();
  agentWatcher = setInterval(() => {
    if (!fs.existsSync(AGENT_STATE_FILE)) return;
    try {
      const state = JSON.parse(fs.readFileSync(AGENT_STATE_FILE, "utf-8"));
      // Agent 需要人工登录 → 自动弹登录窗口
      if (state.needs_human_login && !loginWindow) {
        console.log("Agent 请求人工登录，弹出登录窗口");
        openLoginWindow();
        // 系统通知
        const { Notification } = require("electron");
        if (Notification.isSupported()) {
          new Notification({
            title: "需要手动登录",
            body: "体育馆预约系统需要验证码，请在弹出窗口中完成登录",
          }).show();
        }
      }
    } catch {}
  }, 3000);
}

function stopAgentWatcher() {
  if (agentWatcher) {
    clearInterval(agentWatcher);
    agentWatcher = null;
  }
}

// ─── IPC ───────────────────────────────────────────────
ipcMain.handle("get-status", () => getCookieStatus());
ipcMain.handle("open-login", () => openLoginWindow());
ipcMain.handle("push-cloud", (_, url, token) => pushToCloud(url, token));

ipcMain.handle("load-config", () => loadConfig());
ipcMain.handle("save-config", (_, cfg) => saveConfig(cfg));

ipcMain.handle("run-booking", (_, args) => runPython(args || []));
ipcMain.handle("stop-booking", () => stopPython());

ipcMain.handle("agent-start", () => startAgent());
ipcMain.handle("agent-stop", () => stopAgent());
ipcMain.handle("agent-state", () => getAgentState());
ipcMain.handle("get-tasks", (_, limit) => getTasks(limit));
ipcMain.handle("get-events", (_, limit) => getEvents(limit));
ipcMain.handle("list-rules", () => listRules());
ipcMain.handle("upsert-rule", (_, rule) => upsertRule(rule || {}));
ipcMain.handle("delete-rule", (_, ruleId) => deleteRule(ruleId));
ipcMain.handle("activate-rule", (_, ruleId) => activateRule(ruleId));
ipcMain.handle("get-booking-records", (_, limit) => getBookingRecords(limit));

// ─── 启动 ──────────────────────────────────────────────
app.whenReady().then(createMainWindow);
app.on("window-all-closed", () => {
  stopAgentWatcher();
  if (agentProc) agentProc.kill("SIGTERM");
  app.quit();
});
