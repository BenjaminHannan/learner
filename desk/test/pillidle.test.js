'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { idleSummary, whenLabel, agoLabel } = require('../src/pillidle');

const NOW = new Date(2026, 9, 28, 10, 0, 0).getTime(), MIN = 60000;
const h = (name, o) => ({ name, status: 'idle', paused: false, next: null, lastRun: null, ...o });

test('whenLabel: minutes, hours, today, tomorrow, weekday', () => {
  assert.strictEqual(whenLabel(NOW + 12 * MIN, NOW), 'in 12 min');
  assert.strictEqual(whenLabel(NOW + 20 * 1000, NOW), 'in 1 min');
  assert.strictEqual(whenLabel(NOW + 120 * MIN, NOW), 'in 2 h');
  assert.strictEqual(whenLabel(new Date(2026, 9, 28, 18, 5).getTime(), NOW), 'today 18:05');
  assert.strictEqual(whenLabel(new Date(2026, 9, 29, 8, 0).getTime(), NOW), 'tomorrow 08:00');
  assert.strictEqual(whenLabel(new Date(2026, 9, 31, 8, 0).getTime(), NOW), 'Sat 08:00');
});
test('agoLabel', () => {
  assert.strictEqual(agoLabel(NOW - 10 * 1000, NOW), 'just now');
  assert.strictEqual(agoLabel(NOW - 5 * MIN, NOW), '5 min ago');
  assert.strictEqual(agoLabel(NOW - 125 * MIN, NOW), '2 h ago');
  assert.strictEqual(agoLabel(NOW - 30 * 60 * MIN, NOW), 'yesterday');
});
test('idleSummary: no upcoming or last Mote runs (Ben Oct 29), bedtime, assistant on', () => {
  const s = idleSummary({ now: NOW, autoSleep: true, sleepFrom: '23:00', gateway: 'ready', helpers: [
    h('Morning briefing', { next: new Date(2026, 9, 29, 8, 0).getTime() }), h('Email watch', { next: NOW + 12 * MIN, lastRun: NOW - 18 * MIN }),
    h('Paused one', { paused: true, next: NOW + MIN }), h('Gone', { status: 'stopped', next: NOW + MIN })] });
  assert.strictEqual(s.head, 'Glimmering');
  assert.deepStrictEqual(s.lines, ['Sleeps around 23:00', 'Assistant is on']);
});
test('idleSummary: nothing scheduled is Glimmering; auto-sleep off or asleep hides bedtime; assistant states', () => {
  const s = idleSummary({ now: NOW, autoSleep: false, sleepFrom: '23:00', gateway: 'down', helpers: [] });
  assert.deepStrictEqual(s, { head: 'Glimmering', lines: ['Assistant is off'] });
  assert.ok(!idleSummary({ now: NOW, autoSleep: true, sleepFrom: '23:00', asleep: true, gateway: 'x' }).lines.some((l) => /Sleeps/.test(l)));
  assert.strictEqual(idleSummary({ now: NOW, gateway: 'starting' }).lines.pop(), 'Assistant is starting');
});
test('idleSummary: a running Glim is named in the headline and not listed as upcoming', () => {
  const s = idleSummary({ now: NOW, gateway: 'ready', helpers: [h('Email watch', { status: 'running', next: NOW + 30 * MIN })] });
  assert.strictEqual(s.head, 'Glim · Running Email watch');
  assert.ok(!s.lines.some((l) => /next/.test(l)));
});
test('idleSummary: long names are clipped to fit the card; several running Motes are counted', () => {
  const s = idleSummary({ now: NOW, gateway: 'ready', helpers: [h('A very very long Glim name that goes on and on', { status: 'running' }), h('Other', { status: 'queued' })] });
  assert.ok(s.head.length <= 40 && /…/.test(s.head));
  assert.strictEqual(s.lines[0], '2 Motes working');
});
