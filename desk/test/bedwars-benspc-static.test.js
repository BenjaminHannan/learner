'use strict';
// Static checks for the BensPC tools (src/games/bedwars/benspc). No PowerShell needed.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const DIR = path.join(__dirname, '..', 'src', 'games', 'bedwars', 'benspc');
const read = (f) => fs.readFileSync(path.join(DIR, f), 'utf8');
const scripts = fs.readdirSync(DIR).filter((f) => /\.(ps1|sh|xml|json|md)$/.test(f));

function contractVerbs() {
  const md = fs.readFileSync(path.join(DIR, '..', 'TOOLS.md'), 'utf8');
  const verbs = [];
  for (const line of md.split('\n')) {
    const m = line.match(/^\| `([a-z-]+)` \|/);
    if (m) verbs.push(m[1]);
  }
  return verbs;
}
function allowlist() {
  const src = read('glimtool.ps1');
  const m = src.match(/\$Verbs\s*=\s*@\(([\s\S]*?)\)/);
  assert.ok(m, '$Verbs allowlist not found');
  return [...m[1].matchAll(/'([a-z-]+)'/g)].map((x) => x[1]);
}

test('allowlist is exactly the TOOLS.md verbs', () => {
  const want = contractVerbs().sort();
  const got = allowlist().sort();
  assert.ok(want.length >= 17, 'parsed the verb table');
  assert.deepStrictEqual(got, want);
});

test('every verb has a dispatch case and there is no case outside the allowlist', () => {
  const src = read('glimtool.ps1');
  const body = src.slice(src.indexOf('switch ($verb)'));
  const cases = [...body.matchAll(/^  '([a-z-]+)' \{/gm)].map((x) => x[1]).sort();
  assert.deepStrictEqual(cases, allowlist().sort());
});

test('unknown verbs return "not allowed"', () => {
  assert.match(read('glimtool.ps1'), /error = 'not allowed'/);
  assert.match(read('glimtool.ps1'), /SSH_ORIGINAL_COMMAND/);
});

test('runbook.json is valid; every error has >= 1 fix and an askBen flag', () => {
  const rb = JSON.parse(read('runbook.json'));
  assert.ok(Array.isArray(rb.steps) && rb.steps.length > 0);
  const ids = new Set();
  for (const s of rb.steps) {
    for (const e of s.errors) {
      assert.ok(e.id && e.text, 'id and text');
      assert.ok(!ids.has(e.id), 'duplicate id ' + e.id);
      ids.add(e.id);
      assert.ok(Array.isArray(e.fixes) && e.fixes.length >= 1, e.id + ' needs a fix');
      for (const f of e.fixes) assert.ok(f.do, e.id + ' fix needs "do"');
      assert.strictEqual(typeof e.askBen, 'boolean', e.id + ' needs askBen');
      if (e.askBen) assert.ok(e.askBenWhy, e.id + ' askBen needs a reason');
    }
  }
  for (const need of ['server-wont-start', 'port-in-use', 'map-missing', 'client-crash', 'no-session', 'gpu-held', 'low-disk', 'ssh-down']) {
    assert.ok(ids.has(need), 'runbook lacks ' + need);
  }
});

test('Ben is asked only for: no session, login, purchase, UAC (and the locked screen)', () => {
  const rb = JSON.parse(read('runbook.json'));
  const asks = rb.steps.flatMap((s) => s.errors).filter((e) => e.askBen).map((e) => e.id).sort();
  assert.deepStrictEqual(asks, ['login-required', 'no-session', 'purchase', 'screen-locked', 'uac']);
});

test('every Fail id used in glimtool.ps1 exists in the runbook', () => {
  const rb = JSON.parse(read('runbook.json'));
  const ids = new Set(rb.steps.flatMap((s) => s.errors).map((e) => e.id));
  const used = new Set([...read('glimtool.ps1').matchAll(/Fail '([a-z-]+)'/g)].map((m) => m[1]));
  for (const u of used) assert.ok(ids.has(u), 'Fail id not in runbook: ' + u);
});

test('deploy.sh verifies a sha256 of every copied file', () => {
  const sh = read('deploy.sh');
  assert.match(sh, /sha256|SHA256/);
  assert.match(sh, /certutil -hashfile|Get-FileHash/);
  assert.match(sh, /shasum -a 256|sha256sum/);
  assert.match(sh, /exit 1/);
  assert.match(sh, /deskhelper\.exe/);
  assert.match(sh, /refusing dest outside/);
});

test('setup.ps1 has -DryRun and never installs the SSH key', () => {
  const s = read('setup.ps1');
  assert.match(s, /\[switch\]\$DryRun/);
  assert.match(s, /NOT installed/);
  assert.doesNotMatch(s, /Add-Content[^\n]*authorized_keys|Set-Content[^\n]*authorized_keys|Out-File[^\n]*authorized_keys/);
});

test('Remove-Item only touches our own folder', () => {
  for (const f of scripts.filter((x) => x.endsWith('.ps1'))) {
    for (const [i, line] of read(f).split('\n').entries()) {
      if (/Remove-Item|\bdel\b|\brmdir\b|\brd\b/i.test(line) && !/^\s*#/.test(line)) {
        assert.match(line, /\$Root/, `${f}:${i + 1} deletes without a $Root check: ${line.trim()}`);
        const before = read(f).split('\n').slice(Math.max(0, i - 3), i + 1).join('\n');
        assert.match(before, /StartsWith\(\$Root/, `${f}:${i + 1} lacks a StartsWith($Root) guard`);
      }
    }
  }
});

test('Stop-Process only by -Id, and the file checks the command line first', () => {
  for (const f of scripts.filter((x) => x.endsWith('.ps1'))) {
    const src = read(f);
    const lines = src.split('\n').filter((l) => /Stop-Process|taskkill|Stop-Service|Restart-Computer|shutdown/i.test(l) && !/^\s*#/.test(l));
    if (!lines.length) continue;
    for (const l of lines) {
      assert.match(l, /Stop-Process -Id \(?\[int\]/, `${f}: Stop-Process must use -Id with an int pid: ${l.trim()}`);
    }
    assert.match(src, /CommandLine -like \$TagLike/, `${f}: no command-line check before stopping`);
  }
});

test('no reboots, no non-local hosts, no password typing, no purchases', () => {
  for (const f of scripts) {
    const src = read(f);
    assert.doesNotMatch(src, /hypixel/i, `${f} mentions a public server host`);
    assert.doesNotMatch(src, /\b[a-z0-9-]+\.(hypixel|minehut|mineplex|cubecraft)\.\w+/i, f);
    assert.doesNotMatch(src, /Restart-Computer|shutdown(\.exe)?\s+\/[rs]/i, `${f} could reboot`);
  }
  // the client launcher and the tool only accept the local server
  assert.match(read('launch-client.ps1'), /\^\(127\\\.0\\\.0\\\.1\|localhost\)\$/);
  assert.match(read('glimtool.ps1'), /\(127\\\.0\\\.0\\\.1\|localhost\):/);
});

test('guardrails are present: 15 GB floor, GPU rules, pids.json, our folder', () => {
  const g = read('glimtool.ps1');
  assert.match(g, /\$FloorGB\s*=\s*15/);
  assert.match(g, /C:\\Users\\benja\\glim-bedwars'/);
  assert.match(g, /pids\.json/);
  assert.match(g, /GPU free/);
  assert.match(g, /GPU in use by \$Who since/);
  assert.match(g, /GPU_LOAN\.txt/);
  assert.match(g, /Assert-Disk/);
});

test('bridge: interactive-token task, on demand, request/result files', () => {
  const x = read('bridge-task.xml');
  assert.match(x, /<LogonType>InteractiveToken<\/LogonType>/);
  assert.match(x, /<Triggers\s*\/>/);
  assert.match(x, /bridge\.ps1/);
  const b = read('bridge.ps1');
  assert.match(b, /req/);
  assert.match(b, /res/);
  assert.match(read('glimtool.ps1'), /schtasks \/run \/tn GlimBridge/);
  assert.match(read('glimtool.ps1'), /no signed-in session/);
});

test('RUNBOOK.md lists every runbook error id', () => {
  const rb = JSON.parse(read('runbook.json'));
  const md = read('RUNBOOK.md');
  for (const s of rb.steps) for (const e of s.errors) assert.ok(md.includes('`' + e.id + '`'), e.id);
});
