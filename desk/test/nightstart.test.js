'use strict';
const test = require('node:test');
const assert = require('node:assert');
const path = require('path');
const { execFileSync } = require('child_process');
const { NightStart, plist, command, bundleOf, LABEL } = require('../src/nightstart');
const Platform = require('../renderer/platform');

// Oct 30: Premonition was quit at 10:10 PM, so the 11 PM sleep never started
const EXE = '/Applications/Premonition.app/Contents/MacOS/Premonition';
function memFs() {
  const files = new Map();
  return {
    files,
    readFileSync: (f) => { if (!files.has(f)) throw new Error('ENOENT'); return files.get(f); },
    writeFileSync: (f, d) => files.set(f, String(d)),
    rmSync: (f) => files.delete(f),
    mkdirSync: () => {}
  };
}

test('night start: the agent opens the app hidden at the start of the sleep window, unless it is already running; only an installed .app', () => {
  assert.strictEqual(bundleOf(EXE), '/Applications/Premonition.app');
  assert.strictEqual(bundleOf('/home/x/desk/node_modules/electron/dist/electron'), '');
  assert.strictEqual(bundleOf('/private/var/folders/x/T/AppTranslocation/AB-12/d/Premonition.app/Contents/MacOS/Premonition'), '', 'a translocated download moves every launch');
  assert.strictEqual(bundleOf('/Volumes/Premonition/Premonition.app/Contents/MacOS/Premonition'), '', 'a disk image is gone after it is ejected');
  assert.strictEqual(command(EXE, 501), "/usr/bin/pgrep -xq -U 501 'Premonition' || exec /usr/bin/open -g -j -a '/Applications/Premonition.app' --args --night");
  assert.strictEqual(command('/Applications/P.app/Contents/MacOS/Premonition Nightly Build', 501), '', 'macOS cuts process names at 16 characters, so pgrep could never see it');
  const p = plist(EXE, '23:00', 501, 'com.electron.premonition desk');
  assert.match(p, /<array><string>\/bin\/sh<\/string><string>-c<\/string><string>\/usr\/bin\/pgrep -xq -U 501 'Premonition' \|\| exec \/usr\/bin\/open -g -j -a '\/Applications\/Premonition\.app' --args --night<\/string><\/array>/);
  assert.match(p, /<key>AssociatedBundleIdentifiers<\/key><string>com\.electron\.premonition desk<\/string>/);
  assert.match(p, /<key>Hour<\/key><integer>23<\/integer><key>Minute<\/key><integer>0<\/integer>/);
  assert.doesNotMatch(plist(EXE, '23:00', 501, ''), /AssociatedBundleIdentifiers/);
  assert.match(plist("/Users/b/Ben's A & B.app/Contents/MacOS/Premonition", '0:30', 501), /'\/Users\/b\/Ben'\\''s A &amp; B\.app'[\s\S]*<integer>0<\/integer><key>Minute<\/key><integer>30<\/integer>/);
  assert.strictEqual(plist(EXE, 'late', 501), '');
  assert.strictEqual(Platform.startedHidden('darwin', ['/x/Premonition', '--night'], { wasOpenedAsHidden: false }), true);
  assert.strictEqual(Platform.startedHidden('darwin', ['/x/Premonition'], { wasOpenedAsHidden: false }), false);
});

test('night start: the shell line survives quotes in the path and skips open when the app is running', () => {
  const cmd = command("/Users/b/Ben's Apps/Premonition.app/Contents/MacOS/Premonition", 501).replace('/usr/bin/pgrep -xq -U 501', 'false').replace('exec /usr/bin/open -g -j -a', 'printf "%s|"');
  assert.strictEqual(execFileSync('/bin/sh', ['-c', cmd]).toString(), "/Users/b/Ben's Apps/Premonition.app|--args|--night|");
  assert.strictEqual(execFileSync('/bin/sh', ['-c', command(EXE, 501).replace('/usr/bin/pgrep -xq -U 501', 'true').replace('exec /usr/bin/open', 'echo opened')]).toString(), '');
});

// a pretend launchd: bootout takes `lag` more print calls to let go, bootstrap refuses while the old one is still there
function fakeLaunchd(runs, o = {}) {
  const st = { up: false, lag: 0, refuse: false };
  return Object.assign(st, o, {
    run: (c, a) => {
      runs.push(a[0]);
      if (a[0] === 'print') { if (st.lag > 0 && --st.lag === 0) st.up = false; return st.up; }
      if (a[0] === 'bootout') { if (!st.up) return false; if (st.slow) st.lag = 3; else st.up = false; return true; }
      if (a[0] === 'bootstrap') { if (st.up || st.refuse) return false; st.up = true; return true; }
      return false;
    }
  });
}

test('night start: written and loaded once, rewritten when the window moves, removed when auto-sleep is off', () => {
  const fs = memFs(), runs = [], ld = fakeLaunchd(runs, { slow: true });
  fs.files.set('/Applications/Premonition.app/Contents/Info.plist', '<dict><key>CFBundleIdentifier</key>\n<string>com.electron.premonition desk</string></dict>');
  const n = new NightStart({ fs, home: '/Users/b', execPath: EXE, uid: 501, run: ld.run, wait: () => {} });
  const file = path.join('/Users/b', 'Library', 'LaunchAgents', LABEL + '.plist');
  assert.strictEqual(n.sync({ on: true, from: '23:00' }), 'installed');
  assert.match(fs.files.get(file), /<integer>23<\/integer>/);
  assert.match(fs.files.get(file), /AssociatedBundleIdentifiers<\/key><string>com\.electron\.premonition desk<\/string>/);
  assert.deepStrictEqual(runs, ['print', 'bootstrap'], 'nothing loaded yet: no bootout');
  assert.strictEqual(n.sync({ on: true, from: '23:00' }), 'same');
  assert.strictEqual(runs.length, 2, 'every minute costs nothing when nothing changed');
  runs.length = 0;
  assert.strictEqual(n.sync({ on: true, from: '23:30' }), 'installed', 'waits for launchd to let go of the old one before loading the new one');
  assert.deepStrictEqual(runs, ['bootout', 'print', 'print', 'print', 'bootstrap']);
  assert.match(fs.files.get(file), /<integer>30<\/integer>/);
  assert.strictEqual(n.sync({ on: false, from: '23:30' }), 'removed');
  assert.ok(!fs.files.has(file));
  assert.strictEqual(n.sync({ on: false, from: '23:30' }), 'same');
  assert.ok(!ld.up);
  const dev = new NightStart({ fs, home: '/Users/b', execPath: '/x/electron', run: () => runs.push('x') });
  assert.strictEqual(dev.sync({ on: true, from: '23:00' }), 'skip');
  assert.ok(!fs.files.has(file), 'a dev run never installs it');
});

test('night start: a refused bootstrap is tried again (three times), and what launchd lost is put right at the next launch', () => {
  const fs = memFs(), runs = [], ld = fakeLaunchd(runs, { refuse: true });
  const file = path.join('/Users/b', 'Library', 'LaunchAgents', LABEL + '.plist');
  const opts = { fs, home: '/Users/b', execPath: EXE, uid: 501, run: ld.run, wait: () => {} };
  const n = new NightStart(opts);
  assert.strictEqual(n.sync({ on: true, from: '23:00' }), 'failed');
  ld.refuse = false;
  assert.strictEqual(n.sync({ on: true, from: '23:00' }), 'installed', 'the next minute tries again');
  assert.strictEqual(n.sync({ on: true, from: '23:00' }), 'same');
  ld.refuse = true; ld.up = false; runs.length = 0;   // a new launch: the file is there but launchd does not have it (Login Items switched off)
  const later = new NightStart(opts);
  for (let i = 0; i < 3; i++) assert.strictEqual(later.sync({ on: true, from: '23:00' }), 'failed');
  const tries = runs.filter((r) => r === 'bootstrap').length;
  assert.strictEqual(tries, 3);
  assert.strictEqual(later.sync({ on: true, from: '23:00' }), 'failed');
  assert.strictEqual(runs.filter((r) => r === 'bootstrap').length, 3, 'after three refusals it stops asking every minute');
  ld.refuse = false;
  assert.strictEqual(later.sync({ on: true, from: '23:15' }), 'installed', 'a new window is a new try');
  runs.length = 0;
  const next = new NightStart(opts);
  assert.strictEqual(next.sync({ on: true, from: '23:15' }), 'same', 'loaded and unchanged: nothing to do');
  assert.deepStrictEqual(runs, ['print']);
  ld.up = false;
  assert.strictEqual(new NightStart(opts).sync({ on: false, from: '23:15' }), 'removed', 'an unloaded file is still removed when auto-sleep is off');
  assert.ok(!fs.files.has(file));
  ld.up = true;   // loaded but its file was deleted by hand
  assert.strictEqual(new NightStart(opts).sync({ on: false, from: '23:15' }), 'removed');
  assert.ok(!ld.up, 'booted out');
});

test('night start: main syncs on sleep-setting changes and at quit, never for a test profile', () => {
  const src = require('fs').readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(src, /ch\('autoSleep'\) \|\| ch\('sleepFrom'\) \|\| ch\('sleepTo'\) \|\| ch\('sleepAdapt'\)\)\) syncNightStart\(\)/);
  assert.match(src, /app\.on\('before-quit', \(\) => \{[^\n]*syncNightStart\(\)/);
  assert.match(src, /if \(s\.autoSleep === false \|\| !inWindow\(new Date\(\), w\.from, w\.to\)\) \{[^\n]*app\.quit\(\); return; \}/, 'a late start the next morning closes again');
  assert.match(src, /function syncNightStart\(\) \{\n\s*if \(process\.platform !== 'darwin' \|\| !app\.isPackaged \|\| E2E \|\| app\.commandLine\.hasSwitch\('user-data-dir'\)\) return;/);
});
