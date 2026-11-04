'use strict';
// "Important updates" dashboard: the FILES side. Reads (never writes) what the sleep app and the desk already keep, and hands
// buildDashboard() plain data. Every source is optional: a missing file just means that card is absent.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { buildDashboard } = require('./dashboard');

const readText = (f, max) => {
  try {
    const st = fs.statSync(f);
    if (!max || st.size <= max) return fs.readFileSync(f, 'utf8');
    const fd = fs.openSync(f, 'r');   // only the end of a big log
    try { const b = Buffer.alloc(max); fs.readSync(fd, b, 0, max, st.size - max); return b.toString('utf8').replace(/^[^\n]*\n/, ''); } finally { fs.closeSync(fd); }
  } catch (e) { return ''; }
};
const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { return null; } };
const jsonLines = (text, keep) => text.split('\n').map((l) => { try { return l.trim() ? JSON.parse(l) : null; } catch (e) { return null; } }).filter(Boolean).slice(-keep);
const mtime = (f) => { try { return fs.statSync(f).mtimeMs; } catch (e) { return NaN; } };

// the newest premonition-research-*.noindex/bedwars/STATUS.md next to the sleep folders (optional one-line FYI)
function bedwarsFyi(ops) {
  try {
    const dirs = fs.readdirSync(ops).filter((n) => /^premonition-research-\d+\.noindex$/.test(n)).sort().reverse();
    for (const d of dirs) {
      const f = path.join(ops, d, 'bedwars', 'STATUS.md');
      const t = mtime(f);
      if (!Number.isFinite(t)) continue;
      const when = new Date(t).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      return [{ id: 'bedwars', icon: 'game', title: 'Bedwars bot project', line: 'Its notes were last updated ' + when + '. Nothing for you to do.' }];
    }
  } catch (e) { /* none */ }
  return [];
}

// where the files are: the sleep app's home (status.json, summary.md, inbox.md, events.jsonl) and its trainer's folder (nights.jsonl)
function paths(home, env) {
  env = env || process.env;
  const ops = path.dirname(home);
  const mlx = env.SLEEPMLX_HOME ? env.SLEEPMLX_HOME.replace(/^~(?=$|[\\/])/, os.homedir()) : path.join(ops, 'sleepmlx');
  return { home, ops, mlx, files: [path.join(home, 'summary.md'), path.join(home, 'inbox.md'), path.join(home, 'events.jsonl'), path.join(home, 'status.json'), path.join(mlx, 'nights.jsonl')] };
}

// o: { home, tracked: () => [...], contacts?: () => [...], overrides?: () => ({notJunk:[..]}), env?, now? } -> the input for buildDashboard
function readInput(o) {
  const p = paths(o.home, o.env);
  let tracked = []; try { tracked = (o.tracked && o.tracked()) || []; } catch (e) { /* no list */ }
  let contacts = []; try { contacts = (o.contacts && o.contacts()) || []; } catch (e) { /* none */ }
  let overrides = { notJunk: [] }; try { overrides = (o.overrides && o.overrides()) || overrides; } catch (e) { /* none */ }
  return {
    now: o.now || Date.now(),
    summary: readText(path.join(p.home, 'summary.md'), 200000),
    inbox: readText(path.join(p.home, 'inbox.md'), 400000),
    events: jsonLines(readText(path.join(p.home, 'events.jsonl'), 400000), 2000),
    status: readJson(path.join(p.home, 'status.json')) || {},
    nights: jsonLines(readText(path.join(p.mlx, 'nights.jsonl'), 400000), 30),
    tracked, contacts, overrides, user: o.user || '',
    fyi: bedwarsFyi(p.ops)
  };
}

const getDashboard = (o) => buildDashboard(readInput(o));

// Calls onChange() (debounced) when any source file changes. Two ways, because file-watch events are sometimes dropped:
// fs.watch on the folders (a file that is replaced would lose a file watch) plus a cheap look at the files' size and
// modified time every pollMs (default 5 s). Returns stop(). Never throws: a folder that is not there is simply not watched.
function watchSources(o, onChange) {
  const p = paths(o.home, o.env);
  const names = new Set(p.files.map((f) => path.basename(f)));
  const wait = o.debounceMs == null ? 1500 : o.debounceMs;
  const stamp = () => p.files.map((f) => { try { const st = fs.statSync(f); return st.size + ':' + st.mtimeMs; } catch (e) { return '-'; } }).join('|');
  let last = stamp(), timer = null, poll = null; const ws = [];
  const fire = (_ev, name) => {
    if (name && !names.has(String(name))) return;
    clearTimeout(timer); timer = setTimeout(() => { last = stamp(); try { onChange(); } catch (e) { /* ignore */ } }, wait);
    if (timer.unref) timer.unref();
  };
  for (const dir of new Set([p.home, p.mlx])) { try { const w = fs.watch(dir, fire); w.on('error', () => {}); ws.push(w); } catch (e) { /* folder missing */ } }
  poll = setInterval(() => { const now = stamp(); if (now !== last) { last = now; fire(null, null); } }, o.pollMs || 5000);
  if (poll.unref) poll.unref();
  return () => { clearTimeout(timer); clearInterval(poll); for (const w of ws) { try { w.close(); } catch (e) { /* ignore */ } } };
}

module.exports = { readInput, getDashboard, watchSources, paths, bedwarsFyi };
