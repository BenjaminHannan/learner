'use strict';
// Glim team, Bedwars side: the small tactics vocabulary (in I3's intent format) and the plan rules that carry the play between slow
// brain calls: derived resources and purchases, required follow-ups, done steps dropped, urgent steps.
const test = require('node:test');
const assert = require('node:assert');
const T = require('../src/games/bedwars/tactics');
const intent = require('../src/games/core/intent');

const obs0 = (o) => ({ inv: { iron: 0, gold: 0, wool: 0, shears: 0 }, atBase: true, bridgeLeft: 18, onEnemyIsland: false, enemy: null,
  enemyBed: { alive: true, covered: false }, myBedThreat: false, me: { alive: true, x: 2 }, ...o });
const kinds = (steps) => steps.map((s) => s.kind + (s.item ? ':' + s.item : '') + (s.res ? ':' + s.res + (s.n != null ? s.n : '') : ''));

test('vocabulary: 8-12 calls, each valid for the I3 intent channel, one distinct line each', () => {
  const codes = Object.keys(T.vocab);
  assert.ok(codes.length >= 8 && codes.length <= 12, codes.length + ' calls');
  assert.deepStrictEqual(T.CODES, codes);
  const helps = codes.map((c) => T.vocab[c].help);
  assert.strictEqual(new Set(helps).size, codes.length, 'no two calls share a description');
  for (const h of helps) { assert.ok(h.length >= 20 && h.length <= 110, h); assert.ok(!h.includes('\n')); }
  // the description card the brain sees: one line per call
  const card = T.promptCard(); for (const c of codes) assert.ok(card.includes(c), c);
  // every call with its defaults is valid; the core channel accepts it
  const ch = new intent.IntentChannel(T.vocab);
  for (const c of codes) { const r = T.parseCall(c === 'BUY' ? 'BUY item=wool' : c); assert.ok(r.ok, c + ': ' + r.why); assert.ok(ch.send(r.call, 0, 'test').ok !== false); }
  assert.ok(!T.parseCall('BUY').ok, 'BUY needs its item');
  // OWN vs ENEMY spelled out where the same verb could mean either side
  assert.match(T.vocab.GET.help, /YOUR OWN/); assert.match(T.vocab.BREAK_BED.help, /ENEMY/); assert.match(T.vocab.DEFEND.help, /YOUR OWN/); assert.match(T.vocab.HOME.help, /YOUR OWN/);
});

test('calls parse in the core format (CODE arg=val); bad ones are refused with a reason', () => {
  assert.deepStrictEqual(T.parseCall('GET res=iron n=24').call, { code: 'GET', args: { res: 'iron', n: 24 } });
  assert.deepStrictEqual(T.parseCall('BUY item=shears  # covered bed').call, { code: 'BUY', args: { item: 'shears' } });
  assert.strictEqual(T.parseCall('BRIDGE').call.args.n, 20, 'default');
  assert.strictEqual(T.fmt(T.parseCall('BREAK_BED').call), 'BREAK_BED');
  for (const bad of ['BUY item=diamond_sword', 'GET n=500', 'JUMP', 'BRIDGE n=0', '']) assert.ok(!T.parseCall(bad).ok, bad);
});

test('repair: resources and wool are derived, never trusted from the brain', () => {
  // the brain says only "bridge, break the bed" (or asks for the wrong amounts): the rules add exactly what is needed
  const a = T.repair([T.makeStep('bridge'), T.makeStep('break_bed')], obs0(), []);
  assert.deepStrictEqual(kinds(a), ['get_resources:iron8', 'buy_blocks', 'buy_blocks', 'bridge', 'break_bed']);
  assert.deepStrictEqual(a.map((s) => s.call.code), ['GET', 'BUY', 'BUY', 'BRIDGE', 'BREAK_BED']);
  assert.strictEqual(new Set(a.map((s) => s.id)).size, a.length, 'ids unique');
  const wrong = T.repair([T.makeStep('get_resources', { res: 'gold', n: 64 }), T.makeStep('buy_blocks'), T.makeStep('bridge')], obs0(), []);
  assert.deepStrictEqual(kinds(wrong), kinds(a), 'the brain\'s GET / wool steps are replaced by the derived ones; break_bed added back');
  // wool already carried: fewer buys; enough wool: none
  assert.deepStrictEqual(kinds(T.repair([T.makeStep('bridge')], obs0({ inv: { iron: 4, wool: 10 } }), [])), ['buy_blocks', 'bridge', 'break_bed']);
  assert.deepStrictEqual(kinds(T.repair([T.makeStep('bridge')], obs0({ inv: { wool: 20 } }), [])), ['bridge', 'break_bed']);
});

test('repair: required follow-ups are added by the plan (shears for a covered bed, home before the shop)', () => {
  // covered bed seen, no shears: buy shears BEFORE leaving the island
  const b = T.repair([T.makeStep('bridge'), T.makeStep('break_bed')], obs0({ enemyBed: { alive: true, covered: true } }), []);
  assert.deepStrictEqual(kinds(b), ['get_resources:iron20', 'buy:shears', 'get_resources:iron8', 'buy_blocks', 'buy_blocks', 'bridge', 'break_bed']);
  // on the enemy island, covered, no shears: go home, earn, buy, come back
  const c = T.repair([T.makeStep('break_bed')], obs0({ atBase: false, onEnemyIsland: true, bridgeLeft: 0, enemyBed: { alive: true, covered: true } }), []);
  assert.deepStrictEqual(kinds(c), ['home', 'get_resources:iron20', 'buy:shears', 'break_bed']);
  // shears owned: nothing extra; a permanent item already owned is dropped
  const d = T.repair([T.makeStep('buy', { item: 'shears' }), T.makeStep('break_bed')], obs0({ inv: { shears: 1, wool: 30 }, enemyBed: { alive: true, covered: true } }), []);
  assert.deepStrictEqual(kinds(d), ['bridge', 'break_bed']);
});

test('repair: the plan memory, not the brain, remembers what is done; the goal step is never lost', () => {
  // the brain "forgets" the done list and re-sends the whole plan: done things are dropped by state, ids continue after done ids
  const o = obs0({ atBase: false, bridgeLeft: 0, inv: { wool: 5 }, me: { alive: true, x: 20 } });
  const r = T.repair([T.makeStep('get_resources'), T.makeStep('buy_blocks'), T.makeStep('bridge'), T.makeStep('break_bed')], o, ['get_resources', 'buy_blocks', 'bridge']);
  assert.deepStrictEqual(kinds(r), ['break_bed']);
  // the brain left out the goal: it is put back
  assert.deepStrictEqual(kinds(T.repair([T.makeStep('hold')], o, [])), ['hold', 'break_bed']);
  // bed broken: nothing to add
  assert.deepStrictEqual(kinds(T.repair([T.makeStep('break_bed')], obs0({ enemyBed: { alive: false } }), [])), []);
  // a repeated id after a done one gets a new id (plan memory keys by id)
  const again = T.repair([T.makeStep('bridge')], obs0({ inv: { wool: 30 } }), ['bridge']);
  assert.strictEqual(again[0].kind, 'bridge'); assert.notStrictEqual(again[0].id, 'bridge');
  // a fight with nobody near (e.g. after I died) is dropped
  assert.deepStrictEqual(kinds(T.repair([T.makeStep('fight'), T.makeStep('break_bed')], obs0({ inv: { wool: 30 } }), [])), ['bridge', 'break_bed']);
  assert.deepStrictEqual(kinds(T.repair([T.makeStep('fight'), T.makeStep('break_bed')], obs0({ inv: { wool: 30 }, enemy: { alive: true, dist: 4 } }), [])), ['fight', 'bridge', 'break_bed']);
});

test('urgent: an enemy in fighting range -> FIGHT now; my bed attacked -> HOME + DEFEND; never while dead or already on it', () => {
  const e = (d) => obs0({ enemy: { alive: true, dist: d } });
  assert.deepStrictEqual(kinds(T.urgent(e(4), T.makeStep('bridge'))), ['fight']);
  assert.strictEqual(T.urgent(e(T.FIGHT_RANGE + 1), T.makeStep('bridge')), null);
  assert.strictEqual(T.urgent(e(2), T.makeStep('fight')), null, 'already fighting');
  assert.strictEqual(T.urgent(e(2), T.makeStep('retreat')), null, 'the brain chose to retreat');
  assert.strictEqual(T.urgent({ ...e(2), me: { alive: false } }, T.makeStep('bridge')), null);
  assert.deepStrictEqual(kinds(T.urgent(obs0({ myBedThreat: true }), T.makeStep('bridge'))), ['home', 'defend']);
  assert.ok(T.FIGHT_RANGE < T.DONE_RANGE, 'a started fight is not ended by the range that starts it');
});

test('stepOf maps the brain\'s calls to plan steps; RUSH_PLAN is the goal-scorer\'s default plan', () => {
  const steps = T.withIds(['GET res=iron n=8', 'BUY item=wool', 'BUY item=wool', 'BUY item=shears', 'BRIDGE', 'BREAK_BED', 'FIGHT', 'HOME'].map((l) => T.stepOf(T.parseCall(l).call)), []);
  assert.deepStrictEqual(steps.map((s) => s.kind), ['get_resources', 'buy_blocks', 'buy_blocks', 'buy', 'bridge', 'break_bed', 'fight', 'home']);
  assert.strictEqual(new Set(steps.map((s) => s.id)).size, steps.length);
  assert.deepStrictEqual(T.RUSH_PLAN, ['get_resources', 'buy_blocks', 'bridge', 'break_bed']);
  for (const k of Object.keys(T.STEP_CALL)) { const c = T.STEP_CALL[k]({ item: 'wool' }); assert.ok(intent.validate(T.vocab, c).ok, k); }
});

test('legacy short codes still parse (truth-log cards and old logs), and the new calls map onto them', () => {
  const p = (s) => { const r = T.parse(s); return r.ok ? r.calls[0] : r; };
  assert.deepStrictEqual(p('jc 3'), { code: 'jc', params: { at: 3 } });
  assert.strictEqual(p('buy wool').code, 'buy');
  assert.deepStrictEqual(p('get iron 24').params, { res: 'iron', n: 24 });
  assert.ok(!T.parse('not a call').ok);
  assert.strictEqual(T.parse('br 4; jc 3').calls.length, 2);
  assert.strictEqual(p('BRIDGE').code, 'br', 'a new call is filed under its legacy group');
  assert.strictEqual(p('BREAK_BED').code, 'bb');
  assert.deepStrictEqual(p('BUY item=shears'), { code: 'buy', params: { item: 'shears' } });
  for (const c of T.CODES) assert.ok(T.VOCAB[p(c).code], c + ' has a legacy group');
});
