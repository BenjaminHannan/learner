'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Helpers, Limiter, ScreenLock, createRunner, parseSchedule, nextRun, addNotice, takeNotices, helperText, batchNotice } = require('../src/helpers');
const { agentTools, NO, MAX_KIDS } = require('../src/tools/agents');
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

test('Glim tools: a Glim lists, moves its own time, starts up to MAX_KIDS one level deep, stops only its own', async () => {
  const { m, runs } = mkManager();
  assert.strictEqual(agentTools(m, { isHelper: true }).agent_start({ name: 'x', task: 'y' }, {}).text, NO); // no known self: refuse
  const top = agentTools(m, { isHelper: false });
  top.agent_start({ name: 'brief', task: 'morning briefing', at: '08:00' }, { thread: { id: 'tp' } });
  top.agent_start({ name: 'other', task: 'unrelated job', at: '09:00' }, { thread: { id: 'tp' } });
  const me = m.find('brief');
  const g = agentTools(m, { isHelper: true, selfId: me.id });
  assert.match(g.agent_list(), /brief \(you\)/);
  const mv = g.agent_start({ name: 'brief', at: '07:00' }, {});
  assert.match(mv.text, /Your schedule is now 'daily 07:00'/); assert.strictEqual(m.find('brief').at, '07:00');
  assert.match(g.agent_start({ name: 'Brief' }, {}).text, /give at/);
  const kid = g.agent_start({ name: 'k1', task: 'fetch the weather' }, { thread: { id: me.threadId } });
  assert.match(kid.text, /Started Mote 'k1'/); assert.strictEqual(m.find('k1').byHelper, me.id);
  const kg = agentTools(m, { isHelper: true, selfId: m.find('k1').id });
  assert.match(kg.agent_start({ name: 'k1a', task: 'deeper still' }, {}).text, /Started Mote 'k1a'/); // MAX_DEPTH 2: a grandchild is fine
  const kga = agentTools(m, { isHelper: true, selfId: m.find('k1a').id });
  assert.match(kga.agent_start({ name: 'k1b', task: 'deepest omega' }, {}).text, /cannot start more/);
  for (let i = 2; i <= MAX_KIDS; i++) g.agent_start({ name: 'k' + i, task: 'job number ' + i + ' alpha' + i }, {});
  assert.match(g.agent_start({ name: 'k9', task: 'one too many zeta' }, {}).text, /already run 5 Motes/);
  const rec = m.active.get(m.find('k1').id) || {}; rec.thread = { id: 'th-live' };
  if (m.active.has(m.find('k1').id)) assert.strictEqual(m.liveThread('th-live'), rec.thread);
  assert.strictEqual(m.liveThread('nope'), null);
  assert.match(g.agent_stop({ name_or_id: 'other' }).text, /not yours to change/); assert.notStrictEqual(m.find('other').status, 'stopped');
  assert.match(g.agent_stop({ name_or_id: 'k1' }).text, /Stopped Mote 'k1'/);
  assert.match(g.agent_start({ name: 'k9', task: 'one more now fits zeta' }, {}).text, /Started Mote 'k9'/);
  assert.match(g.agent_stop({ name_or_id: 'brief' }).text, /Stopped Mote 'brief'/);
  assert.ok(runs.length > 0);
});

test('primary agent_* tools', async () => {
  const { m } = mkManager();
  const t = agentTools(m, { isHelper: false });
  const bad = t.agent_start({ name: 'x', task: 'y', every: 'often' }, {});
  assert.strictEqual(bad.error, true); assert.match(bad.text, /every must look like/);
  const ok = t.agent_start({ name: 'x', task: 'y', every: '1h' }, { thread: { id: 'tp' } });
  assert.match(ok.text, /Started Mote 'x' \(id h\w+\)/); assert.match(ok.text, /every 1h/); assert.match(ok.text, /next run/);
  assert.strictEqual(m.list()[0].parent, 'tp');
  assert.match(t.agent_list(), /x \| queued \| every 1h \| next (?:\w+ )?\d\d:\d\d \(in [^)]+\) \| last: none yet/);
  const dup = t.agent_start({ name: 'X', task: 'y' }, {}); assert.match(dup.text, /already exists/);
  const up = t.agent_update({ name_or_id: 'x', at: '07:00', every: '' });
  assert.match(up.text, /Updated Mote 'x': daily 07:00, next run/); assert.strictEqual(m.find('x').every, null);
  assert.match(t.agent_update({ name_or_id: 'x', paused: true }).text, /\(paused\)/);
  assert.match(t.agent_update({ name_or_id: 'x', new_name: 'renamed' }).text, /Updated Mote 'renamed'/);
  assert.match(t.agent_update({ name_or_id: 'zzz', at: '07:00' }).text, /no Mote/);
  assert.match(t.agent_update({ name_or_id: 'renamed', at: '25:00' }).text, /at must look like/);
  assert.match(t.agent_stop({ name_or_id: 'renamed' }).text, /Stopped Mote 'renamed'/);
  assert.match(t.agent_list(), /renamed \| stopped \| once/);
  assert.strictEqual(m.find('renamed').next, null);
  assert.match(t.agent_stop({ name_or_id: 'nope' }).text, /no Mote/);
});

test('agent_update run: true starts a helper now; an idle one-off with no time says it will not run', async () => {
  const { m, runs } = mkManager();
  const t = agentTools(m, { isHelper: false });
  t.agent_start({ name: 'research', task: 'read AI news' }, {});
  runs[0].done({ report: 'done' });
  await until(() => m.find('research').status === 'idle');
  assert.match(t.agent_list(), /research \| idle, not scheduled \| once \| next none/);
  assert.match(t.agent_update({ name_or_id: 'research', task: 'read AI news again' }).text, /Not scheduled: it will not run unless/);
  const r = t.agent_update({ name_or_id: 'research', run: true });
  assert.match(r.text, /; started now; status (queued|working)/); assert.match(r.summary, /^Started Mote research/);
  assert.strictEqual(runs.length, 2); assert.ok(m.isRunning(m.find('research').id));
  assert.match(t.agent_update({ name_or_id: 'research', run: true }).text, /it was already running/);
  assert.strictEqual(runs.length, 2);
});

const HNEW = "Work on your own: if a tool or a step fails, fix it or try another way yourself (agent_update changes a helper); do not ask Ben about errors or tool problems. Finish with a short report of the result only, with no notes about your own tools.";
test('helper user message: date prefix, name, task; recurring runs carry the previous report (<= 600 chars)', async () => {
  const { m, runs } = mkManager();
  m.add({ name: 'w', task: 'check weather', every: '1h' });
  assert.strictEqual(runs[0].text, "You are helper 'w'. Task: check weather. " + HNEW + '\nIf the run found ideas worth testing, put each on its own line starting "IDEA: " (one line, with a short why).');
  runs[0].done({ report: 'R'.repeat(900) });
  await until(() => m.find('w').status === 'idle');
  m.runNow('w');
  const t = runs[1].text;
  assert.match(t, /^You are helper 'w'\. Task: check weather\. Work on your own: .*no notes about your own tools\.\nPrevious report: R+…/);
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
  assert.deepStrictEqual(t.items.map((i) => i.t), []);   // Ben Oct 28: a helper never reports to Ben directly; Glim relays it
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
    assert.match(primary.thread.items.find((i) => i.t === 'step').preview, /Started Mote 'ticker'/);
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
    assert.ok(!primary.thread.items.some((i) => i.t === 'notice')); assert.ok(primary.thread.pendingNotices.some((n) => /42/.test(n.summary)));
    assert.ok(!primary.thread.messages.some((m) => m.role === 'user' && typeof m.content === 'string' && /helper updates/.test(m.content)));
    await mkAgent(false).run(primary.thread, 'what happened?');
    const users = primary.thread.messages.filter((m) => m.role === 'user');
    assert.match(users.at(-1).content, /^\[\w{3} \d{4}-\d\d-\d\d \d\d:\d\d, \d{1,2}:\d\d [AP]M\] \[If this needs tools[^\]]*\] \[helper updates\] ticker: Report: the answer is 42\.\nwhat happened\?$/);
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
  assert.throws(() => m.add({ name: 'morning briefing agent', task: 'give the morning brief', at: '08:00' }), /similar Mote 'Morning briefing'/);
  assert.throws(() => m.add({ name: 'wake-up', task: 'Brief Ben on weather and calendar', at: '08:00' }), /similar Mote/);
  m.add({ name: 'Evening briefing', task: 'Summarize the day', at: '20:00' });            // other schedule: fine
  m.add({ name: 'Email watch', task: 'Check mail', every: '30m', deferFirst: true });       // other name and task: fine
  m.stop('Morning briefing');
  m.add({ name: 'morning briefing agent', task: 'give the morning brief', at: '08:00' }); // the old one is stopped: fine
});

// ---- coordination UX: quiet runs, failures + retry, hold reasons, batching, interrupted recovery ----
test('quiet run: NO_UPDATE keeps the last report, flags quiet, and the prompt only asks for it on recurring Glims', async () => {
  const flags = [];
  const { m, runs, clock } = mkManager({ onFinish: (h, s, p, f) => flags.push(f) });
  m.add({ name: 'once', task: 'x' }); runs[0].done(); await until(() => flags.length === 1);
  m.add({ name: 'watch', task: 'w', every: '1h' }); runs[1].done({ report: 'Real report' }); await until(() => flags.length === 2);
  assert.ok(!/NO_UPDATE/.test(runs[1].text), 'no previous report yet');
  clock.t += 3600000; m.tick(); assert.match(runs[2].text, /reply with exactly: NO_UPDATE/);
  runs[2].done({ report: '  no_update. ' }); await until(() => flags.length === 3);
  const h = m.find('watch');
  assert.deepStrictEqual(flags[2], { quiet: true, failed: false });
  assert.strictEqual(h.lastReport, 'Real report'); assert.match(h.lastSummary, /^No change \(checked/); assert.strictEqual(h.quiet, true);
  clock.t += 3600000; m.tick(); runs[3].done({ report: 'New thing' }); await until(() => flags.length === 4);
  assert.strictEqual(m.find('watch').quiet, false); assert.strictEqual(m.find('watch').lastReport, 'New thing');
  assert.ok(!/NO_UPDATE/.test(helperText({ name: 'o', task: 't', lastReport: 'r' })), 'one-time Glims never get it');
});

test('failure: status failed, one quick retry for a recurring Glim, reset on success, survives load()', async () => {
  const flags = [];
  const { m, runs, clock, store, dir } = mkManager({ onFinish: (h, s, p, f) => flags.push({ s, f }) });
  m.add({ name: 'f', task: 't', every: '2h' });
  runs[0].done({ error: 'fetch failed' }); await until(() => flags.length === 1);
  const h = m.find('f');
  assert.strictEqual(h.status, 'failed'); assert.strictEqual(h.fails, 1); assert.strictEqual(h.lastError, 'fetch failed');
  assert.strictEqual(h.next, clock.t + 5 * 60000); assert.deepStrictEqual(flags[0], { s: 'Failed: fetch failed', f: { quiet: false, failed: true } });
  clock.t += 5 * 60000; m.tick(); assert.strictEqual(runs.length, 2, 'failed does not block a due run');
  runs[1].done({ error: 'again' }); await until(() => flags.length === 2);
  assert.strictEqual(h.fails, 2); assert.ok(h.next > clock.t + 3600000, 'no second early retry');
  const m2 = new Helpers({ file: path.join(dir, 'helpers.json'), store, now: () => clock.t, runner: async () => ({}) });
  assert.strictEqual(m2.find('f').status, 'failed');
  clock.t += 2 * 3600000; m.tick(); runs[2].done({ report: 'fine' }); await until(() => flags.length === 3);
  assert.strictEqual(h.status, 'idle'); assert.strictEqual(h.fails, 0); assert.strictEqual(h.lastError, null);
});

test('batchNotice: one, several, and several with a failure', () => {
  const a = { name: 'A', summary: 'did a', threadId: 'ta', parent: 'p' }, b = { name: 'B', summary: 'did b', threadId: 'tb', parent: 'p' }, c = { name: 'C', summary: 'Failed: x', threadId: 'tc', parent: 'p', failed: true };
  assert.deepStrictEqual(batchNotice([a]), { title: 'Glim finished: A', body: 'did a', threadId: 'ta' });
  assert.strictEqual(batchNotice([c]).title, "Glim couldn't finish: C");
  const two = batchNotice([a, b]); assert.strictEqual(two.title, 'Glim finished 2 tasks'); assert.strictEqual(two.body, 'A, B: did a'); assert.strictEqual(two.threadId, 'p');
  assert.strictEqual(batchNotice([a, b, c]).title, "Glim finished 3 tasks (1 couldn't finish)");
  assert.strictEqual(batchNotice([a, { ...b, parent: 'q' }]).threadId, null);
});

test('hold reasons: dueHeld while sleeping, cleared on run; queued reports slot count', () => {
  let hold = true;
  const { m, runs, clock } = mkManager({ hold: () => hold });
  m.add({ name: 'd', task: 't', every: '1h', deferFirst: true });
  clock.t += 3600000; m.tick();
  assert.strictEqual(runs.length, 0); assert.strictEqual(m.list()[0].dueHeld, true);
  hold = false; m.tick(); assert.strictEqual(runs.length, 1); assert.strictEqual(m.list()[0].dueHeld, false);
  runs[0].hooks.onState('queued', { running: 2 });
  assert.deepStrictEqual([m.list()[0].hold, m.list()[0].holdCount], ['slot', 2]);
  runs[0].hooks.onState('running'); assert.strictEqual(m.list()[0].hold, null);
});

test('interrupted one-time Glim resumes once after a restart, then not again', () => {
  const dir = tmp(), store = new Store(dir), file = path.join(dir, 'helpers.json'), t0 = 1e12;
  fs.writeFileSync(file, JSON.stringify({ helpers: [
    { id: 'a', name: 'a', task: 't', status: 'running', lastReport: '', next: null },
    { id: 'b', name: 'b', task: 't', every: '1h', status: 'running', lastReport: '', next: t0 + 5 },
    { id: 'c', name: 'c', task: 't', status: 'idle', lastReport: '', next: null }] }));
  const m = new Helpers({ file, store, now: () => t0, runner: async () => ({}) });
  const a = m.find('a'); assert.strictEqual(a.status, 'idle'); assert.strictEqual(a.next, t0 + 60000); assert.strictEqual(a.resumed, 1);
  assert.match(a.lastSummary, /Interrupted when the app closed/); assert.strictEqual(m.find('b').next, t0 + 5); assert.strictEqual(m.find('c').next, null);
  a.status = 'running'; m.save();
  const m2 = new Helpers({ file, store, now: () => t0, runner: async () => ({}) });
  assert.match(m2.find('a').lastSummary, /Interrupted twice/); assert.strictEqual(m2.find('a').next, null, 'no third try');
});

test('a Glim report is its final answer without leading "I need to / Let me" narration', () => {
  const { lastAssistantText } = require('../src/helpers');
  const msgs = [
    { role: 'assistant', content: 'I need to check the agent list first.', tool_calls: [{ id: '1' }] },
    { role: 'tool', content: 'x' },
    { role: 'assistant', content: "I need to finish the briefing myself. Let me gather the data. Weather: 34F, fair. School 8:00." }
  ];
  assert.strictEqual(lastAssistantText(msgs), 'Weather: 34F, fair. School 8:00.');
  assert.strictEqual(lastAssistantText([{ role: 'assistant', content: 'Let me look.', tool_calls: [{ id: '1' }] }, { role: 'assistant', content: 'Done: all good.' }]), 'Done: all good.');
  assert.strictEqual(lastAssistantText([{ role: 'assistant', content: 'Let me look.', tool_calls: [{ id: '1' }] }]), 'Let me look.'); // only narration exists: keep it
});

test('fmtWhenRel: today / tomorrow / weekday with how long until', () => {
  const { fmtWhenRel } = require('../src/helpers');
  const now = new Date(2026, 9, 28, 17, 0).getTime();
  assert.strictEqual(fmtWhenRel(new Date(2026, 9, 28, 17, 30).getTime(), now), 'today 17:30 (in 30 min)');
  assert.strictEqual(fmtWhenRel(new Date(2026, 9, 29, 8, 0).getTime(), now), 'tomorrow 08:00 (in 15 h)');
  assert.strictEqual(fmtWhenRel(new Date(2026, 9, 31, 8, 0).getTime(), now), 'Sat 08:00 (in 3 days)');
  assert.strictEqual(fmtWhenRel(null, now), '-');
});

test("Ben's chat first: a due Glim waits while Ben's chat is busy, then runs exactly once", async () => {
  let ben = true;
  const { m, runs, clock } = mkManager({ yieldTo: () => ben });
  m.add({ name: 'mail', task: 't', every: '1h', deferFirst: true });
  clock.t += 61 * 60000;
  m.tick(); m.tick();
  assert.strictEqual(runs.length, 0);                  // held, not lost
  assert.ok(m.find('mail').next <= clock.t);           // still due
  m.tick(true);                                        // forced (sleep check-in) ignores the hold
  assert.strictEqual(runs.length, 1);
  runs[0].done(); await until(() => m.find('mail').status !== 'running');
  ben = true; clock.t += 61 * 60000; m.tick();
  assert.strictEqual(runs.length, 1);
  ben = false; m.tick(); m.tick();
  assert.strictEqual(runs.length, 2);                  // fires once on the first quiet tick, no double run
  assert.ok(m.find('mail').next > clock.t);
});

test("Ben's chat first: a running Glim waits before its next model call without holding a run slot", async () => {
  const gw = await startGateway([{ content: 'Done.' }]);
  try {
    let ben = true; const states = [];
    const slot = new Limiter(() => 1);
    const a = new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 5, mode: 'hands-off', vision: 'off', verify: false }), toolDefs: buildTools({}), tools: {}, slot, benBusy: () => ben, benPollMs: 10,
      onState: (s, info) => states.push(s + (info && info.ben ? ':ben' : '')), emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = { id: 'h', title: 'x', messages: [], items: [] };
    const p = a.run(t, 'check mail');
    await until(() => states.includes('queued:ben'));
    assert.strictEqual(gw.requests.length, 0);
    assert.strictEqual(slot.full(), false);            // Ben's own run can take the slot
    ben = false;
    await p;
    assert.strictEqual(gw.requests.length, 1);
    assert.ok(states.indexOf('running', states.indexOf('queued:ben')) > 0);
  } finally { gw.close(); }
});
