'use strict';
// Built-in browser: a WebContentsView in the persistent partition "persist:desk", driven from the main process.

const { browserAfter } = require('./after');

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
  ses.webRequest.onBeforeRequest((d, cb) => { hit(d, (b) => { b.inflight++; b.lastActivity = Date.now(); }); cb({}); });
  const done = (d) => hit(d, (b) => { b.inflight = Math.max(0, b.inflight - 1); b.lastActivity = Date.now(); });
  ses.webRequest.onCompleted(done);
  ses.webRequest.onErrorOccurred(done);
}

// One Browser per agent (one per thread). Its view is attached to the main window (main.js stacks it under the UI, or above it
// while the browser panel shows it). All share the persist:desk partition (shared sign-ins).
class Browser {
  constructor({ view, session, onState }) {
    this.onState = onState || (() => {});
    this.inflight = 0;
    this.lastActivity = Date.now();
    this.readCache = { url: '', pages: [] };
    this.lastSnap = null; // structured copy of the latest snapshot: the baseline for the next "After" note
    this.view = view;
    this.wc = view.webContents;
    this.favicon = '';
    wireSession(session.fromPartition('persist:desk'));
    registry.set(this.wc.id, this);
    const wc = this.wc;
    wc.setWindowOpenHandler(({ url }) => { setImmediate(() => { if (!wc.isDestroyed()) wc.loadURL(url).catch(() => {}); }); return { action: 'deny' }; });
    const push = () => { if (!wc.isDestroyed()) this.onState(this.state()); };
    for (const ev of ['did-navigate', 'did-navigate-in-page', 'did-start-loading', 'did-stop-loading', 'page-title-updated']) wc.on(ev, push);
    wc.on('did-start-navigation', (e, url, inPlace, main) => { if (main && !inPlace) this.favicon = ''; });
    wc.on('page-favicon-updated', (e, icons) => { this.favicon = (icons && icons[0]) || ''; push(); });
  }

  // Give the page keyboard focus for the agent's typing, unless that would pull it away from Ben (the composer) while the panel is closed.
  focusPage() { if (this.shouldFocus ? this.shouldFocus() : true) this.wc.focus(); }

  state() {
    const wc = this.wc;
    const h = wc.navigationHistory;
    return { url: wc.getURL(), title: wc.getTitle(), favicon: this.favicon, loading: wc.isLoading(), canGoBack: h ? h.canGoBack() : wc.canGoBack(), canGoForward: h ? h.canGoForward() : wc.canGoForward() };
  }

  destroy() {
    registry.delete(this.wc.id);
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
    url = String(url || '').trim();
    if (!url) throw new Error('empty URL');
    if (/^(https?|file|about):/i.test(url)) return url;
    if (/^(localhost|127\.|\d+\.\d+\.\d+\.\d+)/.test(url)) return 'http://' + url;
    if (/^[\w-]+(\.[\w-]+)+(\/|$|:)/.test(url) && !/\s/.test(url)) return 'https://' + url;
    return 'https://duckduckgo.com/?q=' + encodeURIComponent(url);
  }

  async waitSettled(maxMs) {
    const end = Date.now() + (maxMs || 8000);
    // loading flag first
    while (Date.now() < end && this.wc.isLoading()) await sleep(100);
    // then network quiet for ~500 ms
    await sleep(150);
    while (Date.now() < end) {
      if (this.inflight <= 0 && Date.now() - this.lastActivity > 500 && !this.wc.isLoading()) break;
      await sleep(100);
    }
  }

  async go(url) {
    const u = this.normalize(url);
    this.readCache = { url: '', pages: [] };
    try { await Promise.race([this.wc.loadURL(u), sleep(30000).then(() => { throw new Error('load timed out after 30 s'); })]); } catch (e) {
      if (!/ERR_ABORTED/.test(String(e.message))) {
        if (!this.wc.getURL() || this.wc.getURL() === 'about:blank') return { text: 'Error: could not open ' + u + ' (' + String(e.message).split('\n')[0] + ')', error: true };
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
      const pages = [];
      for (let i = 0; i < t.length; i += PAGE_CHARS) pages.push(t.slice(i, i + PAGE_CHARS));
      this.readCache = { url, pages: pages.length ? pages : ['(no readable text)'] };
    }
    const n = this.readCache.pages.length;
    const k = Math.min(Math.max(1, Number(page) || 1), n);
    return 'Page ' + k + ' of ' + n + ' (' + url + ')\n' + this.readCache.pages[k - 1] + (k < n ? '\n[more: browser_read page=' + (k + 1) + ']' : '');
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

module.exports = { Browser, SNAPSHOT_MAX, PAGE_CHARS, pageSnapshot, pageReadText };
