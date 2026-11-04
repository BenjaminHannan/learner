'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const D = require('../src/dashboard');
const Src = require('../src/dashboard-sources');
const Over = require('../src/dashboard-overrides');
const V = require('../renderer/dashboard');

const NOW = Date.parse('2026-11-03T21:00:00-05:00');
// exactly what Ben's screenshot of the "While you slept" card showed (summary.md as the sleep app wrote it)
const SUMMARY = `# Sleep summary

- Woke up: 2026-11-03T20:41:52-05:00 (assistant started)
- Slept for 67.71 h of wall time; training time 3.18 h in 84 chunk(s)
- Quiz (held-out recall % (strict, closed book)): no score yet (a night reports one when it finishes)
- Practice rounds: 0
- Hourly check-ins: 61; pauses: 17

No night finished this time: what was done is saved and the next sleep continues it.

## Things that needed you
- Tell Us About Your Recent Purchase!
- Last call for bonus points🤭⌛
- 5 new AI tools for curious minds 🧠
- She left her kids for days. The case has ricocheted around the internet.
- 🗓️ Today’s the day! Are you in?

## Errors
- tick: RuntimeError('sleep worker: ValueError: Invalid IPv6 URL')
- tick: RuntimeError('sleep worker: ValueError: Invalid IPv6 URL')
- tick: RuntimeError('sleep worker: ValueError: Invalid IPv6 URL')
- tick: RuntimeError('sleep worker: ValueError: Invalid IPv6 URL')
- tick: RuntimeError('sleep worker: ValueError: Invalid IPv6 URL')
`;
// the matching lines of inbox.md (sender + reason are known there)
const INBOX = `## 2026-11-01T04:57:19-05:00  YouVersion <no-reply_at_community_youver: 🗓️ Today’s the day! Are you in?
urgent word: today

## 2026-11-01T02:57:15-05:00  The New York Times <editorpicks@nytimes.: She left her kids for days. The case has ricocheted around the internet.
model triage

## 2026-11-01T02:57:15-05:00  Chelsea with IFTTT <chelsea.c_at_ifttt_c: 5 new AI tools for curious minds 🧠
model triage

## 2026-11-01T02:57:15-05:00  Dunkin' Rewards <dunkinrewards_at_emaili: Last call for bonus points🤭⌛
model triage

## 2026-11-01T02:57:15-05:00  CVS ExtraCare <extracare_at_mystore_cvs_: Tell Us About Your Recent Purchase!
model triage
`;
const sleepErr = (ts) => [{ ts, kind: 'chunk_done', quiz: null, steps: 0, info: { returncode: 1, error: 'ValueError: Invalid IPv6 URL' } },
  { ts, kind: 'error', where: 'tick', error: "RuntimeError('sleep worker: ValueError: Invalid IPv6 URL')" }];
const EVENTS = [{ ts: '2026-10-28T15:07:54-04:00', kind: 'chunk_done', steps: 4, quiz: null, info: {} },
  ...sleepErr('2026-11-01T01:06:22-05:00'), ...sleepErr('2026-11-02T03:02:07-05:00'), ...sleepErr('2026-11-03T18:25:50-05:00')];
const NIGHTS = [{ date: '2026-10-28', status: 'done', dry_run: false, quiz: null, harm: 2.5, reverted: true }];

const JUNK_SUBJECTS = ['Tell Us About Your Recent Purchase!', 'Last call for bonus points🤭⌛', '5 new AI tools for curious minds 🧠',
  'She left her kids for days. The case has ricocheted around the internet.', '🗓️ Today’s the day! Are you in?'];

// ---------------------------------------------------------------- junk filter
test('the five junk emails from the screenshot are all junk (with their senders)', () => {
  const rows = D.parseInbox(INBOX);
  assert.equal(rows.length, 5);
  for (const r of rows) { const c = D.classifyMail(r, []); assert.equal(c.junk, true, r.subject + ' -> ' + JSON.stringify(c)); assert.equal(c.personal, false); }
  assert.deepEqual(rows.map((r) => r.subject).sort(), JUNK_SUBJECTS.slice().sort());
});
test('four of the five are junk from the subject alone (no sender known)', () => {
  for (const s of [JUNK_SUBJECTS[0], JUNK_SUBJECTS[1], JUNK_SUBJECTS[2], JUNK_SUBJECTS[4]]) assert.equal(D.classifyMail({ subject: s }, []).junk, true, s);
});
test('headers count: List-Unsubscribe / bulk / promotions mean junk', () => {
  assert.equal(D.classifyMail({ sender: 'Sam Lee', address: 'sam@shop.com', subject: 'Hello', headers: { 'List-Unsubscribe': '<mailto:x@y>' } }, []).junk, true);
  assert.equal(D.classifyMail({ sender: 'Sam Lee', address: 'sam@shop.com', subject: 'Hello', headers: { Precedence: 'bulk', Category: 'promotions' } }, []).junk, true);
});
test('real personal and school emails are NOT junk', () => {
  const real = [
    { sender: 'Mr. Phipps', address: 'jphipps@dresdenschools.org', subject: 'Lab report due Friday' },
    { sender: 'Sarah Johnson', address: 'sarah.johnson@gmail.com', subject: 'Want to study for the chem test?' },
    { sender: 'Coach Davis', address: 'cdavis@dresdenschools.org', subject: 'Practice moved to 4pm' },
    { sender: 'Alex Kim', address: 'alexkim@gmail.com', subject: 'Re: group project slides' },
    { sender: 'Maria Lopez', address: 'maria.lopez@gmail.com', subject: 'Free pizza at lunch?' },
    { sender: 'Ms. Ortiz', address: 'ortiz@lincoln.k12.us', subject: 'Your essay feedback' }
  ];
  for (const m of real) { const c = D.classifyMail(m, []); assert.equal(c.junk, false, m.subject + ' ' + JSON.stringify(c)); assert.equal(c.personal, true, m.subject); }
});
test('someone Ben already writes to is never junk, even with an automatic-looking address', () => {
  const m = { sender: 'Mom', address: 'noreply.mom@gmail.com', subject: 'Last call for dinner!' };
  assert.equal(D.classifyMail(m, []).junk, true);
  assert.deepEqual([D.classifyMail(m, ['mom']).junk, D.classifyMail(m, ['mom']).personal], [false, true]);
});

// ---------------------------------------------------------------- the screenshot, through the whole builder
test('screenshot content: nothing needs you, 5 junk emails hidden, ONE plain error line (summary only)', () => {
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX });
  assert.equal(m.hero.title, 'Nothing needs you');
  assert.equal(m.hero.needs, 0); assert.deepEqual(m.needs, []);
  assert.equal(m.counts.junk, 5);
  const junk = m.done.find((i) => i.id === 'junk');
  assert.equal(junk.title, 'Hid 5 junk emails'); assert.equal(junk.list.length, 5); assert.equal(junk.level, 'done');
  const fixes = m.done.filter((i) => i.id.startsWith('fix:'));
  assert.equal(fixes.length, 1);
  assert.match(fixes[0].title, /^Sleep couldn't train/); assert.match(fixes[0].title, /retrying automatically$/);
  assert.equal(fixes[0].details.length, 1); assert.match(fixes[0].details[0], /×5/);   // raw text only inside "details", counted once
  const shown = JSON.stringify([m.hero, m.needs, m.done.map((i) => [i.title, i.lines, i.list]), m.worth]);
  assert.doesNotMatch(shown, /RuntimeError|ValueError|IPv6|tick:/);
  for (const s of JUNK_SUBJECTS) assert.ok(!JSON.stringify(m.worth).includes(s), 'junk subject leaked into worth knowing: ' + s);
  assert.match(m.hero.sub, /^I handled 6 things\./);
});
test('screenshot content with the events log: "couldn\'t train for 3 nights"', () => {
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX, events: EVENTS, nights: NIGHTS });
  const fix = m.done.find((i) => i.id === 'fix:sleep');
  assert.equal(fix.title, "Sleep couldn't train for 3 nights; retrying automatically");
  assert.equal(m.done.filter((i) => i.id.startsWith('fix:')).length, 1);
  assert.equal(m.hero.title, 'Nothing needs you');
  const sleep = m.done.find((i) => i.id === 'sleep');   // the last finished night was undone: said plainly, with the quiz line
  assert.equal(sleep.title, 'Slept, but kept nothing new'); assert.ok(sleep.facts.some((l) => /no score yet/.test(l)));
});
test('an old sleep problem that a later good night fixed is not shown', () => {
  const ev = [...sleepErr('2026-10-20T01:00:00-04:00'), { ts: '2026-10-21T01:00:00-04:00', kind: 'chunk_done', steps: 100, info: {} }];
  const m = D.buildDashboard({ now: NOW, events: ev });
  assert.equal(m.done.filter((i) => i.id.startsWith('fix:')).length, 0);
});
test('other problems are grouped too (mail timeouts, disk full), never raw at the top level', () => {
  const ev = [{ ts: '2026-11-03T10:00:00-05:00', kind: 'checkin_scanner_error', scanner: 'mail', error: 'timed out after 35s' },
    { ts: '2026-11-03T11:00:00-05:00', kind: 'checkin_scanner_error', scanner: 'mail', error: 'timed out after 35s' },
    { ts: '2026-11-03T12:00:00-05:00', kind: 'error', where: 'tick', error: "OSError(28, 'No space left on device')" }];
  const m = D.buildDashboard({ now: NOW, events: ev });
  const t = m.done.map((i) => i.title);
  assert.deepEqual(t, ['Checking your mail was slow 2 times; tried again on its own', 'The Mac ran short of disk space once; tried again on its own']);
  assert.equal(m.hero.needs, 0);
});

// ---------------------------------------------------------------- "nothing needs you" logic
test('empty input: calm, no cards, nothing invented', () => {
  const m = D.buildDashboard({ now: NOW });
  assert.equal(m.hero.title, 'Nothing needs you'); assert.match(m.hero.sub, /All quiet/);
  assert.deepEqual([m.needs, m.done, m.worth, m.quiet, m.items], [[], [], [], [], []]);
});
test('junk with an urgent-sounding word ("today") never needs Ben', () => {
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX });
  assert.equal(m.hero.needs, 0);
});
test('a real person writing something urgent is the only email that needs Ben', () => {
  const inbox = INBOX + '\n## 2026-11-03T20:50:00-05:00  Mr. Phipps <jphipps@dresdenschools.org>: Lab report due tomorrow\nurgent word: due\n\n## 2026-11-03T20:55:00-05:00  Sarah Johnson <sarah.johnson@gmail.com>: Want to study for the chem test?\nmodel triage\n';
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox });
  assert.equal(m.hero.title, '1 thing needs you');
  assert.match(m.needs[0].title, /Phipps/);
  const w = m.worth.find((i) => /Sarah/.test(i.title));
  assert.equal(w.level, 'worth'); assert.match(w.sub, /study for the chem test/); assert.match(w.why, /real person/);
  assert.equal(m.counts.junk, 5);
});
test('unsure email goes to worth knowing, never to needs you', () => {
  const m = D.buildDashboard({ now: NOW, mail: [{ sender: 'Pat', address: 'pat@example.com', subject: 'Deadline is today, please confirm', ts: NOW }] });
  assert.equal(m.hero.needs, 0);
  assert.equal(m.worth[0].id, 'mail:maybe');
});
test('deadlines: due today or late need Ben; the next days are worth knowing with a time tag', () => {
  const tracked = [{ what: 'Library book', until: '2026-11-02', source: 'email' }, { what: 'Chem lab report', until: '2026-11-05' }, { what: 'FAFSA form', until: '2026-11-04' },
    { what: 'Far away', until: '2027-02-01' }, { what: 'Pay dues', until: '2026-11-03' }];
  const m = D.buildDashboard({ now: NOW, tracked });
  assert.equal(m.hero.title, '2 things need you');
  assert.deepEqual(m.needs.map((i) => i.title).sort(), ['Library book', 'Pay dues']);
  assert.deepEqual(m.worth.map((i) => [i.title, i.meta, i.metaTone]), [['FAFSA form', 'tomorrow', 'soon'], ['Chem lab report', 'Thu · 2 days', '']]);
  assert.deepEqual(m.needs.map((i) => [i.title, i.meta]).sort(), [['Library book', 'late'], ['Pay dues', 'today']]);
  assert.equal(m.hero.sub, 'Nothing else to report. Next: FAFSA form, tomorrow.');
});
test('a permission the sleep app is waiting for needs Ben', () => {
  const m = D.buildDashboard({ now: NOW, status: { needs_permission: 'Mail' } });
  assert.equal(m.hero.title, '1 thing needs you'); assert.equal(m.needs[0].icon, 'key');
  assert.deepEqual(m.needs[0].quick.map((a) => [a.label, a.kind, a.pane]), [['Open settings', 'system', 'automation']]);
});
test('sleep result: what it learned and the quiz score against yesterday', () => {
  const nights = [{ date: '2026-11-01', status: 'done', quiz: 71, reverted: false }, { date: '2026-11-02', status: 'done', quiz: 78, reverted: false }];
  const m = D.buildDashboard({ now: NOW, nights });
  const s = m.done.find((i) => i.id === 'sleep');
  assert.equal(s.title, 'Learned something new overnight'); assert.equal(s.meta, 'Quiz 78% (+7)');
  assert.ok(s.facts.some((l) => l === 'Morning quiz: 78%, up from 71% last time.'), s.facts.join('|')); assert.match(s.why, /closed-book quiz/);
  // dry runs and unfinished nights are not "learned"
  assert.equal(D.buildDashboard({ now: NOW, nights: [{ date: '2026-11-02', status: 'dry_run', dry_run: true }] }).done.length, 0);
});
test('progress and side-project rows appear only when real data exists, and sit in "Other news"', () => {
  const sum = '- Quiz (held-out recall %): 63.50 -> 78.50 (5 checks)\n- First-try pass rate: 40% -> 60%\n';
  const m = D.buildDashboard({ now: NOW, summary: sum, fyi: [{ icon: 'game', title: 'Bedwars bot project', line: 'Notes updated Nov 3.' }] });
  assert.deepEqual(m.quiet.map((i) => i.id), ['progress:quiz', 'progress:pass', 'fyi:Bedwars bot project']);
  assert.deepEqual(m.worth, []); assert.equal(m.quiet[0].meta, '63.5% to 78.5%'); assert.equal(m.quiet[2].level, 'quiet');
  assert.equal(D.buildDashboard({ now: NOW }).quiet.length, 0);
  // with a finished night the quiz score is on the sleep row already: no second row for the same fact
  const m2 = D.buildDashboard({ now: NOW, summary: sum + '\n## What it learned\nNight of 2026-11-02: kept\n', nights: [{ date: '2026-11-02', status: 'done', quiz: 78.5, reverted: false }] });
  assert.ok(!m2.quiet.some((i) => i.id === 'progress:quiz')); assert.ok(m2.done.some((i) => i.id === 'sleep'));
});
test('signature only changes when what is said changes', () => {
  const a = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX }), b = D.buildDashboard({ now: NOW + 60000, summary: SUMMARY, inbox: INBOX });
  assert.equal(a.signature, b.signature);
  assert.notEqual(a.signature, D.buildDashboard({ now: NOW, tracked: [{ what: 'Pay dues', until: '2026-11-03' }] }).signature);
});

// ---------------------------------------------------------------- reading the real file layout (read-only)
test('sources: reads a sleep folder from disk, builds the same model, and the watcher fires on a change', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dash-'));
  const home = path.join(root, 'sleepmode'), mlx = path.join(root, 'sleepmlx');
  fs.mkdirSync(home); fs.mkdirSync(mlx);
  fs.writeFileSync(path.join(home, 'summary.md'), SUMMARY); fs.writeFileSync(path.join(home, 'inbox.md'), INBOX);
  fs.writeFileSync(path.join(home, 'events.jsonl'), EVENTS.map((e) => JSON.stringify(e)).join('\n') + '\n');
  fs.writeFileSync(path.join(mlx, 'nights.jsonl'), NIGHTS.map((e) => JSON.stringify(e)).join('\n') + '\n');
  const m = Src.getDashboard({ home, now: NOW, tracked: () => [] });
  assert.equal(m.hero.title, 'Nothing needs you'); assert.equal(m.counts.junk, 5);
  assert.equal(m.done.find((i) => i.id === 'fix:sleep').title, "Sleep couldn't train for 3 nights; retrying automatically");
  assert.equal(Src.getDashboard({ home: path.join(root, 'missing'), now: NOW }).hero.title, 'Nothing needs you');   // no files: still fine, nothing invented
  let hits = 0;
  const stop = Src.watchSources({ home, debounceMs: 20, pollMs: 50 }, () => { hits++; });
  fs.appendFileSync(path.join(home, 'inbox.md'), '\n## 2026-11-03T21:00:00-05:00  Mr. Phipps <jphipps@dresdenschools.org>: Lab report due tomorrow\nurgent word: due\n');
  await new Promise((r) => setTimeout(r, 400));
  stop();
  assert.ok(hits >= 1, 'watcher saw the inbox change');
  assert.equal(Src.getDashboard({ home, now: NOW + 1000, tracked: () => [] }).hero.title, '1 thing needs you');
  fs.rmSync(root, { recursive: true, force: true });
});

// ---------------------------------------------------------------- the view: states, rows, buttons
const walk = (v, f, out = []) => { if (typeof v === 'string') return out; if (f(v)) out.push(v); for (const k of v.kids || []) walk(k, f, out); return out; };
const textOf = (v) => (typeof v === 'string' ? v : (v.text || '') + (v.kids || []).map(textOf).join(' '));
const hasCls = (n, c) => (n.cls || '').split(' ').includes(c);
const headings = (v) => walk(v, (n) => n.t === 'h3').map((n) => n.text);
const liveSt = (model, extra) => ({ model, open: new Set(), updatedAt: NOW - 120000, now: NOW, error: '', ...(extra || {}) });
const richModel = (extra) => D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX, events: EVENTS, nights: NIGHTS,
  tracked: [{ what: 'Chem lab report', until: '2026-11-05', source: 'Schoology', added: '2026-11-02' }],
  fyi: [{ icon: 'game', title: 'Bedwars bot project', line: 'x' }], status: { last_checkin: '2026-11-03T20:40:52-05:00' }, ...(extra || {}) });

test('the morning card has a button that opens the dashboard, and shows the same hero line', () => {
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX });
  let opened = 0;
  const card = V.morningCardView(m, { open: () => { opened++; } });
  assert.match(textOf(card), /While you slept/); assert.match(textOf(card), /Nothing needs you/); assert.match(textOf(card), /I handled 6 things/);
  assert.doesNotMatch(textOf(card), /RuntimeError|Tell Us About/);
  const [btn] = walk(card, (n) => n.t === 'button');
  assert.equal(btn.text, 'Open dashboard'); btn.on.click();
  assert.equal(opened, 1);
});
test('all clear: sections in urgency order, one row per event, no coloured pills, raw errors hidden', () => {
  const m = richModel();
  const v = V.dashboardView(m, liveSt(m), {});
  const t = textOf(v);
  assert.deepEqual(headings(v), ['Worth knowing', 'Done for you', 'Other news']);          // no "Needs you" section when nothing needs you
  assert.match(t, /Nothing needs you/); assert.match(t, /I handled 6 things\. Next: Chem lab report, Thu\./);
  assert.match(t, /Hid 5 junk emails/); assert.match(t, /Updated 2 min ago/);
  assert.equal(walk(v, (n) => /\bdb-tag\b|\bdb-pill\b/.test(n.cls || '')).length, 0, 'the old coloured tags are gone');
  assert.equal(walk(v, (n) => (n.attrs || {})['data-tone']).map((n) => n.attrs['data-tone']).join(), 'ok');   // colour only for state
  assert.doesNotMatch(t, /RuntimeError|ValueError|IPv6/);
  const rows = walk(v, (n) => n.t === 'button' && hasCls(n, 'db-row'));
  assert.equal(rows.filter((r) => r.attrs['data-id'] === 'fix:sleep').length, 1, 'the sleep problem is ONE row');
  assert.equal(rows.length, new Set(rows.map((r) => r.attrs['data-id'])).size);
  assert.equal(walk(v, (n) => hasCls(n, 'db-sdot') && hasCls(n, 'live')).length, 1);
});
test('"needs you" comes first, in an amber hero, and the pass mark still holds: marketing never needs you', () => {
  const m = richModel({ tracked: [{ what: 'Pay dues', until: '2026-11-03' }, { what: 'Chem lab report', until: '2026-11-05' }] });
  const v = V.dashboardView(m, liveSt(m), {});
  assert.deepEqual(headings(v), ['Needs you', 'Worth knowing', 'Done for you', 'Other news']);
  assert.match(textOf(v), /1 thing needs you/); assert.match(textOf(v), /I handled the other 6\./);
  assert.equal(walk(v, (n) => (n.attrs || {})['data-tone']).map((n) => n.attrs['data-tone']).join(), 'attn');
  assert.deepEqual(m.needs.map((i) => i.title), ['Pay dues']);           // the 5 marketing emails are not here
  assert.ok(!JSON.stringify(m.needs).includes('Last call'));
});
test('an opened row shows its facts, a "Why:" line and its real buttons; a closed row shows none of that', () => {
  const m = richModel(); const acted = [];
  const closed = textOf(V.dashboardView(m, liveSt(m), {}));
  assert.doesNotMatch(closed, /Why:/); assert.doesNotMatch(closed, /Put all back/);
  const st = liveSt(m, { open: new Set(['junk', 'fix:sleep']) });
  const v = V.dashboardView(m, st, { act: (a) => acted.push(a) });
  const t = textOf(v);
  assert.match(t, /Why:\s+Fixed rules, not a guess about you/); assert.match(t, /Nothing in your mailbox was changed or deleted/);
  assert.match(t, /Dunkin' Rewards: Last call/);                       // the hidden emails can be seen
  const put = walk(v, (n) => n.t === 'button' && n.text === 'Put all back')[0];
  put.on.click({ stopPropagation() {} });
  assert.equal(acted.length, 1); assert.deepEqual([acted[0].kind, acted[0].op, acted[0].keys.length], ['override', 'unhide', 5]);
  assert.deepEqual([acted[0].undo.op, acted[0].undo.keys.length], ['rehide', 5]);
  const det = walk(v, (n) => n.t === 'details')[0];                   // raw error text lives only inside Details
  assert.match(textOf(det), /Invalid IPv6 URL/);
});
test('every button the screen can show is wired to something real (nothing decorative)', () => {
  const REAL = new Set(['Put all back', 'Hide them again', 'Open settings', 'Try now']);
  const restored = richModel({ overrides: { notJunk: Object.keys({}).concat(richModel().done.find((i) => i.id === 'junk').actions[0].keys) }, status: { needs_permission: 'Mail' } });
  for (const model of [richModel(), restored]) {
    for (const it of model.items) for (const a of [].concat(it.actions, it.quick)) {
      assert.ok(a.kind === 'override' ? (['unhide', 'rehide'].includes(a.op) && a.keys.length) : a.kind === 'system' ? typeof a.pane === 'string' : false, JSON.stringify(a));
      assert.ok(REAL.has(a.label), a.label);
      if (a.undo) assert.equal(a.undo.kind, 'override');
    }
    const v = V.dashboardView(model, liveSt(model, { open: new Set(model.items.map((i) => i.id)) }), {});
    for (const b of walk(v, (n) => n.t === 'button' && hasCls(n, 'db-btn'))) assert.ok(REAL.has(b.text), 'unwired button: ' + b.text);
  }
  assert.ok(restored.worth.some((i) => i.id === 'mail:restored' && i.actions[0].label === 'Hide them again'));
  assert.deepEqual(restored.needs.map((i) => i.quick[0].label), ['Open settings']);
});
test('stale: after 15 minutes the hero says it may be old, with the last good time and "Try now"; no "new" dots', () => {
  const m = richModel(); let tried = 0;
  assert.equal(V.feedStatus(liveSt(m, { updatedAt: NOW - 14 * 60000 })), 'live');
  assert.equal(V.feedStatus(liveSt(m, { updatedAt: NOW - 16 * 60000 })), 'stale');
  const st = liveSt(m, { updatedAt: NOW - 3 * 3600000, error: 'ENOENT', lastSeenAt: NOW - 86400000 });
  const v = V.dashboardView(m, st, { refresh: () => { tried++; } });
  const t = textOf(v);
  assert.match(t, new RegExp('Nothing needed you at ' + V.clock(st.updatedAt))); assert.match(t, /this may be old/); assert.match(t, /Last update 3 h ago/);
  assert.doesNotMatch(t, /Updated \d/);
  assert.equal(walk(v, (n) => (n.attrs || {})['data-tone']).map((n) => n.attrs['data-tone']).join(), 'stale');
  assert.equal(walk(v, (n) => hasCls(n, 'db-newdot')).length, 0);
  walk(v, (n) => n.t === 'button' && n.text === 'Try now')[0].on.click(); assert.equal(tried, 1);
  assert.match(textOf(V.dashboardView(m, liveSt(m, { updatedAt: NOW - 3600000 }), {})), /Nothing needed you at/);
  const busy = D.buildDashboard({ now: NOW, tracked: [{ what: 'Pay dues', until: '2026-11-03' }] });
  assert.match(textOf(V.dashboardView(busy, liveSt(busy, { updatedAt: NOW - 3600000 }), {})), /1 thing needed you at/);   // never a cheerful "all clear" when it is old
});
test('error (never loaded): plain words, "Try now", the code only under Details', () => {
  let tried = 0;
  const v = V.dashboardView(null, { open: new Set(), now: NOW, error: 'ECONNRESET at ipc' }, { refresh: () => { tried++; } });
  const t = textOf(v);
  assert.match(t, /Can't load your updates/); assert.match(t, /try again in a minute/); assert.match(t, /Not connected/);
  const det = walk(v, (n) => n.t === 'details')[0];
  assert.match(textOf(det), /ECONNRESET/);
  const outside = (n) => (n === det ? '' : typeof n === 'string' ? n : (n.text || '') + (n.kids || []).map(outside).join(' '));
  assert.doesNotMatch(outside(v), /ECONNRESET/);
  assert.equal(walk(v, (n) => (n.attrs || {})['data-tone']).map((n) => n.attrs['data-tone']).join(), 'err');
  walk(v, (n) => n.t === 'button' && n.text === 'Try now')[0].on.click(); assert.equal(tried, 1);
});
test('loading: a still skeleton and "Checking…" until the first answer', () => {
  const v = V.dashboardView(null, { open: new Set(), now: NOW }, {});
  assert.match(textOf(v), /Checking…/);
  assert.ok(walk(v, (n) => (n.attrs || {})['aria-busy'] === 'true').length === 1);
  assert.equal(V.feedStatus({ now: NOW }), 'loading'); assert.equal(V.feedStatus({ now: NOW, error: 'x' }), 'error');
});
test('quiet day: a hero and one honest line, not an empty page', () => {
  const m = D.buildDashboard({ now: NOW, status: { last_checkin: '2026-11-03T20:40:52-05:00' } });
  const t = textOf(V.dashboardView(m, liveSt(m, { lastSeenAt: NOW - 3600000 }), {}));
  assert.match(t, /Nothing needs you/); assert.match(t, /All quiet/); assert.match(t, /Nothing new since 8:00 pm\./); assert.match(t, /My last check-in was at 8:40 pm\./);
  assert.match(textOf(V.dashboardView(D.buildDashboard({ now: NOW }), liveSt(D.buildDashboard({ now: NOW })), {})), /Nothing to report yet\./);   // no last-check-in claim without data
  assert.doesNotMatch(textOf(V.dashboardView(D.buildDashboard({ now: NOW }), liveSt(D.buildDashboard({ now: NOW })), {})), /last check-in/);
});
test('"new since you last looked": a blue dot on rows made after that, and a count at the top', () => {
  const m = D.buildDashboard({ now: NOW, mail: [{ sender: 'Sarah Johnson', address: 'sarah.johnson@gmail.com', subject: 'Want to study?', ts: NOW - 60000 }, { sender: 'Alex Kim', address: 'alexkim@gmail.com', subject: 'Re: slides', ts: NOW - 5 * 3600000 }] });
  const v = V.dashboardView(m, liveSt(m, { lastSeenAt: NOW - 3600000 }), {});
  assert.equal(walk(v, (n) => hasCls(n, 'db-newdot')).length, 1);
  assert.match(textOf(v), /1 new\s+since 8:00 pm/);
  assert.equal(walk(V.dashboardView(m, liveSt(m), {}), (n) => hasCls(n, 'db-newdot')).length, 0, 'the first time ever nothing is "new"');
});
test('icons: every row and hero icon exists as a line icon; mount() draws them in the SVG namespace', () => {
  const m = richModel({ status: { needs_permission: 'Mail' }, tracked: [{ what: 'Pay dues', until: '2026-11-03' }] });
  for (const it of m.items) assert.ok(V.ICONS[it.icon], 'no icon for ' + it.icon);
  for (const n of ['check', 'alert', 'clock', 'plug', 'chev']) assert.ok(V.ICONS[n]);
  const made = [];
  const doc = { createElement: (t) => mk(t, null), createElementNS: (ns, t) => mk(t, ns), createTextNode: (s) => ({ text: s }) };
  function mk(t, ns) { const e = { t, ns, attrs: {}, kids: [], listeners: {}, setAttribute(k, v) { this.attrs[k] = v; }, addEventListener() {}, appendChild(c) { this.kids.push(c); } }; made.push(e); return e; }
  V.mount(V.dashboardView(m, liveSt(m), {}), doc);
  const svgs = made.filter((e) => e.t === 'svg'); assert.ok(svgs.length > 5);
  assert.ok(svgs.every((e) => e.ns === 'http://www.w3.org/2000/svg' && e.attrs.viewBox === '0 0 24 24' && /\bdb-i\b/.test(e.attrs.class)));
  assert.ok(made.filter((e) => e.t === 'path').every((e) => e.ns === 'http://www.w3.org/2000/svg' && e.attrs.d));
});
test('keyboard: J/K and arrows move, Esc closes, Z undoes, ? lists the shortcuts; nothing with Ctrl/Cmd', () => {
  const k = (key, extra) => V.keyAction({ key, ...(extra || {}) });
  assert.deepEqual(['j', 'ArrowDown', 'k', 'ArrowUp', 'Escape', 'z', '?', 'x'].map((x) => k(x)), ['next', 'next', 'prev', 'prev', 'escape', 'undo', 'keys', null]);
  assert.equal(k('z', { metaKey: true }), null); assert.equal(k('j', { ctrlKey: true }), null);
  const m = richModel();
  assert.match(textOf(V.dashboardView(m, liveSt(m, { keys: true }), {})), /Close all/);
  assert.doesNotMatch(textOf(V.dashboardView(m, liveSt(m), {})), /Close all/);
  assert.match(textOf(V.dashboardView(m, liveSt(m), {})), /Press \? for shortcuts/);
});
test('a toast with Undo is shown when there is something to undo', () => {
  const m = richModel(); let undone = 0;
  const v = V.dashboardView(m, liveSt(m, { toast: { msg: 'Put 5 emails back in Worth knowing.', undo: { kind: 'override', op: 'rehide', keys: ['a|b'] } } }), { undo: () => { undone++; } });
  assert.match(textOf(v), /Put 5 emails back in Worth knowing\./);
  walk(v, (n) => hasCls(n, 'db-undo'))[0].on.click(); assert.equal(undone, 1);
  assert.equal(walk(V.dashboardView(m, liveSt(m, { toast: { msg: 'Undone.', undo: null } }), {}), (n) => hasCls(n, 'db-undo')).length, 0);
});

// ---------------------------------------------------------------- "Put all back" is real: saved, applied, and undoable
test('overrides: put back / hide again are saved to disk, survive a restart, and bad requests are refused', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dash-over-'));
  assert.deepEqual(Over.load(dir), { notJunk: [] });
  assert.ok(Over.apply(dir, 'unhide', ['a|Sender', 'b|Other']).ok);
  assert.deepEqual(Over.load(dir).notJunk, ['a|Sender', 'b|Other']);                  // a fresh load = after a restart
  Over.apply(dir, 'unhide', ['a|Sender']); assert.deepEqual(Over.load(dir).notJunk, ['a|Sender', 'b|Other']);   // no duplicates
  Over.apply(dir, 'rehide', ['a|Sender']); assert.deepEqual(Over.load(dir).notJunk, ['b|Other']);
  assert.ok(Over.apply(dir, 'unhide', []).error); assert.ok(Over.apply(dir, 'delete-everything', ['x|y']).error); assert.ok(Over.apply(dir, 'unhide', [42, null, {}]).error);
  fs.writeFileSync(path.join(dir, Over.FILE), '{not json'); assert.deepEqual(Over.load(dir), { notJunk: [] });   // a damaged file never breaks the dashboard
  fs.rmSync(dir, { recursive: true, force: true });
});
test('undo on hidden junk really un-hides: the batch row goes, the emails come back in Worth knowing, and Undo hides them again', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dash-over-'));
  const home = path.join(dir, 'sleepmode'); fs.mkdirSync(home);
  fs.writeFileSync(path.join(home, 'summary.md'), SUMMARY); fs.writeFileSync(path.join(home, 'inbox.md'), INBOX);
  const build = () => Src.getDashboard({ home, now: NOW, tracked: () => [], overrides: () => Over.load(dir) });
  const before = build();
  const act = before.done.find((i) => i.id === 'junk').actions[0];
  assert.equal(before.counts.junk, 5);
  assert.ok(Over.apply(dir, act.op, act.keys).ok);                                   // what the "Put all back" button does in the main process
  const after = build();
  assert.equal(after.counts.junk, 0); assert.ok(!after.done.some((i) => i.id === 'junk'));
  const back = after.worth.find((i) => i.id === 'mail:restored');
  assert.equal(back.title, '5 emails you put back'); assert.equal(back.list.length, 5);
  assert.equal(after.hero.needs, 0, 'putting emails back never makes them "need you"');
  assert.deepEqual(back.actions[0].undo.keys, act.keys);
  assert.ok(Over.apply(dir, act.undo.op, act.undo.keys).ok);                         // what Undo does
  const again = build();
  assert.equal(again.done.find((i) => i.id === 'junk').title, 'Hid 5 junk emails'); assert.ok(!again.worth.some((i) => i.id === 'mail:restored'));
  assert.notEqual(before.signature, after.signature);                                 // so an open dashboard repaints
  fs.rmSync(dir, { recursive: true, force: true });
});
test('wiring: the main window has an Updates button and sheet, the morning card opens the same dashboard, and the buttons reach the main process', () => {
  const root = path.join(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'renderer/index.html'), 'utf8'), app = fs.readFileSync(path.join(root, 'renderer/app.js'), 'utf8');
  assert.match(html, /id="btnDash"/); assert.match(html, /id="dashSheet"/); assert.match(html, /<script src="dashboard.js">/);
  assert.match(app, /\$\('#btnDash'\)\.onclick = openDash/);
  assert.match(app, /morningCardView\(dash\.state\.model, \{ open: openDash \}\)/);
  assert.match(app, /desk\.onDashboardChanged\(/);
  assert.match(app, /desk\.dashboard\.override\(a\.op, a\.keys\)/); assert.match(app, /desk\.openSystem\(a\.pane\)/);
  assert.match(fs.readFileSync(path.join(root, 'preload.js'), 'utf8'), /dashboard: \{ get: inv\('dashboard:get'\), override: inv\('dashboard:override'\) \}/);
  const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
  assert.match(main, /h\('dashboard:get'/); assert.match(main, /h\('dashboard:override', \(op, keys\) => DashOver\.apply\(/); assert.match(main, /Privacy_Automation/);
});

// ---------------------------------------------------------------- staying fresh
function fakeClock() {
  let t = 1000000; const timers = [];
  return { now: () => t, setInterval: (fn, ms) => { const x = { fn, ms, next: t + ms }; timers.push(x); return x; }, clearInterval: (x) => { timers.splice(timers.indexOf(x), 1); },
    advance(ms) { const end = t + ms; for (;;) { const due = timers.filter((x) => x.next <= end).sort((a, b) => a.next - b.next)[0]; if (!due) break; t = due.next; due.next += due.ms; due.fn(); } t = end; }, timers };
}
const flush = () => new Promise((r) => setImmediate(r));
const model = (title, sig) => ({ hero: { needs: 0, title, sub: 's' }, needs: [], done: [], worth: [], signature: sig || title });

test('refresh: loads at start, then every 60 s, on focus, and when a source file changes', async () => {
  const c = fakeClock(); let n = 0; const seen = [];
  const dash = V.createDashboard({ fetch: async () => { n++; return model('Nothing needs you today'); }, onChange: (s, i) => seen.push(i), now: c.now, setInterval: c.setInterval, clearInterval: c.clearInterval });
  dash.start(); await flush(); assert.equal(n, 1);
  c.advance(59000); await flush(); assert.equal(n, 1);
  c.advance(1500); await flush(); assert.equal(n, 2);
  dash.onFocus(); await flush(); assert.equal(n, 3);
  dash.onSourceChanged(); await flush(); assert.equal(n, 4);
  dash.stop(); c.advance(300000); await flush(); assert.equal(n, 4); assert.equal(c.timers.length, 0);
});
test('refresh: a new important item changes the hero line without a reload; an identical model changes nothing', async () => {
  const c = fakeClock(); let cur = model('Nothing needs you today'); const changes = [];
  const dash = V.createDashboard({ fetch: async () => cur, onChange: (s, i) => { if (i.kind === 'refresh') changes.push([i.changed, s.model.hero.title]); }, now: c.now, setInterval: c.setInterval, clearInterval: c.clearInterval });
  dash.start(); await flush();
  c.advance(60000); await flush();                       // same content: not "changed"
  cur = model('1 thing needs you');
  c.advance(60000); await flush();
  assert.deepEqual(changes, [[true, 'Nothing needs you today'], [false, 'Nothing needs you today'], [true, '1 thing needs you']]);
  assert.equal(dash.state.model.hero.title, '1 thing needs you');
});
test('refresh: requests never pile up, and a failed read keeps the last good model', async () => {
  const c = fakeClock(); let calls = 0, fail = false, release;
  const dash = V.createDashboard({ fetch: () => { calls++; if (fail) return Promise.reject(new Error('boom')); return new Promise((r) => { release = () => r(model('A')); }); }, now: c.now, setInterval: c.setInterval, clearInterval: c.clearInterval });
  const p = dash.refresh(); dash.refresh(); dash.refresh(); assert.equal(calls, 1);   // three triggers, one request in flight
  release(); await p; await flush(); assert.equal(calls, 2);                             // plus exactly one follow-up for what arrived meanwhile
  release(); await flush(); assert.equal(dash.state.model.hero.title, 'A');
  fail = true; await dash.refresh(); assert.equal(dash.state.model.hero.title, 'A'); assert.match(dash.state.error, /boom/);
});
test('the "updated … ago" line', () => {
  const t = 5000000;
  assert.equal(V.agoText(NaN, t), 'not updated yet');
  assert.equal(V.agoText(t - 5000, t), 'updated just now');
  assert.equal(V.agoText(t - 120000, t), 'updated 2 min ago');
  assert.equal(V.agoText(t - 60000, t), 'updated 1 min ago');
  assert.equal(V.agoText(t - 3 * 3600000, t), 'updated 3 h ago');
  assert.equal(V.agoText(t - 72 * 3600000, t), 'updated 3 days ago');
});
test('the ago line ticks without refetching (and uses its own timer)', async () => {
  const c = fakeClock(); let n = 0, ticks = 0;
  const dash = V.createDashboard({ fetch: async () => { n++; return model('X'); }, onChange: (s, i) => { if (i.kind === 'tick') ticks++; }, now: c.now, setInterval: c.setInterval, clearInterval: c.clearInterval });
  dash.start(); await flush(); c.advance(41000); await flush();
  assert.equal(n, 1); assert.equal(ticks, 2);
});

// ---------------------------------------------------------------- buttons, honest errors, closing
test('a button runs a real action; a toast with Undo follows; Undo runs the opposite and reloads', async () => {
  const c = fakeClock(); const ran = []; let loads = 0; const timers = [];
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX });
  const dash = V.createDashboard({ fetch: async () => { loads++; return m; }, act: async (a) => { ran.push([a.kind, a.op, a.keys.length]); return { ok: true }; },
    now: c.now, setInterval: c.setInterval, clearInterval: c.clearInterval, setTimeout: (fn, ms) => { timers.push([fn, ms]); return timers.length; }, clearTimeout() {} });
  await dash.refresh(); assert.equal(loads, 1);
  const put = m.done.find((i) => i.id === 'junk').actions[0];
  await dash.act(put);
  assert.deepEqual(ran, [['override', 'unhide', 5]]); assert.equal(loads, 2, 'the screen reloads after the change');
  assert.equal(dash.state.toast.msg, 'Put 5 emails back in Worth knowing.'); assert.ok(dash.state.toast.undo);
  assert.equal(await dash.undo(), true);
  assert.deepEqual(ran[1], ['override', 'rehide', 5]); assert.equal(dash.state.toast.msg, 'Undone.'); assert.equal(dash.state.toast.undo, null); assert.equal(loads, 3);
  assert.equal(await dash.undo(), false, 'nothing left to undo');
  assert.ok(timers.some(([, ms]) => ms === 10000), 'the toast goes away by itself');
});
test('a button that fails says so instead of pretending', async () => {
  const dash = V.createDashboard({ fetch: async () => model('X'), act: async () => ({ error: 'could not save: disk full' }) });
  await dash.act({ kind: 'override', op: 'unhide', keys: ['a|b'], toast: 'Put 1 email back in Worth knowing.', undo: { kind: 'override', op: 'rehide', keys: ['a|b'] } });
  assert.match(dash.state.toast.msg, /That did not work: could not save: disk full/); assert.equal(dash.state.toast.undo, null);
  dash.stop();
});
test('honest errors: no model from the main process, or no answer in time, is an error (never an endless "Checking…")', async () => {
  const none = V.createDashboard({ fetch: async () => null });
  await none.refresh(); assert.equal(V.feedStatus(none.state), 'error'); assert.match(none.state.error, /No update came back/);
  const slow = V.createDashboard({ fetch: () => new Promise(() => {}), fetchTimeoutMs: 20 });
  const keepAlive = setInterval(() => {}, 20);   // the timeout timer is unref'd (it must not hold a process open), so hold the test open
  await slow.refresh(); clearInterval(keepAlive); assert.equal(V.feedStatus(slow.state), 'error'); assert.match(slow.state.error, /did not answer in time/);
  // after a good answer a later failure keeps the old screen (and it turns "stale" only by age)
  let fail = false;
  const d = V.createDashboard({ fetch: async () => { if (fail) throw new Error('boom'); return model('A'); } });
  await d.refresh(); fail = true; await d.refresh();
  assert.equal(d.state.model.hero.title, 'A'); assert.equal(V.feedStatus(d.state), 'live'); assert.equal(V.feedStatus({ ...d.state, now: d.state.updatedAt + 16 * 60000 }), 'stale');
});
test('Esc closes opened rows first, then the shortcut list, and says when there was nothing to close', () => {
  const dash = V.createDashboard({ fetch: async () => model('A') });
  assert.equal(dash.closeAll(), false);
  dash.toggle('a'); dash.toggle('b'); dash.toggleKeys();
  assert.equal(dash.closeAll(), true); assert.equal(dash.state.open.size, 0); assert.equal(dash.state.keys, false);
  assert.equal(dash.closeAll(), false);
  dash.stop();
});
