/**
 * SZU Sports Venue Tracker SDK  v1.0.0
 * 深圳大学体育场地自动预约系统 · 前端埋点 SDK
 *
 * 用法:
 *   <script src="tracker.js"></script>
 *   <script>
 *     Tracker.init({ appId: 'szu-sports', endpoint: '/api/track' });
 *     Tracker.identify('user_123', { role: 'student' });
 *     Tracker.track('booking_confirmed', { venueId: 3, amount: 20 });
 *   </script>
 */

;(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.Tracker = factory();
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  /* ─────────────────────────────────────────
   * 常量 & 默认配置
   * ───────────────────────────────────────── */
  var VERSION = '1.0.0';
  var SDK_NAME = 'szu-sports-tracker';

  var DEFAULTS = {
    appId: 'szu-sports',
    endpoint: '/api/v1/track',
    batchSize: 10,          // 事件队列积累多少条后批量上报
    flushInterval: 5000,    // ms：定时批量上报间隔
    maxRetry: 3,            // 单批次最大重试次数
    retryDelay: 2000,       // ms：重试初始延迟（指数退避）
    sessionTimeout: 30 * 60 * 1000,  // ms：Session 超时（30分钟）
    debug: false,           // 开启后在控制台打印所有事件
    autoTrack: {
      pageView: true,       // 自动采集 page_view
      click: true,          // 自动采集带 data-track 属性的点击
      formSubmit: true,     // 自动采集表单提交
      pageLeave: true,      // 自动采集页面离开（停留时长）
    }
  };

  /* ─────────────────────────────────────────
   * 工具函数
   * ───────────────────────────────────────── */
  function uuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  function now() { return Date.now(); }

  function merge() {
    var result = {};
    for (var i = 0; i < arguments.length; i++) {
      var obj = arguments[i];
      if (obj && typeof obj === 'object') {
        for (var key in obj) {
          if (Object.prototype.hasOwnProperty.call(obj, key)) {
            result[key] = obj[key];
          }
        }
      }
    }
    return result;
  }

  function getStorage(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  function setStorage(key, val) {
    try { localStorage.setItem(key, val); } catch (e) {}
  }

  function getSessionStorage(key) {
    try { return sessionStorage.getItem(key); } catch (e) { return null; }
  }

  function setSessionStorage(key, val) {
    try { sessionStorage.setItem(key, val); } catch (e) {}
  }

  /* ─────────────────────────────────────────
   * Session 管理
   * ───────────────────────────────────────── */
  var Session = (function () {
    var SESSION_KEY = '_szu_sid';
    var SESSION_TS_KEY = '_szu_sid_ts';
    var SESSION_COUNT_KEY = '_szu_session_count';

    function isExpired(timeout) {
      var ts = parseInt(getSessionStorage(SESSION_TS_KEY), 10);
      return !ts || (now() - ts > timeout);
    }

    function refresh(timeout) {
      if (isExpired(timeout)) {
        var newId = uuid();
        setSessionStorage(SESSION_KEY, newId);
        // 累计 session 数
        var count = parseInt(getStorage(SESSION_COUNT_KEY), 10) || 0;
        setStorage(SESSION_COUNT_KEY, count + 1);
      }
      setSessionStorage(SESSION_TS_KEY, now());
      return getSessionStorage(SESSION_KEY);
    }

    function getId(timeout) {
      return refresh(timeout);
    }

    function getCount() {
      return parseInt(getStorage(SESSION_COUNT_KEY), 10) || 1;
    }

    return { getId: getId, getCount: getCount };
  })();

  /* ─────────────────────────────────────────
   * 设备 & 环境信息
   * ───────────────────────────────────────── */
  var DeviceInfo = (function () {
    var ua = navigator.userAgent;

    function getPlatform() {
      if (/iPhone|iPad|iPod/.test(ua)) return 'iOS';
      if (/Android/.test(ua)) return 'Android';
      if (/Win/.test(ua)) return 'Windows';
      if (/Mac/.test(ua)) return 'macOS';
      return 'Other';
    }

    function getBrowser() {
      if (/Edg\//.test(ua)) return 'Edge';
      if (/Chrome\//.test(ua) && !/Chromium/.test(ua)) return 'Chrome';
      if (/Firefox\//.test(ua)) return 'Firefox';
      if (/Safari\//.test(ua) && !/Chrome/.test(ua)) return 'Safari';
      return 'Other';
    }

    function isMobile() {
      return /Mobi|Android|iPhone|iPad/.test(ua);
    }

    function get() {
      return {
        platform: getPlatform(),
        browser: getBrowser(),
        is_mobile: isMobile(),
        screen_w: screen.width,
        screen_h: screen.height,
        viewport_w: window.innerWidth,
        viewport_h: window.innerHeight,
        language: navigator.language || 'zh-CN',
        timezone: Intl && Intl.DateTimeFormat ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'Asia/Shanghai',
      };
    }

    return { get: get };
  })();

  /* ─────────────────────────────────────────
   * 事件队列 & 上报
   * ───────────────────────────────────────── */
  var Queue = (function () {
    var _queue = [];
    var _timer = null;
    var _cfg = null;
    var _retryCount = 0;

    function flush() {
      if (!_queue.length) return;
      var batch = _queue.splice(0, _cfg.batchSize);
      send(batch, 0);
    }

    function send(batch, attempt) {
      if (_cfg.debug) {
        console.groupCollapsed('[Tracker] 上报 ' + batch.length + ' 条事件');
        batch.forEach(function (e) { console.log(e.event, e.properties); });
        console.groupEnd();
      }

      // Demo 环境：直接存入 localStorage 模拟上报
      if (!_cfg.endpoint || _cfg.endpoint === 'mock') {
        persistToMock(batch);
        return;
      }

      var payload = JSON.stringify({ events: batch, sdk: SDK_NAME, v: VERSION });

      var xhr = new XMLHttpRequest();
      xhr.open('POST', _cfg.endpoint, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.timeout = 8000;

      xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
          _retryCount = 0;
          if (_cfg.debug) console.log('[Tracker] ✅ 上报成功');
        } else {
          retry(batch, attempt);
        }
      };

      xhr.ontimeout = xhr.onerror = function () { retry(batch, attempt); };
      xhr.send(payload);
    }

    function retry(batch, attempt) {
      if (attempt >= _cfg.maxRetry) {
        if (_cfg.debug) console.warn('[Tracker] ❌ 超过最大重试次数，丢弃批次');
        return;
      }
      var delay = _cfg.retryDelay * Math.pow(2, attempt);
      setTimeout(function () { send(batch, attempt + 1); }, delay);
    }

    function persistToMock(batch) {
      try {
        var key = '_szu_track_events';
        var existing = JSON.parse(localStorage.getItem(key) || '[]');
        var merged = existing.concat(batch).slice(-500); // 最多保留500条
        localStorage.setItem(key, JSON.stringify(merged));
      } catch (e) {}
    }

    function start(cfg) {
      _cfg = cfg;
      _timer = setInterval(flush, cfg.flushInterval);
    }

    function stop() {
      if (_timer) { clearInterval(_timer); _timer = null; }
      flush(); // 页面卸载时立刻上报剩余
    }

    function push(event) {
      _queue.push(event);
      if (_queue.length >= _cfg.batchSize) flush();
    }

    return { start: start, stop: stop, push: push, flush: flush };
  })();

  /* ─────────────────────────────────────────
   * 核心 Tracker
   * ───────────────────────────────────────── */
  var _config = merge({}, DEFAULTS);
  var _userId = null;
  var _userProps = {};
  var _superProps = {};   // 全局超级属性，每条事件都会携带
  var _pageEnterTime = 0;
  var _anonymousId = null;
  var _initialized = false;

  function getAnonymousId() {
    if (!_anonymousId) {
      _anonymousId = getStorage('_szu_anon_id');
      if (!_anonymousId) {
        _anonymousId = uuid();
        setStorage('_szu_anon_id', _anonymousId);
      }
    }
    return _anonymousId;
  }

  function buildEvent(eventName, properties) {
    var sessionId = Session.getId(_config.sessionTimeout);
    var device = DeviceInfo.get();
    var base = {
      event_id: uuid(),
      event: eventName,
      timestamp: new Date().toISOString(),
      app_id: _config.appId,
      anonymous_id: getAnonymousId(),
      user_id: _userId || null,
      session_id: sessionId,
      session_count: Session.getCount(),
      page_url: location.href,
      page_path: location.pathname,
      page_title: document.title,
      referrer: document.referrer || '',
    };
    return {
      event_id: base.event_id,
      event: base.event,
      timestamp: base.timestamp,
      properties: merge(base, device, _superProps, _userProps, properties || {}),
    };
  }

  /* ─────────────────────────────────────────
   * 自动采集：页面浏览
   * ───────────────────────────────────────── */
  function autoTrackPageView() {
    _pageEnterTime = now();
    var params = {};
    try {
      var sp = new URLSearchParams(location.search);
      sp.forEach(function (v, k) { params['utm_' + k] = v; });
    } catch (e) {}
    track('page_view', merge({
      page_url: location.href,
      page_path: location.pathname,
      page_title: document.title,
      referrer: document.referrer || '',
    }, params));
  }

  /* ─────────────────────────────────────────
   * 自动采集：点击事件
   * ───────────────────────────────────────── */
  function autoTrackClick(e) {
    var el = e.target;
    // 向上查找带 data-track 的元素
    while (el && el !== document.body) {
      if (el.dataset && el.dataset.track) {
        var props = {};
        // 采集 data-track-* 属性
        for (var key in el.dataset) {
          if (key !== 'track' && key.indexOf('track') === 0) {
            var propName = key.slice(5).replace(/([A-Z])/g, function (m) { return '_' + m.toLowerCase(); }).replace(/^_/, '');
            props[propName] = el.dataset[key];
          }
        }
        props.element_text = (el.innerText || el.value || '').trim().slice(0, 100);
        props.element_id = el.id || '';
        props.element_class = el.className || '';
        track(el.dataset.track, props);
        break;
      }
      el = el.parentElement;
    }
  }

  /* ─────────────────────────────────────────
   * 自动采集：表单提交
   * ───────────────────────────────────────── */
  function autoTrackForm(e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    var eventName = form.dataset.trackSubmit || 'form_submit';
    track(eventName, {
      form_id: form.id || '',
      form_name: form.name || '',
      form_action: form.action || '',
    });
  }

  /* ─────────────────────────────────────────
   * 自动采集：页面离开（停留时长）
   * ───────────────────────────────────────── */
  function autoTrackPageLeave() {
    var duration = _pageEnterTime ? Math.round((now() - _pageEnterTime) / 1000) : 0;
    // 使用 sendBeacon 确保卸载时能发出
    var event = buildEvent('page_leave', {
      page_stay_seconds: duration,
      page_path: location.pathname,
    });
    var payload = JSON.stringify({ events: [event], sdk: SDK_NAME, v: VERSION });
    if (navigator.sendBeacon && _config.endpoint && _config.endpoint !== 'mock') {
      navigator.sendBeacon(_config.endpoint, payload);
    } else {
      Queue.push(event);
      Queue.flush();
    }
  }

  /* ─────────────────────────────────────────
   * 公开 API
   * ───────────────────────────────────────── */

  /**
   * 初始化 SDK
   * @param {Object} options - 配置项（覆盖 DEFAULTS）
   */
  function init(options) {
    if (_initialized) {
      console.warn('[Tracker] 已初始化，请勿重复调用 init()');
      return;
    }
    _config = merge(DEFAULTS, options || {});
    _config.autoTrack = merge(DEFAULTS.autoTrack, (options || {}).autoTrack || {});

    Queue.start(_config);

    // 绑定自动采集
    if (_config.autoTrack.pageView) {
      autoTrackPageView();
      // SPA 路由变化监听
      var origPush = history.pushState;
      var origReplace = history.replaceState;
      history.pushState = function () {
        origPush.apply(history, arguments);
        setTimeout(autoTrackPageView, 0);
      };
      history.replaceState = function () {
        origReplace.apply(history, arguments);
        setTimeout(autoTrackPageView, 0);
      };
      window.addEventListener('popstate', function () { setTimeout(autoTrackPageView, 0); });
    }

    if (_config.autoTrack.click) {
      document.addEventListener('click', autoTrackClick, true);
    }

    if (_config.autoTrack.formSubmit) {
      document.addEventListener('submit', autoTrackForm, true);
    }

    if (_config.autoTrack.pageLeave) {
      window.addEventListener('beforeunload', autoTrackPageLeave);
      document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'hidden') autoTrackPageLeave();
      });
    }

    _initialized = true;
    if (_config.debug) console.log('[Tracker] ✅ 初始化完成', _config);
  }

  /**
   * 手动追踪事件
   * @param {string} eventName - 事件名称（snake_case）
   * @param {Object} properties - 事件属性
   */
  function track(eventName, properties) {
    if (!eventName || typeof eventName !== 'string') {
      console.warn('[Tracker] track() 需要传入事件名称');
      return;
    }
    var event = buildEvent(eventName, properties);
    Queue.push(event);
    return event;
  }

  /**
   * 设置用户 ID（登录后调用）
   * @param {string} userId
   * @param {Object} traits - 用户属性
   */
  function identify(userId, traits) {
    _userId = userId;
    _userProps = merge(_userProps, traits || {});
    track('user_identify', merge({ user_id: userId }, traits || {}));
    if (_config.debug) console.log('[Tracker] identify:', userId, traits);
  }

  /**
   * 用户退出登录
   */
  function reset() {
    _userId = null;
    _userProps = {};
    track('user_logout', {});
  }

  /**
   * 设置全局超级属性（每条事件都会携带）
   * @param {Object} props
   */
  function registerSuperProps(props) {
    _superProps = merge(_superProps, props || {});
  }

  /**
   * 手动触发立即上报
   */
  function flush() {
    Queue.flush();
  }

  /**
   * 获取本地 mock 存储的事件（Demo 调试用）
   * @returns {Array}
   */
  function getLocalEvents() {
    try {
      return JSON.parse(localStorage.getItem('_szu_track_events') || '[]');
    } catch (e) { return []; }
  }

  /**
   * 清空本地 mock 事件（Demo 调试用）
   */
  function clearLocalEvents() {
    try { localStorage.removeItem('_szu_track_events'); } catch (e) {}
  }

  /* ─────────────────────────────────────────
   * 预定义事件辅助方法（业务快捷方式）
   * ───────────────────────────────────────── */
  var Events = {
    // 认证
    loginClick:          function (m) { return track('login_click', { method: m || 'password' }); },
    loginSuccess:        function (u) { return track('login_success', { user_id: u }); },
    loginFail:           function (r) { return track('login_fail', { reason: r }); },
    registerStart:       function () { return track('register_start', {}); },
    registerStepComplete: function (s) { return track('register_step_complete', { step: s }); },
    registerSuccess:     function (u) { return track('register_success', { user_id: u }); },
    forgotPasswordStart: function () { return track('forgot_password_start', {}); },

    // 场地浏览
    venueSearch:         function (q, r) { return track('venue_search', { query: q, result_count: r }); },
    venueFilter:         function (t) { return track('venue_filter', { filter_type: t }); },
    venueCardClick:      function (id, n) { return track('venue_card_click', { venue_id: id, venue_name: n }); },
    venueDetailView:     function (id, n) { return track('venue_detail_view', { venue_id: id, venue_name: n }); },
    venueFavorite:       function (id, a) { return track('venue_favorite', { venue_id: id, action: a }); },

    // 预约流程
    slotSelect:          function (id, t) { return track('slot_select', { slot_id: id, slot_time: t }); },
    slotLock:            function (id) { return track('slot_lock', { slot_id: id }); },
    slotUnlock:          function (id, r) { return track('slot_unlock', { slot_id: id, reason: r }); },
    bookingConfirmClick: function (a) { return track('booking_confirm_click', { amount: a }); },
    bookingSuccess:      function (id, a) { return track('booking_success', { booking_id: id, amount: a }); },
    bookingCancel:       function (id, r) { return track('booking_cancel', { booking_id: id, reason: r }); },

    // 支付
    paymentStart:        function (m, a) { return track('payment_start', { method: m, amount: a }); },
    paymentSuccess:      function (id, a) { return track('payment_success', { order_id: id, amount: a }); },
    paymentFail:         function (r) { return track('payment_fail', { reason: r }); },
    paymentTimeout:      function () { return track('payment_timeout', {}); },

    // 自动预约
    autoRuleCreate:      function (c) { return track('auto_rule_create', { config: c }); },
    autoRuleToggle:      function (id, s) { return track('auto_rule_toggle', { rule_id: id, enabled: s }); },
    autoBookingSuccess:  function (id) { return track('auto_booking_success', { rule_id: id }); },
    memberGateHit:       function (f) { return track('member_gate_hit', { feature: f }); },

    // 会员
    membershipView:      function () { return track('membership_view', {}); },
    membershipPurchaseClick: function (p) { return track('membership_purchase_click', { plan: p }); },
    membershipPurchaseSuccess: function (p, a) { return track('membership_purchase_success', { plan: p, amount: a }); },

    // 积分
    pointsRedeemClick:   function (i) { return track('points_redeem_click', { item_id: i }); },
    pointsRedeemSuccess: function (i, p) { return track('points_redeem_success', { item_id: i, points: p }); },
    inviteShareClick:    function () { return track('invite_share_click', {}); },

    // 评价
    reviewStart:         function (id) { return track('review_start', { booking_id: id }); },
    reviewSubmit:        function (id, r) { return track('review_submit', { booking_id: id, rating: r }); },

    // 通知
    notificationRead:    function (id, t) { return track('notification_read', { notif_id: id, type: t }); },
    notificationAllRead: function () { return track('notification_all_read', {}); },

    // 错误
    jsError:             function (m, s) { return track('js_error', { message: m, stack: s }); },
    apiError:            function (u, c) { return track('api_error', { url: u, status_code: c }); },
  };

  // 自动采集 JS 全局错误
  window.addEventListener('error', function (e) {
    if (_initialized) Events.jsError(e.message, e.filename + ':' + e.lineno);
  });
  window.addEventListener('unhandledrejection', function (e) {
    if (_initialized) Events.jsError('UnhandledRejection: ' + (e.reason || ''), '');
  });

  /* ─────────────────────────────────────────
   * 导出
   * ───────────────────────────────────────── */
  return {
    init: init,
    track: track,
    identify: identify,
    reset: reset,
    registerSuperProps: registerSuperProps,
    flush: flush,
    getLocalEvents: getLocalEvents,
    clearLocalEvents: clearLocalEvents,
    Events: Events,
    VERSION: VERSION,
  };
}));
