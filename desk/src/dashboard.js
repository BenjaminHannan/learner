'use strict';
// "Important updates" dashboard: the DATA side. Pure functions only (no Electron, no files, no clock unless passed in), so a
// new look can be dropped in later without touching any of this. buildDashboard(input) returns a plain model:
//   { hero: {needs, title, sub, next}, items: [item], needs, worth, done, quiet, counts: {junk, handled, needs}, checkedAt, signature, generatedAt }
//   item = { id, kind, level, icon, title, meta, metaTone ('soon' | ''), sub, facts: [short strings], why, createdAt (ms | null),
//            actions: [action], quick: [action] (needs-you rows only, always visible), list?: [strings], details?: [raw strings] }
//   action = { label, primary?, kind: 'override' | 'system', op/keys (override) or pane (system), toast?, undo?: action }
//   level is needs | worth | done | quiet: the four sections, in urgency order. icon is a name the view draws as a line icon.
// Real data only: a row with nothing real behind it is simply not there, and an action is only listed when the app can really do it.
// src/dashboard-sources.js reads the files; the view (renderer/dashboard.js) draws the model.
//
// input: { now (ms), summary (summary.md text), inbox (inbox.md text), mail ([{sender,address,subject,reason,ts,headers}]),
//          events ([events.jsonl objects]), status (status.json), nights ([nights.jsonl objects]), overrides ({notJunk: [mail keys]}),
//          tracked ([{what,until,source,added}]), contacts ([names / addresses Ben writes to]), fyi ([{icon,title,line}]), progress ([{id,title,line}]) }

// ---------------------------------------------------------------- small helpers
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const pad = (n) => String(n).padStart(2, '0');
const ymd = (ms) => { const d = new Date(ms); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };
const daysBetween = (a, b) => Math.round((Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / 86400000);
const niceDate = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || '')); return m ? MONTHS[Number(m[2]) - 1] + ' ' + Number(m[3]) : ''; };
const plural = (n, one, many) => n + ' ' + (n === 1 ? one : many || one + 's');
const clip = (s, n) => { s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s; };
const tsMs = (s) => { const t = Date.parse(s); return Number.isFinite(t) ? t : NaN; };

// ---------------------------------------------------------------- the morning summary (summary.md)
// Parses the sleep app's text. Unknown lines are ignored; nothing is invented.
function parseSummary(text) {
  const out = { wokeAt: NaN, quizText: '', quizSeries: [], needed: [], errors: [], nights: [], trainedNights: 0, passRate: null };
  let sect = '';
  for (const raw of String(text || '').split(/\r?\n/)) {
    const line = raw.replace(/\s+$/, '');
    const h = /^##\s+(.*)$/.exec(line);
    if (h) { sect = h[1].trim().toLowerCase(); continue; }
    if (/^#\s/.test(line)) { sect = ''; continue; }
    if (sect.startsWith('things that needed you')) { const b = /^\s*-\s+(.*)$/.exec(line); if (b && b[1].trim()) out.needed.push(b[1].trim()); continue; }
    if (sect === 'errors') { const b = /^\s*-\s+(.*)$/.exec(line); if (b && b[1].trim()) out.errors.push(b[1].trim()); continue; }
    if (sect === 'what it learned') {
      let m = /^Night of ([^:]+): (UNDONE|kept)/.exec(line);
      if (m) { out.nights.push({ date: m[1].trim(), kept: m[2] === 'kept', recallBefore: null, recallAfter: null }); continue; }
      m = /Held-out recall.*?:\s*(n\/a|[\d.]+)%?\s*before\s*->\s*(n\/a|[\d.]+)%?\s*after/.exec(line);
      if (m && out.nights.length) { const n = out.nights[out.nights.length - 1]; n.recallBefore = m[1] === 'n/a' ? null : Number(m[1]); n.recallAfter = m[2] === 'n/a' ? null : Number(m[2]); }
      continue;
    }
    let m = /^-\s*Woke up:\s*(\S+)/.exec(line);
    if (m) { out.wokeAt = tsMs(m[1]); continue; }
    m = /^-\s*Quiz \([^)]*\):\s*(.*)$/.exec(line);
    if (m) {
      out.quizText = m[1].trim();
      const nums = out.quizText.match(/^(-?[\d.]+)(?:\s*->\s*(-?[\d.]+))?/);
      if (nums && !/no score/i.test(out.quizText)) out.quizSeries = [Number(nums[1])].concat(nums[2] != null ? [Number(nums[2])] : []).filter(Number.isFinite);
      continue;
    }
    m = /^-\s*First-try pass rate:\s*(\d+)%(?:\s*->\s*(\d+)%)?/.exec(line);
    if (m) out.passRate = { from: Number(m[1]), to: m[2] != null ? Number(m[2]) : Number(m[1]) };
  }
  out.trainedNights = out.nights.filter((n) => n.kept).length;
  return out;
}

// ---------------------------------------------------------------- email: parsing and the junk filter
// inbox.md entries: "## <iso>  Sender Name <address-cut-off: Subject>\n<reason>"
function parseInbox(text) {
  const out = [];
  const lines = String(text || '').split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const h = /^##\s+(\S+)\s+(.*)$/.exec(lines[i]);
    if (!h) continue;
    let rest = h[2];
    let name = '', address = '', subject = '';
    let m = /^(.*?)\s*<([^>:]*)>?:\s+(.*)$/.exec(rest);
    if (m) { name = m[1]; address = m[2]; subject = m[3]; }
    else if ((m = /^([^:]{1,60}):\s+(.*)$/.exec(rest))) { name = m[1]; subject = m[2]; }
    else subject = rest;
    let reason = '';
    for (let j = i + 1; j < lines.length && !/^##\s/.test(lines[j]); j++) if (lines[j].trim()) { reason = lines[j].trim(); break; }
    if (/^sleep mode needs permission/i.test(subject) || /^sleep mode needs permission/i.test(name)) continue; // the app talking to itself, not mail
    out.push({ ts: tsMs(h[1]), sender: name.trim(), address: address.trim(), subject: subject.trim(), reason });
  }
  return out;
}

// Each signal adds to a score; at JUNK_AT or more the email is junk. Everything is a fixed rule (no asking Ben, no model).
const JUNK_AT = 0.6;
const RX = {
  strongSender: /no-?reply|do-?not-?reply|donotreply|newsletter|marketing|promo|rewards|editorpicks|digest|mailer-daemon|bounce|unsubscribe|\b(?:deals?|offers?|sales)(?:@|_at_)/i,
  weakSender: /notif|news|alert|update|info(?:@|_at_)|hello(?:@|_at_)|team(?:@|_at_)|support|service|remind|facebookmail|ifttt|orders?(?:@|_at_)|mail_at_|receipt|billing/i,
  senderName: /\b(rewards?|extracare|deals?|offers?|newsletter|news|digest|daily|weekly|briefing|roundup|headlines|notifications?|alerts?|promotions?|marketing|team|club|store|shop)\b/i,
  domainLabel: /^(e|em|email\w*|mail\w*|news\w*|info|go|click|mkt\w*|marketing|community|notify|updates?|offers?|promo\w*|send\w*|reply|bounce|mystore|shop|store|rewards?)$/i,
  subjectStrong: /\b(\d{1,3}\s?%\s?off|sale\b|coupon|discount|exclusive|limited[- ]time|last call|don'?t miss|bonus|rewards?|points\b|free\b|win\b|giveaway|unsubscribe|view (?:this )?(?:email )?in (?:your )?browser|webinar|newsletter|your (?:recent )?purchase|recent purchase|survey|tell us|how did we do|rate your|are you in\b|today.?s the day|new arrivals|shop now|order now|flash|deal\b|deals\b|save \$?\d+|you(?:'|’)?ve been selected|special offer)/i,
  subjectList: /^\s*\d{1,3}\s+(?:new|best|top|ways|things|tools|tips|reasons|ideas|must)\b/i,
  subjectNotifs: /\byou have \d+ (?:new )?notifications?\b/i,
  emoji: /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{231A}-\u{23FF}\u{2B50}\u{2B55}]/u,
  reply: /^\s*(re|fwd?)\s*:/i,
  school: /(\.edu\b|\bk12\b|schoology|\bschool\b|classroom\.google|canvas\.instructure|powerschool|dresden)/i,
  urgent: /\b(urgent|asap|today|deadline|due|overdue|action required|payment failed|security alert|verify|interview|final notice|tomorrow)\b/i
};

function normName(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9@. ]/g, ' ').replace(/\s+/g, ' ').trim(); }

// m: {sender, address, subject, reason, headers:{'list-unsubscribe', precedence, category, 'x-...'}, snippet}; contacts: [string]
// -> {junk, personal, score, signals:[..]}. personal = a real person or school (never junk). junk = hide. otherwise "unsure".
function classifyMail(m, contacts) {
  const sender = String(m.sender || ''), address = String(m.address || ''), subject = String(m.subject || '');
  const headers = {}; for (const k of Object.keys(m.headers || {})) headers[k.toLowerCase()] = String(m.headers[k]);
  const signals = []; let score = 0;
  const add = (w, why) => { score += w; signals.push(why); };
  const who = (sender + ' ' + address).toLowerCase();
  // two-way contact: someone Ben already writes to is never junk
  const known = (contacts || []).map(normName).filter((c) => c.length >= 3);
  const contact = known.some((c) => normName(sender) === c || (address && normName(address).includes(c)) || (c.includes('@') && who.includes(c)));
  if (contact) return { junk: false, personal: true, score: 0, signals: ['someone you write to'] };
  if (headers['list-unsubscribe'] || headers['list-id']) add(0.8, 'has an unsubscribe link');
  if (/bulk|list|junk/.test(headers.precedence || '')) add(0.6, 'sent in bulk');
  if (/promo|update|social|forum|marketing/i.test(headers.category || headers['x-gmail-labels'] || '')) add(0.6, 'promotions folder');
  if (RX.strongSender.test(address) || RX.strongSender.test(sender.replace(/\s+/g, ''))) add(0.7, 'no-reply or marketing sender');
  else if (RX.weakSender.test(address) || RX.weakSender.test(sender)) add(0.3, 'automatic-looking sender');
  if (RX.senderName.test(sender)) add(0.3, 'sender name looks like a company');
  if (/_at_/.test(address)) add(0.4, 'sent through a mailing system');
  const dom = (address.split(/@|_at_/)[1] || '').split(/[._]/).filter(Boolean);
  if (dom.length && RX.domainLabel.test(dom[0])) add(0.3, 'mailing-list address');
  // subject clues are weaker than sender clues: a friend can write "free pizza?" or "win the game!"
  const senderScore = score;
  let subj = 0; const subjSig = [];
  const addS = (w, why) => { subj += w; subjSig.push(why); };
  if (RX.subjectStrong.test(subject)) addS(0.6, 'sounds like an ad or survey');
  if (RX.subjectList.test(subject)) addS(0.4, 'list-style headline');
  if (RX.subjectNotifs.test(subject)) addS(0.6, 'automatic notification');
  if (RX.emoji.test(subject)) addS(0.2, 'emoji in the subject');
  if (/!\s*$/.test(subject)) addS(0.1, 'shouting');
  const looksPerson = /^[A-Z][\p{L}'’-]+(?:\s+[A-Z][\p{L}'’-]+){1,3}$/u.test(sender.trim()) && !RX.senderName.test(sender);
  if (looksPerson && senderScore === 0) subj = Math.min(subj, 0.4);
  score += subj; signals.push(...subjSig);
  // things that point to a real person
  const school = RX.school.test(who);
  if (school) { score -= 0.5; signals.push('school address'); }
  const reply = RX.reply.test(subject);
  if (reply) { score -= 0.6; signals.push('a reply in a conversation'); }
  const junk = score >= JUNK_AT;
  const personal = !junk && (school || reply || (looksPerson && senderScore === 0 && !!address));
  return { junk, personal, score: Math.round(score * 100) / 100, signals };
}

const displayName = (m) => clip(m.sender || (m.address || '').split(/@|_at_/)[0] || 'Someone', 28);

// Mail items for the dashboard: what the morning card listed plus anything newer in the inbox log, each matched to its sender.
function collectMail(input, sum) {
  const now = input.now || Date.now();
  let inbox = Array.isArray(input.mail) ? input.mail.slice() : parseInbox(input.inbox);
  const bySubject = new Map();
  for (const m of inbox) if (!bySubject.has(m.subject)) bySubject.set(m.subject, m);
  const seen = new Set(), out = [];
  const take = (m) => { const k = m.subject + '|' + (m.sender || ''); if (!m.subject || seen.has(k)) return; seen.add(k); out.push(m); };
  for (const s of sum.needed) take(bySubject.get(s) || { sender: '', address: '', subject: s, reason: '', ts: NaN });
  // newer than the morning card (or, with no card, from the last 2 days)
  const since = Number.isFinite(sum.wokeAt) ? sum.wokeAt : now - 2 * 86400000;
  for (const m of inbox) if (Number.isFinite(m.ts) && m.ts > since) take(m);
  return out;
}

// ---------------------------------------------------------------- errors, grouped into plain lines
function errorGroup(text) {
  const t = String(text || '');
  if (/sleep worker|sleepmlx|trainer|adapter|chunk|mps backend|out of memory/i.test(t)) return 'sleep';
  if (/no space left|disk full|ENOSPC|errno 28/i.test(t)) return 'disk';
  if (/\bmail\b|scanner/i.test(t)) return 'mail';
  if (/calendar/i.test(t)) return 'calendar';
  return 'other';
}
const isoDay = (ts) => String(ts || '').slice(0, 10);

// Looks at the raw errors (events + the summary's list) and returns [{key, count, nights, lastTs, resolved, raw:[..]}].
// Sleep problems count only after the last night that really trained (older ones are history); other problems only the last 2 days.
function groupErrors(input, sum) {
  const now = input.now || Date.now();
  const events = Array.isArray(input.events) ? input.events : [];
  const recs = []; // {key, ts, t, raw, sleepChunk}
  let lastTrained = NaN, sawEvents = false;
  for (const e of events) {
    if (!e || !e.ts) continue;
    const t = tsMs(e.ts);
    if (e.kind === 'chunk_done') {
      if (e.info && e.info.error) { sawEvents = true; recs.push({ key: 'sleep', ts: e.ts, t, raw: e.info.error, chunk: true }); }
      else if (e.steps > 0) lastTrained = t;
    } else if (e.kind === 'error') { sawEvents = true; recs.push({ key: errorGroup(e.error), ts: e.ts, t, raw: (e.where ? e.where + ': ' : '') + e.error }); }
    else if (e.kind === 'checkin_scanner_error') { sawEvents = true; recs.push({ key: errorGroup(e.scanner || 'mail'), ts: e.ts, t, raw: (e.scanner || 'mail') + ': ' + e.error }); }
  }
  if (!sawEvents) for (const r of sum.errors) recs.push({ key: errorGroup(r), ts: '', t: NaN, raw: r, chunk: errorGroup(r) === 'sleep' });
  const groups = new Map();
  for (const r of recs) {
    const sleepOld = r.key === 'sleep' && Number.isFinite(lastTrained) && Number.isFinite(r.t) && r.t <= lastTrained;
    const window = (r.key === 'sleep' ? 7 : 2) * 86400000;
    const stale = Number.isFinite(r.t) && now - r.t > window;
    if (sleepOld || stale) continue;
    if (!groups.has(r.key)) groups.set(r.key, { key: r.key, count: 0, days: new Set(), lastTs: NaN, raw: new Map(), resolved: false });
    const x = groups.get(r.key);
    if (r.key !== 'sleep' || r.chunk) x.count++;   // a sleep incident is both a chunk_done error and an "error" event: count it once
    if (r.ts) x.days.add(isoDay(r.ts));
    if (Number.isFinite(r.t) && !(x.lastTs >= r.t)) x.lastTs = r.t;
    const k = clip(r.raw, 200); x.raw.set(k, (x.raw.get(k) || 0) + 1);
  }
  const out = [...groups.values()].map((x) => ({ key: x.key, count: x.count || 1, nights: x.days.size, lastTs: x.lastTs, resolved: false,
    raw: [...x.raw.entries()].map(([r, n]) => (n > 1 ? r + '  (×' + n + ')' : r)) }));
  const order = { sleep: 0, mail: 1, calendar: 2, disk: 3, other: 4 };
  return out.sort((a, b) => order[a.key] - order[b.key]);
}

// ---------------------------------------------------------------- one row per event
const mkItem = (level, o) => ({ level, kind: o.kind || level, icon: o.icon, id: o.id, title: o.title, meta: o.meta || '', metaTone: o.metaTone || '', sub: o.sub || '',
  facts: o.facts || [], why: o.why || '', createdAt: Number.isFinite(o.createdAt) ? o.createdAt : null, actions: o.actions || [], quick: o.quick || [],
  ...(o.list ? { list: o.list } : {}), ...(o.details && o.details.length ? { details: o.details } : {}) });

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const clock = (ms) => { const d = new Date(ms); let h = d.getHours(); const ap = h >= 12 ? 'pm' : 'am'; h = h % 12 || 12; return h + ':' + pad(d.getMinutes()) + ' ' + ap; };
// "4:52 pm" for today, "Nov 2" for an earlier day ('' when the time is not known)
const whenShort = (ms, now) => (Number.isFinite(ms) ? (ymd(ms) === ymd(now) ? clock(ms) : niceDate(ymd(ms))) : '');
const weekday = (ymdStr) => WEEKDAYS[new Date(ymdStr + 'T12:00:00').getDay()];

function errorItem(grp, now) {
  const base = { id: 'fix:' + grp.key, kind: 'autofix', icon: 'wrench', details: grp.raw.slice(0, 6), meta: whenShort(grp.lastTs, now), createdAt: grp.lastTs,
    why: 'Premonition retries problems on its own. The exact error text is under Details.' };
  if (grp.key === 'sleep') {
    if (grp.resolved) return mkItem('done', { ...base, title: 'Sleep had a hiccup, then worked again', sub: 'It fixed itself.' });
    const n = grp.nights || 1;
    return mkItem('done', { ...base, title: n > 1 ? "Sleep couldn't train for " + n + ' nights; retrying automatically' : "Sleep couldn't train this time; retrying automatically",
      sub: 'Nothing is lost. It saves its place and tries again on its own.', facts: ["I'll try again at the next sleep."] });
  }
  if (grp.key === 'mail') return mkItem('done', { ...base, title: 'Checking your mail was slow ' + (grp.count > 1 ? plural(grp.count, 'time') : 'once') + '; tried again on its own', sub: 'No mail was touched.' });
  if (grp.key === 'disk') return mkItem('done', { ...base, title: 'The Mac ran short of disk space ' + (grp.count > 1 ? plural(grp.count, 'time') : 'once') + '; tried again on its own', sub: 'If it keeps happening, free up some space.' });
  if (grp.key === 'calendar') return mkItem('done', { ...base, title: "Couldn't look at your calendar " + (grp.count > 1 ? plural(grp.count, 'time') : 'once') + '; retrying automatically', sub: 'Nothing was changed.' });
  return mkItem('done', { ...base, title: 'Something hiccuped ' + (grp.count > 1 ? plural(grp.count, 'time') : 'once') + '; retrying automatically', sub: 'It is trying again on its own.' });
}

// ---------------------------------------------------------------- the model
function deadlineMeta(days, until) {
  if (days < 0) return 'late';
  if (days === 0) return 'today';
  if (days === 1) return 'tomorrow';
  return weekday(until) + ' · ' + days + ' days';
}
const nextWord = (days, until) => (days <= 0 ? 'today' : days === 1 ? 'tomorrow' : weekday(until));

const permPane = (perm) => (/screen/i.test(perm) ? 'screen' : /access/i.test(perm) ? 'accessibility' : /mic/i.test(perm) ? 'microphone' : 'automation');
const topReasons = (rows, k) => {
  const c = new Map();
  for (const r of rows) for (const s of r.c.signals) c.set(s, (c.get(s) || 0) + 1);
  return [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, k).map(([s, n]) => s + ' (' + n + ')');
};
const mailList = (rows) => {
  const list = rows.slice(0, 8).map((r) => (r.m.sender ? displayName(r.m) + ': ' : '') + clip(r.m.subject, 70));
  if (rows.length > 8) list.push('…and ' + (rows.length - 8) + ' more');
  return list;
};

// input.overrides: { notJunk: [mail keys] } from src/dashboard-overrides.js. Mail Ben put back is never hidden again until he undoes it.
function buildDashboard(input) {
  input = input || {};
  const now = Number.isFinite(input.now) ? input.now : Date.now();
  const today = ymd(now);
  const sum = parseSummary(input.summary);
  const needs = [], done = [], worth = [], quiet = [];
  let handled = 0;
  const notJunk = new Set((input.overrides && input.overrides.notJunk) || []);

  // ---- email: junk is hidden and counted; real people go to "worth knowing"; "needs you" only for a person + something urgent
  const contacts = input.contacts || [];
  const mail = collectMail(input, sum);
  const junk = [], people = [], unsure = [], putBack = [];
  for (const m of mail) {
    const c = classifyMail(m, contacts);
    const row = { m, c, key: m.subject + '|' + (m.sender || '') };
    if (c.junk && notJunk.has(row.key)) putBack.push(row);
    else if (c.junk) junk.push(row); else if (c.personal) people.push(row); else unsure.push(row);
  }
  if (junk.length) {
    handled += junk.length;
    const keys = junk.map((r) => r.key);
    const reasons = topReasons(junk, 3);
    const newest = Math.max(...junk.map((r) => (Number.isFinite(r.m.ts) ? r.m.ts : -Infinity)));
    done.push(mkItem('done', { id: 'junk', kind: 'junk_batch', icon: 'filter', title: 'Hid ' + plural(junk.length, 'junk email'), meta: whenShort(newest, now),
      sub: 'Ads and automatic mail. You do not need to read these.',
      facts: ['I only hide them here. Nothing in your mailbox was changed or deleted.'],
      why: 'Fixed rules, not a guess about you' + (reasons.length ? ': ' + reasons.join(', ') : '') + '. School addresses, replies and people you write to count against hiding.',
      createdAt: newest, list: mailList(junk),
      actions: [{ label: 'Put all back', kind: 'override', op: 'unhide', keys,
        toast: junk.length === 1 ? 'Put 1 email back in Worth knowing.' : 'Put ' + junk.length + ' emails back in Worth knowing.', undo: { kind: 'override', op: 'rehide', keys } }] }));
  }
  for (const { m, c } of people) {
    const urgent = RX.urgent.test(m.subject) && !RX.emoji.test(m.subject);
    const it = mkItem(urgent ? 'needs' : 'worth', { id: 'mail:' + m.subject, kind: 'email', icon: urgent ? 'reply' : 'mail', title: m.sender ? displayName(m) : clip(m.subject, 90),
      meta: whenShort(m.ts, now), sub: m.sender ? clip(m.subject, 90) : '', createdAt: m.ts,
      facts: [urgent ? 'Looks like it wants an answer soon.' : 'From a real person. You can read it later.'],
      why: 'It looks like it came from a real person' + (c.signals.length ? ' (' + c.signals.join(', ') + ')' : '') + (urgent ? ', and the subject has an urgent word.' : '.') });
    (urgent ? needs : worth).push(it);
  }
  if (unsure.length) {
    worth.push(mkItem('worth', { id: 'mail:maybe', kind: 'email', icon: 'mail', title: plural(unsure.length, 'email') + ' I was not sure about',
      sub: 'Not clearly junk, not clearly from a person.', list: mailList(unsure), createdAt: Math.max(...unsure.map((r) => (Number.isFinite(r.m.ts) ? r.m.ts : -Infinity))),
      why: 'They did not look like ads, and they did not look like a person or your school, so I left them for you.' }));
  }
  if (putBack.length) {
    const keys = putBack.map((r) => r.key);
    worth.push(mkItem('worth', { id: 'mail:restored', kind: 'email', icon: 'mail', title: plural(putBack.length, 'email') + ' you put back', sub: 'You said these are not junk.',
      list: mailList(putBack), why: 'You pressed "Put all back" on them.',
      actions: [{ label: 'Hide them again', kind: 'override', op: 'rehide', keys, toast: 'Hidden again.', undo: { kind: 'override', op: 'unhide', keys } }] }));
  }

  // ---- deadlines: due today or late needs you; the next two weeks are worth knowing
  const dl = [];
  for (const t of input.tracked || []) {
    if (!t || !t.what || !/^\d{4}-\d{2}-\d{2}$/.test(t.until || '')) continue;
    dl.push({ t, days: daysBetween(today, t.until) });
  }
  dl.sort((a, b) => a.days - b.days);
  let next = null;
  for (const { t, days } of dl) {
    if (days > 14) continue;
    const src = t.source ? ' (' + clip(t.source, 40) + ')' : '';
    const added = /^\d{4}-\d{2}-\d{2}$/.test(t.added || '') ? Date.parse(t.added + 'T00:00:00') : NaN;
    const it = mkItem(days <= 0 ? 'needs' : 'worth', { id: 'deadline:' + t.what, kind: 'deadline', icon: 'calendar', title: clip(t.what, 90), meta: deadlineMeta(days, t.until),
      metaTone: days <= 1 ? 'soon' : '', sub: (days < 0 ? 'Was due ' : 'Due ') + niceDate(t.until) + src + '.', createdAt: added,
      why: 'It is on your "keeping track of" list' + (days <= 0 ? ', and its date has come.' : ', and it is due within two weeks.') });
    if (days <= 0) needs.push(it); else { worth.push(it); if (!next) next = { title: it.title, when: nextWord(days, t.until) }; }
  }

  // ---- sleep: what it learned (a finished night) and the quiz score vs the night before
  const nights = (Array.isArray(input.nights) ? input.nights : []).filter((n) => n && n.status === 'done' && !n.dry_run);
  const lastDone = nights[nights.length - 1];
  const prevDone = nights[nights.length - 2];
  const sNight = sum.nights[sum.nights.length - 1];
  const pctNum = (v) => (typeof v === 'number' && Number.isFinite(v) ? (v > 0 && v <= 1 ? v * 100 : v) : null);
  const fmtPct = (v) => (Math.round(v * 10) / 10) + '%';
  let quizNow = pctNum(lastDone && lastDone.quiz), quizPrev = pctNum(prevDone && prevDone.quiz);
  if (sum.quizSeries.length) { const q = sum.quizSeries; quizNow = q[q.length - 1]; if (q.length > 1) quizPrev = q[0]; }
  const quizLine = quizNow == null ? 'Morning quiz: no score yet.' :
    'Morning quiz: ' + fmtPct(quizNow) + (quizPrev != null ? (quizNow > quizPrev ? ', up from ' : quizNow < quizPrev ? ', down from ' : ', same as ') + fmtPct(quizPrev) + (sum.quizSeries.length > 1 ? ' earlier' : ' last time') : '') + '.';
  let sleepShown = false;
  if (sNight || lastDone) {
    const kept = sNight ? sNight.kept : !lastDone.reverted;
    const date = niceDate(sNight ? sNight.date : lastDone.date);
    const facts = [];
    if (kept) facts.push('It practised and kept what it learned' + (date ? ' (night of ' + date + ')' : '') + '.');
    else facts.push('It practised' + (date ? ' on the night of ' + date : '') + ', checked itself, and undid the change' + (lastDone && lastDone.harm > 0 ? ' because it got a little worse at general questions' : '') + '.');
    facts.push(quizLine);
    const delta = quizNow != null && quizPrev != null ? Math.round((quizNow - quizPrev) * 10) / 10 : null;
    const meta = quizNow == null ? '' : 'Quiz ' + fmtPct(quizNow) + (delta ? ' (' + (delta > 0 ? '+' : '') + delta + ')' : '');
    done.unshift(mkItem('done', { id: 'sleep', kind: 'sleep', icon: 'moon', title: kept ? 'Learned something new overnight' : 'Slept, but kept nothing new', meta,
      facts, why: 'After practising, it takes a closed-book quiz on things it did not practise. If it got worse, it undoes the change.',
      createdAt: Number.isFinite(sum.wokeAt) ? sum.wokeAt : NaN }));
    sleepShown = true;
    if (kept) handled += 1;
  }

  // ---- problems: grouped into one plain line each; raw text only inside "details"
  for (const grp of groupErrors(input, sum)) { done.push(errorItem(grp, now)); handled += 1; }

  // ---- progress (only real numbers). The quiz score already sits on the sleep row when there is one.
  if (!sleepShown && sum.quizSeries.length > 1 && sum.quizSeries[sum.quizSeries.length - 1] > sum.quizSeries[0]) {
    const q = sum.quizSeries;
    quiet.push(mkItem('quiet', { id: 'progress:quiz', kind: 'health', icon: 'bolt', title: 'Quiz score is going up', meta: fmtPct(q[0]) + ' to ' + fmtPct(q[q.length - 1]), facts: ['During the last sleep.'] }));
  }
  if (sum.passRate && sum.passRate.to > sum.passRate.from) quiet.push(mkItem('quiet', { id: 'progress:pass', kind: 'health', icon: 'bolt', title: 'Getting more answers right on the first try', meta: sum.passRate.from + '% to ' + sum.passRate.to + '%' }));
  for (const p of input.progress || []) if (p && p.title) quiet.push(mkItem('quiet', { id: 'progress:' + (p.id || p.title), kind: 'health', icon: 'bolt', title: clip(p.title, 90), facts: p.line ? [clip(p.line, 120)] : [] }));
  for (const f of input.fyi || []) if (f && f.title) quiet.push(mkItem('quiet', { id: 'fyi:' + (f.id || f.title), kind: 'project', icon: 'game', title: clip(f.title, 90), facts: f.line ? [clip(f.line, 140)] : [] }));

  // the sleep app itself asking for a permission is something only Ben can do
  const perm = input.status && input.status.needs_permission;
  if (perm) {
    const what = clip(typeof perm === 'string' ? perm : 'access', 60);
    needs.unshift(mkItem('needs', { id: 'permission', kind: 'autofix', icon: 'key', title: 'Allow ' + what, sub: 'Premonition cannot go on until you say yes.',
      createdAt: tsMs(input.status && input.status.updated), facts: ['The sleep app asked for it and is waiting.'], why: 'Only you can allow this, in System Settings. I cannot do it for you.',
      quick: [{ label: 'Open settings', primary: true, kind: 'system', pane: permPane(String(perm)) }] }));
  }

  // worth-knowing order: deadlines, people, restored mail, unsure mail
  const rank = (it) => (it.id.startsWith('deadline') ? 0 : it.id === 'mail:restored' ? 3 : it.id === 'mail:maybe' ? 2 : 1);
  worth.sort((a, b) => rank(a) - rank(b));

  const n = needs.length;
  const nextText = next ? ' Next: ' + next.title + ', ' + next.when + '.' : '';
  const hero = {
    needs: n,
    title: n === 0 ? 'Nothing needs you' : n === 1 ? '1 thing needs you' : n + ' things need you',
    sub: n === 0 ? (handled > 0 ? 'I handled ' + plural(handled, 'thing') + '.' + nextText : next ? nextText.trim() : 'All quiet. Nothing to handle.')
      : handled > 0 ? 'I handled the other ' + handled + '.' + nextText : 'Nothing else to report.' + nextText,
    next
  };
  const checkedAt = tsMs(input.status && input.status.last_checkin);
  const model = { generatedAt: now, user: typeof input.user === 'string' ? input.user : '', hero, needs, worth, done, quiet, items: [].concat(needs, worth, done, quiet),
    counts: { junk: junk.length, handled, needs: n }, checkedAt: Number.isFinite(checkedAt) ? checkedAt : null };
  model.signature = signatureOf(model);
  return model;
}

// A short fingerprint of what the dashboard says (not when it was built): a refresh with the same signature changes nothing on screen.
// (createdAt is left out: it only decides which rows get a "new" dot, and that is worked out against when Ben last looked.)
function signatureOf(m) {
  return JSON.stringify([m.hero.title, m.hero.sub, m.checkedAt, m.items.map((i) => [i.id, i.level, i.title, i.meta, i.sub, i.facts, i.why, i.list || null, i.details || null, i.actions, i.quick])]);
}

module.exports = { buildDashboard, parseSummary, parseInbox, classifyMail, collectMail, groupErrors, errorItem, signatureOf, JUNK_AT, ymd, daysBetween, niceDate, clock };
