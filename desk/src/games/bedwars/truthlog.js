'use strict';
// Glim team, Bedwars side: the server truth log (BensPC `log-read` events, TOOLS.md) -> referee outputs. The truth log is the ONLY
// reward and referee (Ben's rule); nothing here reads a grader. Four outputs:
//   (a) rewards()     Ben's rules exactly: +1 per hit landed, -1 per hit taken, +5 kill, -5 death, -0.02 per second with no hit.
//                     A void death counts as a kill for the opponent if they hit the victim within the last 10 s (Ben 11-03; the 10 s
//                     window is ours). Reading as the live contract (research repo QONLY-ENV-CONTRACT.md §7): the idle -0.02 is charged
//                     at the end of every whole second from the match start in which I landed no hit, only while both players are alive;
//                     one kill per death, never two; my death costs -5 whatever the cause.
//   (b) hindsight()   labels for reflex distillation: true time-to-hit, time-to-taken-hit, time-to-edge, crit windows
//   (c) goalScore()   long horizon: which plan steps were completed, in order, with replans counted
//   (d) cards()       "worked / failed" text cards (call -> outcome) for Nanbeige's sleep. Text from the truth log only.
// Event fields (TOOLS.md v2: GlimTruthKit's logs\truth.jsonl; aliases accepted, see who()): hit {attacker, victim, damage, crit, via},
// kill {killer, victim, cause, final, void}, death {victim, killer, cause, final, void}, void_death {victim, killer, final},
// bed_broken {by, by_team, team}, purchase {player, item, cost?, currency?}, pickup {player, item, count}, block_place / block_break
// {player, block, x, y, z}, edge {player, x, y, z, og, last_supported_ms}, tick {arena, tick, p: [{n, x, y, z, vx, vy, vz, og, alive,
// hp, ...}]}, match_start {arena, match_id, teams}, match_end {winner_team, winners, why}. t = ISO text or ms (lines also carry ms).
// One death gives a death line, plus kill (if a killer) and void_death (if void), all with the same ms: deaths() merges them. Pure.
const { toMs, CRIT_WINDOW_MS, CRIT_MID_MS } = require('./timing');
const { VOCAB, parse } = require('./tactics');

const VOID_WINDOW_MS = 10000, IDLE_PER_S = 0.02, RESPAWN_MS = 5000, MERGE_MS = 1000;
const R = { hit: 1, taken: -1, kill: 5, death: -5 };
const VOID_CAUSE = /^(void|outofworld|out_of_world)/i;   // Paper's VOID / outOfWorld, BedWars1058's VOID and VOID_FINAL_KILL

const who = (e, keys) => { for (const k of keys) if (e[k] != null && e[k] !== '') return String(e[k]); return null; };
const attacker = (e) => who(e, ['attacker', 'by', 'damager', 'killer']);
const victim = (e) => who(e, ['victim', 'target', 'player']);
const killerOf = (e) => who(e, ['killer', 'attacker', 'by']);
const actor = (e) => who(e, ['player', 'by', 'breaker', 'attacker']);
// bed_broken from the plain server log has only {text} (glimtool.ps1 v1): "Red Bed was destroyed by GlimBot" -> breaker, team
const bedBreaker = (e) => who(e, ['by', 'breaker', 'player']) || ((String(e.text || '').match(/destroy\w*\s+by\s+(\w+)/i) || [])[1] || null);
const bedTeam = (e) => e.team != null ? String(e.team) : ((String(e.text || '').match(/(\w+)\s+bed\b/i) || [])[1] || null);

function normalize(events) {
  return (events || []).map((e, i) => ({ ...e, t: typeof e.ms === 'number' && Number.isFinite(e.ms) ? e.ms : toMs(e.t), _i: i }))   // GlimTruthKit lines carry ms.filter((e) => Number.isFinite(e.t) && e.type).sort((a, b) => a.t - b.t || a._i - b._i);
}
function span(ev, o) {
  const ms = ev.find((e) => e.type === 'match_start'), me = ev.slice().reverse().find((e) => e.type === 'match_end');
  const start = o && Number.isFinite(o.start) ? o.start : ms ? ms.t : ev.length ? ev[0].t : 0;
  const end = o && Number.isFinite(o.end) ? o.end : me ? me.t : ev.length ? ev[ev.length - 1].t : start;
  return { start, end };
}
// kill, death and void_death lines for one death are merged (same victim within MERGE_MS) -> [{t, victim, void, killer, final}]
function deaths(ev) {
  const out = [];
  for (const e of ev) {
    if (e.type !== 'death' && e.type !== 'void_death' && e.type !== 'kill') continue;
    const v = victim(e); if (!v) continue;
    const isVoid = e.type === 'void_death' || (e.cause != null && VOID_CAUSE.test(String(e.cause))) || e.void === true;
    const k = e.type === 'kill' || e.type === 'death' ? killerOf(e) : null;
    const d = out.find((x) => x.victim === v && Math.abs(x.t - e.t) <= MERGE_MS);
    if (d) { d.void = d.void || isVoid; d.killer = d.killer || k; d.final = d.final || !!e.final; d.t = Math.min(d.t, e.t); }
    else out.push({ t: e.t, victim: v, void: isVoid, killer: k, final: !!e.final });
  }
  return out;
}
// who gets the kill: a void death -> whoever hit the victim last within [t - 10 s, t] (the server's credit is ignored); else the killer
function credit(d, hits) {
  if (!d.void) return d.killer && d.killer !== d.victim ? d.killer : null;
  let best = null;
  for (const h of hits) if (h.victim === d.victim && h.attacker && h.attacker !== d.victim && h.t <= d.t && h.t >= d.t - VOID_WINDOW_MS) best = h;
  return best ? best.attacker : null;
}

// (a) rewards for `me`. o: {opp, start, end, respawnMs} -> {total, parts, timeline:[{t, r, why}]}
function rewards(events, me, o) {
  o = o || {}; const ev = normalize(events), { start, end } = span(ev, o), respawn = o.respawnMs == null ? RESPAWN_MS : o.respawnMs;
  const hits = ev.filter((e) => e.type === 'hit').map((e) => ({ t: e.t, attacker: attacker(e), victim: victim(e) }));
  const inWin = (t) => t >= start && t <= end;
  const parts = { hits: 0, taken: 0, kills: 0, deaths: 0, idle: 0 }, timeline = [];
  const add = (t, r, why, k) => { parts[k] += r; timeline.push({ t, r, why }); };
  for (const h of hits) { if (!inWin(h.t)) continue; if (h.attacker === me) add(h.t, R.hit, 'hit', 'hits'); if (h.victim === me) add(h.t, R.taken, 'hit taken', 'taken'); }
  const ds = deaths(ev);
  for (const d of ds) {
    if (!inWin(d.t)) continue;
    if (d.victim === me) add(d.t, R.death, d.void ? 'death (void)' : 'death', 'deaths');
    else if (credit(d, hits) === me) add(d.t, R.kill, d.void ? 'kill (void, hit within 10 s)' : 'kill', 'kills');
  }
  // idle: whole seconds from the start with no hit by me, both alive the whole second
  const opp = o.opp || (hits.find((h) => h.attacker === me && h.victim) || {}).victim || (hits.find((h) => h.victim === me && h.attacker) || {}).attacker || null;
  const deadSpans = ds.filter((d) => d.victim === me || (opp && d.victim === opp)).map((d) => [d.t, d.final ? Infinity : d.t + respawn]);
  const myHits = hits.filter((h) => h.attacker === me).map((h) => h.t);
  for (let s = start; s + 1000 <= end; s += 1000) {
    const e = s + 1000;
    if (myHits.some((t) => t >= s && t < e)) continue;
    if (deadSpans.some(([a, b]) => a < e && b > s)) continue;
    add(e, -IDLE_PER_S, 'no hit this second', 'idle');
  }
  timeline.sort((a, b) => a.t - b.t);
  const total = Object.values(parts).reduce((a, b) => a + b, 0);
  // hitsLogged = 0 means the hit lines (our truth.jsonl) were missing: hits, the idle charge and void kills are then NOT measurable
  return { total: Math.round(total * 1e6) / 1e6, parts: { ...parts, idle: Math.round(parts.idle * 1e6) / 1e6 }, timeline, start, end, opp, hitsLogged: hits.length };
}

// (b) hindsight labels at each frame time. o: {horizonMs} -> [{t, ttHitMs, ttTakenMs, ttEdgeMs, critJumpTtgMs, critNow}]
function hindsight(frameTimes, events, me, o) {
  const H = (o && o.horizonMs) || 2000, ev = normalize(events);
  const mine = ev.filter((e) => e.type === 'hit' && attacker(e) === me).map((e) => e.t);
  const taken = ev.filter((e) => e.type === 'hit' && victim(e) === me).map((e) => e.t);
  const edges = ev.filter((e) => e.type === 'edge' && actor(e) === me).map((e) => e.t);
  const next = (xs, t) => { for (const x of xs) if (x >= t) return x - t <= H ? x - t : null; return null; };
  return (frameTimes || []).map((f) => {
    const t = toMs(f), h = next(mine, t);
    const crit = mine.find((x) => x - CRIT_MID_MS >= t - 25 && x - t <= H + CRIT_MID_MS);
    return { t, ttHitMs: h, ttTakenMs: next(taken, t), ttEdgeMs: next(edges, t), critJumpTtgMs: crit != null ? crit - CRIT_MID_MS - t : null,
      critNow: mine.some((x) => x - t >= CRIT_WINDOW_MS.from && x - t <= CRIT_WINDOW_MS.to) };
  });
}

// (c) the long-horizon goal scorer. plan: [{step, ...params}] or step names; planLog: our own [{t, type: 'replan', reason}]
// BedWars1058 shop ids (our shop.yml: wool, clay, glass, stone = end stone, ladder, wood, obsidian) plus older spellings
const BLOCK_ITEMS = new Set(['wool', 'wood', 'endstone', 'end_stone', 'stone', 'clay', 'hardened_clay', 'glass', 'planks', 'obsidian']);
const STEP_CHECK = {
  get_resources: (p) => ({ need: p.n || 16, count: (e, me) => e.type === 'pickup' && actor(e) === me && String(e.item || '').toLowerCase().includes(p.res || 'iron') ? Number(e.count || e.amount || 1) : 0 }),
  buy_blocks: () => ({ need: 1, count: (e, me) => e.type === 'purchase' && actor(e) === me && BLOCK_ITEMS.has(String(e.item || '').toLowerCase()) ? 1 : 0 }),
  bridge: (p) => ({ need: p.n || 8, count: (e, me) => e.type === 'block_place' && actor(e) === me ? 1 : 0 }),
  break_bed: (p) => ({ need: 1, count: (e, me) => e.type === 'bed_broken' && bedBreaker(e) === me && (!p.myTeam || String(bedTeam(e) || '').toLowerCase() !== String(p.myTeam).toLowerCase()) ? 1 : 0 })
};
function goalScore(events, me, plan, planLog) {
  const ev = normalize(events), steps = (plan || []).map((s) => typeof s === 'string' ? { step: s } : s), skipped = steps.filter((s) => !STEP_CHECK[s.step]).map((s) => s.step);
  const checks = steps.filter((s) => STEP_CHECK[s.step]).map((s) => ({ step: s.step, ...STEP_CHECK[s.step](s), done: false, t: null }));
  const myDeaths = deaths(ev).filter((d) => d.victim === me).map((d) => d.t);
  let i = 0, have = 0;
  for (const e of ev) {
    if (i >= checks.length) break;
    if ((e.type === 'death' || e.type === 'void_death' || e.type === 'kill') && victim(e) === me) { have = 0; continue; }   // death: the step in progress starts over
    have += checks[i].count(e, me);
    if (have >= checks[i].need) { checks[i].done = true; checks[i].t = e.t; i++; have = 0; }
  }
  const replans = (planLog || []).filter((x) => x.type === 'replan').map((x) => ({ ...x, t: toMs(x.t) }));
  const interruptions = myDeaths.length;
  const replanAfterInterruption = replans.some((r) => myDeaths.some((d) => r.t >= d && r.t - d <= 10000));
  const completed = checks.filter((c) => c.done).length;
  return { steps: checks.map((c) => ({ step: c.step, done: c.done, t: c.t })), completed, total: checks.length, finished: checks.length > 0 && completed === checks.length,
    inOrder: true, replans: replans.length, interruptions, replanAfterInterruption, skipped,
    durationMs: completed && ev.length ? checks[completed - 1].t - (span(ev).start) : null };
}

// (d) "worked / failed" cards. calls: our own call log [{t, text}] -> [{t, call, worked, text}] (identical consecutive calls merge)
const WINDOW = { pvp: 3000, move: 10000, econ: 30000, bed: 45000 };
function cards(calls, events, me) {
  const ev = normalize(events), cs = (calls || []).map((c) => ({ t: toMs(c.t), text: String(c.text || '').trim() })).filter((c) => Number.isFinite(c.t) && c.text).sort((a, b) => a.t - b.t);
  const merged = []; for (const c of cs) { const last = merged[merged.length - 1]; if (last && last.text === c.text) continue; merged.push(c); }
  const out = [], ds = deaths(ev);
  merged.forEach((c, k) => {
    const p = parse(c.text); if (!p.ok) return;
    const first = p.calls[0], spec = VOCAB[first.code], until = Math.min(k + 1 < merged.length ? merged[k + 1].t : Infinity, c.t + WINDOW[spec.group]);
    const w = ev.filter((e) => e.t >= c.t && e.t < until), dw = ds.filter((d) => d.t >= c.t && d.t < until);
    const landed = w.filter((e) => e.type === 'hit' && attacker(e) === me), taken = w.filter((e) => e.type === 'hit' && victim(e) === me);
    const crits = landed.filter((e) => e.crit === true).length, died = dw.some((d) => d.victim === me), fell = dw.some((d) => d.victim === me && d.void);
    const killed = dw.some((d) => d.victim !== me && credit(d, ev.filter((e) => e.type === 'hit').map((e) => ({ t: e.t, attacker: attacker(e), victim: victim(e) }))) === me);
    const firstHit = w.find((e) => e.type === 'hit' && (attacker(e) === me || victim(e) === me));
    let worked = null, why = '';
    const fight = landed.length + ' landed' + (crits ? ' (' + crits + ' crit)' : '') + ', ' + taken.length + ' taken' + (killed ? ', kill' : '') + (died ? ', I died' : '');
    if (spec.group === 'pvp') {
      if (first.code === 'jc') { worked = crits > 0 && !died; why = worked ? 'the crit landed: ' + fight : (firstHit && victim(firstHit) === me ? 'I got hit first: ' : 'no crit: ') + fight; }
      else if (first.code === 'bo') { worked = taken.length === 0 && !died; why = worked ? 'got away clean' : 'still got hit: ' + fight; }
      else if (!landed.length && !taken.length && !killed && !died) return;   // nothing happened: no card
      else { worked = (landed.length > taken.length || killed) && !died; why = (!worked && firstHit && victim(firstHit) === me ? 'I got hit first: ' : '') + fight; }
    } else if (first.code === 'br') { const n = w.filter((e) => e.type === 'block_place' && actor(e) === me).length; worked = n >= first.params.n && !fell; why = 'placed ' + n + '/' + first.params.n + (fell ? ', fell into the void' : ''); }
    else if (first.code === 'jg') { worked = !fell; why = fell ? 'fell into the void' : 'made it across'; }
    else if (first.code === 'buy') { worked = w.some((e) => e.type === 'purchase' && actor(e) === me && String(e.item || '').toLowerCase() === first.params.item); why = worked ? 'bought it' : 'no purchase'; }
    else if (first.code === 'get') { const n = w.filter((e) => e.type === 'pickup' && actor(e) === me && String(e.item || '').toLowerCase().includes(first.params.res)).reduce((a, e) => a + Number(e.count || e.amount || 1), 0); worked = n >= first.params.n; why = 'picked up ' + n + '/' + first.params.n + ' ' + first.params.res; }
    else if (first.code === 'bb') { worked = w.some((e) => e.type === 'bed_broken' && bedBreaker(e) === me); why = worked ? 'bed broken' : 'bed still standing'; }
    else if (first.code === 'db') { const lost = w.some((e) => e.type === 'bed_broken' && bedBreaker(e) !== me); worked = !lost && !died; why = lost ? 'my bed was broken' : died ? 'I died' : 'bed held'; }
    else return;   // rb: the truth log cannot tell
    out.push({ t: c.t, call: c.text, worked, text: 'I called "' + c.text + '" -> ' + (worked ? 'it worked: ' : 'it failed: ') + why + '.' });
  });
  return out;
}

// per-tick rows of one player from `tick` events -> [{t, x, y, z, vx, vy, vz, og, alive, hp, yaw, pitch}] (for hindsight / eyes labels)
function track(events, name) {
  const out = [];
  for (const e of normalize(events)) {
    if (e.type !== 'tick' || !Array.isArray(e.p)) continue;
    const r = e.p.find((x) => x && x.n === name); if (!r) continue;
    out.push({ t: e.t, x: r.x, y: r.y, z: r.z, vx: r.vx, vy: r.vy, vz: r.vz, og: r.og === 1 || r.og === true, alive: r.alive === 1 || r.alive === true, hp: r.hp, yaw: r.yaw, pitch: r.pitch });
  }
  return out;
}

module.exports = { track, bedBreaker, bedTeam, VOID_WINDOW_MS, IDLE_PER_S, RESPAWN_MS, R, normalize, deaths, credit, rewards, hindsight, goalScore, cards, STEP_CHECK };
