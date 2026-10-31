'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'), os = require('os'), path = require('path');
const { seedStanding, STANDING } = require('../src/standing');

test('standing Motes are added once, deferred, and never re-added', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'stand-'));
  const calls = [];
  const helpers = { add: (o) => { calls.push(o); return {}; } };
  assert.deepStrictEqual(seedStanding(helpers, dir), STANDING.map((m) => m.name));
  assert.ok(calls.every((c) => c.deferFirst && (c.every || c.at) && /topic "card"/.test(c.task)));
  assert.deepStrictEqual(seedStanding(helpers, dir), []);
  assert.equal(calls.length, 3);
});

test('standing Motes: a refused add (already exists) does not stop the others', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'stand-'));
  const helpers = { add: (o) => { if (o.name === 'Organizer') throw new Error('exists'); return {}; } };
  assert.deepStrictEqual(seedStanding(helpers, dir), ['Model ideas', 'Week planner']);
});

test('existing seeded Organizer moves only its original schedule once', () => {
  for (const [at, expected] of [['08:00', '06:00'], ['09:00', '09:00']]) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'stand-'));
    fs.writeFileSync(path.join(dir, 'standing-motes.json'), JSON.stringify({ added: ['Organizer'] }));
    const h = { id: 'one', name: 'Organizer', at, status: 'idle' };
    const helpers = { find: () => h, update: (_, p) => Object.assign(h, p) };
    seedStanding(helpers, dir);
    assert.equal(h.at, expected);
    h.at = '08:00'; seedStanding(helpers, dir);
    assert.equal(h.at, '08:00');
  }
  assert.equal(STANDING.find((m) => m.name === 'Organizer').at, '06:00');
});
