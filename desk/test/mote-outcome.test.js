// Lessons v3 logging (aon-notes/lessons-20261105): one outcome record per Mote run.
const test = require('node:test');
const assert = require('node:assert');
const { runOutcome } = require('../src/helpers');

const save = (summary, fact, ok = true) => ({ t: 'step', tool: 'memory_save', ok, summary, args: { fact } });

test('a learn run: marker, attributed / unattributed / maybe / failed saves, self-test parsed from the score note', () => {
  const items = [
    { t: 'assistant', text: 'Searching.' },
    save('Remembered (research; source attributed): A', 'A'),
    save('Remembered (research; source unattributed): B', 'B'),
    save('Noted to check: C', 'C'),
    save('Did not save: too long', 'D', false),
    save('Remembered (research; source attributed): SELF-TEST: 4/5 weak spots', 'SELF-TEST: 4/5, weak spots: dates'),
  ];
  const o = runOutcome({ id: 'h1', name: 'Learn 1: x', threadId: 't1', learnResearch: true }, items, { report: 'NO_UPDATE' }, 1, 2);
  assert.equal(o.ended, 'marker');
  assert.equal(o.learn, true);
  assert.deepEqual([o.saves.attributed, o.saves.unattributed, o.saves.maybe, o.saves.failed, o.saves.ok], [2, 1, 1, 1, 0]);
  assert.deepEqual(o.selftest, { right: 4, asked: 5 });
});

test('ended: error > stopped > marker > report > none', () => {
  const h = { id: 'h', name: 'n', threadId: 't' };
  assert.equal(runOutcome(h, [], { report: 'x', error: 'fetch failed' }, 0, 0).ended, 'error');
  assert.equal(runOutcome(h, [], { report: 'x', stopped: true }, 0, 0).ended, 'stopped');
  assert.equal(runOutcome(h, [], { report: 'Done. Here is the plan.' }, 0, 0).ended, 'report');
  assert.equal(runOutcome(h, [], { report: '' }, 0, 0).ended, 'none');
  assert.equal(runOutcome(h, [], { report: 'NO_UPDATE' }, 0, 0).selftest, null);
});
