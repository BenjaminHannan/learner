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

test('helper: Mac and Windows both run a compiled binary directly (Windows: deskhelper.exe, no PowerShell)', () => {
  assert.deepStrictEqual(P.helperCommand('darwin', '/r/deskhelper'), { cmd: '/r/deskhelper', prefix: [] });
  assert.deepStrictEqual(P.helperCommand('win32', 'C:\\r\\deskhelper.exe'), { cmd: 'C:\\r\\deskhelper.exe', prefix: [] });
  const inv = helperInvocation('C:\\r\\deskhelper.exe', ['look', '--max', '80'], 'win32');
  assert.strictEqual(inv.cmd, 'C:\\r\\deskhelper.exe'); assert.deepStrictEqual(inv.args, ['look', '--max', '80']);
  assert.strictEqual(helperInvocation('/r/deskhelper', ['check'], 'darwin').cmd, '/r/deskhelper');
  assert.strictEqual(P.helperFileName('win32'), 'deskhelper.exe'); assert.strictEqual(P.helperFileName('darwin'), 'deskhelper');
});

test('helper lookup order per platform: settings path, resources, helper/, (win) vendor/helper, build/', () => {
  const win = candidates({ helperPath: 'X' }, 'R', 'win32').map((p) => path.basename(p));
  assert.deepStrictEqual(win, ['X', 'deskhelper.exe', 'deskhelper.exe', 'deskhelper.exe', 'deskhelper.exe']);
  assert.ok(candidates({}, null, 'win32').some((c) => /vendor[\\/]helper[\\/]deskhelper\.exe$/.test(c)));
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
  assert.strictEqual(m.options.type, 'panel'); assert.strictEqual(m.allWorkspaces, true); assert.strictEqual(m.options.enableLargerThanScreen, true); // may sit in the menu-bar band beside the notch
  const w = P.pillOptions('win32', 420, 300);
  assert.strictEqual('type' in w.options, false);
  assert.strictEqual(w.options.frame, false); assert.strictEqual(w.options.alwaysOnTop, true); assert.strictEqual(w.options.skipTaskbar, true);
  assert.strictEqual(w.options.focusable, false); assert.strictEqual(w.level, 'screen-saver'); assert.strictEqual(w.allWorkspaces, false); assert.strictEqual(w.hideInMissionControl, false);
  assert.deepStrictEqual(P.pillPosition({ x: 0, y: 0, width: 1920, height: 1040 }, 420), { x: 750, y: 6 });
  assert.deepStrictEqual(P.pillPosition({ x: 100, y: 25, width: 1440, height: 875 }, 420), { x: 610, y: 31 });
  assert.deepStrictEqual(P.pillPosition({ x: 0, y: 0, width: 1512, height: 982 }, 420, 37), { x: 546, y: 43 }); // full-screen on a notched Mac stays under the camera
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

const SRC = fs.readFileSync(path.join(__dirname, '..', 'helper', 'win', 'DeskHelper.cs'), 'utf8') + fs.readFileSync(path.join(__dirname, '..', 'helper', 'win', 'Ui.cs'), 'utf8');

test('deskhelper.exe source: every command of the Mac helper, the same JSON keys, password rule, no PowerShell script shipped', () => {
  for (const c of ['check', 'ask-permissions', 'look', 'press', 'click', 'type', 'key', 'scroll', 'open-app', 'screenshot']) assert.ok(new RegExp('case "' + c + '"').test(SRC), c);
  // look output: app, pid, windows[{title, frame}], elements[{id, role, title, value, frame}]; cache: pid + elements[{id, path, role, label, frame}]
  for (const k of ['app', 'pid', 'windows', 'elements', 'title', 'frame', 'id', 'role', 'value', 'path', 'label', 'hwnd']) assert.ok(SRC.includes('"' + k + '"'), k);
  for (const k of ['accessibility', 'screenRecording', 'opened', 'chars', 'width', 'height', 'scale', 'ok', 'method']) assert.ok(SRC.includes('"' + k + '"'), k);
  assert.match(SRC, /last_look\.json/); assert.match(SRC, /"SecureEdit"/);
  assert.match(SRC, /IsPassword\) \{ outRole = "SecureEdit"; value = "";/, 'a password field is never read');
  for (const f of ['--app', '--max', '--double', '--right']) assert.ok(SRC.includes('"' + f + '"'), f);
  assert.ok(!fs.existsSync(path.join(__dirname, '..', 'helper', 'deskhelper.ps1')), 'the PowerShell helper is gone (Defender flagged it)');
  const bw = fs.readFileSync(path.join(__dirname, '..', 'build-win.sh'), 'utf8') + fs.readFileSync(path.join(__dirname, '..', 'build-win.ps1'), 'utf8');
  assert.match(bw, /extra-resource=vendor\/helper\/deskhelper\.exe/); assert.ok(!/extra-resource=helper\/deskhelper\.ps1/.test(bw));
});

test('screen.js sends the argument shapes deskhelper.exe expects and reads its look JSON', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dh-'));
  const log = path.join(dir, 'args.log');
  const bin = path.join(dir, 'deskhelper');
  const sample = '{"app":"Notepad","pid":7,"windows":[{"title":"Untitled","frame":[0,0,800,600]}],"elements":[{"id":1,"role":"Edit","title":"Text editor","value":"hi","frame":[5,40,780,500]},{"id":2,"role":"SecureEdit","title":"Password","value":"","frame":[5,10,100,20]}]}';
  fs.writeFileSync(bin, '#!/bin/sh\necho "$@" >> ' + JSON.stringify(log) + '\ncase "$1" in look) echo \'' + sample + '\';; *) echo \'{"ok":true}\';; esac\n', { mode: 0o755 });
  const { createScreen, formatLook } = require('../src/tools/screen');
  const sc = createScreen(() => ({ helperPath: bin }), null);
  const look = await sc.tools.screen_look({ app: 'Notepad' });
  const text = typeof look === 'string' ? look : look.text;
  assert.match(text, /App: Notepad \(pid 7\)[\s\S]*\[1\] Edit "Text editor" value="hi"[\s\S]*\[2\] SecureEdit "Password"/);
  assert.ok(!/SecureEdit "Password" value=/.test(text), 'an empty secure value is not printed');
  await sc.tools.screen_click({ id: 2 }); await sc.tools.screen_click({ x: 10, y: 20, double: true }); await sc.tools.screen_type({ text: 'a b' }); await sc.tools.open_app({ name: 'notepad' });
  const calls = fs.readFileSync(log, 'utf8').trim().split('\n');
  assert.ok(calls.includes('look --app Notepad')); assert.ok(calls.includes('press 2')); assert.ok(calls.includes('click 10 20 --double')); assert.ok(calls.includes('type a b')); assert.ok(calls.includes('open-app notepad'));
  assert.match(formatLook({ app: 'X', elements: [{ id: 3, role: 'Button', title: 'OK', frame: [1, 2, 3, 4] }] }), /\[3\] Button "OK" @1,2,3,4/);
});

const mono = spawnSync('mono', ['--version']);
const exe = path.join(__dirname, '..', 'vendor', 'helper', 'deskhelper.exe');
test('deskhelper.exe smoke test under mono: usage, check, and error JSON with exit code 1', { skip: mono.status === 0 && fs.existsSync(exe) ? false : 'mono or vendor/helper/deskhelper.exe is not here' }, () => {
  const run = (...a) => spawnSync('mono', [exe, ...a], { encoding: 'utf8' });
  const h = run('--help'); assert.strictEqual(h.status, 0); assert.match(h.stdout, /usage: deskhelper check\|ask-permissions\|look/);
  assert.deepStrictEqual(JSON.parse(run('check').stdout), { accessibility: true, screenRecording: true });
  const bad = run('bogus'); assert.strictEqual(bad.status, 1); assert.deepStrictEqual(JSON.parse(bad.stdout), { error: 'unknown command: bogus' });
  assert.strictEqual(JSON.parse(run('click', '1').stdout).error, 'usage: click X Y [--double] [--right]');
  assert.strictEqual(JSON.parse(run('look', '--max', '0').stdout).error, '--max needs a positive number');
  assert.strictEqual(JSON.parse(run('key', 'cmd+zz').stdout).error, 'unknown key combo: cmd+zz');
});
