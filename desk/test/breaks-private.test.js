const test = require('node:test'), assert = require('node:assert');
const { BreakTracker } = require('../src/breaks');
test('private windows keep no raw title', () => {
  const rows = []; const b = new BreakTracker({ onRow: (r) => rows.push(r) });
  const t0 = Date.UTC(2026, 10, 4, 15);
  b.tick(t0, 0, 'work', { app: 'Safari', title: 'Physics notes' });
  b.tick(t0 + 60000, 0, 'other', { app: 'Google Chrome', title: 'New Incognito Tab' });
  b.tick(t0 + 120000, 0, 'other', { app: 'Safari', title: 'Chase Bank - sign in to your account' });
  b.tick(t0 + 180000, 0, 'other', { app: '1Password', title: 'Vault' });
  b.tick(t0 + 30 * 60000, 600, 'other', { app: 'Finder', title: 'x' });   // a break flushes the queue
  b.tick(t0 + 31 * 60000, 0, 'work', { app: 'Finder', title: 'x' });
  const titles = rows.filter((r) => r.raw).map((r) => r.raw.title).join('|');
  assert.ok(!/Incognito|Chase|Vault/.test(titles), titles);
  assert.ok(/Physics notes/.test(titles), 'normal titles still kept: ' + titles);
});
