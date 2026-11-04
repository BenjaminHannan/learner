'use strict';
// Glim team, Bedwars side: the slow brain's VOCABULARY (v2) and the PLAN RULES.
// Real Nanbeige (8-bit, M1, I3's measurements): ~2.7 s per call (0.3-0.4 calls/s); calls always well-formed (24/24) but the right
// call only 6/12 and whole plans 1/12; it often ignored its "already done" list and never sent a required follow-up (0/6). So:
//   - 9 calls, each a plain word with a one-line description written so no two can be mixed up (I3 intent format: "BRIDGE n=20");
//   - the brain only chooses WHAT to aim for (bridge, break the bed, fight, defend, an upgrade to buy). The rules below make the
//     plan correct without asking it again: steps already done are dropped, resources and required purchases are worked out from
//     the inventory ("no wool -> get iron, buy wool"; "bed covered in wool -> buy shears first"), the goal step is never lost;
//   - moment-to-moment play (hitting, W-taps, crits, the jump at the bridge edge) is the reflex's and the schedule's (adapter.js),
//     never a brain call. Urgent rules (an enemy close -> FIGHT) are applied at once, not after a 3-11 s brain answer.
// Pure; no I/O. The old short codes ("jc 3", "br 4") survive only in parse() below, for truthlog.cards() (another builder's file).
const { intent } = require('./core-iface');

const RES = ['iron', 'gold', 'diamond', 'emerald'];
const ITEMS = ['wool', 'stone_sword', 'iron_sword', 'chain_armor', 'shears', 'pickaxe', 'gapple'];
// Hypixel-like prices (ours, approximate): what one BUY costs; wool comes 16 at a time
const PRICE = { wool: ['iron', 4], stone_sword: ['iron', 10], iron_sword: ['gold', 7], chain_armor: ['iron', 40], shears: ['iron', 20], pickaxe: ['iron', 10], gapple: ['gold', 3] };
const WOOL_PER_BUY = 16;
const PERMANENT = new Set(['stone_sword', 'iron_sword', 'chain_armor', 'shears', 'pickaxe']);   // kept after a death

const vocab = {
  GET: { args: { res: { enum: RES, default: 'iron' }, n: { min: 1, max: 64, int: true, default: 16 } }, help: 'stand on YOUR OWN generator until you carry n of res' },
  BUY: { args: { item: { enum: ITEMS } }, help: 'buy one item at YOUR OWN shop (only works on your own island)' },
  BRIDGE: { args: { n: { min: 1, max: 64, int: true, default: 20 } }, help: 'place up to n blocks in a straight line toward the ENEMY island, then jump the last small gap' },
  BREAK_BED: { args: {}, help: 'walk to the ENEMY bed and break it' },
  FIGHT: { args: {}, help: 'attack the nearest ENEMY player until he dies or runs away' },
  RETREAT: { args: {}, help: 'walk backwards away from the nearest ENEMY, still facing him' },
  DEFEND: { args: {}, help: 'stand next to YOUR OWN bed and attack any ENEMY who comes near it' },
  HOME: { args: {}, help: 'walk back to YOUR OWN island over blocks that are already placed' },
  HOLD: { args: {}, help: 'stay where you are; only hit back if someone hits you' }
};
const CODES = Object.keys(vocab);
const parseCall = (text) => intent.parse(vocab, text);   // -> {ok, call: {code, args}} | {ok:false, why}
const fmt = intent.fmt;
const promptCard = () => intent.describe(vocab);

// ---- plan steps: {id, kind, call, item?} ------------------------------------------------------------------------------------
const STEP_CALL = {
  get_resources: (o) => ({ code: 'GET', args: { res: o.res || 'iron', n: o.n || 16 } }),
  buy_blocks: () => ({ code: 'BUY', args: { item: 'wool' } }),
  buy: (o) => ({ code: 'BUY', args: { item: o.item } }),
  bridge: (o) => ({ code: 'BRIDGE', args: { n: o.n || 20 } }),
  break_bed: () => ({ code: 'BREAK_BED', args: {} }),
  fight: () => ({ code: 'FIGHT', args: {} }),
  retreat: () => ({ code: 'RETREAT', args: {} }),
  defend: () => ({ code: 'DEFEND', args: {} }),
  home: () => ({ code: 'HOME', args: {} }),
  hold: () => ({ code: 'HOLD', args: {} })
};
const RUSH_PLAN = ['get_resources', 'buy_blocks', 'bridge', 'break_bed'];   // step names the truth-log goal scorer knows
function makeStep(kind, o) { o = o || {}; const call = STEP_CALL[kind](o); return { id: kind, kind, call, ...(o.item ? { item: o.item } : {}), ...(o.res ? { res: o.res, n: o.n } : {}) }; }
// a brain call -> a plan step
function stepOf(call) {
  const a = call.args || {};
  switch (call.code) {
    case 'GET': return makeStep('get_resources', { res: a.res, n: a.n });
    case 'BUY': return a.item === 'wool' ? makeStep('buy_blocks') : makeStep('buy', { item: a.item });
    case 'BRIDGE': return makeStep('bridge', { n: a.n });
    default: return makeStep(call.code.toLowerCase());
  }
}
// ids unique across the plan's history: the second "get_resources" is get_resources#2
function withIds(steps, done) {
  const used = new Set(done || []);
  return steps.map((s) => { const base = s.kind === 'buy' ? 'buy:' + s.item : s.kind; let id = base, k = 1; while (used.has(id)) id = base + '#' + (++k); used.add(id); return { ...s, id }; });
}

// ---- the rules -------------------------------------------------------------------------------------------------------------
// obs fields the rules read (adapter.js makes them from what Glim sees; HUD counts, scoreboard, own estimates):
//   inv {iron, gold, wool, shears, ...}, atBase, bridgeLeft (blocks still to place before the jump), onEnemyIsland,
//   enemy {dist, alive} | null, enemyBed {alive, covered}, myBedThreat, me {alive}
const own = (inv, item) => !!(inv && inv[item]);
// what one step needs first, given a virtual state v (inventory + where I am) -> steps to put in front of it
function needs(step, v) {
  const out = [];
  const buy = (item, k) => {
    const [cur, cost] = PRICE[item], want = cost * (k || 1);
    if (!v.atBase) { out.push(makeStep('home')); v.atBase = true; }
    if ((v.inv[cur] || 0) < want) { out.push(makeStep('get_resources', { res: cur, n: Math.min(64, want) })); v.inv[cur] = want; }
  };
  if (step.kind === 'get_resources' && !v.atBase) { out.push(makeStep('home')); v.atBase = true; }
  if (step.kind === 'buy' || step.kind === 'buy_blocks') buy(step.kind === 'buy' ? step.item : 'wool');
  if (step.kind === 'bridge' || step.kind === 'break_bed') {
    if (v.bridgeLeft > 0 && (v.inv.wool || 0) < v.bridgeLeft) {
      const k = Math.ceil((v.bridgeLeft - (v.inv.wool || 0)) / WOOL_PER_BUY);
      buy('wool', k); for (let i = 0; i < k; i++) { out.push(makeStep('buy_blocks')); v.inv.iron -= PRICE.wool[1]; v.inv.wool = (v.inv.wool || 0) + WOOL_PER_BUY; }
    }
    if (step.kind === 'break_bed' && v.bridgeLeft > 0) { out.push(makeStep('bridge', { n: Math.min(64, v.bridgeLeft) })); apply(out[out.length - 1], v); }
    if (step.kind === 'break_bed' && v.covered && !own(v.inv, 'shears')) {
      const pre = needs(makeStep('buy', { item: 'shears' }), v); out.push(...pre, makeStep('buy', { item: 'shears' })); apply(out[out.length - 1], v);
    }
  }
  return out;
}
// a step's effect on the virtual state
function apply(step, v) {
  if (step.kind === 'get_resources') { v.inv[step.res || 'iron'] = Math.max(v.inv[step.res || 'iron'] || 0, step.n || 16); v.atBase = true; }
  else if (step.kind === 'buy_blocks') { v.inv.iron -= PRICE.wool[1]; v.inv.wool = (v.inv.wool || 0) + WOOL_PER_BUY; }
  else if (step.kind === 'buy') { const [cur, cost] = PRICE[step.item]; v.inv[cur] -= cost; v.inv[step.item] = 1; }
  else if (step.kind === 'bridge') { v.inv.wool = Math.max(0, (v.inv.wool || 0) - v.bridgeLeft); v.bridgeLeft = 0; v.atBase = false; }
  else if (step.kind === 'break_bed') v.atBase = false;
  else if (step.kind === 'home') v.atBase = true;
}
// make any plan (a brain's, possibly wrong) correct for what is seen now. done = the plan memory's done ids.
//   1. resources and wool purchases are always worked out here: the brain's GET / BUY wool steps are dropped;
//   2. steps the world already shows as done are dropped (bridge complete, bed broken, a permanent item owned, home when at base);
//   3. the goal step (break the enemy bed) is kept at the end while that bed stands;
//   4. every step gets its required steps in front (home before shopping, iron before buying, wool before bridging, shears before a
//      covered bed), tracked through a virtual inventory so nothing is bought twice.
const DONE_RANGE = 8;   // a fight is over once he is further than this (adapter.judge uses the same number)
function repair(steps, obs, done) {
  const near = !!(obs.enemy && obs.enemy.alive && obs.enemy.dist <= DONE_RANGE && !(obs.me && obs.me.alive === false));
  const inv = { ...(obs.inv || {}) }, v = { inv, atBase: !!obs.atBase, bridgeLeft: obs.bridgeLeft || 0, covered: !!(obs.enemyBed && obs.enemyBed.covered) };
  let want = (steps || []).filter((s) => {
    if (s.kind === 'get_resources' || s.kind === 'buy_blocks') return false;
    if (s.kind === 'bridge' && v.bridgeLeft <= 0) return false;
    if (s.kind === 'break_bed' && obs.enemyBed && !obs.enemyBed.alive) return false;
    if (s.kind === 'buy' && PERMANENT.has(s.item) && own(inv, s.item)) return false;
    if ((s.kind === 'fight' || s.kind === 'retreat') && !near) return false;   // nobody to fight or run from (e.g. after I died)
    return true;
  });
  want = want.filter((s, i) => !(i && want[i - 1].kind === s.kind && s.kind !== 'buy'));
  if (obs.enemyBed && obs.enemyBed.alive && !want.some((s) => s.kind === 'break_bed')) want.push(makeStep('break_bed'));
  // a covered enemy bed needs shears: buy them before leaving the island (not after crossing)
  if (v.covered && !own(inv, 'shears') && obs.enemyBed && obs.enemyBed.alive && !want.some((s) => s.kind === 'buy' && s.item === 'shears')) {
    const i = want.findIndex((s) => s.kind === 'bridge' || s.kind === 'break_bed'); want.splice(i < 0 ? want.length : i, 0, makeStep('buy', { item: 'shears' }));
  }
  const out = [];
  for (const s of want) { out.push(...needs(s, v), s); apply(s, v); }
  // a lone "home" at the front while at base is already done
  while (out.length && out[0].kind === 'home' && obs.atBase) out.shift();
  return withIds(out, done);
}
// urgent steps that cannot wait for the brain (applied by the plan at once): an enemy in fighting range -> FIGHT; my bed attacked -> go defend
const FIGHT_RANGE = 5;
function urgent(obs, current) {
  const k = current && current.kind;
  if (obs.me && obs.me.alive === false) return null;
  if (obs.myBedThreat && k !== 'defend' && k !== 'home') return [makeStep('home'), makeStep('defend')];
  if (obs.enemy && obs.enemy.alive && obs.enemy.dist <= FIGHT_RANGE && !['fight', 'retreat', 'defend'].includes(k)) return [makeStep('fight')];
  return null;
}

// ---- legacy text, ONLY for truthlog.cards() (another builder's file reads VOCAB[code].group and the old codes) ---------------------
// New calls map onto the old card codes; old short lines ("jc 3", "br 4", "st l w") still parse. The brain never sees these.
const VOCAB = {
  st: { group: 'pvp', p: ['dir'] }, wt: { group: 'pvp', p: [] }, stap: { group: 'pvp', p: [] }, jc: { group: 'pvp', p: ['at'] }, jr: { group: 'pvp', p: [] },
  bh: { group: 'pvp', p: [] }, hs: { group: 'pvp', p: [] }, cb: { group: 'pvp', p: [] }, bo: { group: 'pvp', p: ['d'] }, br: { group: 'move', p: ['n'] },
  jg: { group: 'move', p: [] }, rb: { group: 'move', p: [] }, hold: { group: 'move', p: [] }, buy: { group: 'econ', p: ['item'] }, get: { group: 'econ', p: ['res', 'n'] },
  bb: { group: 'bed', p: [] }, db: { group: 'bed', p: [] }
};
const TO_LEGACY = { GET: (a) => ({ code: 'get', params: { res: a.res, n: a.n } }), BUY: (a) => ({ code: 'buy', params: { item: a.item } }), BRIDGE: (a) => ({ code: 'br', params: { n: a.n } }),
  BREAK_BED: () => ({ code: 'bb', params: {} }), FIGHT: () => ({ code: 'cb', params: {} }), RETREAT: () => ({ code: 'bo', params: { d: 3 } }), DEFEND: () => ({ code: 'db', params: {} }),
  HOME: () => ({ code: 'rb', params: {} }), HOLD: () => ({ code: 'hold', params: {} }) };
const LEGACY_DEF = { get: { res: 'iron', n: 16 }, jc: { at: 3 }, bo: { d: 3 } };
function parseLegacyOne(text) {
  const toks = String(text || '').trim().toLowerCase().split(/[\s,()]+/).filter(Boolean);
  const spec = toks.length && VOCAB[toks[0]]; if (!spec) return null;
  const params = { ...(LEGACY_DEF[toks[0]] || {}) };
  spec.p.forEach((name, i) => { const v = toks[i + 1]; if (v != null) params[name] = /^-?\d+(\.\d+)?$/.test(v) ? Number(v) : v; });
  return { code: toks[0], params };
}
function parse(line) {
  const parts = String(line || '').split(';').map((s) => s.trim()).filter(Boolean), calls = [];
  for (const p of parts) {
    const n = parseCall(p);
    if (n.ok && /[=]/.test(p) || (n.ok && Object.keys(vocab[n.call.code].args).length === 0)) { calls.push(TO_LEGACY[n.call.code](n.call.args)); continue; }
    const o = parseLegacyOne(p); if (o) { calls.push(o); continue; }
    if (n.ok) { calls.push(TO_LEGACY[n.call.code](n.call.args)); continue; }
    return { ok: false, error: 'not a call: ' + p.slice(0, 40) };
  }
  return calls.length ? { ok: true, calls } : { ok: false, error: 'empty line' };
}

module.exports = { vocab, CODES, RES, ITEMS, PRICE, WOOL_PER_BUY, PERMANENT, parseCall, fmt, promptCard, STEP_CALL, RUSH_PLAN, makeStep, stepOf, withIds,
  needs, repair, urgent, FIGHT_RANGE, DONE_RANGE, VOCAB, parse };
