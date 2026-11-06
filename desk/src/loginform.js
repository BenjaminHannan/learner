'use strict';
// SECURE-LOGIN (Ben 2026-11-05): "when Glim needs a username and password, it collects them through a secure form, never through chat.
// Glim may open that form whenever it wants (no 'may I?'). Once a login is saved, Glim may use it to sign in by itself."
//  - ask_login({site, reason}): the APP opens a small window of its own (renderer/loginform.html: username, masked password, Save,
//    Cancel). What Ben types goes from that window straight to src/logins.js (Keychain / safeStorage). It never enters the chat thread,
//    the model's messages, notes, the diary, sleep lessons or the gateway log. The model reads only {saved, site} (+ a fixed hint).
//  - one form per site: a second ask for a site whose form is open (or queued) joins it; nothing opens twice.
//  - Ben away (or a Mote asking): the form is queued, ONE notification is shown, and the run is told to end politely. The form opens
//    when Ben clicks the notification, or when he is back at the computer. No repeated asking: a site Ben cancelled is not asked
//    again for DECLINE_MS unless the main chat (Ben himself) asks.
const L = require('./logins');

const WAIT_MS = 5 * 60000;        // the main chat waits this long for Ben to fill the form, then goes on (the form stays open)
const DECLINE_MS = 6 * 3600000;   // after Cancel, Motes do not queue that site again for 6 h

// site (what the model wrote: "google.com", "https://accounts.google.com/x", "") + the open page -> the https origin to save for.
// The open page wins when it is the same site (or a subdomain of it): saved logins match EXACT origins (browser_sign_in).
function resolveOrigin(site, pageUrl) {
  const po = L.originOf(pageUrl);
  const s = String(site || '').trim();
  if (!s) return po;
  const so = /[.:/]/.test(s) ? L.originFromInput(s) : null;   // a bare word is not a host
  if (po && so) {
    const ph = L.hostOfOrigin(po).replace(/:\d+$/, ''), sh = L.hostOfOrigin(so).replace(/:\d+$/, '').replace(/^www\./, '');
    if (ph === sh || ph.endsWith('.' + sh)) return po;
  }
  if (so) return so;
  // a bare word ("schoology", "Google"): the page if its host holds it
  const w = s.toLowerCase().replace(/[^a-z0-9.-]/g, '');
  if (po && w && L.hostOfOrigin(po).includes(w)) return po;
  return null;
}

// what the model reads: never a username's password, never a value Ben typed
const HINT = {
  saved: 'Ben saved the login in the app\'s private form. Now call browser_sign_in on the sign-in page (the app fills it).',
  already: 'A login for this site is already saved. Call browser_sign_in on the sign-in page (the app fills it).',
  cancelled: 'Ben closed the private sign-in form without saving. Do not ask for the password in chat and do not open the form again now; say in one line what is not done.',
  declined: 'Ben closed the sign-in form for this site earlier. Do not ask again; say in one line that the task needs his sign-in.',
  queued: 'Ben is away, so the app queued a private sign-in form for him and sent one notification. End this run now: say in one line that it is waiting for his sign-in. Never ask for the password in chat.',
  waiting: 'The private sign-in form is still open for Ben. Do not ask for the password in chat; say in one line that it is waiting for his sign-in, or do other parts of the task.',
  badsite: 'No https site to save a login for. Open the site\'s sign-in page with browser_go first, then call ask_login again.',
  failed: 'The login could not be saved in the keychain. Do not ask for the password in chat; tell Ben in one line.'
};
function modelResult(r) {
  return { text: JSON.stringify({ saved: !!r.saved, site: r.site || '' }) + '\n' + (HINT[r.state] || ''), saved: !!r.saved, site: r.site || '', state: r.state,
    summary: r.saved ? (r.state === 'already' ? 'Login already saved for ' : 'Ben saved a login for ') + (r.site || 'the site') : r.state === 'queued' ? 'Sign-in form queued for Ben (' + (r.site || '') + ')' : 'No login saved for ' + (r.site || 'the site'),
    error: false };
}

// o: {store (LoginStore), open({token, origin, host, reason, focus}) -> handle {close(), show(focus)} | null,
//     notify(title, body, onClick), isAway() -> bool, now, waitMs}
class LoginAsk {
  constructor(o) { this.o = o; this.now = o.now || Date.now; this.byOrigin = new Map(); this.byToken = new Map(); this.declined = new Map(); this.seq = 0; }
  // -> {saved, site, state}. o: {site, reason, pageUrl, helper (a Mote), wait (main chat: true)}
  async ask(a) {
    a = a || {};
    const origin = resolveOrigin(a.site, a.pageUrl);
    if (!origin) return { saved: false, site: String(a.site || '').slice(0, 80), state: 'badsite' };
    const host = L.hostOfOrigin(origin);
    if (this.o.store.item(origin)) return { saved: true, site: host, state: 'already' };
    const away = !!a.helper || (this.o.isAway ? !!this.o.isAway() : false);
    let e = this.byOrigin.get(origin);
    if (!e) {
      const d = this.declined.get(origin);
      if (away && d && this.now() - d < DECLINE_MS) return { saved: false, site: host, state: 'declined' };
      e = this._entry(origin, host, a.reason);
      if (away) { e.queued = true; this._notify(e); return { saved: false, site: host, state: 'queued' }; }
      this._open(e, true);
    } else if (away) {
      return { saved: false, site: host, state: e.handle ? 'waiting' : 'queued' };   // one form, one notification: nothing new
    } else if (!e.handle) this._open(e, true);       // Ben is here now and the main chat asks: the queued form opens
    else { try { e.handle.show(true); } catch (err) { /* ui only */ } }
    if (a.wait === false) return { saved: false, site: host, state: 'waiting' };
    const waitMs = this.o.waitMs == null ? WAIT_MS : this.o.waitMs;
    const timeout = new Promise((r) => { const t = setTimeout(() => r('waiting'), waitMs); if (t.unref) t.unref(); });
    const signal = a.signal ? new Promise((r) => { if (a.signal.aborted) r('stopped'); else a.signal.addEventListener('abort', () => r('stopped'), { once: true }); }) : null;
    const v = await Promise.race([e.done, timeout].concat(signal ? [signal] : []));
    if (v === 'saved') return { saved: true, site: host, state: 'saved' };
    if (v === 'cancelled') return { saved: false, site: host, state: 'cancelled' };
    return { saved: false, site: host, state: 'waiting' };
  }
  _entry(origin, host, reason) {
    const token = 'F' + (++this.seq) + Math.random().toString(36).slice(2, 10);
    let fin; const done = new Promise((r) => { fin = r; });
    const e = { token, origin, host, reason: String(reason || '').replace(/[\u0000-\u001f]/g, ' ').slice(0, 160), done, fin, handle: null, queued: false, notified: false, t: this.now() };
    this.byOrigin.set(origin, e); this.byToken.set(token, e);
    return e;
  }
  _open(e, focus) {
    e.queued = false;
    try { e.handle = this.o.open({ token: e.token, origin: e.origin, host: e.host, reason: e.reason, focus: !!focus }) || null; } catch (err) { e.handle = null; }
  }
  _notify(e) {
    if (e.notified) return; e.notified = true;
    try { this.o.notify('Glim needs a sign-in', 'Tap to sign in to ' + e.host + ' in Glim\'s private form' + (e.reason ? ': ' + e.reason : '.'), () => this.openQueued(e.origin, true)); } catch (err) { /* nicety */ }
  }
  // the notification was clicked, or Ben came back: show the queued form(s)
  openQueued(origin, focus) {
    for (const e of this.byOrigin.values()) if (e.queued && (!origin || e.origin === origin)) this._open(e, focus);
  }
  pending() { return [...this.byOrigin.values()].map((e) => ({ host: e.host, open: !!e.handle, queued: e.queued })); }
  info(token) { const e = this.byToken.get(String(token || '')); return e ? { host: e.host, origin: e.origin, reason: e.reason } : null; }
  // from the form window only (main.js checks the sender). -> {ok, error} for the form; the model never sees this
  async submit(token, user, password) {
    const e = this.byToken.get(String(token || '')); if (!e) return { ok: false, error: 'This form has expired. Close it.' };
    const r = await this.o.store.save(e.origin, user, password);
    if (!r.ok) return { ok: false, error: r.error };
    this._finish(e, 'saved');
    return { ok: true, host: e.host };
  }
  cancel(token) {
    const e = this.byToken.get(String(token || '')); if (!e) return { ok: false };
    this.declined.set(e.origin, this.now());
    this._finish(e, 'cancelled');
    return { ok: true };
  }
  _finish(e, v) {
    this.byOrigin.delete(e.origin); this.byToken.delete(e.token);
    const h = e.handle; e.handle = null;
    try { if (h) h.close(); } catch (err) { /* gone */ }
    e.fin(v);
  }
  // the form window was closed with the window's own close button = Cancel
  closed(token) { if (this.byToken.has(String(token || ''))) this.cancel(token); }
}

// browser_sign_in's body (main.js and test/secure-login-electron.js run this one): a saved login -> the app fills it; none -> the
// private form (askFor); saved there -> filled at once. The model reads the Browser.signIn text or modelResult(), never a secret.
// o: {br (src/tools/browser.js Browser), store (LoginStore), askFor(pageUrl, site, reason) -> Promise<{saved, site, state}>}
async function signInWithAsk(o) {
  const r = await o.br.signIn((u) => o.store.forPage(u));
  if (r.kind !== 'none') return r;
  const q = await o.askFor(o.br.state().url, '', 'to sign in on ' + r.host);
  if (q.saved) return o.br.signIn((u) => o.store.forPage(u));
  const m = modelResult(q);
  return { ...m, text: 'No saved login for ' + r.host + '. ' + m.text };
}

module.exports = { LoginAsk, resolveOrigin, modelResult, signInWithAsk, HINT, WAIT_MS, DECLINE_MS };
