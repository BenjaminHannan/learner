'use strict';
// Glim team, Bedwars side: the Mac client for TOOLS.md (src/games/bedwars/benspc.js). A fake runner only; no network.
const test = require('node:test');
const assert = require('node:assert');
const { BensPC, argTokens, parseLine } = require('../src/games/bedwars/benspc');

// script: host name -> list of replies (consumed in order); every call is recorded
function fakeRunner(script) {
  const calls = [];
  const run = async (cmd, argv, o) => {
    const host = argv.includes('HostName=10.0.0.188') ? 'lan' : 'tailscale';
    calls.push({ cmd, argv, host, timeoutMs: o && o.timeoutMs });
    const q = script[host] || []; const r = q.length > 1 ? q.shift() : q[0];
    return r || { code: 255, stdout: '', stderr: 'no route', timedOut: false };
  };
  return { run, calls };
}
const ok = (o) => ({ code: 0, stdout: JSON.stringify({ ok: true, ...(o || {}) }) + '\n', stderr: '', timedOut: false });
const down = { code: 255, stdout: '', stderr: 'ssh: connect to host 10.0.0.188 port 22: Operation timed out', timedOut: false };

test('LAN first: ssh options, verb and args, and the one JSON line (noise before it is ignored)', async () => {
  const f = fakeRunner({ lan: [{ code: 0, stdout: 'Windows banner\n{"ok":true,"free_gb":120.5}\n', stderr: '' }] });
  const pc = new BensPC({ run: f.run });
  const r = await pc.call('disk');
  assert.deepStrictEqual(r, { ok: true, free_gb: 120.5 });
  assert.strictEqual(f.calls.length, 1); assert.strictEqual(f.calls[0].cmd, 'ssh');
  const a = f.calls[0].argv;
  assert.ok(a.includes('ConnectTimeout=8') && a.includes('BatchMode=yes'));
  assert.deepStrictEqual(a.slice(-3), ['HostName=10.0.0.188', 'benspc', 'disk']);
  await pc.call('gpu-acquire', { who: 'glim-bedwars', why: 'Glim wants to play' });
  assert.deepStrictEqual(f.calls[1].argv.slice(-5), ['gpu-acquire', '--who', 'glim-bedwars', '--why', '"Glim wants to play"']);
});

test('LAN down -> Tailscale; the route that worked is tried first next time', async () => {
  const f = fakeRunner({ lan: [down], tailscale: [ok({ host: 'BENSPC' })] });
  const pc = new BensPC({ run: f.run });
  const r = await pc.call('ping');
  assert.strictEqual(r.host, 'BENSPC');
  assert.deepStrictEqual(f.calls.map((c) => c.host), ['lan', 'tailscale']);
  assert.deepStrictEqual(f.calls[1].argv.slice(-2), ['benspc', 'ping']);
  await pc.call('ping');
  assert.deepStrictEqual(f.calls.map((c) => c.host), ['lan', 'tailscale', 'tailscale']);
});

test('a JSON error from BensPC is returned as is (no second route: that would run the verb twice)', async () => {
  const f = fakeRunner({ lan: [{ code: 1, stdout: '{"ok":false,"error":"GPU busy: in use by qwen","next":["gpu-status"]}\n', stderr: '' }], tailscale: [ok()] });
  const r = await new BensPC({ run: f.run }).call('gpu-acquire', { who: 'glim-bedwars' });
  assert.deepStrictEqual(r, { ok: false, error: 'GPU busy: in use by qwen', next: ['gpu-status'] });
  assert.strictEqual(f.calls.length, 1);
});

test('both routes down -> a plain transport error', async () => {
  const f = fakeRunner({ lan: [down], tailscale: [{ code: 255, stdout: '', stderr: 'ssh: Could not resolve hostname benspc', timedOut: false }] });
  const r = await new BensPC({ run: f.run }).call('server-status');
  assert.strictEqual(r.ok, false); assert.strictEqual(r.transport, true);
  assert.match(r.error, /^transport: lan: ssh could not connect.*; tailscale: ssh could not connect/);
  assert.strictEqual(f.calls.length, 2);
});

test('a timeout: read verbs try the other route; state-changing verbs stop (may have run) and say so', async () => {
  const slow = { code: 255, stdout: '', stderr: '', timedOut: true };
  const f = fakeRunner({ lan: [slow], tailscale: [ok({ running: true })] });
  const pc = new BensPC({ run: f.run });
  assert.strictEqual((await pc.call('server-status')).running, true);
  const g = fakeRunner({ lan: [slow], tailscale: [ok({ pid: 4 })] });
  const r = await new BensPC({ run: g.run }).call('server-start', { map: 'Lighthouse' });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.uncertain, true);
  assert.strictEqual(g.calls.length, 1, 'not resent on the other route');
  assert.strictEqual(g.calls[0].timeoutMs, 240000, 'server-start gets a longer wait (port + RCON + TruthKit)');
  // refused connection (exit 255, no timeout) never reached BensPC: a state-changing verb may use the other route
  const h = fakeRunner({ lan: [down], tailscale: [ok({ pid: 9 })] });
  assert.strictEqual((await new BensPC({ run: h.run }).call('client-launch', { name: 'GlimBot', server: '127.0.0.1:25565' })).pid, 9);
});

test('only TOOLS.md verbs; unsafe argument text never reaches ssh', async () => {
  const f = fakeRunner({ lan: [ok()] }); const pc = new BensPC({ run: f.run });
  assert.deepStrictEqual(await pc.call('kill', { pid: 4 }), { ok: false, error: 'not allowed', next: [] });
  for (const bad of ['a;b', 'x$(y)', 'a"b', "it's", 'a|b', 'a`b', 'a&b', 'a>b', 'line\nbreak']) {
    const r = await pc.call('gpu-acquire', { who: 'glim-bedwars', why: bad });
    assert.strictEqual(r.ok, false, bad); assert.match(r.error, /unsafe argument/);
  }
  assert.strictEqual(f.calls.length, 0);
  assert.throws(() => argTokens({ 'Bad Flag': 1 }));
  assert.deepStrictEqual(argTokens({ since: '2026-11-04T15:00:00.000Z', max: 500, opponent: false, x: true }), ['--since', '2026-11-04T15:00:00.000Z', '--max', '500', '--x']);
  assert.strictEqual(parseLine('noise\n{bad json\n'), null);
});

test('the client knows exactly the TOOLS.md verbs (contract drift shows up here)', () => {
  const fs = require('fs'), path = require('path');
  const md = fs.readFileSync(path.join(__dirname, '..', 'src', 'games', 'bedwars', 'TOOLS.md'), 'utf8');
  const verbs = md.split('\n').map((l) => (l.match(/^\| `([a-z-]+)` \|/) || [])[1]).filter(Boolean).sort();
  assert.deepStrictEqual(require('../src/games/bedwars/benspc').VERBS.slice().sort(), verbs);
});
