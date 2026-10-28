'use strict';
// Hourly check-in while asleep (Windows). Pure helpers, no Electron.
// The rules for "what needs Ben" are a port of the Sleep Mode app's hourly check-in:
//   sleepmode/checkin.py (triage) and sleepmode/config.py (urgent_words, vip_senders, event_soon_h, mail_lookback_h, calendar_ahead_h)
//   on origin/claude/project-thread-sl2x88 (PR #126). The Python package is not used; only its rules are copied.
const path = require('path');

const DEFAULT_TASK = 'Quick check-in while you sleep: run any Glims that are due, and look at my email and calendar in the browser if I am signed in. Reply exactly NOTHING if nothing needs me; otherwise one short line saying what needs me.';
// copied from sleepmode/config.py
const RULES = {
  urgentWords: ['urgent', 'asap', 'today', 'deadline', 'due', 'overdue', 'action required', 'payment failed', 'security alert', 'verify', 'interview', 'final notice'],
  vipSenders: [],
  eventSoonH: 2.0,
  mailLookbackH: 24,
  calendarAheadH: 12
};
const CHECKIN_CAP_MS = 5 * 60000;
const CHECKIN_PERIOD_MIN = 60;

// the task the agent gets: Ben's text plus the triage rules in words (so the system prompt stays byte-constant)
function checkinTask(settings, rules) {
  const s = settings || {}; const r = { ...RULES, ...(rules || {}) };
  const base = String(s.sleepCheckinTask || '').trim() || DEFAULT_TASK;
  const vip = r.vipSenders.length ? ' Anything from these senders needs me: ' + r.vipSenders.join(', ') + '.' : '';
  return base + '\n\nRead only: do not send, reply, delete, archive, accept or change anything. Unread mail from the last ' + r.mailLookbackH + ' hours needs me if its subject or text has one of these words: ' + r.urgentWords.join(', ') + '.' + vip +
    ' A calendar event in the next ' + r.calendarAheadH + ' hours needs me only if it starts within ' + r.eventSoonH + ' hours. If you are not signed in, do not try to sign in: reply NOTHING.';
}

// "NOTHING" (any case, with or without a full stop or quotes) means nothing; anything else is one short line
function parseReply(text) {
  const t = String(text == null ? '' : text).replace(/\s+/g, ' ').trim();
  if (!t) return { nothing: true, line: '' };
  if (/^["'`*_\s]*nothing[\s.!"'`*_]*$/i.test(t)) return { nothing: true, line: '' };
  const first = t.split(/(?<=[.!?])\s+/)[0];
  return { nothing: false, line: (first.length > 160 ? first.slice(0, 157) + '...' : first) };
}

// is a check-in due at this chunk boundary?  i: {enabled, now, sleepStart, lastAt, periodMin, wakeReq, onBattery, onlyPlugged}
function checkinDue(i) {
  if (!i.enabled || i.wakeReq) return { due: false, reason: i.wakeReq ? 'woken' : 'off' };
  if (i.onlyPlugged && i.onBattery) return { due: false, reason: 'unplugged' };
  const period = Math.max(5, Number(i.periodMin) || CHECKIN_PERIOD_MIN) * 60000;
  const since = i.lastAt || i.sleepStart;
  if (!(i.now - since >= period)) return { due: false, reason: 'not yet' };
  return { due: true, reason: 'hour passed' };
}

// the model for a check-in: the newest GATE-PASSED adapter (the converted adapter.gguf; sleep/adapter is what the worker promotes
// after its gate), else the plain base model (''). Never the half-trained work adapter.
function checkinAdapter(home, exists) {
  const f = path.join(home, 'adapter.gguf');
  return exists(f) ? f : '';
}

// Port of triage() in sleepmode/checkin.py for structured items {source:'mail'|'calendar', sender, subject, snippet, startsInMin}.
function triage(items, rules) {
  const r = { ...RULES, ...(rules || {}) };
  const vips = r.vipSenders.map((v) => String(v).toLowerCase()).filter(Boolean);
  const esc = (w) => w.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const words = r.urgentWords.filter(Boolean).map((w) => ({ w, re: new RegExp('\\b' + esc(w) + '\\b') }));
  const out = [];
  for (const it of items || []) {
    let reason = '';
    if (it.source === 'calendar') {
      if (it.startsInMin != null && it.startsInMin >= 0 && it.startsInMin <= r.eventSoonH * 60) reason = 'event starts in ' + it.startsInMin + ' min';
    } else {
      const sender = String(it.sender || '').toLowerCase();
      const text = (String(it.subject || '') + ' ' + String(it.snippet || '')).toLowerCase();
      if (vips.some((v) => sender.includes(v))) reason = 'VIP sender';
      else { const hit = words.find((x) => x.re.test(text)); if (hit) reason = 'urgent word: ' + hit.w; }
    }
    if (reason) out.push({ item: it, reason });
  }
  return out;
}

// Once per item (sleepmode keeps notified.json): the same line is not announced twice in a night
function isRepeat(seen, line) { const k = String(line).toLowerCase().replace(/\W+/g, ' ').trim(); if (seen.has(k)) return true; seen.add(k); return false; }

module.exports = { DEFAULT_TASK, RULES, CHECKIN_CAP_MS, CHECKIN_PERIOD_MIN, checkinTask, parseReply, checkinDue, checkinAdapter, triage, isRepeat };
