'use strict';
const { app, BrowserWindow, WebContentsView, ipcMain, session, shell, nativeTheme } = require('electron');
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

let win = null;
let store = null;
let browser = null;
let agent = null;
let diary = null;
let screen = null;
let toolDefs = null;
let activeThread = null; // thread object being run
const pending = new Map(); // approval/ask id -> resolve

const send = (channel, payload) => { if (win && !win.isDestroyed()) win.webContents.send(channel, payload); };

function waitFor(id, signal, fallback) {
  return new Promise((resolve) => {
    pending.set(id, resolve);
    const onAbort = () => { pending.delete(id); resolve(fallback); };
    if (signal) { if (signal.aborted) return onAbort(); signal.addEventListener('abort', onAbort, { once: true }); }
  });
}

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

function buildAgent(hasDiary) {
  toolDefs = buildTools({ diary: hasDiary });
  screen = createScreen(() => store.getSettings(), process.resourcesPath, (look) => send('screen', look));
  const tools = {
    web_search: (a, ctx) => webSearch(a.query, { signal: ctx.signal }),
    browser_go: (a) => browser.go(a.url),
    browser_click: (a) => browser.click(a.id),
    browser_type: { run: (a) => browser.type(a.id, a.text, a.enter), gate: (a) => browser.sensitiveReason(a.id) },
    browser_scroll: (a) => browser.scroll(a.direction),
    browser_back: () => browser.back(),
    browser_read: (a) => browser.read(a.page),
    run_shell: (a, ctx) => runShell(String(a.command || ''), { signal: ctx.signal }),
    ask_user: () => '',
    ...screen.tools
  };
  if (hasDiary) tools.diary_search = (a) => diary.search(a.query);
  // vision: attach a browser screenshot to snapshots
  for (const n of ['browser_go', 'browser_click', 'browser_type', 'browser_scroll', 'browser_back']) {
    const e = tools[n];
    const run = typeof e === 'function' ? e : e.run;
    const wrapped = async (a, ctx) => {
      let r = await run(a, ctx);
      if (typeof r === 'string') r = { text: r };
      const v = store.getSettings().vision;
      if ((v === 'on' || v === true) && !r.error) r.image = await browser.screenshot(1280);
      return r;
    };
    tools[n] = typeof e === 'function' ? wrapped : { ...e, run: wrapped };
  }
  agent = new Agent({
    getSettings: () => store.getSettings(),
    tools,
    toolDefs,
    emit: (ev) => send('agent', { threadId: activeThread && activeThread.id, ...ev }),
    approve: (req, signal) => {
      send('agent', { threadId: activeThread && activeThread.id, type: 'approval', ...req });
      return waitFor(req.id, signal, 'deny');
    },
    askUser: (question, signal) => {
      const id = 'ask_' + Date.now();
      send('agent', { threadId: activeThread && activeThread.id, type: 'ask', id, question });
      return waitFor(id, signal, '[stopped by user]');
    },
    onThreadChange: (t) => store.saveThread(t)
  });
}

function registerIpc() {
  const h = (name, fn) => ipcMain.handle(name, async (e, ...a) => fn(...a));
  h('settings:get', () => store.getSettings());
  h('settings:set', (patch) => store.saveSettings(patch));
  h('threads:list', () => store.listThreads());
  h('threads:new', () => { const t = store.newThread(); store.saveThread(t); return t; });
  h('threads:load', (id) => store.loadThread(id));
  h('threads:delete', (id) => { store.deleteThread(id); return true; });
  h('threads:rename', (id, title) => { store.renameThread(id, title); return true; });
  h('agent:send', (threadId, text) => {
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
  h('agent:stop', () => { agent.stop(); return true; });
  h('respond', (id, value) => { const r = pending.get(id); if (r) { pending.delete(id); r(value); } return true; });
  h('browser:go', (url) => browser.go(url).then((r) => (typeof r === 'string' ? r : r.text)));
  h('browser:back', () => { const hst = browser.wc.navigationHistory; hst.canGoBack() && hst.goBack(); return true; });
  h('browser:forward', () => { const hst = browser.wc.navigationHistory; hst.canGoForward() && hst.goForward(); return true; });
  h('browser:reload', () => { browser.wc.reload(); return true; });
  h('browser:bounds', (b) => { browser.setBounds(b); return true; });
  h('browser:visible', (v) => { browser.setVisible(v); return true; });
  h('browser:state', () => browser.state());
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
  browser = new Browser({ WebContentsView, session, window: win, onState: (s) => send('browser-state', s) });
  buildAgent(hasDiary);
  registerIpc();
  if (E2E) {
    win.webContents.once('did-finish-load', () => {
      require('./test/e2e.js').run({ app, win, store, browser, send }).catch((e) => { console.error('E2E crashed', e); app.exit(1); });
    });
  }
});

app.on('window-all-closed', () => { try { diary && diary.stop(); } catch (e) { /* ignore */ } app.quit(); });
