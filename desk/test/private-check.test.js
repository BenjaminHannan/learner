'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { EventEmitter } = require('events');
const { PrivateCheck, ProcessIdentity, matchesIdentity, hasArg, privateFetch, WINDOWS_HELPER } = require('../src/private-check');
const roots = [];
process.on('exit', () => roots.forEach(root => fs.rmSync(root, { recursive: true, force: true })));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const tick = () => new Promise(resolve => setImmediate(resolve));
const pending = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const quote = value => /\s/.test(value) ? '"' + value + '"' : value;
const Grading = require('../src/grading');
const good = { ...Grading.binding, ok: true, general_n: 8, general_on: 8, general_off: 8, held_n: 1, held_on: 1, held_off: 0 };

function fixture(options = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'private-check-')); roots.push(root);
  const files = {};
  for (const [key, name, data] of [['exe', 'engine.exe', 'engine'], ['python', 'python.exe', 'python'], ['model', 'base.gguf', 'base'], ['adapter', 'candidate.gguf', 'candidate'], ['cards', 'held.jsonl', '{"status":"held_out","night":1,"q":"Q?","a":"A"}\n']]) {
    files[key] = path.join(root, name); fs.writeFileSync(files[key], data);
  }
  const identities = new Map(), children = [], killed = [], terminated = [], started = { server: pending(), grader: pending() };
  let pid = 1000, controller;
  const processes = {
    async secureDirectory() { return true; },
    async inspect(id) { if (options.inspectUnknown) return { status: 'unknown' }; return identities.get(id) || { status: 'gone', pid: id }; },
    async find(record, role) {
      if (options.findUnknown) return { status: 'unknown' };
      if (options.findUnknownItem) return { status: 'ok', processes: [{ status: 'unknown' }] };
      return { status: 'ok', processes: [...identities.values()].filter(value => matchesIdentity(value, record, role, 'win32', false)) };
    },
    async terminate(record, role) {
      const expected = record.roles[role], identity = identities.get(expected.pid);
      if (!identity || identity.startTime !== expected.startTime) return { status: 'gone' };
      if (options.recoveryKillFails) return { status: 'unknown' };
      assert.ok(matchesIdentity(identity, record, role, 'win32'));
      terminated.push(expected.pid); identities.delete(expected.pid); return { status: 'gone' };
    },
  };
  const spawn = (exe, args, env) => {
    const role = args.includes('--alias') ? 'server' : 'grader';
    if (options.beforeSpawn) options.beforeSpawn(role, exe, args, env, controller);
    if (options.throwSpawn === role) throw Error('spawn failed');
    const child = new EventEmitter(); child.stdout = new EventEmitter(); child.stderr = new EventEmitter(); child.exitCode = null; child.signalCode = null;
    child.pid = ++pid; child.role = role; child.exe = exe; child.args = args; child.options = env;
    identities.set(child.pid, { status: 'alive', pid: child.pid, exe, commandLine: [exe, ...args].map(quote).join(' '), startTime: 'born-' + child.pid });
    child.exit = code => {
      if (child.exitCode != null) return;
      child.exitCode = code;
      if (identities.get(child.pid)?.startTime === 'born-' + child.pid) identities.delete(child.pid);
      child.emit('exit', code); child.emit('close', code);
    };
    child.kill = signal => {
      killed.push({ pid: child.pid, role, signal });
      if (options.ignoreKill === role || (options.ignoreTerm === role && signal === 'SIGTERM')) return true;
      setTimeout(() => child.exit(0), options.stopDelayMs || 0); return true;
    };
    children.push(child); started[role].resolve(child);
    if (role === 'grader' && options.autoGrade !== false) setTimeout(() => {
      if (child.exitCode != null) return;
      const verdict = options.verdict || good;
      child.stdout.emit('data', JSON.stringify(verdict) + '\n'); child.exit(options.gradeCode === undefined ? verdict.ok === true ? 0 : verdict.ok === false ? 1 : 2 : options.gradeCode);
    }, 5);
    return child;
  };
  const fetch = options.fetch || (async (url, init) => {
    const server = children.filter(child => child.role === 'server').at(-1), args = server.args;
    assert.equal(url, 'http://127.0.0.1:32123/v1/models');
    assert.equal(init.headers.Authorization, 'Bearer ' + args[args.indexOf('--api-key') + 1]);
    return { ok: true, json: async () => ({ data: [{ id: options.wrongAlias ? 'ordinary-main-model' : args[args.indexOf('--alias') + 1] }] }) };
  });
  const defaults = { platform: 'win32', spawn, fetch, processes, freePort: async () => 32123,
    pollMs: 2, requestTimeoutMs: 20, startTimeoutMs: 80, graderTimeoutMs: 80, stopWaitMs: 15, forceWaitMs: 15 };
  controller = new PrivateCheck(root, defaults);
  const input = { ...files, sleepmlxParent: root, expectedAdapterSha256: sha(fs.readFileSync(files.adapter)), expectedHeldSha256: sha(fs.readFileSync(files.cards)), flavor: 'cpu' };
  return { root, files, input, controller, defaults, identities, processes, children, killed, terminated, started };
}

function journal(t, overrides = {}) {
  const id = crypto.randomUUID(), jobDir = path.join(t.controller.jobsDir, id);
  fs.mkdirSync(jobDir, { recursive: true });
  const adapter = path.join(jobDir, 'adapter.gguf'), cards = path.join(jobDir, 'held.jsonl');
  fs.copyFileSync(t.files.adapter, adapter); fs.copyFileSync(t.files.cards, cards);
  const record = { version: 1, id, alias: 'premonition-check-' + id, apiKey: crypto.randomBytes(32).toString('hex'), port: 32123,
    url: 'http://127.0.0.1:32123', jobDir, model: { path: t.files.model }, adapter: { path: adapter }, cards: { path: cards },
    roles: { server: { exe: t.files.exe, pid: 2345, startTime: 'original-birth', exited: false } }, ...overrides };
  fs.writeFileSync(t.controller.ledger, JSON.stringify(record), { mode: 0o600 });
  return record;
}
function identityFor(record, role = 'server', changes = {}) {
  const item = record.roles[role];
  const args = role === 'server' ? ['--alias', record.alias, '--api-key', record.apiKey, '-m', record.model.path, '--lora', record.adapter.path]
    : ['--private-check-id', record.id, '--server', record.url, '--cards', record.cards.path];
  return { status: 'alive', pid: item.pid || 4567, exe: item.exe, commandLine: [item.exe, ...args].map(quote).join(' '), startTime: item.startTime || 'discovered-birth', ...changes };
}

test('private check uses copies/authenticated unique alias and returns a pass only after both children exit', async () => {
  const t = fixture({ beforeSpawn(role, exe, args, env, controller) {
    const intent = JSON.parse(fs.readFileSync(controller.ledger));
    assert.equal(intent.roles[role].pid, null); assert.ok(intent.alias && intent.apiKey);
    assert.equal(fs.statSync(controller.ledger).mode & 0o077, 0);
  } });
  const result = await t.controller.check(t.input);
  assert.equal(result.ok, true); assert.equal(result.processStopped, true);
  assert.equal(t.children.length, 2); assert.ok(t.children.every(child => child.exitCode != null));
  const [server, grader] = t.children;
  const adapter = server.args[server.args.indexOf('--lora') + 1], cards = grader.args[grader.args.indexOf('--cards') + 1];
  assert.notEqual(adapter, t.files.adapter); assert.notEqual(cards, t.files.cards);
  assert.equal(grader.options.env.SLEEPMLX_SERVED_PRIVATE_ALIAS, server.args[server.args.indexOf('--alias') + 1]);
  assert.equal(grader.options.env.SLEEPMLX_SERVED_PRIVATE_API_KEY, server.args[server.args.indexOf('--api-key') + 1]);
  assert.equal(fs.readFileSync(t.files.adapter, 'utf8'), 'candidate');
  assert.equal(fs.existsSync(t.controller.ledger), false); assert.equal(t.identities.size, 0);
});

test('CPU private engines use two threads while Metal keeps its existing invocation', async () => {
  for (const flavor of ['cpu', 'metal']) {
    const t = fixture(), result = await t.controller.check({ ...t.input, flavor });
    assert.equal(result.processStopped, true); assert.equal(result.ok, true);
    const args = t.children.find(child => child.role === 'server').args;
    assert.equal(args[args.indexOf('-ngl') + 1], flavor === 'cpu' ? '0' : '99');
    if (flavor === 'cpu') assert.equal(args[args.indexOf('-t') + 1], '2');
    else assert.equal(args.includes('-t'), false);
  }
});

test('abort waits for grader and model exit; no late verdict can become accepted', async () => {
  const t = fixture({ autoGrade: false, stopDelayMs: 10 }), ctl = new AbortController();
  const checking = t.controller.check({ ...t.input, signal: ctl.signal });
  await t.started.grader.promise; ctl.abort();
  const result = await checking;
  assert.equal(result.ok, null); assert.equal(result.processStopped, true);
  assert.ok(t.children.every(child => child.exitCode != null));
  const grader = t.children.find(child => child.role === 'grader'); grader.stdout.emit('data', JSON.stringify(good));
  assert.equal(result.ok, null); assert.equal(fs.existsSync(t.controller.ledger), false);
});

test('external cancellation during confirmed shutdown still prevents a late pass', async () => {
  const t = fixture({ stopDelayMs: 10 }), ctl = new AbortController();
  const checking = t.controller.check({ ...t.input, signal: ctl.signal });
  const server = await t.started.server.promise;
  const originalKill = server.kill;
  server.kill = signal => { ctl.abort(); return originalKill(signal); };
  const result = await checking;
  assert.equal(result.ok, null); assert.equal(result.processStopped, true);
});

test('inputs changed during slow shutdown cannot produce a pass', async () => {
  const t = fixture({ stopDelayMs: 10 }), checking = t.controller.check(t.input);
  const server = await t.started.server.promise, originalKill = server.kill;
  server.kill = signal => { fs.writeFileSync(t.files.cards, 'changed during stop'); return originalKill(signal); };
  const result = await checking;
  assert.equal(result.ok, null); assert.equal(result.processStopped, true); assert.match(result.reasons.join(' '), /changed/);
});

test('late authenticated health after cancellation never starts a grader', async () => {
  const response = pending(), requested = pending();
  const t = fixture({ fetch: async () => { requested.resolve(); return response.promise; } });
  const checking = t.controller.check(t.input); await requested.promise;
  const stopped = await t.controller.cancel(); assert.equal(stopped.ok, true); assert.equal(stopped.processStopped, true);
  response.resolve({ ok: true, json: async () => ({ data: [{ id: 'late' }] }) });
  const result = await checking; await tick();
  assert.equal(result.ok, null); assert.equal(t.children.length, 1); assert.equal(t.identities.size, 0);
});

test('wrong alias/occupied private port cannot be accepted and no unrelated process is reclaimed', async () => {
  const t = fixture({ wrongAlias: true }); t.identities.set(9999, { status: 'alive', pid: 9999, startTime: 'unrelated', exe: '/other.exe', commandLine: 'public server on 32123' });
  const result = await t.controller.check(t.input);
  assert.equal(result.ok, null); assert.equal(result.processStopped, true);
  assert.equal(t.children.length, 1); assert.ok(t.identities.has(9999)); assert.deepEqual(t.terminated, []);
});

test('grader timeout still stops both owned children', async () => {
  const t = fixture({ autoGrade: false }); const result = await t.controller.check(t.input);
  assert.equal(result.ok, null); assert.match(result.reasons.join(' '), /timed out/);
  assert.equal(result.processStopped, true); assert.ok(t.children.every(child => child.exitCode != null));
});

test('SIGTERM escalation targets only the owned child and waits for SIGKILL exit', async () => {
  const t = fixture({ ignoreTerm: 'server' }); const result = await t.controller.check(t.input);
  assert.equal(result.ok, true); assert.equal(result.processStopped, true);
  assert.deepEqual(t.killed.filter(row => row.role === 'server').map(row => row.signal), ['SIGTERM', 'SIGKILL']);
});

test('a passed grader cannot authorize promotion when model exit is unconfirmed; a later exit permits explicit recovery', async () => {
  const t = fixture({ ignoreKill: 'server' }); const result = await t.controller.check(t.input);
  assert.equal(result.ok, null); assert.equal(result.processStopped, false); assert.equal(result.blocked, true);
  const record = JSON.parse(fs.readFileSync(t.controller.ledger)); assert.ok(record.roles.server.pid); assert.ok(record.roles.server.startTime);
  const again = await t.controller.check(t.input); assert.equal(again.processStopped, false); assert.equal(t.children.length, 2);
  t.children.find(child => child.role === 'server').exit(0);
  assert.deepEqual(await t.controller.ensureIdle(), { ok: true, processStopped: true });
  assert.equal(fs.existsSync(t.controller.ledger), false);
});

test('ignored grader kill persists its identity and app restart stops it before allowing normal model load', async () => {
  const t = fixture({ autoGrade: false, ignoreKill: 'grader' });
  const result = await t.controller.check(t.input);
  assert.equal(result.processStopped, false); assert.equal(result.ok, null);
  const record = JSON.parse(fs.readFileSync(t.controller.ledger));
  assert.equal(record.roles.server.exited, true); assert.equal(record.roles.grader.exited, false);
  const restarted = new PrivateCheck(t.root, t.defaults); const recovered = await restarted.ensureIdle();
  assert.equal(recovered.ok, true); assert.equal(recovered.processStopped, true);
  assert.deepEqual(t.terminated, [record.roles.grader.pid]); assert.equal(fs.existsSync(t.controller.ledger), false);
});

test('restart recovers a crash after spawn intent but before PID publication using exact job markers', async () => {
  const t = fixture(); const record = journal(t);
  record.roles.server.pid = null; record.roles.server.startTime = null;
  fs.writeFileSync(t.controller.ledger, JSON.stringify(record));
  const actual = identityFor(record); t.identities.set(actual.pid, actual);
  t.identities.set(9999, { ...actual, pid: 9999, commandLine: actual.commandLine.replace(record.alias, 'public-model') });
  const restarted = new PrivateCheck(t.root, t.defaults); const result = await restarted.ensureIdle();
  assert.equal(result.ok, true); assert.deepEqual(t.terminated, [actual.pid]); assert.ok(t.identities.has(9999));
  assert.equal(fs.existsSync(t.controller.ledger), false);
});

test('a positively reused PID is never killed, even when new owner has the same executable', async () => {
  const t = fixture(); const record = journal(t), reused = identityFor(record, 'server', { startTime: 'unrelated-new-birth' });
  t.identities.set(reused.pid, reused);
  assert.deepEqual(await t.controller.ensureIdle(), { ok: true, processStopped: true });
  assert.deepEqual(t.terminated, []); assert.ok(t.identities.has(reused.pid)); assert.equal(fs.existsSync(t.controller.ledger), false);
});

test('unknown inspection, discovery or recovered kill remain blocked with their journal intact', async () => {
  for (const flag of ['inspectUnknown', 'findUnknown', 'findUnknownItem', 'recoveryKillFails']) {
    const t = fixture({ [flag]: true }), record = journal(t);
    if (flag.startsWith('findUnknown')) { record.roles.server.pid = null; record.roles.server.startTime = null; fs.writeFileSync(t.controller.ledger, JSON.stringify(record)); }
    else t.identities.set(record.roles.server.pid, identityFor(record));
    const result = await t.controller.ensureIdle();
    assert.equal(result.ok, false, flag); assert.equal(result.processStopped, false, flag); assert.equal(result.blocked, true, flag);
    assert.ok(fs.existsSync(t.controller.ledger), flag); assert.deepEqual(t.terminated, []);
  }
});

test('unknown same-birth command identity is blocked rather than signalling another process', async () => {
  const t = fixture(), record = journal(t); t.identities.set(record.roles.server.pid, identityFor(record, 'server', { commandLine: 'some other process' }));
  assert.equal((await t.controller.ensureIdle()).processStopped, false); assert.deepEqual(t.terminated, []);
});

test('a check blocked by an older journal can later recover without retaining a phantom active job', async () => {
  const options = { inspectUnknown: true }, t = fixture(options), record = journal(t);
  t.identities.set(record.roles.server.pid, identityFor(record));
  const result = await t.controller.check(t.input);
  assert.equal(result.processStopped, false); assert.equal(t.children.length, 0);
  options.inspectUnknown = false;
  assert.deepEqual(await t.controller.ensureIdle(), { ok: true, processStopped: true });
  assert.equal(fs.existsSync(t.controller.ledger), false);
});

test('invalid journal is fail-closed and never erased', async () => {
  const t = fixture(); fs.mkdirSync(t.controller.jobsDir, { recursive: true }); fs.writeFileSync(t.controller.ledger, '{');
  const result = await t.controller.ensureIdle(); assert.equal(result.processStopped, false); assert.ok(fs.existsSync(t.controller.ledger)); assert.deepEqual(t.killed, []);
});

test('a malformed exited flag cannot hide an owned live process', async () => {
  const t = fixture(), record = journal(t); record.roles.server.exited = 'false';
  fs.writeFileSync(t.controller.ledger, JSON.stringify(record)); t.identities.set(record.roles.server.pid, identityFor(record));
  const result = await t.controller.ensureIdle(); assert.equal(result.processStopped, false); assert.ok(t.identities.has(record.roles.server.pid)); assert.ok(fs.existsSync(t.controller.ledger));
});

test('partially inspected discovery candidates cannot be mistaken for absent processes', async () => {
  const t = fixture(), record = journal(t); record.roles.server.pid = null; record.roles.server.startTime = null;
  fs.writeFileSync(t.controller.ledger, JSON.stringify(record));
  t.processes.find = async () => ({ status: 'ok', processes: [{ status: 'alive', pid: 4567, startTime: 'known', exe: t.files.exe, commandLine: null }] });
  assert.equal((await t.controller.ensureIdle()).processStopped, false); assert.ok(fs.existsSync(t.controller.ledger));
});

test('changing a candidate or held snapshot before/during grading cannot produce a pass', async () => {
  const before = fixture(); fs.writeFileSync(before.files.cards, 'changed');
  assert.equal((await before.controller.check(before.input)).ok, null); assert.equal(before.children.length, 0);
  const during = fixture({ autoGrade: false }); const promise = during.controller.check(during.input), child = await during.started.grader.promise;
  fs.writeFileSync(during.files.adapter, 'changed'); child.stdout.emit('data', JSON.stringify(good)); child.exit(0);
  const result = await promise; assert.equal(result.ok, null); assert.equal(result.processStopped, true); assert.match(result.reasons.join(' '), /changed/);
});

test('private model crash during grading cancels grader and cannot pass', async () => {
  const t = fixture({ autoGrade: false }); const checking = t.controller.check(t.input); await t.started.grader.promise;
  t.children.find(child => child.role === 'server').exit(1);
  const result = await checking; assert.equal(result.ok, null); assert.equal(result.processStopped, true); assert.ok(t.children.every(child => child.exitCode != null));
});

test('retries get new private copies and never substitute changing live cards', async () => {
  const options = { verdict: { ok: null, reasons: ['temporary infrastructure failure'] } }, t = fixture(options);
  assert.equal((await t.controller.check(t.input)).ok, null);
  fs.writeFileSync(path.join(t.root, 'live-cards.jsonl'), 'a different later night');
  options.verdict = good;
  const result = await t.controller.check(t.input);
  assert.equal(result.ok, true); assert.equal(result.processStopped, true);
  const snapshots = t.children.filter(child => child.role === 'grader').map(child => child.args[child.args.indexOf('--cards') + 1]);
  assert.equal(snapshots.length, 2); assert.notEqual(snapshots[0], snapshots[1]);
  assert.equal(fs.readFileSync(t.files.cards, 'utf8').includes('"q":"Q?"'), true);
});

test('an inspection provider that never resolves cannot hang recovery or forget the owned journal', async () => {
  const t = fixture(); journal(t); t.controller.o.inspectionTimeoutMs = 10;
  t.processes.inspect = () => new Promise(() => {});
  const result = await t.controller.ensureIdle();
  assert.equal(result.processStopped, false); assert.equal(result.blocked, true); assert.ok(fs.existsSync(t.controller.ledger));
});

test('spawn failure and malformed grader output produce no orphaned private model', async () => {
  for (const options of [{ throwSpawn: 'server' }, { verdict: { nonsense: true } }, { verdict: good, gradeCode: 2 }]) {
    const t = fixture(options), result = await t.controller.check(t.input);
    assert.equal(result.ok, null); assert.equal(result.processStopped, true); assert.equal(t.identities.size, 0); assert.equal(fs.existsSync(t.controller.ledger), false);
  }
});

test('Windows recovery helper validates and kills the same open process handle without taskkill', async () => {
  let request;
  const inspector = new ProcessIdentity({ platform: 'win32', exec: async (exe, args) => {
    assert.equal(exe, 'powershell.exe'); assert.ok(args.includes('-NonInteractive'));
    const script = Buffer.from(args.at(-1), 'base64').toString('utf16le');
    request = JSON.parse(Buffer.from(/FromBase64String\('([^']+)'\)/.exec(script)[1], 'base64').toString());
    return '{"status":"gone"}';
  } });
  const t = fixture(), record = journal(t);
  assert.deepEqual(await inspector.terminate(record, 'server', 50), { status: 'gone' });
  assert.equal(request.pid, record.roles.server.pid); assert.equal(request.startTime, record.roles.server.startTime);
  assert.ok(request.markers.some(([flag]) => flag === '--api-key'));
  assert.match(WINDOWS_HELPER, /OpenProcess/); assert.match(WINDOWS_HELPER, /TerminateProcess\(\$handle/);
  assert.match(WINDOWS_HELPER, /WaitForSingleObject\(\$handle/); assert.doesNotMatch(WINDOWS_HELPER, /taskkill|Stop-Process/);
});

test('argument marker matching is exact and does not accept substring aliases', () => {
  assert.equal(hasArg('engine --alias "private-job"', '--alias', 'private-job', 'win32'), true);
  assert.equal(hasArg('engine --alias private-job-other', '--alias', 'private-job', 'win32'), false);
  assert.equal(hasArg('engine --alias public --note private-job', '--alias', 'private-job', 'win32'), false);
});

test('native private HTTP ignores proxies and refuses redirects without forwarding its key', async () => {
  const http = require('http'), seen = [];
  const server = http.createServer((request, response) => {
    seen.push({ path: request.url, auth: request.headers.authorization });
    if (request.url === '/redirect') { response.writeHead(302, { Location: '/target' }); return response.end(); }
    response.setHeader('Content-Type', 'application/json'); response.end('{"data":[]}');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const previous = process.env.HTTP_PROXY; process.env.HTTP_PROXY = 'http://127.0.0.1:1';
  try {
    const response = await privateFetch('http://127.0.0.1:' + server.address().port + '/redirect', { headers: { Authorization: 'Bearer synthetic-private-key' } });
    assert.equal(response.ok, false); assert.deepEqual(seen, [{ path: '/redirect', auth: 'Bearer synthetic-private-key' }]);
  } finally { if (previous === undefined) delete process.env.HTTP_PROXY; else process.env.HTTP_PROXY = previous; await new Promise(resolve => server.close(resolve)); }
});

test('private credentials never escape in the returned verdict', async () => {
  const t = fixture({ autoGrade: false }), checking = t.controller.check(t.input), grader = await t.started.grader.promise;
  const key = grader.options.env.SLEEPMLX_SERVED_PRIVATE_API_KEY;
  grader.stdout.emit('data', JSON.stringify({ ...good, reasons: ['a diagnostic accidentally included ' + key] })); grader.exit(0);
  const result = await checking; assert.equal(JSON.stringify(result).includes(key), false); assert.equal(result.ok, true);
});

test('private grader revision or contract mismatch is inconclusive after confirmed cleanup', async () => {
  for (const verdict of [{ ...good, grader: undefined }, { ...good, grader: 'strict-3' }, { ...good, grading_contract_sha256: '0'.repeat(64) }]) {
    const t = fixture({ verdict }), result = await t.controller.check(t.input);
    assert.equal(result.ok, null); assert.equal(result.processStopped, true);
    assert.match(result.reasons.join(' '), /grader revision/);
    assert.equal(fs.existsSync(t.controller.ledger), false);
    assert.equal(t.identities.size, 0);
  }
});
