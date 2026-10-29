'use strict';
// No models or ML imports. Only a disposable sleeping Python child is owned.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { spawn, execFile } = require('child_process');
const assert = require('assert/strict');
const option = name => process.argv[process.argv.indexOf(name) + 1];
const root = path.resolve(option('--root')), python = fs.realpathSync(option('--python'));
const modulePath = path.resolve(option('--module'));
const { ProcessIdentity, PrivateCheck, matchesIdentity } = require(modulePath);
const inspector = new ProcessIdentity({ platform: 'win32' });
const owned = [];
const audit = { started: new Date().toISOString(), platform: process.platform, node: process.version,
  moduleSha256: crypto.createHash('sha256').update(fs.readFileSync(modulePath)).digest('hex'), cases: [] };
function waitExit(child) {
  if (child.exitCode != null || child.signalCode != null) return Promise.resolve();
  return new Promise((resolve, reject) => { const timer = setTimeout(() => reject(Error('owned child did not exit')), 10000); child.once('exit', () => { clearTimeout(timer); resolve(); }); });
}
function recordFor(controller) {
  const id = crypto.randomUUID(), jobDir = path.join(controller.jobsDir, id);
  fs.mkdirSync(jobDir, { recursive: true });
  const model = path.join(root, 'synthetic-base.gguf'), adapter = path.join(jobDir, 'adapter.gguf'), cards = path.join(jobDir, 'held.jsonl');
  fs.writeFileSync(model, 'synthetic-only'); fs.writeFileSync(adapter, 'synthetic-only'); fs.writeFileSync(cards, '{"status":"held_out","night":1,"q":"Q?","a":"A"}\n');
  return { version: 1, id, alias: 'premonition-check-' + id, apiKey: crypto.randomBytes(32).toString('hex'),
    port: 31337, url: 'http://127.0.0.1:31337', jobDir, model: { path: model }, adapter: { path: adapter }, cards: { path: cards },
    roles: { grader: { exe: python, pid: null, startTime: null, exited: false } } };
}
async function sleeping(record) {
  const child = spawn(python, ['-c', 'import time; time.sleep(180)', '--private-check-id', record.id, '--server', record.url, '--cards', record.cards.path], { windowsHide: true, stdio: 'ignore' });
  owned.push(child); await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); });
  return child;
}
async function acl(dir) {
  const script = `$a=Get-Acl -LiteralPath '${dir.replace(/'/g, "''")}'; $s=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; $rules=@($a.Access); @{protected=$a.AreAccessRulesProtected;count=$rules.Count;onlyCurrentUser=(@($rules|Where-Object {$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -ne $s}).Count -eq 0)}|ConvertTo-Json -Compress`;
  const encoded = Buffer.from(script, 'utf16le').toString('base64');
  const text = await new Promise((resolve, reject) => execFile('powershell.exe', ['-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], { windowsHide: true, timeout: 15000 }, (error, stdout) => error ? reject(error) : resolve(stdout)));
  return JSON.parse(text);
}
(async () => {
  fs.mkdirSync(root, { recursive: true });
  const controller = new PrivateCheck(root, { platform: 'win32', forceWaitMs: 3000 });
  fs.mkdirSync(controller.jobsDir, { recursive: true });
  assert.equal(await inspector.secureDirectory(controller.jobsDir), true);
  const permission = await acl(controller.jobsDir); assert.equal(permission.protected, true); assert.equal(permission.onlyCurrentUser, true); assert.equal(permission.count, 1);
  audit.cases.push({ case: 'user-only-private-directory-ACL', ...permission, pass: true });
  const record = recordFor(controller), child = await sleeping(record);
  const identity = await inspector.inspect(child.pid);
  assert.equal(identity.status, 'alive'); assert.equal(matchesIdentity(identity, record, 'grader', 'win32', false), true);
  record.roles.grader.pid = child.pid; record.roles.grader.startTime = identity.startTime;
  audit.cases.push({ case: 'inspect-owned-sleeping-child', pid: child.pid, executable: path.basename(identity.exe), birthRecorded: !!identity.startTime, pass: true });
  const wrongBirth = JSON.parse(JSON.stringify(record)); wrongBirth.roles.grader.startTime = 'not-the-owned-birth';
  assert.equal((await inspector.terminate(wrongBirth, 'grader', 1000)).status, 'gone');
  assert.equal((await inspector.inspect(child.pid)).status, 'alive');
  audit.cases.push({ case: 'birth-mismatch-does-not-kill-current-PID-owner', pass: true });
  const wrongMarker = JSON.parse(JSON.stringify(record)); wrongMarker.id = crypto.randomUUID();
  assert.equal((await inspector.terminate(wrongMarker, 'grader', 1000)).status, 'unknown');
  assert.equal((await inspector.inspect(child.pid)).status, 'alive');
  audit.cases.push({ case: 'marker-mismatch-does-not-kill', pass: true });
  // Simulate an app crash between spawn and publishing the child's PID.
  record.roles.grader.pid = null; record.roles.grader.startTime = null;
  fs.writeFileSync(controller.ledger, JSON.stringify(record), { mode: 0o600 });
  const journalPermission = await acl(controller.ledger);
  assert.equal(journalPermission.onlyCurrentUser, true); assert.equal(journalPermission.count, 1);
  audit.cases.push({ case: 'journal-inherits-current-user-only-ACL', ...journalPermission, pass: true });
  const restarted = new PrivateCheck(root, { platform: 'win32', forceWaitMs: 3000 });
  const recovered = await restarted.ensureIdle(); assert.equal(recovered.ok, true); assert.equal(recovered.processStopped, true);
  await waitExit(child); assert.equal(fs.existsSync(controller.ledger), false);
  audit.cases.push({ case: 'restart-discovers-unpublished-PID-and-confirms-exit', pass: true });
  assert.equal((await inspector.inspect(child.pid)).status, 'gone');
  audit.pass = true;
})().catch(error => { audit.pass = false; audit.error = error.message; process.exitCode = 1; }).finally(async () => {
  for (const child of owned) if (child.exitCode == null && child.signalCode == null) { child.kill('SIGKILL'); try { await waitExit(child); } catch (error) { audit.cleanupError = error.message; process.exitCode = 1; } }
  audit.finished = new Date().toISOString(); audit.ownedChildrenExited = owned.every(child => child.exitCode != null || child.signalCode != null);
  fs.writeFileSync(path.join(root, 'audit.json'), JSON.stringify(audit, null, 2));
  console.log(JSON.stringify(audit, null, 2));
});
