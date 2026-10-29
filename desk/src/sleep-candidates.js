'use strict';
// Immutable candidate generations; only a fully checked, atomically published
// manifest may make one visible to ordinary chat or hourly check-ins.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const C = require('./runtime/constants');
const read = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) { return null; } };
const hash = (data) => crypto.createHash('sha256').update(data).digest('hex');
function fileHash(p) {
  const digest = crypto.createHash('sha256'), buffer = Buffer.allocUnsafe(1024 * 1024), fd = fs.openSync(p, 'r');
  try { let n; while ((n = fs.readSync(fd, buffer, 0, buffer.length, null)) > 0) digest.update(buffer.subarray(0, n)); }
  finally { fs.closeSync(fd); }
  return digest.digest('hex');
}
function atomic(p, value) {
  const temp = p + '.tmp-' + crypto.randomUUID();
  let fd;
  try {
    fd = fs.openSync(temp, 'wx', 0o600);
    fs.writeFileSync(fd, JSON.stringify(value, null, 2));
    fs.fsyncSync(fd); fs.closeSync(fd); fd = undefined;
    fs.renameSync(temp, p);
    // Windows cannot portably open a directory for fsync through Node. On
    // POSIX, sync the directory entry after the atomic rename as well.
    if (process.platform !== 'win32') {
      const dir = fs.openSync(path.dirname(p), 'r');
      try { fs.fsyncSync(dir); } finally { fs.closeSync(dir); }
    }
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    try { fs.unlinkSync(temp); } catch (_) {}
  }
}
function baseIdentity(root, hfDir) {
  try {
    const model = read(path.join(root, 'runtime', 'state.json')).model;
    const stat = fs.statSync(model.file);
    if (!stat.isFile() || !model.name || !model.sha256 || !/^[0-9a-f]{64}$/i.test(model.sha256)) return null;
    const config = path.join(hfDir, 'config.json');
    const configData = read(config); if (!configData || configData.model_type !== 'lfm3') return null;
    const files = fs.readdirSync(hfDir).filter(n => /\.(?:safetensors|bin)$/.test(n)).sort().map(n => {
      const f = fs.statSync(path.join(hfDir, n)); if (!f.isFile() || !f.size) throw new Error('Invalid source weight');
      return { name: n, size: f.size, mtime_ms: f.mtimeMs };
    });
    if (!files.length) return null;
    const revision = path.basename(fs.realpathSync(hfDir));
    return { repo: C.SLEEP_HF_REPO, gguf_name: model.name, gguf_sha256: model.sha256.toLowerCase(), gguf_size: stat.size, gguf_mtime_ms: stat.mtimeMs,
      hf_config_sha256: fileHash(config), hf_revision: /^[0-9a-f]{40}$/i.test(revision) ? revision.toLowerCase() : null, hf_weights: files };
  } catch (_) { return null; }
}
function sameBase(a, b) { return !!a && !!b && JSON.stringify(a) === JSON.stringify(b); }
function validMetrics(v, heldCount) {
  if (!v || !Number.isInteger(heldCount) || heldCount < 1) return false;
  if (!Number.isInteger(v.general_n) || v.general_n !== 8 || !Number.isInteger(v.held_n) || v.held_n !== heldCount) return false;
  for (const [k, n] of [['general_on',v.general_n],['general_off',v.general_n],['held_on',v.held_n],['held_off',v.held_n]])
    if (!Number.isInteger(v[k]) || v[k] < 0 || v[k] > n) return false;
  return true;
}
function validVerdict(v, heldCount) {
  if (!validMetrics(v, heldCount) || v.ok !== true || v.pending || v.processStopped !== true || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v.checkId || '')) return false;
  return v.general_on >= v.general_off - 1 && !(v.general_on * 2 < v.general_off) && v.held_on >= v.held_off;
}

// Night number is persisted in the trainer state; diary day indices can shift.
// A restored/reset state that disagrees with the date is incomparable, not newer.
function orderKey(rec) {
  if (!rec || !Number.isSafeInteger(rec.night_number) || rec.night_number < 1 ||
      typeof rec.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(rec.date) ||
      typeof rec.created !== 'string' || !/^[a-f0-9]{64}$/.test(rec.id || '')) return null;
  const d = new Date(rec.date + 'T00:00:00.000Z'), t = new Date(rec.created);
  if (!Number.isFinite(d.getTime()) || d.toISOString().slice(0, 10) !== rec.date ||
      !Number.isFinite(t.getTime()) || t.toISOString() !== rec.created) return null;
  return { night_number: rec.night_number, date: rec.date, created: rec.created, id: rec.id };
}
function newer(a, b) {
  a = orderKey(a); b = orderKey(b);
  if (!a || !b || a.night_number < b.night_number || a.date < b.date) return false;
  if (a.night_number === b.night_number && a.date !== b.date) return false;
  if (a.night_number > b.night_number) return true;
  return a.created > b.created || (a.created === b.created && a.id > b.id);
}
function safeDir(home, id) {
  if (typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id)) return null;
  try {
    const root = path.join(home, 'adapter-candidates'), dir = path.join(root, id);
    if (fs.lstatSync(root).isSymbolicLink() || fs.lstatSync(dir).isSymbolicLink()) return null;
    const realRoot = fs.realpathSync(root), realDir = fs.realpathSync(dir);
    if (path.dirname(realDir) !== realRoot) return null;
    for (const n of ['adapter.gguf', 'held.jsonl', 'record.json']) if (fs.lstatSync(path.join(dir, n)).isSymbolicLink()) return null;
    return dir;
  } catch (_) { return null; }
}
function inspect(home, id, identity) {
  const dir = safeDir(home, id); if (!dir) return null;
  try {
    const rec = read(path.join(dir, 'record.json'));
    if (!rec || rec.version !== 1 || rec.id !== id || !orderKey(rec) || !sameBase(rec.base, identity) || rec.base.repo !== C.SLEEP_HF_REPO) return null;
    const adapter = path.join(dir, 'adapter.gguf'), held = path.join(dir, 'held.jsonl');
    if (!fs.statSync(adapter).size || fileHash(adapter) !== rec.adapter_sha256 || fileHash(held) !== rec.held_sha256) return null;
    const cards = fs.readFileSync(held, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
    if (!cards.length || cards.length !== rec.held_count || cards.some(c => c.status !== 'held_out' || !c.q || !c.a || c.night !== rec.day)) return null;
    return { id, dir, rec, adapter, held };
  } catch (_) { return null; }
}
function manifest(home) { const m = read(path.join(home, 'accepted-adapters.json')); return m && m.version === 1 ? m : {}; }
function accepted(home, identity) {
  const m = manifest(home);
  for (const id of [m.current, m.previous]) {
    const c = inspect(home, id, identity);
    if (c && c.rec.status === 'accepted' && validVerdict(c.rec.served, c.rec.held_count)) return c.adapter;
  }
  return '';
}

function heldSnapshot(file, day) {
  if (!Number.isInteger(day) || day < 1) return [];
  try { return fs.readFileSync(file, 'utf8').split('\n').filter(Boolean).map(JSON.parse).filter(r => r.status === 'held_out' && r.night === day && typeof r.q === 'string' && r.q && typeof r.a === 'string' && r.a).slice(0, 12); } catch (_) { return []; }
}
function watermark(home, identity, m) {
  if (m.watermark && sameBase(m.watermark.base, identity) && orderKey(m.watermark)) return m.watermark;
  for (const id of [m.current, m.previous]) {
    const c = inspect(home, id, identity);
    if (c && c.rec.status === 'accepted' && validVerdict(c.rec.served, c.rec.held_count)) return c.rec;
  }
  return null;
}
function pending(home, identity) {
  const root = path.join(home, 'adapter-candidates');
  try {
    const m = manifest(home), mark = watermark(home, identity, m);
    const published = new Set([m.current, m.previous, ...(Array.isArray(m.published) ? m.published : [])]);
    const candidates = fs.readdirSync(root).map(id => inspect(home, id, identity))
      .filter(c => c && ['pending','accepted'].includes(c.rec.status) && !published.has(c.id) && (!mark || newer(c.rec, mark)));
    // If reset state makes two pending nights incomparable, defer both.
    return candidates.find(c => candidates.every(other => other.id === c.id || newer(c.rec, other.rec))) || null;
  } catch (_) { return null; }
}
function promote(home, c) {
  const previous = manifest(home);
  if (previous.current === c.id) return true;
  const verified = inspect(home, c.id, c.rec.base);
  if (!verified || verified.rec.status !== 'accepted' || !validVerdict(verified.rec.served, verified.rec.held_count)) return false;
  const mark = watermark(home, verified.rec.base, previous);
  if (mark && !newer(verified.rec, mark)) return false;
  const fallback = [previous.current, previous.previous].find(id => { const p = inspect(home, id, verified.rec.base); return p && p.rec.status === 'accepted' && validVerdict(p.rec.served, p.rec.held_count); }) || null;
  const published = [...new Set([...(Array.isArray(previous.published) ? previous.published : []), previous.current, previous.previous, verified.id].filter(id => typeof id === 'string' && /^[a-f0-9]{64}$/.test(id)))];
  atomic(path.join(home, 'accepted-adapters.json'), { version: 1, current: verified.id, previous: fallback, published, watermark: { ...orderKey(verified.rec), base: verified.rec.base } });
  return true;
}

module.exports = { read, hash, fileHash, atomic, baseIdentity, sameBase, validMetrics, validVerdict, orderKey, newer, safeDir, inspect, manifest, accepted, heldSnapshot, pending, promote };
