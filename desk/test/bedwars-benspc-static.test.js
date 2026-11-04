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

test('Ben is asked only for: no session, login, purchase, UAC (never to unlock the screen: it is locked on purpose)', () => {
  const rb = JSON.parse(read('runbook.json'));
  const asks = rb.steps.flatMap((s) => s.errors).filter((e) => e.askBen).map((e) => e.id).sort();
  assert.deepStrictEqual(asks, ['login-required', 'no-session', 'purchase', 'uac']);
  const locked = rb.steps.flatMap((s) => s.errors).find((e) => e.id === 'screen-locked');
  assert.match(JSON.stringify(locked.fixes), /never unlocks it/);
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

test('bridge: interactive-token task, on demand, no window, request/result files, idle + lock check', () => {
  const x = read('bridge-task.xml');
  assert.match(x, /<LogonType>InteractiveToken<\/LogonType>/);
  assert.match(x, /<Triggers\s*\/>/);
  assert.match(x, /<Command>wscript\.exe<\/Command>/);
  assert.match(x, /bridge-launch\.vbs/);
  const vbs = fs.readFileSync(path.join(DIR, 'bridge-launch.vbs'), 'utf8');
  assert.match(vbs, /bridge\.ps1"+, 0, True/, 'window style 0 (hidden), wait for the bridge');
  assert.match(read('bridge.ps1'), /'idle' \{/);
  assert.match(read('bridge.ps1'), /GetLastInputInfo/);
  assert.match(read('bridge.ps1'), /WTSQuerySessionInformationW/);
  assert.doesNotMatch(read('bridge.ps1'), /LockWorkStation|SendInput|keybd_event|LogonUser/, 'the bridge never locks/unlocks or types');
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

test('Minecraft is never driven by desktop input: match verbs use GlimTruthKit over RCON; desk input is refused while our client runs', () => {
  const g = read('glimtool.ps1');
  const body = (verb) => { const i = g.indexOf("  '" + verb + "' {"); const rest = g.slice(i + 5); const j = rest.search(/\n  '[a-z-]+' \{/); return rest.slice(0, j < 0 ? undefined : j); };
  for (const v of ['match-start', 'match-status', 'match-stop']) {
    assert.doesNotMatch(body(v), /Invoke-Bridge|'desk'/, v + ' must not use the bridge or desk input');
    assert.match(body(v), /Invoke-Tk/, v + ' uses GlimTruthKit');
  }
  assert.match(body('match-start'), /Invoke-Tk "start \$map"/);
  assert.match(body('match-start'), /bw forceStart debug/);
  assert.match(body('desk'), /Fail 'desk-refused'/);
  assert.match(body('ping'), /Invoke-Bridge 'idle' @\(\) \d+ -Soft/);
  assert.match(body('ping'), /idle_s/); assert.match(body('ping'), /last_input_ms/);
});

test('deploy.sh ships the hidden bridge launcher and GlimTruthKit; setup builds it into OUR server copy and re-registers the task', () => {
  const sh = read('deploy.sh');
  for (const f of ['bridge-launch.vbs', 'truthkit/build.ps1', 'truthkit/res/plugin.yml', 'truthkit/res/config.yml', 'truthkit/src/glim/tk/TruthKit.java']) assert.ok(sh.includes('|' + f + '"'), f);
  const st = read('setup.ps1');
  assert.match(st, /truthkit\\build\.ps1/); assert.match(st, /-Install/);
  assert.match(st, /Register-ScheduledTask -TaskName 'GlimBridge' -Xml/);
  assert.match(st, /'bridge-launch\.vbs'/);
  const b = fs.readFileSync(path.join(DIR, 'truthkit', 'build.ps1'), 'utf8');
  assert.match(b, /glim-bedwars\\server\\plugins/); assert.match(b, /StartsWith\(\$Root/);
  assert.doesNotMatch(b, /Remove-Item|\bdel\b/);
});

test('GlimTruthKit writes every truth-log event type with ms times to our logs\\truth.jsonl (and never human chat)', () => {
  const j = fs.readFileSync(path.join(DIR, 'truthkit', 'src', 'glim', 'tk', 'TruthKit.java'), 'utf8');
  for (const t of ['join', 'leave', 'match_start', 'match_end', 'hit', 'death', 'kill', 'void_death', 'bed_broken', 'purchase', 'pickup', 'block_place', 'block_break', 'tick', 'edge'])
    assert.ok(j.includes('"' + t + '"'), 'event type ' + t);
  assert.ok(j.includes('"{\\"ms\\":" + ms + ",\\"t\\":\\""'), 'every line starts with ms then t');
  assert.match(j, /yyyy-MM-dd'T'HH:mm:ss\.SSSXXX/);
  assert.match(j, /"bw forceStart debug"/);
  assert.match(j, /"bw join "/);
  assert.doesNotMatch(j, /AsyncPlayerChatEvent/, 'chat is never read, so it is never stored');
  const cfg = fs.readFileSync(path.join(DIR, 'truthkit', 'res', 'config.yml'), 'utf8');
  assert.match(cfg, /truth-file: 'C:\/Users\/benja\/glim-bedwars\/logs\/truth\.jsonl'/);
  assert.match(fs.readFileSync(path.join(DIR, 'truthkit', 'res', 'plugin.yml'), 'utf8'), /^name: GlimTruthKit$/m);
});
