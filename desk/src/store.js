'use strict';
const fs = require('fs');
const path = require('path');

const DEFAULT_SETTINGS = {
  gatewayUrl: 'http://127.0.0.1:8090/v1',
  model: 'qwen36-auto',
  maxSteps: 40,
  mode: 'ask',            // ask | hands-off
  vision: 'off',          // off | on
  diaryPath: '',          // path to diary_mcp.py ('' = ~/learner-ops/assistant/diary_mcp.py)
  pythonPath: '',         // '' = ~/learner-ops/.venv/bin/python if present, else python3
  helperPath: ''          // '' = bundled deskhelper
};

class Store {
  constructor(dir) {
    this.dir = dir;
    this.threadsDir = path.join(dir, 'threads');
    this.settingsFile = path.join(dir, 'settings.json');
    fs.mkdirSync(this.threadsDir, { recursive: true });
  }
  getSettings() {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(fs.readFileSync(this.settingsFile, 'utf8')) };
    } catch (e) { return { ...DEFAULT_SETTINGS }; }
  }
  saveSettings(patch) {
    const cur = this.getSettings();
    const next = { ...cur, ...patch };
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
        out.push({ id: t.id, title: t.title, updated: t.updated, created: t.created });
      } catch (e) { /* skip corrupt */ }
    }
    return out.sort((a, b) => b.updated - a.updated);
  }
  renameThread(id, title) {
    const t = this.loadThread(id);
    if (t) { t.title = String(title).slice(0, 80) || t.title; this.saveThread(t); }
  }
}

module.exports = { Store, DEFAULT_SETTINGS };
