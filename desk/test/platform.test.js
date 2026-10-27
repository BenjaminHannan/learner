'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const P = require('../renderer/platform');
const { helperInvocation, candidates, isBrowserApp } = require('../src/tools/screen');
const { migrateUserData, MARKER } = require('../src/migrate');
const { Store, DEFAULT_SETTINGS } = require('../src/store');
const { Warmer, buildWarmBody } = require('../src/warm');
const { makeIco, decodePng } = require('../scripts/make-ico');

test('helper: Mac runs the binary, Windows runs deskhelper.ps1 through powershell', () => {
  assert.deepStrictEqual(P.helperCommand('darwin', '/r/deskhelper'), { cmd: '/r/deskhelper', prefix: [] });
  const w = P.helperCommand('win32', 'C:\\r\\deskhelper.ps1');
  assert.strictEqual(w.cmd, 'powershell.exe');
  assert.deepStrictEqual(w.prefix, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'C:\\r\\deskhelper.ps1']);
  assert.deepStrictEqual(helperInvocation('C:\\r\\deskhelper.ps1', ['look', '--max', '80'], 'win32').args.slice(-3), ['look', '--max', '80']);
  assert.strictEqual(helperInvocation('/r/deskhelper', ['check'], 'darwin').cmd, '/r/deskhelper');
  assert.strictEqual(P.helperFileName('win32'), 'deskhelper.ps1'); assert.strictEqual(P.helperFileName('darwin'), 'deskhelper');
});

test('helper lookup order per platform: settings path, resources, helper/, build/', () => {
  const win = candidates({ helperPath: 'X' }, 'R', 'win32').map((p) => path.basename(p));
  assert.deepStrictEqual(win, ['X', 'deskhelper.ps1', 'deskhelper.ps1', 'deskhelper.ps1']);
  const mac = candidates({}, null, 'darwin').map((p) => path.basename(p));
  assert.deepStrictEqual(mac, ['deskhelper', 'deskhelper']);
});

test('key mapping: cmd -> ctrl and option -> alt on Windows, untouched on Mac', () => {
  assert.strictEqual(P.mapKeys('win32', 'cmd+t'), 'ctrl+t');
  assert.strictEqual(P.mapKeys('win32', 'Command+Shift+T'), 'ctrl+shift+t');
  assert.strictEqual(P.mapKeys('win32', 'option+left'), 'alt+left');
  assert.strictEqual(P.mapKeys('win32', 'cmd+option+i'), 'ctrl+alt+i');
  assert.strictEqual(P.mapKeys('win32', 'return'), 'enter');
  assert.strictEqual(P.mapKeys('win32', 'delete'), 'backspace');
  assert.strictEqual(P.mapKeys('win32', 'cmd+q'), 'alt+f4');
  assert.strictEqual(P.mapKeys('win32', 'ctrl+cmd+a'), 'ctrl+a');
  assert.strictEqual(P.mapKeys('win32', 'fn+f5'), 'f5');
  assert.strictEqual(P.mapKeys('win32', 'cmd++'), 'ctrl+plus');
  assert.strictEqual(P.mapKeys('darwin', 'cmd+t'), 'cmd+t');
  assert.strictEqual(P.mapKeys('linux', 'cmd+t'), 'cmd+t');
  assert.strictEqual(P.mapKeys('win32', ''), '');
});

test('hotkey defaults: Ctrl+Space on Windows (Alt+Space is the window menu), Alt+Space elsewhere; labels per platform', () => {
  assert.strictEqual(P.defaultHotkey('win32'), 'Ctrl+Space');
  assert.strictEqual(P.defaultHotkey('darwin'), 'Alt+Space');
  assert.strictEqual(P.defaultHotkey('linux'), 'Alt+Space');
  assert.strictEqual(P.hotkeyLabel('darwin', 'Alt+Space'), 'Option+Space');
  assert.strictEqual(P.hotkeyLabel('win32', 'Control+Shift+K'), 'Ctrl+Shift+K');
  assert.strictEqual(P.hotkeyLabel('win32', ''), 'Off');
  // the store default follows the platform of the running process (Linux here)
  assert.strictEqual(DEFAULT_SETTINGS.hotkey, P.defaultHotkey(process.platform));
});

test('Settings gating: Windows hides the Mac permissions card (with a note) and keeps Sleep through its own runner', () => {
  const w = P.settingsGating('win32');
  assert.strictEqual(w.showPermRow, false); assert.match(w.permsNote, /Windows doesn't need extra permissions/);
  assert.strictEqual(w.showSleepGroup, true); assert.strictEqual(w.sleepWindows, true); assert.strictEqual(w.showSleepButton, true);
  const m = P.settingsGating('darwin');
  assert.strictEqual(m.showSleepGroup, true); assert.strictEqual(m.showPermRow, true); assert.strictEqual(m.sleepWindows, false); assert.strictEqual(m.permsNote, '');
  assert.strictEqual(P.settingsGating('linux').showSleepGroup, true); // the Linux e2e still drives Sleep
});

test('onboarding skips the Permissions step on Windows (Mac and the Linux e2e keep it)', () => {
  assert.strictEqual(P.needsPermsStep('win32', false), false);
  assert.strictEqual(P.needsPermsStep('darwin', false), true);
  assert.strictEqual(P.needsPermsStep('linux', false), false);
  assert.strictEqual(P.needsPermsStep('linux', true), true);
});

test('pill window: Mac is an all-Spaces panel, Windows a frameless screen-saver-level window with no panel type', () => {
  const m = P.pillOptions('darwin', 420, 300);
  assert.strictEqual(m.options.type, 'panel'); assert.strictEqual(m.allWorkspaces, true);
  const w = P.pillOptions('win32', 420, 300);
  assert.strictEqual('type' in w.options, false);
  assert.strictEqual(w.options.frame, false); assert.strictEqual(w.options.alwaysOnTop, true); assert.strictEqual(w.options.skipTaskbar, true);
  assert.strictEqual(w.options.focusable, false); assert.strictEqual(w.level, 'screen-saver'); assert.strictEqual(w.allWorkspaces, false); assert.strictEqual(w.hideInMissionControl, false);
  assert.deepStrictEqual(P.pillPosition({ x: 0, y: 0, width: 1920, height: 1040 }, 420), { x: 750, y: 6 });
  assert.deepStrictEqual(P.pillPosition({ x: 100, y: 25, width: 1440, height: 875 }, 420), { x: 610, y: 31 });
});

test('closing: Windows hides to the tray, Mac conceals only while browsers exist, off means quit', () => {
  assert.strictEqual(P.closeBehavior('win32', true, true), 'tray');
  assert.strictEqual(P.closeBehavior('win32', true, false), 'tray');
  assert.strictEqual(P.closeBehavior('darwin', true, true), 'conceal');
  assert.strictEqual(P.closeBehavior('darwin', true, false), 'hide');
  assert.strictEqual(P.closeBehavior('linux', true, true), 'hide');
  assert.strictEqual(P.closeBehavior('win32', false, true), 'quit');
  assert.strictEqual(P.features('win32').tray, true); assert.strictEqual(P.features('darwin').tray, false);
});

test('open at login: Windows starts us with --hidden, Mac uses openAsHidden', () => {
  assert.deepStrictEqual(P.loginItemOptions('win32', true), { openAtLogin: true, args: ['--hidden'] });
  assert.deepStrictEqual(P.loginItemOptions('darwin', false), { openAtLogin: false, openAsHidden: true });
  assert.strictEqual(P.startedHidden('win32', ['x.exe', '--hidden']), true);
  assert.strictEqual(P.startedHidden('win32', ['x.exe']), false);
  assert.strictEqual(P.startedHidden('darwin', ['x'], { wasOpenedAsHidden: true }), true);
  const wo = P.windowOptions('win32', '/i.png'); assert.strictEqual(wo.autoHideMenuBar, true); assert.strictEqual(wo.titleBarStyle, 'default');
  const mo = P.windowOptions('darwin', '/i.png'); assert.strictEqual(mo.titleBarStyle, 'hiddenInset'); assert.strictEqual(mo.icon, undefined);
});

test('open_app refuses browsers on Windows names too (msedge, chrome.exe, Internet Explorer), allows Notepad', () => {
  for (const n of ['msedge', 'Microsoft Edge', 'chrome.exe', 'Firefox', 'Brave Browser', 'iexplore', 'Internet Explorer', 'Opera GX']) assert.ok(isBrowserApp(n), n);
  for (const n of ['notepad', 'Calculator', 'File Explorer', 'Word']) assert.ok(!isBrowserApp(n), n);
});

test('model presets: llama.cpp server is :8080/v1 with every model name "default"', () => {
  const l = P.PRESETS.find((x) => x.id === 'llamacpp');
  assert.strictEqual(l.gatewayUrl, 'http://127.0.0.1:8080/v1');
  assert.deepStrictEqual([l.modelAuto, l.modelMain, l.modelFast, l.model], ['default', 'default', 'default', 'default']);
  assert.strictEqual(P.presetFor('http://127.0.0.1:8080/v1/').id, 'llamacpp');
  assert.strictEqual(P.presetFor('http://127.0.0.1:8090/v1').id, 'premonition');
  assert.strictEqual(P.presetFor('http://other'), null);
});

test('model names are settings: defaults, saved, blank falls back', () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'desk-store-'));
  const s = new Store(d);
  const g = s.getSettings();
  assert.deepStrictEqual([g.modelAuto, g.modelMain, g.modelFast], ['qwen36-auto', 'qwen36', 'qwen36-fast']);
  const n = s.saveSettings({ modelAuto: ' default ', modelFast: 'default', modelMain: '   ', gatewayUrl: 'http://127.0.0.1:8080/v1' });
  assert.deepStrictEqual([n.modelAuto, n.modelFast, n.modelMain], ['default', 'default', 'qwen36']);
});

test('warm-up: its model is the Fast name, and a server that refuses the unknown header/request does not break it', async () => {
  assert.strictEqual(buildWarmBody([], 'default').model, 'default');
  assert.strictEqual(buildWarmBody([]).model, 'qwen36-fast');
  const seen = [];
  const w = new Warmer({ getSettings: () => ({ gatewayUrl: 'http://x/v1', modelFast: 'default' }), getTools: () => [], fetch: async (url, o) => { seen.push({ url, o }); return { ok: false, status: 400, text: async () => 'unknown header' }; } });
  await w.warm();
  assert.strictEqual(seen.length, 1); assert.strictEqual(JSON.parse(seen[0].o.body).model, 'default');
  assert.strictEqual(w.warmCount, 0); assert.strictEqual(w.warming, false);
  const w2 = new Warmer({ getSettings: () => ({ gatewayUrl: 'http://x/v1' }), getTools: () => [], fetch: async () => { throw new Error('connection refused'); } });
  await w2.warm(); assert.strictEqual(w2.warming, false);
});

test('rename: old "Premonition Desk" userData is copied once, with a marker, and the old folder stays', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'desk-mig-'));
  const old = path.join(root, 'Premonition Desk'); const nu = path.join(root, 'Premonition');
  fs.mkdirSync(path.join(old, 'threads'), { recursive: true }); fs.mkdirSync(path.join(old, 'Cache'), { recursive: true });
  fs.writeFileSync(path.join(old, 'settings.json'), '{"onboarded":true}'); fs.writeFileSync(path.join(old, 'threads', 't1.json'), '{"id":"t1"}');
  fs.writeFileSync(path.join(old, 'memory.json'), '{"facts":[]}'); fs.writeFileSync(path.join(old, 'helpers.json'), '[]'); fs.writeFileSync(path.join(old, 'Cache', 'junk'), 'x');
  const r = migrateUserData(root, nu);
  assert.strictEqual(r.migrated, true); assert.strictEqual(r.from, old);
  for (const f of ['settings.json', 'memory.json', 'helpers.json', path.join('threads', 't1.json'), MARKER]) assert.ok(fs.existsSync(path.join(nu, f)), f);
  assert.ok(!fs.existsSync(path.join(nu, 'Cache'))); assert.ok(fs.existsSync(path.join(old, 'settings.json')), 'old data kept as a backup');
  // second launch: nothing happens, and later edits are not overwritten
  fs.writeFileSync(path.join(nu, 'settings.json'), '{"onboarded":false}');
  assert.strictEqual(migrateUserData(root, nu).migrated, false);
  assert.strictEqual(fs.readFileSync(path.join(nu, 'settings.json'), 'utf8'), '{"onboarded":false}');
});

test('rename: no migration when the new folder already has settings, when nothing old exists, or for the dev name premonition-desk', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'desk-mig2-'));
  const nu = path.join(root, 'Premonition');
  assert.strictEqual(migrateUserData(root, nu).migrated, false); // nothing old
  fs.mkdirSync(path.join(root, 'premonition-desk'), { recursive: true }); fs.writeFileSync(path.join(root, 'premonition-desk', 'settings.json'), '{"mode":"hands-off"}');
  const r = migrateUserData(root, nu);
  assert.strictEqual(r.migrated, true); assert.strictEqual(JSON.parse(fs.readFileSync(path.join(nu, 'settings.json'), 'utf8')).mode, 'hands-off');
  const root2 = fs.mkdtempSync(path.join(os.tmpdir(), 'desk-mig3-'));
  fs.mkdirSync(path.join(root2, 'Premonition Desk'), { recursive: true }); fs.writeFileSync(path.join(root2, 'Premonition Desk', 'settings.json'), '{}');
  fs.mkdirSync(path.join(root2, 'Premonition'), { recursive: true }); fs.writeFileSync(path.join(root2, 'Premonition', 'settings.json'), '{"keep":1}');
  assert.strictEqual(migrateUserData(root2, path.join(root2, 'Premonition')).migrated, false);
});

test('make-ico: the icon.png becomes a valid .ico with PNG images at 16..256', () => {
  const png = fs.readFileSync(path.join(__dirname, '..', 'assets', 'icon.png'));
  const ico = makeIco(png, [16, 256]);
  assert.strictEqual(ico.readUInt16LE(0), 0); assert.strictEqual(ico.readUInt16LE(2), 1); assert.strictEqual(ico.readUInt16LE(4), 2);
  assert.strictEqual(ico[6], 16); assert.strictEqual(ico[6 + 16], 0); // 256 is stored as 0
  const off = ico.readUInt32LE(6 + 12);
  const small = decodePng(ico.subarray(off, off + ico.readUInt32LE(6 + 8)));
  assert.strictEqual(small.w, 16); assert.strictEqual(small.h, 16);
});

test('deskhelper.ps1 has every command of the Mac helper, is plain ASCII, and the packaged zip step ships it', () => {
  const f = path.join(__dirname, '..', 'helper', 'deskhelper.ps1');
  const src = fs.readFileSync(f, 'utf8');
  assert.ok(!/[^\x00-\x7f]/.test(src), 'ASCII only (PowerShell 5.1 reads BOM-less files as ANSI)');
  for (const c of ['check', 'ask-permissions', 'look', 'press', 'click', 'type', 'key', 'scroll', 'open-app', 'screenshot']) assert.ok(new RegExp("'" + c + "'").test(src), c);
  assert.match(src, /last_look\.json/); assert.match(src, /SecureEdit/);
  assert.match(fs.readFileSync(path.join(__dirname, '..', 'build-win.sh'), 'utf8'), /extra-resource=helper\/deskhelper\.ps1/);
});

const pwsh = spawnSync('pwsh', ['-NoProfile', '-Command', '$PSVersionTable.PSVersion.Major']);
test('deskhelper.ps1 parses (PowerShell syntax check)', { skip: pwsh.status === 0 ? false : 'pwsh is not installed here' }, () => {
  const f = path.join(__dirname, '..', 'helper', 'deskhelper.ps1');
  const cmd = "$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('" + f.replace(/'/g, "''") + "',[ref]$t,[ref]$e);if($e.Count){$e|ForEach-Object{$_.ToString()};exit 1}";
  const r = spawnSync('pwsh', ['-NoProfile', '-Command', cmd], { encoding: 'utf8' });
  assert.strictEqual(r.status, 0, r.stdout + r.stderr);
});

test('with process.platform stubbed to win32, screen.js picks the PowerShell helper by default', () => {
  const real = Object.getOwnPropertyDescriptor(process, 'platform');
  Object.defineProperty(process, 'platform', { value: 'win32' });
  try {
    const inv = helperInvocation('C:\\app\\resources\\deskhelper.ps1', ['check']);
    assert.strictEqual(inv.cmd, 'powershell.exe'); assert.deepStrictEqual(inv.args.slice(0, 5), ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'C:\\app\\resources\\deskhelper.ps1']);
    assert.ok(candidates({}, 'R').every((c) => c.endsWith('deskhelper.ps1')));
  } finally { Object.defineProperty(process, 'platform', real); }
});
