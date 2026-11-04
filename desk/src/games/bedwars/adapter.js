'use strict';
// Glim team, Bedwars side: the Bedwars adapter for I3's two-speed core, in the same shape as src/games/adapters/sparksquest.js and
// orchard.js (interface at the top of src/games/core/loop.js), plus the hooks core-iface.js LiveLoop uses (repair, urgent,
// interrupted, stepsFromCalls).
//
// Who does what, because the real slow brain gives ~0.3-0.4 calls/s and is often wrong (I3's measurement on the M1):
//   slow brain   picks the aim: a first plan, or what to do after a surprise the rules cannot fix (vocabulary: tactics.js, 9 calls)
//   plan rules   tactics.repair / urgent: done steps dropped, resources and required purchases added, an enemy close -> FIGHT now
//   plan memory  core PlanMemory: remembers done steps, judge() below says done / going / blocked every tick, advances by itself
//   reflex       fallback() below (until sleep keeps a net): every tick, follows the current call AND always hits an enemy in reach
//   schedule     timedTargets(): the jump-crit (jump 450 ms before he enters reach) and the jump at the bridge's end, re-estimated
//                every tick and fired on their tick, with no brain call
//
// Observations are what Glim sees (screen, allowed HUD, sound) turned into a few numbers by the eyes: how far along the lane toward
// the enemy island I am, my inventory (hotbar), how much bridge is left, the enemy's distance (MY estimate; no reach display), the
// beds (scoreboard; "covered" once seen). validateObs() keeps the raw inputs human-equivalent. The truth log is never an input.
//
// The second half is a PRACTICE MODEL (init / observe / step): a 1-D side-rush lane (my island, an 18-block gap to bridge, the enemy
// island with its bed, one scripted defender) so the core can run the adapter in tests and toy practice. It is a coarse stand-in,
// NOT Bedwars physics; every number in it is ours. Real play happens on BensPC (session.js, TOOLS.md).
const T = require('./tactics');
const { rng } = require('../../tinynet');

const TICK = 50, MAX_TICKS = 3600, FRAME_TO_KEY_MS = 30;
const CRIT_MID_MS = 450, CRIT_WINDOW = { from: 350, to: 550 };   // = timing.js (1.8 jump: falling ticks 7..11); a test checks they agree
const JUMP_LAG = 50, REACH = 3;

// ---- raw inputs: human-equivalent only ---------------------------------------------------------------------------------------
const FOV_MAX = 110;
const HUD_FIELDS = ['hp', 'hunger', 'armor', 'hotbar', 'held', 'inventory', 'xp', 'scoreboard', 'chat', 'tnt_timer', 'title', 'zoom', 'bossbar'];
const FORBIDDEN = ['minimap', 'reach', 'distance', 'reach_display', 'freelook', 'coords', 'xyz', 'f3', 'truth', 'server_log', 'entities', 'opp_pos', 'radar'];
function validateObs(raw) {
  if (!raw || typeof raw !== 'object') return { ok: false, error: 'no observation' };
  for (const k of Object.keys(raw)) if (!['frame', 'hud', 'sound', 't', 'est'].includes(k)) return { ok: false, error: 'not an allowed input: ' + k };
  for (const k of Object.keys(raw.hud || {})) { if (FORBIDDEN.includes(k.toLowerCase())) return { ok: false, error: 'forbidden HUD field: ' + k }; if (!HUD_FIELDS.includes(k)) return { ok: false, error: 'HUD field not allowed: ' + k }; }
  if (raw.frame && raw.frame.fov != null && raw.frame.fov > FOV_MAX) return { ok: false, error: 'FOV above ' + FOV_MAX };
  if (raw.frame && raw.frame.view && !['first', 'f5'].includes(raw.frame.view)) return { ok: false, error: 'one view at a time: first or f5' };
  return { ok: true };
}

// ---- moves (the reflex's output, nA) ----------------------------------------------------------------------------------------
const MOVES = ['stay', 'forward', 'back', 'attack', 'bridge', 'break', ...T.ITEMS.map((i) => 'buy:' + i)];
const M = Object.fromEntries(MOVES.map((m, i) => [m, i]));
const NA = MOVES.length;

// the reflex's view of a frame (rawFrame) and the hand rule on it. raw.truth (logging only) is never read by features() or the rule.
function rawFrame(obs, call, state) {
  const raw = { x: obs.me.x, alive: obs.me.alive ? 1 : 0, atBase: obs.atBase ? 1 : 0, bl: obs.bridgeLeft, oe: obs.onEnemyIsland ? 1 : 0, edge: obs.edgeAhead,
    e: obs.enemy && obs.enemy.alive ? [Math.round(obs.enemy.dist * 100) / 100, obs.enemy.ahead ? 1 : 0] : null,
    iron: obs.inv.iron || 0, wool: obs.inv.wool || 0, shears: obs.inv.shears ? 1 : 0, cov: obs.enemyBed.covered ? 1 : 0, bed: obs.enemyBed.alive ? 1 : 0,
    call: call ? { code: call.code, args: { ...call.args } } : null };
  if (state && state.enemy.alive) raw.truth = { eDist: Math.abs(state.enemy.x - state.me.x) };
  return raw;
}
// the hand rule: hit an enemy in reach whatever the call (except when told to retreat or go home), else do the call
function rule(raw, call) {
  if (!raw.alive) return M.stay;
  const code = call ? call.code : null, e = raw.e;
  if (e && e[0] <= REACH && code !== 'RETREAT' && code !== 'HOME') return M.attack;
  switch (code) {
    case 'GET': return raw.x > 2 ? M.back : M.stay;
    case 'BUY': return raw.x > 3 ? M.back : M['buy:' + call.args.item];
    case 'BRIDGE': return raw.oe ? M.stay : raw.bl > 0 ? (raw.wool > 0 ? M.bridge : M.stay) : M.forward;
    case 'BREAK_BED': if (!raw.oe && raw.bl > 0) return raw.wool > 0 ? M.bridge : M.stay; return M.break;
    case 'FIGHT': if (!e) return M.stay; if (!e[1]) return M.back; return !raw.oe && raw.bl > 0 && raw.wool > 0 ? M.bridge : M.forward;   // across an unfinished bridge: keep bridging toward him
    case 'RETREAT': case 'HOME': return raw.x > 3 ? M.back : M.stay;
    case 'DEFEND': return raw.x > 1 ? M.back : M.stay;
    default: return M.stay;
  }
}
const fallback = (obs, call) => rule(rawFrame(obs, call), call);
const fallbackRaw = (raw) => rule(raw, raw.call);
// the night labeller (offline, hindsight): the same rule, with the enemy's TRUE distance from the truth log instead of my estimate
function nightLabel(raw) { if (!raw.call) return null; const r = raw.truth && raw.e ? { ...raw, e: [raw.truth.eDist, raw.e[1]] } : raw; return rule(r, raw.call); }
const NIN = 15 + T.CODES.length;
function features(raw) {
  const x = new Float64Array(NIN);
  x[0] = raw.x / 32; x[1] = raw.alive; x[2] = raw.atBase; x[3] = Math.min(1, raw.bl / 20); x[4] = raw.oe; x[5] = raw.edge == null ? 1 : Math.min(1, raw.edge / 6);
  x[6] = raw.e ? 1 : 0; x[7] = raw.e ? Math.min(1, raw.e[0] / 10) : 1; x[8] = raw.e ? raw.e[1] : 0; x[9] = Math.min(1, raw.iron / 32); x[10] = Math.min(1, raw.wool / 32);
  x[11] = raw.shears; x[12] = raw.cov; x[13] = raw.bed;
  if (raw.call) { const i = T.CODES.indexOf(raw.call.code); if (i >= 0) x[14 + i] = 1; if (raw.call.args.item) x[NIN - 1] = (T.ITEMS.indexOf(raw.call.args.item) + 1) / T.ITEMS.length; }
  return x;
}
// timed actions ("baseball"), re-estimated every tick by the core schedule (it fits tau to the gap itself):
//   jump-crit  gap = his distance - reach; fire CRIT_MID_MS before he is in reach so the first hit lands mid-fall
//   jump-gap   gap = distance to the end of my finished bridge; the jump leaves the ground JUMP_LAG after the key
// ids: the eyes number each approach (a new number once the gap grows again or stops shrinking for a while), because the core
// schedule fires (or drops) an id once. A jump-crit is only armed for an approach that starts CRIT_MIN_RUN blocks outside reach:
// closer than that there is no time to jump ahead of him, and the reflex just hits.
const CRIT_MIN_RUN = 2;
const FORWARD_CALLS = new Set(['BRIDGE', 'BREAK_BED', 'FIGHT']);   // the calls whose rule walks toward the enemy island
function timedTargets(obs, call) {
  const out = [], code = call ? call.code : null;
  if (!obs.me.alive) return out;
  if (obs.enemy && obs.enemy.alive && obs.enemy.dist > REACH && !(obs.enemy.approachFrom < CRIT_MIN_RUN) && code !== 'RETREAT' && code !== 'HOME') out.push({ id: 'crit:' + obs.enemy.approach, action: 'jump_crit', lagMs: CRIT_MID_MS, gap: obs.enemy.dist - REACH });
  if (obs.edgeAhead != null && obs.edgeAhead <= 6 && FORWARD_CALLS.has(code)) out.push({ id: 'edge:' + obs.edgeRun, action: 'jump_gap', lagMs: JUMP_LAG, gap: obs.edgeAhead });
  return out;
}

// ---- plan memory: how the current step is going (done / going / blocked + progress) -------------------------------------------
function judge(step, obs) {
  if (!obs.me.alive) return { status: 'going' };   // respawning: no progress number, so no "stalled"
  const ev = obs.events || [], inv = obs.inv || {};
  switch (step.kind) {
    case 'get_resources': { const res = step.res || 'iron', n = step.n || 16; if ((inv[res] || 0) >= n) return { status: 'done' }; return { status: 'going', progress: obs.me.x <= 2 ? 100 + (inv[res] || 0) : -obs.me.x }; }
    case 'buy_blocks': case 'buy': {
      const item = step.kind === 'buy' ? step.item : 'wool';
      if (ev.includes('bought:' + item) || (T.PERMANENT.has(item) && inv[item])) return { status: 'done' };
      const [cur, cost] = T.PRICE[item]; if (obs.atBase && (inv[cur] || 0) < cost) return { status: 'blocked', why: 'need ' + cost + ' ' + cur + ' for ' + item };
      return { status: 'going', progress: -obs.me.x };
    }
    case 'bridge': if (obs.onEnemyIsland) return { status: 'done' }; if (obs.bridgeLeft > 0 && !(inv.wool > 0) && obs.me.x >= 6) return { status: 'blocked', why: 'out of wool' }; return { status: 'going', progress: obs.me.x + 20 - obs.bridgeLeft };
    case 'break_bed':
      if (!obs.enemyBed.alive) return { status: 'done' };
      if (obs.enemyBed.covered && !inv.shears && obs.onEnemyIsland) return { status: 'blocked', why: 'the bed is covered in wool: shears needed' };
      if (obs.bridgeLeft > 0 && !(inv.wool > 0) && obs.me.x >= 6) return { status: 'blocked', why: 'out of wool' };
      return { status: 'going', progress: obs.me.x + (obs.bedWork || 0) };
    case 'fight': if (!obs.enemy || !obs.enemy.alive || obs.enemy.dist > T.DONE_RANGE) return { status: 'done' }; return { status: 'going', progress: 10 * (obs.hits || 0) - obs.enemy.dist };
    case 'retreat': if (!obs.enemy || obs.enemy.dist > 6) return { status: 'done' }; return { status: 'going', progress: obs.enemy.dist };
    case 'defend': if (!obs.myBedThreat && (!obs.enemy || obs.enemy.dist > 10)) return { status: 'done' }; return { status: 'going', progress: obs.hits || 0 };
    case 'home': if (obs.atBase) return { status: 'done' }; return { status: 'going', progress: -obs.me.x };
    case 'hold': return { status: 'done' };
    default: return { status: 'going' };
  }
}
const interrupted = (obs) => ((obs.events || []).includes('died') ? 'died' : null);
const stepsFromCalls = (calls) => T.withIds((calls || []).map(T.stepOf), []);
// the stand-in slow brain (core/loop.js standInBrain uses it): the rule-correct plan for what is seen
const planner = (obs, done) => T.repair([T.makeStep('bridge'), T.makeStep('break_bed')], obs, done);

function describe(obs) {
  const where = !obs.me.alive ? 'You are dead, respawning at your base' : obs.onEnemyIsland ? 'You are on the ENEMY island' : obs.atBase ? 'You are on YOUR OWN island' : 'You are on your bridge';
  const inv = obs.inv || {};
  return where + ', health ' + obs.me.hp + '/20. Carrying ' + (inv.iron || 0) + ' iron, ' + (inv.wool || 0) + ' wool' + (inv.shears ? ', shears' : '') + '. ' +
    (obs.bridgeLeft > 0 ? 'Bridge: ' + obs.bridgeLeft + ' blocks still to place. ' : 'Bridge: finished (a small gap to jump). ') +
    (obs.enemy && obs.enemy.alive ? 'Enemy player about ' + Math.round(obs.enemy.dist) + ' blocks ' + (obs.enemy.ahead ? 'ahead' : 'behind') + '. ' : 'No enemy player in sight. ') +
    'Enemy bed: ' + (obs.enemyBed.alive ? 'standing' + (obs.enemyBed.covered ? ', covered in wool' : '') : 'broken') + '.';
}

// ---- the practice model (see the header: coarse, ours, not Bedwars physics) -----------------------------------------------------
const P = { SPEED: 0.25, BASE: 3, GEN_X: 2, MY_EDGE: 6, ENEMY_EDGE: 26, FRONT_DONE: 24, BED_X: 29.5, GEN_EVERY: 8, PLACE_EVERY: 8, BUY_EVERY: 10, HIT_EVERY: 10,
  ENEMY_HIT_EVERY: 12, MY_DMG: 4, CRIT_DMG: 6, ENEMY_DMG: 3, KNOCKOFF_P: 0.35, SWING_GRACE: 10, RESPAWN_MS: 5000, COVER_TICKS: 20, BED_TICKS: 30, RUSH_AT_X: 14, ENEMY_SPEED: 0.2, EDGE_WIN: 75 };
function init(seed, o) {
  o = o || {}; const r = rng(seed * 4241 + 9);
  return { tick: 0, rs: (seed * 2654435761 + 1) >>> 0, me: { x: P.GEN_X, alive: true, hp: 20, respawnAt: 0 }, inv: { iron: 0, gold: 0, wool: 0, shears: 0 },
    front: P.MY_EDGE, placeT: 0, lastBuy: -99, lastHit: -99, lastSwing: -99, jumps: [], crits: [], edgeA: { n: 0, best: null }, critA: { n: 0, best: null },
    enemy: { x: 29, alive: true, hp: 20, rushing: false, lastHit: -99, respawnAt: 0 },
    bedAlive: true, covered: o.covered != null ? !!o.covered : r() < 0.5, coverSeen: false, coverT: 0, bedT: 0, events: [],
    stats: { deaths: 0, voids: 0, kills: 0, hits: 0, critHits: 0, crossings: 0, edgeFalls: 0, bought: [] }, noise: o.noise == null ? 0.05 : o.noise };
}
function gauss(r) { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }
function observe(s, tMs) {
  const r = rng((s.rs ^ (s.tick * 2246822519)) >>> 0), e = s.enemy, me = s.me, onEnemy = me.x >= P.ENEMY_EDGE;
  const seen = me.alive && e.alive && Math.abs(e.x - me.x) <= 16;
  return { t: tMs, me: { x: Math.round(me.x * 100) / 100, alive: me.alive, hp: me.hp }, inv: { ...s.inv }, atBase: !me.alive || me.x <= P.BASE,
    bridgeLeft: Math.max(0, Math.ceil(P.FRONT_DONE - s.front - 1e-9)), onEnemyIsland: me.alive && onEnemy, edgeRun: s.edgeA.n,
    edgeAhead: me.alive && !onEnemy && s.front >= P.FRONT_DONE ? Math.max(0, s.front - me.x + s.noise * 0.2 * gauss(r)) : null,
    enemy: seen ? { dist: Math.max(0, Math.abs(e.x - me.x) + s.noise * gauss(r)), ahead: e.x >= me.x, alive: true, approach: s.critA.n, approachFrom: s.critA.from } : null,
    enemyBed: { alive: s.bedAlive, covered: s.coverSeen && s.covered }, myBedThreat: false, hits: s.stats.hits, bedWork: s.coverT + s.bedT, events: s.events.slice() };
}
function die(s, t, why) {
  s.me.alive = false; s.me.respawnAt = t + P.RESPAWN_MS; s.inv.iron = 0; s.inv.gold = 0; s.inv.wool = 0; s.jumps = []; s.crits = [];
  s.stats.deaths++; if (why === 'void') s.stats.voids++; s.events.push('died'); if (why === 'void') s.events.push('void'); s.enemy.rushing = false;
}
function forward(s, t, contacts) {
  const x0 = s.me.x; let x1 = x0 + P.SPEED;
  if (x0 < P.ENEMY_EDGE) {
    if (s.front < P.FRONT_DONE) x1 = Math.min(x1, Math.max(x0, s.front - 0.5));   // an unfinished bridge: stop at its end (sneak)
    else if (x1 >= s.front) {   // the end of the finished bridge: a timed jump crosses the gap, anything else falls
      const tc = t + (s.front - x0) / P.SPEED * TICK; contacts.push({ id: 'edge:' + s.edgeA.n, atMs: tc }); s.edgeA.n++; s.edgeA.best = null;
      if (s.jumps.some((j) => Math.abs(j - tc) <= P.EDGE_WIN)) { x1 = P.ENEMY_EDGE + 0.2; s.stats.crossings++; s.events.push('crossed'); s.jumps = []; }
      else { s.stats.edgeFalls++; die(s, t, 'void'); return; }
    }
  }
  s.me.x = Math.min(P.BED_X, x1);
}
// the eyes' approach numbering for timed targets: same number while the gap keeps closing (pauses up to STILL_TICKS allowed),
// a new one when it grows by APART, stalls longer, or the thing goes out of sight
const STILL_TICKS = 8, APART = 0.5;
function renumber(a, gap) {
  if (gap == null) { if (a.best != null) { a.n++; a.best = null; } return; }
  if (a.best == null) { a.best = gap; a.from = gap; a.still = 0; return; }
  if (gap > a.best + APART || a.still >= STILL_TICKS) { a.n++; a.best = gap; a.from = gap; a.still = 0; return; }
  if (gap < a.best - 1e-6) { a.best = gap; a.still = 0; } else a.still++;
}
function step(s0, move, fired, tMs) {
  const s = { ...s0, edgeA: { ...s0.edgeA }, critA: { ...s0.critA }, me: { ...s0.me }, inv: { ...s0.inv }, enemy: { ...s0.enemy }, stats: { ...s0.stats, bought: s0.stats.bought.slice() }, jumps: s0.jumps.slice(), crits: s0.crits.slice(), events: [], tick: s0.tick + 1 };
  const r = rng((s.rs + s.tick * 7477) >>> 0), contacts = [], me = s.me, e = s.enemy, t = tMs;
  for (const f of fired || []) { if (f.action === 'jump_gap') s.jumps.push(f.atMs + JUMP_LAG); if (f.action === 'jump_crit') s.crits.push(f.atMs); }
  const d0 = Math.abs(e.x - me.x), x0 = me.x;
  if (!me.alive) { if (t >= me.respawnAt) { me.alive = true; me.hp = 20; me.x = P.GEN_X; s.events.push('respawned'); } }
  else {
    if (me.x <= P.GEN_X + 1e-9 && s.tick % P.GEN_EVERY === 0) s.inv.iron = Math.min(64, s.inv.iron + 1);
    if (me.x >= 18) s.coverSeen = true;
    if (move === M.forward || (move === M.bridge && me.x < s.front - 0.6) || (move === M.break && me.x < P.BED_X)) forward(s, t, contacts);
    else if (move === M.back) { if (me.x >= P.ENEMY_EDGE && me.x - P.SPEED < P.ENEMY_EDGE) me.x = s.front - 0.1; else me.x = Math.max(0, me.x - P.SPEED); }   // the way back over the gap is not timed (ours)
    else if (move === M.bridge) {   // bridging moves me on smoothly (a block every PLACE_EVERY ticks), the block's wool is spent when it is down
      if (s.front < P.FRONT_DONE && s.inv.wool > 0) { const last = ++s.placeT >= P.PLACE_EVERY; s.front = last ? Math.round(s.front + 1 / P.PLACE_EVERY) : s.front + 1 / P.PLACE_EVERY; if (last) { s.placeT = 0; s.inv.wool--; s.events.push('placed'); } me.x = s.front - 0.5; }
    }
    else if (move === M.attack) {
      s.lastSwing = s.tick;
      if (e.alive && d0 <= REACH && s.tick - s.lastHit >= P.HIT_EVERY) {
        s.lastHit = s.tick; const crit = s.crits.some((f) => t >= f + CRIT_WINDOW.from && t <= f + CRIT_WINDOW.to);
        e.hp -= crit ? P.CRIT_DMG : P.MY_DMG; s.stats.hits++; if (crit) s.stats.critHits++; s.events.push(crit ? 'crit' : 'hit'); e.x += e.x >= me.x ? 1 : -1; if (e.x > s.front && e.x < P.ENEMY_EDGE) e.x = P.ENEMY_EDGE + 0.1;
        if (e.hp <= 0) { e.alive = false; e.respawnAt = t + P.RESPAWN_MS; e.rushing = false; s.stats.kills++; s.events.push('kill'); }
      }
    } else if (move === M.break && me.x >= P.BED_X - 1e-9 && s.bedAlive) {
      if (s.covered) { if (s.inv.shears && ++s.coverT >= P.COVER_TICKS) { s.covered = false; s.events.push('uncovered'); } }
      else if (++s.bedT >= P.BED_TICKS) { s.bedAlive = false; s.events.push('bed_broken'); }
    } else if (move >= M['buy:wool'] && me.x <= P.BASE && s.tick - s.lastBuy >= P.BUY_EVERY) {
      const item = T.ITEMS[move - M['buy:wool']], [cur, cost] = T.PRICE[item];
      if (s.inv[cur] >= cost && !(T.PERMANENT.has(item) && s.inv[item])) { s.lastBuy = s.tick; s.inv[cur] -= cost; if (item === 'wool') s.inv.wool += T.WOOL_PER_BUY; else s.inv[item] = 1; s.stats.bought.push(item); s.events.push('bought:' + item); }
    }
  }
  // the scripted defender: guards its bed; comes at me once I am past the middle of my bridge; hits every 0.6 s; a hit on the bridge
  // while I am not hitting back may knock me off
  if (!e.alive) { if (s.bedAlive && t >= e.respawnAt) { e.alive = true; e.hp = 20; e.x = 29; } }
  else if (me.alive) {
    if (me.x >= P.RUSH_AT_X) e.rushing = true;
    const minX = s.front >= P.FRONT_DONE ? P.MY_EDGE + 0.5 : P.ENEMY_EDGE;
    if (e.rushing && Math.abs(e.x - me.x) > 2.5) e.x = Math.max(minX, e.x + (me.x < e.x ? -P.ENEMY_SPEED : P.ENEMY_SPEED));
    if (Math.abs(e.x - me.x) <= REACH && s.tick - e.lastHit >= P.ENEMY_HIT_EVERY) {
      e.lastHit = s.tick; me.hp -= P.ENEMY_DMG; me.x = Math.max(0, me.x + (me.x < e.x ? -0.6 : 0.6)); if (me.x > s.front && me.x < P.ENEMY_EDGE) me.x = x0 >= P.ENEMY_EDGE ? P.ENEMY_EDGE + 0.1 : s.front - 0.1; s.events.push('hurt');
      const onBridge = me.x > P.MY_EDGE && me.x < P.ENEMY_EDGE;
      if (onBridge && s.tick - s.lastSwing > P.SWING_GRACE && r() < P.KNOCKOFF_P) die(s, t, 'void');   // not fighting back on the bridge else if (me.hp <= 0) die(s, t, 'killed');
    }
  }
  const d1 = Math.abs(e.x - me.x);
  if (e.alive && me.alive && d0 > REACH && d1 <= REACH) { contacts.push({ id: 'crit:' + s.critA.n, atMs: t + TICK * (d0 - REACH) / Math.max(1e-6, d0 - d1) }); s.critA.n++; s.critA.best = null; }
  renumber(s.critA, e.alive && me.alive && d1 > REACH && d1 <= 16 ? d1 - REACH : null);
  renumber(s.edgeA, me.alive && me.x < P.ENEMY_EDGE && s.front >= P.FRONT_DONE && s.front - me.x <= 6.5 ? s.front - me.x : null);
  s.crits = s.crits.filter((f) => f > t - 1000);
  return { state: s, contacts };
}
const done = (s) => !s.bedAlive || s.tick >= MAX_TICKS;
const outcome = (s) => ({ goalDone: !s.bedAlive, ticks: s.tick, ...s.stats, covered: s.covered });

// ---- day data for sleep from the truth log (cards for Nanbeige, rewards, labels): read-only wrappers over truthlog.js ------------
const sleepData = {
  nightPlay: false,   // Ben: no self-play, no practice games at night
  cards: (day) => require('./truthlog').cards(day.calls, day.events, day.me || 'GlimBot'),
  rewards: (day) => require('./truthlog').rewards(day.events, day.me || 'GlimBot'),
  labels: (day) => require('./truthlog').hindsight((day.frames || []).map((f) => f.t), day.events, day.me || 'GlimBot'),
  goal: (day) => require('./truthlog').goalScore(day.events, day.me || 'GlimBot', day.plan || T.RUSH_PLAN, day.planLog)
};

module.exports = { name: 'bedwars', tickMs: TICK, maxTicks: MAX_TICKS, vocab: T.vocab, nIn: NIN, nA: NA, goal: 'break the enemy bed', realtime: true, frameToKeyMs: FRAME_TO_KEY_MS,
  init, observe, planner, judge, fallback, fallbackRaw, rawFrame, features, nightLabel, timedTargets, step, done, outcome, describe,
  repair: T.repair, urgent: T.urgent, interrupted, stepsFromCalls,
  MOVES, P, CRIT_MID_MS, CRIT_MIN_RUN, CRIT_WINDOW, validateObs, HUD_FIELDS, FORBIDDEN, FOV_MAX, sleepData };
