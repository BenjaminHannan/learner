'use strict';
// Imagining ahead (ingredients plan step 5).
//
// Level 1 (tiny): before Glim speaks, the speak-o-meter compares "speak now" with "wait ~5 min". futures() turns the guesser's
//   prediction of the next state into a few weighted future contexts (the next app category Ben is likely in, and the chance he
//   takes a break soon); SpeakOMeter.decideAhead() scores each and defers when waiting is clearly better. Never for urgent says.
//
// Level 2: lookahead in the sandbox games. A proposer suggests a few moves (Nanbeige through a Mote in the app; a random / fake
//   proposer in tests), each one is IMAGINED, the imagined outcome is scored (game result or the game's value), then Glim acts.
//   Phase 1 imagines with the game's own rules: this is "planning with the rulebook", NOT a learned world model. For two-player
//   games the rulebook gives only OUR move; the opponent is unknown, so every possible reply is imagined and the worst one counts
//   (we do not peek at the opponent's real policy). A hook (o.predictAfter) lets a learned guesser predict "the state after move a"
//   later; when it returns a state it is used instead of the rulebook and the plan is marked `learned`.
// Pure JS.

// ---- level 1 ----------------------------------------------------------------------------------------------------------------
// guesser: { predict('app') -> {cat: p} }; breakSoon(): chance Ben takes a break in the next ~5 min (null = unknown -> 0).
// -> [{ w, ctx: { cat, act, minsSinceSay, surprise } }] whose weights sum to 1
function futures(ctx, o) {
  o = o || {}; ctx = ctx || {};
  const horizon = o.horizonMin || 5;
  const later = (ctx.minsSinceSay == null ? null : ctx.minsSinceSay + horizon);
  let pBreak = 0; try { pBreak = Math.max(0, Math.min(1, Number(o.breakSoon ? o.breakSoon(ctx) : 0) || 0)); } catch (e) { pBreak = 0; }
  let dist = null; try { dist = o.guesser && o.guesser.predict ? o.guesser.predict('app') : null; } catch (e) { dist = null; }
  if (!dist || !Object.keys(dist).length) dist = { [ctx.cat || 'other']: 1 };
  const out = [];
  // a break = Ben stops what he is doing and is between things (at the Mac, not in the game / video / typing). Not "idle": the
  // speak-o-meter reads 2+ minutes without input as "maybe not there" (a weak no), which is a different moment.
  if (pBreak > 0) out.push({ w: pBreak, ctx: { cat: 'other', act: 'active', minsSinceSay: later, surprise: 0, stuckError: false, stuckPage: false, brk: true } });
  const tot = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  for (const [cat, p] of Object.entries(dist)) {
    const w = (1 - pBreak) * p / tot; if (w < 1e-3) continue;
    const act = cat === 'video' ? 'video' : cat === 'game' ? 'game' : 'active';
    out.push({ w, ctx: { cat, act, minsSinceSay: later, surprise: 0, stuckError: cat === ctx.cat ? !!ctx.stuckError : false, stuckPage: false } });
  }
  const s = out.reduce((a, f) => a + f.w, 0) || 1; for (const f of out) f.w /= s;
  return out;
}

// ---- level 2 ----------------------------------------------------------------------------------------------------------------
// imagine one move: -> { state, source: 'rulebook' | 'learned', branches (two-player: the imagined replies) }
function imagineMove(game, state, move, o) {
  o = o || {};
  if (o.predictAfter) { try { const s = o.predictAfter(state, move); if (s) return { state: s, source: 'learned', branches: [s] }; } catch (e) { /* fall back to the rulebook */ } }
  if (game.apply && game.replies) {
    const mine = game.apply(state, move); if (!mine) return { state: null, source: 'rulebook', branches: [] };
    if (game.done(mine)) return { state: mine, source: 'rulebook', branches: [mine] };
    const br = game.replies(mine);
    return { state: mine, source: 'rulebook', branches: br.length ? br : [mine] };
  }
  const s = game.step(state, move);
  return { state: s, source: 'rulebook', branches: [s] };
}
const leaf = (game, s) => { const r = game.result(s); return r != null ? r : game.value(s); };
// value of a move: worst imagined reply; with depth 2, our best follow-up after each reply (still with the worst reply)
function moveValue(game, state, move, depth, o) {
  const im = imagineMove(game, state, move, o);
  if (!im.state) return { v: -1, source: im.source };
  let worst = Infinity;
  for (const b of im.branches) {
    let v = leaf(game, b);
    if (depth > 1 && game.result(b) == null) {
      let best = -Infinity;
      for (const m2 of game.moves(b)) { const r = moveValue(game, b, m2, depth - 1, o); if (r.v > best) best = r.v; }
      if (best > -Infinity) v = Math.max(v * 0.5, best * 0.98);   // a little discount: sooner is better
    }
    if (v < worst) worst = v;
  }
  return { v: worst, source: im.source };
}
// propose -> imagine -> score -> pick. -> { move, value, proposals, values, source }
function plan(game, state, proposals, o) {
  o = o || {};
  const legal = (proposals || []).filter((m) => m != null);
  if (!legal.length) return { move: null, value: null, proposals: [], values: [], source: 'none' };
  const vals = legal.map((m) => moveValue(game, state, m, o.depth || 1, o));
  // a repeat of a state seen in this game is a last resort (no ping-pong between two equal moves)
  const seen = o.seen || null;
  let best = 0;
  for (let i = 0; i < legal.length; i++) {
    const rep = (j) => (seen && game.key ? seen.has(game.key(imagineMove(game, state, legal[j], o).state || state)) : false);
    const a = vals[i].v - (rep(i) ? 0.5 : 0), b = vals[best].v - (rep(best) ? 0.5 : 0);
    if (a > b) best = i;
  }
  return { move: legal[best], value: vals[best].v, proposals: legal, values: vals.map((x) => x.v), source: vals[best].source };
}

// a random proposer (tests and the "act at once" baseline): k distinct legal moves, seeded per state
function randomProposer(k, seed) {
  const { rng } = require('./games');
  let n = 0;
  return (state, game) => {
    const r = rng((seed || 1) * 7919 + (++n) * 104729); const ms = game.moves(state).slice();
    for (let i = ms.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [ms[i], ms[j]] = [ms[j], ms[i]]; }
    return ms.slice(0, k || 3);
  };
}
// a model proposer: ask (messages) -> text; JSON {"moves": ["...", ...]} parsed with the game's own parser (illegal ones dropped).
// -> async (state, game) -> { moves, raw, filled }
const PROPOSE_SYSTEM = 'You are playing a small game. Suggest up to 3 good next moves. Reply with ONE JSON object and nothing else: {"moves": ["move", "move", "move"]}, best first, each written exactly like the examples.';
function modelProposer(ask, k) {
  return async (state, game, signal) => {
    const legal = game.moves(state);
    const examples = legal.slice(0, 6).map((m) => game.moveText(m)).join('; ');
    const text = await ask([{ role: 'system', content: PROPOSE_SYSTEM }, { role: 'user', content: game.render(state) + '\nLegal moves look like: ' + examples + '.\nAnswer with the JSON object only.' }], signal);
    let list = []; try { const s = String(text || ''), a = s.indexOf('{'), b = s.lastIndexOf('}'); const j = JSON.parse(s.slice(a, b + 1)); if (Array.isArray(j.moves)) list = j.moves; } catch (e) { list = []; }
    const keyOf = (m) => JSON.stringify(m), out = [], seen = new Set();
    for (const t of list) { const m = game.parseMove(state, String(t)); if (m != null && !seen.has(keyOf(m)) && legal.some((x) => keyOf(x) === keyOf(m))) { seen.add(keyOf(m)); out.push(m); } if (out.length >= (k || 3)) break; }
    return { moves: out, raw: String(text || '').slice(0, 300), filled: false };
  };
}

// play a whole game: mode 'plan' (imagine each proposal, then act) or 'once' (act on the first proposal at once)
function playGame(game, seed, proposer, mode, o) {
  o = o || {};
  let s = game.init(seed), n = 0; const seen = new Set();
  if (game.key) seen.add(game.key(s));
  while (!game.done(s) && n < (o.maxPly || 80)) {
    const props = proposer(s, game); if (!props || !props.length) break;
    const m = mode === 'plan' ? plan(game, s, props, { ...o, seen }).move : props[0];
    if (m == null) break;
    s = game.step(s, m); n++;
    if (game.key) seen.add(game.key(s));
  }
  const r = game.result(s);
  return { result: r == null ? 0 : r, win: r === 1, ply: n };
}

module.exports = { futures, imagineMove, moveValue, plan, randomProposer, modelProposer, playGame, PROPOSE_SYSTEM };
