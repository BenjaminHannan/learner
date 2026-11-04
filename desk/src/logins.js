'use strict';
// Saved logins (track LOGIN1, Ben 2026-11-04: "why won't it type itself" -> "make it so that it's allowed to").
// Glim signs in with logins Ben saved, and the password never passes through the model:
//  - the store: macOS Keychain internet-password items labelled "Premonition" (one per exact https origin), through /usr/bin/security
//    with argv arrays and the password on stdin (`security -i`), never a shell string and never in argv; elsewhere Electron safeStorage.
//    An index file (userData/logins.json) keeps only origins + usernames, for the Settings list. No password is ever written there.
//  - saving: the app (src/tools/browser.js preload, not the model) sees Ben submit a login form, then offers one card: Save / Not now /
//    Never for this site. Or Ben says "save my Schoology login" and a masked app dialog opens (the text never goes in chat).
//  - signing in: the browser_sign_in tool. The APP fills the saved login on the page and submits; the model only reads
//    "Signed in as <user> on <host>" / "No saved login for <host> ..." / "A code is needed ...".
//  - filling happens only when the page's origin is https and EXACTLY the saved origin (a look-alike host gets nothing).
//  - redaction: scrub() drops any line that holds a saved password (tool results, log lines, the day logs, the sleep diary).
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// ---- origins -----------------------------------------------------------------------------------------------------------------------
// 'https://host[:port]' (lower case) or null. Only https: a plain-http page never gets a saved login.
function originOf(url) {
  let u; try { u = new URL(String(url || '')); } catch (e) { return null; }
  if (u.protocol !== 'https:' || !u.hostname) return null;
  return 'https://' + u.hostname.toLowerCase() + (u.port ? ':' + u.port : '');
}
const hostOfOrigin = (o) => { try { return new URL(o).host; } catch (e) { return ''; } };
// the page may get the saved login only if its origin is exactly the saved one (no subdomain, look-alike or http match)
function sameOrigin(saved, pageUrl) { const a = originOf(saved), b = originOf(pageUrl); return !!a && a === b; }
// what Ben typed in the dialog ("dresden.schoology.com", "https://x.com/login") -> an origin, or null
function originFromInput(s) {
  s = String(s || '').trim();
  if (!s) return null;
  if (/^http:\/\//i.test(s)) return null;
  return originOf(/^[a-z][a-z0-9+.-]*:\/\//i.test(s) ? s : 'https://' + s);
}

// ---- redaction: any text that holds a saved password loses those lines ----------------------------------------------------------------
const SECRETS = new Set();   // in this process's memory only (filled from the store); never written anywhere
const HIDDEN = '[hidden: this line held a saved password]';
const MIN_SECRET = 4;        // a 1-3 character "password" would hide ordinary words
function addSecret(p) { p = String(p || ''); if (p.length >= MIN_SECRET) SECRETS.add(p); }
function dropSecret(p) { SECRETS.delete(String(p || '')); }
function holdsSecret(text) { const s = String(text == null ? '' : text); for (const p of SECRETS) if (s.includes(p)) return true; return false; }
function scrub(text) {
  if (typeof text !== 'string' || !SECRETS.size || !holdsSecret(text)) return text;
  return text.split('\n').map((l) => (holdsSecret(l) ? HIDDEN : l)).join('\n');
}
// a whole record (a JSON line, a log line): null = drop it
const scrubRecord = (line) => (holdsSecret(line) ? null : line);

// ---- backends ---------------------------------------------------------------------------------------------------------------------
const LABEL = 'Premonition';
const COMMENT = 'premonition-login';
const enc = (pw) => 'pm1:' + Buffer.from(String(pw), 'utf8').toString('base64');   // ASCII only: no quoting or hex surprises in `security`
const dec = (s) => { s = String(s || '').replace(/\r?\n$/, ''); return s.startsWith('pm1:') ? Buffer.from(s.slice(4), 'base64').toString('utf8') : s; };
const clean = (s, n) => String(s == null ? '' : s).replace(/[\u0000-\u001f\u007f]/g, '').slice(0, n);
// a `security -i` argument: double quotes, with \ and " escaped (checked against the real tool)
const q = (s) => '"' + String(s).replace(/[\\"]/g, (m) => '\\' + m) + '"';

// run(argv, stdin) -> {code, out}. Nothing from these calls is ever logged (stdout holds the password on a read).
function runSecurity(bin, args, input) {
  return new Promise((resolve) => {
    let out = '', done = false;
    const fin = (code) => { if (!done) { done = true; resolve({ code, out }); } };
    let p; try { p = spawn(bin, args, { stdio: ['pipe', 'pipe', 'ignore'] }); } catch (e) { return fin(-1); }
    p.stdout.on('data', (d) => { out += d; if (out.length > 65536) out = out.slice(0, 65536); });
    p.on('error', () => fin(-1));
    p.on('close', (c) => fin(c));
    const t = setTimeout(() => { try { p.kill(); } catch (e) { /* gone */ } fin(-2); }, 15000);
    if (t.unref) t.unref();
    try { if (input != null) p.stdin.write(input); p.stdin.end(); } catch (e) { /* closed */ }
  });
}

// macOS Keychain: internet-password items, label "Premonition", protocol htps, server = host, port when not 443.
// o.keychain: a keychain file path (tests use a throwaway one; the app leaves it unset = Ben's default keychain).
class MacKeychain {
  constructor(o) { o = o || {}; this.bin = o.bin || '/usr/bin/security'; this.keychain = o.keychain || ''; this.run = o.run || runSecurity; }
  _where(origin) { const u = new URL(origin); return { host: u.hostname, port: u.port || '' }; }
  _find(origin, user) {
    const w = this._where(origin);
    const a = ['find-internet-password', '-l', LABEL, '-s', w.host, '-a', user, '-r', 'htps'];
    if (w.port) a.push('-P', w.port);
    a.push('-w'); if (this.keychain) a.push(this.keychain);
    return a;
  }
  async set(origin, user, password) {
    if (this.keychain && !fs.existsSync(this.keychain)) return false;   // `security` would silently fall back to the default (login) keychain
    const w = this._where(origin);
    const line = 'add-internet-password -a ' + q(user) + ' -s ' + q(w.host) + (w.port ? ' -P ' + w.port : '') + ' -r htps -l ' + q(LABEL) + ' -j ' + q(COMMENT) + ' -U -w ' + q(enc(password)) + (this.keychain ? ' ' + q(this.keychain) : '') + '\n';
    await this.run(this.bin, ['-i'], line);   // the password goes on stdin, never in argv (another process could read argv)
    const back = await this.get(origin, user);
    return back === String(password);
  }
  async get(origin, user) { const r = await this.run(this.bin, this._find(origin, user)); return r.code === 0 ? dec(r.out) : null; }
  async del(origin, user) {
    const w = this._where(origin);
    const a = ['delete-internet-password', '-l', LABEL, '-s', w.host, '-a', user, '-r', 'htps'];
    if (w.port) a.push('-P', w.port);
    if (this.keychain) a.push(this.keychain);
    const r = await this.run(this.bin, a); return r.code === 0;
  }
}

// Windows / Linux: Electron safeStorage (DPAPI on Windows), one encrypted blob per origin in userData/logins.secret.json
class SafeStorageBox {
  constructor(o) { this.file = path.join(o.dir, 'logins.secret.json'); this.ss = o.safeStorage; }
  _read() { try { return JSON.parse(fs.readFileSync(this.file, 'utf8')) || {}; } catch (e) { return {}; } }
  _write(j) { const t = this.file + '.tmp'; fs.mkdirSync(path.dirname(this.file), { recursive: true }); fs.writeFileSync(t, JSON.stringify(j)); fs.renameSync(t, this.file); }
  async set(origin, user, password) {
    if (!this.ss || !this.ss.isEncryptionAvailable()) return false;
    const j = this._read(); j[origin + ' ' + user] = this.ss.encryptString(String(password)).toString('base64'); this._write(j); return true;
  }
  async get(origin, user) { const v = this._read()[origin + ' ' + user]; if (!v || !this.ss) return null; try { return this.ss.decryptString(Buffer.from(v, 'base64')); } catch (e) { return null; } }
  async del(origin, user) { const j = this._read(); delete j[origin + ' ' + user]; this._write(j); return true; }
}

// unit tests
class MemoryBox {
  constructor() { this.m = new Map(); }
  async set(o, u, p) { this.m.set(o + ' ' + u, String(p)); return true; }
  async get(o, u) { return this.m.has(o + ' ' + u) ? this.m.get(o + ' ' + u) : null; }
  async del(o, u) { return this.m.delete(o + ' ' + u); }
}

// ---- the store --------------------------------------------------------------------------------------------------------------------
// o: {dir (userData; omit = in memory), box (backend), now}
class LoginStore {
  constructor(o) {
    o = o || {}; this.o = o; this.now = o.now || Date.now; this.box = o.box || new MemoryBox();
    this.file = o.dir ? path.join(o.dir, 'logins.json') : null;
    this.st = { items: [], never: [] };
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && Array.isArray(j.items)) this.st = { items: j.items.filter((x) => x && originOf(x.origin) === x.origin), never: Array.isArray(j.never) ? j.never : [] }; } catch (e) { /* none yet */ } }
  }
  _save() { if (!this.file) return; try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); const t = this.file + '.tmp'; fs.writeFileSync(t, JSON.stringify(this.st, null, 1)); fs.renameSync(t, this.file); } catch (e) { /* in memory */ } }
  // origins + usernames only (Settings > Safety > Saved logins)
  list() { return this.st.items.map((x) => ({ origin: x.origin, host: hostOfOrigin(x.origin), user: x.user, savedAt: x.savedAt })); }
  item(origin) { const o = originOf(origin); return o ? this.st.items.find((x) => x.origin === o) || null : null; }
  isNever(origin) { const o = originOf(origin); return !!o && this.st.never.includes(o); }
  setNever(origin) { const o = originOf(origin); if (o && !this.st.never.includes(o)) { this.st.never.push(o); this._save(); } return !!o; }
  // the saved login for exactly this page's origin: {user, password} or null. Only the app ever calls this, never a tool result.
  async forPage(pageUrl) {
    const o = originOf(pageUrl); if (!o) return null;
    const it = this.st.items.find((x) => x.origin === o); if (!it) return null;
    const pw = await this.box.get(o, it.user);
    if (pw == null) return null;
    addSecret(pw);
    return { origin: o, user: it.user, password: pw };
  }
  async save(origin, user, password) {
    const o = originOf(origin);
    if (!o) return { ok: false, error: 'Only https sites can have a saved login.' };
    user = clean(user, 256).trim(); password = String(password == null ? '' : password).slice(0, 1024);
    if (!user || !password) return { ok: false, error: 'Both the username and the password are needed.' };
    const old = this.st.items.find((x) => x.origin === o);
    let ok = false; try { ok = await this.box.set(o, user, password); } catch (e) { ok = false; }
    if (!ok) return { ok: false, error: 'Could not save it in the keychain.' };
    if (old && old.user !== user) { try { const op = await this.box.get(o, old.user); if (op) dropSecret(op); await this.box.del(o, old.user); } catch (e) { /* the old item stays */ } }
    this.st.items = this.st.items.filter((x) => x.origin !== o);
    this.st.items.push({ origin: o, user, savedAt: new Date(this.now()).toISOString() });
    this.st.never = this.st.never.filter((x) => x !== o);
    this._save(); addSecret(password);
    return { ok: true, host: hostOfOrigin(o), user };
  }
  async remove(origin) {
    const o = originOf(origin); const it = o && this.st.items.find((x) => x.origin === o);
    if (!it) return { ok: false };
    try { const pw = await this.box.get(o, it.user); if (pw) dropSecret(pw); await this.box.del(o, it.user); } catch (e) { /* the index goes anyway */ }
    this.st.items = this.st.items.filter((x) => x.origin !== o); this._save();
    return { ok: true, host: hostOfOrigin(o) };
  }
  // load every saved password into memory once, so scrub() can catch it anywhere (startup, in the background)
  async warm() { for (const it of this.st.items) { try { const pw = await this.box.get(it.origin, it.user); if (pw) addSecret(pw); } catch (e) { /* skip */ } } return SECRETS.size; }
  async same(origin, user, password) { const it = this.item(origin); if (!it || it.user !== user) return false; try { return (await this.box.get(it.origin, it.user)) === String(password); } catch (e) { return false; } }
}

// ---- what the model reads (never the password) ---------------------------------------------------------------------------------------
const say = {
  signedIn: (user, host) => 'Signed in as ' + user + ' on ' + host + '.',
  noLogin: (host) => 'No saved login for ' + host + ': ask Ben to sign in once in Glim\'s browser (the app then offers to save it).',
  code: (host) => 'A code is needed on ' + host + ': Ben enters verification codes himself.',
  notHttps: () => 'Not signed in: this page is not https, so the app will not fill a saved login here.',
  noForm: (host) => 'No sign-in form found on ' + host + '. Open the site\'s sign-in page first, then call browser_sign_in again.',
  failed: (user, host, why) => 'The sign-in as ' + user + ' on ' + host + ' did not go through' + (why ? ': the page says "' + why + '"' : '') + '. Ask Ben to sign in once in Glim\'s browser (the app offers to save the new login).'
};

// ---- capture: Ben submitted a login form in Glim's browser -> offer one Save card ---------------------------------------------------------
// o: {store, offer({token, host, user, update}), allowHost(host) -> bool, now, delayMs}
// submitted({key, url, user, password, step, filling, probe() -> Promise<{pw:bool, failed:bool}>})
class LoginCapture {
  constructor(o) { this.o = o; this.now = o.now || Date.now; this.pending = new Map(); this.lastUser = new Map(); this.offered = new Set(); this.seq = 0; }
  async submitted(d) {
    const o = this.o;
    if (!d || d.filling) return null;   // the app's own fill (browser_sign_in) is not Ben signing in
    const origin = originOf(d.url); if (!origin) return null;
    const host = hostOfOrigin(origin);
    if (o.allowHost && !o.allowHost(host)) return null;
    const user = clean(d.user, 256).trim();
    const pw = String(d.password == null ? '' : d.password).slice(0, 1024);
    if (!pw) { if (user) this.lastUser.set(d.key, { origin, user, t: this.now() }); return null; }   // step 1 of a two-step page
    const lu = this.lastUser.get(d.key);
    const who = user || (lu && lu.origin === origin && this.now() - lu.t < 10 * 60000 ? lu.user : '');
    if (!who || o.store.isNever(origin)) return null;
    const sig = origin + '\n' + who + '\n' + pw;
    if (this.offered.has(sig) || await o.store.same(origin, who, pw)) return null;
    this.offered.add(sig); if (this.offered.size > 50) this.offered.delete(this.offered.values().next().value);
    const token = 'L' + (++this.seq) + Math.random().toString(36).slice(2, 8);
    const it = o.store.item(origin);
    this.pending.set(token, { origin, host, user: who, password: pw, t: this.now(), update: !!it });
    addSecret(pw);   // already in memory: keep it out of every log from now on
    // wait a moment: a page that still shows a filled password field (or an error) did not sign in
    const wait = o.delayMs == null ? 2500 : o.delayMs; if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    let p = null; try { p = d.probe ? await d.probe() : null; } catch (e) { p = null; }
    if (p && (p.pw || p.failed)) { this.pending.delete(token); this.offered.delete(sig); return null; }
    this.expire();
    const ev = { token, host, user: who, update: !!it };
    try { o.offer(ev); } catch (e) { /* ui only */ }
    return ev;
  }
  expire() { for (const [k, v] of this.pending) if (this.now() - v.t > 10 * 60000) this.pending.delete(k); }
  // choice: 'save' | 'later' | 'never'
  async answer(token, choice) {
    const p = this.pending.get(token); this.pending.delete(token);
    if (!p) return { ok: false, error: 'That card has expired.' };
    if (choice === 'save') return this.o.store.save(p.origin, p.user, p.password);
    if (choice === 'never') { this.o.store.setNever(p.origin); return { ok: true, never: true, host: p.host }; }
    return { ok: true, later: true };
  }
}

// ---- "save my Schoology login" (Ben's own chat words) -> the masked dialog ---------------------------------------------------------------
const SAVE_ASK = /\b(?:save|remember|store|add|keep)\s+(?:my|the|a)\s+(?:([a-z0-9][\w.-]*)\s+)?(?:login|log-?in|sign-?in|password|username and password|credentials)\b/i;
function saveLoginAsk(text) {
  const s = String(text || '').trim();
  if (!s || s.length > 200 || /\b(don'?t|do not|never|stop)\b/i.test(s)) return null;
  const m = SAVE_ASK.exec(s); if (!m) return null;
  const w = (m[1] || '').toLowerCase();
  return { word: /^(own|new|old|other)$/.test(w) ? '' : w };
}
// the site to prefill: the open page if it matches the word (or no word), else a signed-in cookie host with the word in it
function guessOrigin(word, pageUrl, hosts) {
  const po = originOf(pageUrl);
  if (po && (!word || hostOfOrigin(po).includes(word))) return po;
  if (word) { const h = (hosts || []).filter((x) => x.includes(word)).sort((a, b) => a.length - b.length)[0]; if (h) return originOf('https://' + h); }
  return '';
}
const DIALOG_NOTE = (word) => '[Glim app: a private box is open for Ben to save his ' + (word ? word + ' ' : '') + 'login; he types it there, never in the chat, and the app keeps it in his keychain. Reply with one short line that says so; call no tools.] ';

// ---- page scripts (serialized into the page by src/tools/browser.js) --------------------------------------------------------------------
// Finds the login fields, marks them data-desk-login=user|pw|submit, and reports what is there (never a value except the username).
function pageLoginForm() {
  for (const e of document.querySelectorAll('[data-desk-login]')) e.removeAttribute('data-desk-login');
  const vis = (el) => { const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false; const cs = getComputedStyle(el); return cs.visibility !== 'hidden' && cs.display !== 'none' && Number(cs.opacity) !== 0 && !el.disabled && el.getAttribute('aria-hidden') !== 'true'; };
  const inputs = Array.from(document.querySelectorAll('input')).filter(vis);
  const ac = (i) => String(i.getAttribute('autocomplete') || '').toLowerCase();
  const words = (i) => ((i.name || '') + ' ' + (i.id || '') + ' ' + (i.placeholder || '') + ' ' + (i.getAttribute('aria-label') || '')).toLowerCase();
  const typ = (i) => String(i.getAttribute('type') || 'text').toLowerCase();
  const isCode = (i) => /one-time-code/.test(ac(i)) || /\b(otp|totp|2fa|mfa|verification|passcode|code|pin)\b/.test(words(i).replace(/[_-]/g, ' '));
  const pw = inputs.find((i) => typ(i) === 'password' && !/new-password/.test(ac(i)) && !isCode(i));
  const userLike = (i) => /^(text|email|tel)$/.test(typ(i)) && !isCode(i) && (/username|email/.test(ac(i)) || typ(i) === 'email' || /user|e-?mail|login|account|identifier|mail/.test(words(i)));
  let user = null;
  const before = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
  if (pw) { const c = inputs.filter((i) => userLike(i) && (!pw.form || i.form === pw.form) && before(i, pw)); user = c[c.length - 1] || null; }
  else user = inputs.find(userLike) || null;
  const code = !pw && inputs.some(isCode);
  const field = pw || user;
  let submit = null;
  if (field) {
    const scope = field.form || document;
    const btns = Array.from(scope.querySelectorAll('button,input[type=submit],input[type=button],[role=button]')).filter(vis);
    const text = (b) => String(b.innerText || b.value || b.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().toLowerCase();
    submit = btns.find((b) => /^(sign ?in|log ?in|login|next|continue|submit|sign on|log on|verify|go)\b/.test(text(b))) || btns.find((b) => (b.getAttribute('type') || '').toLowerCase() === 'submit') || null;
  }
  if (user) user.setAttribute('data-desk-login', 'user');
  if (pw) pw.setAttribute('data-desk-login', 'pw');
  if (submit) submit.setAttribute('data-desk-login', 'submit');
  const alerts = [];
  try { for (const a of document.querySelectorAll('[role=alert],[aria-live=assertive],.error,.alert-danger,.invalid-feedback,[class*=error-message],[class*=errorMessage]')) { const r = a.getBoundingClientRect(); const t = String(a.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120); if (r.width > 1 && r.height > 1 && t) alerts.push(t); if (alerts.length >= 2) break; } } catch (e) { /* none */ }
  const body = String(document.body ? document.body.innerText.slice(0, 2000) : '').toLowerCase();
  return { url: location.href, pw: !!pw, user: !!user, userValue: user ? user.value : '', pwFilled: !!(pw && pw.value), submit: !!submit, code: code || (!pw && !user && /verification code|enter the code|2-step|two-step|security code|authenticator/.test(body)), alerts };
}
// probe used after Ben submits (capture) and after the app's fill: still a filled password field? an error text?
function pageLoginProbe() {
  const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1 && getComputedStyle(el).visibility !== 'hidden'; };
  const pw = Array.from(document.querySelectorAll('input[type=password]')).some((i) => i.value && vis(i));
  let failed = false;
  try { for (const a of document.querySelectorAll('[role=alert],[aria-live=assertive],.error,.alert-danger,.invalid-feedback,[class*=error]')) { if (vis(a) && /incorrect|wrong|invalid|try again|doesn'?t match|not recogni[sz]ed|couldn'?t find/i.test(a.innerText || '')) { failed = true; break; } } } catch (e) { /* none */ }
  return { pw, failed };
}

module.exports = {
  originOf, sameOrigin, originFromInput, hostOfOrigin, scrub, scrubRecord, holdsSecret, addSecret, dropSecret, SECRETS, HIDDEN,
  MacKeychain, SafeStorageBox, MemoryBox, LoginStore, LoginCapture, say, saveLoginAsk, guessOrigin, DIALOG_NOTE,
  pageLoginForm, pageLoginProbe, runSecurity, LABEL
};
