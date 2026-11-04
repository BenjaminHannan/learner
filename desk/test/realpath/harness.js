// Item 4 real-path check: the real desk/main.js under a fake Electron, a fake clock (14:00, outside the night window), fake senses,
// a fake model server, no real web, no child processes, HOME = a temp dir. Read-only towards Ben's files.
const Module = require('module');
const path = require('path'), os = require('os'), fs = require('fs'), http = require('http');
const DESK = path.resolve(__dirname, '..', '..');
// usage (from desk/): node test/realpath/harness.js   — not part of the suite (no .test.js). Writes a temp copy desk/.rp-main.js
// (main.js + a block that exposes the always-on objects to drive.js) and deletes it on exit.
const RP = path.join(DESK, '.rp-main.js');
fs.writeFileSync(RP, fs.readFileSync(path.join(DESK, 'main.js'), 'utf8') + fs.readFileSync(path.join(__dirname, 'exports.js.txt'), 'utf8'));
process.on('exit', () => { try { fs.rmSync(RP, { force: true }); } catch (e) { /* gone */ } });
const tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), 'aon-rp-home-'));
const ud = path.join(tmpHome, 'userData'); fs.mkdirSync(ud);
process.env.HOME = tmpHome;
const T0 = Date.now();
const log = (...a) => console.log('[' + new Date().toTimeString().slice(0, 8) + ' +' + ((Date.now() - T0) / 1000).toFixed(1) + 's]', ...a);
globalThis.__log = log;
// ---- fake clock: today 14:00 local, advanceable
const RealDate = Date; let offset = 0;
{ const d = new RealDate(); d.setHours(14, 0, 0, 0); offset = d.getTime() - RealDate.now(); }
class FakeDate extends RealDate { constructor(...a) { if (!a.length) super(RealDate.now() + offset); else super(...a); } static now() { return RealDate.now() + offset; } }
globalThis.Date = FakeDate;
globalThis.__adv = (ms) => { offset += ms; };
// ---- no child processes except read-only system probes
const cp = require('child_process');
const OK = new Set(['sysctl', 'vm_stat', 'pmset', 'sw_vers', 'uname', 'ioreg', 'memory_pressure']);
const base = (c) => path.basename(String(c || ''));
for (const fn of ['spawn', 'execFile', 'exec', 'fork']) { const o = cp[fn]; cp[fn] = function (c, ...r) { if (OK.has(base(c))) return o.call(this, c, ...r); log('BLOCKED child_process.' + fn, base(c), JSON.stringify(r[0] || '').slice(0, 80)); const e = new (require('events'))(); e.stdout = new (require('events'))(); e.stderr = new (require('events'))(); e.stdin = { write() {}, end() {} }; e.kill = () => {}; e.unref = () => {}; e.pid = 0; const cb = r.find((x) => typeof x === 'function'); setImmediate(() => { if (cb) cb(new Error('blocked in harness'), '', ''); if (e.listenerCount('error')) e.emit('error', new Error('blocked in harness')); e.emit('close', 1); e.emit('exit', 1); }); return e; }; }
for (const fn of ['spawnSync', 'execFileSync', 'execSync']) { const o = cp[fn]; cp[fn] = function (c, ...r) { const b = fn === 'execSync' ? String(c).split(/\s+/)[0] : base(c); if (OK.has(path.basename(b))) return o.call(this, c, ...r); log('BLOCKED child_process.' + fn, b); if (fn === 'spawnSync') return { status: 1, stdout: '', stderr: 'blocked', error: new Error('blocked') }; throw new Error('blocked in harness'); }; }
// ---- fake model + no real web
const calls = []; globalThis.__calls = calls;
const srv = http.createServer((req, res) => {
  let b = ''; req.on('data', (d) => (b += d)); req.on('end', () => {
    let j = {}; try { j = JSON.parse(b); } catch (e) { /* */ }
    const msgs = j.messages || [], sys = String((msgs[0] && msgs[0].content) || ''), user = String((msgs[msgs.length - 1] && msgs[msgs.length - 1].content) || '');
    let kind = 'other', content = 'NO_UPDATE';
    if (/quiet background attention/.test(sys)) {
      kind = 'loop';
      content = /Cannot find module/i.test(user) ? JSON.stringify({ say: 'The same "Cannot find module left-pad" error came up 3 times. Want me to look at it?', note: null, learn: null, urgent: false, why: 'stuck on an error' })
        : JSON.stringify({ say: 'That looks like an interesting page.', note: null, learn: null, urgent: false, why: 'browsing' });
    } else if (/one of Glim's Motes/.test(sys)) { kind = 'mote'; content = JSON.stringify({ claims: ['Octopuses have three hearts.'], question: 'Why do octopuses have blue blood?' }); }
    else if (/You check ONE claim/.test(sys)) { kind = 'judge'; content = JSON.stringify({ verdict: 'unclear', correction: null }); }
    calls.push({ kind, test: j.test === true || req.headers['x-test'] === '1', sys: sys.slice(0, 60) });
    log('MODEL ' + kind + (j.test === true ? ' [test]' : '') + ' model=' + j.model + ' max_tokens=' + j.max_tokens + ' <- ' + user.replace(/\s+/g, ' ').slice(0, 90) + (kind === 'other' ? ' | sys: ' + sys.slice(0, 60) + ' | url ' + req.url : ''));
    setTimeout(() => { res.setHeader('content-type', 'application/json'); res.end(JSON.stringify({ choices: [{ message: { role: 'assistant', content } }] })); }, kind === 'mote' ? 1500 : 50);
  });
});
const realFetch = globalThis.fetch;
globalThis.fetch = (u, o) => { const s = String(u && u.url || u); if (/^https?:\/\/(127\.0\.0\.1|localhost)[:/]/.test(s)) return realFetch(u, o); log('BLOCKED fetch', s.slice(0, 80)); return Promise.reject(new Error('no web in harness')); };
// ---- fake electron
let idleS = 10; globalThis.__idle = (s) => { idleS = s; };
const mk = (name) => new Proxy(function () {}, {
  get(t, k) {
    if (k === 'then') return undefined;
    if (k === Symbol.toPrimitive) return () => '';
    if (k === 'getPath') return () => ud;
    if (k === 'getAppPath') return () => DESK;
    if (k === 'argv') return [];
    if (k === 'platform') return 'darwin';
    if (k === 'whenReady') return () => Promise.resolve();
    if (k === 'isPackaged') return false;
    if (k === 'getSystemIdleTime') return () => idleS;
    if (k === 'isOnBatteryPower') return () => false;
    if (k === 'onBatteryPower') return false;
    if (k === 'isOnline') return () => true;
    if (k === 'requestSingleInstanceLock') return () => true;
    if (k === 'getVersion') return () => '0.0.0-harness';
    if (k === 'getName' || k === 'name') return k === 'name' ? 'Premonition' : () => 'Premonition';
    if (k === 'getAllDisplays') return () => [];
    if (k === 'getPrimaryDisplay') return () => ({ bounds: { x: 0, y: 0, width: 1512, height: 982 }, workArea: { x: 0, y: 38, width: 1512, height: 944 }, size: { width: 1512, height: 982 }, scaleFactor: 2 });
    return mk(name + '.' + String(k));
  },
  apply() { return mk(name + '()'); },
  construct() { return mk('new ' + name); }
});
const fake = mk('electron');
const orig = Module._load;
Module._load = function (req) { if (req === 'electron') return fake; return orig.apply(this, arguments); };
process.on('uncaughtException', (e) => { log('UNCAUGHT', e && e.stack || e); process.exitCode = 1; });
process.on('unhandledRejection', (e) => { log('UNHANDLED', String(e && e.stack || e).split('\n').slice(0, 3).join(' | ')); });
srv.listen(0, '127.0.0.1', () => {
  const port = srv.address().port; globalThis.__port = port;
  fs.writeFileSync(path.join(ud, 'settings.json'), JSON.stringify({ onboarded: true, permsSeen: true, gatewayUrl: 'http://127.0.0.1:' + port, model: 'fake-model', modelFast: 'fake-fast', openAtLogin: false }));
  log('fake model on :' + port + '; userData ' + ud + '; fake clock ' + new Date().toString());
  require(RP);
  log('loaded main.js');
  setTimeout(() => require(path.join(__dirname, 'drive.js')), 2500);
});
