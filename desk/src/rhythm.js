'use strict';
// Ben's daily rhythm (no Electron): when he is usually still up in the evening and when he usually starts in the morning, so
// auto-sleep can fit his routine. The 60-second tick says "active or not"; we keep, per day, the first and last minute he was
// active, as small JSON in userData (last 21 days). A "day" runs from 04:00 to 04:00, so activity at 01:30 belongs to the evening
// before. Minutes are counted from midnight of the day's own date: 04:00 is 240, the next 01:30 is 1530, the next 04:00 is 1680.
const fs = require('fs');
const path = require('path');

const DAY_START = 240;            // 04:00
const KEEP_DAYS = 21;
const MIN_DAYS = 5;               // fewer finished days than this: no opinion
const FLOOR = 18 * 60;            // the window starts between 18:00 ...
const CEIL = 24 * 60 + 4 * 60;    // ... and 04:00 (so there is still a night left)
const MORNING_MIN = 24 * 60 + 5 * 60; // and ends between 05:00 ...
const MORNING_MAX = 24 * 60 + 14 * 60; // ... and 14:00 (he may sleep in)
const MIN_LEN = 3 * 60;           // a window shorter than 3 h is not worth it

const pad = (n) => String(n).padStart(2, '0');
const hhmm = (m) => { m = ((m % 1440) + 1440) % 1440; return pad(Math.floor(m / 60)) + ':' + pad(m % 60); };
// which 04:00-to-04:00 day is `now` in, and how many minutes after that day's midnight is it
function dayOf(now) {
  const t = now.getHours() * 60 + now.getMinutes(), d = new Date(now);
  if (t < DAY_START) d.setDate(d.getDate() - 1);
  return { key: d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()), min: t < DAY_START ? t + 1440 : t };
}
function median(a) {
  const s = a.slice().sort((x, y) => x - y), n = s.length;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
}

/**
 * The window the records suggest, from the finished days only (today's is still being written), or null when the data is thin.
 * days: { 'YYYY-MM-DD': { first, last } } -> { from: 'HH:MM', to: 'HH:MM', days }
 */
function learnedWindow(days, now) {
  const today = dayOf(now).key;
  const done = Object.keys(days || {}).filter((k) => k < today).sort().slice(-KEEP_DAYS).map((k) => days[k])
    .filter((r) => r && Number.isFinite(r.first) && Number.isFinite(r.last));
  if (done.length < MIN_DAYS) return null;
  // last active that evening, rounded up to the next half hour, kept between 18:00 and 04:00
  const from = Math.min(CEIL, Math.max(FLOOR, Math.ceil(median(done.map((r) => r.last)) / 30) * 30));
  // first active the next morning (same clock, one day on), kept between 05:00 and 14:00 and at least 3 h into the night
  const to = Math.max(from + MIN_LEN, Math.min(MORNING_MAX, Math.max(MORNING_MIN, 1440 + Math.round(median(done.map((r) => r.first))))));
  if (to - from < MIN_LEN) return null;
  return { from: hhmm(from), to: hhmm(to), days: done.length };
}

class Rhythm {
  constructor(file) {
    this.file = file || null;
    this.days = {};
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && typeof j.days === 'object') this.days = this._clean(j.days); } catch (e) { /* none yet */ } }
  }
  _clean(days) {
    const out = {};
    for (const k of Object.keys(days || {}).filter((x) => /^\d{4}-\d{2}-\d{2}$/.test(x)).sort().slice(-KEEP_DAYS)) {
      const r = days[k];
      if (r && Number.isFinite(r.first) && Number.isFinite(r.last) && r.first >= 0 && r.last >= r.first && r.last < 2880) out[k] = { first: r.first, last: r.last };
    }
    return out;
  }
  // one sample from the 60 s tick: was Ben active just now? Writes to disk only when a day's first or last moves.
  record(now, active) {
    if (!active) return false;
    const { key, min } = dayOf(now), r = this.days[key];
    if (!r) this.days[key] = { first: min, last: min };
    else if (min < r.first) r.first = min;
    else if (min > r.last) r.last = min;
    else return false;
    this.days = this._clean(this.days);
    this._save();
    return true;
  }
  learned(now) { return learnedWindow(this.days, now || new Date()); }
  _save() {
    if (!this.file) return;
    try {
      fs.mkdirSync(path.dirname(this.file), { recursive: true });
      const tmp = this.file + '.tmp';
      fs.writeFileSync(tmp, JSON.stringify({ days: this.days }));
      fs.renameSync(tmp, this.file);
    } catch (e) { /* a missed save only loses a few minutes of habit data */ }
  }
}

module.exports = { Rhythm, learnedWindow, dayOf, median, hhmm, MIN_DAYS, KEEP_DAYS };
