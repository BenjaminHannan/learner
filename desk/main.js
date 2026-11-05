'use strict';
const { powerMonitor, app, Tray, BrowserWindow, WebContentsView, ipcMain, session, net, shell, nativeTheme, Notification, Menu, globalShortcut, nativeImage, systemPreferences } = require('electron');
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
} else if (!E2E) require('./src/llm').setTestProfile(true);   // its chats must not reach the diary the sleep learns from
// main-process log: userData/logs/main.log (kept to the last ~1 MB), so "what went wrong" is not lost when the app closes
if (!E2E) {
  try {
    const dir = path.join(app.getPath('userData'), 'logs'); fs.mkdirSync(dir, { recursive: true });
    const f = path.join(dir, 'main.log');
    const trim = () => { try { if (fs.statSync(f).size > 1048576) fs.renameSync(f, f + '.old'); } catch (e) { /* none yet */ } };
    trim();
    let writes = 0;   // the app runs for weeks (login item, tray): check the size every 200 lines, not only at launch
    for (const lvl of ['log', 'warn', 'error']) {
      const orig = console[lvl].bind(console);
      console[lvl] = (...a) => { if (++writes % 200 === 0) trim(); let line = a.map((x) => (x && x.stack) || (typeof x === 'string' ? x : JSON.stringify(x))).join(' '); if (require('./src/logins').holdsSecret(line)) { line = '[log line dropped: it held a saved password]'; a = [line]; } orig(...a); try { fs.appendFileSync(f, new Date().toISOString() + ' ' + lvl + ' ' + line + '\n'); } catch (e) { /* ignore */ } };   // LOGIN1: no saved password in the log
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
const StudyGate = require('./src/studygate');   // Learn study Motes: drift guard + truth check (Nov 4)
const { Agent, DANGER_LABELS, noteOldGap, rollupGapStep } = require('./src/agent');
const { buildTools } = require('./src/prompt');
const { Browser } = require('./src/tools/browser');
const { webSearch } = require('./src/tools/web');
const { UrlGuard, hostOf } = require('./src/urlguard');
const { runShell } = require('./src/tools/shell');
const { Diary } = require('./src/tools/diary');
const Feedback = require('./src/feedback');
const { createScreen } = require('./src/tools/screen');
const Uses = require('./renderer/uses');
const { createMemory } = require('./src/memory');
const { createTracking } = require('./src/tracking');
const DashSrc = require('./src/dashboard-sources');
const DashOver = require('./src/dashboard-overrides');
const { Rhythm } = require('./src/rhythm');
const { NightStart, NIGHT_ARG } = require('./src/nightstart');
const { Sleep, effectiveWindow, shouldAutoSleep, shouldAutoWake, windowKey, inWindow, wakeKey, pillLine, computeWakeAt, nightBudgetS, durationFromSetting, wakeLabel, shouldTimedWake } = require('./src/sleep');
const { idleSummary } = require('./src/pillidle');
const { Updater } = require('./src/updater');
const { Helpers, Limiter, ScreenLock, createRunner, addNotice, batchNotice, short } = require('./src/helpers');
const { agentTools } = require('./src/tools/agents');
const { learnFlow } = require('./src/learn');
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
let limiter = null, helperLimiter = null;
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
const BROWSER_TOOLS = ['browser_go', 'browser_click', 'browser_type', 'browser_sign_in', 'browser_scroll', 'browser_back', 'browser_read'];
const pending = new Map(); // approval/ask id -> resolve
const cards = new Map();   // approval/ask id -> {threadId, ev}: replayed when Ben opens that thread later
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const onBattery = () => { try { return !!powerMonitor.isOnBatteryPower(); } catch (e) { return false; } };

const send = (channel, payload) => { if (ui && !ui.webContents.isDestroyed()) ui.webContents.send(channel, payload); };
const dark = () => nativeTheme.shouldUseDarkColors;

// ---- one state source for Glim (pill, top bar, dock badge) -------------------------------------
const pillState = new PillState({ onChange: () => { schedulePill(); }, showHelpers: () => !!store.getSettings().showSparks });
let pillTimer = null;
function schedulePill() { if (pillTimer) return; pillTimer = setTimeout(() => { pillTimer = null; updatePill(); }, 30); }
function chatInFront() { return !E2E && windowShown() && win.isFocused(); }
function updatePill() {
  const st = pillState.status();
  send('glim-state', st);
  try { if (process.platform === 'darwin' && app.dock) app.dock.setBadge(st === 'error' || st === 'waiting' ? '!' : ''); } catch (e) { /* ignore */ }
  if (pillWin) { const v = pillState.view(); if (!v.visible && process.platform === 'darwin') v.idle = idleInfo(); try { v.ear = aoEar(); } catch (e) { v.ear = null; } pillWin.update(v, chatInFront()); }
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
let lastEar = '';
setInterval(() => {
  try { aoVoice.pump(); aoVoice.sweep(); } catch (e) { /* the next second tries again */ }
  if (aoSenses && aoSenses.anyEnabled() && aoSenses.enabled('windows') && !sl.asleep) { const f = aoStuck.front(); if (f.app) { try { aoWatchSecond(getGuesser().observe('app', SpeakMod.categorize(f.app, f.title))); } catch (e) { /* next second */ } } }
  try { aoPool.tick(); } catch (e) { /* next second */ }
  try { aoDeferredTick(); } catch (e) { /* next second */ }   // imagining ahead: a say that chose to wait is re-checked when due
  try { if (aoTruthCtl && aoTruthGate().budget <= 0) aoStopChecks(); else if ((aoSenses && aoSenses.anyEnabled()) || learningNow()) aoTruthTick(); } catch (e) { /* next second */ }
  try { if (aoQuizCtl && !aoQuizGate()) aoStopQuiz(); else if (learnBtn && learnBtn.cur) aoQuizTick(); } catch (e) { /* next second */ }
  // the memory gauge is read every 10 s while always-on or a Learn study is on (the Mote gate skips it while Ben is busy)
  if (((aoSenses && aoSenses.anyEnabled()) || (learnBtn && learnBtn.cur)) && Date.now() % 10000 < 1000) { try { aoGaugeNow = aoGauge.read(); } catch (e) { /* next time */ } }
  if (((aoSenses && aoSenses.anyEnabled()) || (learnBtn && learnBtn.cur)) && aoGaugeNow.level === 'red' && helpers && helpers.active.size) { aoGaugeNow = aoGauge.read(); if (aoGaugeNow.level === 'red') helpers.pauseForSleep('Paused: the Mac is short on memory'); }
  if (aoSenses && aoSenses.anyEnabled() && Date.now() % 60000 < 1000) { saveGuesser(); try { aoJudgeMinute(); } catch (e) { /* next minute */ } try { if (aoNight()) aoNightly(); } catch (e) { /* next minute */ } try { aoUrgeTick(); } catch (e) { console.log('[alwayson] urges', e); } }
  let earCh = false; try { const e = JSON.stringify(aoEar()); earCh = e !== lastEar; lastEar = e; } catch (e) { /* ignore */ }
  if (pillState.tick() || (pillWin && pillWin.view && pillWin.view.visible) || idleStale() || earCh) updatePill();
}, 1000).unref();

// ---- sleep mode ---------------------------------------------------------------------------------------
// The sleepmode app stops the model servers and trains while Ben is away. Desk only starts/wakes it and mirrors its files.
// While asleep: runs are blocked, scheduled Glim runs wait (the missed-run catch-up fires them once after wake), the pill rests.
const sl = { asleep: false, starting: 0, waking: false, wakingAt: 0, startedAuto: false, wakeAt: null, checkingIn: false, sleepKey: null, lastKey: null, lastActive: Date.now(), bad: '' };
const SleepSession = require('./src/sleepsession');
const sleepSessionFile = () => path.join(app.getPath('userData'), 'sleep-session.json');
function persistSleepSession(phase) {
  try {
    SleepSession.save(sleepSessionFile(), { startedAt: sl.startedAt || Date.now(), wakeAt: sl.wakeAt,
      startedAuto: sl.startedAuto, sleepKey: sl.sleepKey, assistantOff: !!sl.assistantOff, phase });
    return true;
  } catch (e) { console.error('[sleep] could not save session:', e.message || e); return false; }
}
function clearSleepSession() { try { SleepSession.clear(sleepSessionFile()); } catch (e) { console.error('[sleep] could not clear session:', e.message || e); } }
function abandonSleepAttempt() { if (sl.assistantOff) persistSleepSession('attention'); else clearSleepSession(); }
function sleepView() {
  const st = sleeper.status(); const av = sleeper.available();
  return { asleep: sl.asleep, starting: !!sl.starting, waking: sl.waking, modelReady: !!warmer && warmer.state === 'ready', line: sl.asleep ? pillLine(st) : '', live: sl.asleep ? sleeper.liveNow(st) : null, hours: st.hours, lastQuiz: st.lastQuiz, demo: st.demo, since: st.since, available: av.ok, reason: av.reason, statusLine: sleeper.statusLine(), startedAuto: sl.startedAuto, wakeAt: sl.wakeAt, wakeLabel: sl.asleep ? wakeLabel(sl.wakeAt, Date.now()) : '', checkingIn: sl.checkingIn, nightTo: effectiveWindow(store.getSettings(), learnedNow(new Date())).to, learned: learnedNow(new Date()), error: sl.bad };
}
function pushSleep() {
  const v = sleepView();
  pillState.setSleep(sl.asleep && !sl.waking ? { line: v.line, detail: v.demo ? 'Demo run: nothing real is being trained' : (v.live ? v.live.now : 'Learning from your chats') + '; ' + v.wakeLabel } : null);
  send('sleep:state', v);
}
// Ben Oct 28: "It should also be aware of its ability to sleep". One line in the first turn of a chat: what sleep does, when, and the last sleep.
function sleepInfo() {
  if (!sleeper || !sleeper.available().ok || (sleeper.needsRuntime && sleeper.needsRuntime())) return '';
  const s = store.getSettings(), w = effectiveWindow(s, learnedNow(new Date()));
  return '[You can sleep: at night (' + w.from + '-' + w.to + ') your local model trains on the day\'s chats and saved notes and skills, so you remember them and get better. Feedback is how you improve: thumbs up/down, corrections and reviews of your Motes\' ideas all feed sleep, so take it as a lesson, never as criticism, and say what you will do differently. '
    + (s.autoSleep ? 'It starts by itself when the person is away then, or ' : 'It starts ') + 'when they press Sleep; while asleep you cannot chat. When this chat began: ' + sleeper.statusLine() + ']';
}
// Ben's chat first (Oct 28): while the main Glim is running, or ran in the last 2 min, Glims (helpers) wait before each model call
// and due ones do not start, so Ben's chat keeps the one local model and its prompt cache. Setting benFirst: false turns it off.
const BEN_FIRST_MS = 120000;
const HELPER_COMPACT = 10000;
let benLastTurn = 0;
const benBusy = () => store.getSettings().benFirst !== false && (!!(agent && agent.running) || !!(call && callAgent && callAgent.running) || Date.now() - benLastTurn < BEN_FIRST_MS);
const sleepHold = () => ((sl.asleep || sl.waking) && store.getSettings().sleepPauseGlims !== false) || !!sl.restoreFailed;
function sleepNotice(text) { send('sleep:notice', { text }); }
// each launch and each new thread starts on the default pill (Auto unless Settings says otherwise); the top-bar pills change only the current one
function resetModelToDefault() {
  const s = store.getSettings(); const want = s[s.modelDefault] || s.modelAuto;
  if (want && s.model !== want) { store.saveSettings({ model: want }); }
}
// Ben's Macs use the managed assistant service; other Macs run the built-in model.
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
// After setup Glim opens with a short hello + one small question, then at most 2 more, one per message (src/opener.js).
// A hidden note rides only on a reply that plausibly answers the question just asked; the scroll shows only the person's words.
const Opener = require('./src/opener');
const GOALS_ASK = Opener.OPENER;
// "go learn about X": learning mode. Hidden note in front of the message; the scroll shows only the person's words.
const LEARN_ASK = /^\s*(?:(?:please|ok|okay|hey)[ ,]+)?(?:go\s+|can you\s+|could you\s+)?(?:learn|study)\s+(?:about\s+|how to\s+|to\s+)?\S/i;
const LEARN_NOTE = '[Learning mode: the person asked you to go learn this. Treat it as building a skill that you keep.] '
  + 'First tell the person your plan in 2 to 4 short lines, and say a short line before each step. 1) Research it: search the web and read 3 to 5 good sources, not just the first hit. '
  + '2) Save what you learned as a skill with memory_save, topic "skill: <short name>": 5 to 8 short, true, useful notes, each with its source and, if it can go stale, an expiry. Also save each concrete fact you find as its own fact card (topic "card", "Subject => relation => Object"). Never save a guess. '
  + '3) Test yourself: write 5 practice questions, answer them from your notes, check each answer against a source, and save one note with the score and the weak spots. '
  + '4) Study the weak spots once more, then tell the person in plain words what you can now do and what is still shaky. '
  + 'Saved notes and practice may be eligible for training during sleep; do not claim training happened without evidence. Keep going until you finish all four steps.\n\n';
const LEARN_ANGLES = ['core concepts and how they connect', 'worked examples and practice problems with checkable answers', 'common mistakes, edge cases and gotchas', 'advanced techniques and shortcuts', 'real-world use and tools', 'history, vocabulary and key facts'];
const LEARN_CITATION = 'For each memory_save, set source_read_id to the Source read ID from browser_read and source_quote to an exact 12–600 character excerpt visible in that read. Set expires to YYYY-MM-DD when relevant. Keep URLs out of fact text. ';
const LEARN_MOTE = (topic, angle) => 'Go learn: ' + topic + (angle ? ', focusing on ' + angle : '') + '. Each run, dig into something new and never repeat a note you already saved. Work quietly and do not report to Ben. 1) Research it: search the web and read 3 to 5 good sources. '
  + LEARN_CITATION + '2) Save what you learn with memory_save, topic "skill: <short name>": 5 to 8 short, true notes, each with its source and an expiry if it can go stale. Also save each concrete fact as its own card (topic "card", "Subject => relation => Object"). Never save a guess. '
  + '3) Test yourself: write 5 practice questions, answer them from your notes, check against a source, and save one note with the score and weak spots. 4) Study the weak spots once more. Saved notes may be eligible for training during sleep; do not claim training happened without evidence. Finish with exactly: NO_UPDATE\n';
// Learn mode: "go learn X" sends Motes off to study quietly (different angles, repeating, stopping at the end time); sleep trains their cards in.
function startLearn(topic, count, hours) {
  topic = String(topic || '').trim().slice(0, 200);
  if (!topic) return { error: 'no topic' };
  if (sl.asleep || sl.waking) return { error: 'Glim is asleep.' };
  const n = Math.max(1, Math.min(12, parseInt(count, 10) || 3)), hrs = Math.max(0, Number(hours) || 0);
  const until = hrs ? Date.now() + hrs * 3600000 : 0, made = [], ids = [];
  let error = null;
  for (let i = 0; i < n; i++) {
    const angle = LEARN_ANGLES[i % LEARN_ANGLES.length] + (i >= LEARN_ANGLES.length ? ' (part ' + (Math.floor(i / LEARN_ANGLES.length) + 1) + ')' : '');
    try { const v = helpers.add({ name: ('Learn ' + (i + 1) + ': ' + topic).slice(0, 40), task: LEARN_MOTE(topic, n > 1 ? angle : ''), every: hrs === 0 || hrs > 1 ? '45m' : '20m', until, allowSimilar: true }, { learnResearch: true, learnTopic: topic }); made.push(v.name); ids.push(v.id); }
    catch (e) { error = String(e && e.message || e); break; }
  }
  return { ok: made.length > 0, count: made.length, topic, error, ids };
}
const pendingLearn = new Map();
// the toolbar's Learn button (src/learnbutton.js): Start = Learn-mode Motes with lifetime forever, Stop = stop them
let learnBtn = null;
const getLearnBtn = () => learnBtn || (learnBtn = new (require('./src/learnbutton').LearnButton)({ dir: app.getPath('userData'), startLearn, stopMote: (id) => helpers.stop(id), onChange: (v) => { if (v.learning) { try { aoQuizFor(v.topic); } catch (e) { /* the quiz tick retries */ } } send('learn:state', v.learning ? { ...v, ...aoQuizView(v.topic) } : v); if (aoState) aoState.setFocus(v.learning ? v.topic : null, 'learn'); } }));
const learningNow = () => !!(learnBtn && learnBtn.cur);
const isLearnAsk = (t, text) => !!t && !t.helper && LEARN_ASK.test(String(text || ''));
// the opener flow: the note for this reply, or '' (an unrelated message or a skip ends the flow; a step never fires twice)
function goalsNoteFor(t, text) {
  const r = Opener.decide(t, text, store.getSettings().goalsSteps);
  if (r.step) store.saveSettings({ goalsSteps: r.done });
  return r.note;
}
function startSleep(o) {
  o = o || {};
  if (sl.asleep || sl.waking) return { error: 'Glim is already asleep.' };
  if (sl.stopping && !o.assistantStopped) return { error: 'Turning off the chat model first. One moment.' };
  if (agent && agent.running) return { error: 'Glim is busy answering you right now. Sleep starts when it is idle, because your chats come first.' };
  if (typeof o.pauseGlims === 'boolean') store.saveSettings({ sleepPauseGlims: o.pauseGlims });
  // how long: minutes | 'morning' | null (until woken). Auto-sleep: to the end of the night window.
  const now0 = new Date(), cfg = store.getSettings();
  const dur = o.auto ? 'morning' : ('minutes' in o ? o.minutes : durationFromSetting(cfg.sleepDuration));
  if (!o.auto && 'minutes' in o) store.saveSettings({ sleepDuration: o.minutes === null ? 'open' : String(o.minutes) });
  const until = computeWakeAt(now0, dur, cfg, learnedNow(now0));
  const deadline = o.auto && !cfg.wakeAt ? null : until;
  // Persist before detaching: a desktop restart must retain both the deadline and
  // the obligation to restore a chat model stopped for this night.
  sl.startedAt = now0.getTime(); sl.wakeAt = deadline; sl.startedAuto = !!o.auto;
  if (!persistSleepSession('preparing')) return { error: 'Could not save this sleep session. Check available disk space and try again.' };
  const r = sleeper.start({ budgetS: nightBudgetS(now0.getTime(), until), wakeAt: deadline });
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
    abandonSleepAttempt();
    return { error: "Glim's chat model is on and using the memory sleep needs.", assistantOn: true };
  }
  if (r.needsRuntime) { abandonSleepAttempt(); send('sleep:needs-runtime', r.plan); return { needsRuntime: true, plan: r.plan, error: r.error }; }
  if (!r.ok) { abandonSleepAttempt(); return { error: r.error }; }
  { const n = new Date(), w = effectiveWindow(store.getSettings(), learnedNow(n)); sl.sleepKey = inWindow(n, w.from, w.to) ? windowKey(n, w.from, w.to) : null; } // the night this sleep belongs to (if any)
  sl.asleep = true; if (helpers && helpers.active.size) helpers.pauseForSleep();   // Motes mid-run stop and run again once after wake; they no longer block sleep (asleep first so their due runs are held)
  try { aoNightly(); aoSleepHandoff(); } catch (e) { /* always-on v2: the speak-o-meter and guesser retune and the handoff is written as sleep starts (best effort) */ }
  sleeper.mark(); sl.wakeAt = o.auto && !cfg.wakeAt ? null : until; sl.asleep = true; sl.starting = Date.now(); sl.startedAuto = !!o.auto; sl.bad = '';
  persistSleepSession('sleeping');
  pushSleep(); updatePill();
  return { ok: true };
}
// stop.sh stops the model servers and gateway and clears ASSISTANT_RUNNING; resolves '' or a plain error
function stopAssistantForSleep() {
  return new Promise((resolve) => {
    // Record the obligation before stop.sh can change the model processes. A
    // crash between its exit and this callback must still restore the model.
    sl.assistantOff = true;
    if (!persistSleepSession('preparing')) { sl.assistantOff = false; return resolve('Could not save the model restart plan, so sleep did not stop your chat model.'); }
    require('child_process').execFile('/bin/bash', [path.join(path.dirname(SERVE_SH), 'stop.sh')], { timeout: 60000 }, (err) => {
      if (sleeper.assistantState() === 'on') return resolve("Could not turn off Glim's big chat model, so sleep could not start" + (err ? ' (' + String(err.message || err).slice(0, 120) + ')' : '') + '.');
      sl.assistantOff = true; persistSleepSession('preparing'); resolve('');
    });
  });
}
// the chat model was turned off for this sleep: start it again (when Glim wakes, or when the sleep never started)
function restoreAssistant() {
  if (!sl.assistantOff || sl.restoreRequested) return;
  const cmd = modelStartCommand(store.getSettings());
  if (cmd) try {
    if (warmer) warmer.gatewayMoved();
    require('child_process').spawn('/bin/zsh', ['-lc', cmd], { cwd: os.homedir(), detached: true, stdio: 'ignore' }).unref();
    sl.restoreRequested = true;
  } catch (e) { /* retain the restart obligation; Turn on is still available */ }
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
  sl.waking = true; sl.wakingAt = Date.now(); sl.bad = ''; persistSleepSession('waking');
  const now = new Date(), s = store.getSettings();
  const wk = wakeKey({ sleepKey: sl.sleepKey, now, settings: s, learned: learnedNow(now) }); // never a key from outside the window: waking at 08:00 must not block tonight
  if (wk) sl.lastKey = wk;
  pushSleep(); updatePill();
  let r;
  try { r = await sleeper.wake(); }
  catch (e) { r = { ok: false, error: String(e.message || e) }; }
  if (!r.ok) { sl.waking = false; sl.bad = 'Could not wake Glim: ' + (r.error || 'unknown error'); pushSleep(); sleepNotice(sl.bad); return { error: sl.bad }; }
  return { ok: true };
}
// "Important updates" dashboard: model for the window, and a push when a source file changes so an open dashboard updates itself.
function dashOpts() { return { home: sleeper.home, tracked: () => (tracking ? tracking.list() : []), overrides: () => DashOver.load(app.getPath('userData')), user: (() => { try { const n = require('./src/user').NAME; return n === 'the user' ? '' : n; } catch (e) { return ''; } })() }; }
function dashboardModel() {
  try { return DashSrc.getDashboard(dashOpts()); }
  catch (e) { console.log('[dashboard] ' + (e && e.message || e)); return null; }
}
let stopDashWatch = null;
function startDashboardWatch() {
  if (stopDashWatch || !sleeper) return;
  try { stopDashWatch = DashSrc.watchSources(dashOpts(), () => send('dashboard:changed', null)); } catch (e) { /* the 60 s refresh still runs */ }
}
// the sleep app has stopped: wait for the gateway to answer again, then show the morning summary
async function onWoke() {
  sl.waking = true; sl.starting = 0; persistSleepSession('restoring'); pushSleep(); updatePill();
  restoreAssistant();
  if (warmer) { warmer.gatewayMoved(); for (let i = 0; i < 240 && warmer.state !== 'ready'; i++) await new Promise((r) => setTimeout(r, E2E ? 100 : 500)); }
  const ready = !!warmer && warmer.state === 'ready';
  sl.asleep = false; sl.waking = false; sl.wakeAt = null; sl.lastActive = Date.now();
  sl.restoreFailed = !ready;
  if (ready) { sl.assistantOff = false; sl.restoreRequested = false; }
  sl.bad = ready ? '' : 'Sleep has stopped, but the chat model is not ready. Use Turn on to try again. Your draft is still here.';
  if (ready) clearSleepSession(); else persistSleepSession('attention');
  const summary = sleeper.readSummary();
  pushSleep(); updatePill();
  send('sleep:woke', { summary, demo: sleeper.status().demo, ready });
  notify(ready ? 'Glim is awake' : 'Sleep stopped · model needs attention', ready ? (summary ? short(summary.replace(/^#.*\n+/, ''), 140) : 'Welcome back.') : sl.bad);
  if (helpers && ready) helpers.tick(); // wait for the restored model before releasing due runs
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
  if (sl.waking && st.sleeping && Date.now() - sl.wakingAt > 90000) { sl.waking = false; sl.bad = 'Glim is taking a long time to wake up. Your draft is still here. Try Wake again or look at ' + sleeper.p.log + '.'; pushSleep(); sleepNotice(sl.bad); return; }
  if (sl.asleep) pushSleep();
}
// Oct 30: Premonition was quit at 10:10 PM and the 11 PM sleep never started. On Ben's kind of Mac (packaged app, his real profile) a
// LaunchAgent opens it hidden at the start of the night window while auto-sleep is on (src/nightstart.js).
let nightStart = null;
function syncNightStart() {
  if (process.platform !== 'darwin' || !app.isPackaged || E2E || app.commandLine.hasSwitch('user-data-dir')) return;
  try {
    nightStart = nightStart || new NightStart({ home: app.getPath('home'), execPath: process.execPath });
    const s = store.getSettings();
    const r = nightStart.sync({ on: s.autoSleep !== false && sleeper.available().ok, from: effectiveWindow(s, learnedNow(new Date())).from });
    if (r === 'installed' || r === 'removed' || (r === 'failed' && syncNightStart.last !== 'failed')) console.log('[sleep] night start ' + r + ' (' + effectiveWindow(s, learnedNow(new Date())).from + ')');
    syncNightStart.last = r;
  } catch (e) { /* never in the way of the app */ }
}

function autoSleepTick(now, over) {
  const s = store.getSettings(); now = now || new Date();
  const common = { settings: s, now, asleep: sl.asleep || sl.waking, startedAuto: sl.startedAuto, learned: learnedNow(now) };
  const w = shouldAutoWake({ ...common, asleep: sl.asleep && !sl.waking });
  if (w.wake) { wakeNow(); return { action: 'wake' }; }
  if (shouldTimedWake({ asleep: sl.asleep, waking: sl.waking, wakeAt: sl.wakeAt, nowMs: now.getTime() })) { wakeNow(); return { action: 'wake', reason: 'the chosen sleep time is up' }; }
  const d = shouldAutoSleep({ ...common, available: sleeper.available().ok && !(sleeper.needsRuntime && sleeper.needsRuntime()), idleMs: Date.now() - sl.lastActive, systemIdleMs: (() => { try { return powerMonitor.getSystemIdleTime() * 1000; } catch (e) { return null; } })(), runActive: !!(agent && agent.running), gatewayBusy: !!(warmer && warmer.warming), windowFocused: !!(win && !win.isDestroyed() && win.isFocused()), onBattery: onBattery(), lastKey: sl.lastKey, ...over });
  // Only Ben's own chat run holds sleep off. Motes mid-run are paused by startSleep and run once after wake (#243); counting them here
  // kept the first night-start night (Oct 30-31) awake: the Motes it had missed ran back to back from 23:00 to morning.
  // Ben's Macs keep the big chat model on all day and it holds the memory sleep needs: without stopAssistant the nightly sleep was refused
  // every night (and lastKey kept it from trying again). It is turned off for the night and back on when Glim wakes, like the Sleep sheet does.
  if (d.sleep) {
    sl.lastKey = d.key;
    const r = startSleep({ auto: true, stopAssistant: true });
    Promise.resolve(r).then((x) => { if (x && x.ok) notify('Glim went to sleep', 'It is past ' + effectiveWindow(s, common.learned).from + ' and you have been away. It wakes when you press Wake.'); }).catch(() => {});
    return { action: 'sleep', result: r };
  }
  if (d.reason !== sl.sleepWhyNot && !/^(off|outside the night window|already)/.test(d.reason)) console.log('[sleep] auto-sleep waits: ' + d.reason);   // once per change: why a night had no sleep
  sl.sleepWhyNot = d.reason;
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
    let done = false;   // answered once; the run's abort listener goes with it (a long run asks many times)
    const fin = (v) => { if (done) return; done = true; if (signal) signal.removeEventListener('abort', onAbort); pending.delete(id); cards.delete(id); pillState.onEvent && resumeRid(id); resolve(v); };
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
  win.on('focus', () => { const t = setTimeout(() => followUpTick().catch(() => {}), 1500); if (t.unref) t.unref(); });
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
    // Ben Oct 28 "I can't see the browser": addChildView(view, undefined) did NOT raise the view on macOS (Electron 33; diag said
    // topIsView=false), so the page stayed under the opaque UI. Re-adding with no index is what moves a child to the top.
    try { if (top) win.contentView.addChildView(rec.view); else win.contentView.addChildView(rec.view, 0); } catch (e) { /* ignore */ }
    if (top) { try { rec.view.setVisible(true); rec.view.webContents.invalidate(); } catch (e) { /* ignore */ } } // Ben Oct 28: a page that loaded while the view was hidden (e.g. right after a restart) stayed blank until repainted
    if (top) diagView(rec, r);
  }
  if (rec.popup) {   // the sign-in popup sits on the page, in the same place
    try {
      rec.popup.setBounds(r);
      if (top !== rec.popupTop) { rec.popupTop = top; if (top) { win.contentView.addChildView(rec.popup); rec.popup.webContents.invalidate(); } else win.contentView.addChildView(rec.popup, 0); }
    } catch (e) { /* closed */ }
  }
}
// Ben Oct 28: the panel showed a dark empty page on his Mac (top=true, right rect) for every URL. One log line per panel open,
// and one 2 s later, says whether the page loaded and painted: url, loading, crashed, renderer pid, bounds, and whether a
// capture of the page is one flat colour (nothing painted).
function diagView(rec, r) {
  const line = async (tag) => {
    try {
      const wc = rec.br.wc;
      if (wc.isDestroyed()) return console.log('[browser:diag] ' + tag + ' destroyed');
      const [cw, ch] = win && !win.isDestroyed() ? win.getContentSize() : [0, 0];
      let paint = '?';
      try {
        const img = await wc.capturePage();
        const sz = img.getSize(), bmp = img.toBitmap();
        if (!sz.width || !bmp.length) paint = 'empty';
        else { let diff = 0; for (let i = 4; i < bmp.length && diff < 50; i += 4 * 97) if (bmp[i] !== bmp[0] || bmp[i + 1] !== bmp[1] || bmp[i + 2] !== bmp[2]) diff++; paint = (diff ? 'content' : 'flat') + ' ' + sz.width + 'x' + sz.height; }
      } catch (e) { paint = 'capture failed: ' + (e && e.message); }
      const b = rec.view.getBounds();
      console.log('[browser:diag] ' + tag + ' url=' + String(wc.getURL()).slice(0, 80) + ' loading=' + wc.isLoading() + ' crashed=' + wc.isCrashed() + ' pid=' + wc.getOSProcessId() + ' bounds=' + [b.x, b.y, b.width, b.height].join(',') + ' rect=' + [r.x, r.y, r.width, r.height].join(',') + ' content=' + cw + 'x' + ch + ' children=' + win.contentView.children.length + ' topIsView=' + (win.contentView.children[win.contentView.children.length - 1] === rec.view) + ' paint=' + paint);
    } catch (e) { console.log('[browser:diag] ' + tag + ' error ' + (e && e.message)); }
  };
  line('open');
  setTimeout(() => line('open+2s'), 2000);
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
  if (rec && rec.br.wc.isDestroyed()) { dropBrowser(key); rec = null; } // the page closed itself: start a fresh one
  if (rec) { rec.used = Date.now(); return rec; }
  const view = new WebContentsView({ webPreferences: { partition: 'persist:desk', contextIsolation: true, sandbox: true, nodeIntegration: false, backgroundThrottling: false, preload: path.join(__dirname, 'preload-browser.js') } });   // LOGIN1: the preload only notices Ben submitting a sign-in form (Save card)
  try { view.setBackgroundColor('#ffffff'); } catch (e) { /* ignore */ } // an empty page shows white, so it is not mistaken for a broken panel
  const br = new Browser({ view, session, onState: () => pushBState(key) });
  br.shouldFocus = () => !(ui && !ui.webContents.isDestroyed() && ui.webContents.isFocused()) || (panel.open && panel.key === key);
  rec = { key, label, view, br, helper: !!(opts && opts.helper), onTop: false, active: false, used: Date.now() };
  browsers.set(key, rec);
  const made = rec;
  // a page that closes its own window (window.close) destroys the view: forget it so the next use makes a new one
  // (diagnostics) why a page would show nothing
  br.wc.on('did-fail-load', (e, code, desc, url, main) => { if (main) console.log('[browser:diag] fail-load ' + code + ' ' + desc + ' ' + String(url).slice(0, 80)); });
  br.wc.on('render-process-gone', (e, d) => console.log('[browser:diag] renderer gone ' + (d && d.reason)));
  br.wc.on('unresponsive', () => console.log('[browser:diag] page unresponsive ' + String(br.wc.getURL()).slice(0, 80)));
  br.wc.once('destroyed', () => setImmediate(() => { if (browsers.get(key) === made) dropBrowser(key); }));
  try { rec.br.wc.setBackgroundThrottling(false); } catch (e) { /* ignore */ }
  if (win && !win.isDestroyed()) { win.contentView.addChildView(view, 0); placeView(rec); }
  // a sign-in popup (Google "Continue with ...") shows over this page inside the browser panel, not as its own window; it goes
  // when the provider closes it after signing in
  if (!rec.helper) br.onPopup = (pv) => {   // (a Mote's popup keeps its own small window: showing it would switch Ben's chat)
    if (!win || win.isDestroyed()) return;
    if (made.popup) { try { win.contentView.removeChildView(made.popup); } catch (e) { /* gone */ } }
    made.popup = pv; made.popupTop = undefined;
    try { pv.setBackgroundColor('#ffffff'); } catch (e) { /* ignore */ }
    win.contentView.addChildView(pv, 0); placeView(made);
    pv.webContents.once('destroyed', () => setImmediate(() => {
      if (made.popup !== pv) return;
      made.popup = null;
      try { if (win && !win.isDestroyed()) win.contentView.removeChildView(pv); } catch (e) { /* gone */ }
      pushBState(key);
    }));
    send('browser-show', { key, threadId: key });
    try { pv.webContents.focus(); } catch (e) { /* ignore */ }
  };
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
  if (rec.popup) { try { win.contentView.removeChildView(rec.popup); } catch (e) { /* ignore */ } rec.popup = null; }
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
  if (!signal) return h.p;
  if (signal.aborted) return Promise.resolve();
  let onAbort;
  const aborted = new Promise((r) => { onAbort = () => r(); signal.addEventListener('abort', onAbort, { once: true }); });
  return Promise.race([h.p, aborted]).finally(() => signal.removeEventListener('abort', onAbort));   // one listener per browser call while Ben holds it: removed each time
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
// Sites Ben is signed in to in the built-in browser (its cookies), for the Motes' "no guessed addresses" check (src/urlguard.js).
// One guard for every agent: a page that failed for one Mote is not retried by the next (each run is a new agent).
const urlGuard = new UrlGuard();
const signedIn = { at: 0, hosts: [] };
async function signedInHosts() {
  if (Date.now() - signedIn.at < 5 * 60000) return signedIn.hosts;
  try { signedIn.hosts = [...new Set((await session.fromPartition('persist:desk').cookies.get({})).map((c) => String(c.domain || '').replace(/^\./, '')).filter(Boolean))]; } catch (e) { /* keep the last list */ }
  signedIn.at = Date.now();
  return signedIn.hosts;
}

function createAgent({ helper, rec, voice }) {
  const isHelper = !!helper;
  const isVoice = !!voice; // the call's own agent: it runs beside the main agent, so a call works while a task is running
  // one browser per thread: a helper's is made up front (its thread id), a chat thread's on its first browser tool
  const bk = () => (isHelper ? helper.threadId : a.threadId);
  // a helper's page that closed itself (window.close) dropped its browser: the next tool call makes a fresh one instead of using the dead one
  const getBr = () => (isHelper ? (rec && browsers.get(bk()) === rec ? rec : (rec = makeBrowser(bk(), (rec && rec.label) || helper.name, { helper: true }))) : makeBrowser(bk(), isVoice ? 'Call' : activeThread && activeThread.title)).br;
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
      if (!cur || cur.br.wc.isDestroyed()) return;
      const s = cur.br.state();
      it.url = s.url; it.title = s.title; it.favicon = s.favicon;
      const t = await cur.br.thumb(360);
      if (t) it.thumb = t;
    } catch (e) { return; }   // the page or its view went away between ticks (Oct 28: 160 unhandled "Object has been destroyed" in 4 min)
    finally { live.busy = false; }
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
    browser_go: async (x, ctx) => {
      // a Mote may only open sites that came from somewhere real, and not a page that keeps failing (src/urlguard.js)
      const no = urlGuard.check(x.url, { strict: isHelper, thread: ctx.thread, extraHosts: isHelper ? await signedInHosts() : [] });
      if (no) return { text: no, error: true, summary: 'Did not open ' + (hostOf(x.url) || 'that address') };
      const r = await getBr().go(x.url);
      if (net.isOnline()) urlGuard.record(x.url, r);   // offline, every site fails: that is not the site's fault
      return r;
    },
    browser_click: (x) => getBr().click(x.id),
    browser_type: async (x, ctx) => {
      const b = getBr();
      // Ben 2026-11-04: passwords in chat are fine (Glim is local). A password field is typed when the model has the text (Ben gave it);
      // empty text, or a payment field, still means Ben fills it himself in the browser panel while we wait.
      const why = await b.sensitiveReason(x.id);
      if (why && !(why === 'password field' && String(x.text || ''))) {
        const v = await ctx.waitForBen(() => signInWait(bk(), a.threadId, ctx.signal));
        return { text: await afterSignIn(b, v), summary: 'Waited while Ben signed in', error: v === 'stopped' };
      }
      return b.type(x.id, x.text, x.enter);
    },
    // LOGIN1: the app fills Ben's saved login for exactly this https site; the model reads only "Signed in as <user> on <host>"
    browser_sign_in: async (x, ctx) => {
      const b = getBr();
      const r = await b.signIn((u) => glimLogins().forPage(u));
      // no saved login on a sign-in form, or a code: Ben does it once in the panel (the app then offers to save the login); a Mote never asks Ben
      if (!isHelper && (r.kind === 'none' || r.kind === 'code')) {
        const v = await ctx.waitForBen(() => signInWait(bk(), a.threadId, ctx.signal));
        const lead = r.kind === 'none' ? 'No saved login for ' + r.host + ', so the app asked Ben to sign in once himself (it then offers to save it). ' : 'A code was needed on ' + r.host + '. ';
        return { text: lead + (await afterSignIn(b, v)), summary: r.kind === 'none' ? 'Ben signed in once on ' + r.host : 'Ben entered the code', error: v === 'stopped' };
      }
      return r;
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
  // a Learn study Mote (src/studygate.js): every search step and every note passes the drift guard, and notes go to the truth check
  // as `maybe` (2 independent sites) instead of straight to memory
  const studyTopic = isHelper && helper.learnResearch && helper.learnTopic ? helper.learnTopic : '';
  const study = studyTopic ? { topic: studyTopic, vocab: () => aoTopicNotes(studyTopic), from: 'learn', onDrift: (kind, text) => aoStudyDrift(studyTopic, kind, text) } : null;
  if (study) tools.web_search = StudyGate.guardSearch(tools.web_search, study);
  const agentMemory = study ? StudyGate.studyMemory({ ...study, memory, truth: getTruth() }) : memory;
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
  const meta = () => ({ title: isHelper ? helper.name : isVoice ? 'Call' : '' }); // the main Glim has no chat title on the pill (Ben Oct 28)
  const a = new Agent({
    memory: agentMemory, tracking, learnResearch: !!(isHelper && helper.learnResearch), helperId: isHelper ? helper.id : null,
    getSettings: isHelper ? () => { const s = store.getSettings(); return { ...s, mode: helper.mode || s.helperMode || 'hands-off', compactTokens: Math.min(Number(s.compactTokens) || 24000, HELPER_COMPACT), thinkActing: false }; } // a Glim's prompt stays small so its cache entry does not push Ben's chat out of the model's prompt cache
      : () => {
        const saved = store.getSettings();
        const s = builtinWanted() ? { ...saved, backendModelFamily: 'lfm3' } : saved;
        return isVoice ? { ...s, model: s.modelFast || s.model, verify: false, thinkActing: false } : s;
      }, // a voice turn uses the fast model and skips the extra self-check
    tools,
    toolDefs: () => toolDefs,
    sleepInfo: isHelper ? null : sleepInfo,
    slot: isHelper ? helperLimiter : limiter,
    onState: helper && helper.onState,
    benBusy: isHelper ? benBusy : null,
    onEnd: () => { holder.release(); endCard(); if (!isHelper) { sl.lastActive = Date.now(); benLastTurn = Date.now(); setTimeout(() => { try { aoHold.flush(); } catch (e) { /* ignore */ } }, 0); } },   // UI2: held proactive words go in once the run is over   // Oct 29: the half-hourly check-in (a helper run) reset Desk's idle clock, so auto-sleep never found 2 idle hours
    emit: (ev) => { send('agent', { threadId: a.threadId, ...ev }); pillState.onEvent(pKey, pName, a.threadId, ev, meta()); if (callTurn && !isHelper && a.threadId === callTurn.threadId) callTurn.onEvent(ev); },
    rememberAlways: (key) => { const cur = store.getSettings().alwaysAllow || []; if (!cur.includes(key)) store.saveSettings({ alwaysAllow: [...cur, key] }); },
    // track I5: safety levels + Glim's hands (enforced in src/agent.js runTool; levels change only from Ben's own words or Settings)
    safety: glimSafety(), hands: E2E ? null : glimHands(),   // the e2e drives screen tools with no real user: no idle wait there
    safetyCtx: () => ({ selfPaths: GLIM_SELF_PATHS(), frontApp: (() => { try { return aoStuck.front().app; } catch (e) { return ''; } })(),
      pageUrl: (() => { try { const b = browsers.get(bk()); return b ? b.br.state().url : ''; } catch (e) { return ''; } })(),
      labelOf: (n, id) => { try { if (n.startsWith('screen_')) return screen.labelOf(id); const b = browsers.get(bk()); const ls = (b && b.br.lastSnap && b.br.lastSnap.lines) || []; return ls.find((l) => l.startsWith('[' + id + ']')) || ''; } catch (e) { return ''; } } }),
    approve: (req, signal) => {
      if (isHelper) return Promise.resolve('deny'); // Ben Oct 31: he only ever talks to the main Glim; a Mote never puts a question or approval in front of him
      const rid = a.threadId + ':' + req.id;
      const ev = { threadId: a.threadId, type: 'approval', rid, ...req };
      send('agent', ev); pillState.onEvent(pKey, pName, a.threadId, ev, meta()); if (callTurn && !isHelper && a.threadId === callTurn.threadId) callTurn.onEvent(ev);
      return waitFor(rid, signal, 'deny', { threadId: a.threadId, ev });
    },
    askUser: (question, signal, options, multi) => {
      const id = 'ask_' + Date.now() + '_' + a.threadId;
      const ev = { threadId: a.threadId, type: 'ask', id, question, options: options && options.length ? options : undefined, multi: multi ? true : undefined };
      send('agent', ev); pillState.onEvent(pKey, pName, a.threadId, ev, meta()); if (callTurn && !isHelper && a.threadId === callTurn.threadId) callTurn.onEvent(ev);
      if (signal) signal.addEventListener('abort', () => send('agent', { threadId: a.threadId, type: 'ask_closed', id }), { once: true });   // I5: hands went ahead / run stopped
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
  const agent = createAgent({ helper: { id: h.id, name: h.name, threadId: h.threadId, mode: h.mode, learnResearch: h.learnResearch === true, learnTopic: h.learnResearch === true ? StudyGate.topicOf(h) : '', onState }, rec });
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
  relayReports(threadId, 0);
}
// Ben Oct 28: "I don't want the subagents to report to me. everything should be filtered through the Glim." A finished helper's report
// waits in the thread's pendingNotices; when Glim is free it reads the reports and tells Ben what matters in its own words (a hidden turn).
const RELAY_ASK = '[A helper finished; its report is above. Tell Ben what matters in one or two short sentences, in your own words as Glim. Do not paste the report. Call the helpers Motes, never agents.]';
const relayTimers = new Map();   // per thread: a report for one chat must not cancel another chat's pending relay
function relayReports(threadId, tries) {
  if (E2E) return; // the scripted test gateway does not expect an extra turn
  clearTimeout(relayTimers.get(threadId));
  const relayTimer = setTimeout(async () => {
    relayTimers.delete(threadId);
    try {
      const t = (activeThread && activeThread.id === threadId && agent.running) ? null : store.loadThread(threadId);
      if (!t || !t.pendingNotices || !t.pendingNotices.length) return;
      if (agent.running || sl.asleep || sl.waking) { if (tries < 30) relayReports(threadId, tries + 1); return; } // Ben's chat first; the notes also ride with his next message
      activeThread = t;
      const r = await agent.run(t, RELAY_ASK, { hidden: true });
      send('threads:changed', {});
      if (!r.stopped && !chatInFront() && !(pillWin && pillWin.enabled)) notify('Glim has news', t.title, t.id);
    } catch (e) { /* the reports stay queued for Ben's next message */ }
  }, tries ? 20000 : 4000);
  relayTimers.set(threadId, relayTimer);
  if (relayTimer.unref) relayTimer.unref();
}

// Ben Oct 28: "make it proactive". Once a day, when Ben brings the chat to the front, Glim follows up on what he left open (a hidden turn in
// his latest main thread). The day is recorded first, so a failure never repeats it. NO_UPDATE means nothing needed him: the turn leaves no trace.
const FU = require('./src/followup');
let followBusy = false;
// Ben Oct 29: the first summary of his long chat read only its newest part. agent.js keeps unread parts as ctxGaps; this rolls them
// up one chunk a minute (fast model) while his chat is idle and Glim is awake, and writes only those fields onto a fresh copy of the
// thread. A message from Ben aborts it; if a window summary changed the gaps meanwhile, the chunk is dropped and redone.
let rollCtl = null;
async function rollupTick() {
  if (rollCtl || benBusy() || sl.asleep || sl.waking || sl.starting || (agent && agent.running)) return;
  const row = (store.listThreads() || []).find((x) => !x.helper && x.title !== 'Call');
  const t = row && store.loadThread(row.id);
  if (!t) return;
  if (noteOldGap(t)) store.patchThread(t.id, (x) => { if ((x.ctxV || 0) >= t.ctxV) return false; x.ctxV = t.ctxV; delete x.ctxOlder; if (t.ctxGaps) x.ctxGaps = t.ctxGaps; else delete x.ctxGaps; });
  if (!t.ctxGaps) return;
  const gaps = JSON.stringify(t.ctxGaps), older = t.ctxOlder || '';
  rollCtl = new AbortController();
  try {
    if (!(await rollupGapStep(t, store.getSettings(), rollCtl.signal)) || rollCtl.signal.aborted || (agent && agent.running)) return;
    store.patchThread(t.id, (x) => {
      if (JSON.stringify(x.ctxGaps) !== gaps || (x.ctxOlder || '') !== older) return false;
      if (t.ctxGaps) x.ctxGaps = t.ctxGaps; else delete x.ctxGaps;
      if (t.ctxOlder) x.ctxOlder = t.ctxOlder;
    });
  } finally { rollCtl = null; }
}
async function followUpTick(over) {
  if (followBusy || E2E || !agent) return;
  const s = store.getSettings(), now = new Date();
  if (!s.onboarded) return;
  const latest = store.listThreads().find((x) => !x.helper && x.title !== 'Call' && x.updated);   // never the Call chat
  const t0 = latest && store.loadThread(latest.id);
  if (!t0 || !(t0.messages || []).length) return;
  if (!FU.shouldFollowUp({ now, lastDay: s.followupDay, hour: now.getHours(), front: chatInFront(), busy: agent.running, asleep: sl.asleep || sl.waking || !!sl.starting, lastActivity: t0.updated, enabled: s.followUp, ...over })) return;
  followBusy = true;
  try {
    await Promise.race([toolsReady, sleep(3000)]);
    if (agent.running || sl.asleep || sl.waking) return; // Ben started something meanwhile: try again on the next tick
    store.saveSettings({ followupDay: FU.dayKey(now) });
    const t = t0, nm = t.messages.length, ni = (t.items || []).length;
    activeThread = t;
    const r = await agent.run(t, FU.FOLLOWUP_ASK, { hidden: true });
    const last = (t.items || []).filter((i) => i.t === 'assistant').pop();
    if (!r.stopped && !r.error && last && String(last.text || '').trim() === 'NO_UPDATE' && !t.items.slice(ni).some((i) => i.t === 'user') && t.messages.length > nm) { t.items.splice(ni); t.messages.splice(nm); store.saveThread(t); } // nothing to say: drop the hidden turn
    else if (!r.stopped && !chatInFront() && !(pillWin && pillWin.enabled)) notify('Glim has a question', t.title, t.id);
    send('threads:changed', {}); if (!openThreadId || openThreadId === t.id) send('open-thread', t.id); // repaint his view; never pull him off another chat
  } catch (e) { /* tomorrow is another day */ } finally { followBusy = false; }
}

// Ben Oct 28: Claude judges the Motes' IDEA lines once a day (the day is saved first, so a failure waits for tomorrow). Feedback goes back to the Mote
// (helperText) and to its parent chat as a notice that Glim relays to Ben.
const IJ = require('./src/ideajudge');
let ideaJudging = false;
async function ideaJudgeTick() {
  if (ideaJudging || E2E || !helpers) return;
  const s = store.getSettings(), today = FU.dayKey(new Date());
  if (s.ideaJudgeDay === today || sl.asleep || sl.waking) return;
  const dir = app.getPath('userData');
  if (!IJ.findKey(dir) || !IJ.pending(dir).length) return;
  ideaJudging = true;
  try {
    store.saveSettings({ ideaJudgeDay: today });
    await IJ.runJudge({ dir, onFeedback: (name, text, vs) => {
      helpers.setFeedback(name, text);
      const h = helpers.find(name), good = vs.filter((x) => x.verdict === 'good').length;
      if (h && h.parent) postNotice(h.parent, 'Idea review', name + ': ' + good + ' good, ' + (vs.length - good) + ' poor. ' + IJ.clean(text, 600));
    } });
  } catch (e) { /* tomorrow */ } finally { ideaJudging = false; }
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
  // Motes share Glim's one local model: 12 at once while Ben chatted swapped the Mac and made his chat crawl (Oct 28). Ben wants many at once, so while he is away there is no cap; while he chats (or just did) only a couple run and the rest queue. Glim's own chat never waits behind them.
  helperLimiter = new Limiter(() => { const m = store.getSettings().maxParallel; return m > 0 ? m : hasLocalAssistant && benBusy() ? 2 : 0; });
  helpers = new Helpers({
    file: path.join(app.getPath('userData'), 'helpers.json'),
    store,
    hold: sleepHold,
    yieldTo: benBusy,
    runner: createRunner({ store, makeAgent: makeHelperAgent }),
    onChange: () => send('helpers:changed', helpers.list()),
    onFinish: (h, summary, parent, flags) => {
      // always-on: a Learn Mote's findings join the inbox (web sense; its notes are already saved for sleep by memory_save)
      { const f = String((flags && flags.report) || summary || '').replace(/\bNO_UPDATE\b/g, '').trim(); if (aoSenses && /^Learn \d+: /.test(h.name) && f) aoSenses.push('web', h.name.replace(/^Learn \d+: /, 'Learned about ') + ': ' + f.slice(0, 400)); }
      if (flags && flags.quiet) return send('helpers:changed', helpers.list()); // nothing new: no notice, no notification
      // Ben Oct 28: a helper never reports to Ben itself. With a parent chat, Glim reads the report and tells him (relayReports, its own
      // notification); only a helper with no chat to report to gets the plain desktop notification.
      if (flags && flags.report && !E2E) { try { require('./src/ideas').appendIdeas(app.getPath('userData'), h.name, h.threadId, require('./src/ideas').parseIdeas(flags.report)); } catch (e) { /* ideas are a bonus */ } }
      // Ben Oct 28-29: "I want them to learn for themselves, not to tell me" / "then don't tell me about that?". A repeating Mote (standing jobs,
      // learn mode) works silently: its findings are saved as notes and cards for sleep, and Glim does not start a turn to relay them. Only a
      // one-time job or a dated reminder, which Ben asked to hear back from, is passed on.
      if (/^(every|daily)\b/.test(String(h.schedule || ''))) return send('helpers:changed', helpers.list());
      if (parent) postNotice(parent, h.name, summary);
      else queueFinish({ name: h.name, summary, threadId: h.threadId, parent, failed: !!(flags && flags.failed) });
      send('threads:changed', {});
    },
    onNeedBen: (h) => notify('Glim needs you', h.name + ': open it to answer.', h.threadId)
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
  glimSafetyFromBen(text, 'ben-voice');   // I5
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
  const micOwner = 'call:' + Date.now() + Math.random(); if (!E2E) getHearing().pause(micOwner);
  const stt = await sttUrl();
  calling = false;
  if (stt.error) { if (hearing) hearing.resume(micOwner); return { error: stt.error, needsVoice: stt.needsVoice }; }
  if (call || dictation) { if (hearing) hearing.resume(micOwner); return { error: 'You are already on a call.' }; }
  callThread = store.newThread(); callThread.title = 'Call'; store.saveThread(callThread);
  const c = new Call({
    helper: bin,
    spawn: (cmd, args) => require('child_process').spawn(cmd, [...args, '--stt', stt.url], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true }),
    ask: callAsk,
    onEvent: (ev) => {
      send('call', ev);
      if (ev.type === 'state' && ev.state === 'ended') { call = null; pillState.setCall(null); if (hearing) hearing.resume(micOwner); if (!((callThread.items || []).length)) store.deleteThread(callThread.id); send('threads:changed', {}); } // a call nobody spoke in leaves no empty chat
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
  const micOwner = 'dictate:' + Date.now() + Math.random(); if (!E2E) getHearing().pause(micOwner);
  const stt = await sttUrl();
  dictStarting = false;
  if (stt.error) { if (hearing) hearing.resume(micOwner); return { error: stt.error, needsVoice: stt.needsVoice }; }
  if (call || dictation) { if (hearing) hearing.resume(micOwner); return { error: 'Dictation is already on.' }; }
  const d = new Dictation({
    helper: bin,
    spawn: (cmd, args) => require('child_process').spawn(cmd, [...args, '--stt', stt.url], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true }),
    onEvent: (ev) => { send('dictate', ev); if (ev.type === 'state' && ev.state === 'ended' && dictation === d) { dictation = null; if (hearing) hearing.resume(micOwner); } }
  });
  dictation = d;
  d.start();
  return { ok: true };
}
function stopDictate(hard) { const d = dictation; if (!d) return; if (hard) { dictation = null; d.close(); } else d.stop('stopped'); }

// ---- Watch me once (src/watchme.js; I4 2026-11-04; setting watchMe, OFF by default) --------------------------------------
// Ben narrates while he does a task; the screen is read at 1 fps (helper look + OCR words), his words come from the local speech
// to text, and stopping saves a skill card (userData/watchme-skills.json) that sleep trains on (SLEEPMLX_SKILL_CARDS). Raw pictures
// are kept as evidence only on a Mac, 3 days at most, 300 MB at most; a private-looking screen is never kept. Redo asks Ben first.
let watchSess = null, watchDict = null;
const watchmeMod = () => require('./src/watchme');
const skillStore = () => new (watchmeMod().SkillStore)(app.getPath('userData'));
async function watchStart() {
  if (store.getSettings().watchMe !== true) return { error: 'Watch me is off (Settings).' };
  if (watchSess) return { error: 'Already watching.' };
  if (call || calling || dictation || dictStarting) return { error: 'End the call or dictation first.' };
  const bin = screen && screen.findHelper();
  if (!bin) return { error: 'Watch me needs the Glim helper, which is not installed in this build.' };
  const W = watchmeMod();
  const clips = process.platform === 'darwin' ? new W.Clips(app.getPath('userData')) : null;
  if (clips) clips.prune();
  const sess = new W.WatchSession({ fps: 1, clips, look: () => screen.run(['look', '--max', '80']),
    ocr: async () => { const j = await screen.run(['ocr', '--max', '3000']); return j && !j.error && typeof j.text === 'string' ? j.text : ''; },
    shot: clips ? async () => { const u = await screen.screenshot(1280); return u ? Buffer.from(u.split(',')[1], 'base64') : null; } : null });
  watchSess = sess;
  sess.start();
  const micOwner = 'watchme:' + Date.now();
  if (!E2E) getHearing().pause(micOwner);
  const stt = await sttUrl();
  if (!stt.error && watchSess === sess) {
    const d = new Dictation({ helper: bin, spawn: (cmd, args) => require('child_process').spawn(cmd, [...args, '--stt', stt.url], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true }),
      onEvent: (ev) => { if (ev.type === 'final') sess.heard(ev.text); if (ev.type === 'state' && ev.state === 'ended' && watchDict === d) { watchDict = null; if (hearing) hearing.resume(micOwner); } } });
    watchDict = d; d.start();
  } else if (hearing) hearing.resume(micOwner);
  return { ok: true, id: sess.id, narration: !stt.error, why: stt.error || '' };
}
function watchStop(name) {
  if (!watchSess) return { error: 'Not watching.' };
  const s = watchSess; watchSess = null;
  if (watchDict) watchDict.stop('stopped');
  const card = s.stop(String(name || '').slice(0, 80));
  const r = card.steps.length ? skillStore().save(card) : { ok: false, error: 'No steps seen.' };
  return { ...r, card: { id: card.id, name: card.name, how: card.how, steps: card.steps.map((x) => ({ n: x.n, what: x.what, say: x.say, how: x.how })) }, privateFramesDropped: s.dropped, clips: s.shots };
}
async function watchRedo(id) {
  if (store.getSettings().watchMe !== true) return { error: 'Watch me is off (Settings).' };
  const card = skillStore().list().find((x) => x.id === id) || skillStore().find(id);
  if (!card) return { error: 'No such skill.' };
  if (!screen || !screen.findHelper()) return { error: 'Redo needs the Glim helper, which is not installed in this build.' };
  const t0 = screen.tools, fz = (n) => (a) => glimHands().freezeOnly((signal) => t0[n](a, { signal }));   // I5: freeze on Ben's input
  const t = { open_app: fz('open_app'), screen_click: fz('screen_click'), screen_type: fz('screen_type'), screen_key: fz('screen_key') };
  const res = (r) => (r && typeof r === 'object' && r.error ? { error: String(r.text || 'failed') } : typeof r === 'string' && /^Error:/.test(r) ? { error: r } : {});
  const tools = { look: () => screen.run(['look', '--max', '80']), open_app: (a) => t.open_app(a).then(res), press: (a) => t.screen_click({ id: a.id }).then(res),
    click: (a) => t.screen_click({ x: a.x, y: a.y }).then(res), type: (a) => t.screen_type(a).then(res), key: (a) => t.screen_key(a).then(res) };
  const confirm = async (c) => (await require('electron').dialog.showMessageBox(win, { type: 'question', buttons: ['Redo it', 'Cancel'], defaultId: 1, cancelId: 1,
    message: 'Let Glim redo "' + c.name + '" on your screen (' + c.steps.length + ' steps)?', detail: c.steps.map((x) => x.n + '. ' + x.what).join('\n').slice(0, 1500) })).response === 0;
  return watchmeMod().replaySkill(card, tools, { confirm });
}

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
  if (FEATURES.sleep && (ch('autoSleep') || ch('sleepFrom') || ch('sleepTo') || ch('sleepAdapt'))) syncNightStart();   // before Ben can quit within the minute
  return out;
}

async function afterFirstPaint() {
  if (afterFirstPaint.done) return;
  try { if (!E2E) aoApply(); } catch (e) { console.error('[alwayson] start', e); }
  afterFirstPaint.done = true;
  timing.deferred = Date.now(); timing.browsersAtPaint = browsers.size; timing.helpersTimerAtPaint = !!(helpers && helpers.timer);
  const s = store.getSettings();
  // everything below is deferred until the window is on screen
  await refreshDiary();
  warmer = new Warmer({
    getSettings: () => store.getSettings(), getTools: () => toolDefs, busy: () => !!(agent && agent.running),
    onState: (state, info) => { if (state === 'ready') { gwReadyAt = Date.now(); if (!sl.asleep && !sl.waking && !sl.stopping && (sl.bad || (sl.assistantOff && sl.restoreRequested) || sl.restoreFailed)) { sl.bad = ''; sl.restoreFailed = false; sl.assistantOff = false; sl.restoreRequested = false; clearSleepSession(); pushSleep(); } } gwState = { state, ...info }; send('gateway', gwState); }
  });
  warmer.start();
  if (builtinWanted()) builtin.start({ lora: sleeper.currentLora && sleeper.currentLora() });
  if (FEATURES.sleep) {
    sleeper.watch(E2E ? 200 : 5000, onSleepPoll);
    if (!E2E) { sampleRhythm(); syncNightStart(); setInterval(() => { sampleRhythm(); syncNightStart(); autoSleepTick(); awakeCheckinTick().catch(() => {}); }, 60000).unref(); }
    {
      const st = sleeper.status();
      const saved = SleepSession.reconcile(SleepSession.read(sleepSessionFile()), st);
      if (saved) { sl.startedAt = saved.startedAt; sl.wakeAt = saved.wakeAt; sl.startedAuto = !!saved.startedAuto; sl.sleepKey = saved.sleepKey; sl.assistantOff = !!saved.assistantOff; }
      if (st.sleeping) { sl.asleep = true; if (!saved) sl.wakeAt = st.wakeAt || null; pushSleep(); autoSleepTick(); }
      else if (saved && saved.phase !== 'attention') { sl.wokeRunning = true; onWoke().finally(() => { sl.wokeRunning = false; }); }
      else if (saved) { restoreAssistant(); sl.restoreFailed = true; sl.bad = 'Sleep has stopped. The chat model may need Turn on before it can answer.'; pushSleep(); }
    }
  }
  if (!E2E) setInterval(() => { followUpTick().catch(() => {}); ideaJudgeTick().catch(() => {}); rollupTick().catch(() => {}); }, 60000).unref();
  if (!E2E && fs.existsSync(SERVE_SH)) { try { require('./src/standing').seedStanding(helpers, app.getPath('userData')); } catch (e) { /* optional */ } }
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
    { label: 'File', submenu: [...(FEATURES.sleepSoon ? [] : [{ label: 'Sleep…', click: () => { showWindow(); send('sleep-open', true); } }]), ...(mac ? [] : [{ label: 'Settings…', accelerator: 'CmdOrCtrl+,', click: openSettings }, { type: 'separator' }]), mac ? { role: 'close' } : { role: 'quit' }] },
    { role: 'editMenu' },
    { label: 'View', submenu: [{ role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' }, { role: 'togglefullscreen' }] },
    { role: 'windowMenu' }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(tpl));
}


// ---- Always-on Premonition (src/senses.js, src/alwayson.js, src/hearing.js) ------------------------------------
// Ben Nov 3: Glim as a persistent state that notices what it is allowed to (screen words, open windows, what it hears, chats,
// its own web reading) and decides by itself when to speak. Every sense starts on (Ben Nov 4: no start-up card; src/senses.js ASK_AT_START) and each can be switched off in Settings (userData/senses.json);
// only words are kept (userData/alwayson-state.json), never a picture or a sound, and private-looking text is dropped first.
const SensesMod = require('./src/senses');
let aoState = null, aoSenses = null, aoLoop = null, hearing = null, lastTyping = 0;
// always-on v2, phase 2: the speak-o-meter (src/speakometer.js) and the stuck detector it reads
const SpeakMod = require('./src/speakometer');
let aoMeter = null;
const aoStuck = new SpeakMod.Stuck();
let aoObservers = [];   // more listeners (the guesser) are added below
function aoObserved(e) { aoStuck.observe(e.sense, e.text); for (const f of aoObservers) { try { f(e); } catch (err) { /* a listener never breaks storage */ } } }
// always-on v2, phase 3: the tiny guesser (src/guesser.js). ~1 s ticks on the latest front app; screen and sound categories on each
// observation. A big Bayesian surprise wakes an always-on tick early and is filed (words only); anything else is not saved.
const GuesserMod = require('./src/guesser');
const aoGuessFile = () => path.join(aoDir(), 'guesser.json');
let aoGuesser = null;
function getGuesser() {
  if (aoGuesser) return aoGuesser;
  let saved = null; try { saved = JSON.parse(fs.readFileSync(aoGuessFile(), 'utf8')); } catch (e) { /* fresh */ }
  return (aoGuesser = new GuesserMod.Guesser({ saved, when: true, onBig: (s) => aoOnSurprise(s) }));   // when: feeling time (src/timesense.js)
}
function saveGuesser() { if (!aoGuesser) return; try { fs.writeFileSync(aoGuessFile(), JSON.stringify(aoGuesser.toJSON())); } catch (e) { /* next minute */ } }
function aoOnSurprise(s) {
  const f = aoStuck.front();
  const what = s.unusualTime ? 'Ben opened ' + (f.app || s.cat) + ' at an unusual time for him (' + TimeSense.clockWords(s.t || Date.now()) + ', ' + s.cat + ').'
    : s.stream === 'app' ? 'Ben switched to ' + (f.app || s.cat) + (f.title ? ' (' + f.title.slice(0, 80) + ')' : '') + ', which I did not expect here (' + s.cat + ').'
    : 'Unexpected ' + s.stream + ': ' + s.cat + '.';
  aoSurprise = { at: Date.now(), what: s.cat };
  if (aoState) { aoState.addSurprise({ stream: s.stream, what, kl: s.kl }); aoState.logActivity('surprise', { what, kl: Math.round(s.kl * 100) / 100 }); }
  aoMinSurprise = true;
  if (aoLoop && aoWakeAllowed()) aoLoop.wake();   // where to look: the early-wake budget is spent in proportion to each region's learned surprise rate
  schedulePill();
}
aoObservers.push((e) => { if (aoSenses && aoSenses.anyEnabled()) getGuesser().observeEntry(e); });
let aoCtxExtra = () => ({ surprise: aoGuesser ? aoGuesser.level() : 0, urges: aoUrges ? aoUrges.view() : {} });
function aoContext(extra) {
  const f = aoStuck.front(), cat = SpeakMod.categorize(f.app, f.title);
  let idleS = 0; try { idleS = powerMonitor.getSystemIdleTime(); } catch (e) { /* unknown */ }
  const typing = Date.now() - lastTyping < 15000 || idleS < 2;
  const last = aoState && aoState.lastSpokeAt;
  return { cat, act: SpeakMod.activity({ idleS, typing, cat }), minsSinceSay: last ? (Date.now() - last) / 60000 : null,
    stuckError: !!aoStuck.error(), stuckPage: aoStuck.pageMinutes() >= 10, ...aoCtxExtra(), ...(extra || {}) };
}
// nightly retune (sleep window or sleep start): the speak-o-meter refits on its whole feedback log; later phases add theirs
let aoNightlyDay = '';
const aoNightlyJobs = [() => aoMeter && aoMeter.refit(), () => aoJudgesNight(), () => aoSleepHandoff()];   // aoJudgesNight: the guesser's fade is LEARNED now (was a fixed 0.8)
function aoNightly(force) {
  const d = new Date().toDateString();
  if (!force && aoNightlyDay === d) return; aoNightlyDay = d;
  for (const j of aoNightlyJobs) { try { j(); } catch (e) { console.log('[alwayson] nightly retune', e); } }
}
// ---- Glim's hands + safety levels (track I5: src/safety-levels.js, src/hands.js, src/goodtime.js) -----------------------------------
// Levels: free / ask / never per category (userData/safety-levels.json). Hands: freeze on the user's own input (deskhelper watch-input,
// Glim's events are tagged), quiet hands first, real mouse only after 2 min idle + one ask that goes ahead after 1 min unanswered.
// Interruption rows -> the 'goodtime' day log (features only). The judge is NOT PROVEN in its toy test (premonition-handslab-i5): it is not
// trained at night yet and judge() returns null, so it never vetoes.
const SafetyMod = require('./src/safety-levels'), HandsMod = require('./src/hands');
let glimSafetyObj = null, glimHandsObj = null, glimHandsWatch = null;
const GLIM_SELF_PATHS = () => [__dirname, app.getPath('userData'), path.join(os.homedir(), 'learner-ops', 'sleepmlx'), path.join(os.homedir(), 'learner-ops', 'sleepmlx-src')];
const glimSafety = () => glimSafetyObj || (glimSafetyObj = new SafetyMod.SafetyLevels({ dir: app.getPath('userData'), onChange: (l) => send('safety:levels', l) }));
function glimHands() {
  if (glimHandsObj) return glimHandsObj;
  const input = new HandsMod.InputWatch();
  glimHandsObj = new HandsMod.Hands({ input, levels: glimSafety(),
    askUser: () => Promise.resolve('No'),   // only used without a run's own card
    notify: (t) => { if (!chatInFront()) notify('Glim', t); },
    notice: (n) => send('safety:notice', n),
    status: (t) => { try { pillState.flash(t); updatePill(); } catch (e) { /* ui only */ } },
    record: (row) => aoJudges().record('goodtime', row),
    judge: () => null,
    frontApp: () => { try { const f = aoStuck.front(); return SpeakMod.categorize(f.app, f.title); } catch (e) { return 'other'; } } });
  if (process.platform === 'darwin' && !E2E) {
    glimHandsWatch = new HandsMod.HelperWatch({ input, log: (m) => console.log('[hands]', m),
      spawn: () => { const b = screen && screen.findHelper(); return b ? require('child_process').spawn(b, ['watch-input'], { stdio: ['pipe', 'pipe', 'ignore'] }) : null; } });
    glimHandsWatch.start();
  }
  let n = 0;
  setInterval(() => { try { if (input.source !== 'helper') input.fromIdleSample(powerMonitor.getSystemIdleTime()); if (++n % 8 === 0) glimHandsObj.tick(); } catch (e) { /* next */ } }, 2000).unref();
  return glimHandsObj;
}
// Ben's own words (main chat box or a call): a level change is applied at once with a one-line notice + Undo; "stop"/"not now" is logged
function glimSafetyFromBen(text, source) {
  try { const ch = SafetyMod.fromBenText(text); if (ch.length) { const r = glimSafety().set(ch, { source }); if (r.ok) send('safety:notice', { text: r.notice, undo: r.undo }); } } catch (e) { /* never blocks the chat */ }
  try { glimHands().onBenText(text); } catch (e) { /* log only */ }
}
// ---- saved logins (track LOGIN1: src/logins.js) --------------------------------------------------------------------------------------
// Glim signs in with logins Ben saved; the password never passes through the model. Mac: Keychain items labelled "Premonition";
// Windows: safeStorage. The Save card comes from Ben submitting a sign-in form in Glim's browser (preload-browser.js), or from the
// masked dialog ("save my Schoology login"). Settings > Safety lists them (hosts + usernames only) with Remove.
const Logins = require('./src/logins');
let glimLoginsObj = null, loginCapture = null;
function glimLogins() {
  if (glimLoginsObj) return glimLoginsObj;
  const dir = app.getPath('userData');
  const box = process.platform === 'darwin' ? new Logins.MacKeychain() : new Logins.SafeStorageBox({ dir, safeStorage: require('electron').safeStorage });
  glimLoginsObj = new Logins.LoginStore({ dir, box });
  glimLoginsObj.warm().catch(() => {});   // every saved password into memory once, so the redaction pass can catch it anywhere
  loginCapture = new Logins.LoginCapture({ store: glimLoginsObj,
    allowHost: (host) => !SafetyMod.isBanking(host) || glimSafety().level('banking') !== 'never',
    offer: (ev) => send('logins:offer', ev) });
  return glimLoginsObj;
}
// a browser view of Glim's (or its sign-in popup) reports a submitted form; the sender's real URL decides the site, never the message
ipcMain.on('pm-login:submit', (e, d) => {
  try {
    const wc = e.sender; if (!wc || wc.isDestroyed() || (ui && wc === ui.webContents)) return;
    const rec = [...browsers.values()].find((r) => r.br.wc === wc || (r.popup && r.popup.webContents === wc));
    if (!rec || rec.helper) return;   // only Ben's own browsing offers a Save card
    const url = (e.senderFrame && e.senderFrame.url) || wc.getURL();
    glimLogins();
    loginCapture.submitted({ key: wc.id, url, user: d && d.user, password: d && d.password, filling: rec.br.wc === wc && rec.br.filling > Date.now(),
      probe: () => wc.isDestroyed() ? Promise.resolve(null) : wc.executeJavaScript('(' + Logins.pageLoginProbe.toString() + ')()') }).catch(() => {});
  } catch (err) { /* never breaks browsing */ }
});
// "save my Schoology login" in Ben's own chat box -> the masked dialog (prefilled with the likely site), and a note for the model
async function loginDialogFor(text, threadId) {
  const ask = Logins.saveLoginAsk(text); if (!ask) return '';
  let page = ''; try { const b = browsers.get(threadId); page = b ? b.br.state().url : ''; } catch (e) { /* none */ }
  let hosts = []; try { hosts = await signedInHosts(); } catch (e) { /* none */ }
  send('logins:dialog', { site: Logins.guessOrigin(ask.word, page, hosts), word: ask.word });
  return Logins.DIALOG_NOTE(ask.word);
}

// ---- sleep for the small judges (sleep track T1: src/sleepjudges.js + src/breaks.js; toy lab premonition-sleeplab-t1) -------------
// Only the parts that passed the toy test (3/3 seeds): the guesser's fade rates are LEARNED per stream (app / when / idle) instead of
// a fixed 0.8; the scientist's think-longer threshold (extra tries only when the first try is unsure); where to look (the early-wake
// budget follows each region's learned surprise rate). Every night: replay -> update -> seatbelt (held-out day, keep or roll back; a
// day that contradicts everything is held, and quarantined unless the next day agrees) -> one diary line per part. Logs in userData.
// The idle/break stream is learned and logged but NOT fed to imagine's breakSoon (its toy test failed by one share): aoBreakSoon stays null.
const JudgesMod = require('./src/sleepjudges'), BreaksMod = require('./src/breaks');
let aoJudgesObj = null, aoBreaks = null, aoLook = null, aoMinSurprise = false, aoWakes = { day: -1, by: {}, seen: {} };
const aoJudges = () => aoJudgesObj || (aoJudgesObj = new JudgesMod.SleepJudges({ dir: aoDir() }));
const aoJudgeFile = (n) => path.join(aoDir(), n);
const aoJudgeSave = (n, obj) => { const tmp = aoJudgeFile(n) + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(obj)); fs.renameSync(tmp, aoJudgeFile(n)); };   // JSON state only, atomic
function aoBreaksGet() {
  if (aoBreaks) return aoBreaks;
  let saved = null; try { saved = JSON.parse(fs.readFileSync(aoJudgeFile('breaks.json'), 'utf8')); } catch (e) { /* fresh */ }
  return (aoBreaks = new BreaksMod.BreakTracker({ saved, onRow: (r) => aoJudges().record('guesser', r) }));
}
function aoLookGet() {
  if (aoLook) return aoLook;
  try { aoLook = JSON.parse(fs.readFileSync(aoJudgeFile('where.json'), 'utf8')); } catch (e) { aoLook = null; }
  if (!aoLook || !aoLook.a || !aoLook.b) aoLook = { a: {}, b: {} };
  return aoLook;
}
const aoRegion = () => { const f = aoStuck.front(); return SpeakMod.categorize(f.app, f.title) + ':' + String(f.app || '?').toLowerCase().slice(0, 40); };
const aoWakeDay = () => { const d = JudgesMod.dayIndex(Date.now()); if (aoWakes.day !== d) aoWakes = { day: d, by: {}, seen: {} }; return aoWakes; };
// once a minute with the windows sense on: the break tracker (its rows -> the guesser log) and one "look" at the front region
function aoJudgeMinute() {
  if (!aoSenses || !aoSenses.enabled('windows') || sl.asleep) return;
  const now = Date.now(), f = aoStuck.front(); let idleS = 0; try { idleS = powerMonitor.getSystemIdleTime(); } catch (e) { /* unknown */ }
  aoBreaksGet().tick(now, idleS, SpeakMod.categorize(f.app, f.title), { app: f.app, title: f.title });   // raw kept for the truth check (I2)
  const r = aoRegion(), y = aoMinSurprise ? 1 : 0, w = aoLookGet(); aoMinSurprise = false;
  const k = y ? 'a' : 'b'; w[k][r] = (w[k][r] || 0) + 1; aoWakeDay().seen[r] = 1;
  aoJudges().record('where-to-look', { t: now, r, y });
  try { aoJudgeSave('breaks.json', aoBreaks.toJSON()); aoJudgeSave('where.json', w); } catch (e) { /* next minute */ }
}
// an early wake on a surprise, within the front region's share of today's budget
function aoWakeAllowed() {
  const W = aoWakeDay(), r = aoRegion(); W.seen[r] = 1;
  const allow = JudgesMod.wakeAllowance(aoLookGet(), Object.keys(W.seen));
  if ((W.by[r] || 0) >= allow[r]) return false;
  W.by[r] = (W.by[r] || 0) + 1; return true;
}
function aoJudgesNight() {
  const J = aoJudges(), outs = [];
  // truth check before sleep (I2, src/truthcheck.js; settings.truthCheck, default ON): only labels with a real truth are checked
  const tc = require('./src/truthcheck').forSettings(store.getSettings(), aoDir());
  if (aoGuesser) {
    const g = aoGuesser, br = aoBreaksGet(), st = J.state('guesser'), prevK = (st.start && st.start.k) || { app: 0.8, when: 0.8, idle: 0.8 };
    let out = null;
    if (g.when) { try { out = J.run(JudgesMod.guesserPart(), { app: g.streams.app.toJSON(), when: g.when.toJSON(), idle: br.model.toJSON(), k: prevK }, { truthcheck: tc }); } catch (e) { console.log('[alwayson] judges guesser', e); } }
    const k = out && out.rec.action === 'kept' ? out.model.k : prevK;   // rolled back / held / no log today: yesterday's rates (0.8 at first)
    g.streams.app.decay(k.app); if (g.when) g.when.decay(k.when); br.model.decay(k.idle);
    g.streams.screen.decay(0.8); g.streams.sound.decay(0.8);           // not part of the toy test: today's fixed fade
    saveGuesser(); try { aoJudgeSave('breaks.json', br.toJSON()); } catch (e) { /* next minute */ }
    if (out) outs.push(out);
  }
  try { const out = J.run(JudgesMod.thinkPart(), J.state('think-longer').start || JudgesMod.thinkPart().init()); if (out) outs.push(out); } catch (e) { console.log('[alwayson] judges think', e); }
  try { const out = J.run(JudgesMod.wherePart(), aoLookGet()); if (out) { if (out.rec.action === 'kept') { aoLook = out.model; try { aoJudgeSave('where.json', aoLook); } catch (e) { /* */ } } outs.push(out); } } catch (e) { console.log('[alwayson] judges where', e); }
  for (const o of outs) { console.log('[alwayson] sleep judge ' + o.line); if (aoState) aoState.logActivity('sleep-part', { part: o.rec.part, line: o.line }); }
  try {   // learners without a separate truth: logged so the morning shows they were not checked
    tc.note('think-longer', 'right/wrong was set by the executor when the row was logged; the answers are not kept to re-run');
    tc.note('where-to-look', 'its label is the day\'s own surprise signal, not a truth');
    tc.note('watcher', 'labels are recomputed each night from the tick and outcome log');
    tc.note('patterns', 'made by formula from notes; wrong notes never join, maybe notes make a pattern maybe');
    for (const l of tc.lines) console.log('[alwayson] ' + l);
  } catch (e) { /* log only */ }
  return outs;
}
// ---- feeling time + patterns (Task B, src/timesense.js + src/patterns.js) ------------------------------------------------
// A timeline of timestamped words (observations, surprises, truth notes) with a name-masked shape key each. The loop's prompt
// gets the clock, "N min ago", up to 5 recalled memories (2 of them may come by shape = analogy) and up to 2 patterns.
// Patterns are made at sleep start by formula only (clustering + counting); no model is called there.
const TimeSense = require('./src/timesense');
const PatternsMod = require('./src/patterns');
let aoTimeline = null;
const getTimeline = () => aoTimeline || (aoTimeline = new PatternsMod.Timeline({ dir: aoDir() }));
aoObservers.push((e) => { if (aoSenses && aoSenses.anyEnabled()) getTimeline().add({ t: e.t, kind: 'obs', sense: e.sense, text: e.text }); });
function aoTimelineSync() {
  const tl = getTimeline();
  if (aoTruth) tl.syncNotes(aoTruth.notes);
  if (aoState) for (const x of aoState.surprises) if (x && x.what && x.t && !tl.byRef.has('sur:' + x.t)) tl.add({ t: x.t, kind: 'surprise', text: x.what, ref: 'sur:' + x.t });
  return tl;
}
function aoLoopContext(fresh) {
  try { aoWatchTickStart(fresh); } catch (e) { /* T6 watcher labels only */ }
  const tl = aoTimelineSync(), now = Date.now();
  const query = fresh.slice(-3).map((o) => o.text).join(' ').slice(0, 1200);
  const oldest = Math.min(...fresh.map((o) => (TimeSense.validT(o.t) ? o.t : now)));
  const recall = tl.recall(query, { k: 5, before: oldest - 1 }).map((r) => '(' + (r.item.kind === 'obs' ? 'seen' : r.item.kind) + ' ' + TimeSense.ago(r.item.t, now) + (r.via === 'shape' ? ', same shape' : '') + (r.item.status === 'maybe' || r.item.status === 'unsure' ? ', maybe' : '') + ') ' + r.item.text.slice(0, 140));
  const patterns = tl.patternsFor(query).map((x) => PatternsMod.patternLine(x.p));
  return { recall, patterns, likely: aoGuesser && aoGuesser.when ? TimeSense.likelyWords(aoGuesser.when, now) : '' };
}
// Ben asks a time question in chat ("how long ago did I…", "what happened right before…", "what usually happens after…"):
// a hidden note with the answer from the timestamped records (like the diary); '' for anything else
const PATTERN_ASK = /\bwhat\s+(?:usually|normally|typically)\s+happens\s+(?:after|when)\s+(.+)$/i;
function aoTimeNote(text) {
  const t = String(text || '');
  if (!aoState || !(TimeSense.isTimeAsk(t) || PATTERN_ASK.test(t))) return '';
  const tl = aoTimelineSync(), now = Date.now();
  const pm = PATTERN_ASK.exec(t);
  if (pm) {
    const w = tl.whatFollows(pm[1]);
    const ans = w && w.follow ? 'From ' + w.pattern.size + ' times I saw "' + w.pattern.template + '"' + (w.pattern.maybe ? ' (some from unchecked notes, so maybe)' : '') + ': next, ' + w.follow.count + ' of ' + w.follow.of + ' times, "' + w.follow.template + '" (about ' + Math.round(w.follow.medianMin) + ' min later).' : 'I have not seen that often enough to know what usually follows it.';
    return '[Glim\'s patterns (made by counting, not guessing). Ben asked what usually happens after something: answer briefly from this only.\n' + ans + '\n] ';
  }
  const recs = tl.items.filter((x) => TimeSense.validT(x.t)).map((x) => ({ t: x.t, text: x.text })).concat(aoState.inbox.filter((x) => TimeSense.validT(x.t)).map((x) => ({ t: x.t, text: x.text })));
  const a = TimeSense.answerTimeQuestion(t, recs, now);
  return '[Glim\'s timestamped records. Ben asked a time question: answer briefly from this only' + (a ? '' : '; nothing matches, so say you do not know') + '. Now: ' + TimeSense.clockWords(now) + '.\n' + (a ? a.answer : 'No record matches.') + '\n] ';
}
// at sleep start: patterns by formula (src/patterns.js Timeline.sleep: clustering + counts; never a model call)
function aoPatternSleep() {
  const r = aoTimelineSync().sleep({ shapeKeys: store.getSettings().learnedShapeKeys === true });   // T3: off by default (seatbelt unproven)
  console.log('[alwayson] patterns: ' + r.kept + ' kept, ' + r.made + ' new, ' + r.filed + ' filed, ' + r.revived + ' revived (' + r.items + ' records, ' + r.ms + ' ms)');
  if (aoState) aoState.logActivity('patterns', { made: r.made, kept: r.kept, filed: r.filed });
  // sleep track T3: per-link pruning by next-day surprise + learned shape keys (seatbelt inside Timeline.sleep)
  if (aoState && r.links) aoState.logActivity('sleep-part', { part: 'patterns', line: 'Patterns: ' + r.links.dropped + ' "what follows" links switched off (they made the next day worse), ' + r.links.back + ' back on, ' + r.links.quiet + ' patterns quiet.' });
  if (aoState && r.shapeKeys) aoState.logActivity('sleep-part', { part: 'shapekeys', line: 'Shape keys (analogy): ' + (r.shapeKeys.kept ? 'kept' : 'not updated') + (r.shapeKeys.old != null ? ', latest-day margin ' + r.shapeKeys.old.toFixed(2) + ' -> ' + r.shapeKeys.new.toFixed(2) : '') + (r.shapeKeys.kept ? '' : ' (' + r.shapeKeys.why + ')') + '.' });
  return r;
}
aoNightlyJobs.push(() => aoPatternSleep());
// sleep track T3: the learned world model for the sandbox games (src/worldmodel.js). The scientist logs every rulebook step it
// sees; each night the counts are re-learned with the seatbelt (latest day held out + fixed checks; rolled back if worse).
// aoWorld() is what L2 planning passes as imagine's o.world (the rulebook stays the fallback).
const WorldModelMod = require('./src/worldmodel');
let aoGameLogObj = null, aoWorldObj;
const aoGameLog = () => aoGameLogObj || (aoGameLogObj = new WorldModelMod.GameLog({ dir: aoDir() }));
const aoWorld = () => (aoWorldObj === undefined ? (aoWorldObj = WorldModelMod.load(aoDir())) : aoWorldObj);
aoNightlyJobs.push(() => {
  const r = WorldModelMod.nightly({ dir: aoDir(), log: aoGameLog(), truthCheck: store.getSettings().truthCheck !== false }); aoWorldObj = undefined;   // I2 truth check: the rulebook replays every logged step
  console.log('[alwayson] ' + r.line);
  if (aoState) aoState.logActivity('sleep-part', { part: 'worldmodel', line: r.line });
});
const aoDir = () => app.getPath('userData');
function aoSetup() {
  if (aoSenses) return;
  aoState = new SensesMod.AlwaysOnState(aoDir(), { onAdd: (e) => aoObserved(e) });
  aoMeter = new SpeakMod.SpeakOMeter({ dir: aoDir() });
  getTruth();
  aoUrges = new UrgesMod.Urges({ saved: aoState.urges });
  const sc = SensesMod.startConsent(SensesMod.loadConsent(aoDir()));   // no start-up card: undecided = every sense on (Ben Nov 4)
  if (sc.granted) { try { SensesMod.saveConsent(aoDir(), sc.consent); } catch (e) { /* used in memory; saved on the next change */ } }
  aoSenses = new SensesMod.Senses({ consent: sc.consent, state: aoState, changeOnly: () => store.getSettings().senseChangeOnly === true, onScreen: (text, win) => aoEyesLook(text, win), samplers: {
    // words on screen through Vision OCR inside the helper (nothing written to disk)
    screen: async () => { if (!screen || !screen.findHelper()) return ''; const j = await screen.run(['ocr', '--max', '3000']); return j && !j.error && typeof j.text === 'string' ? j.text : ''; },
    windows: async () => {
      if (!screen || !screen.findHelper()) return '';
      const w = await screen.run(['windows']); const l = await screen.run(['look', '--max', '60']);
      return SensesMod.windowsText(w, l);
    }
  } });
}
async function aoPerms() {
  const out = { accessibility: null, screenRecording: null, microphone: null };
  if (process.platform !== 'darwin' || E2E) return out;
  try { if (screen && screen.findHelper()) { const c = await screen.check(); if (c && !c.error) { out.accessibility = !!c.accessibility; out.screenRecording = !!c.screenRecording; } } } catch (e) { /* unknown */ }
  try { out.microphone = systemPreferences.getMediaAccessStatus('microphone') === 'granted'; } catch (e) { /* unknown */ }
  return out;
}
async function sensesView() {
  aoSetup();
  const c = aoSenses.consent, p = await aoPerms();
  return { consent: c, senses: SensesMod.SENSES, needs: SensesMod.needsConsent(c), missing: SensesMod.missingPerms(c, p), perms: p, status: aoLoop ? aoLoop.statusLine() : '' };
}
async function setSenses(patch) {
  aoSetup();
  const prev = aoSenses.consent;
  const c = SensesMod.saveConsent(aoDir(), { ...prev, ...patch, senses: { ...prev.senses, ...((patch && patch.senses) || {}) }, decidedAt: Date.now() });
  aoSenses.setConsent(c);
  aoApply();
  return sensesView();
}
async function askSensesPerms() {
  const r = {};
  try { if (screen && screen.findHelper()) Object.assign(r, await screen.askPermissions()); } catch (e) { /* shown as missing */ }
  try { if (process.platform === 'darwin' && aoSenses && aoSenses.consent.senses.hearing) r.microphone = await systemPreferences.askForMediaAccess('microphone'); } catch (e) { /* shown as missing */ }
  return r;
}
// Ben first: typing in the last 15 s, a chat reply, a call or dictation all hold the always-on loop (and cancel a tick in flight)
const aoBusy = () => benBusy() || !!(agent && agent.running) || Date.now() - lastTyping < 15000 || !!call || calling || !!dictation || dictStarting;
const aoNight = () => { if (sl.asleep || sl.waking) return true; const n = new Date(), w = effectiveWindow(store.getSettings(), learnedNow(n)); return inWindow(n, w.from, w.to); };
// one short non-streamed request to the same gateway and model as chat's Fast pill (AlwaysOnMod.chatModel: Nanbeige on Ben's Mac). Marked test so the gateway keeps these background
// prompts out of the diary the nightly sleep trains on: only the notes Glim chooses to save reach sleep (through memory).
async function aoAsk(messages, signal, opts) {
  const { buildChatBody, chatUrl } = require('./src/llm');
  const s = store.getSettings();
  const body = buildChatBody({ model: AlwaysOnMod.chatModel(s), messages, stream: false, maxTokens: (opts && opts.maxTokens) || 220, temperature: opts && opts.temperature != null ? opts.temperature : 0.2, test: true });
  const headers = { 'content-type': 'application/json', 'x-test': '1' };
  if (s.apiKey) headers.authorization = 'Bearer ' + s.apiKey;
  const ctl = new AbortController(); const kill = setTimeout(() => ctl.abort(), 90000);
  const stop = () => ctl.abort(); signal.addEventListener('abort', stop);
  try {
    const r = await fetch(chatUrl(s.gatewayUrl), { method: 'POST', headers, body: JSON.stringify(body), signal: ctl.signal });
    if (!r.ok) throw new Error('gateway ' + r.status);
    const j = await r.json();
    return (j && j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content) || '';
  } finally { clearTimeout(kill); signal.removeEventListener('abort', stop); }
}
function mainChatId() { const t = (store.listThreads() || []).find((x) => !x.helper && x.title !== 'Call'); return t ? t.id : null; }
// always-on v2 (src/glimvoice.js): Glim's unprompted words go to the notch island (notched Mac), the floating pill (no notch), or a
// macOS notification ("Use the notch" off). Never while Ben is typing: they wait for a pause and are dropped after 2 minutes.
const GlimVoice = require('./src/glimvoice');
let aoSurprise = { at: 0, what: '' };
const aoTypingNow = () => { if (Date.now() - lastTyping < 15000) return true; try { return powerMonitor.getSystemIdleTime() < 2; } catch (e) { return false; } };
const aoNotched = () => !!(pillWin && pillWin.geo && pillWin.geo.notchH > 0);
const aoWhere = () => { const s = store.getSettings(); return GlimVoice.route({ useNotch: s.useNotch !== false, notched: aoNotched(), pillOn: s.pill !== false && !!pillWin }); };
// UI2 (Ben Nov 4, M3): a proactive chat message while a task runs waits for the task to end (it used to be dropped); it never cuts the task
const { HoldWhileBusy } = require('./src/aohold');
const aoHold = new HoldWhileBusy({
  busy: () => !!(agent && agent.running),
  post: (m) => {
    const id = mainChatId(); m.threadId = id;
    if (!id) return;
    const t = store.loadThread(id);
    // Ben Nov 4 (M1 test): these went to the chat view only, so asked "how do you know that?" Glim said it had no record of saying it.
    // Now the model's history holds it too, tagged as said unprompted from what the loop noticed.
    const at = new Date(), hh = at.getHours() % 12 || 12, mm = String(at.getMinutes()).padStart(2, '0'), ap = at.getHours() < 12 ? 'AM' : 'PM';
    if (t) { t.items.push({ t: 'assistant', text: m.text, ts: Date.now(), alwaysOn: true, sayId: m.id });
      if (Array.isArray(t.messages)) t.messages.push({ role: 'assistant', content: "(Said on my own at " + hh + ':' + mm + ' ' + ap + ", from what I noticed on Ben's screen or mic; he did not ask.) " + m.text });
      store.saveThread(t); send('threads:changed', {}); if (openThreadId === id) send('open-thread', id); }
  }
});
const aoVoice = new GlimVoice.Voice({
  where: aoWhere, typing: aoTypingNow,
  outlets: {
    chat: (m) => aoHold.offer(m),   // UI2: while a task runs it waits (never cuts or lands inside the task); posted when the task ends
    notch: (m) => pillState.say(m), pill: (m) => pillState.say(m),
    notification: (m) => notify('Glim', m.text, m.threadId)
  },
  onOutcome: (m, kind) => { try { aoOnOutcome(m, kind); } catch (e) { console.log('[alwayson] outcome', e); } },
  log: (...a) => console.log('[alwayson]', ...a)
});
// feedback -> the speak-o-meter: logged with the features the message went out with, one online step now, refit at night
let aoOnOutcome = (m, kind) => { if (aoMeter && m.features) aoMeter.learn(m.features, kind, { sayId: m.id }); };
function aoSay(text, d) { aoVoice.offer(text, { why: d && d.why, features: d && d.features }); if (aoUrges) aoUrges.spoke(); if (aoState) aoState.logActivity('said', { text: String(text).slice(0, 120) }); }
// the ear: 😴 resting · 📚 learning (+ Motes) · 💭 thinking · 😲 surprised, while always-on is on
let aoEarExtra = () => ({});
function aoEar() {
  if (!aoSenses || !aoSenses.anyEnabled()) return null;
  const lb = learnBtn && learnBtn.cur;
  return GlimVoice.statusIcon({ now: Date.now(), asleep: sl.asleep, thinking: !!(aoLoop && aoLoop.inTick) || !!aoPool.thinking(), thinkingAbout: aoPool.thinking(), gauge: aoGaugeNow.level, surprisedAt: aoSurprise.at, surpriseWhat: aoSurprise.what,
    learning: lb ? { topic: lb.topic, levels: aoQuizView(lb.topic).levels } : null, motes: (lb ? lb.ids.length : 0) + aoPool.count(), ...aoEarExtra() });
}
// "note": the existing notes path (memory.md), which the nightly sleep reads with the day's chats
// v2 (phase 5): a note from the loop is a `maybe` until 2 independent websites confirm it (src/truthnotes.js); only then does it reach memory
function aoStudyDrift(topic, kind, text) {
  console.log('[alwayson] study drift (' + kind + ') off "' + topic + '": ' + String(text).slice(0, 100));
  if (aoState) aoState.logActivity('thought', { topic, claims: 0, drift: 1, step: kind });
}
function aoNote(text) { try { if (aoTruth) aoTruth.add(text, { from: 'noticed' }); } catch (e) { /* skipped */ } aoWatchRef('note:' + String(text).slice(0, 200)); }
// ---- T6 (2026-11-04): the watcher (src/watcher.js), a tiny net beside the guesser, trained only in sleep ---------------------
// Every second it scores cheap features (app, screen/sound category, how much the words changed, keyword flags, the guesser's
// surprise). Its labels are what happened: a tick that read those seconds and whose say got 👍 / was used / got a reply, or whose
// note became confirmed = useful; a finished tick with nothing to say = not useful. Nightly: replay + train + seatbelt + keep/roll back.
// Until a night has kept a model (it must first beat the guesser's own surprise on held-out), it only logs. Setting `watcher: false` = off.
const WatcherMod = require('./src/watcher');
let aoWatcherObj = null, aoWatchPending = null;
const aoWatcher = () => aoWatcherObj || (aoWatcherObj = new WatcherMod.Watcher({ dir: aoDir(), log: (...a) => console.log('[alwayson]', ...a) }));
// ---- Glim can see (track I1: src/eyes.js + tools/glim_eyes.py + the model server's image_features path; setting glimCanSee, off) ----
// Each screen read (senses onScreen) -> one small screenshot -> SigLIP2 features on this Mac -> sense sleep's FeatureStore (screen words
// as the anchor) + the latest frame for the always-on loop's next ask. Private-looking screens/windows: no picture is taken.
const EyesMod = require('./src/eyes');
let aoEyesObj = null;
function aoEyes() {
  if (aoEyesObj) return aoEyesObj;
  const s0 = store.getSettings();
  const py = s0.eyesPython || path.join(os.homedir(), 'learner-ops', 'nb2-venv', 'bin', 'python');
  const script = path.join(__dirname, 'tools', 'glim_eyes.py');
  const worker = new EyesMod.EyesWorker({ log: (m) => console.log('[eyes]', m),
    spawn: () => require('child_process').spawn(py, ['-I', script, 'serve'], { stdio: ['pipe', 'pipe', 'pipe'], cwd: os.tmpdir() }) });
  aoEyesObj = new EyesMod.Eyes({ userData: aoDir(), worker, isPrivate: SensesMod.isPrivate, log: (m) => console.log('[eyes]', m),
    on: () => store.getSettings().glimCanSee === true && process.platform === 'darwin' && !E2E,
    keepEvidence: () => store.getSettings().keepSenseEvidence === true,
    shot: async () => (screen ? EyesMod.fromDataUrl(await screen.screenshot(512)) : null) });
  return aoEyesObj;
}
function aoEyesLook(text, win) { if (store.getSettings().glimCanSee !== true) return null; return aoEyes().look(text, win || aoLatestText('windows')); }
// the always-on loop's asks carry the latest frame (once, < 2 min old) when the eyes are on; every other ask is unchanged
function aoAskSeeing(messages, signal, opts) { const part = aoEyesObj && aoEyesObj.framePart(); return aoAsk(part ? EyesMod.withFrame(messages, part) : messages, signal, opts); }
setInterval(() => { if (aoEyesObj && store.getSettings().glimCanSee !== true) aoEyesObj.o.worker.stop(); }, 60000).unref();
aoNightlyJobs.push(() => { if (store.getSettings().glimCanSee !== true && !aoEyesObj) return; const r = aoEyes().nightly(); console.log('[eyes] night', JSON.stringify(r)); if (aoState) aoState.logActivity('sleep-part', { part: 'eyes', line: r.manifests.length ? 'eye practice ready for ' + r.manifests.map((m) => m.night + ' (' + m.eye + ')').join(', ') : 'no eye practice' }); });
function aoLatestText(sense) { const ib = aoState ? aoState.inbox : []; for (let i = ib.length - 1; i >= 0; i--) if (ib[i].sense === sense) return ib[i].text; return ''; }
function aoWatchSecond(gr) {
  if (!gr || store.getSettings().watcher === false) return;
  const cat = gr.cat;
  const g = aoGuesser, other = g && g.last && g.last.stream !== 'app' && Date.now() - g.last.at < 1500 ? g.last.kl : 0;
  const r = aoWatcher().observe({ app: cat, screenText: aoLatestText('screen'), soundText: aoLatestText('hearing'), kl: (gr ? gr.kl : 0) + other });
  if (r.wake && aoLoop && aoLoop.wake() && aoState) aoState.logActivity('watcher', { score: Math.round(r.score * 100) / 100 });
}
// a tick starts (it read the fresh observations): remember its window; a say / note it makes links its outcome
function aoWatchTickStart(fresh) {
  const ts = fresh.map((o) => o.t).filter((t) => TimeSense.validT(t));
  aoWatchPending = { t0: ts.length ? Math.min(...ts) - 1000 : Date.now() - 60000, t1: Date.now(), ref: null };
}
function aoWatchRef(ref) { if (!aoWatchPending || !ref) return; try { aoWatcher().tickRead(aoWatchPending.t0, aoWatchPending.t1, ref, null); aoWatchPending.ref = ref; } catch (e) { /* log only */ } }
// a tick ended: finished with nothing to say = not useful; cancelled / unreadable / error = unknown (no label)
function aoWatchTickEnd(reason) {
  const p = aoWatchPending; if (!p) return; aoWatchPending = null;
  if (reason === 'done' && !p.ref) { try { aoWatcher().tickRead(p.t0, p.t1, null, false); } catch (e) { /* log only */ } }
}
function aoWatchHook(loop) {
  if (!loop || loop.watchHooked) return; loop.watchHooked = true;
  const r0 = loop.result.bind(loop); loop.result = (reason, extra) => { try { aoWatchTickEnd(reason); } catch (e) { /* log only */ } return r0(reason, extra); };
}
// a say offered while a tick is in flight links that tick (deferred says outside a tick link nothing)
{ const offer0 = aoVoice.offer.bind(aoVoice); aoVoice.offer = (text, extra) => { const m = offer0(text, extra); if (m) aoWatchRef('say:' + m.id); return m; }; }
{ const prevOutcome = aoOnOutcome; aoOnOutcome = (m, kind) => { prevOutcome(m, kind); try { aoWatcher().outcome('say:' + m.id, ['up', 'used', 'reply'].includes(kind)); } catch (e) { /* log only */ } }; }
aoNightlyJobs.push(() => { if (store.getSettings().watcher === false) return; const w = aoWatcher(); w.nightly(); w.prune(); });
// ---- T6: the real-time sandbox game "Sparks" (src/games/realtime.js) with a reflex fast path (muscle memory) --------------------
// While Ben is away and Glim may think, one practice game at most every 10 minutes with the fast path (the late planner until a
// reflex has been kept). At night the slow planner labels the logged frames at its own pace and the reflex is distilled (seatbelt +
// rollback). Glim's own game; nothing from the Bedwars bots. Setting `reflexGames: false` = off.
const RealtimeMod = require('./src/games/realtime');
let aoReflexObj = null, aoReflexLast = 0;
const aoReflex = () => aoReflexObj || (aoReflexObj = new RealtimeMod.Reflex({ dir: aoDir(), cfg: { maxFrames: 8000 }, log: (...a) => console.log('[alwayson]', ...a) }));
function aoReflexPlay() {
  if (store.getSettings().reflexGames === false || Date.now() - aoReflexLast < 600000) return;
  let idleS = 0; try { idleS = powerMonitor.getSystemIdleTime(); } catch (e) { return; }
  if (idleS < 120 || !aoMoteGate().budget) return;
  aoReflexLast = Date.now();
  try { const sc = aoReflex().playDay(Date.now() % 1e9); if (aoState) aoState.logActivity('game', { game: 'sparks', score: Math.round(sc), fast: aoReflex().ready() ? 'reflex' : 'late planner' }); } catch (e) { console.log('[alwayson] sparks', e); }
}
setInterval(() => { try { aoReflexPlay(); } catch (e) { /* next minute */ } }, 60000).unref();
aoNightlyJobs.push(() => { if (store.getSettings().reflexGames !== false) aoReflex().nightly(); });
// ---- I3: the two-speed core (src/games/core/): plan memory + intent channel + timed actions + reflex-in-sleep ---------------------
// Setting "Two-speed play" (`twoSpeedPlay`, default OFF). When on, while Ben is away (the same gates as Sparks above), one practice
// game at most every 10 minutes, Sparks quest and Orchard in turn, played by the two-speed loop with the STAND-IN slow brain (the
// adapter's planner, in simulated time; the real model is not called). Frames are logged per day; at night the reflex is distilled
// from that day's frames only (head-by-head seatbelt on held-out days, rollback). Toy evidence: premonition-sleeplab-i3 MARKS v1.
const TwoSpeed = { loop: require('./src/games/core/loop'), sleep: require('./src/games/core/reflex'), games: { sparksquest: require('./src/games/adapters/sparksquest'), orchard: require('./src/games/adapters/orchard') } };
let aoTwoLast = 0, aoTwoTurn = 0; const aoTwoSleeps = {};
const aoTwoSleep = (name) => aoTwoSleeps[name] || (aoTwoSleeps[name] = new TwoSpeed.sleep.ReflexSleep({ dir: path.join(aoDir(), 'twospeed', name), log: (...a) => console.log('[alwayson]', ...a) }));
function aoTwoSpeedPlay() {
  if (store.getSettings().twoSpeedPlay !== true || Date.now() - aoTwoLast < 600000) return;
  let idleS = 0; try { idleS = powerMonitor.getSystemIdleTime(); } catch (e) { return; }
  if (idleS < 120 || !aoMoteGate().budget) return;
  aoTwoLast = Date.now(); const name = Object.keys(TwoSpeed.games)[aoTwoTurn++ % 2], ad = TwoSpeed.games[name], sl = aoTwoSleep(name);
  try {
    const r = TwoSpeed.loop.runEpisode(ad, { seed: Date.now() % 1e9, reflex: sl.net }); sl.logDay(r.acts, r.times);
    if (aoState) aoState.logActivity('game', { game: ad.name, goal: !!r.outcome.goalDone, replans: r.replans, timingMs: r.timing.medianAbsMs === Infinity ? null : Math.round(r.timing.medianAbsMs || 0), fast: sl.ready() ? 'reflex' : 'hand rule' });
  } catch (e) { console.log('[alwayson] two-speed', e); }
}
setInterval(() => { try { aoTwoSpeedPlay(); } catch (e) { /* next minute */ } }, 60000).unref();
aoNightlyJobs.push(() => { if (store.getSettings().twoSpeedPlay !== true) return; for (const [name, ad] of Object.entries(TwoSpeed.games)) { try { aoTwoSleep(name).nightly({ features: ad.features, label: ad.nightLabel, fallback: ad.fallbackRaw, nIn: ad.nIn, nA: ad.nA }); } catch (e) { console.log('[alwayson] two-speed night', e); } } });
// "learn": one quiet Mote for 2 hours, only when no Learn study is running (Ben's Learn button always wins)
function aoLearn(topic) { if (learningNow()) return false; const r = startLearn(topic, 1, 2); return !!r.ok; }
// ---- always-on v2, phase 4: urges, the memory gauge, bored-mode Motes (src/urges.js, src/memgauge.js, src/motepool.js) ----------
// Bored -> a batch of thinking Motes through chat's own model. The gauge decides how many: 🟢 + away + AC = full batch, 🟢 + busy = 2,
// 🟡 = 1 (away) or 0, 🔴 / swap growing = 0. Ben chatting, typing, sleep or the night window stop every one at once.
const UrgesMod = require('./src/urges'), GaugeMod = require('./src/memgauge'), PoolMod = require('./src/motepool');
let aoUrges = null, aoShare = null;
const aoRecent = {};   // topic (lower case) -> when a Mote last thought about it
const aoGauge = new GaugeMod.MemGauge({ pressure: () => AlwaysOnMod.macPressure() });
let aoGaugeNow = { level: 'green', pressure: 1, swapGrowMB: 0 };
// o.learnOnly: the Learn quiz needs no sense switched on (the Learn button works without always-on); everything else does
function aoMoteGate(o) {
  if (!(o && o.learnOnly) && (!aoSenses || !aoSenses.anyEnabled())) return { budget: 0, why: 'off' };
  if (sl.asleep || sl.waking) return { budget: 0, why: 'asleep' };
  if (aoBusy()) return { budget: 0, why: 'chat' };
  try { if (aoNight()) return { budget: 0, why: 'night' }; } catch (e) { /* not known: carry on */ }
  aoGaugeNow = aoGauge.read();
  let idleS = 0; try { idleS = powerMonitor.getSystemIdleTime(); } catch (e) { /* unknown */ }
  const budget = GaugeMod.budget({ gauge: aoGaugeNow.level, away: idleS >= 120, onAC: !onBattery(), chatting: false });
  return { budget, why: budget ? null : aoGaugeNow.level === 'red' ? 'memory' : 'busy', gauge: aoGaugeNow.level };
}
const MOTE_SYSTEM = 'You are one of Glim\'s Motes, thinking quietly about one topic while Ben is busy. Nobody sees this but Glim. '
  + 'Reply with ONE JSON object and nothing else: {"claims": [up to 3 short, specific statements you believe are true about the topic], "question": "one thing about it you are not sure of" or null}. '
  + 'Only claims a website could confirm. No opinions, no advice.';
const MOTE_WHY = { learn: 'Ben asked you to learn this.', day: 'This came up on Ben\'s screen today.', wonder: 'It is on your wonder list (something you did not understand).' };
let aoMotePrompt = (job) => [{ role: 'system', content: MOTE_SYSTEM }, { role: 'user', content: 'Topic: ' + job.topic + '\n' + (MOTE_WHY[job.kind] || '') + '\nAnswer with the JSON object only.' }];
// every claim a Mote makes becomes a `maybe` note for the truth check (phase 5)
// drift guard (phase 6): a Learn-topic claim must still be about the topic, else it is skipped
let aoMoteClaims = (job, claims) => {
  let kept = claims, skipped = 0;
  if (job.kind === 'learn') { const vocab = aoTopicNotes(job.topic); kept = claims.filter((c) => QuizMod.onTopic(c, job.topic, vocab)); skipped = claims.length - kept.length; }
  for (const c of kept) getTruth().add(c, { topic: job.topic, from: 'mote:' + job.kind });
  if (aoState) aoState.logActivity('thought', { topic: job.topic, claims: kept.length, drift: skipped });
};
function aoMoteResult(job, r) {
  aoRecent[job.topic.toLowerCase()] = Date.now();
  if (!r) { if (aoState) aoState.logActivity('mote', { topic: job.topic, kind: job.kind, ok: false }); return; }
  if (r.question && aoState && aoState.addWonder(r.question, 'a Mote was unsure while thinking about ' + job.topic) && aoUrges) aoUrges.wonder();
  if (aoState) aoState.logActivity('mote', { topic: job.topic, kind: job.kind, ok: true, minutes: Math.max(0.1, (Date.now() - job.at) / 60000) });
  aoMoteClaims(job, r.claims || []);
}
// E1: setting moteBatch -> a Mote's K tries go to the server together, streamed (src/motebatch.js); stopAll aborts all of them
async function aoAskStream(messages, signal, opts) {
  const { buildChatBody, chatUrl } = require('./src/llm');
  const s = store.getSettings();
  const body = buildChatBody({ model: AlwaysOnMod.chatModel(s), messages, stream: true, maxTokens: (opts && opts.maxTokens) || 350, temperature: opts && opts.temperature != null ? opts.temperature : 0.2, test: true });
  const headers = { 'content-type': 'application/json', 'x-test': '1' };
  if (s.apiKey) headers.authorization = 'Bearer ' + s.apiKey;
  const ctl = new AbortController(); const kill = setTimeout(() => ctl.abort(), 90000);
  const stop = () => ctl.abort(); signal.addEventListener('abort', stop);
  try { return await require('./src/motebatch').streamText({ url: chatUrl(s.gatewayUrl), headers, body, signal: ctl.signal }); }
  finally { clearTimeout(kill); signal.removeEventListener('abort', stop); }
}
const aoAskBatch = require('./src/motebatch').makeAskBatch({ askOne: (m, sig, o) => aoAskStream(m, sig, o) });
const aoPool = new PoolMod.MotePool({ ask: (m, sig, o) => aoAsk(m, sig, { maxTokens: 350, ...(o || {}) }), gate: aoMoteGate, prompt: (job) => QuizMod.safeStudier(aoMotePrompt, job, aoQuizS()),
  askBatch: aoAskBatch, canBatch: () => store.getSettings().moteBatch === true,
  tries: () => aoTries(), pick: (job, parsed) => aoPickThought(job, parsed),
  onResult: (job, r, t, x) => { aoMoteResult(job, r); aoAfterPick(job, r, x); }, onChange: () => schedulePill(), log: (...a) => console.log('[alwayson]', ...a) });
// ---- ingredients (2026-11-04): the checker + "I'm not sure" (src/checker.js), the little scientist (src/scientist.js) ------------
// Bored-mode thinking Motes make K tries (setting moteTries, default 4; back-to-back, Ben's server is serial) and the checker picks
// one: a settled truth note wins, else the agreement share (UNTESTED as a picker; the Oct 17 toy test found vote pickers fail).
// A low top score = "I'm not sure" -> the wonder list. Ben's live chat never uses multi-try (it does not go through this pool).
const CheckerMod = require('./src/checker'), ScientistMod = require('./src/scientist');
let aoCheckerObj = null, aoScientistObj = null, aoSciTurn = 0;
const aoChecker = () => aoCheckerObj || (aoCheckerObj = new CheckerMod.Checker({ dir: aoDir(), learned: { enabled: store.getSettings().checkerLearned === true } }));
const aoTries = () => { const k = Number(store.getSettings().moteTries); return Number.isFinite(k) && k >= 1 ? Math.min(8, k | 0) : ScientistMod.K_TRIES; };
function aoPickThought(job, parsed) { const p = aoChecker().pickThoughts(job.topic, parsed, { truth: aoTruth }); job.pickInfo = p; return p.index; }
function aoAfterPick(job, r, x) {
  const p = job.pickInfo; if (!p || !r) return;
  for (const c of p.claims || []) if (!c.verified) aoChecker().expect(c.text, c.p_correct, { method: c.method, kind: 'claim' });   // calibration when the 2-site check settles it
  if (p.notSure && p.claims && p.claims.length && aoState) {
    const top = p.claims.slice().sort((a, b) => b.p_correct - a.p_correct)[0];
    if (aoState.addWonder(top.text, "I'm not sure (" + p.method + ' ' + p.p_correct.toFixed(2) + (p.method === 'agreement' ? ', untested' : '') + ')') && aoUrges) aoUrges.wonder();
    aoState.logActivity('notsure', { topic: job.topic, text: aoChecker().hedge(top.text, p.p_correct).slice(0, 140), p: Math.round(p.p_correct * 100) / 100 });
    aoStuckAdd(StuckMod.fromNotSure(top.text, p.p_correct));   // T5 stuck list (no truth at night: stays until a day check settles it)
  }
}
// the little scientist: experiments in the sandbox / puzzle generator / games, run as Motes (same gate, same stop), guesses first
const aoScientist = () => aoScientistObj || (aoScientistObj = new ScientistMod.Scientist({ dir: aoDir(), checker: aoChecker(), k: aoTries(), gameLog: aoGameLog(),
  thinkMore: (c) => JudgesMod.thinkMore(aoJudges().state('think-longer').start, c), onTries: (r) => aoJudges().record('think-longer', r),   // think longer only when unsure (threshold learned at night)
  onSurprise: (x) => { if (aoState) { aoState.addSurprise({ stream: x.stream, what: x.what, kl: x.kl }); aoState.logActivity('surprise', { what: x.what.slice(0, 140), kl: Math.round(x.kl * 100) / 100, source: 'sandbox' }); } },
  onActivity: (kind, o) => { if (aoState) aoState.logActivity(kind, o); }, onStuck: (x) => aoStuckAdd(StuckMod.fromExperiment(x)), log: (...a) => console.log('[alwayson]', ...a) }));
// how many of a bored batch are experiments: half (rounded up); with a budget of 1 they take turns with thinking. Setting scientist: false = none.
function aoSciShare(budget) { if (store.getSettings().scientist === false || budget <= 0) return 0; if (budget === 1) return (aoSciTurn++ % 2) ? 1 : 0; return Math.ceil(budget / 2); }
function aoSciEnd(why) { if (aoScientistObj) aoScientistObj.endSession(why); }
let aoLearnTopics = () => (learnBtn && learnBtn.cur ? [learnBtn.cur.topic] : []);
function aoDayTopics() {
  const out = []; const e = aoStuck.error(); if (e) out.push('what causes this error and how to fix it: ' + e.text);
  if (e) aoStuckAdd(StuckMod.fromBenError(e));   // T5 stuck list: Ben stuck on the same error 3+ times
  if (aoState) for (const x of aoState.surprises.slice(-3).reverse()) if (x.stream !== 'app') out.push(x.what);
  if (aoState && aoState.focus && aoState.focus.topic) out.push(aoState.focus.topic);
  return out;
}
// every minute: urges fill or drain; a bored Glim starts a batch; something worth telling may go to the speak-o-meter
function aoUrgeTick() {
  if (!aoUrges || !aoSenses || !aoSenses.anyEnabled()) return;
  aoUrges.tick({ fresh: aoState.fresh().length > 0, chatting: !!(agent && agent.running) || Date.now() - benLastTurn < 10 * 60000, wonder: aoState.wonder.length });
  aoState.urges = aoUrges.view(); aoState.save();
  if (aoUrges.isBored() && !aoPool.count()) {
    const g = aoMoteGate();
    if (g.budget > 0) {
      const nSci = aoSciShare(g.budget);
      const topics = UrgesMod.chooseTopics({ learn: aoLearnTopics(), day: aoDayTopics(), wonder: aoState.wonder.slice().reverse().map((w) => w.text.replace(/^weak spot in (.+?) \(quiz [^)]*\)$/, 'the weak spots of $1')), recent: aoRecent }, g.budget - nSci);
      const sci = nSci ? aoScientist().jobs(nSci, { learnTopic: aoLearnTopics()[0] || null }) : [];
      if ((topics.length || sci.length) && aoPool.startBatch(topics.concat(sci))) { aoUrges.studied(topics.length + sci.length); aoState.logActivity('bored', { motes: topics.length, experiments: sci.length, gauge: g.gauge, topics: topics.map((t) => t.topic.slice(0, 60)) }); }
    }
  }
  aoMaybeShare();
}
// 📣 share: something worth telling waits until the speak-o-meter AND the v1 limits (Ben first, pressure, night, 20 min) allow it
function aoMaybeShare() {
  if (!aoShare || !aoUrges || aoUrges.share < 0.5 || !aoLoop || !aoMeter) return false;
  if (aoLoop.gate() || !aoLoop.sayAllowed({ say: aoShare.text })) return false;
  const d = aoMeter.decide(aoContext());
  if (!d.speak) return false;
  aoState.spoke(); aoSay(aoShare.text, { why: 'share', features: d.x }); aoUrges.spoke(); aoShare = null;
  return true;
}
function aoWorthTelling(text, w) { if (!aoUrges) return; aoShare = { text: String(text).slice(0, 300), at: Date.now() }; aoUrges.worthTelling(w); }
// ---- always-on v2, phase 5: truth-seeking notes (src/truthnotes.js) ------------------------------------------------------
// Thoughts are `maybe` notes; one at a time (when the Mote gate is open) the checker searches the web and asks chat's model whether
// each result supports or contradicts the note. 2 independent sites -> confirmed / wrong (a correction). Only those reach memory.
const TruthMod = require('./src/truthnotes');
let aoTruth = null, aoTruthCtl = null, aoTruthAt = 0;
const JUDGE_SYSTEM = 'You check ONE claim against ONE search result. Reply with ONE JSON object and nothing else: {"verdict": "supports" | "contradicts" | "unclear", "correction": "the correct fact in one short sentence if the result contradicts the claim, else null"}. '
  + 'Say "supports" only if the result clearly states the same fact. Say "contradicts" only if it clearly states a different fact.';
async function aoJudge(claim, src, signal) {
  const text = await aoAsk([{ role: 'system', content: JUDGE_SYSTEM }, { role: 'user', content: 'Claim: ' + claim + '\nResult title: ' + src.title + '\nResult text: ' + (src.snippet || '').slice(0, 500) + '\nAnswer with the JSON object only.' }], signal, { maxTokens: 120 });
  const a = String(text || '').indexOf('{'), b = String(text || '').lastIndexOf('}');
  try { const j = JSON.parse(String(text).slice(a, b + 1)); if (['supports', 'contradicts', 'unclear'].includes(j.verdict)) return { verdict: j.verdict, correction: typeof j.correction === 'string' ? j.correction : '' }; } catch (e) { /* fall back */ }
  return TruthMod.lexicalJudge(claim, src);
}
function getTruth() {
  return aoTruth || (aoTruth = new TruthMod.TruthNotes({ dir: aoDir(), search: (q, signal) => webSearch(q, { signal }), judge: aoJudge,
    save: (text, topic, opts) => memory.save(text, topic, opts),
    onSettled: (n) => {
      if (aoState) aoState.logActivity('note', { status: n.status, topic: n.topic, text: (n.status === 'wrong' ? n.correction : n.text).slice(0, 140) });
      if (n.status === 'wrong' && aoUrges) aoUrges.worthTelling(0.15);
      try { aoChecker().settled(n.text, n.status === 'confirmed'); } catch (e) { /* calibration only */ }
      try { aoWatcher().outcome('note:' + String(n.text).slice(0, 200), n.status === 'confirmed'); } catch (e) { /* watcher labels only */ }
    }, log: (...a) => console.log('[alwayson]', ...a) }));
}
// the 1 s clock: at most one check every 20 s, only while bored-mode Motes would be allowed (Ben first, sleep, night, memory)
function aoTruthTick() {
  if (!aoTruth || aoTruth.checking || Date.now() - aoTruthAt < 20000) return;
  const n = aoTruth.next(); if (!n) return;
  if (aoTruthGate().budget <= 0) return;
  aoTruthAt = Date.now(); const ctl = aoTruthCtl = new AbortController();
  aoTruth.check(n, ctl.signal).finally(() => { if (aoTruthCtl === ctl) aoTruthCtl = null; });
}
// the truth check runs while always-on is on OR a Learn study is on (its notes wait as `maybe` until checked); same Ben-first gate
function aoTruthGate() { return aoMoteGate({ learnOnly: learningNow() }); }
function aoStopChecks() { if (aoTruthCtl) { try { aoTruthCtl.abort(); } catch (e) { /* gone */ } aoTruthCtl = null; } }
// ---- always-on v2, phase 6: the Learn quiz score (src/quiz.js) ------------------------------------------------------------
// Starting a Learn topic queues a separate WRITER pass that builds a locked quiz (~20 questions, answers found on the pages, source
// URLs) in userData/learn-quiz/. Studier prompts never see it (checked on every prompt). The EXAMINER answers it with chat's model
// (guess + confidence first), graded against the stored answers. Official score = the first one after the nightly sleep.
const QuizMod = require('./src/quiz');
let aoQuizStore = null, aoQuizCache = { at: 0, topic: '', v: null };
const aoQuizS = () => aoQuizStore || (aoQuizStore = new QuizMod.QuizStore(aoDir()));
let aoQuizCtl = null, aoQuizAt = 0, aoQuizOfficialDue = false, aoQuizLastSleep = false;
function privateHost(u) { try { const h = new URL(u).hostname; return !/^https?:$/.test(new URL(u).protocol) || /^(?:localhost|127\.|10\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.|\[?::1\]?$)/i.test(h) || h.endsWith('.local'); } catch (e) { return true; } }
async function aoFetchPage(url, signal) {
  if (privateHost(url)) throw new Error('not a public web page');
  const ctl = new AbortController(), kill = setTimeout(() => ctl.abort(), 15000), stop = () => ctl.abort();
  if (signal) signal.addEventListener('abort', stop, { once: true });
  try {
    const r = await fetch(url, { headers: { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15', accept: 'text/html' }, signal: ctl.signal, redirect: 'follow' });
    if (!r.ok || !/text\/html|text\/plain/i.test(r.headers.get('content-type') || '')) return '';
    return (await r.text()).slice(0, 1500000);
  } finally { clearTimeout(kill); if (signal) signal.removeEventListener('abort', stop); }
}
function aoTopicNotes(topic) {
  const out = [];
  if (aoTruth) for (const n of aoTruth.notes) if (n.status === 'confirmed' && (n.topic === topic || QuizMod.onTopic(n.text, topic))) out.push(n.text);
  try { for (const f of memory.list()) if (f && f.text && QuizMod.onTopic(f.text, topic)) out.push(f.text); } catch (e) { /* memory unreadable */ }
  return out.slice(-30);
}
function aoQuizView(topic) {
  if (aoQuizCache.topic === topic && Date.now() - aoQuizCache.at < 5000) return aoQuizCache.v;   // the ear asks every second
  const z = topic ? aoQuizS().load(topic) : null;
  const v = z ? { score: QuizMod.scoreLine(z), levels: QuizMod.scoreLevels(z), writing: z.status === 'writing' } : { score: '', levels: [] };
  aoQuizCache = { at: Date.now(), topic, v };
  return v;
}
function learnView() { const v = getLearnBtn().view(); return v.learning ? { ...v, ...aoQuizView(v.topic) } : v; }
const aoQuizGate = () => aoMoteGate({ learnOnly: true }).budget > 0;
// a new Learn topic: make the (empty) quiz record now; the writer fills it when the gate opens
function aoQuizFor(topic) { if (!topic || aoQuizS().load(topic)) return; aoQuizS().save({ topic, createdAt: Date.now(), status: 'writing', levels: [], scores: [], guesses: [] }); }
async function aoQuizWork(z, signal) {
  const ask = (m, sig) => aoAsk(m, sig, { maxTokens: 400 });
  const newest = z.levels.length ? Math.max(...z.levels.map((l) => l.level)) : 0;
  if (z.status === 'writing' || z.levelUpDue) {
    const level = z.status === 'writing' && !newest ? 1 : newest + 1;
    const r = await QuizMod.writeLevel(z.topic, level, { search: (q, sig) => webSearch(q, { signal: sig }), fetchPage: aoFetchPage, ask, parseResults: TruthMod.parseResults, siteOf: TruthMod.siteOf, signal, gate: aoQuizGate, avoid: z.levels.flatMap((l) => l.questions.map((q) => q.q.toLowerCase())) });
    if (signal.aborted) return;
    const cur = aoQuizS().load(z.topic) || z;
    if (r.questions.length >= 5) { cur.levels.push({ level, questions: r.questions, sources: r.sources, writtenAt: Date.now() }); cur.status = 'ready'; cur.levelUpDue = false; cur.examDue = true; }
    else { cur.writeTries = (cur.writeTries || 0) + 1; if (cur.writeTries >= 3) { cur.status = cur.levels.length ? 'ready' : 'failed'; cur.levelUpDue = false; } }
    aoQuizS().save(cur); aoQuizCache.at = 0;
    if (aoState) aoState.logActivity('quiz-written', { topic: z.topic, level, questions: r.questions.length, sites: r.sources.length });
    send('learn:state', learnView());
    return;
  }
  const official = aoQuizOfficialDue;
  const before = QuizMod.scoreLevels(z);
  for (const L of z.levels) {
    const res = await QuizMod.takeLevel(z, L.level, { ask, notes: aoTopicNotes(z.topic), signal, gate: aoQuizGate });
    if (!res) return;   // stopped (Ben came back, memory, sleep): it runs again later
    const cur = aoQuizS().load(z.topic) || z;
    cur.guesses = (cur.guesses || []).concat(res.guesses.map((g) => ({ ...g, level: L.level, at: Date.now() }))).slice(-400);
    const { levelUp } = QuizMod.recordScore(cur, res, official);
    if (levelUp) cur.levelUpDue = true;
    cur.examDue = false; cur.lastExamAt = Date.now();
    aoQuizS().save(cur); aoQuizCache.at = 0;
    // free checker labels (graded by quiz.js; the labels file is never shown to studiers and never read by sleep)
    for (const g of res.guesses) { try { const q = (L.questions || []).find((x) => x.id === g.id); aoChecker().label({ question: q ? q.q : g.id, answer: g.guess, correct: !!g.correct, p: g.confidence, pMethod: 'self', method: 'quiz', source: 'quiz', truth: 'sources', kind: 'quiz:' + z.topic.slice(0, 40) }); } catch (e) { /* labels only */ } }
    // a confident miss is a surprise; it goes on the wonder list WITHOUT the question (the quiz stays locked from the studiers)
    for (const g of res.guesses) {
      const fs2 = GuesserMod.factSurprise(g.confidence, g.correct);
      if (fs2.wonder && aoState) { aoState.addWonder('weak spot in ' + z.topic + ' (quiz ' + g.id + ')', 'confident quiz miss'); aoState.addSurprise({ stream: 'fact', what: 'I was sure about a ' + z.topic + ' quiz answer and got it wrong.', kl: fs2.surprise }); if (aoUrges) aoUrges.wonder(); }
    }
    for (const g of res.guesses) if (!g.correct) aoStuckAdd(StuckMod.fromQuizMiss(z.topic, g.id));   // T5 stuck list: locked (topic + item id only)
    const was = (before.find((b) => b.level === L.level) || {}).pct;
    if (aoState) aoState.logActivity('quiz', { topic: z.topic, level: L.level, pct: res.pct, was: was == null ? null : was, official });
    if (official && levelUp) aoWorthTelling('I reached ' + res.pct + '% on my ' + z.topic + ' quiz (level ' + L.level + '), so I am starting a harder level.', 0.5);
  }
  if (official) aoQuizOfficialDue = false;
  send('learn:state', learnView());
}
// the 1 s clock: one quiz job at a time, at most every 30 s, only when the Mote gate is open; chat aborts it
function aoQuizTick() {
  if (sl.asleep !== aoQuizLastSleep) { if (aoQuizLastSleep && !sl.asleep) aoQuizOfficialDue = true; aoQuizLastSleep = sl.asleep; }
  if (aoQuizCtl || Date.now() - aoQuizAt < 30000 || !learnBtn || !learnBtn.cur) return;
  const z = aoQuizS().load(learnBtn.cur.topic); if (!z) { aoQuizFor(learnBtn.cur.topic); return; }
  const due = z.status === 'writing' || z.levelUpDue || (z.status === 'ready' && (z.examDue || aoQuizOfficialDue || Date.now() - (z.lastExamAt || 0) > 6 * 3600000));
  if (!due || !aoQuizGate()) return;
  aoQuizAt = Date.now(); const ctl = aoQuizCtl = new AbortController();
  aoQuizWork(z, ctl.signal).catch((e) => { if (!e || !e.paused) console.log('[alwayson] quiz', e); }).finally(() => { if (aoQuizCtl === ctl) aoQuizCtl = null; });
}
function aoStopQuiz() { if (aoQuizCtl) { try { aoQuizCtl.abort(); } catch (e) { /* gone */ } aoQuizCtl = null; } }
// ---- always-on v2, phase 7: the diary on ask + the sleep handoff (src/diary-ao.js) --------------------------------------------
const DiaryAO = require('./src/diary-ao');
function aoDiaryNote() {
  let text = DiaryAO.recap({ activity: aoState.activity, truth: aoTruth ? aoTruth.counts() : null, since: Date.now() - 24 * 3600000 });
  try { const sc = aoScientistObj ? aoScientistObj.recap(Date.now() - 24 * 3600000) : ''; const ns = aoState.activity.filter((x) => x.kind === 'notsure' && x.t >= Date.now() - 24 * 3600000);
    text += (sc ? '\n' + sc : '') + (ns.length ? '\nNot sure about ' + ns.length + ' thing' + (ns.length === 1 ? '' : 's') + ', e.g. "' + ns[ns.length - 1].text + '" (on my wonder list).' : '') + (aoCheckerObj ? '\n' + aoCheckerObj.reportLine() : ''); } catch (e) { /* diary still works */ }
  return '[Glim\'s diary for the last 24 hours. Ben asked what you did: tell him briefly, in plain words, from this log only; do not add anything it does not say.\n' + text + '\n] ';
}
// ---- imagining ahead, level 1 (src/imagine.js + SpeakOMeter.decideAhead): speak now, or wait ~5 min? ---------------------------------
// The guesser's predicted next app (and, when a time sense supplies it, the chance of a break soon) gives a few imagined futures; a
// say waits when waiting is clearly better, then is re-checked plainly ONCE (no lookahead), still under every code limit. Never urgent.
const ImagineMod = require('./src/imagine');
let aoDeferred = null;
let aoBreakSoon = () => null;   // a hook for a time sense: the chance Ben takes a break in the next ~5 min (null = unknown)
function aoSpeakAhead(d) {
  if (!aoMeter) return { speak: true };
  const ctx = aoContext({ urgent: !!d.urgent });
  if (d.urgent || store.getSettings().imagineAhead === false || aoDeferred) return aoMeter.decide(ctx);
  const r = aoMeter.decideAhead(ctx, ImagineMod.futures(ctx, { guesser: aoGuesser, breakSoon: () => aoBreakSoon(ctx) }));
  if (r.defer) { aoDeferred = { d, at: Date.now(), due: Date.now() + r.waitMs }; if (aoState) aoState.logActivity('waited', { p: Math.round(r.p * 100) / 100, pWait: Math.round(r.pWait * 100) / 100, text: String(d.say).slice(0, 80) }); }
  return r;
}
function aoDeferredTick() {
  const w = aoDeferred; if (!w || Date.now() < w.due) return;
  if (!aoLoop || !aoMeter || Date.now() - w.at > 20 * 60000) { aoDeferred = null; return; }   // too old now: dropped, never late
  if (aoLoop.gate()) return;                                                               // Ben busy / night / pressure: keep waiting (max 20 min)
  aoDeferred = null;
  if (!aoLoop.sayAllowed(w.d)) return;
  const r = aoMeter.decideAhead(aoContext({ urgent: !!w.d.urgent }), null, { noLookahead: true });
  if (!r.speak) { if (aoState) aoState.logActivity('waited', { dropped: true, p: Math.round(r.p * 100) / 100 }); return; }
  aoState.spoke(); aoSay(w.d.say, { ...w.d, why: (w.d.why || '') + ' (waited for a better moment)', features: r.x });
}
// what the nightly sleep may learn from: confirmed notes, corrections, surprises (never a maybe). Written as sleep starts.
function aoSleepHandoff() { if (!aoState) return null; return DiaryAO.writeHandoff(aoDir(), DiaryAO.sleepHandoff({ truth: aoTruth, surprises: aoState.surprises })); }
// ---- sleep insight (track T5: src/stuck.js + sleepmlx insight.py; toy lab premonition-sleeplab-t5) ----------------------------------
// Day: failed problems go on the stuck list (userData/alwayson-stuck.json). Night (the sleep app): related memories are mixed into K
// candidates and only those the executor / puzzle-generator truth confirms become sleep cards. Morning: solved entries leave, the rest
// fade; Glim tells Ben only if something clicked, through the speak-o-meter (aoWorthTelling -> aoMaybeShare). Setting stuckList: false = off.
const StuckMod = require('./src/stuck');
let aoStuckListObj = null;
const aoStuckList = () => aoStuckListObj || (aoStuckListObj = new StuckMod.StuckList({ dir: aoDir() }));
function aoStuckAdd(e) { if (!e || store.getSettings().stuckList === false) return; try { aoStuckList().add(e); } catch (err) { console.log('[alwayson] stuck list', err); } }
function aoStuckMorning() {
  if (sl.asleep || sl.waking) return;
  try { const line = aoStuckList().morning(StuckMod.readResults(aoDir())); if (line) { aoWorthTelling(line, 0.6); if (aoState) aoState.logActivity('sleep-part', { part: 'insight', line }); } } catch (e) { console.log('[alwayson] stuck morning', e); }
}
setInterval(aoStuckMorning, 60000).unref();
const AlwaysOnMod = require('./src/alwayson');
// start / stop what the consent asks for: the loop runs while always-on is on and any sense is on
function aoApply() {
  aoSetup();
  if (!aoLoop) aoLoop = new AlwaysOnMod.AlwaysOn({ senses: aoSenses, state: aoState, ask: aoAskSeeing,
    deliver: { say: aoSay, note: aoNote, learn: aoLearn },
    gates: { busy: aoBusy, pressure: () => AlwaysOnMod.macPressure(), night: aoNight },
    speakGate: (d) => aoSpeakAhead(d),
    context: (fresh) => aoLoopContext(fresh),   // feeling time + recall + patterns (Task B)
    log: (...a) => console.log('[alwayson]', ...a) });
  aoWatchHook(aoLoop);   // T6: a finished tick labels the watcher's seconds
  if (!E2E && aoSenses.anyEnabled()) aoLoop.start(); else aoLoop.stop();
  aoHearingApply();
}
// hearing: one always-on `deskhelper dictate` whose finished utterances become observations (src/hearing.js). Switching it on also
// pre-warms the local speech server in the background (its first load takes about 2 minutes). Calls and dictation own the mic:
// hearing pauses while they run and resumes after.
function getHearing() {
  return hearing || (hearing = new (require('./src/hearing').Hearing)({
    helper: () => (FEATURES.dictate && screen ? screen.findHelper() : null),
    sttUrl: () => sttUrl(),
    spawn: (cmd, args, url) => require('child_process').spawn(cmd, [...args, '--stt', url], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true }),
    onText: (text) => { if (aoSenses) aoSenses.push('hearing', 'Heard: ' + text); },
    onState: (st, why) => { if (st === 'error') console.log('[alwayson] hearing:', why); }
  }));
}
function aoHearingApply() {
  if (E2E) return;
  const want = !!(aoSenses && aoSenses.enabled('hearing'));
  if (want) getHearing().enable(); else if (hearing) hearing.disable();
}

const hp0 = (id) => !!(helpers && helpers.byThread(id));
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
  { const own = (e) => !!(ui && e && e.sender === ui.webContents);   // I5: only the app's own window may change a safety level
    ipcMain.handle('safety:get', () => ({ levels: glimSafety().levels(), hands: glimSafety().hands() }));
    ipcMain.handle('safety:set', (e, cat, level) => (own(e) ? glimSafety().set([{ cat, level }], { source: 'settings' }) : { ok: false }));
    ipcMain.handle('safety:undo', (e, token) => (own(e) ? glimSafety().undo(token, { source: 'settings' }) : { ok: false }));
    ipcMain.handle('safety:hands', (e, patch) => (own(e) ? glimSafety().setHands(patch, { source: 'settings' }) : { ok: false }));
    // LOGIN1 saved logins: only the app's own window; the list never holds a password
    ipcMain.handle('logins:list', (e) => (own(e) ? glimLogins().list() : []));
    ipcMain.handle('logins:remove', (e, origin) => (own(e) ? glimLogins().remove(origin) : { ok: false }));
    ipcMain.handle('logins:answer', (e, token, choice) => { if (!own(e)) return { ok: false }; glimLogins(); return loginCapture.answer(String(token || ''), String(choice || '')); });
    ipcMain.handle('logins:add', (e, site, user, password) => { if (!own(e)) return { ok: false }; const o = Logins.originFromInput(site); if (!o) return { ok: false, error: 'Type the site as https://… or just its name, like dresden.schoology.com.' }; return glimLogins().save(o, user, password); }); }
  h('threads:list', () => store.listThreads());
  // One Glim chat (Ben Oct 28): "new thread" hands back the existing main chat; only the very first run creates one.
  h('threads:new', () => { resetModelToDefault(); const old = (store.listThreads() || []).find((x) => !x.helper && x.title !== 'Call'); if (old) { const t = store.loadThread(old.id); if (t) { openThreadId = t.id; return t; } } const t = store.newThread(); store.saveThread(t); openThreadId = t.id; return t; });
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
  // like / dislike an answer (src/feedback.js): kept on the item and logged for sleep. A running thread is the live object, so its next save keeps the mark.
  h('threads:feedback', (id, answer, fb) => {
    if (helpers && helpers.byThread(id)) return { ok: false }; // a helper's log is not Ben's chat
    const live = agent && agent.running && activeThread && activeThread.id === id;
    const t = live ? activeThread : (helpers && helpers.liveThread(id)) || store.loadThread(id);
    const r = Feedback.rate(t, answer, fb);
    if (!r) return { ok: false };
    store.saveThread(t);
    try { Feedback.record(app.getPath('userData'), { ts: new Date().toISOString(), thread: id, fb, user: r.user, answer: r.answer }); } catch (e) { /* the mark is still on the thread */ }
    return { ok: true };
  });
  h('agent:send', async (threadId, text) => {
    text = Logins.scrub(String(text == null ? '' : text));   // LOGIN1: a saved password pasted here never reaches the model, the day log or sleep
    sl.lastActive = Date.now(); lastTyping = Date.now(); if (aoLoop) aoLoop.cancel('chat'); aoPool.stopAll('chat'); aoStopChecks(); aoStopQuiz(); aoSciEnd('chat');
    if (aoSenses && !hp0(threadId)) aoSenses.push('chats', 'Ben wrote: ' + String(text || '').slice(0, 300));
    if (!hp0(threadId)) { try { aoVoice.onBenChat(text); } catch (e) { /* feedback only */ } }
    if (!hp0(threadId)) glimSafetyFromBen(text, 'ben-chat');   // I5: only Ben's own typed words can change a safety level
    if (rollCtl) rollCtl.abort();   // Ben's turn gets the model
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
    if (!t.title || t.title === 'New thread') t.title = 'Glim'; // one Glim: no chat is named after its first message
    activeThread = t;
    // Ben Oct 28: "the chat should just never get slow". The local model serves one request at a time, so a Mote mid-reply would make his message wait: stop them now, they run again once he is done.
    if (store.getSettings().benFirst !== false && helpers && helpers.active.size) helpers.pauseForSleep('Paused so your chat stays fast; runs again when you are done');
    const goalsNote = goalsNoteFor(t, text), goals = !!goalsNote;
    // Learn mode: "go learn X" -> Glim asks how many Motes and for how long -> Ben's answer starts them.
    let learn = false, learnNote = LEARN_NOTE;
    if (!goals) {
      const flow = learnFlow({ pending: pendingLearn.get(t.id), text, isAsk: isLearnAsk(t, text), start: startLearn });
      if (flow.pending) pendingLearn.set(t.id, flow.pending); else pendingLearn.delete(t.id);
      if (flow.handled) { learn = true; learnNote = flow.note; }
    }
    // always-on v2: the diary is shown ONLY when Ben asks ("Glim, what did you do?"): a hidden note with the activity recap
    const diary = !goals && !learn && aoState && DiaryAO.isDiaryAsk(text) ? aoDiaryNote() : '';
    const timeNote = !goals && !learn && !diary ? aoTimeNote(text) : '';   // feeling time: a time question gets a hidden note from the timestamped records
    const loginNote = !goals && !learn && !diary && !timeNote ? await loginDialogFor(text, t.id).catch(() => '') : '';   // LOGIN1: "save my Schoology login" -> the masked dialog
    if (loginNote) { agent.run(t, loginNote + text, { display: text }).then(() => send('threads:changed', {})).catch((e) => send('agent', { threadId: t.id, type: 'error', message: String(e && e.message || e) })); return { started: true, title: t.title, loginDialog: true }; }
    agent.run(t, timeNote ? timeNote + text : goals ? goalsNote + text : learn ? learnNote + text : diary ? diary + text : text, goals || learn || diary ? { display: text } : timeNote ? { display: text } : undefined).then((r) => {
      send('threads:changed', {});
      if (!r.stopped && !chatInFront() && !(pillWin && pillWin.enabled)) notify('Glim finished', t.title, t.id);
    }).catch((e) => send('agent', { threadId: t.id, type: 'error', message: String(e && e.message || e) }));
    return { started: true, title: t.title };
  });
  h('learn:state', () => learnView());
  // Ben can peek at the locked quiz (questions, source answers, sources, scores)
  h('learn:quiz', (topic) => { const t = topic || (learnBtn && learnBtn.cur && learnBtn.cur.topic); const z = t ? aoQuizS().load(t) : null; return z ? { topic: z.topic, status: z.status, line: QuizMod.scoreLine(z), levels: z.levels.map((l) => ({ level: l.level, questions: l.questions.map((q) => ({ q: q.q, answer: q.answer, source: q.source_url })) })), scores: (z.scores || []).slice(-20) } : null; });
  h('learn:start', (topic) => getLearnBtn().start(topic));
  h('learn:stop', () => getLearnBtn().stop());
  h('senses:get', () => sensesView());
  h('senses:set', (patch) => setSenses(patch || {}));
  h('senses:askPerms', () => askSensesPerms());
  h('alwayson:feedback', (id, kind) => { const m = aoVoice.feedback(id, ['up', 'down', 'used'].includes(kind) ? kind : 'down'); return { ok: !!m }; });
  ipcMain.on('alwayson:typing', () => { lastTyping = Date.now(); if (aoLoop) aoLoop.cancel('typing'); aoPool.stopAll('typing'); aoStopChecks(); aoStopQuiz(); });
  h('call:start', () => startCall());
  h('call:stop', () => { if (call) call.hangup(); return true; });
  h('call:mute', (m) => { if (call) call.setMuted(m); return true; });
  h('dictate:start', () => startDictate());
  h('dictate:stop', () => { stopDictate(false); return true; });
  h('watchme:start', () => watchStart());
  h('watchme:stop', (name) => watchStop(name));
  h('watchme:list', () => skillStore().list().map((s) => ({ id: s.id, name: s.name, created: s.created, steps: s.steps.length, text: s.text })));
  h('watchme:redo', (id) => watchRedo(id));
  h('watchme:remove', (id) => skillStore().remove(id));
  // Stop in the Call chat stops the call's own agent, not a task running in the main chat
  h('agent:stop', (threadId) => { const hp = threadId && helpers.byThread(threadId); if (hp) helpers.abort(hp.id); else if (callAgent && threadId && callAgent.threadId === threadId) callAgent.stop(); else agent.stop(); return true; });
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
  h('memory:write', (text, expectedText) => memory.write(text, expectedText));
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
  // the "Important updates" dashboard: built fresh from the files each time it is asked (read-only; src/dashboard.js)
  h('dashboard:get', () => dashboardModel());
  // "Put all back" on the hidden-junk row (and its undo): a correction saved in userData/dashboard-overrides.json; mail itself is never touched
  h('dashboard:override', (op, keys) => DashOver.apply(app.getPath('userData'), op, keys));
  // "Learn" button: a Mote goes off to study a topic quietly; sleep trains its notes and fact cards in overnight.
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
    const urls = { accessibility: 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility', screen: 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture', microphone: 'x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone', automation: 'x-apple.systempreferences:com.apple.preference.security?Privacy_Automation' };
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
    if (name !== 'hover' && name !== 'fence') sl.lastActive = Date.now();
    switch (name) {
      case 'hover': if (pillWin) pillWin.setInteractive(!!arg); break;
      case 'fence': if (pillWin) pillWin.setFence(arg); break;
      case 'open': { showWindow(); if (arg && arg.threadId) send('open-thread', arg.threadId); if (arg && arg.key) pillState.dismiss(arg.key); break; }
      case 'stop': if (arg === 'main') agent.stop(); else if (arg === 'call') { if (callAgent) callAgent.stop(); } else helpers.abort(arg); break;
      case 'respond': { const r = pending.get(arg.rid); if (r) { pending.delete(arg.rid); r(arg.value); send('agent', { threadId: arg.threadId, type: 'resolved', rid: arg.rid, value: arg.value }); } break; }
      case 'openBrowser': { const pa = [...pillState.agents.values()].find((x) => x.key === arg); const key = pa && pa.threadId; if (key && browsers.has(key)) { showWindow(); send('browser-show', { key, threadId: key, login: loginWaits.has(key) }); } break; }
      case 'dismiss': pillState.dismiss(arg); break;
      case 'aoSay': { if (!arg) break; aoVoice.feedback(arg.id, arg.kind); if (arg.key) pillState.dismiss(arg.key); if (arg.kind === 'used') { showWindow(); const id = mainChatId(); if (id) send('open-thread', id); } break; }
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
app.on('before-quit', () => { console.log('[app] quitting'); quitting = true; if (FEATURES.sleep && store) syncNightStart(); try { call && call.hangup(); } catch (e) { /* ignore */ } try { stopDictate(true); } catch (e) { /* ignore */ } try { sttSrv && sttSrv.stop(); } catch (e) { /* ignore */ } try { builtin && builtin.stop(); } catch (e) { /* ignore */ } });
app.on('will-quit', () => { try { globalShortcut.unregisterAll(); } catch (e) { /* ignore */ } });

app.whenReady().then(async () => {
  if (!gotLock) return;
  applyPresetDefaults(Platform.defaultPreset(process.platform, PLATFORM_OPTS));
  store = new Store(app.getPath('userData'));
  memory = createMemory(app.getPath('userData'));
  tracking = createTracking(app.getPath('userData'));
  rhythm = new Rhythm(path.join(app.getPath('userData'), 'rhythm.json'));
  try { powerMonitor.on('resume', () => urlGuard.clear()); } catch (e) { /* not on this platform */ }   // a dead site before the Mac slept may be back
  // opened by the night-start agent: Ben was not just here, so the away-time is the Mac's idle time, not "since launch"
  if (process.argv.includes(NIGHT_ARG)) {
    // launchd runs a missed start when the Mac wakes, which can be the next morning: outside the night window it closes again
    const s = store.getSettings(), w = effectiveWindow(s, learnedNow(new Date()));
    if (s.autoSleep === false || !inWindow(new Date(), w.from, w.to)) { console.log('[app] opened for the night (' + NIGHT_ARG + ') outside ' + w.from + '-' + w.to + ', closing'); app.quit(); return; }
    try { sl.lastActive = Date.now() - powerMonitor.getSystemIdleTime() * 1000; } catch (e) { /* keep launch time */ }
    console.log('[app] opened for the night (' + NIGHT_ARG + ')');
  }
  if (FEATURES.builtin || process.env.PREMONITION_BUILTIN) setupBuiltin(); else sleeper = new Sleep({ getSettings: () => store.getSettings(), home: E2E ? path.join(app.getPath('userData'), 'sleepmode') : undefined });
  if (E2E) e2eEnv = await require('./test/e2e.js').prepare(store);
  resetModelToDefault();
  applyTheme(store.getSettings());
  diary = new Diary(() => store.getSettings());
  buildMenu();
  if (FEATURES.tray && Platform.startedHidden(process.platform, process.argv)) ensureTray();
  buildAgent();
  registerIpc();
  try { glimLogins(); } catch (e) { /* LOGIN1: no saved logins this run */ }
  updater = new Updater({ version: app.getVersion(), platform: process.platform, arch: process.arch, execPath: process.execPath, pid: process.pid, packaged: app.isPackaged && !E2E,
    onState: (st) => send('update:state', st), quit: () => { quitting = true; app.quit(); } });
  if (app.isPackaged && !E2E && store.getSettings().autoUpdateCheck !== false) updater.startTimer(30000);
  startDashboardWatch();
  createWindow(); // shown on ready-to-show; diary, helpers, warm-up, pill, hotkey start after that (afterFirstPaint)
});

app.on('window-all-closed', () => { try { if (hearing) hearing.disable(); if (aoLoop) aoLoop.stop(); } catch (e) { /* ignore */ } try { helpers && helpers.close(); } catch (e) { /* ignore */ } try { diary && diary.stop(); } catch (e) { /* ignore */ } app.quit(); });
