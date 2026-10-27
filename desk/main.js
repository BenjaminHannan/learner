'use strict';
const { app, BrowserWindow, WebContentsView, ipcMain, session, shell, nativeTheme, Notification } = require('electron');
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
const { Agent } = require('./src/agent');
const { buildTools } = require('./src/prompt');
const { Browser } = require('./src/tools/browser');
const { webSearch } = require('./src/tools/web');
const { runShell } = require('./src/tools/shell');
const { Diary } = require('./src/tools/diary');
const { createScreen } = require('./src/tools/screen');
const { Helpers, Limiter, ScreenLock, createRunner, addNotice, short } = require('./src/helpers');
const { agentTools } = require('./src/tools/agents');

let win = null;
let store = null;
let browser = null;       // the primary agent's browser (the one Ben normally sees)
let shown = null;         // whichever browser is attached to the window right now
let agent = null;
let diary = null;
let screen = null;
let toolDefs = null;
let activeThread = null; // thread object being run by the primary agent
let helpers = null;
let limiter = null;
const screenLock = new ScreenLock();
const helperBrowsers = new Map(); // helper thread id -> Browser (only while that helper runs)
let openThreadId = null;  // thread the UI has open
let lastBounds = null;
let lastVisible = false;
const SCREEN_TOOLS = new Set(['screen_look', 'screen_click', 'screen_type', 'screen_key', 'open_app']);
const pending = new Map(); // approval/ask id -> resolve
const cards = new Map();   // approval/ask id -> {threadId, ev}: replayed when Ben opens that thread later

const send = (channel, payload) => { if (win && !win.isDestroyed()) win.webContents.send(channel, payload); };

function waitFor(id, signal, fallback, card) {
  return new Promise((resolve) => {
    const fin = (v) => { pending.delete(id); cards.delete(id); resolve(v); };
    pending.set(id, fin);
    if (card) cards.set(id, card);
    const onAbort = () => fin(fallback);
    if (signal) { if (signal.aborted) return onAbort(); signal.addEventListener('abort', onAbort, { once: true }); }
  });
}

function notify(title, body, threadId) {
  try {
    if (!Notification.isSupported()) return;
    const n = new Notification({ title, body: short(body, 180) });
    n.on('click', () => { if (win && !win.isDestroyed()) { win.show(); win.focus(); if (threadId) send('open-thread', threadId); } });
    n.show();
  } catch (e) { /* notifications are a nicety */ }
}

// ---- browsers: one per agent; the Browser tab shows the one that belongs to the open thread ----
const makeView = () => new WebContentsView({ webPreferences: { partition: 'persist:desk', contextIsolation: true, sandbox: true, nodeIntegration: false } });
const cur = () => shown || browser;
const browserState = (b) => (s) => { if (b === cur()) send('browser-state', s); };
function showBrowser(b) {
  const old = cur();
  if (old === b) return;
  old.detach();
  shown = b;
  if (lastBounds) b.setBounds(lastBounds);
  b.setVisible(lastVisible);
  send('browser-state', b.state());
}
function showFor(threadId) { showBrowser(helperBrowsers.get(threadId) || browser); }

function createWindow() {
  const mac = process.platform === 'darwin';
  win = new BrowserWindow({
    width: 1360, height: 860, minWidth: 980, minHeight: 600,
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#14110f' : '#f7f2ec',
    title: 'Premonition Desk',
    titleBarStyle: mac ? 'hiddenInset' : 'default',
    trafficLightPosition: mac ? { x: 16, y: 16 } : undefined,
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: false, nodeIntegration: false }
  });
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  win.on('closed', () => { win = null; });
  return win;
}

// One Agent per run owner: the primary, and a fresh one for each helper run. Same prompt, same tool list.
function createAgent({ helper, br }) {
  const isHelper = !!helper;
  const holder = screenLock.holder();
  const tools = {
    web_search: (a, ctx) => webSearch(a.query, { signal: ctx.signal }),
    browser_go: (a) => br.go(a.url),
    browser_click: (a) => br.click(a.id),
    browser_type: { run: (a) => br.type(a.id, a.text, a.enter), gate: (a) => br.sensitiveReason(a.id) },
    browser_scroll: (a) => br.scroll(a.direction),
    browser_back: () => br.back(),
    browser_read: (a) => br.read(a.page),
    run_shell: (a, ctx) => runShell(String(a.command || ''), { signal: ctx.signal }),
    ask_user: () => '',
    ...screen.tools,
    ...agentTools(helpers, { isHelper })
  };
  if (toolDefs.some((t) => t.function.name === 'diary_search')) tools.diary_search = (a) => diary.search(a.query);
  // vision: attach a browser screenshot to snapshots
  for (const n of ['browser_go', 'browser_click', 'browser_type', 'browser_scroll', 'browser_back']) {
    const e = tools[n];
    const run = typeof e === 'function' ? e : e.run;
    const wrapped = async (a, ctx) => {
      let r = await run(a, ctx);
      if (typeof r === 'string') r = { text: r };
      const v = store.getSettings().vision;
      if ((v === 'on' || v === true) && !r.error) r.image = await br.screenshot(1280);
      return r;
    };
    tools[n] = typeof e === 'function' ? wrapped : { ...e, run: wrapped };
  }
  // one mouse: the first screen tool of a run takes the global lock (FIFO) and keeps it until the run ends
  for (const n of SCREEN_TOOLS) {
    const run = tools[n];
    tools[n] = async (a, ctx) => { await holder.ensure(ctx.signal); return run(a, ctx); };
  }
  const a = new Agent({
    getSettings: isHelper ? () => ({ ...store.getSettings(), mode: store.getSettings().helperMode || 'hands-off' }) : () => store.getSettings(),
    tools,
    toolDefs,
    slot: limiter,
    onState: helper && helper.onState,
    onEnd: () => holder.release(),
    emit: (ev) => send('agent', { threadId: a.threadId, ...ev }),
    approve: (req, signal) => {
      const rid = a.threadId + ':' + req.id;
      const ev = { threadId: a.threadId, type: 'approval', rid, ...req };
      send('agent', ev);
      return waitFor(rid, signal, 'deny', { threadId: a.threadId, ev });
    },
    askUser: (question, signal) => {
      const id = 'ask_' + Date.now() + '_' + a.threadId;
      const ev = { threadId: a.threadId, type: 'ask', id, question };
      send('agent', ev);
      return waitFor(id, signal, '[stopped by user]', { threadId: a.threadId, ev });
    },
    onThreadChange: (t) => store.saveThread(t)
  });
  return a;
}

// Helper run: its own hidden browser (same partition), destroyed when the run ends.
function makeHelperAgent(h, { onState }) {
  const br = new Browser({ view: makeView(), session, window: win, onState: null });
  br.onState = browserState(br);
  helperBrowsers.set(h.threadId, br);
  if (openThreadId === h.threadId) showBrowser(br);
  const agent = createAgent({ helper: { id: h.id, onState }, br });
  return {
    agent,
    dispose: () => {
      if (cur() === br) showBrowser(browser);
      helperBrowsers.delete(h.threadId);
      br.destroy();
    }
  };
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

function buildAgent(hasDiary) {
  toolDefs = buildTools({ diary: hasDiary });
  screen = createScreen(() => store.getSettings(), process.resourcesPath, (look) => send('screen', look));
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
  agent = createAgent({ helper: null, br: browser });
}

function registerIpc() {
  const h = (name, fn) => ipcMain.handle(name, async (e, ...a) => fn(...a));
  h('settings:get', () => store.getSettings());
  h('settings:set', (patch) => store.saveSettings(patch));
  h('threads:list', () => store.listThreads());
  h('threads:new', () => { const t = store.newThread(); store.saveThread(t); openThreadId = t.id; showFor(t.id); return t; });
  h('threads:load', (id) => {
    const t = store.loadThread(id);
    if (!t) return t;
    openThreadId = id; showFor(id);
    const hp = helpers.byThread(id);
    t.running = hp ? helpers.isRunning(hp.id) : !!(agent.running && activeThread && activeThread.id === id);
    t.pendingCards = [...cards.values()].filter((c) => c.threadId === id).map((c) => c.ev);
    return t;
  });
  h('threads:delete', (id) => { if (!helpers.byThread(id)) store.deleteThread(id); return true; });
  h('threads:rename', (id, title) => { store.renameThread(id, title); return true; });
  h('agent:send', (threadId, text) => {
    const hp = helpers.byThread(threadId);
    if (hp) return helpers.steer(hp.id, text) ? { steered: true } : { error: "This is a helper's thread. Use Run now in the Agents list, or ask the primary agent." };
    if (agent.running) {
      if (activeThread && activeThread.id === threadId) { agent.steer(text); return { steered: true }; }
      return { error: 'Premonition is busy in another thread.' };
    }
    const t = store.loadThread(threadId) || store.newThread();
    if (!t.title || t.title === 'New thread') t.title = String(text).replace(/\s+/g, ' ').trim().slice(0, 48) || 'New thread';
    activeThread = t;
    agent.run(t, text).then(() => { send('threads:changed', {}); });
    return { started: true, title: t.title };
  });
  h('agent:stop', (threadId) => { const hp = threadId && helpers.byThread(threadId); if (hp) helpers.abort(hp.id); else agent.stop(); return true; });
  h('helpers:list', () => helpers.list());
  h('helpers:run', (id) => helpers.runNow(id));
  h('helpers:pause', (id) => { helpers.pause(id); return true; });
  h('helpers:delete', (id) => helpers.remove(id));
  h('respond', (id, value) => { const r = pending.get(id); if (r) { pending.delete(id); r(value); } return true; });
  h('browser:go', (url) => cur().go(url).then((r) => (typeof r === 'string' ? r : r.text)));
  h('browser:back', () => { const hst = cur().wc.navigationHistory; hst.canGoBack() && hst.goBack(); return true; });
  h('browser:forward', () => { const hst = cur().wc.navigationHistory; hst.canGoForward() && hst.goForward(); return true; });
  h('browser:reload', () => { cur().wc.reload(); return true; });
  h('browser:bounds', (b) => { lastBounds = b; cur().setBounds(b); return true; });
  h('browser:visible', (v) => { lastVisible = !!v; cur().setVisible(v); return true; });
  h('browser:state', () => cur().state());
  h('screen:check', async () => {
    if (!screen.findHelper()) return { error: 'screen control helper not installed' };
    return screen.check();
  });
  h('screen:ask', async () => {
    if (!screen.findHelper()) return { error: 'screen control helper not installed' };
    return screen.askPermissions();
  });
  h('screen:shot', async () => screen.screenshot(1280));
  h('open:external', (url) => { if (/^https?:/.test(url)) shell.openExternal(url); return true; });
  h('gateway:ping', async () => {
    const s = store.getSettings();
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 2500);
      const r = await fetch(String(s.gatewayUrl).replace(/\/+$/, '') + '/models', { signal: ctl.signal });
      clearTimeout(t);
      return { ok: r.ok };
    } catch (e) { return { ok: false }; }
  });
  h('info', () => ({ platform: process.platform, e2e: E2E, diary: !!(toolDefs && toolDefs.some((t) => t.function.name === 'diary_search')) }));
}

app.whenReady().then(async () => {
  store = new Store(app.getPath('userData'));
  diary = new Diary(() => store.getSettings());
  const hasDiary = E2E ? false : await diary.probe(); // decided once per run
  createWindow();
  browser = new Browser({ view: makeView(), session, window: win, onState: null });
  browser.onState = browserState(browser);
  buildAgent(hasDiary);
  registerIpc();
  helpers.start(); // runs anything that came due while the app was closed (once), then ticks every 30 s
  if (E2E) {
    win.webContents.once('did-finish-load', () => {
      require('./test/e2e.js').run({ app, win, store, browser, helpers, send }).catch((e) => { console.error('E2E crashed', e); app.exit(1); });
    });
  }
});

app.on('window-all-closed', () => { try { helpers && helpers.close(); } catch (e) { /* ignore */ } try { diary && diary.stop(); } catch (e) { /* ignore */ } app.quit(); });
