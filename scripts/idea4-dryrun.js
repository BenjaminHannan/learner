'use strict';
// Uses the production offer policy on temporary files; no live app data is written.
const fs = require('fs'), os = require('os'), path = require('path');
const { HabitOffers } = require('../desk/src/habit-offers');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'habit-replay-'));
try {
  const policy = new HabitOffers(dir, { items: input.helpers });
  const offers = [];
  for (const row of input.days) {
    fs.writeFileSync(policy.input, JSON.stringify({ habits: row.habits }), { mode: 0o600 });
    const [y, m, d] = row.date.split('-').map(Number);
    const h = policy.offer(new Date(y, m - 1, d, 12));
    if (h) { offers.push({ date: row.date, target: h.target, days: h.days }); const state = policy.read(); state.pending = null; if (!policy.save(state)) throw Error('cannot save replay state'); }
  }
  process.stdout.write(JSON.stringify(offers));
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
