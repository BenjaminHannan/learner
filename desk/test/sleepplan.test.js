'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path');
const S = require('../src/sleep');
const CK = require('../src/checkin');
const { WinSleep, workerEnv, CHUNK_BUDGET_S } = require('../src/sleepwin');

const at = (h, m, d) => new Date(2026, 9, d || 28, h, m, 0);

test('wakeAt: minutes, morning (same day and across midnight), open', () => {
  const st = { sleepTo: '06:00' };
  assert.strictEqual(S.computeWakeAt(at(22, 0), 90, st), at(22, 0).getTime() + 90 * 60000);
  assert.strictEqual(S.computeWakeAt(at(23, 30), 'morning', st), at(6, 0, 29).getTime()); // crosses midnight
  assert.strictEqual(S.computeWakeAt(at(2, 0), 'morning', st), at(6, 0, 28).getTime());   // before it today
  assert.strictEqual(S.computeWakeAt(at(6, 0), 'morning', st), at(6, 0, 29).getTime());   // exactly at it: next one
  assert.strictEqual(S.computeWakeAt(at(1, 0), null, st), null);
  assert.strictEqual(S.computeWakeAt(at(1, 0), 'morning', {}), at(7, 0, 28).getTime());
  assert.strictEqual(S.durationFromSetting('120'), 120); assert.strictEqual(S.durationFromSetting('open'), null); assert.strictEqual(S.durationFromSetting('zzz'), 'morning');
});
test('night budget: 85% of the sleep, 8 h when open, never under 5 minutes', () => {
  const t0 = 1e9;
  assert.strictEqual(S.nightBudgetS(t0, t0 + 3600e3), 3060);
  assert.strictEqual(S.nightBudgetS(t0, null), Math.floor(8 * 3600 * 0.85));
  assert.strictEqual(S.nightBudgetS(t0, t0 + 60e3), 300);
});
test('workerEnv carries SLEEPMLX_NIGHT_BUDGET_S; Mac _env does too', () => {
  const o = { outFile: 'o', home: 'h', diaryDir: 'd', sleepmlxParent: 'p', hfHome: 'x', nightBudgetS: 3060.4 };
  assert.strictEqual(workerEnv(o).SLEEPMLX_NIGHT_BUDGET_S, '3060');
  assert.ok(!('SLEEPMLX_NIGHT_BUDGET_S' in workerEnv({ ...o, nightBudgetS: 0 })));
  assert.ok(CHUNK_BUDGET_S <= 900);
  const m = new S.Sleep({ home: os.tmpdir() }); m.nightBudgetS = 1234;
  assert.strictEqual(m._env().SLEEPMLX_NIGHT_BUDGET_S, '1234');
});
test('wake label and the 60 s tick', () => {
  const now = at(2, 28).getTime();
  assert.strictEqual(S.wakeLabel(at(3, 40).getTime(), now), 'wakes at 3:40 (1 h 12 m left)');
  assert.strictEqual(S.wakeLabel(null, now), 'until you wake it');
  assert.strictEqual(S.wakeLabel(at(2, 40).getTime(), now), 'wakes at 2:40 (12 m left)');
  const base = { asleep: true, waking: false, wakeAt: 1000 };
  assert.strictEqual(S.shouldTimedWake({ ...base, nowMs: 999 }), false);
  assert.strictEqual(S.shouldTimedWake({ ...base, nowMs: 1000 }), true);
  assert.strictEqual(S.shouldTimedWake({ ...base, nowMs: 5000, waking: true }), false);
  assert.strictEqual(S.shouldTimedWake({ ...base, wakeAt: null, nowMs: 5000 }), false);
});
test('check-in schedule', () => {
  const b = { enabled: true, now: 7200e3, sleepStart: 0, lastAt: null, periodMin: 60, wakeReq: false, onBattery: false, onlyPlugged: true };
  assert.strictEqual(CK.checkinDue({ ...b, now: 3599e3 }).due, false);
  assert.strictEqual(CK.checkinDue({ ...b, now: 3600e3 }).due, true);
  assert.strictEqual(CK.checkinDue({ ...b, lastAt: 6000e3 }).due, false);   // counted from the last check-in
  assert.strictEqual(CK.checkinDue({ ...b, enabled: false }).due, false);
  assert.strictEqual(CK.checkinDue({ ...b, wakeReq: true }).due, false);
  assert.strictEqual(CK.checkinDue({ ...b, onBattery: true }).due, false);
  assert.strictEqual(CK.checkinDue({ ...b, onBattery: true, onlyPlugged: false }).due, true);
});
test('check-in model: the gate-passed adapter or plain, never the work adapter', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'ck-'));
  fs.mkdirSync(path.join(home, 'work', 'adapter'), { recursive: true });
  assert.strictEqual(CK.checkinAdapter(home, fs.existsSync), '');
  fs.writeFileSync(path.join(home, 'adapter.gguf'), 'x');
  assert.strictEqual(CK.checkinAdapter(home, fs.existsSync), path.join(home, 'adapter.gguf'));
});
test('NOTHING parsing and the task text', () => {
  for (const t of ['NOTHING', 'nothing.', ' "Nothing" ', '**NOTHING**', '', null]) assert.strictEqual(CK.parseReply(t).nothing, true, String(t));
  const r = CK.parseReply('Mail from the dean says your deadline is today. Also something else.');
  assert.strictEqual(r.nothing, false); assert.strictEqual(r.line, 'Mail from the dean says your deadline is today.');
  assert.strictEqual(CK.parseReply('Nothing is wrong except the oven is on').nothing, false);
  const task = CK.checkinTask({ sleepCheckinTask: '' });
  assert.ok(task.startsWith(CK.DEFAULT_TASK) && /Read only/.test(task) && /payment failed/.test(task) && /within 2 hours/.test(task));
  assert.ok(CK.checkinTask({ sleepCheckinTask: 'Check mail.' }).startsWith('Check mail.'));
});
test('triage port of sleepmode/checkin.py', () => {
  const r = CK.triage([
    { source: 'mail', sender: 'Dean <d@x.edu>', subject: 'Final notice about your account' },
    { source: 'mail', sender: 'news', subject: 'Weekly digest' },
    { source: 'mail', sender: 'news', subject: 'overdueness is not a word hit' },
    { source: 'calendar', subject: 'Dentist', startsInMin: 90 },
    { source: 'calendar', subject: 'Later', startsInMin: 300 },
    { source: 'mail', sender: 'Mom', subject: 'hi' }
  ], { vipSenders: ['mom'] });
  assert.deepStrictEqual(r.map((x) => x.reason), ['urgent word: final notice', 'event starts in 90 min', 'VIP sender']);
});

function fakeSleep(over) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ws-'));
  const calls = []; let settings = { sleepPauseGlims: true, sleepCheckinMins: 60, sleepOnlyPlugged: false };
  const w = new WinSleep({
    getSettings: () => settings, root, installer: { installed: () => true, state: () => ({}), dir: root, pythonExe: () => 'py', plan: () => ({}) },
    sleepmlxParent: root, retryMs: 0,
    hooks: {
      pauseModel: async () => { calls.push('pause'); }, resumeModel: async (l) => { calls.push('resume:' + path.basename(l || '') ); return { ok: true }; },
      checkin: async () => { calls.push('checkin'); return { reply: 'NOTHING' }; }, onCheckin: (l) => calls.push('alert:' + l)
    }, ...(over || {})
  });
  return { w, calls, root, set: (s) => { settings = { ...settings, ...s }; } };
}
test('WinSleep check-in: up with the old adapter, task, down; alert only when not NOTHING; never twice for one line', async () => {
  const { w, calls, root } = fakeSleep();
  fs.mkdirSync(w.home, { recursive: true }); fs.writeFileSync(path.join(w.home, 'adapter.gguf'), 'x');
  w.since = Date.now() - 3700e3; w.wakeReq = false;
  await w._maybeCheckin();
  assert.deepStrictEqual(calls, ['resume:adapter.gguf', 'checkin', 'pause']);
  const ev = fs.readFileSync(w.p.events, 'utf8'); assert.ok(/checkin_start/.test(ev) && /"kind":"checkin"/.test(ev));
  calls.length = 0; await w._maybeCheckin(); assert.deepStrictEqual(calls, [], 'not due again right away');
  w.hooks.checkin = async () => ({ reply: 'Your exam deadline is today.' });
  w.lastCheckinAt = Date.now() - 3700e3; await w._maybeCheckin();
  assert.ok(calls.includes('alert:Your exam deadline is today.'));
  calls.length = 0; w.lastCheckinAt = Date.now() - 3700e3; await w._maybeCheckin();
  assert.ok(!calls.some((c) => c.startsWith('alert')), 'same line is not announced twice');
  assert.deepStrictEqual(w.checkins, ['Your exam deadline is today.']);
});
test('WinSleep check-in: plain model when there is no adapter; a failing task still stops the server; wake aborts it', async () => {
  const { w, calls } = fakeSleep();
  w.since = Date.now() - 3700e3;
  w.hooks.checkin = async () => { throw new Error('boom'); };
  await w._maybeCheckin();
  assert.deepStrictEqual(calls, ['resume:', 'pause']);
  w.lastCheckinAt = Date.now() - 3700e3; calls.length = 0;
  w.hooks.checkin = ({ signal }) => new Promise((res) => signal.addEventListener('abort', () => res({ aborted: true }), { once: true }));
  const p = w._maybeCheckin(); await new Promise((r) => setTimeout(r, 20)); await w.wake(); await p;
  assert.strictEqual(calls[calls.length - 1], 'pause');
});
test('WinSleep: wake and the early finish note', () => {
  const { w } = fakeSleep();
  w.since = Date.now() - 3600e3; w.wakeAtMs = Date.now() + 3 * 3600e3; w.finishedNight = true; w.lastQuiz = 80;
  w._writeSummary();
  assert.ok(/Finished early: it practiced everything new\./.test(fs.readFileSync(w.p.summary, 'utf8')));
});
