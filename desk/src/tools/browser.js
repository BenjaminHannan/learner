'use strict';
// Built-in browser: a WebContentsView in the persistent partition "persist:desk", driven from the main process.

const { browserAfter } = require('./after');
const { attachSourceRead } = require('../evidence');
const { normalizeUrl, NET_FAIL } = require('../urlguard');

const SNAPSHOT_MAX = 3500;
const PAGE_CHARS = 6000;

// ---- page-side scripts (serialized into the page) ---------------------------------------------
function pageSnapshot(maxEls) {
  const old = document.querySelectorAll('[data-desk-id]');
  for (const o of old) { o.removeAttribute('data-desk-id'); o.removeAttribute('data-desk-sensitive'); }
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox],[role=switch],[role=option],[contenteditable=""],[contenteditable=true],[onclick],[tabindex]:not([tabindex="-1"])';
  const vw = window.innerWidth, vh = window.innerHeight;
  const clean = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
  const lines = [];
  let id = 0;
  const seen = new Set();
  for (const el of document.querySelectorAll(sel)) {
    if (id >= maxEls) break;
    if (seen.has(el)) continue;
    seen.add(el);
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) === 0) continue;
    if (el.disabled) continue;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    let label = el.getAttribute('aria-label') || '';
    if (!label && el.id) { const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]'); if (l) label = l.innerText; }
    if (!label && (tag === 'input' || tag === 'textarea' || tag === 'select')) label = el.placeholder || el.getAttribute('name') || el.title || '';
    if (!label && tag === 'input' && /^(submit|button|reset)$/.test(type)) label = el.value;
    if (!label) label = el.innerText || el.textContent || '';
    if (!label) label = el.title || el.getAttribute('alt') || (el.querySelector('img') && el.querySelector('img').alt) || '';
    label = clean(label, 60);
    id++;
    el.setAttribute('data-desk-id', String(id));
    let line;
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
      const hint = ((el.name || '') + ' ' + (el.id || '') + ' ' + (el.getAttribute('autocomplete') || '')).toLowerCase();
      let sens = '';
      if (type === 'password') sens = 'password';
      else if (/cc-(number|csc|exp)|card.?(num|number)|cardnumber|cvv|cvc|ccnum|security.?code/.test(hint)) sens = 'payment';
      if (sens) el.setAttribute('data-desk-sensitive', sens);
      const kind = tag === 'input' ? (type || 'text') : tag;
      const t = tag === 'input' ? 'input(' + kind + (sens === 'payment' ? ',payment' : '') + ')' : tag;
      let val = '';
      if (type === 'password') val = el.value ? '••••' : '';
      else if (type === 'checkbox' || type === 'radio') val = el.checked ? 'checked' : 'unchecked';
      else if (tag === 'select') val = clean(el.options && el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : el.value, 40);
      else if (sens === 'payment') val = el.value ? '••••' : '';
      else val = clean(el.value, 50);
      line = '[' + id + '] ' + t + ' "' + label + '" value="' + val + '"';
    } else if (tag === 'a') {
      const href = el.getAttribute('href') || '';
      line = '[' + id + '] link "' + label + '" -> ' + clean(href, 80);
    } else {
      line = '[' + id + '] ' + (tag === 'button' || el.getAttribute('role') === 'button' ? 'button' : (el.getAttribute('role') || tag)) + ' "' + label + '"';
    }
    lines.push(line);
  }
  const text = clean(document.body ? document.body.innerText : '', 800);
  // evidence for the "After" note: the focused element's line (values already masked above) and visible error/alert text
  const ae = document.activeElement;
  const fid = ae && ae.getAttribute ? Number(ae.getAttribute('data-desk-id')) : 0;
  const focus = fid && lines[fid - 1] ? lines[fid - 1] : '';
  const alerts = [];
  try {
    for (const a of document.querySelectorAll('[role=alert],[aria-live=assertive],.error,.errors,.alert,.alert-danger,.invalid-feedback,.field-error,.form-error,[class*=error-message],[class*=errorMessage]')) {
      const r = a.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      const t = clean(a.innerText || '', 100);
      if (t && !alerts.includes(t)) alerts.push(t);
      if (alerts.length >= 2) break;
    }
  } catch (e) { /* ignore */ }
  return { url: location.href, title: document.title, lines, text, count: id, focus, alerts };
}

function pageReadText() {
  const cands = Array.from(document.querySelectorAll('main,article,[role=main]'));
  let best = document.body;
  let bestLen = 0;
  for (const c of cands) { const l = (c.innerText || '').length; if (l > bestLen) { best = c; bestLen = l; } }
  if (!best || bestLen < 400) best = document.body;
  const raw = best.innerText;
  const lines = String(raw || '').split('\n').map((l) => l.replace(/\s+/g, ' ').trim()).filter(Boolean);
  return lines.join('\n');
}

// Re-measure just before the click: a page that moved during the badge pause (claude.ai's login buttons shift as it
// loads) would otherwise get the click on the old spot, i.e. on the button that slid there (Ben Oct 28: Google -> Apple).
function pagePoint(id) {
  const el = document.querySelector('[data-desk-id="' + id + '"]');
  if (!el) return { ok: false };
  const r = el.getBoundingClientRect();
  const x = Math.round(r.left + r.width / 2), y = Math.round(r.top + r.height / 2);
  const hit = document.elementFromPoint(x, y);
  return { ok: true, x, y, hit: !!hit && (hit === el || el.contains(hit) || hit.contains(el)) };
}

function pagePrepare(id, wantPoint) {
  const el = document.querySelector('[data-desk-id="' + id + '"]');
  if (!el) return { ok: false, error: 'no element [' + id + '] in the latest snapshot (take a new one)' };
  el.scrollIntoView({ block: 'center', inline: 'center' });
  const r = el.getBoundingClientRect();
  const x = Math.round(r.left + r.width / 2), y = Math.round(r.top + r.height / 2);
  const flash = () => {
    const b = document.createElement('div');
    b.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;left:' + (r.left - 3) + 'px;top:' + (r.top - 3) + 'px;width:' + (r.width + 6) + 'px;height:' + (r.height + 6) + 'px;border:2px solid #f5a524;border-radius:6px;box-shadow:0 0 0 3px rgba(245,165,36,.25);transition:opacity .5s .5s;opacity:1';
    const tag = document.createElement('div');
    tag.textContent = '#' + id;
    tag.style.cssText = 'position:absolute;top:-18px;left:-2px;background:#f5a524;color:#14110f;font:700 11px/16px -apple-system,sans-serif;padding:0 6px;border-radius:4px';
    b.appendChild(tag);
    document.documentElement.appendChild(b);
    requestAnimationFrame(() => { b.style.opacity = '0'; });
    setTimeout(() => b.remove(), 1200);
  };
  flash();
  const hit = document.elementFromPoint(x, y);
  return { ok: true, x, y, hit: !!hit && (hit === el || el.contains(hit) || hit.contains(el)), sensitive: el.getAttribute('data-desk-sensitive') || '', tag: el.tagName.toLowerCase(), label: (el.getAttribute('aria-label') || el.innerText || el.placeholder || el.getAttribute('name') || '').replace(/\s+/g, ' ').trim().slice(0, 40) };
}

function pageFocusSelect(id) {
  const el = document.querySelector('[data-desk-id="' + id + '"]');
  if (!el) return { ok: false };
  el.focus();
  if (typeof el.select === 'function' && /^(input|textarea)$/i.test(el.tagName)) { try { el.select(); } catch (e) { /* some types disallow select */ } }
  else if (el.isContentEditable) document.execCommand('selectAll');
  return { ok: true, editable: /^(input|textarea)$/i.test(el.tagName) || el.isContentEditable };
}

function pageEnsureValue(id, text) {
  const el = document.querySelector('[data-desk-id="' + id + '"]');
  if (!el) return false;
  if (/^(input|textarea)$/i.test(el.tagName)) {
    if (el.value === text) return true;
    const proto = el.tagName.toLowerCase() === 'input' ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, text);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }
  return true;
}

const call = (fn, ...args) => '(' + fn.toString() + ').apply(null,' + JSON.stringify(args) + ')';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// webRequest listeners are one per session, so one dispatcher serves every Browser (by webContents id).
const registry = new Map(); // webContents id -> Browser
const wired = new WeakSet();
function wireSession(ses) {
  if (wired.has(ses)) return;
  wired.add(ses);
  const hit = (d, fn) => { const b = registry.get(d.webContentsId); if (b) fn(b); };
  // Requests in flight, by id: a redirect fires onBeforeRequest again for the same request (a counter went up for good and every later
  // step waited the full 8 s), and a WebSocket stays open as long as the page does, so it never counts.
  ses.webRequest.onBeforeRequest((d, cb) => { hit(d, (b) => { if (d.resourceType !== 'webSocket') b.reqs.add(d.id); b.lastActivity = Date.now(); }); cb({}); });
  const done = (d) => hit(d, (b) => { b.reqs.delete(d.id); b.lastActivity = Date.now(); });
  ses.webRequest.onCompleted(done);
  ses.webRequest.onErrorOccurred(done);
}

// a sign-in provider's popup (it needs window.opener to hand the sign-in back to the page that opened it)
const AUTH_HOSTS = ['accounts.google.com', 'appleid.apple.com', 'login.microsoftonline.com', 'login.live.com', 'github.com'];
function isAuthPopup(url) {
  let u; try { u = new URL(url); } catch (e) { return false; }
  if (u.protocol !== 'https:') return false;
  if (u.hostname === 'github.com') return u.pathname.startsWith('/login');
  return AUTH_HOSTS.includes(u.hostname);
}

// One Browser per agent (one per thread). Its view is attached to the main window (main.js stacks it under the UI, or above it
// while the browser panel shows it). All share the persist:desk partition (shared sign-ins).
class Browser {
  constructor({ view, session, onState }) {
    this.onState = onState || (() => {});
    this.reqs = new Set();
    this.lastActivity = Date.now();
    this.readCache = { url: '', pages: [] };
    this.lastSnap = null; // structured copy of the latest snapshot: the baseline for the next "After" note
    this.view = view;
    this.wc = view.webContents;
    this.favicon = '';
    wireSession(session.fromPartition('persist:desk'));
    this.id = this.wc.id; // kept: a destroyed webContents can no longer be asked
    registry.set(this.id, this);
    const wc = this.wc;
    // Sign-in popups (Google / Apple "Continue with ...") must keep their opener: the page signs in by messaging the opener and
    // then closes itself. Loaded in place (below) it had no opener, and its window.close() destroyed this browser (Ben Oct 28:
    // "the browser isn't opening now"). Ben Oct 29: as its own window it "should be a side browser", so when main.js takes it
    // (onPopup) the popup's page is shown in a view over this one, in the browser panel. Any other popup still opens in place.
    wc.setWindowOpenHandler(({ url }) => {
      if (isAuthPopup(url) && this.onPopup) {
        return { action: 'allow', createWindow: (options) => { const pv = new view.constructor({ webContents: options.webContents }); this.onPopup(pv); return pv.webContents; } };
      }
      if (isAuthPopup(url)) return { action: 'allow', overrideBrowserWindowOptions: { width: 520, height: 680, title: 'Sign in', autoHideMenuBar: true, backgroundColor: '#ffffff' } };
      // web pages only: a page's window.open('file:///…') must not turn a local file into the page the model reads
      if (/^https?:/i.test(url)) setImmediate(() => { if (!wc.isDestroyed()) wc.loadURL(url).catch(() => {}); });
      return { action: 'deny' };
    });
    const push = () => { if (!wc.isDestroyed()) this.onState(this.state()); };
    for (const ev of ['did-navigate', 'did-navigate-in-page', 'did-start-loading', 'did-stop-loading', 'page-title-updated']) wc.on(ev, push);
    wc.on('did-start-navigation', (e, url, inPlace, main) => { if (main && !inPlace) this.favicon = ''; });
    wc.on('page-favicon-updated', (e, icons) => { this.favicon = (icons && icons[0]) || ''; push(); });
  }

  // Give the page keyboard focus for the agent's typing, unless that would pull it away from Ben (the composer) while the panel is closed.
  focusPage() { if (this.shouldFocus ? this.shouldFocus() : true) this.wc.focus(); }

  state() {
    const wc = this.wc;
    if (wc.isDestroyed()) return { url: '', title: '', favicon: '', loading: false, canGoBack: false, canGoForward: false, gone: true };
    const h = wc.navigationHistory;
    return { url: wc.getURL(), title: wc.getTitle(), favicon: this.favicon, loading: wc.isLoading(), canGoBack: h ? h.canGoBack() : wc.canGoBack(), canGoForward: h ? h.canGoForward() : wc.canGoForward() };
  }

  destroy() {
    registry.delete(this.id);
    try { if (!this.wc.isDestroyed()) this.wc.close(); } catch (e) { /* ignore */ }
  }

  // Small JPEG data URL of the page for the live card (cheap: ~360 px wide). null if the page cannot be captured.
  async thumb(width) {
    try {
      const img = await Promise.race([this.wc.capturePage(), sleep(2000).then(() => null)]);
      if (!img || img.isEmpty()) return null;
      const s = img.getSize();
      const small = s.width > (width || 360) ? img.resize({ width: width || 360 }) : img;
      return 'data:image/jpeg;base64,' + small.toJPEG(55).toString('base64');
    } catch (e) { return null; }
  }

  // Does this look like a sign-in / 2-step / passkey page? (used when the model gets stuck on one)
  async looksLikeAuth() {
    try {
      const r = await this.wc.executeJavaScript('(function(){return (location.href+" "+document.title+" "+(document.body?document.body.innerText.slice(0,1500):"")).toLowerCase()})()');
      return /passkey|security key|2-?step|two-?step|verification code|verify (it'?s|that it)|sign.?in|log.?in|authenticat|captcha|confirm (it'?s )?you/.test(r);
    } catch (e) { return false; }
  }

  normalize(url) {
    const u = normalizeUrl(url);
    if (!u) throw new Error('empty URL');
    return u;
  }

  async waitSettled(maxMs) {
    const end = Date.now() + (maxMs || 8000);
    // loading flag first
    while (Date.now() < end && this.wc.isLoading()) await sleep(100);
    // then network quiet for ~500 ms
    await sleep(150);
    while (Date.now() < end) {
      if (this.reqs.size === 0 && Date.now() - this.lastActivity > 500 && !this.wc.isLoading()) break;
      await sleep(100);
    }
  }

  async go(url) {
    const u = this.normalize(url);
    let before = ''; try { before = this.wc.getURL(); } catch (e) { /* destroyed */ }
    this.readCache = { url: '', pages: [] };
    try { await Promise.race([this.wc.loadURL(u), sleep(30000).then(() => { throw new Error('load timed out after 30 s'); })]); } catch (e) {
      const why = String(e.message).split('\n')[0];
      // a site that cannot be reached leaves Chrome's error page under its own URL: that is a failure, not a page with no text (Oct 30-31:
      // the Motes read those error pages and kept trying the same dead addresses)
      if (!/ERR_ABORTED/.test(why) && (!this.wc.getURL() || this.wc.getURL() === 'about:blank' || (NET_FAIL.test(why) && !/load timed out/.test(why)))) return { text: 'Error: could not open ' + u + ' (' + why + ')', error: true };
      // no answer within 30 s (a dead server can take minutes to time out): a failure unless the page itself is there with some text
      if (/load timed out/.test(why)) {
        try { this.wc.stop(); } catch (err) { /* destroyed */ }
        const never = this.wc.getURL() === before && before !== u;   // still the page from before: the new one never arrived
        const text = never ? false : await this.wc.executeJavaScript('!!(document.body && document.body.innerText.trim())').catch(() => false);
        if (!text) return { text: 'Error: could not open ' + u + ' (' + why + ')', error: true };
      }
    }
    await this.waitSettled();
    return this.snapshot('navigate');
  }

  // kind (click|type|navigate|back): append the compact "After" evidence note (what changed since the previous snapshot).
  async snapshot(kind) {
    let s;
    try { s = await this.wc.executeJavaScript(call(pageSnapshot, 120)); } catch (e) { return { text: 'Error: page not readable (' + e.message + ')', error: true }; }
    const prev = this.lastSnap;
    this.lastSnap = s;
    const head = 'URL: ' + s.url + ' | Title: ' + s.title;
    const tail = '\nText: ' + s.text;
    let body = '';
    let shown = 0;
    for (const l of s.lines) {
      if ((head.length + body.length + l.length + tail.length + 40) > SNAPSHOT_MAX) break;
      body += '\n' + l; shown++;
    }
    let out = head + body + tail;
    if (shown < s.lines.length) out += '\n[' + (s.lines.length - shown) + ' more elements not shown; scroll or read the page]';
    if (kind) out += '\n' + browserAfter(prev, s, kind);
    return out;
  }

  async result(summary, kind) {
    const text = await this.snapshot(kind);
    const r = typeof text === 'string' ? { text } : text;
    if (summary) r.summary = summary;
    return r;
  }

  // no page open yet: a click/type/read on an empty browser used to wait forever for a page that never loads
  noPage() {
    let u = ''; try { u = this.wc.getURL(); } catch (e) { /* destroyed */ }
    if (u && u !== 'about:blank') return null;
    return { text: 'Error: no page is open. Use browser_go with a URL or a search first.', error: true };
  }

  async click(id) {
    const np = this.noPage(); if (np) return np;
    const p = await this.wc.executeJavaScript(call(pagePrepare, id));
    if (!p.ok) return { text: 'Error: ' + p.error, error: true };
    await sleep(250); // let the badge show
    const q = await this.wc.executeJavaScript(call(pagePoint, id)).catch(() => null);
    if (q && q.ok) { p.x = q.x; p.y = q.y; p.hit = q.hit; } // where it is now, not where it was 250 ms ago
    if (p.hit) {
      this.focusPage();
      this.wc.sendInputEvent({ type: 'mouseMove', x: p.x, y: p.y });
      this.wc.sendInputEvent({ type: 'mouseDown', x: p.x, y: p.y, button: 'left', clickCount: 1 });
      this.wc.sendInputEvent({ type: 'mouseUp', x: p.x, y: p.y, button: 'left', clickCount: 1 });
    } else {
      await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'[data-desk-id="' + Number(id) + '"]\');if(e)e.click();})()');
    }
    this.readCache = { url: '', pages: [] };
    await sleep(200);
    await this.waitSettled();
    return this.result('Clicked [' + id + '] ' + (p.label ? '“' + p.label + '”' : ''), 'click');
  }

  async sensitiveReason(id) {
    try {
      const r = await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'[data-desk-id="' + Number(id) + '"]\');return e?e.getAttribute("data-desk-sensitive")||"":""})()');
      return r ? (r === 'password' ? 'password field' : 'payment field') : null;
    } catch (e) { return null; }
  }

  async type(id, text, enter) {
    const np = this.noPage(); if (np) return np;
    const p = await this.wc.executeJavaScript(call(pagePrepare, id));
    if (!p.ok) return { text: 'Error: ' + p.error, error: true };
    const f = await this.wc.executeJavaScript(call(pageFocusSelect, id));
    if (!f.ok || !f.editable) return { text: 'Error: element [' + id + '] is not a text field', error: true };
    this.focusPage();
    text = String(text == null ? '' : text);
    if (text) this.wc.insertText(text);
    await sleep(80);
    await this.wc.executeJavaScript(call(pageEnsureValue, id, text));
    if (enter) {
      const k = { keyCode: 'Enter' };
      this.wc.sendInputEvent({ type: 'keyDown', ...k });
      this.wc.sendInputEvent({ type: 'char', keyCode: '\r' });
      this.wc.sendInputEvent({ type: 'keyUp', ...k });
    }
    this.readCache = { url: '', pages: [] };
    await sleep(200);
    await this.waitSettled();
    return this.result('Typed into [' + id + ']' + (p.label ? ' “' + p.label + '”' : '') + (enter ? ' + Enter' : ''), 'type');
  }

  // track LOGIN1: sign in with Ben's saved login. lookup(pageUrl) -> {user, password} for EXACTLY that https origin, or null.
  // The app fills the fields and submits; the result names only the user and host (never the password).
  // -> {text, summary, kind: 'signed'|'none'|'code'|'failed'|'noform'|'http', host}
  async signIn(lookup) {
    const np = this.noPage(); if (np) return np;
    const L = require('../logins');
    this.filling = Date.now() + 60000;   // the preload sees this fill as a form submit: main ignores it while this is set
    try {
      let used = null;
      for (let step = 0; step < 3; step++) {
        const url = this.wc.getURL();
        const origin = L.originOf(url);
        const host = (() => { try { return new URL(url).host; } catch (e) { return url; } })();
        if (!origin) return { text: L.say.notHttps(), kind: 'http', host, error: true, summary: 'Did not sign in (not https)' };
        let f; try { f = await this.wc.executeJavaScript(call(L.pageLoginForm)); } catch (e) { return { text: 'Error: page not readable (' + e.message + ')', error: true }; }
        if (!f.pw && !f.user) {
          if (f.code) return { text: L.say.code(host), kind: 'code', host, summary: 'A code is needed on ' + host };
          if (used) break;   // the form went away after submitting: done
          return { text: L.say.noForm(host), kind: 'noform', host, error: true, summary: 'No sign-in form on ' + host };
        }
        const login = await lookup(url);
        if (!login || L.originOf(url) !== L.originOf(this.wc.getURL())) return { text: L.say.noLogin(host), kind: 'none', host, summary: 'No saved login for ' + host };
        used = { user: login.user, host, url };
        if (f.user && f.userValue !== login.user) await this._fillLogin('user', login.user);
        if (f.pw) {
          if (L.originOf(this.wc.getURL()) !== login.origin) return { text: L.say.noLogin(host), kind: 'none', host, summary: 'No saved login for ' + host };   // moved mid-way
          await this._fillLogin('pw', login.password);
          const before = this.wc.getURL();
          await this._submitLogin(f.submit, 'pw');
          await sleep(300); await this.waitSettled();
          // nothing happened (a click that did not land): press the button from the page once
          let p0 = null; try { p0 = await this.wc.executeJavaScript(call(L.pageLoginProbe)); } catch (e) { p0 = null; }
          if (p0 && p0.pw && !p0.failed && this.wc.getURL() === before && f.submit) { await this._submitLogin(f.submit, 'pw', true); await sleep(300); await this.waitSettled(); }
          break;
        }
        // a username-only step: Next, then wait for the password field (or a new page)
        let moved = false;
        for (let attempt = 0; attempt < 2 && !moved; attempt++) {   // the second attempt presses the button from the page (a click that did not land)
          await this._submitLogin(f.submit, 'user', attempt > 0);
          await sleep(300); await this.waitSettled();
          for (let i = 0; i < 8; i++) {
            let g = null; try { g = await this.wc.executeJavaScript(call(L.pageLoginForm)); } catch (e) { g = null; }
            if (!g || g.pw || g.code || !g.user || L.originOf(this.wc.getURL()) !== origin) { moved = true; break; }
            await sleep(400);
          }
        }
        if (!moved) return { text: L.say.failed(login.user, host, 'the Next step did not open') , kind: 'failed', host, error: true, summary: 'Sign-in stuck on ' + host };
      }
      if (!used) return { text: L.say.noForm(this.state().url), kind: 'noform', error: true };
      await sleep(500);
      let g = null; try { g = await this.wc.executeJavaScript(call(L.pageLoginForm)); } catch (e) { g = null; }
      let p = null; try { p = await this.wc.executeJavaScript(call(L.pageLoginProbe)); } catch (e) { p = null; }
      this.readCache = { url: '', pages: [] };
      const snap = await this.snapshot('click');
      const tail = '\n' + (typeof snap === 'string' ? snap : (snap && snap.text) || '');
      if (g && g.code) return { text: L.say.code(used.host) + tail, kind: 'code', host: used.host, summary: 'A code is needed on ' + used.host };
      if ((p && (p.failed || p.pw)) || (g && g.pw && g.alerts && g.alerts.length) || (g && g.user && !g.pw && g.userValue === used.user && L.originOf(this.wc.getURL()) === L.originOf(used.url))) return {   // still the form: not signed in
        text: L.say.failed(used.user, used.host, g && g.alerts && g.alerts[0]) + tail, kind: 'failed', host: used.host, error: true, summary: 'Sign-in did not go through on ' + used.host };
      return { text: L.say.signedIn(used.user, used.host) + tail, kind: 'signed', host: used.host, summary: 'Signed in on ' + used.host };
    } finally { this.filling = Date.now() + 4000; }
  }

  async _fillLogin(which, value) {
    const sel = '[data-desk-login="' + which + '"]';
    const ok = await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'' + sel + '\');if(!e)return false;e.scrollIntoView({block:"center"});e.focus();try{e.select()}catch(x){}return true})()').catch(() => false);
    if (!ok) return false;
    this.focusPage();
    this.wc.insertText(String(value));
    await sleep(80);
    // a page that missed the typed text (it was not focused) gets the value set directly, as browser_type does
    const len = await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'' + sel + '\');return e?e.value.length:-1})()').catch(() => -1);
    if (len !== String(value).length) {
      await this.wc.executeJavaScript('(function(v){var e=document.querySelector(\'' + sel + '\');if(!e)return;var p=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value");p.set.call(e,v);e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))})(' + JSON.stringify(String(value)) + ')').catch(() => {});
    }
    return true;
  }

  async _submitLogin(hasButton, field, fromPage) {
    if (hasButton && fromPage) { await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'[data-desk-login="submit"]\');if(e)e.click()})()').catch(() => {}); return; }
    if (hasButton) {
      const p = await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'[data-desk-login="submit"]\');if(!e)return null;var r=e.getBoundingClientRect();var x=Math.round(r.left+r.width/2),y=Math.round(r.top+r.height/2);var h=document.elementFromPoint(x,y);return{x:x,y:y,hit:!!h&&(h===e||e.contains(h)||h.contains(e))}})()').catch(() => null);
      if (p && p.hit) {
        this.focusPage();
        this.wc.sendInputEvent({ type: 'mouseMove', x: p.x, y: p.y });
        this.wc.sendInputEvent({ type: 'mouseDown', x: p.x, y: p.y, button: 'left', clickCount: 1 });
        this.wc.sendInputEvent({ type: 'mouseUp', x: p.x, y: p.y, button: 'left', clickCount: 1 });
        return;
      }
      if (p) { await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'[data-desk-login="submit"]\');if(e)e.click()})()').catch(() => {}); return; }
    }
    // no button: Enter in the field (implicit form submission)
    await this.wc.executeJavaScript('(function(){var e=document.querySelector(\'[data-desk-login="' + field + '"]\');if(e)e.focus()})()').catch(() => {});
    this.focusPage();
    this.wc.sendInputEvent({ type: 'keyDown', keyCode: 'Enter' });
    this.wc.sendInputEvent({ type: 'char', keyCode: '\r' });
    this.wc.sendInputEvent({ type: 'keyUp', keyCode: 'Enter' });
  }

  async scroll(direction) {
    const np = this.noPage(); if (np) return np;
    const dy = direction === 'up' ? -0.85 : 0.85;
    await this.wc.executeJavaScript('window.scrollBy(0, Math.round(window.innerHeight*' + dy + '))');
    await sleep(350);
    return this.result();
  }

  async back() {
    const h = this.wc.navigationHistory;
    const can = h ? h.canGoBack() : this.wc.canGoBack();
    if (!can) return { text: 'Error: no earlier page in history', error: true };
    if (h) h.goBack(); else this.wc.goBack();
    await sleep(200);
    await this.waitSettled();
    return this.result('Went back', 'back');
  }

  async read(page) {
    const np = this.noPage(); if (np) return np;
    const url = this.wc.getURL();
    if (this.readCache.url !== url || !this.readCache.pages.length) {
      let t = '';
      try { t = await this.wc.executeJavaScript(call(pageReadText)); } catch (e) { return { text: 'Error: page not readable (' + e.message + ')', error: true }; }
      if (this.wc.isDestroyed() || this.wc.getURL() !== url) return { text: 'Error: page changed during reading; read the current page again.', error: true };
      const pages = [];
      for (let i = 0; i < t.length; i += PAGE_CHARS) pages.push(t.slice(i, i + PAGE_CHARS));
      this.readCache = { url, pages: pages.length ? pages : ['(no readable text)'], readAt: Date.now(), readable: !!t.trim() };
    }
    const n = this.readCache.pages.length;
    const k = Math.min(Math.max(1, Math.floor(Number(page)) || 1), n);
    const header = 'Page ' + k + ' of ' + n + ' (' + url + ')\n';
    const body = this.readCache.pages[k - 1];
    const result = { text: header + body + (k < n ? '\n[more: browser_read page=' + (k + 1) + ']' : '') };
    if (this.readCache.readable) attachSourceRead(result, { url, body, bodyStart: header.length, page: k, readAt: this.readCache.readAt });
    return result;
  }

  async screenshot(max) {
    try {
      let img = await this.wc.capturePage();
      const s = img.getSize();
      if (s.width > (max || 1280)) img = img.resize({ width: max || 1280 });
      return 'data:image/jpeg;base64,' + img.toJPEG(70).toString('base64');
    } catch (e) { return null; }
  }
}

module.exports = { Browser, isAuthPopup, SNAPSHOT_MAX, PAGE_CHARS, pageSnapshot, pageReadText };
