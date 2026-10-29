'use strict';
// Structural smoke only: a known all-zero LoRA cannot demonstrate learning.
const fs = require('fs'), path = require('path'), os = require('os'), crypto = require('crypto');
const { spawn, execFileSync } = require('child_process');
const project = path.resolve(__dirname, '../..');
const { PrivateCheck } = require(path.join(project, 'desk/src/private-check'));
const fixturePath = process.env.PREMONITION_ZERO_FIXTURE || path.join(__dirname, 'fixtures/private-zero-lfm3/fixture.json');
const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
fixture.gguf = path.resolve(path.dirname(fixturePath), fixture.gguf);
const ops = path.join(os.homedir(), 'learner-ops');
const root = process.argv[2];
if (!root || !path.isAbsolute(root) || !path.basename(root).startsWith('premonition-private-native-')) throw Error('Supply the isolated smoke directory.');
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const audit = { version: 1, purpose: 'Structural native private-engine and actual HTTP-only grader smoke; zero LoRA, no learning claim or promotion.',
  started: new Date().toISOString(), project, root, fixture: { adapter: fixture.gguf, bytes: fs.statSync(fixture.gguf).size, sha256: sha(fixture.gguf) },
  moduleSha256: { controller: sha(path.join(project, 'desk/src/private-check.js')), grader: sha(path.join(project, 'sleepmlx/served.py')) }, events: [], resources: [] };
const save = () => fs.writeFileSync(path.join(root, 'check-audit.json'), JSON.stringify(audit, null, 2));
const held = path.join(root, 'held.jsonl');
fs.writeFileSync(held, JSON.stringify({ q: 'For this synthetic check, repeat the city name Paris. Answer just the city name.', a: 'Paris', kind: 'fact', night: 1, status: 'held_out', key: 'synthetic|native-private-paris' }) + '\n', { mode: 0o600, flag: 'wx' });
audit.held = { path: held, sha256: sha(held), cards: 1 };
const children = [];
let key = '';
const controller = new PrivateCheck(root, {
  startTimeoutMs: 90000, graderTimeoutMs: 240000, stopWaitMs: 10000, forceWaitMs: 5000,
  spawn(exe, args, options) {
    const role = args.includes('served-check') ? 'grader' : 'server';
    if (role === 'server') key = args[args.indexOf('--api-key') + 1];
    const child = spawn(exe, args, options), event = { role, pid: child.pid, exe, spawned: new Date().toISOString() };
    audit.events.push(event); children.push(child);
    child.on('exit', (code, signal) => { event.code = code; event.signal = signal; event.exited = new Date().toISOString(); save(); });
    if (role === 'grader') {
      let stderr = ''; child.stderr.on('data', chunk => { stderr += chunk; });
      child.on('close', () => { const modules = stderr.split('\n').filter(line => line.startsWith('import time:')).map(line => line.split('|').pop().trim());
        event.imports = { count: modules.length, heavyBackendImports: modules.filter(name => /^(torch|transformers|mlx|tensorflow|safetensors)(\.|$)/.test(name)) }; });
    } else {
      let stderr = ''; child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-20000); });
      child.on('close', () => { event.stderrTail = stderr.split(key).join('[private key]'); save(); });
    }
    save(); return child;
  },
});
process.env.SLEEPMLX_HOME = path.join(root, 'isolated-sleepmlx');
process.env.SLEEPMLX_DIARY_DIR = path.join(root, 'isolated-diary');
process.env.SLEEPMLX_USERDATA = path.join(root, 'isolated-userdata');
process.env.PYTHONPROFILEIMPORTTIME = '1';
const abort = new AbortController();
process.on('SIGTERM', () => abort.abort()); process.on('SIGINT', () => abort.abort());
const deadline = setTimeout(() => abort.abort(), 360000);
const sample = () => {
  try { const pids = [process.pid, ...children.filter(child => child.exitCode === null && child.signalCode === null).map(child => child.pid)].filter(Boolean);
    audit.resources.push({ at: new Date().toISOString(), rss: execFileSync('/bin/ps', ['-p', pids.join(','), '-o', 'pid=,rss=']).toString().trim(),
      pressure: execFileSync('/usr/sbin/sysctl', ['-n', 'kern.memorystatus_vm_pressure_level']).toString().trim(),
      swap: execFileSync('/usr/sbin/sysctl', ['-n', 'vm.swapusage']).toString().trim() }); save();
  } catch (_) {}
};
const sampler = setInterval(sample, 2000); sample();
(async () => {
  try {
    audit.idleBefore = await controller.ensureIdle(); save();
    audit.verdict = await controller.check({
      exe: path.join(ops, 'lfm3/llama.cpp/build/bin/llama-server'),
      model: path.join(ops, 'lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf'),
      adapter: fixture.gguf, cards: held, expectedAdapterSha256: fixture.gguf_sha256, expectedHeldSha256: audit.held.sha256,
      python: path.join(ops, 'speedbench/venv312/bin/python'), sleepmlxParent: project, flavor: 'metal', ctx: 2048, signal: abort.signal,
    });
    audit.idleAfter = await controller.ensureIdle();
    audit.remainingJournal = fs.existsSync(controller.ledger);
    audit.remainingJobEntries = fs.readdirSync(controller.jobsDir);
    audit.sourceAdapterUnchanged = sha(fixture.gguf) === fixture.gguf_sha256;
    audit.heldUnchanged = sha(held) === audit.held.sha256;
    audit.complete = audit.verdict.processStopped === true && audit.idleAfter.ok === true && !audit.remainingJournal && audit.remainingJobEntries.length === 0
      && audit.events.some(event => event.role === 'grader' && event.exited) && audit.events.every(event => event.exited) && audit.verdict.held_n === 1;
  } catch (error) { audit.error = String(error.stack || error).split(key || '\0').join('[private key]'); audit.idleAfter = await controller.ensureIdle(); }
  finally { clearTimeout(deadline); clearInterval(sampler); audit.finished = new Date().toISOString(); sample(); save();
    console.log(JSON.stringify({ root, complete: audit.complete, verdict: audit.verdict, idleAfter: audit.idleAfter })); process.exitCode = audit.complete ? 0 : 1; }
})();
