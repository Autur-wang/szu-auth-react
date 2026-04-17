import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Button, Dialog, Layout } from 'animal-crossing-ui';
// Input 未从主入口导出，深度导入 dist 目录
import Input from 'animal-crossing-ui/dist/lib/input';

/* ============================================================
 *  深大体育 · 登录 / 注册
 *  真实 import from 'animal-crossing-ui'
 *  Apple Skin 外层 + Liquid Glass 玻璃卡
 * ============================================================ */

const LS = {
  USERS: 'szu_auth.users',
  CURRENT: 'szu_auth.currentUser',
  REMEMBER: 'szu_auth.remembered',
};

function load(k, d) {
  try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; }
  catch { return d; }
}
function save(k, v) { localStorage.setItem(k, JSON.stringify(v)); }

async function sha256(str) {
  const data = new TextEncoder().encode(str);
  const buf = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('');
}

function validatePassword(pwd) {
  return pwd.length >= 8 && /[A-Za-z]/.test(pwd) && /\d/.test(pwd);
}
function pwdStrength(pwd) {
  let s = 0;
  if (pwd.length >= 8)  s++;
  if (pwd.length >= 12) s++;
  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) s++;
  if (/\d/.test(pwd) && /[^\w\s]/.test(pwd)) s++;
  return s;
}

export default function App() {
  const [tab, setTab] = useState('login');
  const [toasts, setToasts] = useState([]);
  const [compat, setCompat] = useState('');
  const [dialog, setDialog] = useState(null);

  useEffect(() => {
    // 兼容性提示
    const hasBackdrop = CSS.supports('backdrop-filter', 'blur(1px)')
                      || CSS.supports('-webkit-backdrop-filter', 'blur(1px)');
    const hasSvgBackdrop = CSS.supports('backdrop-filter', 'url(#a)');
    if (!hasBackdrop) setCompat('✱ 浏览器不支持 backdrop-filter —— 已降级为半透明纯色');
    else if (!hasSvgBackdrop) setCompat('✱ 不支持 SVG 位移玻璃（仅 Chrome/Chromium）—— 已用 blur+saturate 降级');
    else setCompat('✓ Liquid Glass 全部生效（Chrome 原生 SVG 位移）');

    // 已登录 → 2 秒后跳转
    const cur = load(LS.CURRENT, null);
    if (cur && Date.now() - cur.loginAt < 7 * 86400 * 1000) {
      toast(`已识别你：${cur.name || cur.sid}。2 秒后自动进入预约…`);
      setTimeout(() => { window.location.href = 'http://localhost:8765/szu-booking/index.html'; }, 2000);
    }
  }, []);

  function toast(msg, kind = 'info') {
    const id = Math.random().toString(36).slice(2);
    setToasts(t => [...t, { id, msg, kind }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 2800);
  }

  return (
    <>
      {/* 背景层 */}
      <div className="stage" aria-hidden="true">
        <div className="blob blob--1" />
        <div className="blob blob--2" />
        <div className="blob blob--3" />
        <div className="stage__grid" />
      </div>

      {/* 玻璃条 Nav */}
      <nav className="nav">
        <span className="nav__mark" />
        <span className="nav__title">深大体育</span>
        <span className="nav__spacer" />
        <div className="nav__links">
          <a href="http://localhost:8765/szu-booking/index.html">预约</a>
          <a href="#about">关于</a>
          <a href="#">支持</a>
        </div>
        <span className="nav__powered">
          powered by{' '}
          <code>animal-crossing-ui</code>
        </span>
      </nav>

      <div className="page">
        {/* 左侧 Hero */}
        <section className="hero">
          <span className="hero__eyebrow">SZU Athletics · 2026</span>
          <h1 className="hero__title">
            预约场地,<br /><em>从掌心开始。</em>
          </h1>
          <p className="hero__lede">
            用你的学号登录，设好自动抢号。全站组件来自真实的 <code>animal-crossing-ui</code> React 库，穿苹果视觉的外套。
          </p>

          <div className="hero__points">
            <Point icon="⚡" head="放号即抢，0.3 秒提交" sub="连续重试 · 备选时段自动回落" />
            <Point icon="🏀" head="4 大主力场馆" sub="篮球 · 羽毛球 · 游泳 · 田径" />
            <Point icon="🔒" head="学号 + 校园邮箱双因子" sub="所有凭据只存本机浏览器" />
          </div>
        </section>

        {/* 右侧玻璃 Auth 卡 */}
        <section className="auth-wrap">
          <div className="glass-card">
            <div className="glass-card__head">
              <div className="glass-card__mark">SZU</div>
              <div>
                <h2 className="glass-card__title">
                  {tab === 'login' ? '欢迎回来' : '创建账号'}
                </h2>
                <p className="glass-card__sub">
                  {tab === 'login' ? '用你的深大账号登录' : '只需 60 秒，即可开始使用'}
                </p>
              </div>
            </div>

            {/* Tab 切换器 */}
            <div className="tabs" role="tablist">
              <button
                className={`tab ${tab === 'login' ? 'is-active' : ''}`}
                onClick={() => setTab('login')}
                role="tab"
              >登录</button>
              <button
                className={`tab ${tab === 'register' ? 'is-active' : ''}`}
                onClick={() => setTab('register')}
                role="tab"
              >注册</button>
            </div>

            {tab === 'login'
              ? <LoginForm onToast={toast} onShowDialog={setDialog} onSwitch={setTab} />
              : <RegisterForm onToast={toast} onShowDialog={setDialog} onSwitch={setTab} />
            }
          </div>
        </section>
      </div>

      {/* Toast 栈 */}
      <div className="toasts">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast--${t.kind}`}>{t.msg}</div>
        ))}
      </div>

      {/* gui-dialog 真实渲染 */}
      {dialog && (
        <Dialog
          visible={true}
          titleNode={dialog.title}
          onCancel={() => setDialog(null)}
          buttons={
            <>
              {dialog.buttons.map((b, i) => (
                <Button
                  key={i}
                  colortype={b.kind}
                  onClick={() => { setDialog(null); b.onClick && b.onClick(); }}
                >{b.label}</Button>
              ))}
            </>
          }
        >
          {dialog.content}
        </Dialog>
      )}

      <div className="hint">{compat}</div>
    </>
  );
}

/* ============================================================
 *  Login Form —— 真实 Input / Button
 * ============================================================ */
function LoginForm({ onToast, onShowDialog, onSwitch }) {
  const [id, setId] = useState(() => load(LS.REMEMBER, ''));
  const [pwd, setPwd] = useState('');
  const [remember, setRemember] = useState(true);
  const [showPwd, setShowPwd] = useState(false);
  const [errors, setErrors] = useState({});

  async function submit(e) {
    e.preventDefault();
    const errs = {};
    if (!id.trim()) errs.id = '请输入学号或校园邮箱';
    if (!pwd) errs.pwd = '请输入密码';
    setErrors(errs);
    if (Object.keys(errs).length) return;

    const users = load(LS.USERS, []);
    const user = users.find(u => u.sid === id.trim() || u.email.toLowerCase() === id.trim().toLowerCase());
    if (!user) {
      setErrors({ id: '账号不存在，先去注册吧' });
      onToast('账号不存在', 'error');
      return;
    }
    const h = await sha256(pwd);
    if (h !== user.pwdHash) {
      setErrors({ pwd: '密码不正确' });
      onToast('密码错误', 'error');
      return;
    }
    save(LS.CURRENT, { sid: user.sid, name: user.name, email: user.email, loginAt: Date.now() });
    if (remember) save(LS.REMEMBER, id.trim()); else localStorage.removeItem(LS.REMEMBER);
    onToast(`✓ 登录成功，欢迎 ${user.name}`, 'success');
    setTimeout(() => { window.location.href = 'http://localhost:8765/szu-booking/index.html'; }, 900);
  }

  function forgot(e) {
    e.preventDefault();
    onShowDialog({
      title: '忘记密码',
      content: '演示系统没有邮件通道。真实环境会发送重置链接到你的深大邮箱。',
      buttons: [{ label: '知道了', kind: 'primary' }],
    });
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <Field label="学号 · 邮箱" icon="👤" error={errors.id}>
        <Input
          name="id"
          type="text"
          autoComplete="username"
          placeholder="20xx2xxxxxx · xxx@szu.edu.cn"
          value={id}
          onChange={e => setId(e.target.value)}
        />
      </Field>
      <Field label="密码" icon="🔑" error={errors.pwd}
             trailing={
               <button type="button" className="field__reveal" onClick={() => setShowPwd(!showPwd)}>
                 {showPwd ? '隐藏' : '显示'}
               </button>
             }>
        <Input
          name="password"
          type={showPwd ? 'text' : 'password'}
          autoComplete="current-password"
          placeholder="••••••••"
          value={pwd}
          onChange={e => setPwd(e.target.value)}
        />
      </Field>

      <div className="row-extra">
        <label className="check">
          <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
          <span className="check__box" />
          <span>记住我</span>
        </label>
        <a href="#" onClick={forgot}>忘记密码?</a>
      </div>

      <Button colortype="blue" className="primary w-full" type="submit">登录进入</Button>

      <div className="divider">或使用</div>
      <div className="social-row">
        <SocialBtn icon="🪶" label="飞书" onClick={() => socialDemo('lark', onToast)} />
        <SocialBtn icon="🟢" label="微信" onClick={() => socialDemo('wechat', onToast)} />
        <SocialBtn icon="🎓" label="深大 SSO" onClick={() => socialDemo('szu', onToast)} />
      </div>

      <p className="switch-link">
        第一次来？<button type="button" onClick={() => onSwitch('register')}>创建账号</button>
      </p>
    </form>
  );
}

/* ============================================================
 *  Register Form
 * ============================================================ */
function RegisterForm({ onToast, onShowDialog, onSwitch }) {
  const [form, setForm] = useState({ name: '', sid: '', email: '', pwd: '', pwd2: '', agree: false });
  const [showPwd, setShowPwd] = useState(false);
  const [errors, setErrors] = useState({});
  const strength = useMemo(() => pwdStrength(form.pwd), [form.pwd]);
  const strengthLabel = ['太弱', '一般', '较好', '很棒', '极强'][strength];

  function set(k, v) { setForm(f => ({ ...f, [k]: v })); }

  async function submit(e) {
    e.preventDefault();
    const errs = {};
    if (!form.name.trim()) errs.name = '请输入真实姓名';
    if (!/^20\d{2}2\d{6}$/.test(form.sid.trim())) errs.sid = '10 位学号，格式 20xx2xxxxxx';
    if (!/^[^\s@]+@(mails\.)?szu\.edu\.cn$/i.test(form.email.trim())) errs.email = '请输入 @szu.edu.cn 或 @mails.szu.edu.cn 邮箱';
    if (!validatePassword(form.pwd)) errs.pwd = '至少 8 位，包含字母和数字';
    if (form.pwd !== form.pwd2) errs.pwd2 = '两次输入不一致';
    if (!form.agree) { onToast('请先同意服务协议', 'error'); errs.agree = 1; }
    setErrors(errs);
    if (Object.keys(errs).length) {
      onToast('请修正标红的字段', 'error');
      return;
    }
    const users = load(LS.USERS, []);
    if (users.find(u => u.sid === form.sid.trim())) {
      setErrors({ sid: '这个学号已经注册过了' });
      onToast('学号已存在，直接登录吧', 'error');
      return;
    }
    if (users.find(u => u.email.toLowerCase() === form.email.trim().toLowerCase())) {
      setErrors({ email: '这个邮箱已绑定其它账号' });
      onToast('邮箱已被占用', 'error');
      return;
    }
    const h = await sha256(form.pwd);
    users.push({
      sid: form.sid.trim(), name: form.name.trim(), email: form.email.trim(),
      pwdHash: h, createdAt: Date.now(),
    });
    save(LS.USERS, users);
    save(LS.CURRENT, { sid: form.sid.trim(), name: form.name.trim(), email: form.email.trim(), loginAt: Date.now() });
    onToast(`✓ ${form.name.trim()} 注册成功，正在为你登录`, 'success');
    setTimeout(() => { window.location.href = 'http://localhost:8765/szu-booking/index.html'; }, 1100);
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <div className="form__row">
        <Field label="姓名" error={errors.name}>
          <Input name="name" value={form.name} onChange={e => set('name', e.target.value)} placeholder="张同学" />
        </Field>
        <Field label="学号" error={errors.sid}>
          <Input name="sid" value={form.sid} onChange={e => set('sid', e.target.value)} placeholder="20xx2xxxxxx" inputMode="numeric" />
        </Field>
      </div>

      <Field label="校园邮箱" icon="✉️" error={errors.email}>
        <Input name="email" type="email" value={form.email} onChange={e => set('email', e.target.value)} placeholder="name@mails.szu.edu.cn" autoComplete="email" />
      </Field>

      <Field label="密码" icon="🔑" error={errors.pwd}
             trailing={<button type="button" className="field__reveal" onClick={() => setShowPwd(!showPwd)}>{showPwd ? '隐藏' : '显示'}</button>}>
        <Input name="password" type={showPwd ? 'text' : 'password'} value={form.pwd} onChange={e => set('pwd', e.target.value)} placeholder="至少 8 位，含字母+数字" autoComplete="new-password" />
        <div className="strength">
          {[1,2,3,4].map(i => (
            <div key={i} className={`strength__bar ${strength >= i ? 'is-on-' + Math.min(4, strength) : ''}`} />
          ))}
        </div>
        <p className="strength__label">
          {form.pwd.length === 0 ? '密码强度' : `密码强度：${strengthLabel}`}
        </p>
      </Field>

      <Field label="确认密码" icon="✓" error={errors.pwd2}>
        <Input name="password2" type={showPwd ? 'text' : 'password'} value={form.pwd2} onChange={e => set('pwd2', e.target.value)} placeholder="再输一次" autoComplete="new-password" />
      </Field>

      <div className="row-extra">
        <label className="check">
          <input type="checkbox" checked={form.agree} onChange={e => set('agree', e.target.checked)} />
          <span className="check__box" />
          <span style={{ fontSize: 12 }}>
            我已阅读并同意{' '}
            <a href="#" onClick={e => e.preventDefault()} style={{ color: 'var(--color-link)' }}>服务协议</a>
            {' '}和{' '}
            <a href="#" onClick={e => e.preventDefault()} style={{ color: 'var(--color-link)' }}>隐私政策</a>
          </span>
        </label>
      </div>

      <Button colortype="blue" className="primary w-full" type="submit">创建账号</Button>

      <p className="switch-link">
        已经有账号?<button type="button" onClick={() => onSwitch('login')}>直接登录</button>
      </p>
    </form>
  );
}

/* ============================================================
 *  小部件
 * ============================================================ */
function Field({ label, icon, error, children, trailing }) {
  return (
    <div className={`field ${icon ? 'field--with-icon' : ''} ${error ? 'has-error' : ''}`}>
      <span className="field__label">{label}</span>
      {icon && <span className="field__icon">{icon}</span>}
      {children}
      {trailing}
      {error && <p className="field__error">{error}</p>}
    </div>
  );
}

function Point({ icon, head, sub }) {
  return (
    <div className="point">
      <span className="point__icon">{icon}</span>
      <div>
        <div className="point__head">{head}</div>
        <div className="point__sub">{sub}</div>
      </div>
    </div>
  );
}

function SocialBtn({ icon, label, onClick }) {
  return (
    <button type="button" className="btn-glass" onClick={onClick}>
      <span className="btn-glass__icon">{icon}</span>
      {label}
    </button>
  );
}

function socialDemo(provider, onToast) {
  const names = { lark: '飞书', wechat: '微信', szu: '深大 SSO' };
  onToast(`${names[provider]} 登录演示：模拟跳转中…`);
  setTimeout(() => {
    const demoUser = {
      sid: '20222' + Math.floor(100000 + Math.random() * 900000),
      name: `${names[provider]}同学`,
      email: `demo-${provider}@mails.szu.edu.cn`,
      loginAt: Date.now(),
    };
    save(LS.CURRENT, demoUser);
    onToast(`✓ 欢迎 ${demoUser.name}`, 'success');
    setTimeout(() => { window.location.href = 'http://localhost:8765/szu-booking/index.html'; }, 900);
  }, 1500);
}
