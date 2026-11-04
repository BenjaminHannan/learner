'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const D = require('../src/dashboard');
const Src = require('../src/dashboard-sources');
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
  assert.equal(m.hero.title, 'Nothing needs you today');
  assert.equal(m.hero.needs, 0); assert.deepEqual(m.needs, []);
  assert.equal(m.counts.junk, 5);
  const junk = m.done.find((i) => i.id === 'junk');
  assert.equal(junk.title, 'Hid 5 junk emails'); assert.equal(junk.list.length, 5); assert.equal(junk.tag.text, 'hidden');
  const fixes = m.done.filter((i) => i.icon === '🔧');
  assert.equal(fixes.length, 1);
  assert.match(fixes[0].title, /^Sleep couldn't train/); assert.match(fixes[0].title, /retrying automatically$/);
  assert.equal(fixes[0].details.length, 1); assert.match(fixes[0].details[0], /×5/);   // raw text only inside "details", counted once
  const shown = JSON.stringify([m.hero, m.needs, m.done.map((i) => [i.title, i.lines, i.list]), m.worth]);
  assert.doesNotMatch(shown, /RuntimeError|ValueError|IPv6|tick:/);
  for (const s of JUNK_SUBJECTS) assert.ok(!JSON.stringify(m.worth).includes(s), 'junk subject leaked into worth knowing: ' + s);
  assert.match(m.hero.sub, /handled 6 things on its own/);
});
test('screenshot content with the events log: "couldn\'t train for 3 nights"', () => {
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX, events: EVENTS, nights: NIGHTS });
  const fix = m.done.find((i) => i.id === 'fix:sleep');
  assert.equal(fix.title, "Sleep couldn't train for 3 nights; retrying automatically");
  assert.equal(m.done.filter((i) => i.icon === '🔧').length, 1);
  assert.equal(m.hero.title, 'Nothing needs you today');
  const sleep = m.done.find((i) => i.id === 'sleep');   // the last finished night was undone: said plainly, with the quiz line
  assert.equal(sleep.tag.text, 'undone'); assert.ok(sleep.lines.some((l) => /no score yet/.test(l)));
});
test('an old sleep problem that a later good night fixed is not shown', () => {
  const ev = [...sleepErr('2026-10-20T01:00:00-04:00'), { ts: '2026-10-21T01:00:00-04:00', kind: 'chunk_done', steps: 100, info: {} }];
  const m = D.buildDashboard({ now: NOW, events: ev });
  assert.equal(m.done.filter((i) => i.icon === '🔧').length, 0);
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
  assert.equal(m.hero.title, 'Nothing needs you today'); assert.match(m.hero.sub, /All quiet/);
  assert.deepEqual([m.needs, m.done, m.worth], [[], [], []]);
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
  assert.equal(w.tag.text, 'read'); assert.equal(w.tag.tone, 'amber');
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
  assert.deepEqual(m.worth.map((i) => [i.title, i.tag.text, i.tag.tone]), [['FAFSA form', 'tomorrow', 'amber'], ['Chem lab report', 'in 2 days', 'amber']]);
});
test('a permission the sleep app is waiting for needs Ben', () => {
  const m = D.buildDashboard({ now: NOW, status: { needs_permission: 'Mail' } });
  assert.equal(m.hero.title, '1 thing needs you'); assert.equal(m.needs[0].icon, '🔑');
});
test('sleep result: what it learned and the quiz score against yesterday', () => {
  const nights = [{ date: '2026-11-01', status: 'done', quiz: 71, reverted: false }, { date: '2026-11-02', status: 'done', quiz: 78, reverted: false }];
  const m = D.buildDashboard({ now: NOW, nights });
  const s = m.done.find((i) => i.id === 'sleep');
  assert.equal(s.tag.text, 'learned'); assert.equal(s.tag.tone, 'green');
  assert.ok(s.lines.some((l) => l === 'Morning quiz: 78%, up from 71% last time.'), s.lines.join('|'));
  // dry runs and unfinished nights are not "learned"
  assert.equal(D.buildDashboard({ now: NOW, nights: [{ date: '2026-11-02', status: 'dry_run', dry_run: true }] }).done.length, 0);
});
test('progress and FYI cards appear only when real data exists; FYI is dimmed', () => {
  const sum = '- Quiz (held-out recall %): 63.50 -> 78.50 (5 checks)\n- First-try pass rate: 40% -> 60%\n';
  const m = D.buildDashboard({ now: NOW, summary: sum, fyi: [{ icon: '🎮', title: 'Bedwars bot project', line: 'Notes updated Nov 3.' }] });
  assert.deepEqual(m.worth.map((i) => i.tag.text), ['progress', 'progress', 'FYI']);
  assert.equal(m.worth[2].dim, true);
  assert.equal(D.buildDashboard({ now: NOW }).worth.length, 0);
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
  assert.equal(m.hero.title, 'Nothing needs you today'); assert.equal(m.counts.junk, 5);
  assert.equal(m.done.find((i) => i.id === 'fix:sleep').title, "Sleep couldn't train for 3 nights; retrying automatically");
  assert.equal(Src.getDashboard({ home: path.join(root, 'missing'), now: NOW }).hero.title, 'Nothing needs you today');   // no files: still fine, nothing invented
  let hits = 0;
  const stop = Src.watchSources({ home, debounceMs: 20, pollMs: 50 }, () => { hits++; });
  fs.appendFileSync(path.join(home, 'inbox.md'), '\n## 2026-11-03T21:00:00-05:00  Mr. Phipps <jphipps@dresdenschools.org>: Lab report due tomorrow\nurgent word: due\n');
  await new Promise((r) => setTimeout(r, 400));
  stop();
  assert.ok(hits >= 1, 'watcher saw the inbox change');
  assert.equal(Src.getDashboard({ home, now: NOW + 1000, tracked: () => [] }).hero.title, '1 thing needs you');
  fs.rmSync(root, { recursive: true, force: true });
});

// ---------------------------------------------------------------- the view: opening it, and the model drawn as cards
const walk = (v, f, out = []) => { if (typeof v === 'string') return out; if (f(v)) out.push(v); for (const k of v.kids || []) walk(k, f, out); return out; };
const textOf = (v) => (typeof v === 'string' ? v : (v.text || '') + (v.kids || []).map(textOf).join(' '));

test('the morning card has a button that opens the dashboard, and shows the same hero line', () => {
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX });
  let opened = 0;
  const card = V.morningCardView(m, { open: () => { opened++; } });
  assert.match(textOf(card), /While you slept/); assert.match(textOf(card), /Nothing needs you today/); assert.match(textOf(card), /handled 6 things/);
  assert.doesNotMatch(textOf(card), /RuntimeError|Tell Us About/);
  const [btn] = walk(card, (n) => n.t === 'button');
  assert.equal(btn.text, 'Open dashboard'); btn.on.click();
  assert.equal(opened, 1);
});
test('the dashboard shows the hero and the sections as tap-to-expand cards with coloured tags', () => {
  const m = D.buildDashboard({ now: NOW, summary: SUMMARY, inbox: INBOX, events: EVENTS, nights: NIGHTS, fyi: [{ icon: '🎮', title: 'Bedwars bot project', line: 'x' }] });
  const toggled = [];
  const st = { open: new Set(['junk']), updatedAt: NOW - 120000, now: NOW };
  const v = V.dashboardView(m, st, { toggle: (id) => toggled.push(id), refresh() {} });
  const t = textOf(v);
  assert.match(t, /Nothing needs you today/); assert.match(t, /DONE FOR YOU/); assert.match(t, /WORTH KNOWING/); assert.doesNotMatch(t, /NEEDS YOU/);
  assert.match(t, /Hid 5 junk emails/); assert.match(t, /Dunkin' Rewards: Last call/);          // junk card is open: its list is visible
  assert.match(t, /updated 2 min ago/);
  const rows = walk(v, (n) => n.t === 'button' && n.attrs && n.attrs['data-id']);
  assert.ok(rows.length >= 4);
  rows.find((r) => r.attrs['data-id'] === 'fix:sleep').on.click(); assert.deepEqual(toggled, ['fix:sleep']);
  assert.equal(rows.find((r) => r.attrs['data-id'] === 'junk').attrs['aria-expanded'], 'true');
  assert.equal(rows.find((r) => r.attrs['data-id'] === 'fix:sleep').attrs['aria-expanded'], 'false');
  assert.ok(!/RuntimeError|ValueError/.test(t), 'raw errors stay hidden until the card is opened');
  const tags = walk(v, (n) => /\bdb-tag\b/.test(n.cls)).map((n) => n.cls.split(' ')[1] + ':' + n.text);
  assert.ok(tags.includes('grey:hidden') && tags.includes('blue:retrying') && tags.includes('grey:FYI'), tags.join(','));
  // opening the retry card reveals the raw text only inside the Details part
  const v2 = V.dashboardView(m, { open: new Set(['fix:sleep']), now: NOW });
  const det = walk(v2, (n) => n.t === 'details')[0];
  assert.match(textOf(det), /Invalid IPv6 URL/);
});
test('"N things need you" shows a NEEDS YOU section', () => {
  const m = D.buildDashboard({ now: NOW, tracked: [{ what: 'Pay dues', until: '2026-11-03' }] });
  const t = textOf(V.dashboardView(m, { open: new Set(), now: NOW }));
  assert.match(t, /1 thing needs you/); assert.match(t, /NEEDS YOU/);
});
test('wiring: the main window has an Updates button and sheet, and the morning card opens the same dashboard', () => {
  const root = path.join(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'renderer/index.html'), 'utf8'), app = fs.readFileSync(path.join(root, 'renderer/app.js'), 'utf8');
  assert.match(html, /id="btnDash"/); assert.match(html, /id="dashSheet"/); assert.match(html, /<script src="dashboard.js">/);
  assert.match(app, /\$\('#btnDash'\)\.onclick = openDash/);
  assert.match(app, /morningCardView\(dash\.state\.model, \{ open: openDash \}\)/);
  assert.match(app, /desk\.onDashboardChanged\(/);
  assert.match(fs.readFileSync(path.join(root, 'preload.js'), 'utf8'), /dashboard: \{ get: inv\('dashboard:get'\) \}/);
  assert.match(fs.readFileSync(path.join(root, 'main.js'), 'utf8'), /h\('dashboard:get'/);
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
