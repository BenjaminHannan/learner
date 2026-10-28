'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Helpers, Limiter, ScreenLock, createRunner, parseSchedule, nextRun, addNotice, takeNotices, helperText } = require('../src/helpers');
const { agentTools, NO } = require('../src/tools/agents');
const { Agent } = require('../src/agent');
const { Store } = require('../src/store');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'desk-helpers-'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const until = async (fn, ms) => { const end = Date.now() + (ms || 3000); while (Date.now() < end) { if (await fn()) return true; await sleep(10); } return false; };

// A manager with a fake runner: each run waits on a gate the test opens.
function mkManager(extra) {
  const dir = tmp();
  const store = new Store(dir);
  const runs = [];
  const clock = { t: new Date(2026, 9, 27, 10, 0).getTime() };
  const finished = [];
  const m = new Helpers({
    file: path.join(dir, 'helpers.json'), store, now: () => clock.t,
    runner: (h, text, hooks) => new Promise((resolve) => { runs.push({ h, text, hooks, done: (r) => resolve(r || { report: 'ok ' + h.name }) }); }),
    onFinish: (h, summary, parent) => finished.push({ name: h.name, summary, parent }),
    ...(extra || {})
  });
  return { m, store, runs, clock, finished, dir };
}

test('schedule parsing: every / at / once, with clear errors', () => {
  assert.deepStrictEqual(parseSchedule({}), { kind: 'once', label: 'once' });
  assert.deepStrictEqual(parseSchedule({ every: '30m' }), { kind: 'every', ms: 1800000, label: 'every 30m' });
  assert.strictEqual(parseSchedule({ every: '2h' }).label, 'every 2h');
  assert.strictEqual(parseSchedule({ every: '1d' }).ms, 86400000);
  assert.strictEqual(parseSchedule({ every: '1.5h' }).label, 'every 90m');
  assert.deepStrictEqual(parseSchedule({ at: '8:05' }), { kind: 'at', h: 8, m: 5, label: 'daily 08:05' });
  assert.throws(() => parseSchedule({ every: 'soon' }), /every must look like/);
  assert.throws(() => parseSchedule({ every: '1m' }), /at least 5m/);
  assert.throws(() => parseSchedule({ at: '25:00' }), /at must look like/);
  assert.throws(() => parseSchedule({ at: '08:60' }), /at must look like/);
  // lenient: both given -> `at` wins (daily)
  const daily = { kind: 'at', h: 8, m: 0, label: 'daily 08:00' };
  assert.deepStrictEqual(parseSchedule({ every: '1d', at: '08:00' }), daily);
  assert.deepStrictEqual(parseSchedule({ every: '24h', at: '08:00' }), daily);
  assert.deepStrictEqual(parseSchedule({ every: '1h', at: '08:00' }), daily);
});

test('next run: every adds the interval; at picks the next local clock time, also across a day', () => {
  const t = new Date(2026, 9, 27, 10, 0).getTime();
  assert.strictEqual(nextRun(parseSchedule({ every: '2h' }), t), t + 7200000);
  assert.strictEqual(nextRun({ kind: 'once' }, t), null);
  const at = parseSchedule({ at: '08:00' });
  assert.strictEqual(new Date(nextRun(at, t)).getDate(), 28);            // 08:00 already passed today
  assert.strictEqual(new Date(nextRun(at, t)).getHours(), 8);
  const early = new Date(2026, 9, 27, 6, 30).getTime();
  assert.strictEqual(nextRun(at, early), new Date(2026, 9, 27, 8, 0).getTime());
  assert.ok(nextRun(at, new Date(2026, 9, 27, 8, 0).getTime()) > new Date(2026, 9, 27, 8, 0).getTime()); // strictly after
  // month end, and a DST-ish date: the clock time stays 08:00 whatever the elapsed hours
  for (const d of [new Date(2026, 9, 31, 12, 0), new Date(2026, 10, 1, 12, 0), new Date(2026, 2, 7, 12, 0), new Date(2026, 2, 8, 12, 0)]) {
    const n = new Date(nextRun(at, d.getTime()));
    assert.strictEqual(n.getHours(), 8); assert.strictEqual(n.getMinutes(), 0);
    assert.ok(n.getTime() > d.getTime() && n.getTime() - d.getTime() < 26 * 3600000);
  }
});

test('missed-run rule: after the app was closed past a due time, run once on startup, not once per missed slot', async () => {
  const { m, runs, clock, dir, store } = mkManager();
  const h = m.add({ name: 'news', task: 'headlines', every: '30m' });
  assert.strictEqual(runs.length, 1);                 // recurring helpers run once right away
  runs[0].done(); await until(() => m.find('news').status === 'idle');
  const first = m.find('news').next;
  assert.strictEqual(first, clock.t + 1800000);
  // "close the app" for 5 hours (10 missed slots), then start again from the file
  clock.t += 5 * 3600000;
  const m2 = new Helpers({ file: path.join(dir, 'helpers.json'), store, now: () => clock.t, runner: (hh, text, hooks) => new Promise((resolve) => { runs.push({ h: hh, hooks, done: () => resolve({ report: 'r' }) }); }) });
  runs.length = 0;
  m2.tick(); m2.tick(); m2.tick();
  assert.strictEqual(runs.length, 1, 'exactly one catch-up run');
  assert.strictEqual(m2.find('news').next, clock.t + 1800000, 'next slot counted from now');
  runs[0].done();
  // a daily helper missed for 3 days: one run, next is tomorrow 08:00
  const d = m2.add({ name: 'daily', task: 't', at: '08:00' });
  runs.length = 0;
  clock.t += 3 * 86400000;
  m2.tick(); m2.tick();
  assert.strictEqual(runs.length, 1);
  assert.ok(m2.find('daily').next > clock.t && m2.find('daily').next - clock.t <= 86400000);
  assert.strictEqual(d.schedule, 'daily 08:00');
});

test('tick skips paused and stopped helpers, and ones that are still running', async () => {
  const { m, runs, clock } = mkManager();
  m.add({ name: 'a', task: 't', at: '12:00' });
  m.add({ name: 'b', task: 't', at: '12:00' });
  clock.t = new Date(2026, 9, 27, 12, 1).getTime();
  m.pause('b', true);
  m.tick();
  assert.deepStrictEqual(runs.map((r) => r.h.name), ['a']);
  m.tick();                                           // 'a' still running: no second run
  assert.strictEqual(runs.length, 1);
  m.pause('b', false);                                // resume with a due time: waits for the next slot, no burst
  assert.ok(m.find('b').next > clock.t);
});

test('concurrency limit: extra runs queue FIFO, a slot frees when a run ends, abort leaves the queue', async () => {
  assert.strictEqual(new Limiter(() => 0).max(), Infinity); assert.strictEqual(new Limiter(() => 0).full(), false); // 0 = unlimited
  const lim = new Limiter(() => 2);
  const r1 = await lim.acquire(), r2 = await lim.acquire();
  assert.strictEqual(lim.full(), true);
  const order = [];
  const p3 = lim.acquire().then((r) => { order.push(3); return r; });
  const p4 = lim.acquire().then((r) => { order.push(4); return r; });
  const ctl = new AbortController();
  const p5 = lim.acquire(ctl.signal).then(() => order.push(5), (e) => order.push('abort:' + e.message));
  await sleep(10);
  assert.deepStrictEqual(order, []);
  ctl.abort(); await sleep(5);
  assert.deepStrictEqual(order, ['abort:aborted']);
  r1(); r1();                                         // double release is harmless
  await sleep(10);
  assert.deepStrictEqual(order, ['abort:aborted', 3]);
  assert.strictEqual(lim.active, 2);
  r2(); await sleep(10);
  assert.deepStrictEqual(order, ['abort:aborted', 3, 4]);
  (await p3)(); (await p4)(); await p5;
  assert.strictEqual(lim.active, 0);
  let max = 1; const lim2 = new Limiter(() => max);   // the limit is read live (the setting can change)
  const a = await lim2.acquire(); let got = false; lim2.acquire().then(() => { got = true; });
  await sleep(5); assert.strictEqual(got, false);
  max = 2; a(); await sleep(5); assert.strictEqual(got, true);
});

test('Agent holds a run slot for its run and queues behind a full limiter', async () => {
  const gw = await startGateway([{ content: 'one' }]);
  try {
    const lim = new Limiter(() => 1);
    const hold = await lim.acquire();
    const events = [];
    const mk = () => new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 5, mode: 'hands-off' }), toolDefs: buildTools({}), tools: {}, slot: lim, emit: (e) => events.push(e.type), approve: async () => 'once', askUser: async () => '' });
    const p = mk().run({ id: 'x', messages: [], items: [] }, 'hi');
    await sleep(60);
    assert.ok(events.includes('queued')); assert.strictEqual(gw.requests.length, 0, 'no model call while queued');
    hold();
    const r = await p;
    assert.strictEqual(r.stopped, false); assert.strictEqual(gw.requests.length, 1); assert.ok(events.includes('started'));
    assert.strictEqual(lim.active, 0, 'slot released at the end');
  } finally { gw.close(); }
});

test('screen lock is FIFO, held per run, abortable', async () => {
  const lock = new ScreenLock();
  const a = lock.holder(), b = lock.holder(), c = lock.holder();
  const order = [];
  await a.ensure();
  await a.ensure();                                   // idempotent for the same run
  const pb = b.ensure().then(() => order.push('b'));
  const pc = c.ensure().then(() => order.push('c'));
  await sleep(10);
  assert.deepStrictEqual(order, []);
  a.release(); await pb;
  assert.deepStrictEqual(order, ['b']);
  b.release(); await pc;
  assert.deepStrictEqual(order, ['b', 'c']);
  const ctl = new AbortController();
  const d = lock.holder();
  const pd = d.ensure(ctl.signal);
  ctl.abort();
  await assert.rejects(pd, /aborted/);
  c.release();
  const e = lock.holder(); await e.ensure(); assert.ok(e.held()); e.release();
});

test('helper-can\'t-spawn: agent_* refuse for helpers, work for the primary', async () => {
  const { m, runs } = mkManager();
  const helperTools = agentTools(m, { isHelper: true });
  for (const n of ['agent_start', 'agent_list', 'agent_stop']) {
    const r = await helperTools[n]({ name: 'x', task: 'y' }, {});
    assert.strictEqual(r.error, true); assert.strictEqual(r.text, NO); assert.match(r.text, /Glims can't start Glims/);
  }
  assert.strictEqual(m.list().length, 0); assert.strictEqual(runs.length, 0);
  const t = agentTools(m, { isHelper: false });
  const bad = t.agent_start({ name: 'x', task: 'y', every: 'often' }, {});
  assert.strictEqual(bad.error, true); assert.match(bad.text, /every must look like/);
  const ok = t.agent_start({ name: 'x', task: 'y', every: '1h' }, { thread: { id: 'tp' } });
  assert.match(ok.text, /Started Glim 'x' \(id h\w+\)/); assert.match(ok.text, /every 1h/); assert.match(ok.text, /next run/);
  assert.strictEqual(m.list()[0].parent, 'tp');
  assert.match(t.agent_list(), /x \| queued \| every 1h \| next (?:\w{3} )?\d\d:\d\d \| last: none yet/);
  const dup = t.agent_start({ name: 'X', task: 'y' }, {}); assert.match(dup.text, /already exists/);
  assert.match(t.agent_stop({ name_or_id: 'x' }).text, /Stopped Glim 'x'/);
  assert.match(t.agent_list(), /x \| stopped \| once/);
  assert.strictEqual(m.find('x').next, null);
  assert.match(t.agent_stop({ name_or_id: 'nope' }).text, /no Glim/);
});

test('helper user message: date prefix, name, task; recurring runs carry the previous report (<= 600 chars)', async () => {
  const { m, runs } = mkManager();
  m.add({ name: 'w', task: 'check weather', every: '1h' });
  assert.strictEqual(runs[0].text, "You are helper 'w'. Task: check weather. Finish with a short report.");
  runs[0].done({ report: 'R'.repeat(900) });
  await until(() => m.find('w').status === 'idle');
  m.runNow('w');
  const t = runs[1].text;
  assert.match(t, /^You are helper 'w'\. Task: check weather\. Finish with a short report\.\nPrevious report: R+…/);
  assert.ok(t.includes('R'.repeat(599)) && !t.includes('R'.repeat(601)));
  const once = { name: 'o', task: 't', lastReport: 'old' };
  assert.ok(!/Previous report/.test(helperText(once)), 'one-off helpers have no previous report');
});

test('finished run: status, summary, onFinish with the parent; stop and delete', async () => {
  const { m, runs, finished, store } = mkManager();
  m.add({ name: 'job', task: 't', parent: 'tparent' });
  assert.strictEqual(m.find('job').status, 'queued');
  runs[0].hooks.onState('running'); assert.strictEqual(m.find('job').status, 'running');
  runs[0].hooks.onState('waiting'); assert.strictEqual(m.find('job').status, 'waiting-for-Ben');
  runs[0].hooks.onState('running');
  runs[0].done({ report: 'Found 3 things.\nAll good.' });
  await until(() => finished.length);
  assert.deepStrictEqual(finished[0], { name: 'job', summary: 'Found 3 things. All good.', parent: 'tparent' });
  assert.strictEqual(m.find('job').status, 'idle'); assert.strictEqual(m.find('job').next, null);
  // stop during a run: aborted, no notice
  m.add({ name: 'long', task: 't' });
  const sig = runs[1].hooks.signal;
  m.stop('long');
  assert.strictEqual(m.find('long').status, 'stopped');
  runs[1].done({ report: 'late' });
  await sleep(20);
  assert.strictEqual(finished.length, 1);
  const tid = m.find('job').threadId;
  assert.ok(store.loadThread(tid) && store.loadThread(tid).helper === m.find('job').id);
  assert.strictEqual(m.remove('job'), true);
  assert.strictEqual(store.loadThread(tid), null);
  assert.strictEqual(m.find('job'), null);
});

test('persistence: helpers.json survives a restart; a run in flight comes back idle', async () => {
  const { m, runs, dir, store } = mkManager();
  m.add({ name: 'p', task: 't', at: '07:30' });
  m.add({ name: 'q', task: 't2' });                    // running (never finishes)
  const m2 = new Helpers({ file: path.join(dir, 'helpers.json'), store, runner: async () => ({ report: '' }) });
  assert.deepStrictEqual(m2.list().map((h) => [h.name, h.status, h.schedule]), [['p', 'idle', 'daily 07:30'], ['q', 'idle', 'once']]);
  assert.ok(m2.find('p').next);
  assert.strictEqual(runs.length, 1);
});

test('notices: queued in the primary thread, injected as one line before Ben\'s next message, then cleared', () => {
  const t = { id: 'p', messages: [], items: [] };
  addNotice(t, 'news', 'Three new stories.\nTop: X');
  addNotice(t, 'disk', 'Disk is 80% full');
  assert.deepStrictEqual(t.items.map((i) => i.t), ['notice', 'notice']);   // visible in the UI right away
  assert.strictEqual(t.messages.length, 0);                                // not in model history yet
  assert.strictEqual(takeNotices(t), '[helper updates] news: Three new stories. Top: X; disk: Disk is 80% full');
  assert.strictEqual(takeNotices(t), '');
});

test('agent + fake gateway: primary calls agent_start -> helper runs -> notice queued -> next user message carries it', async () => {
  const dir = tmp();
  const store = new Store(dir);
  const gw = await startGateway([(req) => {
    const msgs = req.messages;
    const firstUser = msgs.find((m) => m.role === 'user').content;
    const last = msgs[msgs.length - 1];
    if (/You are helper 'ticker'/.test(firstUser)) {
      return last.role === 'tool' ? { content: 'Report: the answer is 42.' } : { tool_calls: [{ name: 'run_shell', arguments: { command: 'echo 42' } }] };
    }
    if (last.role === 'tool') return { content: 'Helper started.' };
    if (/\[helper updates\]/.test(last.content)) return { content: 'Got the update.' };
    return { tool_calls: [{ name: 'agent_start', arguments: { name: 'ticker', task: 'compute the answer' } }] };
  }]);
  try {
    const settings = () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 10, mode: 'ask', helperMode: 'hands-off', vision: 'off' });
    const lim = new Limiter(() => 2);
    let mgr;
    const mkAgent = (isHelper) => new Agent({
      getSettings: isHelper ? () => ({ ...settings(), mode: 'hands-off' }) : settings,
      toolDefs: buildTools({}), slot: lim,
      tools: { run_shell: async (a) => 'ran ' + a.command, ...agentTools(mgr, { isHelper }) },
      emit: () => {}, approve: async () => 'deny', askUser: async () => '', onThreadChange: (t) => store.saveThread(t)
    });
    const primary = new Thread('primary');
    let notified;
    const done = new Promise((r) => { notified = r; });
    mgr = new Helpers({
      file: path.join(dir, 'helpers.json'), store,
      runner: createRunner({ store, makeAgent: (h, { onState }) => { const a = mkAgent(true); a.o.onState = onState; return { agent: a, dispose() {} }; } }),
      onFinish: (h, summary, parent) => { addNotice(primary.thread, h.name, summary); notified({ h, parent }); }
    });
    await mkAgent(false).run(primary.thread, 'start a helper to compute the answer');
    assert.match(primary.thread.items.find((i) => i.t === 'step').preview, /Started Glim 'ticker'/);
    const { h, parent } = await done;
    assert.strictEqual(parent, primary.thread.id);
    // the helper ran against the same gateway with the same system prompt and tool list as the primary
    const helperReqs = gw.requests.filter((r) => /You are helper/.test(r.messages.find((m) => m.role === 'user').content));
    const primReqs = gw.requests.filter((r) => !/You are helper/.test(r.messages.find((m) => m.role === 'user').content));
    assert.strictEqual(helperReqs[0].messages[0].content, primReqs[0].messages[0].content);
    assert.strictEqual(JSON.stringify(helperReqs[0].tools), JSON.stringify(primReqs[0].tools));
    assert.strictEqual(helperReqs.length, 2);
    // helper thread saved with its report
    const ht = store.loadThread(h.threadId);
    assert.strictEqual(ht.helper, h.id);
    assert.ok(ht.items.some((i) => i.t === 'step' && i.tool === 'run_shell'));
    assert.strictEqual(ht.messages.at(-1).content, 'Report: the answer is 42.');
    assert.match(mgr.find('ticker').lastSummary, /answer is 42/);
    // notice visible in the primary thread, but not in model history until the next user turn
    assert.ok(primary.thread.items.some((i) => i.t === 'notice' && /42/.test(i.text)));
    assert.ok(!primary.thread.messages.some((m) => m.role === 'user' && typeof m.content === 'string' && /helper updates/.test(m.content)));
    await mkAgent(false).run(primary.thread, 'what happened?');
    const users = primary.thread.messages.filter((m) => m.role === 'user');
    assert.match(users.at(-1).content, /^\[\w{3} \d{4}-\d\d-\d\d \d\d:\d\d\] \[helper updates\] ticker: Report: the answer is 42\.\nwhat happened\?$/);
    assert.strictEqual(primary.thread.items.filter((i) => i.t === 'user').at(-1).text, 'what happened?');
    assert.deepStrictEqual(primary.thread.pendingNotices, []);
  } finally { gw.close(); }
});

function Thread(id) { this.thread = { id, title: 'x', messages: [], items: [] }; }

test('Helpers.tick: a hold (sleeping) defers due runs; they fire once when the hold lifts', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hold-'));
  const store = new Store(dir);
  let hold = true; const runs = []; const clock = { t: Date.parse('2026-10-26T08:00:00Z') };
  const m = new Helpers({ file: path.join(dir, 'helpers.json'), store, now: () => clock.t, hold: () => hold, runner: async (h) => { runs.push(h.name); return { report: 'r' }; } });
  m.add({ name: 'briefing', task: 't', at: '08:00' });
  clock.t += 2 * 86400000;
  m.tick(); assert.deepStrictEqual(runs, []);
  hold = false; m.tick(); assert.deepStrictEqual(runs, ['briefing']);
});

test('Helpers.add: deferFirst waits for the next slot, and a per-Glim mode is kept', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'defer-'));
  const runs = []; const clock = { t: Date.parse('2026-10-26T08:00:00Z') };
  const m = new Helpers({ file: path.join(dir, 'helpers.json'), store: new Store(dir), now: () => clock.t, runner: async (h) => { runs.push(h.name); return { report: 'r' }; } });
  const v = m.add({ name: 'news', task: 't', every: '2h', deferFirst: true, mode: 'ask' });
  assert.deepStrictEqual(runs, []);
  assert.strictEqual(m.find('news').next, clock.t + 2 * 3600000);
  assert.strictEqual(m.find('news').mode, 'ask'); assert.ok(v.id);
  const x = m.add({ name: 'plain', task: 't', every: '2h' });   // the normal path still starts at once
  assert.deepStrictEqual(runs, ['plain']); assert.ok(x);
  assert.strictEqual(new Helpers({ file: path.join(dir, 'helpers.json'), store: new Store(dir), runner: async () => ({}) }).find('news').mode, 'ask'); // persisted
});

test('Helpers.add: refuses a near-duplicate of an active Glim on the same schedule, allows different ones', () => {
  const { m } = mkManager();
  m.add({ name: 'Morning briefing', task: 'Brief Ben on weather and calendar', at: '08:00', deferFirst: true });
  assert.throws(() => m.add({ name: 'morning briefing agent', task: 'give the morning brief', at: '08:00' }), /similar Glim 'Morning briefing'/);
  assert.throws(() => m.add({ name: 'wake-up', task: 'Brief Ben on weather and calendar', at: '08:00' }), /similar Glim/);
  m.add({ name: 'Evening briefing', task: 'Summarize the day', at: '20:00' });            // other schedule: fine
  m.add({ name: 'Email watch', task: 'Check mail', every: '30m', deferFirst: true });       // other name and task: fine
  m.stop('Morning briefing');
  m.add({ name: 'morning briefing agent', task: 'give the morning brief', at: '08:00' }); // the old one is stopped: fine
});
