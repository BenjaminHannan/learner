'use strict';
// Glim team, Bedwars side: the self-sufficient play session (src/games/bedwars/session.js) against a fake BensPC (no network).
const test = require('node:test');
const assert = require('node:assert');
const S = require('../src/games/bedwars/session');
const H = require('../src/games/bedwars/harness');

// a small stateful stand-in for glimtool.ps1. o.script: verb -> replies served first (an object, or fn(st) -> object|null to fall through)
function fakePC(o) {
  o = o || {};
  const st = { gpu: o.gpuHolder || null, server: o.serverRunning ? { pid: 999, ours: false } : null, match: null, client: null, polls: 0, violations: [] };
  const script = o.script || {}, calls = [];
  const call = async (verb, args) => {
    calls.push({ verb, args: args || {} });
    const q = script[verb]; if (q && q.length) { const r = q.shift(); const x = typeof r === 'function' ? r(st) : r; if (x) return x; }
    switch (verb) {
      case 'gpu-acquire': if (st.gpu) return { ok: false, error: 'GPU busy: in use by ' + st.gpu, next: ['gpu-status'] }; st.gpu = 'glim-bedwars'; return { ok: true, holder: 'glim-bedwars' };
      case 'gpu-status': return { ok: true, holder: st.gpu, free: !st.gpu };
      case 'gpu-release': if (st.gpu === 'glim-bedwars') st.gpu = null; return { ok: true };
      case 'server-status': return st.server ? { ok: true, running: true, pid: st.server.pid, port: 25565 } : { ok: true, running: false };
      case 'server-start': st.server = { pid: 4242, ours: true }; return { ok: true, pid: 4242, port: 25570 };
      case 'server-stop': if (st.server && !st.server.ours) st.violations.push('stopped a server we did not start'); st.server = null; return { ok: true };
      case 'map-list': return { ok: true, maps: ['Lighthouse', 'Pernicious'] };
      case 'match-start': st.match = { state: 'running' }; return { ok: true, match_id: 'm1' };
      case 'match-status': st.polls++; if (!st.match) return { ok: true, state: 'none' }; if (st.polls >= (o.pollsToEnd || 2)) st.match.state = 'ended'; return { ok: true, state: st.match.state, teams: ['red', 'blue'] };
      case 'match-stop': st.match = null; return { ok: true };
      case 'log-read': return { ok: true, events: st.polls === 1 ? [{ t: '2026-11-04T15:00:00.000Z', type: 'match_start' }] : [], next_since: '2026-11-04T15:00:01.000Z' };
      case 'client-launch': st.client = { pid: 5150 }; return { ok: true, pid: 5150, window: 'Minecraft 1.8.9' };
      case 'client-stop': st.client = null; return { ok: true };
    }
    return { ok: false, error: 'not allowed' };
  };
  return { call, calls, st };
}
function session(pc, o) {
  const asked = [], sleeps = [];
  const s = new S.PlaySession({ benspc: pc, askBen: (r, d) => asked.push(r), sleep: async (ms) => { sleeps.push(ms); }, ...(o || {}) });
  return { s, asked, sleeps };
}
const verbs = (pc) => pc.calls.map((c) => c.verb);
const noPids = (pc) => pc.calls.every((c) => !('pid' in c.args));

test('success: decide -> launch -> match -> play -> quit, in order; everything we started is stopped; GPU handed back', async () => {
  const pc = fakePC(); const { s, asked } = session(pc, { map: 'Pernicious' });
  const r = await s.run({});
  assert.strictEqual(r.outcome, 'played'); assert.strictEqual(r.ok, true);
  assert.deepStrictEqual(r.reached, { decide: true, launch: true, match: true, play: true, quit: true });
  assert.deepStrictEqual(verbs(pc), ['gpu-acquire', 'server-status', 'server-start', 'map-list', 'match-start', 'client-launch',
    'match-status', 'log-read', 'match-status', 'log-read', 'client-stop', 'match-stop', 'server-stop', 'gpu-release']);
  assert.strictEqual(r.map, 'Pernicious');
  assert.deepStrictEqual(pc.calls.find((c) => c.verb === 'match-start').args, { map: 'Pernicious', mode: '1v1', opponent: 'scripted:L2' });
  assert.deepStrictEqual(pc.calls.find((c) => c.verb === 'client-launch').args, { name: 'GlimBot', server: '127.0.0.1:25570' }, 'our local server only');
  assert.strictEqual(pc.calls.find((c) => c.verb === 'gpu-acquire').args.who, 'glim-bedwars');
  assert.strictEqual(r.events.length, 1);
  assert.deepStrictEqual([pc.st.gpu, pc.st.server, pc.st.match, pc.st.client], [null, null, null, null]);
  assert.deepStrictEqual(asked, []); assert.ok(noPids(pc));
});

test('a server that was already running is reused and left running (never stop what we did not start; never name a pid)', async () => {
  const pc = fakePC({ serverRunning: true }); const { s } = session(pc);
  const r = await s.run({});
  assert.strictEqual(r.outcome, 'played');
  assert.ok(!verbs(pc).includes('server-start') && !verbs(pc).includes('server-stop'));
  assert.deepStrictEqual(pc.st.server, { pid: 999, ours: false });
  assert.deepStrictEqual(pc.st.violations, []); assert.ok(noPids(pc));
  assert.strictEqual(pc.calls.find((c) => c.verb === 'client-launch').args.server, '127.0.0.1:25565');
  assert.strictEqual(pc.st.gpu, null);
});

test('a failing step: retries with backoff, reads the error, runs allowed runbook alternatives only, then cleans up', async () => {
  const err = { ok: false, error: 'bedwars plugin did not answer on RCON', next: ['match-status', 'server-stop', 'client-stop', 'reinstall the plugin'] };
  const pc = fakePC({ script: { 'match-start': [err, err, err] } }); const { s, asked, sleeps } = session(pc);
  const r = await s.run({});
  assert.strictEqual(r.outcome, 'failed'); assert.strictEqual(r.ok, false);
  const step = r.steps.find((x) => x.step === 'match-start');
  assert.strictEqual(step.tries, 3); assert.strictEqual(step.errors.length, 3);
  assert.deepStrictEqual(sleeps, [2000, 4000], 'backoff doubles');
  assert.strictEqual(verbs(pc).filter((v) => v === 'match-status').length, 1, 'a read-only alternative runs once per step');
  assert.ok(step.alternatives.some((a) => a.hint === 'server-stop' && !a.ran), 'stopping the server is not a match-start alternative');
  assert.ok(step.alternatives.some((a) => /reinstall/.test(a.hint) && !a.ran), 'free-text hints are logged, not run');
  assert.deepStrictEqual(r.reached, { decide: true, launch: false, match: false, play: false, quit: true });
  assert.ok(!verbs(pc).includes('client-stop') && !verbs(pc).includes('match-stop'), 'nothing we did not start is stopped');
  assert.deepStrictEqual(verbs(pc).slice(-2), ['server-stop', 'gpu-release']);
  assert.strictEqual(pc.st.gpu, null); assert.deepStrictEqual(asked, []);
});

test('the GPU is always released: an exception in play, an abort (Ben first), a failing release is reported', async () => {
  const pc = fakePC(); const { s } = session(pc, { play: async () => { throw new Error('reflex crashed'); } });
  const r = await s.run({});
  assert.strictEqual(r.outcome, 'failed'); assert.match(r.error, /reflex crashed/);
  assert.deepStrictEqual(verbs(pc).slice(-4), ['client-stop', 'match-stop', 'server-stop', 'gpu-release']);
  assert.strictEqual(pc.st.gpu, null);
  // Ben starts chatting: the gate closes mid-play -> yielded, cleaned up
  const pc2 = fakePC({ pollsToEnd: 99 }); let open = true; const { s: s2 } = session(pc2, { sleep: async () => { open = false; } });
  const r2 = await s2.run({ gateOk: () => open });
  assert.strictEqual(r2.outcome, 'yielded'); assert.strictEqual(pc2.st.gpu, null); assert.strictEqual(pc2.st.client, null);
  // the release itself keeps failing: retried, and the result says the GPU may still be held
  const bad = { ok: false, error: 'GPU_LOAN.txt is locked' };
  const pc3 = fakePC({ script: { 'gpu-release': [bad, bad, bad] } }); const { s: s3 } = session(pc3);
  const r3 = await s3.run({});
  assert.strictEqual(verbs(pc3).filter((v) => v === 'gpu-release').length, 3);
  assert.strictEqual(r3.reached.quit, false); assert.strictEqual(r3.ok, false);
  assert.deepStrictEqual(r3.cleanup.find((c) => c.what === 'gpu'), { what: 'gpu', verb: 'gpu-release', ok: false, error: 'GPU_LOAN.txt is locked' });
});

test('GPU busy (Ben\'s duels first): deferred, no other step, no question to Ben, the loan is untouched', async () => {
  const pc = fakePC({ gpuHolder: 'ben-duel' }); const { s, asked } = session(pc);
  const r = await s.run({});
  assert.strictEqual(r.outcome, 'deferred'); assert.deepStrictEqual(verbs(pc), ['gpu-acquire', 'gpu-status'], 'one read-only look: is the holder us?');
  assert.strictEqual(pc.st.gpu, 'ben-duel'); assert.deepStrictEqual(asked, []);
});

test('an uncertain gpu-acquire (timed out) is settled by gpu-status, and released at the end when it was ours', async () => {
  const lost = (st) => { st.gpu = 'glim-bedwars'; return { ok: false, error: 'transport: lan: timed out (may have run; check status)', transport: true, uncertain: true, next: [] }; };
  const pc = fakePC({ script: { 'gpu-acquire': [lost] } }); const { s } = session(pc);
  const r = await s.run({});
  assert.strictEqual(r.outcome, 'played'); assert.strictEqual(pc.st.gpu, null);
  // it timed out AND every later check failed: the session still asks gpu-status at the end and releases if we hold it
  const lost2 = (st) => { st.gpu = 'glim-bedwars'; return { ok: false, error: 'transport: timed out', transport: true, uncertain: true, next: [] }; };
  const tout = { ok: false, error: 'transport: timed out', transport: true };
  const pc2 = fakePC({ script: { 'gpu-acquire': [lost2, lost2, lost2], 'gpu-status': [tout, tout, tout] } });
  const r2 = await session(pc2).s.run({});
  assert.strictEqual(r2.outcome, 'failed'); assert.strictEqual(pc2.st.gpu, null, 'released after the end-of-session check');
  assert.deepStrictEqual(verbs(pc2).slice(-2), ['gpu-status', 'gpu-release']);
  // "busy" because the holder is us (a lost reply earlier): gpu-status settles it, the session plays and releases
  const pc3 = fakePC({ gpuHolder: 'glim-bedwars' }); const r3 = await session(pc3).s.run({});
  assert.strictEqual(r3.outcome, 'played'); assert.strictEqual(pc3.st.gpu, null);
});

test('askBen only for the four truly-blocked cases (signed out, login, purchase, UAC), once, and the session still cleans up', async () => {
  const cases = [
    [{ ok: false, error: 'no signed-in session', next: ['ask-ben: sign in to BensPC'] }, 'signed_out'],
    [{ ok: false, error: 'the launcher wants a Microsoft account login', next: [] }, 'login'],
    [{ ok: false, error: 'a purchase is needed to continue', next: [] }, 'purchase'],
    [{ ok: false, error: 'a UAC prompt appeared (elevation needed)', next: [] }, 'uac'],
    [{ ok: false, error: 'client could not start', next: ['ask-ben: sign in to BensPC'] }, 'signed_out']
  ];
  for (const [reply, reason] of cases) {
    const pc = fakePC({ script: { 'client-launch': [reply, reply, reply] } }); const { s, asked } = session(pc);
    const r = await s.run({});
    assert.strictEqual(r.outcome, 'blocked', reply.error); assert.deepStrictEqual(asked, [reason], reply.error);
    assert.strictEqual(r.askedBen.reason, reason);
    assert.strictEqual(verbs(pc).filter((v) => v === 'client-launch').length, 1, 'blocked: no pointless retries');
    assert.deepStrictEqual([pc.st.gpu, pc.st.server, pc.st.match], [null, null, null]);
  }
  const notBlocked = [
    { ok: false, error: 'port 25570 is in use', next: ['server-status'] },
    { ok: false, error: 'java.exe not found', next: ['ask-ben: please install java'] },
    { ok: false, error: 'disk below the 15 GB floor', next: [] },
    { ok: false, error: 'transport: lan: ssh could not connect (Permission denied (publickey,password))', transport: true, next: [] }
  ];
  for (const reply of notBlocked) {
    const pc = fakePC({ script: { 'client-launch': [reply, reply, reply] } }); const { s, asked } = session(pc);
    const r = await s.run({});
    assert.strictEqual(r.outcome, 'failed', reply.error); assert.deepStrictEqual(asked, [], reply.error);
    assert.strictEqual(pc.st.gpu, null);
  }
  assert.deepStrictEqual(S.ASK_BEN_REASONS, ['signed_out', 'login', 'purchase', 'uac']);
  assert.strictEqual(new S.PlaySession({ benspc: fakePC() }).askBen('server crashed', 'x'), false);
});

test('wantToPlay(): a Mote-pool job the motivation path can run; harness acceptance counts 9/10 with per-step failures', async () => {
  assert.strictEqual(S.wantToPlay({ enabled: false }), null);
  const results = [];
  for (let i = 0; i < 10; i++) {
    const pc = fakePC(i === 3 ? { script: { 'map-list': [{ ok: true, maps: [] }] } } : {});
    const job = S.wantToPlay({ benspc: pc, sleep: async () => {} });
    assert.strictEqual(job.kind, 'game:bedwars'); assert.strictEqual(typeof job.run, 'function'); assert.strictEqual(job.realtime, true);
    results.push(await job.run({ signal: new AbortController().signal, gateOk: () => true }));
  }
  const a = H.acceptance(results);
  assert.deepStrictEqual([a.n, a.passes, a.pass], [10, 9, true]);
  assert.deepStrictEqual(a.perStepFailures, { 'map-list': 1 });
  assert.deepStrictEqual(a.perStageMisses, { launch: 1 }, 'the first stage missed');
  assert.strictEqual(a.tries[3].firstMiss, 'launch');
  assert.strictEqual(H.acceptance(results.slice(0, 9)).pass, null, 'fewer than 10 tries: no verdict');
  results[0] = { ...results[0], outcome: 'failed' };
  assert.strictEqual(H.acceptance(results).pass, false, '8/10 fails the mark');
});
