'use strict';
// What the status pill says when you hover it while Glim is idle: a few plain lines (what is running now, bedtime, assistant on/off).
// Pure Node (unit tested); main.js feeds it the helper list, settings and gateway state.
const p2 = (n) => String(n).padStart(2, '0');
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const clip = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };

// "in 12 min", "in 3 h", "today 14:00", "tomorrow 08:00", "Thu 08:00"
function whenLabel(ts, now) {
  const left = Math.max(0, Math.round((ts - now) / 60000));
  if (left < 60) return 'in ' + Math.max(1, left) + ' min';
  const d = new Date(ts), n = new Date(now), hm = p2(d.getHours()) + ':' + p2(d.getMinutes());
  if (left < 180) return 'in ' + Math.round(left / 60) + ' h';
  const days = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - new Date(n.getFullYear(), n.getMonth(), n.getDate())) / 864e5);
  return (days <= 0 ? 'today' : days === 1 ? 'tomorrow' : DAYS[d.getDay()]) + ' ' + hm;
}
// "just now", "5 min ago", "2 h ago", "yesterday"
function agoLabel(ts, now) {
  const m = Math.max(0, Math.round((now - ts) / 60000));
  return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.floor(m / 60) + ' h ago' : m < 2880 ? 'yesterday' : Math.floor(m / 1440) + ' days ago';
}

// i: {now, helpers: Helpers.list() views, autoSleep, sleepFrom, gateway: 'ready'|'down'|..., asleep}
// -> {head, lines: [string]} (lines are short: the card is narrow)
function idleSummary(i) {
  const hs = (i.helpers || []).filter((h) => h.status !== 'stopped');
  const lines = [];
  const busy = hs.filter((h) => h.status === 'running' || h.status === 'queued');
  // Ben Oct 29: "I don't care when the next model runs": no upcoming or last Mote runs, only what is happening now
  if (busy.length > 1) lines.push(busy.length + ' Motes working');
  if (i.autoSleep && i.sleepFrom && !i.asleep) lines.push('Sleeps around ' + i.sleepFrom);
  lines.push(i.gateway === 'ready' ? 'Assistant is on' : i.gateway === 'down' ? 'Assistant is off' : 'Assistant is starting');
  return { head: busy.length ? 'Glim · Running ' + clip(busy[0].name, 24) : 'Glimmering', lines };
}

module.exports = { idleSummary, whenLabel, agoLabel };
