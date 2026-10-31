'use strict';
const fs = require('fs');
const path = require('path');

const Platform = require('../renderer/platform');

const DEFAULT_SETTINGS = {
  // Model
  modelStartCmd: '',      // run when the Offline chip is clicked; empty = the Mac assistant's serve.sh if present
  gatewayUrl: Platform.defaultPreset(process.platform).gatewayUrl, // Windows: the built-in model
  model: Platform.defaultPreset(process.platform).model,   // the model id in use (one of the three below, or a custom name)
  modelAuto: Platform.defaultPreset(process.platform).modelAuto, // the ids behind the Auto / Think / Fast pills (all "default" on a llama.cpp server)
  modelMain: Platform.defaultPreset(process.platform).modelMain,
  modelFast: Platform.defaultPreset(process.platform).modelFast, // also used for the warm-up and the self-check
  // Backend-private options: no UI controls. Deployment sets the family only after
  // the configured endpoint serves a supported family; other models skip the scratchpad.
  backendModelFamily: '',
  creativeProposer: true,
  creativeDeadlineMs: 12000,
  // Autonomy
  modelDefault: 'modelFast', // Oct 28: the Auto router's judge call alone took 9-60 s before the first token; Fast answers at once, Think is one tap away. Which pill (modelAuto | modelMain | modelFast) each launch and each new thread starts on; the top-bar pills only change the current one
  mode: 'ask',            // ask | hands-off (main agent)
  morningPrep: true,      // one preparation card after the morning Organizer
  followUp: true,         // once a day, when Ben opens the chat, Glim checks on what he left open and offers clickable choices
  ideaJudgeDay: '',       // the day (YYYY-MM-DD) the Motes' ideas were last judged
  followupDay: '',        // the day (YYYY-MM-DD) that follow-up last ran
  verify: true,           // double-check state-changing work before saying done (one extra, quick model call)
  helperMode: 'hands-off', // autonomy for helper agents
  maxSteps: 0,            // model calls per task before Glim stops and asks; 0 = no limit (Ben Oct 28: threads are unlimited)
  stepsPlan: 2,           // settings migration marker: 1 = the old 40-step default moved to no limit; 2 = runs at once moved to no limit
  contextTokens: Platform.defaultPreset(process.platform).contextTokens, // past this the model reads a summary of the older part of a chat plus the recent part (agent.js trimWindow)
  compactTokens: Platform.defaultPreset(process.platform).compactTokens, // history size that triggers compaction (small local models have small context)
  maxToolChars: Platform.defaultPreset(process.platform).maxToolChars,
  // Helpers
  maxParallel: 0,         // model runs at once (primary + helpers); 0 = no limit
  // Memory
  diaryEnabled: true,
  diaryPath: '',          // path to diary_mcp.py ('' = ~/learner-ops/assistant/diary_mcp.py)
  pythonPath: '',         // '' = ~/learner-ops/.venv/bin/python if present, else python3
  // Screen control
  helperPath: '',         // '' = bundled deskhelper
  // Vision
  vision: 'off',          // off | on
  // Appearance
  theme: 'system',        // system | light | dark
  textSize: 'm',          // s | m | l
  alwaysAllow: [],       // actions Ben chose "Always allow" for: 'shell:<program>' and 'screen' (never risky commands)
  goalsAsked: false,     // Glim has asked about long-term goals once, right after first-run setup
  autoUpdateCheck: true, // look for a newer Premonition at launch and every 5 minutes (an update still needs your click)
  showSparks: false,     // list Motes (helpers) in a side panel and let you read their logs (view only; you cannot talk to them)
  highContrast: false,    // stronger text and borders
  onboarded: false,       // first-run setup (Meet your Glims) has been finished or skipped
  uses: [],               // what Ben wants Glims for (ids from renderer/uses.js)
  usesOther: '',          // free text "something else"
  permsSeen: false,       // the Permissions card has been shown once on first launch
  onboardAt: '',          // 'perms' = setup reached its Permissions page (macOS makes you quit and reopen after a switch; setup resumes there)
  pill: true,             // the always-on-top status pill at the top of the screen
  // Sleep (the separate sleepmode app trains on the diary while Glim is idle)
  sleepApp: '',           // '' = ~/learner-ops/sleepmode/app
  sleepPython: '',        // '' = first of sleepmode/venv312, learner-ops/.venv, homebrew python3, python3
  benFirst: true,         // Glims wait while Ben's chat is busy (or was, in the last 2 min) so his chat keeps the local model
  sleepPauseGlims: true,  // hold the Glims' scheduled runs while asleep (they catch up once after wake)
  autoSleep: true,        // sleep by itself at night when idle (Ben Oct 28: on by default)
  sleepPlan: 2,           // settings migration marker: 2 = the 23:00-08:00 / 2 h idle / adaptive plan
  sleepFrom: Platform.defaultSleepWindow(process.platform)[0], // night window start (HH:MM); 23:00 by default (until the routine is learned)
  sleepTo: Platform.defaultSleepWindow(process.platform)[1],   // night window end; 08:00 by default
  sleepOnlyPlugged: process.platform === 'win32', // never start a sleep on battery (Windows laptops: sleep is slow and power hungry)
  sleepAdapt: true,       // fit the night window to Ben's routine (src/rhythm.js); off = the sleepFrom/sleepTo window as set
  sleepIdleMin: 120,      // minutes without use before auto-sleep
  sleepDuration: 'morning', // last pick in the sleep sheet: 30 | 60 | 120 | 240 | morning | open
  sleepCheckinMins: 60,   // Windows: the hourly check-in while asleep
  sleepCheckinTask: require('./checkin').DEFAULT_TASK, // what the hourly check-in does (empty = this default)
  awakeCheckinMins: 30,   // quick check-in every N minutes while Glim is awake and you are away from the chat (0 = off)
  wakeAt: false,          // wake at the end of the window (only for a sleep Desk started by itself)
  // Startup
  openAtLogin: false,
  keepRunning: true,      // closing the window hides it; the app (and helpers) keep running
  hotkey: Platform.defaultHotkey(process.platform) // global shortcut that toggles the window ('' = off); Ctrl+Space on Windows
};

const ENUMS = {
  model: null, // free text on purpose (a custom model name is allowed)
  backendModelFamily: ['', 'apex35b', 'lfm3'],
  mode: ['ask', 'hands-off'], helperMode: ['ask', 'hands-off'], vision: ['off', 'on'],
  theme: ['system', 'light', 'dark'], textSize: ['s', 'm', 'l'], onboardAt: ['', 'perms']
};
const BOOLS = ['onboarded', 'permsSeen', 'diaryEnabled', 'openAtLogin', 'keepRunning', 'pill', 'highContrast', 'showSparks', 'autoUpdateCheck', 'goalsAsked', 'verify', 'followUp', 'morningPrep', 'benFirst', 'sleepPauseGlims', 'sleepOnlyPlugged', 'autoSleep', 'sleepAdapt', 'wakeAt', 'creativeProposer'];
const NUMS = { compactTokens: [1500, 200000], contextTokens: [1500, 400000], maxToolChars: [500, 20000], maxSteps: [0, 1000], maxParallel: [0, 64], sleepIdleMin: [1, 720], sleepCheckinMins: [10, 720], awakeCheckinMins: [0, 720], creativeDeadlineMs: [1, 15000] };
const TIMES = ['sleepFrom', 'sleepTo'];
const DURATION_PICKS = ['30', '60', '120', '240', 'morning', 'open'];
const cleanTime = (v, d) => { const m = /^(\d{1,2}):(\d{2})$/.exec(String(v == null ? '' : v).trim()); return m && +m[1] < 24 && +m[2] < 60 ? String(+m[1]).padStart(2, '0') + ':' + m[2] : d; };
const STRS = ['modelDefault', 'modelStartCmd', 'gatewayUrl', 'model', 'modelAuto', 'modelMain', 'modelFast', 'diaryPath', 'pythonPath', 'helperPath', 'hotkey', 'sleepApp', 'sleepPython', 'sleepCheckinTask', 'followupDay', 'ideaJudgeDay'];
const { cleanUses } = require('../renderer/uses');
const USES_OTHER_MAX = 200;

// Keep only known keys with sane values (bad values fall back to the default).
function sanitize(patch) {
  const out = {};
  for (const [k, v] of Object.entries(patch || {})) {
    if (!(k in DEFAULT_SETTINGS)) continue;
    if (BOOLS.includes(k)) out[k] = !!v;
    else if (NUMS[k]) { const n = Math.round(Number(v)); out[k] = Number.isFinite(n) ? Math.min(NUMS[k][1], Math.max(NUMS[k][0], n)) : DEFAULT_SETTINGS[k]; }
    else if (ENUMS[k]) out[k] = ENUMS[k].includes(v === true ? 'on' : v) ? (v === true ? 'on' : v) : DEFAULT_SETTINGS[k];
    else if (k === 'alwaysAllow') out[k] = (Array.isArray(v) ? v : []).map((x) => String(x)).filter((x) => /^[\w:.\/+-]{1,60}$/.test(x)).slice(0, 60);
    else if (k === 'uses') out[k] = cleanUses(v);
    else if (k === 'usesOther') out[k] = String(v == null ? '' : v).replace(/\s+/g, ' ').trim().slice(0, USES_OTHER_MAX);
    else if (k === 'sleepDuration') out[k] = DURATION_PICKS.includes(String(v)) ? String(v) : DEFAULT_SETTINGS[k];
    else if (TIMES.includes(k)) out[k] = cleanTime(v, DEFAULT_SETTINGS[k]);
    else if (STRS.includes(k)) out[k] = String(v == null ? '' : v).trim() || (['gatewayUrl', 'model', 'modelAuto', 'modelMain', 'modelFast'].includes(k) ? DEFAULT_SETTINGS[k] : '');
  }
  return out;
}

// The model defaults depend on the machine (Windows and Macs without Ben's assistant start on the built-in model). main.js calls this
// once, before the first Store is made, with Platform.defaultPreset(process.platform, {hasLocalAssistant}). A saved settings.json still wins.
function applyPresetDefaults(preset) {
  for (const k of ['gatewayUrl', 'model', 'modelAuto', 'modelMain', 'modelFast', 'compactTokens', 'contextTokens', 'maxToolChars']) if (preset && preset[k] !== undefined) DEFAULT_SETTINGS[k] = preset[k];
}

class Store {
  constructor(dir) {
    this.dir = dir;
    this.threadsDir = path.join(dir, 'threads');
    this.settingsFile = path.join(dir, 'settings.json');
    fs.mkdirSync(this.threadsDir, { recursive: true });
  }
  // settings.json is written atomically (tmp + rename) with the previous good copy kept as settings.json.bak. If the file is ever
  // unreadable (a crash or a quit in the middle of an older, non-atomic write) the backup is used, never the defaults:
  // falling back to defaults meant onboarded=false, so the first-run setup came back after a restart.
  _readSettings() {
    for (const f of [this.settingsFile, this.settingsFile + '.bak']) {
      try { const raw = JSON.parse(fs.readFileSync(f, 'utf8')); if (raw && typeof raw === 'object') return raw; } catch (e) { /* try the next copy */ }
    }
    return null;
  }
  getSettings() {
    try {
      const raw = this._readSettings();
      if (!raw) return { ...DEFAULT_SETTINGS, uses: [] };
      if (raw.vision === true) raw.vision = 'on';
      // Ben Oct 28: sleep by itself after 2 h idle, 23:00-08:00, then fit his routine. Settings files from before that move onto the plan once;
      // anything he changes in Settings afterwards sticks (sleepPlan marks the migration as done).
      if ((raw.sleepPlan || 0) < 2) {
        const w = Platform.defaultSleepWindow(process.platform);
        Object.assign(raw, { autoSleep: true, sleepAdapt: true, sleepFrom: w[0], sleepTo: w[1], sleepIdleMin: 120, sleepPlan: 2 });
      }
      // Ben Oct 28: threads and concurrent Glims are unlimited. Old settings files carry the old caps (40 steps, 2 or 4 runs at once): drop them once;
      // a number Ben picks in Settings afterwards sticks.
      if ((raw.stepsPlan || 0) < 1 && raw.maxSteps === 40) raw.maxSteps = 0;
      if ((raw.stepsPlan || 0) < 2) { raw.maxParallel = 0; raw.stepsPlan = 2; }
      return { ...DEFAULT_SETTINGS, ...raw, uses: cleanUses(raw.uses) };
    } catch (e) { return { ...DEFAULT_SETTINGS, uses: [] }; }
  }
  saveSettings(patch) {
    const cur = this.getSettings();
    const next = { ...cur, ...sanitize(patch) };
    const tmp = this.settingsFile + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(next, null, 2));
    try { JSON.parse(fs.readFileSync(this.settingsFile, 'utf8')); fs.copyFileSync(this.settingsFile, this.settingsFile + '.bak'); } catch (e) { /* the main file is missing or broken: keep the good .bak */ }
    fs.renameSync(tmp, this.settingsFile);
    return next;
  }
  _file(id) { return path.join(this.threadsDir, String(id).replace(/[^\w\-]/g, '') + '.json'); }
  newThread() {
    const id = 't' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const t = { id, title: 'New thread', created: Date.now(), updated: Date.now(), messages: [], items: [] };
    return t;
  }
  saveThread(t) {
    t.updated = Date.now();
    const f = this._file(t.id);
    const tmp = f + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(t));
    fs.renameSync(tmp, f);
  }
  // Change a stored thread in the background without marking it active (keeps `updated`: follow-ups and the chat list read it).
  // fn changes the loaded copy, or returns false to skip the write.
  patchThread(id, fn) {
    const t = this.loadThread(id);
    if (!t || fn(t) === false) return t;
    const f = this._file(t.id), tmp = f + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(t));
    fs.renameSync(tmp, f);
    return t;
  }
  loadThread(id) {
    try { return JSON.parse(fs.readFileSync(this._file(id), 'utf8')); } catch (e) { return null; }
  }
  deleteThread(id) { try { fs.unlinkSync(this._file(id)); } catch (e) { /* ignore */ } }
  listThreads() {
    const out = [];
    for (const f of fs.readdirSync(this.threadsDir)) {
      if (!f.endsWith('.json')) continue;
      try {
        const t = JSON.parse(fs.readFileSync(path.join(this.threadsDir, f), 'utf8'));
        out.push({ id: t.id, title: t.title, updated: t.updated, created: t.created, helper: t.helper || null });
      } catch (e) { /* skip corrupt */ }
    }
    return out.sort((a, b) => b.updated - a.updated);
  }
  renameThread(id, title) {
    const t = this.loadThread(id);
    if (t) { t.title = String(title).slice(0, 80) || t.title; this.saveThread(t); }
  }
}

module.exports = { Store, DEFAULT_SETTINGS, sanitize, applyPresetDefaults };
