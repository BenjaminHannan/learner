'use strict';
const { powerMonitor, app, Tray, BrowserWindow, WebContentsView, ipcMain, session, shell, nativeTheme, Notification, Menu, globalShortcut, nativeImage, systemPreferences } = require('electron');
const path = require('path');
const os = require('os');
const fs = require('fs');

const E2E = process.argv.includes('--e2e');
const Platform = require('./renderer/platform');
const APP_NAME = 'Premonition';
app.setName(APP_NAME);
if (!E2E && !app.commandLine.hasSwitch('user-data-dir')) { // a test profile must start empty, never a copy of the real data
  // renamed from "Premonition Desk": bring the old settings/threads/memory/helpers along, once (the old folder stays as a backup)
  try { const r = require('./src/migrate').migrateUserData(app.getPath('appData'), app.getPath('userData')); if (r.migrated) console.log('userData copied from', r.from); } catch (e) { /* start fresh */ }
}
// main-process log: userData/logs/main.log (kept to the last ~1 MB), so "what went wrong" is not lost when the app closes
if (!E2E) {
  try {
    const dir = path.join(app.getPath('userData'), 'logs'); fs.mkdirSync(dir, { recursive: true });
    const f = path.join(dir, 'main.log');
    try { if (fs.statSync(f).size > 1048576) fs.renameSync(f, f + '.old'); } catch (e) { /* none yet */ }
    for (const lvl of ['log', 'warn', 'error']) {
      const orig = console[lvl].bind(console);
      console[lvl] = (...a) => { orig(...a); try { fs.appendFileSync(f, new Date().toISOString() + ' ' + lvl + ' ' + a.map((x) => (x && x.stack) || (typeof x === 'string' ? x : JSON.stringify(x))).join(' ') + '\n'); } catch (e) { /* ignore */ } };
    }
    process.on('uncaughtException', (e) => { console.error('uncaught', e); });
  } catch (e) { /* no log */ }
}
if (E2E) {
  app.setPath('userData', fs.mkdtempSync(path.join(os.tmpdir(), 'desk-e2e-')));
  app.commandLine.appendSwitch('no-sandbox');
  app.commandLine.appendSwitch('disable-gpu');
}
if (process.platform === 'linux') app.commandLine.appendSwitch('no-sandbox');
// Browser views sit underneath the opaque UI view while the panel is closed; without this switch Chromium treats a fully covered
// view as occluded and stops painting it (no capturePage thumbnails, no animation frames, stalled typing).
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows');

const { Store, applyPresetDefaults } = require('./src/store');
const { Agent, DANGER_LABELS } = require('./src/agent');
const { buildTools } = require('./src/prompt');
const { Browser } = require('./src/tools/browser');
const { webSearch } = require('./src/tools/web');
const { runShell } = require('./src/tools/shell');
const { Diary } = require('./src/tools/diary');
const { createScreen } = require('./src/tools/screen');
const Uses = require('./renderer/uses');
const { createMemory } = require('./src/memory');
const { createTracking } = require('./src/tracking');
const { Rhythm } = require('./src/rhythm');
const { Sleep, effectiveWindow, shouldAutoSleep, shouldAutoWake, windowKey, inWindow, wakeKey, pillLine, computeWakeAt, nightBudgetS, durationFromSetting, wakeLabel, shouldTimedWake } = require('./src/sleep');
const { idleSummary } = require('./src/pillidle');
const { Updater } = require('./src/updater');
const { Helpers, Limiter, ScreenLock, createRunner, addNotice, batchNotice, short } = require('./src/helpers');
const { agentTools } = require('./src/tools/agents');
const { Warmer } = require('./src/warm');
const { PillState } = require('./src/pillstate');
const { ensureCard } = require('./src/cards');
const { PillWindow } = require('./src/pillwin');
const perms = require('./src/perms');
const { WinSleep, sleepmlxParent } = require('./src/sleepwin');
const CK = require('./src/checkin');
const StartLog = require('./src/startlog');
const { Builtin, runtimeRoot } = require('./src/runtime/builtin');
const { SleepInstaller } = require('./src/runtime/sleepinstall');
const { Call } = require('./src/call');
const { Dictation } = require('./src/dictate');

let win = null;
let ui = null;   // the app UI (chat, panel chrome) is a WebContentsView filling the window; browser views sit below it unless a panel is open
let concealed = false;
let store = null;
let builtin = null;  // the built-in local model (Windows): download, llama-server, gateway (src/runtime)
let sleepInstaller = null;
let sleeper = null;  // bridge to the separate sleepmode app (src/sleep.js)
let tracking = null; // things Glim keeps track of (userData/tracking.md)
let rhythm = null;   // when Ben is usually up (userData/rhythm.json); auto-sleep fits its window to it
let memory = null;   // Ben's saved facts (userData/memory.md)
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
let updater = null; // in-app updates (src/updater.js)
let gwState = { state: 'down' };
let gwReadyAt = 0; // last time the gateway was seen ready (0 = not this session)
let e2eEnv = null;
const permsFake = E2E ? { accessibility: false, screenRecording: false } : null; // the e2e stands in for macOS
const dragIcons = new Map(); // bundle path -> 64 px nativeImage (the Finder icon of the app)
const timing = {}; // startup marks (checked by the e2e: the window must show before the deferred work starts)
const screenLock = new ScreenLock();
const browsers = new Map();   // thread id (chat threads and helper threads alike) -> {key, label, view, br, helper, onTop, used}  (created on first use)
const holds = new Map();      // browser key -> {p, release}: Ben took over, the agent's browser tools wait
const panel = { key: null, open: false, top: false, rect: null }; // what the renderer last told us about the in-window browser panel
const loginWaits = new Map(); // browser key -> finish(value): a sign-in hand-off is waiting for Ben
let openThreadId = null;  // thread the UI has open
const SCREEN_TOOLS = new Set(['screen_look', 'screen_click', 'screen_type', 'screen_key', 'open_app']);
const BROWSER_TOOLS = ['browser_go', 'browser_click', 'browser_type', 'browser_scroll', 'browser_back', 'browser_read'];
const pending = new Map(); // approval/ask id -> resolve
const cards = new Map();   // approval/ask id -> {threadId, ev}: replayed when Ben opens that thread later
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const onBattery = () => { try { return !!powerMonitor.isOnBatteryPower(); } catch (e) { return false; } };

const send = (channel, payload) => { if (ui && !ui.webContents.isDestroyed()) ui.webContents.send(channel, payload); };
const dark = () => nativeTheme.shouldUseDarkColors;

// ---- one state source for Glim (pill, top bar, dock badge) -------------------------------------
const pillState = new PillState({ onChange: () => { schedulePill(); } });
let pillTimer = null;
function schedulePill() { if (pillTimer) return; pillTimer = setTimeout(() => { pillTimer = null; updatePill(); }, 30); }
function chatInFront() { return !E2E && windowShown() && win.isFocused(); }
function updatePill() {
  const st = pillState.status();
  send('glim-state', st);
  try { if (process.platform === 'darwin' && app.dock) app.dock.setBadge(st === 'error' || st === 'waiting' ? '!' : ''); } catch (e) { /* ignore */ }
  if (pillWin) { const v = pillState.view(); if (!v.visible && process.platform === 'darwin') v.idle = idleInfo(); pillWin.update(v, chatInFront()); }
}
// hover card of the resting pill (Mac): rebuilt at most every 5 s, not on every 1 s tick
let idleCache = null;
function idleInfo() {
  const now = Date.now();
  if (idleCache && now - idleCache.at < 5000) return idleCache.v;
  const s = store.getSettings();
  const v = idleSummary({ now, helpers: helpers ? helpers.list() : [], autoSleep: s.autoSleep, sleepFrom: effectiveWindow(s, learnedNow(new Date())).from, asleep: sl.asleep, gateway: gwState.state });
  idleCache = { at: now, v };
  return v;
}
// the resting pill's card also refreshes when its 5 s cache runs out, so "in 12 min" and the assistant state stay current
const idleStale = () => process.platform === 'darwin' && pillWin && pillWin.view && !pillWin.view.visible && !(idleCache && Date.now() - idleCache.at < 5000);
setInterval(() => { if (pillState.tick() || (pillWin && pillWin.view && pillWin.view.visible) || idleStale()) updatePill(); }, 1000).unref();

// ---- sleep mode ---------------------------------------------------------------------------------------
// The sleepmode app stops the model servers and trains while Ben is away. Desk only starts/wakes it and mirrors its files.
// While asleep: runs are blocked, scheduled Glim runs wait (the missed-run catch-up fires them once after wake), the pill rests.
const sl = { asleep: false, starting: 0, waking: false, wakingAt: 0, startedAuto: false, wakeAt: null, checkingIn: false, sleepKey: null, lastKey: null, lastActive: Date.now(), bad: '' };
function sleepView() {
  const st = sleeper.status(); const av = sleeper.available();
  return { asleep: sl.asleep, starting: !!sl.starting, waking: sl.waking, line: sl.asleep ? pillLine(st) : '', hours: st.hours, lastQuiz: st.lastQuiz, demo: st.demo, since: st.since, available: av.ok, reason: av.reason, statusLine: sleeper.statusLine(), startedAuto: sl.startedAuto, wakeAt: sl.wakeAt, wakeLabel: sl.asleep ? wakeLabel(sl.wakeAt, Date.now()) : '', checkingIn: sl.checkingIn, nightTo: effectiveWindow(store.getSettings(), learnedNow(new Date())).to, learned: learnedNow(new Date()), error: sl.bad };
}
function pushSleep() {
  const v = sleepView();
  pillState.setSleep(sl.asleep && !sl.waking ? { line: v.line, detail: v.demo ? 'Demo run: nothing real is being trained' : 'Training on your chats; ' + v.wakeLabel } : null);
  send('sleep:state', v);
}
const sleepHold = () => (sl.asleep || sl.waking) && store.getSettings().sleepPauseGlims !== false;
function sleepNotice(text) { send('sleep:notice', { text }); }
// each launch and each new thread starts on the default pill (Auto unless Settings says otherwise); the top-bar pills change only the current one
function resetModelToDefault() {
  const s = store.getSettings(); const want = s[s.modelDefault] || s.modelAuto;
  if (want && s.model !== want) { store.saveSettings({ model: want }); }
}
// Ben's Macs have the assistant (qwen through serve.sh); any other Mac runs the built-in model like Windows does.
const SERVE_SH = path.join(os.homedir(), 'learner-ops', 'assistant', 'serve.sh');
const hasLocalAssistant = process.platform === 'darwin' && fs.existsSync(SERVE_SH);
const WATCHDOG_FILE = path.join(os.homedir(), 'learner-ops', 'assistant', 'WATCHDOG_STOPPED');
const PLATFORM_OPTS = { hasLocalAssistant };
function modelStartCommand(st) {
  const c = String(st.modelStartCmd || '').trim();
  if (c) return c;
  return hasLocalAssistant ? '"' + SERVE_SH + '" --autostart' : ''; // --autostart keeps serve.sh's memory check (--yes skips it)
}
// the night window learned from Ben's routine (null when "Fit sleep to my routine" is off or there is not enough data yet)
const learnedNow = (now) => { try { return rhythm && store.getSettings().sleepAdapt ? rhythm.learned(now) : null; } catch (e) { return null; } };
// the 60-second sample: Ben counts as active when the machine had input in the last 2 minutes or he used Desk
function sampleRhythm(now) {
  if (!rhythm) return;
  let idleS = Infinity; try { idleS = powerMonitor.getSystemIdleTime(); } catch (e) { /* not available: Desk's own use below */ }
  rhythm.record(now || new Date(), idleS < 120 || Date.now() - sl.lastActive < 120000);
}
const GOALS_ASK = 'Setup is done. One more thing, so I can help over the long run: what are your short-term and long-term goals? Anything counts, big or small: school, a skill, a project, a habit, money, health. If you are not sure yet, tell me what matters to you and I can help you brainstorm some. Then I will turn them into a plan with clear steps, and offer to check in on them for you.';
// rides (hidden) in front of the first answer to GOALS_ASK; the scroll shows only the person's words
const GOALS_NOTE = '[You just asked about their goals; this is the answer.] Save each goal to memory. Then make a short plan for each goal: '
  + '2 to 4 milestones and the first small step for this week. Ask at most one question if something important is unclear. If they have no goals yet, '
  + 'help them brainstorm a few first. Finally offer Sparks that would help (for example a weekly check-in or a reminder for the first step), and ask before creating any.\n\n';
// "go learn about X": learning mode. Hidden note in front of the message; the scroll shows only the person's words.
const LEARN_ASK = /^\s*(?:(?:please|ok|okay|hey)[ ,]+)?(?:go\s+|can you\s+|could you\s+)?(?:learn|study)\s+(?:about\s+|how to\s+|to\s+)?\S/i;
const LEARN_NOTE = '[Learning mode: the person asked you to go learn this. Treat it as building a skill that you keep.] '
  + 'First tell the person your plan in 2 to 4 short lines, and say a short line before each step. 1) Research it: search the web and read 3 to 5 good sources, not just the first hit. '
  + '2) Save what you learned as a skill with memory_save, topic "skill: <short name>": 5 to 8 short, true, useful notes, each with its source and, if it can go stale, an expiry. Never save a guess. '
  + '3) Test yourself: write 5 practice questions, answer them from your notes, check each answer against a source, and save one note with the score and the weak spots. '
  + '4) Study the weak spots once more, then tell the person in plain words what you can now do and what is still shaky. '
  + 'Your saved notes and this practice are what sleep trains into you overnight. Keep going until you finish all four steps.\n\n';
const isLearnAsk = (t, text) => !!t && !t.helper && LEARN_ASK.test(String(text || ''));
const isGoalsAnswer = (t) => !!t && !t.helper && (t.messages || []).length === 1 && t.messages[0].role === 'assistant' && t.messages[0].content === GOALS_ASK;
function startSleep(o) {
  o = o || {};
  if (sl.asleep || sl.waking) return { error: 'Glim is already asleep.' };
  if (sl.stopping && !o.assistantStopped) return { error: 'Turning off the chat model first. One moment.' };
  if ((agent && agent.running) || (helpers && helpers.active.size)) return { error: 'Glim is busy with a run right now. Sleep starts only when it is idle, because your chats come first.' };
  if (typeof o.pauseGlims === 'boolean') store.saveSettings({ sleepPauseGlims: o.pauseGlims });
  // how long: minutes | 'morning' | null (until woken). Auto-sleep: to the end of the night window.
  const now0 = new Date(), cfg = store.getSettings();
  const dur = o.auto ? 'morning' : ('minutes' in o ? o.minutes : durationFromSetting(cfg.sleepDuration));
  if (!o.auto && 'minutes' in o) store.saveSettings({ sleepDuration: o.minutes === null ? 'open' : String(o.minutes) });
  const until = computeWakeAt(now0, dur, cfg, learnedNow(now0));
  const r = sleeper.start({ budgetS: nightBudgetS(now0.getTime(), until), wakeAt: until });
  // the big chat model is on and holds the memory sleep needs: the sheet offers "Turn it off for now" (stopAssistant), which
  // stops it, sleeps, and turns it back on at wake
  if (r.assistantOn && hasLocalAssistant) {
    if (o.stopAssistant && !o.assistantStopped) {
      sl.stopping = true;
      return stopAssistantForSleep().then((e) => {
        const r2 = e ? { error: e } : startSleep({ ...o, stopAssistant: false, assistantStopped: true });
        if (r2.ok) sleepNotice('Turned off the chat model for now so Glim can sleep. It turns back on when Glim wakes.'); else restoreAssistant();
        return r2;
      }).finally(() => { sl.stopping = false; });
    }
    return { error: "Glim's chat model is on and using the memory sleep needs.", assistantOn: true };
  }
  if (r.needsRuntime) { send('sleep:needs-runtime', r.plan); return { needsRuntime: true, plan: r.plan, error: r.error }; }
  if (!r.ok) return { error: r.error };
  { const n = new Date(), w = effectiveWindow(store.getSettings(), learnedNow(n)); sl.sleepKey = inWindow(n, w.from, w.to) ? windowKey(n, w.from, w.to) : null; } // the night this sleep belongs to (if any)
  sleeper.mark(); sl.wakeAt = o.auto && !cfg.wakeAt ? null : until; sl.asleep = true; sl.starting = Date.now(); sl.startedAuto = !!o.auto; sl.bad = '';
  pushSleep(); updatePill();
  return { ok: true };
}
// stop.sh stops the model servers and gateway and clears ASSISTANT_RUNNING; resolves '' or a plain error
function stopAssistantForSleep() {
  return new Promise((resolve) => {
    require('child_process').execFile('/bin/bash', [path.join(path.dirname(SERVE_SH), 'stop.sh')], { timeout: 60000 }, (err) => {
      if (sleeper.assistantState() === 'on') return resolve("Could not turn off Glim's big chat model, so sleep could not start" + (err ? ' (' + String(err.message || err).slice(0, 120) + ')' : '') + '.');
      sl.assistantOff = true; resolve('');
    });
  });
}
// the chat model was turned off for this sleep: start it again (when Glim wakes, or when the sleep never started)
function restoreAssistant() {
  if (!sl.assistantOff) return;
  sl.assistantOff = false;
  const cmd = modelStartCommand(store.getSettings());
  if (cmd) try { require('child_process').spawn('/bin/zsh', ['-lc', cmd], { cwd: os.homedir(), detached: true, stdio: 'ignore' }).unref(); } catch (e) { /* the Offline button still works */ }
}
// plain words for the last line the sleep app printed before it stopped
function sleepWhy(line) {
  if (/assistant is running/i.test(line)) return "Glim's chat model was on and using the memory sleep needs. Press Sleep and choose Turn it off for now.";
  if (/Already sleeping/i.test(line)) return 'Sleep was already running. Press Wake, then Sleep.';
  if (/No module named|ModuleNotFoundError|ImportError/.test(line)) return 'The sleep app is missing a Python package (' + short(line, 100) + '). Check the Sleep Python path in Settings > Sleep.';
  if (/No space left|ENOSPC/i.test(line)) return 'The disk is full, so sleep could not start. Free a few GB and press Sleep again.';
  if (/memory|MemoryError|out of memory/i.test(line)) return 'There was not enough free memory to sleep. Close big apps and press Sleep again.';
  return line ? 'The sleep app stopped right away: ' + short(line, 160) : 'The sleep app stopped right away (see ' + sleeper.p.log + ').';
}
async function wakeNow() {
  if (!sl.asleep || sl.waking) return { ok: true };
  sl.waking = true; sl.wakingAt = Date.now();
  const now = new Date(), s = store.getSettings();
  const wk = wakeKey({ sleepKey: sl.sleepKey, now, settings: s, learned: learnedNow(now) }); // never a key from outside the window: waking at 08:00 must not block tonight
  if (wk) sl.lastKey = wk;
  pushSleep(); updatePill();
  const r = await sleeper.wake();
  if (!r.ok) { sl.waking = false; pushSleep(); sleepNotice('Could not wake Glim: ' + (r.error || 'unknown error')); return { error: r.error }; }
  return { ok: true };
}
// the sleep app has stopped: wait for the gateway to answer again, then show the morning summary
async function onWoke() {
  sl.waking = true; sl.starting = 0; pushSleep(); updatePill();
  restoreAssistant();
  if (warmer) { warmer.gatewayMoved(); for (let i = 0; i < 240 && warmer.state !== 'ready'; i++) await new Promise((r) => setTimeout(r, E2E ? 100 : 500)); }
  sl.asleep = false; sl.waking = false; sl.wakeAt = null; sl.lastActive = Date.now();
  const summary = sleeper.readSummary();
  pushSleep(); updatePill();
  send('sleep:woke', { summary, demo: sleeper.status().demo });
  notify('Glim is awake', summary ? short(summary.replace(/^#.*\n+/, ''), 140) : 'Welcome back.');
  if (helpers) helpers.tick(); // scheduled runs that came due while asleep fire once now
}
function onSleepPoll(st, events) {
  let alerts = 0; const lines = [];
  for (const e of events) {
    if (e.kind === 'checkin' && Number(e.notified) > 0) alerts += Number(e.notified);
    else if (e.kind === 'inbox') lines.push(e.line);
    else if (e.kind === 'checkin_needs_permission') {
      const what = /cal/i.test(e.scanner || '') ? 'Calendar' : /mail/i.test(e.scanner || '') ? 'Mail' : (e.scanner || 'Mail or Calendar');
      const text = 'Sleep check-ins need permission to read ' + what + '. Open System Settings > Privacy & Security > Automation and allow the app that runs sleep mode to control ' + what + ', then check in again.';
      sleepNotice(text); notify('Sleep check-in needs permission', 'Allow access to ' + what + ' in System Settings > Privacy & Security > Automation.');
    }
  }
  if (lines.length || alerts) {
    const body = lines.length ? lines.slice(0, 3).join('\n') : alerts + ' new thing' + (alerts > 1 ? 's' : '') + ' in your mail or calendar need you.';
    notify('Glim checked in while you sleep', body);
    pillState.flash(lines[0] || (alerts + ' check-in alert' + (alerts > 1 ? 's' : '')));
    sleepNotice('Check-in: ' + body.replace(/\n/g, ' · '));
  }
  const was = sl.asleep;
  let now = st.sleeping;
  if (sl.starting) {
    if (st.sleeping) sl.starting = 0;
    else if (sleeper.exit && (sleeper.exit.error || sleeper.exit.code)) { sl.starting = 0; sl.asleep = false; sl.bad = sleepWhy(sleeper.lastLogLine()); restoreAssistant(); sleepNotice(sl.bad); pushSleep(); updatePill(); return; }
    else if (Date.now() - sl.starting > 20000) { sl.starting = 0; sl.asleep = false; sl.bad = 'The sleep app did not start (see ' + sleeper.p.log + ').'; restoreAssistant(); sleepNotice(sl.bad); pushSleep(); updatePill(); return; }
    else now = true;
  }
  if (!was && now && !sl.waking) { sl.asleep = true; sl.startedAuto = false; pushSleep(); updatePill(); return; } // started from outside (Mac launcher)
  if ((was || sl.waking) && !now && !sl.wokeRunning) { sl.wokeRunning = true; onWoke().finally(() => { sl.wokeRunning = false; }); return; }
  if (sl.waking && st.sleeping && Date.now() - sl.wakingAt > 90000) { sl.waking = false; pushSleep(); sleepNotice('Glim is taking a long time to wake up. Look at ' + sleeper.p.log + '.'); return; }
  if (sl.asleep) pushSleep();
}
function autoSleepTick(now, over) {
  const s = store.getSettings(); now = now || new Date();
  const common = { settings: s, now, asleep: sl.asleep || sl.waking, startedAuto: sl.startedAuto, learned: learnedNow(now) };
  const w = shouldAutoWake({ ...common, asleep: sl.asleep && !sl.waking });
  if (w.wake) { wakeNow(); return { action: 'wake' }; }
  if (shouldTimedWake({ asleep: sl.asleep, waking: sl.waking, wakeAt: sl.wakeAt, nowMs: now.getTime() })) { wakeNow(); return { action: 'wake', reason: 'the chosen sleep time is up' }; }
  const d = shouldAutoSleep({ ...common, available: sleeper.available().ok && !(sleeper.needsRuntime && sleeper.needsRuntime()), idleMs: Date.now() - sl.lastActive, systemIdleMs: (() => { try { return powerMonitor.getSystemIdleTime() * 1000; } catch (e) { return null; } })(), runActive: !!(agent && agent.running) || !!(helpers && helpers.active.size), gatewayBusy: !!(warmer && warmer.warming), windowFocused: !!(win && !win.isDestroyed() && win.isFocused()), onBattery: onBattery(), lastKey: sl.lastKey, ...over });
  if (d.sleep) { sl.lastKey = d.key; const r = startSleep({ auto: true }); if (r.ok) notify('Glim went to sleep', 'It is past ' + effectiveWindow(s, common.learned).from + ' and you have been away. It wakes when you press Wake.'); return { action: 'sleep', result: r }; }
  return { action: 'none', reason: d.reason };
}

// ---- built-in local model + its sleep --------------------------------------------------------------------
// Windows and a Mac without Ben's assistant: the app runs LFM3 itself (src/runtime) and sleeps with the sleepmlx trainer
// (src/sleepwin.js; MPS on a Mac). Ben's Macs use the sleepmode app instead.
const builtinWanted = () => !!builtin && (Platform.presetFor(store.getSettings().gatewayUrl) || {}).id === 'builtin';
function setupBuiltin() {
  const root = runtimeRoot(app.getPath('userData')); // follows --user-data-dir; default is %APPDATA%\\Premonition
  builtin = new Builtin({ root, platform: process.platform, skipDiary: () => sl.checkingIn, bundledExe: path.join(process.resourcesPath || '', 'llama', 'llama-server.exe'), isWanted: builtinWanted, onState: (st) => { send('runtime:state', st); if (warmer && st.phase === 'ready') warmer.gatewayMoved(); } });
  sleepInstaller = new SleepInstaller({ root, platform: process.platform, llamaTag: () => { const s = builtin.installer.state(); const l = s.llama && (s.llama.vulkan || s.llama.cpu || s.llama.metal); return l && l.tag; }, onProgress: (p) => send('sleep:install-progress', p) });
  sleeper = new WinSleep({
    getSettings: () => store.getSettings(), root, installer: sleepInstaller, onBattery, tracked: () => tracking.list(),
    sleepmlxParent: sleepmlxParent(process.resourcesPath, path.join(__dirname, '..')),
    hooks: { pauseModel: () => builtin.pauseForSleep(), resumeModel: (lora) => builtin.resume(lora), servedUrl: () => (builtin.server && builtin.server.url ? builtin.server.url() : ''), checkin: runCheckin, onCheckin: (line) => { notify('Glim checked in while you sleep', line); pillState.flash(line); sleepNotice('Check-in: ' + line); } }
  });
}
// One hourly check-in (Windows sleep): due Glims run, then the check-in task goes through the normal agent in its own
// hidden thread ('ask' mode, so nothing that needs approval goes ahead). Returns {reply}. The caller owns the model server.
async function runCheckin({ signal, task }) {
  sl.checkingIn = true; pushSleep();
  try {
    if (helpers) {
      helpers.tick(true);
      while (helpers.active.size && !signal.aborted) await sleep(500);
      if (signal.aborted) { for (const id of [...helpers.active.keys()]) helpers.abort(id); return { aborted: true, reason: 'time or woken' }; }
    }
    return await checkinAgent('sleep-checkin', task, signal);
  } finally { sl.checkingIn = false; pushSleep(); }
}
async function checkinAgent(id, task, signal) {
  const h = { id, name: 'Check-in', threadId: id, mode: 'ask' };
  const r = await createRunner({ store, makeAgent: makeHelperAgent })(h, task, { signal, onState: () => {}, attach: () => {} });
  if (signal.aborted) return { aborted: true };
  if (r.error) return { error: String(r.error) };
  return { reply: r.report || '' };
}
// Awake check-in (every awakeCheckinMins): cheap checks first (tracking list, model server, disk, failed recurring Glims), then the
// same read-only mail/calendar triage through the model, only when the model server is up. Silent unless something is new.
// It never touches sl.lastActive (it is not Ben), and never runs while asleep, waking, mid-run, or with the chat in front.
const awake = { last: Date.now(), running: false, seen: new Set() };
function awakeDiskStats() { try { const f = fs.statfsSync(app.getPath('userData')); return { total: f.blocks * f.bsize, free: f.bavail * f.bsize }; } catch (e) { return null; } }
async function awakeCheckinTick(now, over) {
  const s = store.getSettings(); now = now || Date.now();
  if (awake.running) return { action: 'none', reason: 'running' };
  const sysIdle = (() => { try { return powerMonitor.getSystemIdleTime() * 1000; } catch (e) { return Infinity; } })();
  const d = CK.shouldAwakeCheckin({ now, last: awake.last, mins: s.awakeCheckinMins, asleep: sl.asleep || sl.waking || !!sl.starting, sleepBusy: sl.checkingIn, runActive: !!(agent && agent.running) || !!(helpers && helpers.active.size), focused: !!(win && !win.isDestroyed() && win.isFocused()), idleMs: Math.min(Date.now() - sl.lastActive, sysIdle), ...over });
  if (!d.due) return { action: 'none', reason: d.reason };
  awake.last = now; awake.running = true;
  try {
    const t = new Date(now); const pad = (n) => String(n).padStart(2, '0');
    const findings = CK.awakeFindings({ gateway: gwState.state, disk: awakeDiskStats(), helpers: helpers ? helpers.items : [], tracked: tracking.list(), today: t.getFullYear() + '-' + pad(t.getMonth() + 1) + '-' + pad(t.getDate()) });
    let line = '';
    if (gwState.state === 'ready' && !sl.asleep && !sl.starting) {
      const ac = new AbortController(); const cap = setTimeout(() => ac.abort(), CK.CHECKIN_CAP_MS); if (cap.unref) cap.unref();
      try {
        const res = await checkinAgent('awake-checkin', CK.awakeTask(s), ac.signal);
        if (!res.error && !res.aborted) { const p = CK.parseReply(res.reply); if (!p.nothing) line = p.line; }
      } catch (e) { /* a failed look is not news */ } finally { clearTimeout(cap); }
    }
    if (line) findings.push({ key: 'model:' + line.toLowerCase().replace(/\W+/g, ' ').trim(), line });
    const fresh = CK.freshFindings(awake.seen, findings);
    if (fresh.length) { notify('Glim checked in', fresh.slice(0, 3).map((f) => f.line).join('\n')); pillState.flash(fresh[0].line); updatePill(); }
    return { action: 'checkin', found: findings.length, fresh: fresh.length };
  } finally { awake.running = false; }
}
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
// One BrowserWindow. Its content is a stack of views: [idle browser views ... , the app UI, the open browser panel's view].
// The UI view fills the window and sits above every browser view that is not on show, so those pages stay attached at full
// panel size (they paint, take input and can be captured) while hidden behind the opaque UI. Opening the panel lifts that
// one view above the UI, over the panel's content rect (the renderer measures it and tells us).
function showWindow(focusComposer) {
  if (!win || win.isDestroyed()) createWindow();
  if (concealed) revealWindow();
  if (win.isMinimized()) win.restore();
  win.show(); win.focus();
  if (ui && !ui.webContents.isDestroyed()) ui.webContents.focus();
  if (focusComposer) send('focus-composer', true);
  updatePill();
}
// "Closing" the window keeps the app running. A hidden window would stop painting its pages (no thumbnails, no typing), so while
// browsers exist the window stays shown but see-through, click-through and unfocusable instead of hidden.
function hideWindow() {
  if (!win || win.isDestroyed()) return;
  const how = Platform.closeBehavior(process.platform, true, browsers.size > 0);
  if (how === 'tray') { ensureTray(); win.hide(); }
  else if (how === 'conceal') {
    concealed = true;
    win.setIgnoreMouseEvents(true);
    try { win.setFocusable(false); win.setOpacity(0); win.setHiddenInMissionControl(true); win.setHasShadow(false); } catch (e) { /* ignore */ }
  } else win.hide();
  updatePill();
}
// Windows: closing (with keep-running on) hides the window to a tray icon with Open / Quit.
let tray = null;
function ensureTray() {
  if (tray || !FEATURES.tray) return;
  try {
    const img = nativeImage.createFromPath(ICON).resize({ width: 16, height: 16 });
    tray = new Tray(img);
    tray.setToolTip(APP_NAME);
    tray.setContextMenu(Menu.buildFromTemplate([{ label: 'Open ' + APP_NAME, click: () => showWindow(true) }, { type: 'separator' }, { label: 'Quit', click: () => { quitting = true; app.quit(); } }]));
    tray.on('click', () => showWindow(true));
  } catch (e) { tray = null; }
}
function revealWindow() {
  concealed = false;
  try { win.setIgnoreMouseEvents(false); win.setFocusable(true); win.setOpacity(1); win.setHiddenInMissionControl(false); win.setHasShadow(true); } catch (e) { /* ignore */ }
}
const windowShown = () => !!win && !win.isDestroyed() && win.isVisible() && !concealed;
function toggleWindow() {
  if (windowShown() && win.isFocused()) hideWindow();
  else showWindow(true);
}

function fitUi() {
  if (!win || win.isDestroyed() || !ui) return;
  const [w, h] = win.getContentSize();
  ui.setBounds({ x: 0, y: 0, width: w, height: h });
}

function createWindow() {
  timing.created = Date.now();
  const bg = dark() ? '#17120f' : '#faf6f0';
  win = new BrowserWindow({
    width: 1000, height: 840, minWidth: 560, minHeight: 520,
    show: false, // shown once the UI has loaded: no white flash, no half-painted window
    backgroundColor: bg,
    title: APP_NAME,
    ...Platform.windowOptions(process.platform, ICON) // icon, title bar, auto-hide menu bar on Windows
  });
  ui = new WebContentsView({ webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: false, nodeIntegration: false } });
  // A transparent view background keeps Chromium from treating the browser views stacked beneath this UI as occluded (an
  // occluded page stops painting: no thumbnails, no rAF). The page itself paints an opaque background, so nothing shows through.
  ui.setBackgroundColor('#00000000');
  win.contentView.addChildView(ui);
  fitUi();
  // (on X11 the content size can lag one event behind the window size, so fit again shortly after)
  // macOS full screen hides the traffic lights, so the top bar drops the space it keeps for them
  win.on('enter-full-screen', () => send('fullscreen', true)); win.on('leave-full-screen', () => send('fullscreen', false));
  // a window that opens already in full screen fires neither event, so the page would keep the gap: tell it on every load
  ui.webContents.on('did-finish-load', () => send('fullscreen', win.isFullScreen()));
  // a reload mid-dictation leaves the page without its mic state: stop the helper at once
  ui.webContents.on('did-start-navigation', (e, url, inPlace, isMainFrame) => { if (isMainFrame) { try { stopDictate(true); } catch (err) { /* ignore */ } } });
  for (const ev of ['resize', 'resized', 'maximize', 'unmaximize', 'enter-full-screen', 'leave-full-screen', 'restore', 'show']) win.on(ev, () => { fitUi(); if (!panel.rect) applyPanel(); setTimeout(fitUi, 80); });
  ui.webContents.once('did-finish-load', () => {
    timing.readyToShow = Date.now();
    const hidden = !E2E && Platform.startedHidden(process.platform, process.argv, process.platform === 'darwin' ? app.getLoginItemSettings() : null);
    if (!hidden) { win.show(); ui.webContents.focus(); }
    setTimeout(() => afterFirstPaint().catch((e) => console.error('startup', e)), 0);
  });
  if (process.env.E2E_DEBUG) ui.webContents.on('console-message', (e, level, msg, line, src) => console.log('[renderer]', level, msg, src + ':' + line));
  ui.webContents.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  win.on('close', (e) => {
    if (quitting || !store || !store.getSettings().keepRunning) return;
    e.preventDefault(); hideWindow(); // keep running in the background (Cmd+Q really quits)
  });
  for (const ev of ['focus', 'blur', 'show', 'hide']) win.on(ev, () => {
    if (ev === 'focus' || ev === 'show') pillState.markSeen(openThreadId);
    if (ev === 'focus') sl.lastActive = Date.now();
    if (ev === 'focus') send('perms-recheck', true);
    if (ev === 'focus' && ui && !ui.webContents.isDestroyed()) {
      const top = [...browsers.values()].find((r) => r.onTop);
      if (!(top && top.view.webContents.isFocused())) ui.webContents.focus();
    }
    updatePill();
  });
  win.on('closed', () => { try { stopDictate(true); } catch (e) { /* ignore */ } win = null; ui = null; if (!quitting && store && !store.getSettings().keepRunning) app.quit(); });
  return win;
}

// ---- browsers: one per thread (helper threads too), created on first use ---------------------------------------
// Stacking: see "window" above. placeView puts a view on top of the UI only while the panel is open, showing that browser,
// and not suspended (Settings / a modal / the dragged divider need the UI on top).
function defaultRect() {
  const [w, h] = win && !win.isDestroyed() ? win.getContentSize() : [1000, 800];
  const pw = w < 1000 ? w : Math.max(420, Math.round(w * 0.58));
  return { x: w - pw, y: 150, width: pw, height: Math.max(100, h - 160) };
}
function placeView(rec) {
  if (!win || win.isDestroyed()) return;
  const r = panel.rect || defaultRect();
  const top = panel.open && panel.top && panel.key === rec.key;
  rec.view.setBounds(r);
  if (top !== rec.onTop) {
    rec.onTop = top;
    try { win.contentView.addChildView(rec.view, top ? undefined : 0); } catch (e) { /* ignore */ }
  }
}
function applyPanel() { for (const rec of browsers.values()) placeView(rec); }

function bstate(key) {
  const rec = browsers.get(key);
  if (!rec || rec.br.wc.isDestroyed()) return null;
  return { key, ...rec.br.state(), active: !!rec.active, login: loginWaits.has(key), held: holds.has(key), label: rec.label };
}
function pushBState(key) { const s = bstate(key); if (s) send('browser-state', s); }

function makeBrowser(key, label, opts) {
  let rec = browsers.get(key);
  if (rec) { rec.used = Date.now(); return rec; }
  const view = new WebContentsView({ webPreferences: { partition: 'persist:desk', contextIsolation: true, sandbox: true, nodeIntegration: false, backgroundThrottling: false } });
  const br = new Browser({ view, session, onState: () => pushBState(key) });
  br.shouldFocus = () => !(ui && !ui.webContents.isDestroyed() && ui.webContents.isFocused()) || (panel.open && panel.key === key);
  rec = { key, label, view, br, helper: !!(opts && opts.helper), onTop: false, active: false, used: Date.now() };
  browsers.set(key, rec);
  try { rec.br.wc.setBackgroundThrottling(false); } catch (e) { /* ignore */ }
  if (win && !win.isDestroyed()) { win.contentView.addChildView(view, 0); placeView(rec); }
  // keep a handful of idle thread browsers; the oldest idle one goes first
  const idle = [...browsers.values()].filter((r) => r.key !== key && !r.helper && !r.active && !loginWaits.has(r.key) && !(panel.open && panel.key === r.key) && !holds.has(r.key));
  if (idle.length > 4) { idle.sort((a, b) => a.used - b.used); dropBrowser(idle[0].key); }
  return rec;
}
function dropBrowser(key) {
  const rec = browsers.get(key);
  if (!rec) return;
  browsers.delete(key);
  const f = loginWaits.get(key); if (f) f('stopped');
  setHold(key, false);
  try { if (win && !win.isDestroyed()) win.contentView.removeChildView(rec.view); } catch (e) { /* ignore */ }
  rec.br.destroy();
  if (panel.key === key) send('browser-gone', { key });
}
function setHold(key, on) {
  if (on && !holds.has(key)) { let release; const p = new Promise((r) => { release = r; }); holds.set(key, { p, release }); }
  else if (!on && holds.has(key)) { holds.get(key).release(); holds.delete(key); }
  pushBState(key);
}
// Ben took over: the agent's browser tools wait here until he hands back (or Stop is pressed)
function gate(key, signal) {
  const h = holds.get(key);
  if (!h) return null;
  return Promise.race([h.p, new Promise((r) => { if (signal) { if (signal.aborted) r(); else signal.addEventListener('abort', () => r(), { once: true }); } })]);
}

// A sign-in hand-off: open the panel with the banner and wait (abortably) until Ben clicks Done or Not now.
function signInWait(key, threadId, signal) {
  return new Promise((resolve) => {
    const rec = browsers.get(key);
    if (!rec) return resolve('skip');
    const finish = (v) => {
      if (!loginWaits.has(key)) return;
      loginWaits.delete(key); pushBState(key);
      send('browser-hide', { key });
      send('agent', { threadId, type: 'resumed', key });
      resolve(v);
    };
    loginWaits.set(key, finish);
    if (signal) { if (signal.aborted) return finish('stopped'); signal.addEventListener('abort', () => finish('stopped'), { once: true }); }
    if (win && !win.isDestroyed() && !windowShown()) showWindow();
    pushBState(key);
    send('browser-show', { key, threadId, login: true });
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
function createAgent({ helper, rec, voice }) {
  const isHelper = !!helper;
  const isVoice = !!voice; // the call's own agent: it runs beside the main agent, so a call works while a task is running
  // one browser per thread: a helper's is made up front (its thread id), a chat thread's on its first browser tool
  const bk = () => (isHelper ? helper.threadId : a.threadId);
  const getBr = () => (isHelper ? rec : makeBrowser(bk(), isVoice ? 'Call' : activeThread && activeThread.title)).br;
  const pKey = isHelper ? helper.id : isVoice ? 'call' : 'main';
  const pName = isHelper ? helper.name : 'Glim';
  const holder = screenLock.holder();
  const agentRef = { withoutSlot: (fn, signal) => a.withoutSlot(fn, signal) };

  // live browser card: one per activity group; thumbnail refreshed after every action and every 1.5 s while the run is going
  const live = { item: null, timer: null, busy: false, thread: null };
  const cardEvent = (active) => {
    const it = live.item; if (!it) return;
    send('agent', { threadId: a.threadId, type: 'bcard', id: it.id, key: bk(), url: it.url, title: it.title, favicon: it.favicon, thumb: it.thumb, active, login: loginWaits.has(bk()) });
  };
  const capture = async () => {
    const it = live.item; if (!it || live.busy) return;
    live.busy = true;
    try {
      const cur = browsers.get(bk());
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
    const it = ensureCard(thread, 'browser', bk());
    if (live.item !== it) { live.item = it; cardEvent(true); }
    const cur = browsers.get(bk()); if (cur) { cur.active = true; cur.used = Date.now(); pushBState(bk()); }
    if (!live.timer) { live.timer = setInterval(capture, 1500); live.timer.unref && live.timer.unref(); }
  };
  const endCard = async () => {
    clearInterval(live.timer); live.timer = null;
    const it = live.item, thread = live.thread;
    if (!it) return;
    await capture();
    const cur = browsers.get(bk()); if (cur) { cur.active = false; pushBState(bk()); }
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
      // Never type into a password / payment field: Ben signs in himself in the browser panel while we wait.
      const why = await b.sensitiveReason(x.id);
      if (why) {
        const v = await ctx.waitForBen(() => signInWait(bk(), a.threadId, ctx.signal));
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
    ...agentTools(helpers, { isHelper, selfId: isHelper ? helper.id : null })
  };
  for (const n of BROWSER_TOOLS) {
    const run = tools[n];
    tools[n] = async (x, ctx) => {
      const g = gate(bk(), ctx.signal); // Ben took over: wait until he hands back
      if (g) { await g; if (ctx.signal && ctx.signal.aborted) return { text: '[stopped by user]', error: true }; }
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
    tools[n] = async (x, ctx) => {
      if (!holder.held()) await agentRef.withoutSlot(() => holder.ensure(ctx.signal), ctx.signal);
      const r = await run(x, ctx);
      const txt = typeof r === 'string' ? r : (r && r.text) || '';
      if (/^Error:.*(accessib|permission|not trusted|screen recording)/i.test(txt)) showPerms('a screen tool was refused');
      return r;
    };
  }
  const meta = () => ({ title: isHelper ? helper.name : isVoice ? 'Call' : (activeThread && activeThread.title) });
  const a = new Agent({
    memory, tracking,
    getSettings: isHelper ? () => ({ ...store.getSettings(), mode: helper.mode || store.getSettings().helperMode || 'hands-off' })
      : () => { const s = store.getSettings(); return isVoice ? { ...s, model: s.modelFast || s.model, verify: false } : s; }, // a voice turn uses the fast model and skips the extra self-check
    tools,
    toolDefs: () => toolDefs,
    slot: limiter,
    onState: helper && helper.onState,
    onEnd: () => { holder.release(); endCard(); sl.lastActive = Date.now(); },
    emit: (ev) => { send('agent', { threadId: a.threadId, ...ev }); pillState.onEvent(pKey, pName, a.threadId, ev, meta()); if (callTurn && !isHelper && a.threadId === callTurn.threadId) callTurn.onEvent(ev); },
    approve: (req, signal) => {
      const rid = a.threadId + ':' + req.id;
      const ev = { threadId: a.threadId, type: 'approval', rid, ...req };
      send('agent', ev); pillState.onEvent(pKey, pName, a.threadId, ev, meta()); if (callTurn && !isHelper && a.threadId === callTurn.threadId) callTurn.onEvent(ev);
      return waitFor(rid, signal, 'deny', { threadId: a.threadId, ev });
    },
    askUser: (question, signal) => {
      const id = 'ask_' + Date.now() + '_' + a.threadId;
      const ev = { threadId: a.threadId, type: 'ask', id, question };
      send('agent', ev); pillState.onEvent(pKey, pName, a.threadId, ev, meta()); if (callTurn && !isHelper && a.threadId === callTurn.threadId) callTurn.onEvent(ev);
      return waitFor(id, signal, '[stopped by user]', { threadId: a.threadId, ev });
    },
    // the model keeps repeating itself: a sign-in / passkey page goes to Ben, anything else is a question to Ben
    onStuck: async (stuck, signal) => {
      if (stuck.tool.startsWith('browser_') && browsers.get(bk()) && await browsers.get(bk()).br.looksLikeAuth()) {
        const b = browsers.get(bk()).br;
        const v = await signInWait(bk(), a.threadId, signal);
        return v === 'done' ? 'You were stuck on a sign-in page. Ben completed that step himself in the browser panel. Fresh snapshot:\n' + (await b.snapshot()) : v === 'stopped' ? '[stopped by user]' : 'Ben did not complete the sign-in. Stop trying that page and tell him what is blocked.';
      }
      if (isHelper) return 'You were stuck repeating ' + stuck.summary + '. Do not ask Ben. Try a different approach, or finish with a short report of what worked and what could not be done.'; // a Glim fixes it itself
      const answer = await a.o.askUser('I keep repeating "' + stuck.summary + '" and nothing changes. What should I do instead?', signal);
      return 'You were stuck repeating ' + stuck.summary + '. Ben says: ' + answer;
    },
    onThreadChange: (t) => store.saveThread(t)
  });
  return a;
}

// Helper run: its own browser (attached but covered, same partition), destroyed when the run ends.
function makeHelperAgent(h, { onState }) {
  const rec = makeBrowser(h.threadId, h.name + '’s browser', { helper: true });
  const agent = createAgent({ helper: { id: h.id, name: h.name, threadId: h.threadId, mode: h.mode, onState }, rec });
  return { agent, dispose: () => dropBrowser(h.threadId) };
}

// Glims finishing close together share one desktop notification (needs-you ones are urgent and skip this)
let finishBuf = [], finishTimer = null;
function queueFinish(x) {
  finishBuf.push(x);
  if (finishTimer) return;
  finishTimer = setTimeout(() => { const n = batchNotice(finishBuf); finishBuf = []; finishTimer = null; notify(n.title, n.body, n.threadId); }, 8000);
  if (finishTimer.unref) finishTimer.unref();
}

// A finished helper leaves a notice in the thread that started it (injected into the model's history on
// Ben's next message) and a macOS notification.
function postNotice(threadId, name, summary) {
  const live = activeThread && activeThread.id === threadId && agent.running;
  const t = live ? activeThread : (helpers && helpers.liveThread(threadId)) || store.loadThread(threadId); // a Glim's child reporting while that Glim still runs
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
  limiter = new Limiter(() => store.getSettings().maxParallel); // 0 = unlimited
  helpers = new Helpers({
    file: path.join(app.getPath('userData'), 'helpers.json'),
    store,
    hold: sleepHold,
    runner: createRunner({ store, makeAgent: makeHelperAgent }),
    onChange: () => send('helpers:changed', helpers.list()),
    onFinish: (h, summary, parent, flags) => {
      if (flags && flags.quiet) return send('helpers:changed', helpers.list()); // nothing new: no notice, no notification
      if (parent) postNotice(parent, h.name, summary);
      queueFinish({ name: h.name, summary, threadId: h.threadId, parent, failed: !!(flags && flags.failed) });
      send('threads:changed', {});
    },
    onNeedBen: (h) => notify("Spark '" + h.name + "' needs you", 'Open it to answer.', h.threadId)
  });
  agent = createAgent({ helper: null, rec: null });
}

// ---- Call Glim (speech to speech, Mac) ------------------------------------------------------------------
// One `deskhelper call` process hears and speaks; src/call.js cuts the streamed answer into sentences. Each spoken turn is a normal agent
// turn in one thread titled "Call" (kept as a chat). The instruction to answer briefly rides in the user message, NEVER in the system
// prompt (the cached prefix must stay byte-identical).
const VOICE_PREFIX = '[voice call] Answer out loud: one to three short spoken sentences, no lists, no markdown, no emoji. ';
// the date and time in plain words, so "what time is it" is answered from this turn and not guessed (rides in the user message, never the system prompt)
const nowWords = (d) => 'It is now ' + d.toLocaleString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) + '. ';
let call = null, callThread = null, calling = false, dictStarting = false;
let callTurn = null; // {threadId, onEvent(ev)} while a spoken turn runs on the call's own agent
let callAgent = null; // separate from the main agent, so a call works while a task runs
async function callAsk(text, { onDelta, signal }) {
  if (sl.asleep || sl.waking) throw new Error('Glim is asleep');
  if (!callAgent) callAgent = createAgent({ helper: null, rec: null, voice: true });
  for (let i = 0; i < 100 && callAgent.running && callTurn; i++) await sleep(30); // the turn we just interrupted is still unwinding
  if (callAgent.running) throw new Error('Glim is busy with another turn of this call');
  await Promise.race([toolsReady, sleep(3000)]);
  if (signal.aborted) return;
  if (callAgent.running) throw new Error('Glim is busy with another turn of this call');
  const t = callThread;
  callTurn = {
    threadId: t.id,
    onEvent: (ev) => {
      if (ev.type === 'text') onDelta(ev.delta);
      else if (ev.type === 'assistant_end') onDelta('\n');
      else if (ev.type === 'step_start' && call) call.toolStarted();
      else if (ev.type === 'approval' || ev.type === 'ask') onDelta('I need your OK in the chat for that.\n'); // a voice call cannot answer cards
    }
  };
  const stop = () => callAgent.stop();
  signal.addEventListener('abort', stop);
  send('agent', { threadId: t.id, type: 'user', text });
  try { await callAgent.run(t, VOICE_PREFIX + nowWords(new Date()) + text, { display: text }); } finally { callTurn = null; signal.removeEventListener('abort', stop); send('threads:changed', {}); }
}
// Local speech to text (src/stt.js): one LFM3-Audio server for the whole app, started on the first call / dictation.
let sttSrv = null;
const getStt = () => sttSrv || (sttSrv = new (require('./src/stt').Stt)({ resourcesPath: process.resourcesPath, devRoot: __dirname, voiceDir: voiceDir(), managedPython: () => { try { return sleepInstaller && sleepInstaller.pythonExe(); } catch (e) { return null; } } }));
const voiceDir = () => require('path').join(app.getPath('userData'), 'voice');
let voiceInstaller = null;
const getVoiceInstaller = () => voiceInstaller || (voiceInstaller = new (require('./src/runtime/voiceinstall').VoiceInstaller)({ dir: voiceDir(), onProgress: (p) => send('voice:install-progress', p) }));
async function sttUrl() {
  try { const u = await getStt().ensure(); getStt().warm(); return { url: u }; } catch (e) { return { error: String((e && e.message) || e), needsVoice: !!(e && e.needsVoice) }; }
}
async function startCall() {
  if (!FEATURES.call) return { error: 'Calling is coming to Windows soon.' };
  if (call || calling) return { error: 'You are already on a call.' };
  if (dictation || dictStarting) return { error: 'Stop dictation first, then call.' };
  if (sl.asleep || sl.waking) return { error: 'Glim is asleep. Wake it first, then call.' };
  const bin = screen.findHelper();
  if (!bin) return { error: 'Calling needs the Glim helper, which is not installed in this build.' };
  calling = true;
  const stt = await sttUrl();
  calling = false;
  if (stt.error) return { error: stt.error, needsVoice: stt.needsVoice };
  if (call || dictation) return { error: 'You are already on a call.' };
  callThread = store.newThread(); callThread.title = 'Call'; store.saveThread(callThread);
  const c = new Call({
    helper: bin,
    spawn: (cmd, args) => require('child_process').spawn(cmd, [...args, '--stt', stt.url], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true }),
    ask: callAsk,
    onEvent: (ev) => {
      send('call', ev);
      if (ev.type === 'state' && ev.state === 'ended') { call = null; pillState.setCall(null); if (!((callThread.items || []).length)) store.deleteThread(callThread.id); send('threads:changed', {}); } // a call nobody spoke in leaves no empty chat
    }
  });
  call = c; pillState.setCall(Date.now()); send('threads:changed', {});
  c.start();
  return { ok: true, threadId: callThread.id };
}

// ---- Dictation (speech to text in the chat box, Mac) -----------------------------------------------------------------
// One `deskhelper dictate` process; its partial / final text goes to the renderer on the 'dictate' channel. Never together with a call.
let dictation = null;
async function startDictate() {
  if (!FEATURES.dictate) return { error: 'Dictation is coming to Windows soon.' };
  if (call || calling) return { error: 'End the call before dictating.' };
  if (dictation || dictStarting) return { error: 'Dictation is already on.' };
  const bin = screen.findHelper();
  if (!bin) return { error: 'Dictation needs the Glim helper, which is not installed in this build.' };
  dictStarting = true;
  const stt = await sttUrl();
  dictStarting = false;
  if (stt.error) return { error: stt.error, needsVoice: stt.needsVoice };
  if (call || dictation) return { error: 'Dictation is already on.' };
  const d = new Dictation({
    helper: bin,
    spawn: (cmd, args) => require('child_process').spawn(cmd, [...args, '--stt', stt.url], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true }),
    onEvent: (ev) => { send('dictate', ev); if (ev.type === 'state' && ev.state === 'ended' && dictation === d) dictation = null; }
  });
  dictation = d;
  d.start();
  return { ok: true };
}
function stopDictate(hard) { const d = dictation; if (!d) return; if (hard) { dictation = null; d.close(); } else d.stop('stopped'); }

// ---- permissions card (drag the app into System Settings) ------------------------------------------------------
const FEATURES = Platform.features(process.platform, PLATFORM_OPTS);
const permsSupported = () => FEATURES.perms || E2E;
const appFile = () => perms.appBundlePath(app.getPath('exe'), process.execPath);
async function iconFor(file) {
  if (dragIcons.has(file)) return dragIcons.get(file);
  let img = null;
  // app.getFileIcon kills Electron 33 on macOS 26 (SIGTRAP in a thread-pool worker, any .app path),
  // which crashed the app whenever the permissions card opened. macOS uses the bundled icon instead.
  if (process.platform !== 'darwin') {
    try { img = await app.getFileIcon(file, { size: 'large' }); } catch (e) { /* use the bundled icon */ }
  }
  if (!img || img.isEmpty()) img = nativeImage.createFromPath(ICON);
  img = img.resize({ width: 64, height: 64 });
  dragIcons.set(file, img);
  return img;
}
async function permsStatus() {
  const mac = process.platform === 'darwin';
  let helperR = null; let electronR = {};
  if (permsFake) { helperR = { accessibility: permsFake.accessibility, screenRecording: permsFake.screenRecording }; electronR = { accessibility: permsFake.accessibility, screen: permsFake.screenRecording }; }
  else if (mac) {
    if (screen.findHelper()) helperR = await screen.check();
    try { electronR = { accessibility: systemPreferences.isTrustedAccessibilityClient(false), screen: systemPreferences.getMediaAccessStatus('screen') === 'granted' }; } catch (e) { /* not available */ }
  }
  const c = perms.combine(helperR, electronR);
  if (!c.missing && preDockBounds) undockFromSettings();
  const file = appFile();
  const helperFile = c.helperTile ? screen.findHelper() : null;
  const icon = await iconFor(file);
  return {
    supported: permsSupported(), missing: c.missing, appName: APP_NAME, appPath: file, icon: icon.toDataURL(),
    helperPath: helperFile, helperError: helperR && helperR.error ? helperR.error : null,
    rows: c.rows.map((r) => ({ ...r, ...perms.ROWS.find((x) => x.id === r.id), pane: undefined }))
  };
}

// Put Premonition on the left half of the screen and System Settings on the right, so the drag tile sits next to the list.
// Moving System Settings goes through AppleScript and may be refused; then it just opens where macOS puts it.
let preDockBounds = null;
function dockBesideSettings() {
  try {
    if (!win || win.isDestroyed()) return;
    const { screen: scr } = require('electron');
    const wa = scr.getDisplayMatching(win.getBounds()).workArea;
    if (!preDockBounds) preDockBounds = win.getBounds();
    const half = Math.floor(wa.width / 2);
    win.setBounds({ x: wa.x, y: wa.y, width: half, height: wa.height });
    win.show();
    const script = 'tell application "System Settings" to set bounds of window 1 to {' + [wa.x + half, wa.y + 25, wa.x + wa.width, wa.y + wa.height].join(', ') + '}';
    let tries = 0;
    // The first move asks Ben to let Premonition control System Settings (Automation). A short timeout killed osascript while
    // that prompt was up, so the prompt vanished and the move never happened: give him a minute, and stop if he said no (-1743).
    const go = () => {
      require('child_process').execFile('osascript', ['-e', script], { timeout: 60000 }, (err, out, stderr) => {
        if (err && !/-1743|not allowed/i.test(String(stderr || err.message)) && ++tries < 5) setTimeout(go, 700);
      });
    };
    setTimeout(go, 900);
  } catch (e) { /* layout is a convenience */ }
}
function undockFromSettings() { try { if (preDockBounds && win && !win.isDestroyed()) win.setBounds(preDockBounds); } catch (e) { /* ignore */ } preDockBounds = null; }
let lastPermsShow = 0;
function showPerms(reason) { if (!permsSupported() || Date.now() - lastPermsShow < 60000) return; lastPermsShow = Date.now(); showWindow(); send('perms-show', { reason }); }

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
  try { return globalShortcut.register(acc, () => { sl.lastActive = Date.now(); toggleWindow(); }) ? { ok: true } : { ok: false, error: 'That shortcut is taken by another app.' }; } catch (e) { return { ok: false, error: 'That is not a valid shortcut.' }; }
}
function setLoginItem(on) { try { app.setLoginItemSettings(Platform.loginItemOptions(process.platform, on)); } catch (e) { /* not supported here */ } }
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
  // renaming the model behind the pill that is selected keeps that pill selected
  for (const k of ['modelAuto', 'modelMain', 'modelFast']) if (ch(k) && prev.model === prev[k] && !('model' in patch)) { next.model = next[k]; store.saveSettings({ model: next.model }); out.model = next.model; }
  if (ch('gatewayUrl') && builtin) { if (builtinWanted()) builtin.start({ lora: sleeper.currentLora && sleeper.currentLora() }); else builtin.stop(); }
  if (ch('gatewayUrl') && warmer) warmer.gatewayMoved();
  else if ((ch('model') || ch('modelAuto') || ch('modelMain') || ch('modelFast')) && warmer) warmer.rewarm();
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
    onState: (state, info) => { if (state === 'ready') gwReadyAt = Date.now(); gwState = { state, ...info }; send('gateway', gwState); }
  });
  warmer.start();
  if (builtinWanted()) builtin.start({ lora: sleeper.currentLora && sleeper.currentLora() });
  if (FEATURES.sleep) {
    sleeper.watch(E2E ? 200 : 5000, onSleepPoll);
    if (!E2E) { sampleRhythm(); setInterval(() => { sampleRhythm(); autoSleepTick(); awakeCheckinTick().catch(() => {}); }, 60000).unref(); }
    { const st = sleeper.status(); if (st.sleeping) { sl.asleep = true; pushSleep(); } }
  }
  helpers.start(); // runs anything that came due while the app was closed (once), then ticks every 30 s
  pillWin = new PillWindow({ dark: dark() });
  pillWin.enabled = s.pill !== false;
  pillWin.ready.then(updatePill);
  const hk = registerHotkey(s.hotkey);
  if (!hk.ok) console.warn('hotkey:', hk.error);
  if (!E2E) setLoginItem(s.openAtLogin);
  // (while first-run setup is pending, the Permissions card is its last step instead)
  if (!E2E && permsSupported() && s.onboarded && !s.permsSeen) { store.saveSettings({ permsSeen: true }); lastPermsShow = Date.now(); send('perms-show', { reason: 'first launch' }); }
  toolsReady = Promise.resolve();
  if (E2E) {
    require('./test/e2e.js').run({
      app, win, ui, store, memory, tracking, sleeper, sl, autoSleepTick, helpers, send, browsers, panel, pillWin, pillState, warmer, applySettings, env: e2eEnv, pending,
      loginWaits, timing, getWin: () => win, showWindow, holds, permsFake, permsStatus
    }).catch((e) => { console.error('E2E crashed', e); app.exit(1); });
  }
}

function buildMenu() {
  const mac = process.platform === 'darwin';
  const openSettings = () => { showWindow(); send('open-settings', true); };
  const tpl = [
    ...(mac ? [{ label: app.name, submenu: [{ role: 'about' }, { type: 'separator' }, { label: 'Settings…', accelerator: 'CmdOrCtrl+,', click: openSettings }, { type: 'separator' }, { role: 'hide' }, { role: 'hideOthers' }, { role: 'unhide' }, { type: 'separator' }, { role: 'quit' }] }] : []),
    { label: 'File', submenu: [{ label: 'New thread', accelerator: 'CmdOrCtrl+N', click: () => { showWindow(); send('new-thread', true); } }, ...(FEATURES.sleepSoon ? [] : [{ label: 'Sleep…', click: () => { showWindow(); send('sleep-open', true); } }]), ...(mac ? [] : [{ label: 'Settings…', accelerator: 'CmdOrCtrl+,', click: openSettings }, { type: 'separator' }]), mac ? { role: 'close' } : { role: 'quit' }] },
    { role: 'editMenu' },
    { label: 'View', submenu: [{ role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' }, { role: 'togglefullscreen' }] },
    { role: 'windowMenu' }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(tpl));
}

function registerIpc() {
  const h = (name, fn) => ipcMain.handle(name, async (e, ...a) => fn(...a));
  h('update:status', () => updater ? updater.state : null);
  h('update:check', () => updater ? updater.check() : null);
  h('update:install', () => {
    if (!updater) return null;
    if ((agent && agent.running) || (helpers && helpers.active.size)) return { ...updater.state, error: 'Glim is busy with a run. Try again when it finishes.' };
    return updater.install();
  });
  h('settings:get', () => store.getSettings());
  h('settings:set', (patch) => applySettings(patch));
  h('threads:list', () => store.listThreads());
  h('threads:new', () => { resetModelToDefault(); const t = store.newThread(); store.saveThread(t); openThreadId = t.id; return t; });
  h('threads:load', (id) => {
    const t = store.loadThread(id);
    if (!t) return t;
    openThreadId = id; pillState.markSeen(id);
    const hp = helpers.byThread(id);
    t.running = hp ? helpers.isRunning(hp.id) : !!(agent.running && activeThread && activeThread.id === id);
    t.pendingCards = [...cards.values()].filter((c) => c.threadId === id).map((c) => c.ev);
    t.loginWaiting = loginWaits.has(id);
    return t;
  });
  h('threads:delete', (id) => { if (!helpers.byThread(id)) { store.deleteThread(id); dropBrowser(id); } return true; });
  h('threads:rename', (id, title) => { store.renameThread(id, title); return true; });
  h('agent:send', async (threadId, text) => {
    sl.lastActive = Date.now();
    if (sl.asleep || sl.waking) return { sleeping: true, error: sl.waking ? 'Glim is waking up. Try again in a moment.' : 'Glim is asleep. Wake it first, then I can take this.' };
    const hp = helpers.byThread(threadId);
    if (hp) return helpers.steer(hp.id, text) ? { steered: true } : { error: "This is a Glim's thread. Use Run now in the Glims list, or ask your main Glim." };
    if (agent.running) {
      if (activeThread && activeThread.id === threadId) { agent.steer(text); return { steered: true }; }
      return { error: 'Premonition is busy in another thread.' };
    }
    await Promise.race([toolsReady, sleep(3000)]); // the tool list must be final before the first request (prompt cache)
    if (agent.running) return { error: 'Premonition is busy in another thread.' };
    const t = store.loadThread(threadId) || store.newThread();
    if (!t.title || t.title === 'New thread') t.title = String(text).replace(/\s+/g, ' ').trim().slice(0, 48) || 'New thread';
    activeThread = t;
    const goals = isGoalsAnswer(t), learn = !goals && isLearnAsk(t, text);
    agent.run(t, goals ? GOALS_NOTE + text : learn ? LEARN_NOTE + text : text, goals || learn ? { display: text } : undefined).then((r) => {
      send('threads:changed', {});
      if (!r.stopped && !chatInFront() && !(pillWin && pillWin.enabled)) notify('Glim finished', t.title, t.id);
    }).catch((e) => send('agent', { threadId: t.id, type: 'error', message: String(e && e.message || e) }));
    return { started: true, title: t.title };
  });
  h('call:start', () => startCall());
  h('call:stop', () => { if (call) call.hangup(); return true; });
  h('call:mute', (m) => { if (call) call.setMuted(m); return true; });
  h('dictate:start', () => startDictate());
  h('dictate:stop', () => { stopDictate(false); return true; });
  h('agent:stop', (threadId) => { const hp = threadId && helpers.byThread(threadId); if (hp) helpers.abort(hp.id); else agent.stop(); return true; });
  // First-run setup: create the picked recurring Glims through the same Helpers.add that agent_start uses (no model call).
  h('onboard:create', (ids) => (Array.isArray(ids) ? ids : []).map((use) => {
    const t = Uses.templateFor(use);
    if (!t) return { use, ok: false, name: String(use), error: 'nothing to schedule for this use' };
    try { const v = helpers.add({ name: t.name, task: t.task, every: t.every, at: t.at, deferFirst: true, mode: 'ask' }); return { use, ok: true, name: v.name, id: v.id, schedule: v.schedule }; }
    catch (e) { return { use, ok: false, name: t.name, error: String(e && e.message || e) }; }
  }));
  // After first-run setup Glim asks about long-term goals: the question is written into the open chat as Glim's own first message
  h('onboard:goals', (id) => {
    const st = store.getSettings();
    if (st.goalsAsked) return { ok: false };
    const t = store.loadThread(id); if (!t || t.helper || (t.messages || []).length) return { ok: false };
    const text = GOALS_ASK;
    t.messages = [{ role: 'assistant', content: text }]; t.items = [...(t.items || []), { t: 'assistant', text }];
    store.saveThread(t); store.saveSettings({ goalsAsked: true });
    return { ok: true };
  });
  h('memory:list', () => memory.list());
  h('memory:read', () => memory.read());
  h('memory:write', (text) => memory.write(text));
  h('memory:reveal', () => { try { if (fs.existsSync(memory.file)) shell.showItemInFolder(memory.file); else shell.openPath(app.getPath('userData')); } catch (e) { /* ignore */ } return true; });
  h('memory:open', async () => { try { if (!fs.existsSync(memory.file)) memory.write(memory.read().text); const err = await shell.openPath(memory.file); return err ? { ok: false, error: err } : { ok: true }; } catch (e) { return { ok: false, error: String(e && e.message || e) }; } });
  h('memory:add', (o) => memory.add(o));
  h('memory:edit', (id, o) => memory.edit(id, o));
  h('memory:delete', (id) => memory.delete(id));
  h('tracking:list', () => tracking.list());
  h('tracking:done', (what) => tracking.done({ what }));
  h('tracking:remove', (what) => tracking.remove(what));
  h('helpers:list', () => helpers.list());
  h('helpers:run', (id) => ((sl.asleep || sl.waking) ? { error: 'Glim is asleep. Wake it first.' } : helpers.runNow(id)));
  h('sleep:state', () => sleepView());
  h('sleep:start', (o) => startSleep(o));
  h('runtime:state', () => (builtin ? builtin.state() : null));
  h('runtime:retry', () => (builtin ? builtin.retry() : null));
  h('sleep:install', async () => {
    try { await sleepInstaller.install(); } catch (e) { send('sleep:install-progress', { stage: 'error', label: String(e.message || e), pct: 0 }); return { error: String(e.message || e) }; }
    return startSleep({ auto: false });
  });
  h('voice:install', async () => {
    try { await getVoiceInstaller().install(); getStt().stop(); } catch (e) { send('voice:install-progress', { stage: 'error', label: String(e.message || e), pct: 0 }); return { error: String(e.message || e) }; }
    return { ok: true };
  });
  h('sleep:wake', () => wakeNow());
  h('sleep:summary', () => sleeper.readSummary());
  h('helpers:pause', (id) => { helpers.pause(id); return true; });
  h('helpers:delete', (id) => helpers.remove(id));
  h('respond', (id, value) => { const r = pending.get(id); if (r) { pending.delete(id); r(value); } return true; });
  // in-window browser panel: a card or a link was clicked. The thread's own browser is used (made now if it is gone, e.g.
  // after a restart or for a finished helper), then the renderer slides the panel open and reports where it sits.
  h('browser:open', async (key, url, navigate, threadId) => {
    const k = browsers.has(key) ? key : (threadId || key);
    const fresh = !browsers.has(k);
    const rec = makeBrowser(k, null);
    const cur = rec.br.wc.getURL();
    if (url && (navigate || fresh || !cur || cur === 'about:blank')) rec.br.go(url).catch(() => {});
    send('browser-show', { key: k, threadId: threadId || k });
    pushBState(k);
    return { key: k };
  });
  h('browser:exists', (key) => browsers.has(key));
  // the renderer measured the panel's content rect (window coordinates) and whether the browser should sit above the UI
  h('browser:layout', (p) => {
    p = p || {};
    panel.key = p.key || null; panel.open = !!p.open; panel.top = !!p.top;
    if (panel.lastTop !== panel.top) { panel.lastTop = panel.top; console.log('[browser:layout] top=' + panel.top + ' open=' + panel.open + ' key=' + (panel.key || '-')); } // a blank panel = top false while open
    if (p.rect) {
      const z = ui && !ui.webContents.isDestroyed() ? ui.webContents.getZoomFactor() : 1;
      const r = p.rect;
      panel.rect = { x: Math.round(r.x * z), y: Math.round(r.y * z), width: Math.max(1, Math.round(r.width * z)), height: Math.max(1, Math.round(r.height * z)) };
    }
    applyPanel();
    return true;
  });
  // panel chrome (address bar, back/forward, take over / hand back, sign-in Done, close)
  h('browser:cmd', async (key, cmd, arg) => {
    const rec = browsers.get(key);
    if (!rec) return null;
    const wc = rec.br.wc;
    const hst = wc.navigationHistory;
    switch (cmd) {
      case 'back': if (hst.canGoBack()) hst.goBack(); break;
      case 'forward': if (hst.canGoForward()) hst.goForward(); break;
      case 'reload': wc.reload(); break;
      case 'go': rec.br.go(arg).catch(() => {}); break;
      case 'takeover': setHold(key, true); break;
      case 'handback': case 'close': setHold(key, false); break;
      case 'done': { const f = loginWaits.get(key); if (f) f('done'); break; }
      case 'skip': { const f = loginWaits.get(key); if (f) f('skip'); break; }
      case 'focus': try { wc.focus(); } catch (e) { /* ignore */ } break;
      case 'state': return bstate(key);
      default: break;
    }
    return true;
  });
  h('perms:status', () => permsStatus());
  h('perms:open', async (id) => {
    const ok = await perms.openPane(shell, id);
    if (ok && process.platform === 'darwin' && !E2E) dockBesideSettings();
    return ok;
  });
  h('perms:reveal', (which) => { const f = which === 'helper' ? screen.findHelper() : appFile(); if (f) shell.showItemInFolder(f); return !!f; });
  ipcMain.on('perms:drag', perms.makeDragHandler({
    getSender: () => (ui && !ui.webContents.isDestroyed() ? ui.webContents : null),
    getFiles: () => ({ app: appFile(), helper: screen.findHelper() }),
    getIcon: (which) => dragIcons.get(which === 'helper' ? screen.findHelper() : appFile()) || nativeImage.createFromPath(ICON).resize({ width: 64, height: 64 })
  }));
  h('screen:check', async () => {
    if (!screen.findHelper()) return { error: 'screen control helper not installed' };
    return screen.check();
  });
  h('screen:ask', async () => {
    if (!screen.findHelper()) return { error: 'screen control helper not installed' };
    return screen.askPermissions();
  });
  h('system:open', (pane) => {
    const urls = { accessibility: 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility', screen: 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture', microphone: 'x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone' };
    if (urls[pane]) { try { shell.openExternal(urls[pane]); } catch (e) { /* not on a Mac */ } }
    return true;
  });
  // "Start setup over": setup counts as not done and the app restarts into it. Chats, memory and everything else stay.
  h('app:startOver', () => {
    store.saveSettings({ onboarded: false, permsSeen: false, onboardAt: '' });
    if (!E2E) { app.relaunch(); setTimeout(() => app.exit(0), 300); }
    return { ok: true };
  });
  h('open:external', (url) => { if (/^https?:/.test(url)) shell.openExternal(url); return true; });
  h('gateway:state', () => gwState);
  // Click on "Offline": start the model. Windows built-in: restart it. Otherwise the start command from Settings (Mac default:
  // the assistant's serve.sh), run detached; the warmer notices when the gateway answers.
  h('gateway:start', async () => {
    if (builtinWanted()) { builtin.retry(); return { ok: true, via: 'builtin' }; }
    const cmd = modelStartCommand(store.getSettings());
    if (!cmd) return { error: 'No start command is set. Add one in Settings > Model (for example the script that starts your model server).' };
    try {
      const sh = process.platform === 'win32' ? ['powershell.exe', ['-NoProfile', '-Command', cmd]] : ['/bin/zsh', ['-lc', cmd]];
      // the command's output goes to a log, so a start that dies at once can say why instead of doing nothing
      const logFile = path.join(app.getPath('userData'), 'model-start.log');
      let fd = 'ignore'; try { fd = fs.openSync(logFile, 'w'); } catch (e) { /* no log */ }
      const c = require('child_process').spawn(sh[0], sh[1], { cwd: os.homedir(), detached: true, stdio: ['ignore', fd, fd], windowsHide: true });
      const early = await new Promise((resolve) => { c.on('error', (e) => resolve({ code: -1, msg: String(e && e.message || e) })); c.on('exit', (code) => resolve({ code })); setTimeout(() => resolve(null), 6000); });
      c.unref(); if (typeof fd === 'number') try { fs.closeSync(fd); } catch (e) { /* ignore */ }
      // serve.sh --autostart declines (exit 0, within a second or two) when memory is short or another job runs
      if (early && early.code === 0) {
        let log = ''; try { log = fs.readFileSync(logFile, 'utf8'); } catch (e) { /* no log */ }
        const refusal = StartLog.parseRefusal(log);
        if (refusal) return { error: refusal.error, reason: refusal.reason };
      }
      if (early && early.code !== 0) {
        let tail = early.msg || ''; try { tail = tail || fs.readFileSync(logFile, 'utf8').trim().split('\n').slice(-3).join(' | '); } catch (e) { /* ignore */ }
        return { error: 'The start command stopped at once (exit ' + early.code + ')' + (tail ? ': ' + tail.slice(0, 300) : '') + '.' };
      }
      for (const ms of [5000, 15000, 30000, 60000, 90000]) setTimeout(() => { if (warmer) warmer.gatewayMoved(); }, ms).unref();
      return { ok: true, via: 'command' };
    } catch (e) { return { error: String(e && e.message || e) }; }
  });
  // Why the assistant is down: the watchdog leaves a marker when it stops it to save memory; without it, it was turned off.
  h('gateway:why', () => {
    if (!hasLocalAssistant || builtinWanted() || String(store.getSettings().modelStartCmd || '').trim()) return { kind: 'unknown' };
    try {
      // a marker from before the assistant last ran (or older than 12 h when unknown) is stale: it was stopped by hand since
      const m = fs.statSync(WATCHDOG_FILE).mtimeMs;
      if (gwReadyAt ? m < gwReadyAt : Date.now() - m > 12 * 3600e3) return { kind: 'off' };
      const w = StartLog.parseWatchdog(fs.readFileSync(WATCHDOG_FILE, 'utf8')); return { kind: 'memory', at: w.at, text: w.text }; } catch (e) { return { kind: 'off' }; }
  });
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
  h('info', () => ({ platform: process.platform, hasLocalAssistant, e2e: E2E, diary: toolDefs.some((t) => t.function.name === 'diary_search'), danger: DANGER_LABELS, version: app.getVersion() }));

  // status pill actions
  ipcMain.handle('pill:act', async (e, name, arg) => {
    if (name !== 'hover') sl.lastActive = Date.now();
    switch (name) {
      case 'hover': if (pillWin) pillWin.setInteractive(!!arg); break;
      case 'open': { showWindow(); if (arg && arg.threadId) send('open-thread', arg.threadId); if (arg && arg.key) pillState.dismiss(arg.key); break; }
      case 'stop': if (arg === 'main') agent.stop(); else helpers.abort(arg); break;
      case 'respond': { const r = pending.get(arg.rid); if (r) { pending.delete(arg.rid); r(arg.value); send('agent', { threadId: arg.threadId, type: 'resolved', rid: arg.rid, value: arg.value }); } break; }
      case 'openBrowser': { const pa = [...pillState.agents.values()].find((x) => x.key === arg); const key = pa && pa.threadId; if (key && browsers.has(key)) { showWindow(); send('browser-show', { key, threadId: key, login: loginWaits.has(key) }); } break; }
      case 'dismiss': pillState.dismiss(arg); break;
      case 'wake': wakeNow(); break;
      case 'hangup': if (call) call.hangup(); break;
      default: break;
    }
    return true;
  });
}

const gotLock = E2E || app.requestSingleInstanceLock();
if (!gotLock) app.quit();
app.on('second-instance', () => showWindow(true));
app.on('activate', () => { if (store) showWindow(); });
app.on('before-quit', () => { quitting = true; try { call && call.hangup(); } catch (e) { /* ignore */ } try { stopDictate(true); } catch (e) { /* ignore */ } try { sttSrv && sttSrv.stop(); } catch (e) { /* ignore */ } try { builtin && builtin.stop(); } catch (e) { /* ignore */ } });
app.on('will-quit', () => { try { globalShortcut.unregisterAll(); } catch (e) { /* ignore */ } });

app.whenReady().then(async () => {
  if (!gotLock) return;
  applyPresetDefaults(Platform.defaultPreset(process.platform, PLATFORM_OPTS));
  store = new Store(app.getPath('userData'));
  memory = createMemory(app.getPath('userData'));
  tracking = createTracking(app.getPath('userData'));
  rhythm = new Rhythm(path.join(app.getPath('userData'), 'rhythm.json'));
  if (FEATURES.builtin || process.env.PREMONITION_BUILTIN) setupBuiltin(); else sleeper = new Sleep({ getSettings: () => store.getSettings(), home: E2E ? path.join(app.getPath('userData'), 'sleepmode') : undefined });
  if (E2E) e2eEnv = await require('./test/e2e.js').prepare(store);
  resetModelToDefault();
  applyTheme(store.getSettings());
  diary = new Diary(() => store.getSettings());
  buildMenu();
  if (FEATURES.tray && Platform.startedHidden(process.platform, process.argv)) ensureTray();
  buildAgent();
  registerIpc();
  updater = new Updater({ version: app.getVersion(), platform: process.platform, arch: process.arch, execPath: process.execPath, pid: process.pid, packaged: app.isPackaged && !E2E,
    onState: (st) => send('update:state', st), quit: () => { quitting = true; app.quit(); } });
  if (app.isPackaged && !E2E && store.getSettings().autoUpdateCheck !== false) updater.startTimer(30000);
  createWindow(); // shown on ready-to-show; diary, helpers, warm-up, pill, hotkey start after that (afterFirstPaint)
});

app.on('window-all-closed', () => { try { helpers && helpers.close(); } catch (e) { /* ignore */ } try { diary && diary.stop(); } catch (e) { /* ignore */ } app.quit(); });
