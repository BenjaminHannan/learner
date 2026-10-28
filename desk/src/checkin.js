'use strict';
// Hourly check-in while asleep (Windows), and the lighter awake check-in (every 30 min). Pure helpers, no Electron.
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

// "Keeping track of" items (src/tracking.js) that are past their until date or due within 2 days need Ben. tracked: [{what, source, until}]
function trackedRule(tracked) {
  const T = require('./tracking');
  const today = new Date(); const pad = (n) => String(n).padStart(2, '0');
  const due = T.dueItems(tracked || [], today.getFullYear() + '-' + pad(today.getMonth() + 1) + '-' + pad(today.getDate()), T.SOON_DAYS);
  if (!due.length) return '';
  return '\n\nThings I am keeping track of that need me (past their date or due within ' + T.SOON_DAYS + ' days): ' + due.map((d) => T.describe(d.item) + ' [' + d.reason + ']').join('; ') + '. Say so in your reply even if mail and calendar are quiet.';
}

// the task the agent gets: Ben's text plus the triage rules in words (so the system prompt stays byte-constant)
function checkinTask(settings, rules, tracked) {
  const s = settings || {}; const r = { ...RULES, ...(rules || {}) };
  const base = String(s.sleepCheckinTask || '').trim() || DEFAULT_TASK;
  const vip = r.vipSenders.length ? ' Anything from these senders needs me: ' + r.vipSenders.join(', ') + '.' : '';
  return base + trackedRule(tracked) + '\n\nRead only: do not send, reply, delete, archive, accept or change anything. Unread mail from the last ' + r.mailLookbackH + ' hours needs me if its subject or text has one of these words: ' + r.urgentWords.join(', ') + '.' + vip +
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
// fits(f): the adapter was trained on the built-in model's base (adapter.gguf.json); then adapter.prev.gguf when the newest was set aside.
function checkinAdapter(home, exists, fits) {
  const ok = (f) => exists(f) && (!fits || fits(f));
  for (const n of ['adapter.gguf', 'adapter.prev.gguf']) { const f = path.join(home, n); if (ok(f)) return f; }
  return '';
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

// ---- awake check-in (every awakeCheckinMins while Glim is up and Ben is not using it) ----------------------------------------
const AWAKE_TASK = 'Quick check-in while you are awake: look at my email and calendar in the browser if I am signed in. Reply exactly NOTHING if nothing needs me; otherwise one short line saying what needs me.';
const AWAKE_DEFAULT_MINS = 30;
const AWAKE_IDLE_MAX_MS = 2 * 3600000; // idle longer than this: the sleep path covers it
const DISK_LOW_FRAC = 0.05, DISK_LOW_BYTES = 2 * 1024 ** 3;

// Is an awake check-in due now?  i: {now, last, mins, asleep, runActive, focused, idleMs, sleepBusy}  (now/last in ms; last = 0/null when none yet)
function shouldAwakeCheckin(i) {
  const mins = Number(i.mins);
  if (!(mins > 0)) return { due: false, reason: 'off' };
  if (i.asleep || i.sleepBusy) return { due: false, reason: 'asleep' };
  if (i.runActive) return { due: false, reason: 'run active' };
  if (i.focused) return { due: false, reason: 'chat focused' };
  if (i.idleMs != null && i.idleMs > AWAKE_IDLE_MAX_MS) return { due: false, reason: 'idle' };
  if (i.last && !(i.now - i.last >= mins * 60000)) return { due: false, reason: 'not yet' };
  return { due: true, reason: 'due' };
}

// the free-space test: stats {total, free} in bytes
function diskLow(stats) {
  if (!stats || !(stats.total > 0)) return false;
  return stats.free < DISK_LOW_BYTES || stats.free / stats.total < DISK_LOW_FRAC;
}

// cheap deterministic checks, no model. i: {gateway:'down'|'warming'|'ready', disk:{total,free}|null, helpers:[{id,name,every,at,paused,status,lastSummary,lastRun}], tracked:[...], today:'YYYY-MM-DD', builtinStarting}
// -> [{key, line}]; the key changes when the situation changes, so a fixed problem can be announced again later
function awakeFindings(i) {
  const out = [];
  const T = require('./tracking');
  if (i.gateway === 'down' && !i.builtinStarting) out.push({ key: 'gateway', line: 'The model server is not answering.' });
  if (diskLow(i.disk)) out.push({ key: 'disk', line: 'The disk is almost full (' + (i.disk.free / 1024 ** 3).toFixed(1) + ' GB left).' });
  for (const h of i.helpers || []) {
    if (!(h.every || h.at) || h.paused || h.status === 'stopped') continue;
    if (h.status === 'failed' || /^Failed:/.test(h.lastSummary || '')) out.push({ key: 'glim:' + h.id + ':' + (h.lastRun || ''), line: 'The Glim "' + h.name + '" failed on its last run.' });
  }
  for (const d of T.dueItems(i.tracked || [], i.today, T.SOON_DAYS)) out.push({ key: 'track:' + T.describe(d.item) + ':' + d.reason, line: T.describe(d.item) + ' is ' + d.reason + '.' });
  return out;
}

// Notified-state (like sleepmode's notified.json, but a Set of keys that forgets a key once it stops showing up, so a problem
// that came back is announced again but one that is still there is not announced twice). Returns the fresh findings.
function freshFindings(seen, findings) {
  const now = new Set(findings.map((f) => f.key));
  for (const k of [...seen]) if (!now.has(k)) seen.delete(k);
  const fresh = findings.filter((f) => !seen.has(f.key));
  for (const f of fresh) seen.add(f.key);
  return fresh;
}

// the model part (mail and calendar through the browser, read only) reuses the sleep check-in task text and rules; the tracking list is
// handled by awakeFindings, so it is not repeated here
function awakeTask(settings, rules) { return checkinTask({ ...(settings || {}), sleepCheckinTask: AWAKE_TASK }, rules, []); }

module.exports = { AWAKE_TASK, AWAKE_DEFAULT_MINS, AWAKE_IDLE_MAX_MS, shouldAwakeCheckin, diskLow, awakeFindings, freshFindings, awakeTask, trackedRule, DEFAULT_TASK, RULES, CHECKIN_CAP_MS, CHECKIN_PERIOD_MIN, checkinTask, parseReply, checkinDue, checkinAdapter, triage, isRepeat };
