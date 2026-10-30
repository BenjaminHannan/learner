'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), os = require('os'), path = require('path');
const { HabitOffers } = require('../src/habit-offers');
function setup(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'habit-test-')); t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const made = []; const helpers = { items: [], add: x => { made.push(x); return x; } };
  const offers = new HabitOffers(dir, helpers);
  const rows = (...targets) => fs.writeFileSync(offers.input, JSON.stringify({ habits: targets.map(target => ({ key: 'habit|website|' + target, target, cat: 'website', days: 3 })) }));
  return { offers, rows, made, helpers };
}
const date = n => new Date(2026, 9, n, 12);
test('only an explicit yes creates one deferred daily Mote', t => {
  const { offers, rows, made } = setup(t); rows('example.org');
  assert.equal(offers.respond('habit|website|example.org', 'yes').ok, false);
  const h = offers.offer(date(1)); assert.equal(made.length, 0);
  assert.equal(offers.respond(h.key, 'maybe').ok, false); assert.equal(made.length, 0);
  assert.equal(offers.respond(h.key, 'yes').ok, true); assert.equal(made.length, 1);
  assert.equal(made[0].at, '08:00'); assert.equal(made[0].deferFirst, true);
  assert.equal(offers.respond(h.key, 'yes').ok, false); assert.equal(made.length, 1);
});
test('at most one a day and three in rolling seven days; never repeat a key', t => {
  const { offers, rows, made } = setup(t); rows('a.org', 'b.org', 'c.org', 'd.org');
  for (const d of [1, 2, 3]) { const h = offers.offer(date(d)); assert.ok(h); assert.ok(offers.respond(h.key, 'no').ok); assert.equal(offers.offer(date(d)), null); }
  assert.equal(offers.offer(date(4)), null); const h = offers.offer(date(8)); assert.equal(h.target, 'd.org');
  offers.respond(h.key, 'no'); assert.equal(offers.offer(date(15)), null); assert.equal(made.length, 0);
});
test('five consecutive declines stop until re-enabled, and yes resets the streak', t => {
  const { offers, rows } = setup(t); rows('a.org', 'b.org', 'c.org', 'd.org', 'e.org', 'f.org', 'g.org');
  for (const d of [1, 2, 3, 8, 9]) { const h = offers.offer(date(d)); const r = offers.respond(h.key, 'no'); if (d === 9) assert.equal(r.stopped, true); }
  assert.equal(offers.offer(date(10)), null); assert.ok(offers.reenable()); const h = offers.offer(date(10)); assert.ok(h); offers.respond(h.key, 'yes'); assert.equal(offers.read().declines, 0);
});
test('skips secret targets and existing Motes', t => {
  const { offers, rows, helpers } = setup(t); rows('password is hello123', 'example.org', 'other.org'); helpers.items.push({ name: 'Example', task: 'Check example.org', status: 'idle' });
  assert.equal(offers.offer(date(1)).target, 'other.org');
});
test('unanswered offer is stable across reopen and failed writes do not offer', t => {
  const { offers, rows } = setup(t); rows('a.org'); const h = offers.offer(date(1)); assert.deepEqual(offers.offer(date(2)), h);
  offers.respond(h.key, 'no'); rows('b.org'); offers.save = () => false; assert.equal(offers.offer(date(2)), null);
});
