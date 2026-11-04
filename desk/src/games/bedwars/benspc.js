'use strict';
// Glim team, Bedwars side: the Mac client for the BensPC tool contract (./TOOLS.md). ssh to the LAN address first, then Tailscale,
// each with ConnectTimeout 8 s and an overall timeout; the remote side is the forced command glimtool.ps1, which prints ONE JSON line.
// The runner is injectable so tests never touch the network: run(cmd, argv, {timeoutMs}) -> Promise<{code, stdout, stderr, timedOut}>.
// Fallback rule: only TRANSPORT failures (ssh exit 255, a timeout, no JSON at all) move on to the next host. A JSON answer, even
// {"ok":false}, is BensPC talking and is returned as is (retrying it on another route would run the verb twice).

const VERBS = ['ping', 'disk', 'gpu-status', 'gpu-acquire', 'gpu-release', 'server-start', 'server-stop', 'server-status', 'map-list',
  'match-start', 'match-status', 'match-stop', 'log-read', 'client-launch', 'client-stop', 'desk', 'fetch'];
const HOSTS = [
  { name: 'lan', argv: ['-o', 'HostName=10.0.0.188', 'benspc'] },
  { name: 'tailscale', argv: ['benspc'] }
];
const SSH_OPTS = ['-o', 'ConnectTimeout=8', '-o', 'BatchMode=yes'];
const TIMEOUT_MS = 60000;
const SLOW = { 'server-start': 150000, 'client-launch': 150000, 'match-start': 90000 };   // ours: these wait on BensPC
// verbs that change state: after a TIMEOUT they may already have run, so we do not resend them on the other route (the caller
// checks status instead). A refused connection (exit 255) never reached BensPC, so it is always safe to try the other route.
const MUTATING = new Set(['gpu-acquire', 'server-start', 'match-start', 'client-launch', 'desk']);
// an argument value may only hold these characters (no quotes, no shell or PowerShell specials); spaces are allowed and quoted
const SAFE = /^[A-Za-z0-9 _.:\/\\\-+=,@#%]*$/;

function defaultRunner() {
  const { execFile } = require('child_process');
  return (cmd, argv, o) => new Promise((resolve) => {
    execFile(cmd, argv, { timeout: (o && o.timeoutMs) || TIMEOUT_MS, maxBuffer: 32 * 1024 * 1024, windowsHide: true }, (err, stdout, stderr) => {
      resolve({ code: err ? (typeof err.code === 'number' ? err.code : 255) : 0, stdout: String(stdout || ''), stderr: String(stderr || ''), timedOut: !!(err && err.killed) });
    });
  });
}

// args: {flag: value} or an array of raw tokens (for `desk`). -> ['--flag', 'value', ...] with values checked; throws on bad input
function argTokens(args) {
  const out = [];
  const push = (v) => { const s = String(v); if (!SAFE.test(s)) throw new Error('unsafe argument: ' + s.slice(0, 40)); out.push(/\s/.test(s) ? '"' + s + '"' : s); };
  if (Array.isArray(args)) { args.forEach(push); return out; }
  for (const [k, v] of Object.entries(args || {})) {
    if (!/^[a-z][a-z0-9-]*$/.test(k)) throw new Error('bad flag: ' + k);
    if (v == null || v === false) continue;
    out.push('--' + k); if (v !== true) push(v);
  }
  return out;
}
// the one JSON line (the last line that parses as an object)
function parseLine(stdout) {
  const lines = String(stdout || '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i--) { if (!lines[i].startsWith('{')) continue; try { const j = JSON.parse(lines[i]); if (j && typeof j === 'object') return j; } catch (e) { /* keep looking */ } }
  return null;
}

class BensPC {
  // o: {run, hosts, timeoutMs, log}
  constructor(o) {
    o = o || {}; this.run = o.run || defaultRunner(); this.hosts = o.hosts || HOSTS; this.timeoutMs = o.timeoutMs || TIMEOUT_MS;
    this.log = o.log || (() => {}); this.prefer = 0; this.calls = [];
  }
  // -> the tool's JSON ({ok, ...}); transport failure on every route -> {ok:false, error:'transport: ...', transport:true, next:[]}
  async call(verb, args, o) {
    if (!VERBS.includes(verb)) return { ok: false, error: 'not allowed', next: [] };
    let toks; try { toks = argTokens(args); } catch (e) { return { ok: false, error: e.message, next: [] }; }
    const order = this.hosts.map((h, i) => i).sort((a, b) => (a === this.prefer ? -1 : b === this.prefer ? 1 : a - b));
    const errs = [];
    for (const i of order) {
      const h = this.hosts[i];
      const r = await this.run('ssh', SSH_OPTS.concat(h.argv, [verb], toks), { timeoutMs: (o && o.timeoutMs) || SLOW[verb] || this.timeoutMs });
      const j = r && !r.timedOut ? parseLine(r.stdout) : null;
      this.calls.push({ verb, host: h.name, code: r && r.code, timedOut: !!(r && r.timedOut), ok: j ? !!j.ok : null });
      if (j) { this.prefer = i; return j; }
      const why = r && r.timedOut ? 'timed out' : r && r.code === 255 ? 'ssh could not connect' + (r.stderr ? ' (' + r.stderr.trim().split('\n').pop().slice(0, 120) + ')' : '') : 'no JSON reply (exit ' + (r && r.code) + ')';
      errs.push(h.name + ': ' + why); this.log('benspc ' + verb + ' via ' + h.name + ': ' + why);
      if (MUTATING.has(verb) && !(r && r.code === 255 && !r.timedOut)) return { ok: false, error: 'transport: ' + errs.join('; ') + ' (may have run; check status)', transport: true, uncertain: true, next: [] };
    }
    return { ok: false, error: 'transport: ' + errs.join('; '), transport: true, next: [] };
  }
}

module.exports = { BensPC, VERBS, HOSTS, SSH_OPTS, MUTATING, SLOW, argTokens, parseLine, defaultRunner };
