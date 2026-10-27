'use strict';
const fs = require('fs');
const path = require('path');

const DEFAULT_SETTINGS = {
  // Model
  gatewayUrl: 'http://127.0.0.1:8090/v1',
  model: 'qwen36-auto',   // qwen36-auto | qwen36 | qwen36-fast
  // Autonomy
  mode: 'ask',            // ask | hands-off (main agent)
  helperMode: 'hands-off', // autonomy for helper agents
  maxSteps: 40,
  // Helpers
  maxParallel: 2,         // model runs at once (primary + helpers)
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
  highContrast: false,    // stronger text and borders
  pill: true,             // the always-on-top status pill at the top of the screen
  // Startup
  openAtLogin: false,
  keepRunning: true,      // closing the window hides it; the app (and helpers) keep running
  hotkey: 'Alt+Space'     // global shortcut that toggles the window ('' = off)
};

const ENUMS = {
  model: null, // free text on purpose (a custom model name is allowed)
  mode: ['ask', 'hands-off'], helperMode: ['ask', 'hands-off'], vision: ['off', 'on'],
  theme: ['system', 'light', 'dark'], textSize: ['s', 'm', 'l']
};
const BOOLS = ['diaryEnabled', 'openAtLogin', 'keepRunning', 'pill', 'highContrast'];
const NUMS = { maxSteps: [1, 200], maxParallel: [1, 4] };
const STRS = ['gatewayUrl', 'model', 'diaryPath', 'pythonPath', 'helperPath', 'hotkey'];

// Keep only known keys with sane values (bad values fall back to the default).
function sanitize(patch) {
  const out = {};
  for (const [k, v] of Object.entries(patch || {})) {
    if (!(k in DEFAULT_SETTINGS)) continue;
    if (BOOLS.includes(k)) out[k] = !!v;
    else if (NUMS[k]) { const n = Math.round(Number(v)); out[k] = Number.isFinite(n) ? Math.min(NUMS[k][1], Math.max(NUMS[k][0], n)) : DEFAULT_SETTINGS[k]; }
    else if (ENUMS[k]) out[k] = ENUMS[k].includes(v === true ? 'on' : v) ? (v === true ? 'on' : v) : DEFAULT_SETTINGS[k];
    else if (STRS.includes(k)) out[k] = String(v == null ? '' : v).trim() || (k === 'gatewayUrl' || k === 'model' ? DEFAULT_SETTINGS[k] : '');
  }
  return out;
}

class Store {
  constructor(dir) {
    this.dir = dir;
    this.threadsDir = path.join(dir, 'threads');
    this.settingsFile = path.join(dir, 'settings.json');
    fs.mkdirSync(this.threadsDir, { recursive: true });
  }
  getSettings() {
    try {
      const raw = JSON.parse(fs.readFileSync(this.settingsFile, 'utf8'));
      if (raw.vision === true) raw.vision = 'on';
      return { ...DEFAULT_SETTINGS, ...raw };
    } catch (e) { return { ...DEFAULT_SETTINGS }; }
  }
  saveSettings(patch) {
    const cur = this.getSettings();
    const next = { ...cur, ...sanitize(patch) };
    fs.writeFileSync(this.settingsFile, JSON.stringify(next, null, 2));
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

module.exports = { Store, DEFAULT_SETTINGS, sanitize };
