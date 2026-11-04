'use strict';
// Glim team, Bedwars side (plan v4.1 §1): the fixed TACTICAL vocabulary the slow brain (Nanbeige) uses to steer the reflex.
// Codes come from bedwars/PVP-HABITS.md (research repo) plus the Bedwars economy / bed steps. Each call is a few tokens:
//   "st l w"  strafe left + W-tap        "jc 3"   jump-crit when he is 3 blocks away      "bh"  block-hit
//   "br 2; jg" bridge 2 blocks, then jump the gap                                         "buy wool"  "get iron 16"
// A line may hold up to MAX_CALLS calls joined by ';' (done in order). Long names are accepted too ("strafe left wtap").
// No fishing rods (Ben, 11-03). Pure; no I/O.

const MAX_CALLS = 3;
const ITEMS = ['wool', 'wood', 'endstone', 'stone_sword', 'iron_sword', 'chain_armor', 'iron_armor', 'pickaxe', 'axe', 'shears', 'gapple', 'fireball', 'tnt', 'pearl'];
const RESOURCES = ['iron', 'gold', 'diamond', 'emerald'];
const DIRS = { l: 'l', left: 'l', r: 'r', right: 'r' };

// p: [{name, type: 'enum'|'int'|'num'|'flag', values?, min?, max?, def?, flag? (the token for a flag)}]
const VOCAB = {
  st:   { name: 'strafe', group: 'pvp', p: [{ name: 'dir', type: 'enum', values: ['l', 'r'] }, { name: 'wtap', type: 'flag', flag: 'w', def: false }], says: 'strafe left/right (w = W-tap each hit)' },
  wt:   { name: 'sprint_reset', group: 'pvp', p: [], says: 'W-tap: release and re-press W after the hit' },
  stap: { name: 's_tap', group: 'pvp', p: [], says: 'S-tap after the hit' },
  jc:   { name: 'jump_crit', group: 'pvp', timed: 'crit_on_fall', p: [{ name: 'at', type: 'num', min: 0.5, max: 6, def: 3 }], says: 'jump so the hit lands falling, when he is AT blocks away' },
  jr:   { name: 'jump_reset', group: 'pvp', p: [], says: 'jump on the tick you get hit' },
  bh:   { name: 'block_hit', group: 'pvp', timed: 'block_at_hit', p: [], says: 'sword-block right after each landed hit' },
  hs:   { name: 'hit_select', group: 'pvp', p: [], says: 'land the sprint hit just after his hit' },
  cb:   { name: 'combo', group: 'pvp', p: [], says: 'keep him in knockback: chase and hit' },
  bo:   { name: 'back_off', group: 'pvp', p: [{ name: 'd', type: 'num', min: 1, max: 12, def: 3 }], says: 'back off D blocks' },
  br:   { name: 'bridge', group: 'move', p: [{ name: 'n', type: 'int', min: 1, max: 64 }], says: 'bridge N blocks' },
  jg:   { name: 'jump_gap', group: 'move', timed: 'jump_at_edge', p: [], says: 'jump the gap at the edge' },
  rb:   { name: 'return_base', group: 'move', p: [], says: 'go back to base' },
  buy:  { name: 'buy', group: 'econ', p: [{ name: 'item', type: 'enum', values: ITEMS }], says: 'buy ITEM at the shop' },
  get:  { name: 'get', group: 'econ', p: [{ name: 'res', type: 'enum', values: RESOURCES }, { name: 'n', type: 'int', min: 1, max: 64, def: 16 }], says: 'collect N of RES at a generator' },
  bb:   { name: 'break_bed', group: 'bed', p: [], says: 'break the enemy bed' },
  db:   { name: 'defend_bed', group: 'bed', p: [], says: 'defend my bed' }
};
const CODES = Object.keys(VOCAB);
const BY_NAME = {}; for (const c of CODES) { BY_NAME[c] = c; BY_NAME[VOCAB[c].name] = c; BY_NAME[VOCAB[c].name.replace(/_/g, '')] = c; BY_NAME[VOCAB[c].name.replace(/_/g, '-')] = c; }
BY_NAME.wtap = 'wt'; BY_NAME.stap = 'stap'; BY_NAME.blockhit = 'bh'; BY_NAME.jumpcrit = 'jc';

const fail = (error) => ({ ok: false, error });

function checkParam(spec, v) {
  if (spec.type === 'enum') { const x = spec.name === 'dir' ? DIRS[String(v).toLowerCase()] : String(v).toLowerCase(); return spec.values.includes(x) ? { ok: true, v: x } : fail(spec.name + ' must be one of ' + spec.values.join('/')); }
  if (spec.type === 'flag') return v === true || v === false ? { ok: true, v } : fail(spec.name + ' is on or off');
  const n = Number(v);
  if (!Number.isFinite(n)) return fail(spec.name + ' must be a number');
  if (spec.type === 'int' && !Number.isInteger(n)) return fail(spec.name + ' must be a whole number');
  if (n < spec.min || n > spec.max) return fail(spec.name + ' must be ' + spec.min + '..' + spec.max);
  return { ok: true, v: n };
}

// a call object -> validated canonical call {code, params} (defaults filled) or {ok:false, error}
function validate(call) {
  if (!call || typeof call !== 'object') return fail('not a call');
  const code = BY_NAME[String(call.code || '').toLowerCase()];
  if (!code) return fail('unknown code "' + call.code + '"');
  const spec = VOCAB[code], given = call.params || {}, params = {};
  for (const k of Object.keys(given)) if (!spec.p.some((p) => p.name === k)) return fail(code + ': unknown param ' + k);
  for (const p of spec.p) {
    if (given[p.name] == null) { if (p.def === undefined) return fail(code + ': missing ' + p.name); params[p.name] = p.def; continue; }
    const r = checkParam(p, given[p.name]); if (!r.ok) return fail(code + ': ' + r.error); params[p.name] = r.v;
  }
  return { ok: true, call: { code, params } };
}

// canonical short text (what Nanbeige writes and reads back): code, then params in order; flags only when on; defaults kept explicit
function toText(call) {
  const v = validate(call); if (!v.ok) throw new Error(v.error);
  const { code, params } = v.call, out = [code];
  for (const p of VOCAB[code].p) { if (p.type === 'flag') { if (params[p.name]) out.push(p.flag); } else out.push(String(params[p.name])); }
  return out.join(' ');
}

// one call's text -> {ok, call} | {ok:false, error}
function parseOne(text) {
  const toks = String(text || '').trim().toLowerCase().split(/[\s,()]+/).filter(Boolean);
  if (!toks.length) return fail('empty call');
  const code = BY_NAME[toks[0]]; if (!code) return fail('unknown code "' + toks[0] + '"');
  const spec = VOCAB[code], params = {}, rest = toks.slice(1);
  const flags = spec.p.filter((p) => p.type === 'flag'), plain = spec.p.filter((p) => p.type !== 'flag');
  const pos = [];
  for (const t of rest) {
    const f = flags.find((p) => t === p.flag || t === p.name || (p.name === 'wtap' && t === 'w-tap'));
    if (f) { params[f.name] = true; continue; }
    if (t === '+' || t === 'and') continue;
    const v = t.replace(/blocks?$/, ''); if (v) pos.push(v);
  }
  if (pos.length > plain.length) return fail(code + ': too many params (' + rest.join(' ') + ')');
  plain.forEach((p, i) => { if (pos[i] != null && pos[i] !== '') params[p.name] = pos[i]; });
  return validate({ code, params });
}

// a whole line ("br 2; jg") -> {ok, calls} | {ok:false, error}. "then" also splits ("bridge 2 then jump_gap").
function parse(line) {
  const parts = String(line || '').split(/;|\bthen\b|\n/i).map((s) => s.trim()).filter(Boolean);
  if (!parts.length) return fail('empty line');
  if (parts.length > MAX_CALLS) return fail('at most ' + MAX_CALLS + ' calls per line');
  const calls = [];
  for (const p of parts) { const r = parseOne(p); if (!r.ok) return r; calls.push(r.call); }
  return { ok: true, calls };
}
const lineText = (calls) => calls.map(toText).join('; ');

// the vocabulary card for Nanbeige's prompt (stable text, so it caches)
function promptCard() {
  return CODES.map((c) => {
    const s = VOCAB[c], ps = s.p.map((p) => p.type === 'flag' ? '[' + p.flag + ']' : p.type === 'enum' ? (p.values.length <= 4 ? p.values.join('|') : p.name.toUpperCase()) : (p.def !== undefined ? '[' + p.name.toUpperCase() + ']' : p.name.toUpperCase()));
    return [c].concat(ps).join(' ') + ' = ' + s.says;
  }).join('\n') + '\nItems: ' + ITEMS.join(' ') + '\nUp to ' + MAX_CALLS + ' calls per line, joined by ";".';
}

// ---- long horizon: plan-level steps (plan §1: get iron -> buy blocks -> bridge -> break bed), replanned when disrupted -------------
const PLAN_STEPS = {
  get_resources: { call: (o) => ({ code: 'get', params: { res: (o && o.res) || 'iron', n: (o && o.n) || 16 } }), timeoutMs: 60000 },
  buy_blocks:    { call: (o) => ({ code: 'buy', params: { item: (o && o.item) || 'wool' } }), timeoutMs: 30000 },
  bridge:        { call: (o) => ({ code: 'br', params: { n: (o && o.n) || 16 } }), timeoutMs: 60000 },
  break_bed:     { call: () => ({ code: 'bb', params: {} }), timeoutMs: 45000 },
  return_base:   { call: () => ({ code: 'rb', params: {} }), timeoutMs: 30000 },
  defend_bed:    { call: () => ({ code: 'db', params: {} }), timeoutMs: 30000 }
};
const RUSH_PLAN = ['get_resources', 'buy_blocks', 'bridge', 'break_bed'];
const LOW_HP = 6;   // ours: 3 hearts

// observation -> replan reasons (empty = keep going). obs: {knockedOff, died, hp, bedUnderAttack, stepStartedAt, now, step}
function replanTriggers(obs) {
  const why = [], o = obs || {};
  if (o.knockedOff || o.died) why.push('knocked_off');
  if (Number.isFinite(o.hp) && o.hp <= LOW_HP) why.push('low_hp');
  if (o.bedUnderAttack) why.push('bed_under_attack');
  const spec = o.step && PLAN_STEPS[o.step];
  if (spec && Number.isFinite(o.stepStartedAt) && Number.isFinite(o.now) && o.now - o.stepStartedAt > spec.timeoutMs) why.push('step_timeout');
  return why;
}
// a simple default replan the slow brain may override: bed in danger -> defend first; knocked off / low hp -> start the rush again
function replan(reasons, current) {
  if (reasons.includes('bed_under_attack')) return ['return_base', 'defend_bed'].concat(RUSH_PLAN);
  if (reasons.includes('knocked_off') || reasons.includes('low_hp')) return RUSH_PLAN.slice();
  if (reasons.includes('step_timeout') && current) { const i = RUSH_PLAN.indexOf(current); return i > 0 ? RUSH_PLAN.slice(i - 1) : RUSH_PLAN.slice(); }
  return null;
}

// the same vocabulary in the I3 core's format (src/games/core/intent.js: { CODE: { args: { name: spec }, help } }), for the wiring
function coreVocab() {
  const v = {};
  for (const c of CODES) {
    const s = VOCAB[c], args = {};
    for (const p of s.p) {
      if (p.type === 'enum') args[p.name] = { enum: p.values.slice() };
      else if (p.type === 'flag') args[p.name] = { enum: [0, 1], default: 0 };
      else args[p.name] = { min: p.min, max: p.max, int: p.type === 'int', ...(p.def !== undefined ? { default: p.def } : {}) };
    }
    v[c] = { args, help: s.says };
  }
  return v;
}
const toCoreCall = (call) => ({ code: call.code, args: Object.fromEntries(Object.entries(call.params).map(([k, x]) => [k, typeof x === 'boolean' ? (x ? 1 : 0) : x])) });

module.exports = { coreVocab, toCoreCall, VOCAB, CODES, ITEMS, RESOURCES, MAX_CALLS, validate, toText, parseOne, parse, lineText, promptCard, PLAN_STEPS, RUSH_PLAN, LOW_HP, replanTriggers, replan };
