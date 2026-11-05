'use strict';
// connect-20261105 #3: settings.notesByRelevance (memory.js). Off = the old behaviour (memory.test.js); on = keep notes, choose by closeness.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path');
const { createMemory, MAX_CHARS, STORE_CHARS, selectLines } = require('../src/memory');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'memrel-'));
const W = ['apple', 'river', 'violin', 'garden', 'rocket', 'lantern', 'harbor', 'meadow', 'pepper', 'canyon', 'falcon', 'marble', 'velvet', 'thunder', 'orchid', 'glacier'];
const fill = (m, n) => { for (let i = 0; i < n; i++) { const w = (k) => W[(i * 7 + k * 3 + Math.floor(i / 16) * k) % W.length] + (i * 31 + k); m.save('Ben noted ' + w(1) + ' ' + w(2) + ' ' + w(3) + ' ' + w(4) + ' ' + w(5) + ' near the ' + w(6) + ' by ' + w(7), 'misc'); } };

test('on: notes past the old 6,000-char cap are kept (off would delete the oldest)', () => {
  const dir = tmp(); let on = true;
  const m = createMemory(dir, { notesByRelevance: () => on });
  m.save('Ben has AP Chemistry with Mr. Phipps in period 4', 'school');
  fill(m, 120);
  const size = m.list().reduce((n, f) => n + f.text.length + (f.topic || '').length, 0);
  assert.ok(size > MAX_CHARS && size <= STORE_CHARS, 'kept ' + size);
  assert.ok(m.list().some((f) => /Phipps/.test(f.text)));
  on = false; m.save('one more note while off', 'misc');
  assert.ok(!m.list().some((f) => /Phipps/.test(f.text)), 'off: the oldest Glim note is deleted as before');
});

test('on: an old note close to the message is shown, the block stays within budget, and the left-out count is stated', () => {
  const dir = tmp(); const m = createMemory(dir, { notesByRelevance: () => true });
  m.save('Ben has AP Chemistry with Mr. Phipps in period 4', 'school');
  fill(m, 120);
  const b = m.block('who teaches my chem class?');
  assert.match(b, /AP Chemistry with Mr\. Phipps/);
  assert.match(b, /more saved notes are not shown here/);
  assert.ok(b.split('\n').slice(1).join('\n').length <= MAX_CHARS);
});

test('on, everything fits: byte-identical to the old block whatever the message', () => {
  const dir = tmp(); const on = createMemory(dir, { notesByRelevance: () => true }), off = createMemory(dir);
  on.save('Ben likes short answers', 'style'); on.save('Maya is Ben\'s lab partner', 'people');
  assert.strictEqual(on.block('who is maya?'), off.block());
  assert.strictEqual(on.block(), off.block());
});

test('Ben\'s own lines (no id) are kept first; a throwing setting getter means off', () => {
  const dir = tmp(); const m = createMemory(dir, { notesByRelevance: () => true });
  fill(m, 120);
  const t = m.read().text; m.write(t.replace('# What Glim remembers', '# What Glim remembers\n\n- Ben hand-wrote this: call grandma on Sundays'));
  assert.match(m.block('what is the plan for today?'), /call grandma on Sundays/);
  const bad = createMemory(dir, { notesByRelevance: () => { throw new Error('x'); } });
  assert.strictEqual(bad.block('anything'), createMemory(dir).block());
});

test('selectLines: pure; closest notes before newest; never over budget', () => {
  const lines = Array.from({ length: 50 }, (_, i) => ({ text: '- n' + i + ': note ' + i + (i === 3 ? ' zebra crossing' : ''), doc: 'note ' + i + (i === 3 ? ' zebra crossing' : '') }));
  const { keep, left } = selectLines(lines, 'where is the zebra?', 200);
  assert.ok(keep.has(3) && keep.has(49) && !keep.has(10));
  assert.strictEqual(left, 50 - keep.size);
  assert.ok([...keep].reduce((n, i) => n + lines[i].text.length + 1, 0) <= 200);
});
