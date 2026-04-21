const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  // Cookie
  getStatus: () => ipcRenderer.invoke("get-status"),

  // 登录
  openLogin: () => ipcRenderer.invoke("open-login"),
  onLoginResult: (cb) => ipcRenderer.on("login-result", (_, r) => cb(r)),

  // 配置
  loadConfig: () => ipcRenderer.invoke("load-config"),
  saveConfig: (cfg) => ipcRenderer.invoke("save-config", cfg),

  // 运行预约
  runBooking: (args) => ipcRenderer.invoke("run-booking", args),
  stopBooking: () => ipcRenderer.invoke("stop-booking"),
  onStdout: (cb) => ipcRenderer.on("py-stdout", (_, d) => cb(d)),
  onStderr: (cb) => ipcRenderer.on("py-stderr", (_, d) => cb(d)),
  onExit: (cb) => ipcRenderer.on("py-exit", (_, c) => cb(c)),

  // 云端推送
  pushCloud: (url, token) => ipcRenderer.invoke("push-cloud", url, token),

  // Agent
  agentStart: () => ipcRenderer.invoke("agent-start"),
  agentStop: () => ipcRenderer.invoke("agent-stop"),
  agentState: () => ipcRenderer.invoke("agent-state"),
  getTasks: (limit) => ipcRenderer.invoke("get-tasks", limit),
  getEvents: (limit) => ipcRenderer.invoke("get-events", limit),
  listRules: () => ipcRenderer.invoke("list-rules"),
  upsertRule: (rule) => ipcRenderer.invoke("upsert-rule", rule),
  deleteRule: (ruleId) => ipcRenderer.invoke("delete-rule", ruleId),
  activateRule: (ruleId) => ipcRenderer.invoke("activate-rule", ruleId),
  getBookingRecords: (limit) => ipcRenderer.invoke("get-booking-records", limit),
  onAgentStdout: (cb) => ipcRenderer.on("agent-stdout", (_, d) => cb(d)),
  onAgentStderr: (cb) => ipcRenderer.on("agent-stderr", (_, d) => cb(d)),
  onAgentExit: (cb) => ipcRenderer.on("agent-exit", (_, c) => cb(c)),
});
