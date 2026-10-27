'use strict';
const { app, BrowserWindow, WebContentsView, ipcMain, session, shell, nativeTheme, Notification, Menu, globalShortcut, nativeImage } = require('electron');
const path = require('path');
const os = require('os');
const fs = require('fs');

const E2E = process.argv.includes('--e2e');
if (E2E) {
  app.setPath('userData', fs.mkdtempSync(path.join(os.tmpdir(), 'desk-e2e-')));
  app.commandLine.appendSwitch('no-sandbox');
  app.commandLine.appendSwitch('disable-gpu');
}
if (process.platform === 'linux') app.commandLine.appendSwitch('no-sandbox');

const { Store } = require('./src/store');
const { Agent, DANGER_LABELS } = require('./src/agent');
const { buildTools } = require('./src/prompt');
const { Browser } = require('./src/tools/browser');
const { webSearch } = require('./src/tools/web');
const { runShell } = require('./src/tools/shell');
const { Diary } = require('./src/tools/diary');
const { createScreen } = require('./src/tools/screen');
const { Helpers, Limiter, ScreenLock, createRunner, addNotice, short } = require('./src/helpers');
const { agentTools } = require('./src/tools/agents');
const { Warmer } = require('./src/warm');
const { PillState } = require('./src/pillstate');
const { ensureCard } = require('./src/cards');
const { Popup } = require('./src/popup');
const { PillWindow } = require('./src/pillwin');

let win = null;
let store = null;
let agent = null;
let diary = null;
let screen = null;
let toolDefs = buildTools({ diary: false }); // replaced once the diary probe is done (after first paint)
let toolsReady = Promise.resolve();
let activeThread = null; // thread object being run by the primary agent
let helpers = null;
let limiter = null;
let warmer = null;
let pillWin = null;
let quitting = false;
let gwState = { state: 'down' };
let e2eEnv = null;
const timing = {}; // startup marks (checked by the e2e: the window must show before the deferred work starts)
const screenLock = new ScreenLock();
const browsers = new Map();   // 'primary' | helper thread id -> {key, label, br, popup}  (created on first use)
const loginWaits = new Map(); // browser key -> finish(value): a sign-in hand-off is waiting for Ben
let openThreadId = null;  // thread the UI has open
const SCREEN_TOOLS = new Set(['screen_look', 'screen_click', 'screen_type', 'screen_key', 'open_app']);
const BROWSER_TOOLS = ['browser_go', 'browser_click', 'browser_type', 'browser_scroll', 'browser_back', 'browser_read'];
const pending = new Map(); // approval/ask id -> resolve
const cards = new Map();   // approval/ask id -> {threadId, ev}: replayed when Ben opens that thread later
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const send = (channel, payload) => { if (win && !win.isDestroyed()) win.webContents.send(channel, payload); };
const dark = () => nativeTheme.shouldUseDarkColors;

// ---- one state source for Glim (pill, top bar, dock badge) -------------------------------------
const pillState = new PillState({ onChange: () => { schedulePill(); } });
let pillTimer = null;
function schedulePill() { if (pillTimer) return; pillTimer = setTimeout(() => { pillTimer = null; updatePill(); }, 30); }
function chatInFront() { return !E2E && win && !win.isDestroyed() && win.isVisible() && win.isFocused(); }
function updatePill() {
  const st = pillState.status();
  send('glim-state', st);
  try { if (process.platform === 'darwin' && app.dock) app.dock.setBadge(st === 'error' || st === 'waiting' ? '!' : ''); } catch (e) { /* ignore */ }
  if (pillWin) pillWin.update(pillState.view(), chatInFront());
}
setInterval(() => { if (pillState.tick() || (pillWin && pillWin.view && pillWin.view.visible)) updatePill(); }, 1000).unref();

function waitFor(id, signal, fallback, card) {
  return new Promise((resolve) => {
    const fin = (v) => { pending.delete(id); cards.delete(id); pillState.onEvent && resumeRid(id); resolve(v); };
    pending.set(id, fin);
    if (card) cards.set(id, card);
    const onAbort = () => fin(fallback);
    if (signal) { if (signal.aborted) return onAbort(); signal.addEventListener('abort', onAbort, { once: true }); }
  });
}
function resumeRid(rid) {
  for (const a of pillState.agents.values()) if (a.approval && a.approval.rid === rid) pillState.onEvent(a.key, a.name, a.threadId, { type: 'resumed' });
}

const ICON = path.join(__dirname, 'assets', 'icon.png');
function notify(title, body, threadId) {
  try {
    if (!Notification.isSupported()) return;
    const n = new Notification({ title, body: short(body, 180), icon: process.platform === 'darwin' ? ICON : undefined });
    n.on('click', () => { showWindow(); if (threadId) send('open-thread', threadId); });
    n.show();
  } catch (e) { /* notifications are a nicety */ }
}

// ---- window --------------------------------------------------------------------------------------
function showWindow(focusComposer) {
  if (!win || win.isDestroyed()) createWindow();
  if (win.isMinimized()) win.restore();
  win.show(); win.focus();
  if (focusComposer) send('focus-composer', true);
  updatePill();
}
function toggleWindow() {
  if (win && !win.isDestroyed() && win.isVisible() && win.isFocused()) win.hide();
  else showWindow(true);
}

function createWindow() {
  timing.created = Date.now();
  const mac = process.platform === 'darwin';
  win = new BrowserWindow({
    width: 1000, height: 840, minWidth: 560, minHeight: 520,
    show: false, // shown on ready-to-show: no white flash, no half-painted window
    backgroundColor: dark() ? '#17120f' : '#faf6f0',
    title: 'Premonition Desk',
    icon: mac ? undefined : ICON,
    titleBarStyle: mac ? 'hiddenInset' : 'default',
    trafficLightPosition: mac ? { x: 16, y: 18 } : undefined,
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: false, nodeIntegration: false }
  });
  win.once('ready-to-show', () => {
    timing.readyToShow = Date.now();
    const hidden = !E2E && process.platform === 'darwin' && app.getLoginItemSettings().wasOpenedAsHidden;
    if (!hidden) win.show();
    setTimeout(() => afterFirstPaint().catch((e) => console.error('startup', e)), 0);
  });
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  win.on('close', (e) => {
    if (quitting || !store || !store.getSettings().keepRunning) return;
    e.preventDefault(); win.hide(); // keep running in the background (Cmd+Q really quits)
  });
  for (const ev of ['focus', 'blur', 'show', 'hide']) win.on(ev, () => { if (ev === 'focus' || ev === 'show') pillState.markSeen(openThreadId); updatePill(); });
  win.on('closed', () => { win = null; if (!quitting && store && !store.getSettings().keepRunning) app.quit(); });
  return win;
}

// ---- browsers: one per agent, created on first use; each has a hidden popup window that Ben can open ----
function makeBrowser(key, label) {
  let rec = browsers.get(key);
  if (rec) return rec;
  const view = new WebContentsView({ webPreferences: { partition: 'persist:desk', contextIsolation: true, sandbox: true, nodeIntegration: false, backgroundThrottling: false } });
  const popup = new Popup({ parent: win, view, title: label || 'Browser', dark: dark(), quitting: () => quitting });
  const br = new Browser({ view, session, onState: (s) => popup.sendState(s) });
  rec = { key, label, br, popup };
  browsers.set(key, rec);
  return rec;
}
function dropBrowser(key) {
  const rec = browsers.get(key);
  if (!rec) return;
  browsers.delete(key);
  const f = loginWaits.get(key); if (f) f('stopped');
  rec.br.destroy(); rec.popup.destroy();
}
const primary = () => makeBrowser('primary', 'Glim’s browser');

// A sign-in hand-off: show the popup with the banner and wait (abortably) until Ben clicks Done or Not now.
function signInWait(key, threadId, signal) {
  return new Promise((resolve) => {
    const rec = browsers.get(key);
    if (!rec) return resolve('skip');
    const finish = (v) => {
      if (!loginWaits.has(key)) return;
      loginWaits.delete(key); rec.popup.setBanner(false); rec.popup.hide();
      send('agent', { threadId, type: 'resumed', key });
      resolve(v);
    };
    loginWaits.set(key, finish);
    if (signal) { if (signal.aborted) return finish('stopped'); signal.addEventListener('abort', () => finish('stopped'), { once: true }); }
    if (win && !win.isDestroyed() && !win.isVisible()) showWindow();
    rec.popup.show({ banner: true });
    send('agent', { threadId, type: 'login', key });
    const a = [...pillState.agents.values()].find((x) => x.threadId === threadId);
    if (a) pillState.onEvent(a.key, a.name, threadId, { type: 'login' });
  });
}
const afterSignIn = async (br, v) => v === 'done'
  ? 'Login needed: Ben is signing in himself. He clicked Done. Fresh snapshot of the page now:\n' + (await br.snapshot())
  : v === 'stopped' ? '[stopped by user]' : 'Login needed: Ben is signing in himself, but he chose not to right now. Do not type credentials. Tell him what you could not finish.';

// ---- agents ------------------------------------------------------------------------------------
// One Agent per run owner: the primary, and a fresh one for each helper run. Same prompt, same tool list.
function createAgent({ helper, rec }) {
  const isHelper = !!helper;
  const br = rec ? rec.br : null;                  // helpers get theirs up front; the primary's is created on first use
  const bKey = isHelper ? helper.threadId : 'primary';
  const getBr = () => (isHelper ? br : primary().br);
  const pKey = isHelper ? helper.id : 'main';
  const pName = isHelper ? helper.name : 'Glim';
  const holder = screenLock.holder();
  const agentRef = { withoutSlot: (fn, signal) => a.withoutSlot(fn, signal) };

  // live browser card: one per activity group; thumbnail refreshed after every action and every 1.5 s while the run is going
  const live = { item: null, timer: null, busy: false, thread: null };
  const cardEvent = (active) => {
    const it = live.item; if (!it) return;
    send('agent', { threadId: a.threadId, type: 'bcard', id: it.id, key: bKey, url: it.url, title: it.title, favicon: it.favicon, thumb: it.thumb, active, login: loginWaits.has(bKey) });
  };
  const capture = async () => {
    const it = live.item; if (!it || live.busy) return;
    live.busy = true;
    try {
      const cur = browsers.get(bKey);
      if (!cur) return;
      const s = cur.br.state();
      it.url = s.url; it.title = s.title; it.favicon = s.favicon;
      const t = await cur.br.thumb(360);
      if (t) it.thumb = t;
    } finally { live.busy = false; }
    cardEvent(true);
  };
  const touchCard = (thread) => {
    live.thread = thread;
    const it = ensureCard(thread, 'browser', bKey);
    if (live.item !== it) { live.item = it; cardEvent(true); }
    const cur = browsers.get(bKey); if (cur) cur.popup.setActive(true);
    if (!live.timer) { live.timer = setInterval(capture, 1500); live.timer.unref && live.timer.unref(); }
  };
  const endCard = async () => {
    clearInterval(live.timer); live.timer = null;
    const it = live.item, thread = live.thread;
    if (!it) return;
    await capture();
    const cur = browsers.get(bKey); if (cur) cur.popup.setActive(false);
    cardEvent(false);
    live.item = null; live.thread = null;
    try { if (thread) store.saveThread(thread); } catch (e) { /* ignore */ }
  };

  const tools = {
    web_search: (x, ctx) => webSearch(x.query, { signal: ctx.signal }),
    browser_go: (x) => getBr().go(x.url),
    browser_click: (x) => getBr().click(x.id),
    browser_type: async (x, ctx) => {
      const b = getBr();
      // Never type into a password / payment field: Ben signs in himself in the popup while we wait.
      const why = await b.sensitiveReason(x.id);
      if (why) {
        const v = await ctx.waitForBen(() => signInWait(bKey, a.threadId, ctx.signal));
        return { text: await afterSignIn(b, v), summary: 'Waited while Ben signed in', error: v === 'stopped' };
      }
      return b.type(x.id, x.text, x.enter);
    },
    browser_scroll: (x) => getBr().scroll(x.direction),
    browser_back: () => getBr().back(),
    browser_read: (x) => getBr().read(x.page),
    run_shell: (x, ctx) => runShell(String(x.command || ''), { signal: ctx.signal }),
    ask_user: () => '',
    diary_search: (x) => diary.search(x.query),
    ...screen.tools,
    ...agentTools(helpers, { isHelper })
  };
  for (const n of BROWSER_TOOLS) {
    const run = tools[n];
    tools[n] = async (x, ctx) => {
      touchCard(ctx.thread);
      let r = await run(x, ctx);
      if (typeof r === 'string') r = { text: r };
      const v = store.getSettings().vision;
      if (n !== 'browser_read' && (v === 'on' || v === true) && !r.error) r.image = await getBr().screenshot(1280);
      await capture();
      return r;
    };
  }
  // one mouse: the first screen tool of a run takes the global lock (FIFO) and keeps it until the run ends
  for (const n of SCREEN_TOOLS) {
    const run = tools[n];
    // (waiting for the lock must not hold a run slot: the lock holder may be queued for one)
    tools[n] = async (x, ctx) => { if (!holder.held()) await agentRef.withoutSlot(() => holder.ensure(ctx.signal), ctx.signal); return run(x, ctx); };
  }
  const meta = () => ({ title: isHelper ? helper.name : (activeThread && activeThread.title) });
  const a = new Agent({
    getSettings: isHelper ? () => ({ ...store.getSettings(), mode: store.getSettings().helperMode || 'hands-off' }) : () => store.getSettings(),
    tools,
    toolDefs: () => toolDefs,
    slot: limiter,
    onState: helper && helper.onState,
    onEnd: () => { holder.release(); endCard(); },
    emit: (ev) => { send('agent', { threadId: a.threadId, ...ev }); pillState.onEvent(pKey, pName, a.threadId, ev, meta()); },
    approve: (req, signal) => {
      const rid = a.threadId + ':' + req.id;
      const ev = { threadId: a.threadId, type: 'approval', rid, ...req };
      send('agent', ev); pillState.onEvent(pKey, pName, a.threadId, ev, meta());
      return waitFor(rid, signal, 'deny', { threadId: a.threadId, ev });
    },
    askUser: (question, signal) => {
      const id = 'ask_' + Date.now() + '_' + a.threadId;
      const ev = { threadId: a.threadId, type: 'ask', id, question };
      send('agent', ev); pillState.onEvent(pKey, pName, a.threadId, ev, meta());
      return waitFor(id, signal, '[stopped by user]', { threadId: a.threadId, ev });
    },
    // the model keeps repeating itself: a sign-in / passkey page goes to Ben, anything else is a question to Ben
    onStuck: async (stuck, signal) => {
      if (stuck.tool.startsWith('browser_') && browsers.get(bKey) && await browsers.get(bKey).br.looksLikeAuth()) {
        const b = browsers.get(bKey).br;
        const v = await signInWait(bKey, a.threadId, signal);
        return v === 'done' ? 'You were stuck on a sign-in page. Ben completed that step himself in the browser window. Fresh snapshot:\n' + (await b.snapshot()) : v === 'stopped' ? '[stopped by user]' : 'Ben did not complete the sign-in. Stop trying that page and tell him what is blocked.';
      }
      const answer = await a.o.askUser('I keep repeating "' + stuck.summary + '" and nothing changes. What should I do instead?', signal);
      return 'You were stuck repeating ' + stuck.summary + '. Ben says: ' + answer;
    },
    onThreadChange: (t) => store.saveThread(t)
  });
  return a;
}

// Helper run: its own browser (hidden popup, same partition), destroyed when the run ends.
function makeHelperAgent(h, { onState }) {
  const rec = makeBrowser(h.threadId, h.name + '’s browser');
  const agent = createAgent({ helper: { id: h.id, name: h.name, threadId: h.threadId, onState }, rec });
  return { agent, dispose: () => dropBrowser(h.threadId) };
}

// A finished helper leaves a notice in the thread that started it (injected into the model's history on
// Ben's next message) and a macOS notification.
function postNotice(threadId, name, summary) {
  const live = activeThread && activeThread.id === threadId && agent.running;
  const t = live ? activeThread : store.loadThread(threadId);
  if (!t) return;
  addNotice(t, name, summary);
  store.saveThread(t);
  send('agent', { threadId, type: 'notice', helper: name, text: short(summary, 200) });
}

function buildAgent() {
  screen = createScreen(() => store.getSettings(), process.resourcesPath, (look, ctx) => {
    // screen card: latest capture as a small thumbnail in the chat; the full image rides along for the viewer
    const thread = ctx && ctx.thread; if (!thread) return;
    const it = ensureCard(thread, 'screen', 'screen');
    it.text = short(look.text, 3500);
    let thumb = null;
    try { if (look.image) { const im = nativeImage.createFromDataURL(look.image); thumb = 'data:image/jpeg;base64,' + im.resize({ width: 480 }).toJPEG(60).toString('base64'); } } catch (e) { /* no thumbnail */ }
    if (thumb) it.thumb = thumb;
    send('agent', { threadId: thread.id, type: 'scard', id: it.id, thumb: it.thumb, text: it.text, image: look.image || null });
  });
  limiter = new Limiter(() => store.getSettings().maxParallel || 2);
  helpers = new Helpers({
    file: path.join(app.getPath('userData'), 'helpers.json'),
    store,
    runner: createRunner({ store, makeAgent: makeHelperAgent }),
    onChange: () => send('helpers:changed', helpers.list()),
    onFinish: (h, summary, parent) => {
      if (parent) postNotice(parent, h.name, summary);
      notify('Helper ' + h.name + ' finished', summary, h.threadId);
      send('threads:changed', {});
    },
    onNeedBen: (h) => notify('Helper ' + h.name + ' needs you', 'Open its thread to answer.', h.threadId)
  });
  agent = createAgent({ helper: null, rec: null });
}

// ---- settings side effects -----------------------------------------------------------------------
async function refreshDiary() {
  diary.stop(); diary.ready = null;
  const s = store.getSettings();
  const has = E2E || !s.diaryEnabled ? false : await diary.probe();
  toolDefs = buildTools({ diary: has });
  return has;
}
function registerHotkey(acc) {
  try { globalShortcut.unregisterAll(); } catch (e) { /* ignore */ }
  acc = String(acc || '').trim();
  if (!acc) return { ok: true, off: true };
  try { return globalShortcut.register(acc, toggleWindow) ? { ok: true } : { ok: false, error: 'That shortcut is taken by another app.' }; } catch (e) { return { ok: false, error: 'That is not a valid shortcut.' }; }
}
function setLoginItem(on) { try { app.setLoginItemSettings({ openAtLogin: !!on, openAsHidden: true }); } catch (e) { /* not supported here */ } }
function applyTheme(s) { nativeTheme.themeSource = s.theme === 'light' || s.theme === 'dark' ? s.theme : 'system'; }

async function applySettings(patch) {
  const prev = store.getSettings();
  const next = store.saveSettings(patch);
  const ch = (k) => k in patch && next[k] !== prev[k];
  const out = { ...next };
  if (ch('theme')) applyTheme(next);
  if (ch('openAtLogin')) setLoginItem(next.openAtLogin);
  if (ch('hotkey')) out._hotkey = registerHotkey(next.hotkey);
  if (ch('pill') && pillWin) { pillWin.enabled = next.pill; updatePill(); }
  if (ch('gatewayUrl') && warmer) warmer.gatewayMoved();
  else if (ch('model') && warmer) warmer.rewarm();
  if (ch('diaryEnabled') || ch('diaryPath') || ch('pythonPath')) { await refreshDiary(); if (warmer) warmer.rewarm(); }
  return out;
}

async function afterFirstPaint() {
  if (afterFirstPaint.done) return;
  afterFirstPaint.done = true;
  timing.deferred = Date.now(); timing.browsersAtPaint = browsers.size; timing.helpersTimerAtPaint = !!(helpers && helpers.timer);
  const s = store.getSettings();
  // everything below is deferred until the window is on screen
  await refreshDiary();
  warmer = new Warmer({
    getSettings: () => store.getSettings(), getTools: () => toolDefs, busy: () => !!(agent && agent.running),
    onState: (state, info) => { gwState = { state, ...info }; send('gateway', gwState); }
  });
  warmer.start();
  helpers.start(); // runs anything that came due while the app was closed (once), then ticks every 30 s
  pillWin = new PillWindow({ dark: dark() });
  pillWin.enabled = s.pill !== false;
  pillWin.ready.then(updatePill);
  const hk = registerHotkey(s.hotkey);
  if (!hk.ok) console.warn('hotkey:', hk.error);
  if (!E2E) setLoginItem(s.openAtLogin);
  toolsReady = Promise.resolve();
  if (E2E) {
    require('./test/e2e.js').run({
      app, win, store, helpers, send, browsers, pillWin, pillState, warmer, applySettings, env: e2eEnv, pending,
      loginWaits, timing, getWin: () => win, showWindow
    }).catch((e) => { console.error('E2E crashed', e); app.exit(1); });
  }
}

function buildMenu() {
  const mac = process.platform === 'darwin';
  const openSettings = () => { showWindow(); send('open-settings', true); };
  const tpl = [
    ...(mac ? [{ label: app.name, submenu: [{ role: 'about' }, { type: 'separator' }, { label: 'Settings…', accelerator: 'CmdOrCtrl+,', click: openSettings }, { type: 'separator' }, { role: 'hide' }, { role: 'hideOthers' }, { role: 'unhide' }, { type: 'separator' }, { role: 'quit' }] }] : []),
    { label: 'File', submenu: [{ label: 'New thread', accelerator: 'CmdOrCtrl+N', click: () => { showWindow(); send('new-thread', true); } }, ...(mac ? [] : [{ label: 'Settings…', accelerator: 'CmdOrCtrl+,', click: openSettings }, { type: 'separator' }]), mac ? { role: 'close' } : { role: 'quit' }] },
    { role: 'editMenu' },
    { label: 'View', submenu: [{ role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' }, { role: 'togglefullscreen' }] },
    { role: 'windowMenu' }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(tpl));
}

function registerIpc() {
  const h = (name, fn) => ipcMain.handle(name, async (e, ...a) => fn(...a));
  h('settings:get', () => store.getSettings());
  h('settings:set', (patch) => applySettings(patch));
  h('threads:list', () => store.listThreads());
  h('threads:new', () => { const t = store.newThread(); store.saveThread(t); openThreadId = t.id; return t; });
  h('threads:load', (id) => {
    const t = store.loadThread(id);
    if (!t) return t;
    openThreadId = id; pillState.markSeen(id);
    const hp = helpers.byThread(id);
    t.running = hp ? helpers.isRunning(hp.id) : !!(agent.running && activeThread && activeThread.id === id);
    t.pendingCards = [...cards.values()].filter((c) => c.threadId === id).map((c) => c.ev);
    t.loginWaiting = [...loginWaits.keys()].some((k) => (k === 'primary' ? (activeThread && activeThread.id === id) : k === id));
    return t;
  });
  h('threads:delete', (id) => { if (!helpers.byThread(id)) store.deleteThread(id); return true; });
  h('threads:rename', (id, title) => { store.renameThread(id, title); return true; });
  h('agent:send', async (threadId, text) => {
    const hp = helpers.byThread(threadId);
    if (hp) return helpers.steer(hp.id, text) ? { steered: true } : { error: "This is a helper's thread. Use Run now in the Agents list, or ask the primary agent." };
    if (agent.running) {
      if (activeThread && activeThread.id === threadId) { agent.steer(text); return { steered: true }; }
      return { error: 'Premonition is busy in another thread.' };
    }
    await Promise.race([toolsReady, sleep(3000)]); // the tool list must be final before the first request (prompt cache)
    const t = store.loadThread(threadId) || store.newThread();
    if (!t.title || t.title === 'New thread') t.title = String(text).replace(/\s+/g, ' ').trim().slice(0, 48) || 'New thread';
    activeThread = t;
    agent.run(t, text).then((r) => {
      send('threads:changed', {});
      if (!r.stopped && !chatInFront() && !(pillWin && pillWin.enabled)) notify('Glim finished', t.title, t.id);
    });
    return { started: true, title: t.title };
  });
  h('agent:stop', (threadId) => { const hp = threadId && helpers.byThread(threadId); if (hp) helpers.abort(hp.id); else agent.stop(); return true; });
  h('helpers:list', () => helpers.list());
  h('helpers:run', (id) => helpers.runNow(id));
  h('helpers:pause', (id) => { helpers.pause(id); return true; });
  h('helpers:delete', (id) => helpers.remove(id));
  h('respond', (id, value) => { const r = pending.get(id); if (r) { pending.delete(id); r(value); } return true; });
  // browser popup: open the real page for Ben (a card was clicked, or a link in the chat)
  h('browser:open', async (key, url, navigate) => {
    let rec = browsers.get(key);
    const fresh = !rec;
    if (!rec) rec = primary(); // that agent's browser is gone (helper finished / app restarted): use the main one
    if (url && (navigate || fresh || !rec.br.wc.getURL() || rec.br.wc.getURL() === 'about:blank')) rec.br.go(url).catch(() => {});
    await rec.popup.show({ banner: loginWaits.has(rec.key) });
    return true;
  });
  h('screen:check', async () => {
    if (!screen.findHelper()) return { error: 'screen control helper not installed' };
    return screen.check();
  });
  h('screen:ask', async () => {
    if (!screen.findHelper()) return { error: 'screen control helper not installed' };
    return screen.askPermissions();
  });
  h('system:open', (pane) => {
    const urls = { accessibility: 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility', screen: 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture' };
    if (urls[pane]) { try { shell.openExternal(urls[pane]); } catch (e) { /* not on a Mac */ } }
    return true;
  });
  h('open:external', (url) => { if (/^https?:/.test(url)) shell.openExternal(url); return true; });
  h('gateway:state', () => gwState);
  h('gateway:test', async () => {
    const s = store.getSettings();
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 4000);
    const t0 = Date.now();
    try {
      const r = await fetch(String(s.gatewayUrl).replace(/\/+$/, '') + '/models', { signal: ctl.signal });
      return { ok: r.ok, ms: Date.now() - t0, status: r.status };
    } catch (e) { return { ok: false, error: ctl.signal.aborted ? 'No answer within 4 s' : String(e && e.cause && e.cause.code || e.message) }; } finally { clearTimeout(t); }
  });
  h('info', () => ({ platform: process.platform, e2e: E2E, diary: toolDefs.some((t) => t.function.name === 'diary_search'), danger: DANGER_LABELS, version: app.getVersion() }));

  // popup chrome (address bar, back/forward, hand back, close)
  ipcMain.handle('popup:cmd', async (e, cmd, arg) => {
    const rec = [...browsers.values()].find((r) => r.popup.wcId === e.sender.id);
    if (!rec) return null;
    const wc = rec.br.wc;
    const hst = wc.navigationHistory;
    switch (cmd) {
      case 'back': if (hst.canGoBack()) hst.goBack(); break;
      case 'forward': if (hst.canGoForward()) hst.goForward(); break;
      case 'reload': wc.reload(); break;
      case 'go': rec.br.go(arg).catch(() => {}); break;
      case 'close': rec.popup.hide(); break;
      case 'done': { const f = loginWaits.get(rec.key); if (f) f('done'); else rec.popup.hide(); break; }
      case 'skip': { const f = loginWaits.get(rec.key); if (f) f('skip'); else rec.popup.hide(); break; }
      case 'handback': { const f = loginWaits.get(rec.key); if (f) f('done'); else rec.popup.hide(); break; }
      case 'state': return { ...rec.br.state(), active: !!rec.popup.active, banner: rec.popup.banner, label: rec.label };
      default: break;
    }
    return true;
  });
  // status pill actions
  ipcMain.handle('pill:act', async (e, name, arg) => {
    switch (name) {
      case 'hover': if (pillWin) pillWin.setInteractive(!!arg); break;
      case 'open': { showWindow(); if (arg && arg.threadId) send('open-thread', arg.threadId); if (arg && arg.key) pillState.dismiss(arg.key); break; }
      case 'stop': if (arg === 'main') agent.stop(); else helpers.abort(arg); break;
      case 'respond': { const r = pending.get(arg.rid); if (r) { pending.delete(arg.rid); r(arg.value); send('agent', { threadId: arg.threadId, type: 'resolved', rid: arg.rid, value: arg.value }); } break; }
      case 'openBrowser': { const key = arg === 'main' ? 'primary' : arg; const rec = browsers.get(key); if (rec) { showWindow(); rec.popup.show({ banner: loginWaits.has(key) }); } break; }
      case 'dismiss': pillState.dismiss(arg); break;
      default: break;
    }
    return true;
  });
}

if (!E2E && !app.requestSingleInstanceLock()) app.quit();
app.on('second-instance', () => showWindow(true));
app.on('activate', () => { if (store) showWindow(); });
app.on('before-quit', () => { quitting = true; });
app.on('will-quit', () => { try { globalShortcut.unregisterAll(); } catch (e) { /* ignore */ } });

app.whenReady().then(async () => {
  store = new Store(app.getPath('userData'));
  if (E2E) e2eEnv = await require('./test/e2e.js').prepare(store);
  applyTheme(store.getSettings());
  diary = new Diary(() => store.getSettings());
  buildMenu();
  buildAgent();
  registerIpc();
  createWindow(); // shown on ready-to-show; diary, helpers, warm-up, pill, hotkey start after that (afterFirstPaint)
});

app.on('window-all-closed', () => { try { helpers && helpers.close(); } catch (e) { /* ignore */ } try { diary && diary.stop(); } catch (e) { /* ignore */ } app.quit(); });
