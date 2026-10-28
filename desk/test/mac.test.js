'use strict';
// The built-in model on macOS (Apple silicon): asset picking, unpacking paths, llama-server arguments, the Platform defaults for
// a Mac with / without Ben's assistant, and the "Sleep is not available on this Mac yet" fallback. No Mac is needed: everything is
// driven with platform 'darwin' passed in, fake releases, and a tiny real .tar.gz made with the tar on this machine.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const C = require('../src/runtime/constants');
const R = require('../src/runtime/releases');
const { ChatInstaller, findFile, tarExe, tarArgs } = require('../src/runtime/install');
const { buildArgs, reclaimPort, parseLsofPid, lsofArgs, isLlamaServerComm } = require('../src/runtime/llamaserver');
const { Builtin } = require('../src/runtime/builtin');
const { UnavailableSleep, shouldAutoSleep } = require('../src/sleep');
const { DEFAULT_SETTINGS, applyPresetDefaults } = require('../src/store');
const P = require('../renderer/platform');

const tmp = (n) => fs.mkdtempSync(path.join(os.tmpdir(), n));
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const mac = (tag, at, extra) => ({ tag_name: tag, published_at: at, draft: false, prerelease: false, assets: [
  { name: C.llamaAssetName(tag, 'metal', 'darwin'), browser_download_url: 'https://x/' + tag + '/llama-' + tag + '-bin-macos-arm64.tar.gz', size: 16000000, digest: 'sha256:' + 'e'.repeat(64) },
  { name: C.llamaAssetName(tag, 'vulkan'), browser_download_url: 'https://x/' + tag + '/win.zip', size: 1 }], ...(extra || {}) });

// ---- asset name and picking ---------------------------------------------------------------------------------------
test('mac asset name is the arm64 tar.gz (no zip for macOS); the Windows names are unchanged', () => {
  assert.strictEqual(C.llamaAssetName('b11945', 'metal', 'darwin'), 'llama-b11945-bin-macos-arm64.tar.gz');
  assert.strictEqual(C.llamaAssetName('b11945', 'vulkan'), 'llama-b11945-bin-win-vulkan-x64.zip');
  assert.strictEqual(C.llamaAssetName('b11945', 'cpu', 'win32'), 'llama-b11945-bin-win-cpu-x64.zip');
  assert.deepStrictEqual(C.llamaFlavors('darwin'), ['metal']); assert.deepStrictEqual(C.llamaFlavors('win32'), ['vulkan', 'cpu']);
  assert.strictEqual(C.llamaExeName('darwin'), 'llama-server'); assert.strictEqual(C.llamaExeName('win32'), 'llama-server.exe');
});

test('mac asset pick: newest macos-arm64 release at or above the LFM3 floor (b11938, 2026-10-27T23:57:45Z), drafts skipped', () => {
  const rels = [mac('b11937', '2026-10-27T22:00:00Z'), mac('b11938', '2026-10-27T23:57:45Z'), mac('b11945', '2026-10-28T09:00:00Z'), mac('b11991', '2026-10-29T10:00:00Z', { draft: true })];
  assert.strictEqual(R.pickLlamaAsset([mac('b11946', '2026-10-28T09:00:00Z', { prerelease: true })], { platform: 'darwin' }).tag, 'b11946'); // llama.cpp marks every release a prerelease
  const a = R.pickLlamaAsset(rels, { platform: 'darwin' });
  assert.strictEqual(a.tag, 'b11945'); assert.strictEqual(a.name, 'llama-b11945-bin-macos-arm64.tar.gz'); assert.strictEqual(a.url, 'https://x/b11945/llama-b11945-bin-macos-arm64.tar.gz'); assert.strictEqual(a.sha256, 'e'.repeat(64));
  assert.strictEqual(R.pickLlamaAsset([rels[0]], { platform: 'darwin' }), null);        // b11937 predates LFM3
  assert.strictEqual(R.pickLlamaAsset([rels[1]], { platform: 'darwin' }).tag, 'b11938'); // the floor release itself qualifies
  // a newest release without the mac asset falls through to the previous one
  const noMac = { ...mac('b12000', '2026-10-30T00:00:00Z'), assets: [{ name: 'llama-b12000-bin-win-vulkan-x64.zip', browser_download_url: 'u', size: 1 }] };
  assert.strictEqual(R.pickLlamaAsset([noMac, rels[2]], { platform: 'darwin' }).tag, 'b11945');
  // the default platform is still Windows, with the Windows asset
  assert.strictEqual(R.pickLlamaAsset(rels, { flavor: 'vulkan' }).name, 'llama-b11945-bin-win-vulkan-x64.zip');
});

// ---- unpacking ----------------------------------------------------------------------------------------------------
test('mac extraction: /usr/bin/tar -xf <archive> -C <dest>; Windows keeps System32\\tar.exe; others plain tar', () => {
  assert.strictEqual(tarExe('darwin'), '/usr/bin/tar'); assert.strictEqual(tarExe('linux'), 'tar');
  assert.deepStrictEqual(tarArgs('/a/x.tar.gz', '/d'), ['-xf', '/a/x.tar.gz', '-C', '/d']);
  const real = process.env.SystemRoot; process.env.SystemRoot = 'C:\\WINDOWS';
  try { assert.strictEqual(tarExe('win32'), path.join('C:\\WINDOWS', 'System32', 'tar.exe')); } finally { if (real === undefined) delete process.env.SystemRoot; else process.env.SystemRoot = real; }
});

// A real tiny archive shaped like the official one: llama-bNNNN/llama-server next to lib*.dylib
function fakeMacTarball(dir, tag) {
  const root = path.join(dir, 'src', 'llama-' + tag); fs.mkdirSync(root, { recursive: true });
  fs.writeFileSync(path.join(root, 'llama-server'), '#!/bin/sh\n'); fs.writeFileSync(path.join(root, 'libllama.dylib'), 'x'); fs.writeFileSync(path.join(root, 'libggml.dylib'), 'x');
  const out = path.join(dir, 'asset.tar.gz');
  execFileSync('tar', ['-czf', out, '-C', path.join(dir, 'src'), 'llama-' + tag]);
  return fs.readFileSync(out);
}
const GGUF = Buffer.from('GGUF-fake-model');
function macFetch(releases, tarball, seen) {
  return async (url) => {
    seen.push(String(url));
    if (/api\.github\.com\/repos\/ggml-org\/llama\.cpp\/releases/.test(url)) return Response.json(releases);
    if (/huggingface\.co\/api\/models/.test(url)) return Response.json([{ type: 'file', path: C.MODEL_FILE, size: GGUF.length, lfs: { oid: sha(GGUF), size: GGUF.length } }]);
    if (/\.tar\.gz$/.test(url)) return new Response(tarball, { status: 200, headers: { 'content-length': String(tarball.length) } });
    if (/\.gguf$/.test(url)) return new Response(GGUF, { status: 200, headers: { 'content-length': String(GGUF.length) } });
    return new Response('no', { status: 404 });
  };
}
const releasesFor = (tarball) => { const r = [mac('b11945', '2026-10-28T09:00:00Z')]; r[0].assets[0].digest = 'sha256:' + sha(tarball); return r; };

test('mac install: picks the tar.gz, unpacks with the real tar, finds llama-server beside its dylibs, strips quarantine, saves state under "metal"', async () => {
  const d = tmp('mac-inst-'); const seen = []; const un = [];
  const tarball = fakeMacTarball(d, 'b11945');
  const prog = [];
  const inst = new ChatInstaller({ dir: path.join(d, 'runtime'), platform: 'darwin', fetch: macFetch(releasesFor(tarball), tarball, seen), unquarantine: async (dir, exe) => { un.push([dir, exe]); }, onProgress: (p) => prog.push(p.stage) });
  assert.strictEqual(inst.installed(), false);
  const l = await inst.ensureLlama();                     // flavor defaults to metal on a Mac
  assert.strictEqual(l.flavor, 'metal'); assert.strictEqual(l.tag, 'b11945');
  assert.strictEqual(l.exe, path.join(d, 'runtime', 'llama-b11945-metal', 'llama-b11945', 'llama-server'));
  assert.ok(fs.existsSync(path.join(path.dirname(l.exe), 'libllama.dylib')), 'the dylibs stay next to the binary');
  assert.deepStrictEqual(un, [[path.join(d, 'runtime', 'llama-b11945-metal'), l.exe]]);
  assert.ok(seen.includes('https://x/b11945/llama-b11945-bin-macos-arm64.tar.gz'));
  assert.ok(!fs.existsSync(path.join(d, 'runtime', 'llama-b11945-bin-macos-arm64.tar.gz')), 'the archive is removed after unpacking');
  assert.strictEqual(inst.llamaExe('metal').exe, l.exe);
  const m = await inst.ensureModel();                      // the same resumable download as Windows
  assert.strictEqual(fs.readFileSync(m.file).toString(), GGUF.toString());
  assert.strictEqual(inst.installed(), true);
  assert.ok(prog.includes('llama') && prog.includes('model'));
  assert.strictEqual(findFile(path.join(d, 'runtime'), 'llama-server'), l.exe);
});

test('mac install: no qualifying release gives a plain-English error', async () => {
  const inst = new ChatInstaller({ dir: tmp('mac-none-'), platform: 'darwin', fetch: async () => Response.json([mac('b11937', '2026-10-27T22:00:00Z')]) });
  await assert.rejects(() => inst.ensureLlama(), /No llama\.cpp build for macOS \(Apple silicon\) from 2026-10-27 or later/);
});

test('windows install message and flavor default are unchanged', async () => {
  const inst = new ChatInstaller({ dir: tmp('win-none-'), platform: 'win32', fetch: async () => Response.json([]) });
  await assert.rejects(() => inst.ensureLlama('vulkan'), /No llama\.cpp vulkan build for Windows from 2026-10-27 or later was found/);
  assert.strictEqual(inst.installed(), false);
});

// ---- llama-server arguments -------------------------------------------------------------------------------------------
test('mac llama-server args are the Windows ones with full Metal offload: 8192 ctx, one slot, --jinja, -ngl 99', () => {
  const a = buildArgs({ model: '/m/LFM3.gguf', flavor: 'metal' });
  assert.deepStrictEqual(a, ['-m', '/m/LFM3.gguf', '--host', '127.0.0.1', '--port', '18090', '-c', '8192', '-np', '1', '--jinja', '--no-webui', '-ngl', '99']);
  assert.deepStrictEqual(buildArgs({ model: '/m/LFM3.gguf', flavor: 'vulkan' }), a);            // identical to the Windows graphics build
  assert.strictEqual(buildArgs({ model: 'M', flavor: 'cpu' }).slice(-2).join(' '), '-ngl 0');   // Windows CPU build unchanged
  assert.strictEqual(C.CTX, 8192);
});

// ---- orphaned server on the port (macOS) -------------------------------------------------------------------------------------
test('mac: an orphaned llama-server on :18090 is found with lsof and killed, other programs are left alone', async () => {
  assert.deepStrictEqual(lsofArgs(18090), ['-nP', '-iTCP:18090', '-sTCP:LISTEN', '-t']);
  assert.strictEqual(parseLsofPid('4321\n'), 4321); assert.strictEqual(parseLsofPid(''), 0);
  assert.strictEqual(isLlamaServerComm('/Users/e/Library/Application Support/Premonition/runtime/llama-b11945-metal/llama-b11945/llama-server\n'), true);
  assert.strictEqual(isLlamaServerComm('/Applications/Safari.app/Contents/MacOS/Safari'), false);
  const calls = [];
  const ex = (comm) => async (cmd, args) => { calls.push(cmd + ' ' + args.join(' ')); return cmd.endsWith('lsof') ? '4321\n' : cmd.endsWith('ps') ? comm + '\n' : ''; };
  assert.strictEqual(await reclaimPort(18090, ex('/x/llama-server'), 'darwin'), 4321); assert.ok(calls.includes('/bin/kill 4321'));
  calls.length = 0;
  assert.strictEqual(await reclaimPort(18090, ex('/x/node'), 'darwin'), 0); assert.ok(!calls.some((c) => c.startsWith('/bin/kill')));
  assert.strictEqual(await reclaimPort(18090, async () => '', 'darwin'), 0);
});

// ---- Platform defaults ----------------------------------------------------------------------------------------------------
test('Platform: a Mac without the local assistant gets the built-in model; Ben\'s Mac and an unknown value keep the gateway', () => {
  const emma = { hasLocalAssistant: false }, ben = { hasLocalAssistant: true };
  assert.strictEqual(P.features('darwin', emma).builtin, true); assert.strictEqual(P.features('darwin', ben).builtin, false); assert.strictEqual(P.features('darwin').builtin, false);
  assert.strictEqual(P.defaultPreset('darwin', emma).id, 'builtin'); assert.strictEqual(P.defaultPreset('darwin', ben).id, 'premonition'); assert.strictEqual(P.defaultPreset('darwin').id, 'premonition');
  assert.deepStrictEqual(P.presetsFor('darwin', emma).map((x) => x.id), ['premonition', 'llamacpp', 'builtin']);
  assert.deepStrictEqual(P.presetsFor('darwin', ben).map((x) => x.id), ['premonition', 'llamacpp']);
  // the flag never changes other systems
  assert.strictEqual(P.features('win32', ben).builtin, true); assert.strictEqual(P.features('linux', emma).builtin, false);
  assert.strictEqual(P.defaultPreset('linux', emma).id, 'premonition'); assert.strictEqual(P.defaultPreset('win32', ben).id, 'builtin');
  // the permission card and Mac keys stay as they were
  assert.strictEqual(P.features('darwin', emma).perms, true); assert.strictEqual(P.needsPermsStep('darwin', false), true);
});

test('Platform: sleep is off (with the honest note) only on a Mac running the built-in model', () => {
  const emma = { hasLocalAssistant: false };
  const g = P.settingsGating('darwin', emma);
  assert.strictEqual(g.sleepUnavailable, true); assert.strictEqual(g.sleepNote, 'Sleep is not available on this Mac yet.'); assert.strictEqual(g.showSleepButton, false); assert.strictEqual(g.showPermRow, true);
  assert.strictEqual(P.features('darwin', emma).sleep, false);
  for (const [p, o] of [['darwin', { hasLocalAssistant: true }], ['darwin', undefined], ['win32', undefined], ['win32', emma], ['linux', undefined]]) {
    const x = P.settingsGating(p, o);
    assert.strictEqual(x.sleepUnavailable, false, p); assert.strictEqual(x.showSleepButton, true, p); assert.strictEqual(P.features(p, o).sleep, true, p);
  }
});

test('store defaults follow the preset main.js passes in (a saved settings file still wins over them)', () => {
  const keep = { ...DEFAULT_SETTINGS };
  try {
    applyPresetDefaults(P.defaultPreset('darwin', { hasLocalAssistant: false }));
    assert.strictEqual(DEFAULT_SETTINGS.gatewayUrl, 'http://127.0.0.1:18091/v1'); assert.strictEqual(DEFAULT_SETTINGS.model, 'auto'); assert.strictEqual(DEFAULT_SETTINGS.modelFast, 'fast');
    assert.strictEqual(DEFAULT_SETTINGS.compactTokens, 4500); assert.strictEqual(DEFAULT_SETTINGS.maxToolChars, 3000);
    applyPresetDefaults(P.defaultPreset('darwin', { hasLocalAssistant: true }));
    assert.strictEqual(DEFAULT_SETTINGS.gatewayUrl, 'http://127.0.0.1:8090/v1'); assert.strictEqual(DEFAULT_SETTINGS.model, 'qwen36-auto'); assert.strictEqual(DEFAULT_SETTINGS.compactTokens, 24000);
  } finally { Object.assign(DEFAULT_SETTINGS, keep); }
});

// ---- sleep stub ---------------------------------------------------------------------------------------------------------------------
test('UnavailableSleep: never starts, never writes, says so in plain words, and auto-sleep cannot fire', async () => {
  const home = path.join(tmp('nosleep-'), 'sleep-unavailable');
  const s = new UnavailableSleep({ getSettings: () => ({}), home });
  assert.strictEqual(s.available().ok, false); assert.strictEqual(s.available().reason, 'Sleep is not available on this Mac yet.');
  assert.deepStrictEqual(s.start({ budgetS: 3600 }), { ok: false, error: 'Sleep is not available on this Mac yet.' });
  assert.strictEqual(s.statusLine(), 'Sleep is not available on this Mac yet.'); assert.strictEqual(s.status().sleeping, false);
  assert.strictEqual(s.needsRuntime(), false); assert.strictEqual(s.currentLora(), '');
  assert.strictEqual((await s.wake()).ok, true);
  assert.strictEqual(fs.existsSync(home), false);
  const d = shouldAutoSleep({ settings: { autoSleep: true }, now: new Date('2026-10-29T02:00:00'), available: s.available().ok, idleMs: 9e9, systemIdleMs: 9e9, runActive: false, gatewayBusy: false, windowFocused: false, onBattery: false });
  assert.strictEqual(d.sleep, false);
});

// ---- the Builtin on a Mac ---------------------------------------------------------------------------------------------------------
test('Builtin on a Mac: downloads, starts llama-server from the unpacked folder with Metal, no CPU fallback, then the gateway', async () => {
  const d = tmp('mac-bi-'); const seen = [];
  const tarball = fakeMacTarball(d, 'b11945');
  const started = []; const states = [];
  const makeServer = (o) => ({ o, url: () => 'http://127.0.0.1:1', start: async () => { started.push({ exe: o.exe, model: o.model, flavor: o.flavor, cwd: o.cwd, args: buildArgs(o) }); return { ok: true }; }, stop: async () => {} });
  const b = new Builtin({ root: path.join(d, 'root'), platform: 'darwin', fetch: macFetch(releasesFor(tarball), tarball, seen), unquarantine: async () => {}, makeServer, gatewayPort: 0, skipDiary: () => true, onState: (s) => states.push(s.phase) });
  assert.strictEqual(b.state().flavor, 'metal'); assert.strictEqual(b.needsDownload(), true);
  const st = await b.start();
  assert.strictEqual(st.phase, 'ready', st.error);
  assert.strictEqual(started.length, 1); assert.strictEqual(started[0].flavor, 'metal');
  assert.strictEqual(path.basename(started[0].exe), 'llama-server'); assert.strictEqual(started[0].cwd, path.dirname(started[0].exe));
  assert.strictEqual(started[0].args.slice(-2).join(' '), '-ngl 99');
  assert.ok(states.includes('downloading') && states.includes('starting'));
  assert.strictEqual(b.needsDownload(), false);
  await b.stop();
});
