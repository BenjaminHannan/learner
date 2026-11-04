'use strict';
// I3 two-speed core (2026-11-04), part 1: the INTENT CHANNEL. Game-agnostic: no game names in this file.
// The slow brain (Nanbeige, every ~0.5-2 s) sends short TACTICAL calls from a fixed vocabulary the game adapter declares, e.g.
//   STRAFE dir=left wtap=1        JUMPCRIT at=3        BRIDGE n=2 then=jump        GOTO to=B2
// The fast reflex reads current() every tick. If no call arrives for more than holdMs (2 s) it KEEPS the last call (marked stale).
// Unknown codes or bad arguments are rejected, never guessed. stats() measures the real call rate.
//
// vocab: { CODE: { args: { name: spec }, help } }   spec: { enum: [...] } | { min, max, int: bool } ; every arg may be optional:true

function checkArg(spec, v) {
  if (spec.enum) { const hit = spec.enum.find((e) => String(e).toLowerCase() === String(v).toLowerCase()); return hit === undefined ? { ok: false } : { ok: true, v: hit }; }
  const n = Number(v); if (!Number.isFinite(n)) return { ok: false };
  if (spec.int && !Number.isInteger(n)) return { ok: false };
  if (spec.min != null && n < spec.min) return { ok: false };
  if (spec.max != null && n > spec.max) return { ok: false };
  return { ok: true, v: n };
}

function validate(vocab, call) {
  if (!call || typeof call.code !== 'string') return { ok: false, why: 'no code' };
  const code = Object.keys(vocab).find((k) => k.toLowerCase() === call.code.toLowerCase());
  if (!code) return { ok: false, why: 'unknown code ' + call.code };
  const spec = vocab[code].args || {}, args = {};
  for (const [k, v] of Object.entries(call.args || {})) {
    const key = Object.keys(spec).find((s) => s.toLowerCase() === String(k).toLowerCase());
    if (!key) return { ok: false, why: 'unknown arg ' + k };
    const c = checkArg(spec[key], v); if (!c.ok) return { ok: false, why: 'bad value ' + k + '=' + v };
    args[key] = c.v;
  }
  for (const [k, s] of Object.entries(spec)) if (!s.optional && !(k in args)) { if (s.default !== undefined) args[k] = s.default; else return { ok: false, why: 'missing arg ' + k }; }
  return { ok: true, call: { code, args } };
}

// text -> call. Accepts "GOTO to=C3 guard=jump", "GOTO(to=C3, guard=jump)", "GOTO to: C3" and a JSON object. First line with a
// known code wins (models sometimes add words around it).
function parse(vocab, text) {
  const t = String(text == null ? '' : text).trim();
  if (t.startsWith('{')) { try { const j = JSON.parse(t); return validate(vocab, { code: j.code, args: j.args || {} }); } catch (e) { /* fall through */ } }
  const codes = Object.keys(vocab);
  for (const line of t.split(/\n/)) {
    const m = new RegExp('\\b(' + codes.join('|') + ')\\b', 'i').exec(line); if (!m) continue;
    const rest = line.slice(m.index + m[1].length).replace(/\s(#|\/\/).*$/, '').replace(/[()`*]/g, ' ');   // a trailing # comment is not arguments
    const args = {}; const re = /([A-Za-z_]+)\s*[=:]\s*([A-Za-z0-9_.\-]+)/g; let a;
    while ((a = re.exec(rest))) args[a[1]] = a[2];
    return validate(vocab, { code: m[1], args });
  }
  return { ok: false, why: 'no known code in reply' };
}

const fmt = (call) => call ? call.code + Object.entries(call.args || {}).map(([k, v]) => ' ' + k + '=' + v).join('') : '(none)';
function describe(vocab) {
  return Object.entries(vocab).map(([code, d]) => code + Object.entries(d.args || {}).map(([k, s]) => ' ' + k + '=' + (s.enum ? s.enum.join('|') : (s.min + '..' + s.max))).join('') + (d.help ? '   # ' + d.help : '')).join('\n');
}

class IntentChannel {
  constructor(vocab, o) { this.vocab = vocab; this.o = o || {}; this.holdMs = this.o.holdMs || 2000; this.last = null; this.lastAt = null; this.source = null; this.times = []; this.sent = 0; this.rejected = 0; this.why = []; }
  // call: {code,args} or text. -> {ok, call|why}
  send(call, nowMs, source) {
    const r = typeof call === 'string' ? parse(this.vocab, call) : validate(this.vocab, call);
    if (!r.ok) { this.rejected++; if (this.why.length < 20) this.why.push(r.why); return r; }
    this.last = r.call; this.lastAt = nowMs; this.source = source || 'brain'; this.sent++;
    if (this.source === 'brain') this.times.push(nowMs);
    return r;
  }
  current(nowMs) {
    if (!this.last) return { call: null, ageMs: null, stale: true, source: null };
    const ageMs = nowMs - this.lastAt; return { call: this.last, ageMs, stale: ageMs > this.holdMs, source: this.source };
  }
  stats() {
    const g = []; for (let i = 1; i < this.times.length; i++) g.push(this.times[i] - this.times[i - 1]);
    const span = this.times.length > 1 ? this.times[this.times.length - 1] - this.times[0] : 0, s = g.slice().sort((a, b) => a - b);
    return { sent: this.sent, fromBrain: this.times.length, rejected: this.rejected, ratePerS: span ? (this.times.length - 1) / (span / 1000) : null, p50GapMs: s.length ? s[Math.floor(s.length / 2)] : null, maxGapMs: s.length ? s[s.length - 1] : null };
  }
}

module.exports = { IntentChannel, validate, parse, describe, fmt };
