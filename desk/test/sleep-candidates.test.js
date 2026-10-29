'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { WinSleep } = require('../src/sleepwin');
const A = require('../src/sleep-candidates');
const C = require('../src/runtime/constants');
const roots = [];
process.on('exit', () => roots.forEach(r => fs.rmSync(r, { recursive: true, force: true })));
const Grading = require('../src/grading');
const good = { ...Grading.binding, ok: true, processStopped: true, checkId: '123e4567-e89b-42d3-a456-426614174000', general_n: 8, general_on: 7, general_off: 7, held_n: 1, held_on: 1, held_off: 0 };

test('new authorization requires current grader and exact contract bytes', () => {
  assert.equal(A.validVerdict(good, 1), true);
  for (const verdict of [{ ...good, grader: undefined }, { ...good, grader: 'strict-3' }, { ...good, grading_contract_sha256: '0'.repeat(64) }])
    assert.equal(A.validVerdict(verdict, 1), false);
});
for (const platform of ['win32', 'darwin']) {
function setup() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'adapter-candidate-')); roots.push(root);
  const home = path.join(root, 'sleep'), runtime = path.join(root, 'runtime'), hf = path.join(root, 'hf');
  fs.mkdirSync(path.join(home, 'adapter'), { recursive: true }); fs.mkdirSync(runtime); fs.mkdirSync(hf);
  const base = path.join(runtime, 'base.gguf'), exe = path.join(runtime, 'llama-server.exe'); fs.writeFileSync(base, 'base'); fs.writeFileSync(exe, 'engine'); fs.writeFileSync(path.join(hf, 'config.json'), '{"model_type":"lfm3"}'); fs.writeFileSync(path.join(hf, 'model.safetensors'), 'source weights');
  fs.writeFileSync(path.join(runtime, 'state.json'), JSON.stringify({ model: { file: base, name: C.MODEL_FILE, sha256: 'a'.repeat(64) }, llama: { cpu: { exe }, metal: { exe } } }));
  fs.writeFileSync(path.join(home, 'adapter', 'adapter_model.safetensors'), 'weights');
  fs.writeFileSync(path.join(home, 'state.json'), JSON.stringify({ nights: 2, last_night: { id: 'night-one', date: '2026-10-29', reverted: false } }));
  fs.writeFileSync(path.join(home, 'cards.jsonl'), JSON.stringify({ night: 1, status: 'held_out', q: 'Question?', a: 'Answer' }) + '\n');
  fs.writeFileSync(path.join(home, 'adapter.prev.gguf'), 'previous');
  fs.writeFileSync(path.join(home, 'adapter.prev.gguf.json'), JSON.stringify({ base_hf_id: C.SLEEP_HF_REPO, served: { ok: true } }));
  const id = 'a'.repeat(64), acceptedDir = path.join(home, 'adapter-candidates', id);
  fs.mkdirSync(acceptedDir, { recursive: true });
  fs.writeFileSync(path.join(acceptedDir, 'adapter.gguf'), 'checked');
  const oldHeld = JSON.stringify({ night: 1, status: 'held_out', q: 'Old?', a: 'Old' }) + '\n';
  fs.writeFileSync(path.join(acceptedDir, 'held.jsonl'), oldHeld);
  const oldRecord = { version: 1, id, status: 'accepted', date: '2026-10-28', night_number: 1, created: '2026-10-28T01:00:00.000Z', base: A.baseIdentity(root, hf), day: 1, held_count: 1, adapter_sha256: A.hash('checked'), held_sha256: A.hash(oldHeld), served: good };
  fs.writeFileSync(path.join(acceptedDir, 'record.json'), JSON.stringify(oldRecord));
  fs.writeFileSync(path.join(home, 'accepted-adapters.json'), JSON.stringify({ version: 1, current: id, previous: null, published: [id] }));
  const installer = { state: () => ({ hfDir: hf, convert: 'converter' }), pythonExe: () => 'python', installed: () => true };
  const calls = [], checks = []; let verdict = { ok: null };
  const ws = new WinSleep({ root, platform, installer, sleepmlxParent: root, getSettings: () => ({}), run: async (_, args) => fs.writeFileSync(args[args.indexOf('--outfile')+1], 'candidate'), privateChecker: { ensureIdle: async () => ({ ok: true, processStopped: true }), check: async (cmd) => { checks.push(cmd); return { ...verdict, processStopped: true }; } }, hooks: { resumeModel: async f => { calls.push(f); return { ok: true }; }, servedUrl: () => 'http://127.0.0.1:18090' } });
  ws.night = { status: 'done', date: '2026-10-29', night: 2, day: 1, reverted: false }; ws.active = true;
  return { root, home, hf, base, ws, calls, checks, fallback: path.join(acceptedDir, 'adapter.gguf'), setVerdict: v => { verdict = v; } };
}

test('inconclusive candidate stays pending; next wake retries its saved cards and promotes only after complete pass', async () => {
  const t = setup(); await t.ws._finish();
  const fallback = t.fallback; assert.equal(t.ws.currentLora(), fallback); assert.equal(t.calls.at(-1), fallback);
  assert.match(t.ws.readSummary(), /previously checked adapter/); assert.doesNotMatch(t.ws.readSummary(), /tonight's checked adapter/);
  assert.equal(t.checks.length, 1); assert.equal(t.checks[0].flavor, platform === 'darwin' ? 'metal' : 'cpu'); assert.deepEqual(t.calls, [fallback], 'candidate never reaches the shared gateway');
  assert.match(t.checks[0].adapter, /adapter-candidates/); assert.match(t.checks[0].expectedAdapterSha256, /^[a-f0-9]{64}$/);
  const cards = t.checks[0].cards; assert.match(cards, /held\.jsonl$/);
  fs.writeFileSync(path.join(t.home, 'cards.jsonl'), JSON.stringify({ night: 2, status: 'held_out', q: 'Other?', a: 'Other' }));
  t.ws.night = null; t.ws.active = true; t.setVerdict(good); await t.ws._finish();
  assert.equal(t.checks[1].cards, cards); assert.match(fs.readFileSync(cards, 'utf8'), /Question/);
  assert.notEqual(t.ws.currentLora(), fallback); assert.match(t.ws.currentLora(), /adapter-candidates/);
  assert.equal(fs.readFileSync(fallback, 'utf8'), 'checked');
});

test('empty, malformed, wrong-base, incomplete and changed candidates never become day adapters', async () => {
  const t = setup(); await t.ws._finish();
  const id = fs.readdirSync(path.join(t.home, 'adapter-candidates')).find(x => x !== 'a'.repeat(64)); const dir = path.join(t.home, 'adapter-candidates', id);
  assert.equal(A.validVerdict({ ok: true, general_n: 8, held_n: 1 }, 1), false);
  assert.equal(A.validVerdict({ ...good, held_on: NaN }, 1), false);
  fs.writeFileSync(path.join(dir, 'adapter.gguf'), 'tampered');
  const current = t.ws.currentLora(); assert.equal(current, t.fallback);
  assert.equal(A.inspect(t.home, id, A.baseIdentity(t.root, t.hf)), null);
  fs.writeFileSync(path.join(t.home, 'accepted-adapters.json'), '{}');
  fs.writeFileSync(path.join(t.home, 'adapter.prev.gguf.json'), '{bad'); assert.equal(t.ws.currentLora(), '');
  fs.writeFileSync(path.join(t.home, 'adapter.prev.gguf.json'), JSON.stringify({ base_hf_id: 'other', served: { ok: true } })); assert.equal(t.ws.currentLora(), '');
  fs.writeFileSync(path.join(t.home, 'adapter.prev.gguf.json'), JSON.stringify({ base_hf_id: C.SLEEP_HF_REPO, served: { ok: null } })); assert.equal(t.ws.currentLora(), '');
  assert.equal(fs.existsSync(path.join(t.home, 'adapter.prev.gguf')), true);
});

test('a passed sidecar recovers after a lost manifest and base changes invalidate candidates', async () => {
  const t = setup(); await t.ws._stageCandidate();
  const identity = A.baseIdentity(t.root, t.hf), c = A.pending(t.home, identity);
  c.rec.status = 'accepted'; c.rec.served = good; A.atomic(path.join(c.dir, 'record.json'), c.rec);
  assert.equal(t.ws.currentLora(), t.fallback);
  t.ws.night = null; t.ws.active = true; await t.ws._finish();
  assert.equal(t.ws.currentLora(), c.adapter);
  fs.writeFileSync(t.base, 'different base'); assert.equal(t.ws.currentLora(), '');
});

test('accepted but unpublished old pass is privately rechecked before promotion', async () => {
  const t = setup(); await t.ws._stageCandidate();
  const identity = A.baseIdentity(t.root, t.hf), candidate = A.pending(t.home, identity);
  candidate.rec.status = 'accepted'; candidate.rec.served = { ...good, grader: 'strict-3' };
  A.atomic(path.join(candidate.dir, 'record.json'), candidate.rec);
  assert.equal(A.promote(t.home, candidate), false);
  assert.equal(t.ws.currentLora(), t.fallback);
  t.ws.night = null; t.ws.active = true; t.setVerdict(good); await t.ws._finish();
  assert.equal(t.checks.length, 1); assert.equal(t.ws.currentLora(), candidate.adapter);
});

test('old committed adapter remains available but a corrupted current cannot use idempotent promotion', async () => {
  const t = setup(), identity = A.baseIdentity(t.root, t.hf);
  const committed = A.inspect(t.home, 'a'.repeat(64), identity);
  delete committed.rec.served.grader; delete committed.rec.served.grading_contract_sha256;
  A.atomic(path.join(committed.dir, 'record.json'), committed.rec);
  assert.equal(t.ws.currentLora(), t.fallback);
  assert.equal(A.promote(t.home, committed), true);
  fs.writeFileSync(committed.adapter, 'broken!');
  assert.equal(A.promote(t.home, committed), false);
  assert.equal(t.ws.currentLora(), '');
  assert.equal(fs.existsSync(committed.adapter), true);
});

test('manifest path escapes and symlinked candidate files are rejected', () => {
  const t = setup(), outside = fs.mkdtempSync(path.join(os.tmpdir(), 'outside-')); roots.push(outside);
  fs.writeFileSync(path.join(t.home, 'accepted-adapters.json'), JSON.stringify({ version: 1, current: '../../outside' }));
  assert.equal(t.ws.currentLora(), '');
  fs.symlinkSync(outside, path.join(t.home, 'adapter-candidates', 'b'.repeat(64)));
  assert.equal(A.safeDir(t.home, 'b'.repeat(64)), null);
});

test('multiple pending nights retain distinct immutable candidates and never replace a verified fallback', async () => {
  const t = setup(); await t.ws._finish();
  const first = fs.readdirSync(path.join(t.home, 'adapter-candidates')).find(x => x !== 'a'.repeat(64));
  fs.writeFileSync(path.join(t.home, 'adapter', 'adapter_model.safetensors'), 'night two weights');
  fs.writeFileSync(path.join(t.home, 'state.json'), JSON.stringify({ nights: 3, last_night: { id: 'night-two', date: '2026-10-30', reverted: false } }));
  fs.writeFileSync(path.join(t.home, 'cards.jsonl'), JSON.stringify({ night: 2, status: 'held_out', q: 'Second?', a: 'Different' }));
  t.ws.night = { status: 'done', date: '2026-10-30', night: 3, day: 2, reverted: false }; t.ws.active = true; await t.ws._finish();
  const ids = fs.readdirSync(path.join(t.home, 'adapter-candidates'));
  assert.equal(ids.length, 3); assert.ok(ids.includes(first));
  assert.equal(fs.readFileSync(path.join(t.home, 'adapter.prev.gguf'), 'utf8'), 'previous');
  assert.equal(t.ws.currentLora(), t.fallback);
});

test('definite failed check rejects candidate; incomplete results and wake during a check remain pending', async () => {
  const failed = setup(); failed.setVerdict({ ...good, ok: false, held_on: 0, held_off: 1 }); await failed.ws._finish();
  const id = fs.readdirSync(path.join(failed.home, 'adapter-candidates')).find(x => x !== 'a'.repeat(64));
  assert.equal(A.read(path.join(failed.home, 'adapter-candidates', id, 'record.json')).status, 'rejected');
  assert.equal(failed.ws.currentLora(), failed.fallback);
  const incomplete = setup(); incomplete.setVerdict({ ok: true }); await incomplete.ws._finish();
  const incId = fs.readdirSync(path.join(incomplete.home, 'adapter-candidates')).find(x => x !== 'a'.repeat(64));
  assert.equal(A.read(path.join(incomplete.home, 'adapter-candidates', incId, 'record.json')).status, 'pending');
  const cancel = setup(); let resolve, started;
  const inFlight = new Promise(r => { resolve = r; }), checking = new Promise(r => { started = r; });
  cancel.ws.o.privateChecker.check = () => { started(); return inFlight; };
  const finished = cancel.ws._finish(); await checking; await cancel.ws.wake(); resolve({ ...good, processStopped: true }); await finished;
  const cancelId = fs.readdirSync(path.join(cancel.home, 'adapter-candidates')).find(x => x !== 'a'.repeat(64));
  assert.equal(A.read(path.join(cancel.home, 'adapter-candidates', cancelId, 'record.json')).status, 'pending');
  assert.equal(cancel.ws.currentLora(), cancel.fallback);
});

test('a failed manifest write leaves a passed candidate recoverable without replacing fallback', async () => {
  const t = setup(); t.setVerdict(good); const promote = A.promote; A.promote = () => { throw Error('disk full'); };
  try { await t.ws._finish(); } finally { A.promote = promote; }
  assert.equal(t.ws.currentLora(), t.fallback);
  t.ws.night = null; t.ws.active = true; await t.ws._finish();
  assert.match(t.ws.currentLora(), /adapter-candidates/); assert.equal(t.checks.length, 1);
});

test('unbound legacy files are preserved and never selected, even with a success sidecar', () => {
  const t = setup(); fs.writeFileSync(path.join(t.home, 'accepted-adapters.json'), '{}');
  assert.equal(t.ws.currentLora(), '');
  assert.equal(fs.readFileSync(path.join(t.home, 'adapter.prev.gguf'), 'utf8'), 'previous');
});

test('missing held-out evidence prevents candidate conversion', async () => {
  const t = setup(); fs.writeFileSync(path.join(t.home, 'cards.jsonl'), '');
  await t.ws._stageCandidate();
  assert.deepEqual(fs.readdirSync(path.join(t.home, 'adapter-candidates')), ['a'.repeat(64)]);
  assert.equal(t.ws.currentLora(), t.fallback);
});

test('unconfirmed private child exit blocks promotion and normal resume until ownership is recovered', async () => {
  const t = setup(); let idle = true;
  t.ws.o.privateChecker.ensureIdle = async () => ({ ok: idle, processStopped: idle, error: 'still running' });
  t.ws.o.privateChecker.check = async () => { idle = false; return { ...good, processStopped: false }; };
  await t.ws._finish();
  assert.equal(t.ws.privateBlocked, true); assert.equal(t.ws.active, true);
  assert.equal(t.calls.length, 0); assert.equal(t.ws.currentLora(), t.fallback);
  const id = fs.readdirSync(path.join(t.home, 'adapter-candidates')).find(x => x !== 'a'.repeat(64));
  assert.equal(A.read(path.join(t.home, 'adapter-candidates', id, 'record.json')).status, 'pending');
  idle = true; await t.ws.wake();
  for (let i = 0; i < 100 && t.ws.active; i++) await new Promise(r => setTimeout(r, 5));
  assert.equal(t.ws.active, false); assert.equal(t.calls.at(-1), t.fallback);
});

test('public built-in model start and resume fail closed when private ownership is unresolved', async () => {
  const { Builtin } = require('../src/runtime/builtin');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'private-gate-')); roots.push(root);
  let allowed = false, launches = 0;
  const checker = { ensureIdle: async () => ({ ok: allowed, processStopped: allowed, error: 'owned check still active' }) };
  const b = new Builtin({ root, platform, privateChecker: checker });
  b._launch = async () => { launches++; return { ok: true }; };
  assert.equal((await b.start()).phase, 'error'); assert.equal(launches, 0);
  b.running = true; b.server = { start: async () => { launches++; return { ok: true }; } };
  assert.equal((await b.resume('')).ok, false); assert.equal(launches, 0);
});

test('a stop during private recovery prevents a late public launch', async () => {
  const { Builtin } = require('../src/runtime/builtin');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'private-gate-')); roots.push(root);
  let release, entered; const wait = new Promise(r => { release = r; }), began = new Promise(r => { entered = r; }); let launches = 0;
  const b = new Builtin({ root, platform, privateChecker: { ensureIdle: () => { entered(); return wait; } } });
  b._launch = async () => { launches++; return { ok: true }; };
  const start = b.start(); await began; await b.stop(); release({ ok: true, processStopped: true }); await start;
  assert.equal(launches, 0); assert.equal(b.state().phase, 'off');
});

test('older published generations are not retried after later promotions', async () => {
  const t = setup(); const base = A.baseIdentity(t.root, t.hf);
  for (let day = 1; day <= 3; day++) {
    const date = '2026-10-' + String(28 + day);
    fs.writeFileSync(path.join(t.home, 'state.json'), JSON.stringify({ nights: day + 1, last_night: { id: 'night-' + day, date, reverted: false } }));
    fs.writeFileSync(path.join(t.home, 'adapter', 'adapter_model.safetensors'), 'weights-' + day);
    fs.writeFileSync(path.join(t.home, 'cards.jsonl'), JSON.stringify({ night: day, status: 'held_out', q: 'Q' + day, a: 'A' + day }));
    t.ws.night = { status: 'done', date, night: day + 1, day, reverted: false }; await t.ws._stageCandidate();
    const c = A.pending(t.home, base); assert.ok(c);
    c.rec.status = 'accepted'; c.rec.served = good; A.atomic(path.join(c.dir, 'record.json'), c.rec); A.promote(t.home, c);
  }
  const manifest = A.manifest(t.home); assert.equal(manifest.published.length, 4);
  assert.equal(A.pending(t.home, base), null);
  fs.writeFileSync(path.join(t.home, 'adapter-candidates', manifest.current, 'adapter.gguf'), 'broken');
  assert.equal(t.ws.currentLora(), path.join(t.home, 'adapter-candidates', manifest.previous, 'adapter.gguf'));
});

test('source HF weights and config changes invalidate a previously accepted candidate', () => {
  const t = setup(); assert.equal(t.ws.currentLora(), t.fallback);
  fs.writeFileSync(path.join(t.hf, 'model.safetensors'), 'changed source weights');
  assert.equal(t.ws.currentLora(), '');
  assert.equal(fs.existsSync(t.fallback), true);
});

test('atomic manifest fsync failure before rename preserves the old manifest and removes its temporary file', () => {
  const t = setup(), file = path.join(t.home, 'accepted-adapters.json');
  const old = fs.readFileSync(file, 'utf8'), original = fs.fsyncSync; let called = 0;
  try {
    fs.fsyncSync = () => { called++; const e = new Error('disk sync failed'); e.code = 'EIO'; throw e; };
    assert.throws(() => A.atomic(file, { version: 1, current: 'b'.repeat(64) }), /disk sync failed/);
  } finally { fs.fsyncSync = original; }
  assert.equal(called, 1); assert.equal(fs.readFileSync(file, 'utf8'), old);
  assert.equal(fs.readdirSync(t.home).some(n => n.startsWith('accepted-adapters.json.tmp-')), false);
  assert.equal(t.ws.currentLora(), t.fallback);
  A.atomic(file, { version: 1, current: 'a'.repeat(64) });
  assert.equal(t.ws.currentLora(), t.fallback);
});

test('older pending or recovered passes cannot replace a newer accepted night', async () => {
  const t = setup(), identity = A.baseIdentity(t.root, t.hf);
  await t.ws._stageCandidate();
  const old = A.pending(t.home, identity); assert.equal(old.rec.date, '2026-10-29');
  fs.writeFileSync(path.join(t.home, 'state.json'), JSON.stringify({ nights: 3, last_night: { id: 'night-two', date: '2026-10-30', reverted: false } }));
  fs.writeFileSync(path.join(t.home, 'adapter', 'adapter_model.safetensors'), 'newer weights');
  fs.writeFileSync(path.join(t.home, 'cards.jsonl'), JSON.stringify({ night: 2, status: 'held_out', q: 'Q2', a: 'A2' }));
  t.ws.night = { status: 'done', date: '2026-10-30', night: 3, day: 2, reverted: false };
  await t.ws._stageCandidate();
  const newest = A.pending(t.home, identity); assert.equal(newest.rec.date, '2026-10-30');
  newest.rec.status = 'accepted'; newest.rec.served = good; A.atomic(path.join(newest.dir, 'record.json'), newest.rec); A.promote(t.home, newest);
  assert.equal(t.ws.currentLora(), newest.adapter);
  assert.equal(A.pending(t.home, identity), null, 'older pending must not be retried');
  old.rec.status = 'accepted'; old.rec.served = good; A.atomic(path.join(old.dir, 'record.json'), old.rec);
  A.promote(t.home, old);
  assert.equal(t.ws.currentLora(), newest.adapter, 'direct or recovered old pass must not roll back');
});

test('same-night recovery accepts the later candidate and refuses an earlier one', async () => {
  const t = setup(), identity = A.baseIdentity(t.root, t.hf);
  await t.ws._stageCandidate();
  const earlier = A.pending(t.home, identity);
  earlier.rec.created = '2026-10-29T01:00:00.000Z'; A.atomic(path.join(earlier.dir, 'record.json'), earlier.rec);
  fs.writeFileSync(path.join(t.home, 'adapter', 'adapter_model.safetensors'), 'different same-night weights');
  await t.ws._stageCandidate();
  const candidates = fs.readdirSync(path.join(t.home, 'adapter-candidates')).map(id => A.inspect(t.home, id, identity)).filter(c => c && c.id !== earlier.id && c.id !== 'a'.repeat(64));
  assert.equal(candidates.length, 1); const later = candidates[0];
  later.rec.created = '2026-10-29T02:00:00.000Z'; later.rec.status = 'accepted'; later.rec.served = good;
  A.atomic(path.join(later.dir, 'record.json'), later.rec);
  assert.equal(A.pending(t.home, identity).id, later.id);
  A.promote(t.home, later); assert.equal(t.ws.currentLora(), later.adapter);
  earlier.rec.status = 'accepted'; earlier.rec.served = good; A.atomic(path.join(earlier.dir, 'record.json'), earlier.rec);
  assert.equal(A.promote(t.home, earlier), false); assert.equal(t.ws.currentLora(), later.adapter);
});

test('night counter or calendar regressions remain pending, even if the formerly current file disappears', async () => {
  const t = setup(), identity = A.baseIdentity(t.root, t.hf);
  await t.ws._stageCandidate(); const newer = A.pending(t.home, identity);
  newer.rec.status = 'accepted'; newer.rec.served = good; A.atomic(path.join(newer.dir, 'record.json'), newer.rec); A.promote(t.home, newer);
  fs.writeFileSync(path.join(t.home, 'state.json'), JSON.stringify({ nights: 1, last_night: { id: 'reset', date: '2026-10-30', reverted: false } }));
  fs.writeFileSync(path.join(t.home, 'adapter', 'adapter_model.safetensors'), 'reset weights');
  fs.writeFileSync(path.join(t.home, 'cards.jsonl'), JSON.stringify({ night: 1, status: 'held_out', q: 'Q', a: 'A' }));
  t.ws.night = { status: 'done', date: '2026-10-30', night: 1, day: 1, reverted: false }; await t.ws._stageCandidate();
  assert.equal(A.pending(t.home, identity), null);
  const resetId = fs.readdirSync(path.join(t.home, 'adapter-candidates')).find(id => !['a'.repeat(64), newer.id].includes(id));
  const reset = A.inspect(t.home, resetId, identity); reset.rec.status = 'accepted'; reset.rec.served = good; A.atomic(path.join(reset.dir, 'record.json'), reset.rec);
  fs.unlinkSync(newer.adapter);
  assert.equal(A.promote(t.home, reset), false, 'durable watermark outlives its artifact');
  assert.equal(t.ws.currentLora(), t.fallback);
  assert.equal(A.newer({ ...reset.rec, night_number: 3, date: '2026-10-28' }, newer.rec), false, 'a backwards calendar is also incomparable');
});

test('incomparable pending nights after a clock or state reset are not guessed into an order', async () => {
  const t = setup(), identity = A.baseIdentity(t.root, t.hf);
  for (const [number, date, day] of [[3, '2026-10-30', 2], [4, '2026-10-29', 1]]) {
    fs.writeFileSync(path.join(t.home, 'state.json'), JSON.stringify({ nights: number, last_night: { id: 'n' + number, date, reverted: false } }));
    fs.writeFileSync(path.join(t.home, 'adapter', 'adapter_model.safetensors'), 'weights-' + number);
    fs.writeFileSync(path.join(t.home, 'cards.jsonl'), JSON.stringify({ night: day, status: 'held_out', q: 'Q', a: 'A' }));
    t.ws.night = { status: 'done', date, night: number, day, reverted: false }; await t.ws._stageCandidate();
  }
  assert.equal(A.pending(t.home, identity), null); assert.equal(t.ws.currentLora(), t.fallback);
});

test('startup and check-ins select accepted, previous, then base while legacy files stay quarantined', async () => {
  const t = setup();
  const legacy = path.join(t.home, 'adapter.gguf'); fs.writeFileSync(legacy, 'unbound legacy');
  fs.writeFileSync(legacy + '.json', JSON.stringify({ base_hf_id: C.SLEEP_HF_REPO, served: { ok: true } }));
  t.ws.hooks.pauseModel = async () => ({}); t.ws.hooks.checkin = async () => ({ reply: 'NOTHING' });
  t.ws.since = Date.now() - 3700e3; t.ws.wakeReq = false;
  assert.equal(t.ws.currentLora(), t.fallback); await t.ws._maybeCheckin(); assert.equal(t.calls.at(-1), t.fallback);
  t.setVerdict(good); await t.ws._finish(); const newer = t.ws.currentLora(); assert.notEqual(newer, t.fallback);
  t.ws.lastCheckinAt = 0; await t.ws._maybeCheckin(); assert.equal(t.calls.at(-1), newer);
  fs.writeFileSync(newer, 'tampered'); assert.equal(t.ws.currentLora(), t.fallback);
  t.ws.lastCheckinAt = 0; await t.ws._maybeCheckin(); assert.equal(t.calls.at(-1), t.fallback);
  fs.writeFileSync(t.fallback, 'tampered'); assert.equal(t.ws.currentLora(), '');
  t.ws.lastCheckinAt = 0; await t.ws._maybeCheckin(); assert.equal(t.calls.at(-1), '');
  assert.equal(fs.readFileSync(legacy, 'utf8'), 'unbound legacy'); assert.ok(fs.existsSync(legacy + '.json'));
});

test('missing HF identity refuses pending conversion and retains all old unbound files', async () => {
  const t = setup();
  const old = path.join(t.home, 'adapter.gguf'); fs.writeFileSync(old, 'unbound old');
  fs.writeFileSync(old + '.json', JSON.stringify({ base_hf_id: C.SLEEP_HF_REPO, served: { ok: null } }));
  fs.unlinkSync(path.join(t.hf, 'config.json'));
  assert.equal(t.ws.currentLora(), ''); await t.ws._finish();
  assert.equal(t.calls.at(-1), ''); assert.equal(t.checks.length, 0);
  assert.equal(fs.readFileSync(old, 'utf8'), 'unbound old');
  assert.ok(fs.existsSync(path.join(t.home, 'adapter.prev.gguf')));
});

test('conversion uses the published immutable generation once, never a legacy fallback', async () => {
  const t = setup(); const generation = path.join(t.home, 'adapters', 'night-one'); fs.mkdirSync(generation, { recursive: true });
  fs.writeFileSync(path.join(generation, 'adapter_model.safetensors'), 'generation weights');
  fs.writeFileSync(path.join(t.home, 'adapters.json'), JSON.stringify({ version: 1, current: 'adapters/night-one', previous: 'adapter' }));
  const calls = []; t.ws.o.run = async (_, args) => { calls.push(args); fs.writeFileSync(args[args.indexOf('--outfile') + 1], 'candidate'); };
  await t.ws._stageCandidate(); await t.ws._stageCandidate();
  assert.equal(calls.length, 1); assert.equal(calls[0][1], generation);
  const c = A.pending(t.home, A.baseIdentity(t.root, t.hf)); assert.equal(c.rec.generation, 'adapters/night-one');
});

test('missing published generation fails closed instead of converting legacy weights', async () => {
  const t = setup(); fs.writeFileSync(path.join(t.home, 'adapters.json'), JSON.stringify({ version: 1, current: 'adapters/missing', previous: 'adapter' }));
  let calls = 0; t.ws.o.run = async () => { calls++; };
  await t.ws._finish(); assert.equal(calls, 0); assert.equal(t.ws.currentLora(), t.fallback);
  assert.match(fs.readFileSync(t.ws.p.events, 'utf8'), /convert_failed/);
});

} // run the complete candidate lifecycle matrix for Windows and built-in Mac
