'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Sleep, findPython, appDir, inWindow, windowKey, shouldAutoSleep, shouldAutoWake, pillLine } = require('../src/sleep');

const FAKE = path.join(__dirname, 'fake-sleepmode.js');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sleep-'));
const mk = (extra, settings) => {
  const home = tmp(); fs.mkdirSync(path.join(home, 'app'));
  return { home, sl: new Sleep({ home, getSettings: () => ({ sleepPython: FAKE, ...settings }), env: { ...extra } }) };
const withPs = (sl, fn) => { sl.o.psCommand = fn; return sl; };
};
const withPs = (sl, fn) => { sl.o.psCommand = fn; return sl; };
const until = async (f, ms = 5000) => { const t = Date.now(); while (Date.now() - t < ms) { if (await f()) return true; await new Promise((r) => setTimeout(r, 50)); } return false; };

test('app dir and python lookup: settings win, then the usual places, then python3', () => {
  assert.strictEqual(appDir({}, '/h/sleepmode'), path.join('/h/sleepmode', 'app'));
  assert.strictEqual(appDir({ sleepApp: '/x/app' }, '/h/sleepmode'), '/x/app');
  assert.strictEqual(findPython({ sleepPython: '/my/py' }, '/ops/sleepmode'), '/my/py');
  const has = (set) => (p) => set.includes(p);
  assert.strictEqual(findPython({}, '/ops/sleepmode', has(['/ops/sleepmode/venv312/bin/python', '/ops/.venv/bin/python'])), '/ops/sleepmode/venv312/bin/python');
  assert.strictEqual(findPython({}, '/ops/sleepmode', has(['/ops/.venv/bin/python', '/opt/homebrew/bin/python3'])), '/ops/.venv/bin/python');
  assert.strictEqual(findPython({}, '/ops/sleepmode', has(['/opt/homebrew/bin/python3'])), '/opt/homebrew/bin/python3');
  assert.strictEqual(findPython({}, '/ops/sleepmode', has([]), 'linux'), 'python3');
  assert.strictEqual(findPython({}, '/ops/sleepmode', has([]), 'darwin'), '');   // never bare python3 on a Mac
  assert.strictEqual(findPython({ sleepPython: '~/py' }, '/ops/sleepmode', has([]), 'darwin'), require('os').homedir() + '/py');
});

test('available(): says plainly when the app folder is missing', () => {
  const home = tmp();
  const sl = new Sleep({ home, getSettings: () => ({}) });
  const a = sl.available();
  assert.strictEqual(a.ok, false); assert.match(a.reason, /not found/);
  fs.mkdirSync(path.join(home, 'app'));
  assert.strictEqual(sl.available().ok, true);
});

test('status(): reads status.json, needs the marker and a live pid (stale markers do not count)', () => {
  const { home, sl } = mk();
  assert.strictEqual(sl.status().sleeping, false);
  fs.writeFileSync(path.join(home, 'status.json'), JSON.stringify({ mode: 'sleep', since: new Date(Date.now() - 9e6).toISOString(), hours_slept: 2.5, last_quiz: 78, last_checkin: '2026-10-26T03:00:00Z', pid: process.pid }));
  fs.writeFileSync(path.join(home, 'SLEEPING'), process.pid + '\n');
  withPs(sl, () => 'python -m sleepmode start --foreground');
  const st = sl.status();
  assert.ok(st.sleeping); assert.strictEqual(st.hours, 2.5); assert.strictEqual(st.lastQuiz, 78); assert.strictEqual(st.mode, 'sleep'); assert.ok(st.lastCheckin > 0); assert.strictEqual(st.demo, false);
  assert.strictEqual(pillLine(st), 'Sleeping · 2.5 h · quiz 78');
  fs.writeFileSync(path.join(home, 'SLEEPING'), '999999\n'); // dead pid
  assert.strictEqual(sl.status().sleeping, false);
  fs.unlinkSync(path.join(home, 'SLEEPING'));
  assert.strictEqual(sl.status().sleeping, false);
});

test('demo runs are labelled: status.json or events say fake, and the pill/status line say demo instead of numbers', () => {
  const { home, sl } = mk();
  fs.writeFileSync(path.join(home, 'status.json'), JSON.stringify({ mode: 'sleep', hours_slept: 3, last_quiz: 70, fake: true, since: '2026-10-25T22:00:00Z', updated: '2026-10-26T01:00:00Z' }));
  const st = sl.status();
  assert.ok(st.demo); assert.strictEqual(pillLine(st), 'Sleeping · 3 h · demo');
  assert.match(sl.statusLine(), /demo run/); assert.ok(!/quiz|→/.test(sl.statusLine()));
  const b = mk();
  fs.writeFileSync(path.join(b.home, 'status.json'), JSON.stringify({ hours_slept: 3, since: '2026-10-25T22:00:00Z', updated: '2026-10-26T01:00:00Z', last_checkin: '2026-10-26T00:30:00Z' }));
  assert.ok(!b.sl.status().demo);
  b.sl.mark();
  fs.writeFileSync(path.join(b.home, 'events.jsonl'), JSON.stringify({ kind: 'chunk_done', info: { fake: true } }) + '\n');
  assert.ok(!b.sl.status().demo);        // status() never reads the events file
  b.sl.poll();                            // the tail reader notices the flag
  assert.ok(b.sl.status().demo);
  const c = mk();
  fs.writeFileSync(path.join(c.home, 'status.json'), JSON.stringify({ hours_slept: 3, since: '2026-10-25T22:00:00Z', updated: '2026-10-26T01:00:00Z', last_checkin: '2026-10-26T00:30:00Z' }));
  assert.match(c.sl.statusLine(), /3 h slept · last check-in/);
});

test('poll(): new events only (offset saved), partial lines wait, truncation restarts, inbox lines are new-only', () => {
  const { home, sl } = mk();
  const ef = path.join(home, 'events.jsonl'), ib = path.join(home, 'inbox.md');
  fs.writeFileSync(ef, JSON.stringify({ kind: 'old' }) + '\n'); fs.writeFileSync(ib, '- old alert\n');
  sl.mark();
  assert.deepStrictEqual(sl.poll(), []);
  fs.appendFileSync(ef, JSON.stringify({ kind: 'chunk_done', quiz: 1 }) + '\n' + '{"kind":"chec');
  assert.deepStrictEqual(sl.poll().map((e) => e.kind), ['chunk_done']);
  fs.appendFileSync(ef, 'kin","notified":2}\n');
  fs.writeFileSync(ib, '- Mail: urgent from Mr. Phipps\n- old alert\n');
  const got = sl.poll();
  assert.deepStrictEqual(got.map((e) => e.kind), ['checkin', 'inbox']); assert.strictEqual(got[0].notified, 2); assert.strictEqual(got[1].line, 'Mail: urgent from Mr. Phipps');
  assert.deepStrictEqual(sl.poll(), []);
  fs.writeFileSync(ef, JSON.stringify({ kind: 'wake' }) + '\n'); // file replaced by a shorter one
  assert.deepStrictEqual(sl.poll().map((e) => e.kind), ['wake']);
});

test('start / status / wake / readSummary against a fake sleepmode (PYTHONPATH + SLEEPMODE_HOME passed)', async () => {
  const { home, sl } = mk({ FAKE_SLEEP_HOURS: '2.5' });
  const r = sl.start();
  assert.ok(r.ok, r.error);
  assert.ok(await until(() => sl.status().sleeping), 'sleeping after start');
  assert.strictEqual(sl.status().mode, 'sleep');
  assert.ok(fs.existsSync(path.join(home, 'desk-sleep.log')));
  assert.strictEqual(sl.start().ok, false); // already sleeping
  assert.strictEqual(sl.readSummary(), '');
  const w = await sl.wake(10000);
  assert.ok(w.ok); assert.strictEqual(w.via, 'cli');
  assert.ok(await until(() => !sl.status().sleeping));
  assert.match(sl.readSummary(), /While you slept/);
});

test('wake falls back to touching WAKE when the command cannot run', async () => {
  const home = tmp(); fs.mkdirSync(path.join(home, 'app'));
  const sl = new Sleep({ home, getSettings: () => ({ sleepPython: '/no/such/python' }) });
  const w = await sl.wake(3000);
  assert.ok(w.ok); assert.strictEqual(w.via, 'file'); assert.ok(fs.existsSync(path.join(home, 'WAKE')));
  const none = new Sleep({ home: tmp(), getSettings: () => ({}) }); // no app dir at all: still leaves the WAKE file
  assert.strictEqual((await none.wake(1000)).via, 'file');
});

test('start fails plainly when the app is missing', () => {
  const sl = new Sleep({ home: tmp(), getSettings: () => ({}) });
  const r = sl.start(); assert.strictEqual(r.ok, false); assert.match(r.error, /not found/);
});

const at = (h, m, d) => new Date(2026, 9, d || 26, h, m);
const S = { autoSleep: true, sleepFrom: '23:00', sleepTo: '07:00', sleepIdleMin: 30, wakeAt: false };
const base = { settings: S, now: at(23, 40), idleMs: 31 * 60000, runActive: false, gatewayBusy: false, windowFocused: false, asleep: false, available: true };

test('night window: crosses midnight, same-day windows, equal ends mean never', () => {
  assert.ok(inWindow(at(23, 0), '23:00', '07:00')); assert.ok(inWindow(at(2, 0), '23:00', '07:00')); assert.ok(!inWindow(at(7, 0), '23:00', '07:00')); assert.ok(!inWindow(at(12, 0), '23:00', '07:00'));
  assert.ok(inWindow(at(13, 0), '12:00', '14:00')); assert.ok(!inWindow(at(14, 0), '12:00', '14:00'));
  assert.ok(!inWindow(at(3, 0), '03:00', '03:00')); assert.ok(inWindow(at(23, 30), 'junk', '07:00')); // bad text falls back to the defaults
  assert.strictEqual(windowKey(at(23, 40, 26), '23:00', '07:00'), '2026-10-26');
  assert.strictEqual(windowKey(at(2, 0, 27), '23:00', '07:00'), '2026-10-26'); // after midnight: still the same night
});

test('auto-sleep decision: only when enabled, at night, idle long enough, nothing running, gateway idle, Desk not in front', () => {
  const d = (o) => shouldAutoSleep({ ...base, ...o });
  const yes = d({}); assert.ok(yes.sleep); assert.strictEqual(yes.key, '2026-10-26');
  assert.ok(!d({ settings: { ...S, autoSleep: false } }).sleep);
  assert.ok(!d({ now: at(15, 0) }).sleep);
  assert.ok(!d({ idleMs: 10 * 60000 }).sleep);
  assert.ok(!d({ runActive: true }).sleep); assert.ok(!d({ gatewayBusy: true }).sleep); assert.ok(!d({ windowFocused: true }).sleep);
  assert.ok(!d({ asleep: true }).sleep); assert.ok(!d({ available: false }).sleep);
  assert.ok(!d({ lastKey: '2026-10-26' }).sleep); // Ben woke it tonight: not again
  assert.ok(d({ lastKey: '2026-10-25' }).sleep);
  assert.ok(!d({ settings: { ...S, sleepIdleMin: 60 } }).sleep);
  assert.ok(d({ settings: { ...S, sleepIdleMin: 5 }, idleMs: 6 * 60000 }).sleep);
});

test('auto-wake: only if wakeAt is on, the sleep was started automatically and the window is over', () => {
  const w = (o) => shouldAutoWake({ settings: { ...S, wakeAt: true }, now: at(7, 5), asleep: true, startedAuto: true, ...o }).wake;
  assert.ok(w({})); assert.ok(!w({ now: at(3, 0) })); assert.ok(!w({ startedAuto: false })); assert.ok(!w({ asleep: false }));
  assert.ok(!shouldAutoWake({ settings: S, now: at(7, 5), asleep: true, startedAuto: true }).wake);
});

test('missing Python on a Mac is reported (Sleep disabled, "Set the Sleep Python path")', () => {
  const home = tmp(); fs.mkdirSync(path.join(home, 'app'));
  const sl = new Sleep({ home, getSettings: () => ({}), platform: 'darwin', pythonExists: () => false });
  const a = sl.available(); assert.strictEqual(a.ok, false); assert.match(a.reason, /Set the Sleep Python path/);
  assert.strictEqual(sl.start().ok, false);
});

test('SLEEPMODE_HOME expands ~', () => {
  const { homeDir } = require('../src/sleep');
  assert.strictEqual(homeDir({ SLEEPMODE_HOME: '~/x/sm' }), path.join(os.homedir(), 'x', 'sm'));
});

test('status(): a timestamp in SLEEPING is not a pid; a live pid that is not sleepmode does not count; ps runs once per pid', () => {
  const { home, sl } = mk();
  let calls = 0;
  withPs(sl, () => { calls++; return '/usr/bin/some-other-program --x'; });
  fs.writeFileSync(path.join(home, 'SLEEPING'), '2026-10-26T03:00:00Z\n');
  assert.strictEqual(sl.status().sleeping, false); assert.strictEqual(calls, 0);   // not numeric: no pid, no ps call
  fs.writeFileSync(path.join(home, 'SLEEPING'), '12345abc\n');
  assert.strictEqual(sl.status().sleeping, false);
  fs.writeFileSync(path.join(home, 'SLEEPING'), process.pid + '\n');
  assert.strictEqual(sl.status().sleeping, false);                                   // alive, but not sleepmode
  for (let i = 0; i < 5; i++) sl.status();
  assert.strictEqual(calls, 1);                                                      // cached per pid
  sl.psCache.clear(); sl.o.psCommand = () => 'python -m sleepmode start';
  assert.strictEqual(sl.status().sleeping, true);
});

test('status(): the 5 s poll does not read events.jsonl or an unchanged inbox', () => {
  const { home, sl } = mk();
  const ef = path.join(home, 'events.jsonl'), ib = path.join(home, 'inbox.md');
  fs.writeFileSync(ef, 'x'.repeat(5e6)); fs.writeFileSync(ib, '- a\n');
  sl.mark();
  const real = fs.readFileSync; const read = [];
  fs.readFileSync = function (f, ...r) { read.push(String(f)); return real.call(fs, f, ...r); };
  try { for (let i = 0; i < 3; i++) { sl.status(); sl.poll(); } } finally { fs.readFileSync = real; }
  assert.ok(!read.some((f) => f.endsWith('events.jsonl') || f.endsWith('inbox.md')), read.join(','));
});

test('wakeKey: waking at 08:00 or auto-waking at 07:00 never blocks tonight', () => {
  const { wakeKey } = require('../src/sleep');
  const st = { ...S, wakeAt: true };
  // auto-slept at 23:40 on the 26th (key 2026-10-26); woke at 08:00 on the 27th
  const k1 = wakeKey({ sleepKey: '2026-10-26', now: at(8, 0, 27), settings: st });
  assert.strictEqual(k1, '2026-10-26');
  assert.ok(shouldAutoSleep({ ...base, now: at(23, 40, 27), lastKey: k1 }).sleep);        // tonight (the 27th) still sleeps
  const k2 = wakeKey({ sleepKey: '2026-10-26', now: at(7, 0, 27), settings: st });        // auto-wake at 07:00
  assert.ok(shouldAutoSleep({ ...base, now: at(23, 40, 27), lastKey: k2 }).sleep);
  // a daytime sleep (no key) woken at 08:00 or 15:00 records nothing
  assert.strictEqual(wakeKey({ sleepKey: null, now: at(8, 0), settings: st }), null);
  assert.strictEqual(wakeKey({ sleepKey: null, now: at(15, 0), settings: st }), null);
  // woken by hand at 02:00 inside the window: that night is done
  assert.strictEqual(wakeKey({ sleepKey: null, now: at(2, 0, 27), settings: st }), '2026-10-26');
  assert.ok(!shouldAutoSleep({ ...base, now: at(2, 30, 27), lastKey: '2026-10-26' }).sleep);
});

test('auto-sleep idle uses the Mac idle time too: working in another app is not idle', () => {
  const d = (o) => shouldAutoSleep({ ...base, ...o });
  assert.ok(!d({ idleMs: 40 * 60000, systemIdleMs: 2 * 60000 }).sleep);      // Desk untouched for 40 min, but Ben used the Mac 2 min ago
  assert.ok(d({ idleMs: 40 * 60000, systemIdleMs: 35 * 60000 }).sleep);
  assert.ok(!d({ idleMs: 5 * 60000, systemIdleMs: 90 * 60000 }).sleep);      // the smaller of the two decides
  assert.ok(d({ idleMs: 40 * 60000 }).sleep);                                // no system reading: Desk idle alone
});

test('assistant marker: start refuses in plain words while the chat model runs, and clears a marker left by a crash', () => {
  const ops = tmp(), home = path.join(ops, 'sleepmode'), marker = path.join(ops, 'ASSISTANT_RUNNING'); // its own ops dir, not the shared tmp
  fs.mkdirSync(path.join(home, 'app'), { recursive: true });
  const sl = new Sleep({ home, getSettings: () => ({ sleepPython: FAKE }) });
  assert.strictEqual(sl.p.assistant, marker);
  assert.strictEqual(sl.assistantState(), 'off');
  fs.writeFileSync(marker, 'started: now\nbig pid: ' + process.pid + '\ngateway pid: 999999\n');
  assert.strictEqual(sl.assistantState(), 'on');
  const r = sl.start({});
  assert.strictEqual(r.ok, false); assert.ok(r.assistantOn); assert.match(r.error, /using the memory sleep needs/);
  fs.writeFileSync(marker, 'big pid: 999998\ngateway pid: 999999\n');
  assert.strictEqual(sl.assistantState(), 'stale');
  sl.spawn = () => ({ pid: 1, on() {}, unref() {} });
  assert.ok(sl.start({}).ok);
  assert.strictEqual(fs.existsSync(marker), false);
  fs.writeFileSync(path.join(home, 'desk-sleep.log'), 'x\nThe assistant is running (y exists); sleeping would stop at once.\n\n');
  assert.match(sl.lastLogLine(), /assistant is running/);
});

test("poll(): check-in entries read 'Sender: Subject' (no time stamp, address or 'model triage' line)", () => {
  const { home, sl } = mk();
  const ib = path.join(home, 'inbox.md');
  fs.writeFileSync(ib, '## 2026-10-28T14:00:00-04:00  Old <a@b.c>: seen before\nmodel triage\n\n');
  sl.mark();
  fs.writeFileSync(ib, '## 2026-10-28T15:07:02-04:00  Facebook <reminders@facebookmail.com>: You have 35 notifications about Parker and others\nmodel triage\n\n'
    + '## 2026-10-28T15:07:01-04:00  IFTTT <mail_at_ifttt_com_gkdx8smyzq_c11f: We\'re IFTTT.ai\nmodel triage\n\n'
    + '## 2026-10-28T15:07:00-04:00  Event soon: Piano\n18:30 (starts within 2 h)\n\n'
    + '## 2026-10-28T14:00:00-04:00  Old <a@b.c>: seen before\nmodel triage\n\n');
  assert.deepStrictEqual(sl.poll().map((e) => e.line), ['Facebook: You have 35 notifications about Parker and others', "IFTTT: We're IFTTT.ai", 'Event soon: Piano, 18:30']);
  assert.deepStrictEqual(sl.poll(), []);
});

test('sleepNow: tells what Glim is doing in its sleep, from the trainer log and events', () => {
  const { sleepNow } = require('../src/sleep');
  const since = new Date(2026, 9, 28, 15, 6, 31).getTime();
  const log = [
    '2026-10-28 02:07:41 [night 1] day 2026-10-27 scale 0.40',   // an older sleep: ignored
    '2026-10-28 15:07:10 [night 1] day 2026-10-28 scale 0.43',
    "2026-10-28 15:07:15 [night] tagging {'tag_empty': 4, 'kept': 3, 'extracted': 5}",
    "2026-10-28 15:07:20 [night] dream {'backlog': 0, 'items': 6, 'held_out': 1}",
    '2026-10-28 15:07:30 [night] step 4/19 ce 2.2 8.6s',
    '2026-10-28 15:07:40 [night] step 8/19 ce 2.0 8.6s',
    'not a log line'
  ].join('\n');
  const ev = [{ ts: '2026-10-28T15:07:02', kind: 'checkin', counts: { mail: 8, calendar: 0 } }];
  let r = sleepNow({ log, events: ev, since });
  assert.equal(r.now, "Learning from today's chats (step 8 of 19)");
  assert.deepEqual(r.recent.map((x) => x.line), ['Checked your mail (8 emails)', "Reading today's chats", "Picked out 3 facts from today's chats", 'Made 6 practice cards', "Learning from today's chats (step 8 of 19)"]);
  r = sleepNow({ log: log + '\n2026-10-28 15:07:50 [night] step 19/19 ce 1.9 8s', events: ev, since });
  assert.equal(r.now, 'Checking what it learned (quiz)');
  ev.push({ ts: '2026-10-28T15:07:54', kind: 'chunk_done', info: { status: 'done', reverted: true, revert_reason: ['no held-out cards to check what was learned'] } });
  assert.equal(sleepNow({ log, events: ev, since }).now, 'Done for tonight: kept nothing (no quiz cards to check it with)');
  assert.equal(sleepNow({ log: '', events: [], since }).now, 'Learning from your chats');
  assert.equal(sleepNow({ log, events: [], since: null }).now, 'Learning from your chats');   // no start time: last night's lines are not shown
  const late = [{ ts: '2026-10-28T15:08:00', kind: 'checkin', counts: { mail: 2 } }];
  assert.equal(sleepNow({ log, events: late, since, nowMs: Date.parse('2026-10-28T15:08:30') }).now, 'Checked your mail (2 emails)');
  assert.equal(sleepNow({ log, events: late, since, nowMs: Date.parse('2026-10-28T15:20:00') }).now, "Learning from today's chats (step 8 of 19)");
  assert.equal(sleepNow({ log: '', events: [{ ts: '2026-10-28T15:08:00', kind: 'chunk_done', info: { error: 'RuntimeError: MPS backend out of memory' } }], since }).now, 'Stopped: ran out of memory');
  assert.equal(sleepNow({ log: '', events: [{ ts: '2026-10-28T15:08:00', kind: 'chunk_done', steps: 100 }], since }).now, 'Learning from your chats');
});

test('Sleep.liveNow reads the real files next to the sleep home', () => {
  const { Sleep } = require('../src/sleep');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'live-'));
  const home = path.join(root, 'sleepmode'); fs.mkdirSync(home); fs.mkdirSync(path.join(root, 'sleepmlx'));
  fs.writeFileSync(path.join(root, 'sleepmlx', 'sleepmlx.log'), '2026-10-28 15:07:30 [night] step 4/19 ce 2.2 8.6s\n');
  fs.writeFileSync(path.join(home, 'events.jsonl'), '{"ts":"2026-10-28T15:07:02","kind":"checkin","counts":{"mail":1}}\n');
  const s = new Sleep({ home });
  const r = s.liveNow({ since: new Date(2026, 9, 28, 15, 6, 0).getTime() });
  assert.equal(r.now, "Learning from today's chats (step 4 of 19)");
  assert.equal(r.recent[0].line, 'Checked your mail (1 email)');
});
