'use strict';
// Offers are persisted before display; a failed write fails closed. No scheduler is called here.
const fs = require('fs');
const path = require('path');
const { looksSecret } = require('./memory');
const day = (d) => [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
function candidate(h, helpers) {
  if (!h || !['website', 'app'].includes(h.cat) || typeof h.key !== 'string' || typeof h.target !== 'string' || !h.target.trim() || h.target.length > 120 || !Number.isInteger(h.days) || h.days < 3 || looksSecret(h.target) || looksSecret(h.key)) return null;
  const target = h.target.trim();
  if (helpers.items.some(x => x.status !== 'stopped' && (String(x.name || '') + ' ' + String(x.task || '')).toLowerCase().includes(target.toLowerCase()))) return null;
  return { key: h.key, target, cat: h.cat, days: h.days, name: ('Check ' + target).slice(0, 40), task: (h.cat === 'website' ? 'Check the website ' : 'Open and check the app ') + target + ' and report what matters.' };
}
class HabitOffers {
  constructor(dir, helpers) { this.file = path.join(dir, 'habit-offers-state.json'); this.input = path.join(dir, 'habit-candidates.json'); this.helpers = helpers; }
  read() { try { const s = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (!Array.isArray(s.offered) || !Array.isArray(s.dates) || !Number.isInteger(s.declines)) return null; return s; } catch (e) { return e.code === 'ENOENT' ? { offered: [], dates: [], declines: 0, pending: null } : null; } }
  save(s) { try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); const tmp = this.file + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(s), { mode: 0o600 }); fs.renameSync(tmp, this.file); return true; } catch (_) { return false; } }
  reenable() { const s = this.read(); if (!s) return false; s.declines = 0; return this.save(s); }
  offer(now = new Date(), enabled = true) {
    const s = this.read(); if (!s || !enabled || s.declines >= 5) return null;
    if (s.pending) return s.pending;
    const today = day(now), cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6); const start = day(cutoff);
    if (s.dates.includes(today) || s.dates.filter(d => d >= start && d <= today).length >= 3) return null;
    let rows; try { rows = JSON.parse(fs.readFileSync(this.input, 'utf8')).habits; } catch (_) { return null; }
    if (!Array.isArray(rows)) return null;
    const h = rows.map(x => candidate(x, this.helpers)).find(x => x && !s.offered.includes(x.key));
    if (!h) return null;
    s.offered.push(h.key); s.dates.push(today); s.pending = h;
    return this.save(s) ? h : null;
  }
  respond(key, answer) {
    const s = this.read(); if (!s || !s.pending || s.pending.key !== key || !['yes', 'no'].includes(answer)) return { ok: false };
    const h = s.pending;
    // Consume the explicit decision before attempting creation, preventing repeated clicks from creating another Mote.
    s.pending = null; s.declines = answer === 'no' ? s.declines + 1 : 0;
    if (!this.save(s)) return { ok: false };
    if (answer === 'no') return { ok: true, stopped: s.declines >= 5 };
    try { const valid = candidate(h, this.helpers); if (!valid) return { ok: false, error: 'This Mote already exists or the offer is no longer safe.' }; const mote = this.helpers.add({ name: valid.name, task: valid.task, at: '08:00', deferFirst: true }); return { ok: true, name: mote.name }; } catch (e) { return { ok: false, error: e.message }; }
  }
}
module.exports = { HabitOffers, candidate, day };
