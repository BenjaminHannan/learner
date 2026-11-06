'use strict';
// SECURE-LOGIN real check in Electron (marks S1, S3, S4, S5, S9 in docs/secure-login/MARKS.md). Not part of the unit suite.
// Run: electron scripts/secure-login-electron.js (kept out of test/ so node --test does not pick it up)
// TEMP userData + a THROWAWAY keychain file (never Ben's). A scripted gateway plays the model; the real Agent, Browser, LoginAsk,
// the app's form window (src/loginwin.js + renderer/loginform.html) and MacKeychain do the rest.
//  1. ask -> save -> autofill: browser_go + browser_sign_in with no saved login -> the app's form opens -> "Ben" types into it, Save
//     -> keychain -> the app fills + submits the page.   2. reuse: a fresh run signs in with NO form.   3. a Mote (Ben away) asks
//     ask_login for another site twice -> queued, one notification, no window.   4. grep the test password through the temp userData.
const { app, BrowserWindow, WebContentsView, session } = require('electron');
const https = require('https');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'secure-login-e2e-'));
const UD = path.join(TMP, 'ud');
app.setPath('userData', UD);
const KC = path.join(TMP, 'secure-login-test.keychain-db');
const PW = 'Sx-' + Math.random().toString(36).slice(2, 10) + '-9q!';
const USER = 'ben.test@example.org';
const L = require('../src/logins');
const F = require('../src/loginform');
const { formOpener } = require('../src/loginwin');
const { Browser } = require('../src/tools/browser');
const { Agent } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { Store } = require('../src/store');
const { startGateway } = require('../test/helpers');

// every console line of this process also goes to a log file in the temp userData (so the grep covers logs too)
fs.mkdirSync(path.join(UD, 'logs'), { recursive: true });
const LOG = path.join(UD, 'logs', 'main.log');
for (const lvl of ['log', 'warn', 'error']) { const o = console[lvl]; console[lvl] = (...a) => { const line = a.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join(' '); try { fs.appendFileSync(LOG, line + '\n'); } catch (e) { /* ignore */ } o(...a); }; }

const posts = [];
const page = (title, body) => '<!doctype html><html><head><title>' + title + '</title></head><body style="font:16px sans-serif;padding:20px">' + body + '</body></html>';
const ONE = page('Sign in to Fake Mail', '<h1>Sign in</h1><form method="post" action="/done"><label for=u>Email</label> <input id=u name=username type=email autocomplete=username><br><label for=p>Password</label> <input id=p name=password type=password autocomplete=current-password><br><button type=submit>Sign in</button></form>');
function handler(req, res) {
  if (req.method === 'POST') { let b = ''; req.on('data', (d) => { b += d; }); req.on('end', () => { posts.push({ host: req.headers.host, body: Object.fromEntries(new URLSearchParams(b)) }); res.setHeader('content-type', 'text/html'); res.end(page('Inbox', '<h1>Inbox</h1><p>You are signed in. 3 new messages.</p>')); }); return; }
  res.setHeader('content-type', 'text/html'); res.end(ONE);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const check = (name, ok, extra) => { results.push([name, !!ok]); console.log((ok ? 'PASS ' : 'FAIL ') + name + (extra ? ' :: ' + extra : '')); };

app.commandLine.appendSwitch('ignore-certificate-errors');   // the local test server's self-signed certificate (this test process only)
app.on('certificate-error', (e, wc, url, err, cert, cb) => { if (/^https:\/\/(127\.0\.0\.1|localhost):/.test(url)) { e.preventDefault(); cb(true); } else cb(false); });
app.on('window-all-closed', () => { /* keep running */ });

app.whenReady().then(async () => {
  let code = 1;
  try {
    execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', path.join(TMP, 'k.pem'), '-out', path.join(TMP, 'c.pem'), '-days', '1', '-subj', '/CN=localhost'], { stdio: 'ignore' });
    const srv = https.createServer({ key: fs.readFileSync(path.join(TMP, 'k.pem')), cert: fs.readFileSync(path.join(TMP, 'c.pem')) }, handler);
    await new Promise((r) => srv.listen(0, '127.0.0.1', r));
    const A = 'https://127.0.0.1:' + srv.address().port, B = 'https://localhost:' + srv.address().port;
    execFileSync('/usr/bin/security', ['create-keychain', '-p', 'secure-login-test', KC]);
    execFileSync('/usr/bin/security', ['unlock-keychain', '-p', 'secure-login-test', KC]);
    check('S9: the test keychain is not in Ben\'s search list', !execFileSync('/usr/bin/security', ['list-keychains']).toString().includes(KC));

    const store = new L.LoginStore({ dir: UD, box: new L.MacKeychain({ keychain: KC }) });
    const threads = new Store(UD);
    // the app's form window, exactly as main.js makes it; the test plays Ben typing into it
    const wins = new Map(), opened = [], notes = [];
    let ask = null, away = false;
    const open = formOpener({ BrowserWindow, wins, onClosed: (t) => ask.closed(t) });
    let benFills = true;
    const formChecks = [];
    ask = new F.LoginAsk({ store, isAway: () => away, notify: (title, body, onClick) => notes.push({ title, body }),
      open: (f) => {
        const h = open({ ...f, focus: false }); opened.push(f);   // shown without taking focus: never steal Ben's keyboard during a test
        const w = h.win;
        w.webContents.once('did-finish-load', async () => {
          try {
            await sleep(300);
            const info = await w.webContents.executeJavaScript('({url: location.href, pwType: document.getElementById("p").type, title: document.getElementById("title").textContent})');
            formChecks.push(info);
            if (!benFills) return;
            const type = async (sel, text) => { await w.webContents.executeJavaScript('document.querySelector(' + JSON.stringify(sel) + ').focus()'); w.webContents.insertText(text); await sleep(80); };
            await type('#u', USER); await type('#p', PW);
            await w.webContents.executeJavaScript('document.getElementById("save").click()');
          } catch (e) { console.log('form fill error', e.message); }
        });
        return h;
      } });
    // IPC the form uses (main.js registers the same three handlers with the same sender check)
    const { ipcMain } = require('electron');
    const formSender = (e, token) => { const w = wins.get(String(token || '')); return !!w && !w.isDestroyed() && e.sender === w.webContents; };
    ipcMain.handle('loginform:info', (e, t) => (formSender(e, t) ? ask.info(t) : null));
    ipcMain.handle('loginform:save', (e, t, u, p) => (formSender(e, t) ? ask.submit(t, u, p) : { ok: false, error: 'Not allowed.' }));
    ipcMain.handle('loginform:cancel', (e, t) => (formSender(e, t) ? ask.cancel(t) : { ok: false }));

    const win = new BrowserWindow({ width: 900, height: 700, show: false });
    const view = new WebContentsView({ webPreferences: { partition: 'persist:desk', contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, '..', 'preload-browser.js') } });
    win.contentView.addChildView(view); view.setBounds({ x: 0, y: 0, width: 900, height: 700 }); win.showInactive();
    const br = new Browser({ view, session });
    br.shouldFocus = () => true;

    const toolResults = [];
    const mkAgent = (gw, isHelper) => {
      const askFor = (url, site, why) => ask.ask({ site, reason: why, pageUrl: url, helper: isHelper });
      const tools = {
        browser_go: (x) => br.go(x.url),
        browser_sign_in: () => F.signInWithAsk({ br, store, askFor }),
        ask_login: async (x) => F.modelResult(await askFor(br.state().url, x.site, x.reason))
      };
      for (const k of Object.keys(tools)) { const f = tools[k]; tools[k] = async (x, c) => { const r = await f(x, c); toolResults.push({ tool: k, r }); return r; }; }
      return new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 20, mode: 'hands-off', vision: 'off', verify: false, thinkCapSecs: 0 }), toolDefs: buildTools({}), tools, emit: () => {}, approve: async () => { throw new Error('no approval expected'); }, askUser: async () => '' });
    };
    const allRequests = [];
    // each answer depends on how many tool results the request already holds (a side request of the agent cannot shift the script)
    const runTask = async (script, text, isHelper) => {
      const steps = script;
      const fn = (req) => { const k = (req.messages || []).filter((m) => m.role === 'tool').length; return steps[Math.min(k, steps.length - 1)]; };
      const gw = await startGateway(Array(30).fill(fn));
      try { const t = threads.createThread ? threads.createThread() : { id: 'th' + Date.now(), title: 'x', messages: [], items: [] }; await mkAgent(gw, isHelper).run(t, text); threads.saveThread(t); allRequests.push(...gw.requests); return { t, gw }; } finally { gw.close(); }
    };

    // 1. ask -> save -> autofill
    const r1 = await runTask([{ tool_calls: [{ name: 'browser_go', arguments: { url: A + '/login' } }] }, { tool_calls: [{ name: 'browser_sign_in', arguments: {} }] }, { content: 'Signed in to your mail.' }], 'check my fake mail');
    check('S3: one app form opened for the site', opened.length === 1 && opened[0].host === '127.0.0.1:' + srv.address().port, JSON.stringify(opened.map((o) => o.host)));
    check('S3: the form is the app\'s own page (file://…/loginform.html), password field masked', formChecks.length === 1 && /^file:.*\/renderer\/loginform\.html\?t=/.test(formChecks[0].url) && formChecks[0].pwType === 'password', JSON.stringify(formChecks));
    check('S3: Save put it in the (test) keychain', (await new L.MacKeychain({ keychain: KC }).get(A, USER)) === PW);
    check('S3: the app filled + submitted the page; the site got the right login', posts.length === 1 && posts[0].body.username === USER && posts[0].body.password === PW, JSON.stringify(posts.map((p) => p.body.username)));
    const sr = toolResults.find((x) => x.tool === 'browser_sign_in');
    check('S2: browser_sign_in result says signed in, holds no password', sr && sr.r.kind === 'signed' && !JSON.stringify(sr.r).includes(PW), sr && String(sr.r.text).split('\n')[0]);
    check('the form window closed after Save', wins.size === 0);

    // 2. saved-login reuse: a fresh run, no form
    posts.length = 0;
    await runTask([{ tool_calls: [{ name: 'browser_go', arguments: { url: A + '/login' } }] }, { tool_calls: [{ name: 'browser_sign_in', arguments: {} }] }, { content: 'Signed in again.' }], 'check my fake mail again');
    check('S4: reuse signed in with no new form', opened.length === 1 && posts.length === 1 && posts[0].body.password === PW);

    // 3. a Mote with Ben away: ask_login for another origin, twice -> queued, one notification, no window
    away = true; benFills = false;
    await runTask([{ tool_calls: [{ name: 'browser_go', arguments: { url: B + '/login' } }] }, { tool_calls: [{ name: 'ask_login', arguments: { site: 'localhost', reason: 'webmail check' } }] }, { tool_calls: [{ name: 'ask_login', arguments: { reason: 'again' } }] }, { content: 'NO_UPDATE' }], 'Mote: look at the newest mail', true);
    const al = toolResults.filter((x) => x.tool === 'ask_login');
    console.log('tools:', JSON.stringify(toolResults.map((x) => x.tool + ':' + (x.r.state || x.r.kind || '') + ':' + String(x.r.text || '').slice(0, 80))));
    check('S5: Mote ask_login -> queued twice, ONE notification, no window', al.length === 2 && al.every((x) => x.r.state === 'queued' && x.r.saved === false) && notes.length === 1 && opened.length === 1 && wins.size === 0, JSON.stringify(al.map((x) => x.r.state)) + ' notes=' + notes.length);

    // 4. S1/S2: the secret is nowhere the model or a log can see
    const models = JSON.stringify(allRequests);
    check('S1: no model request (messages + tool results) holds the password', !models.includes(PW));
    check('S2: no tool result holds the password', !JSON.stringify(toolResults).includes(PW));
    fs.writeFileSync(path.join(UD, 'gateway-requests.jsonl'), allRequests.map((r) => JSON.stringify(r)).join('\n'));   // the "gateway training log" of this run
    await session.fromPartition('persist:desk').flushStorageData();
    let hits = '';
    try { hits = execFileSync('/usr/bin/grep', ['-r', '-l', '-a', '-F', PW, UD]).toString(); } catch (e) { hits = e.status === 1 ? '' : 'grep error ' + e.status; }
    const nfiles = Number(execFileSync('/bin/sh', ['-c', 'find "$1" -type f | wc -l', 'sh', UD]).toString().trim());
    check('S1: grep -r -F <test password> over the temp userData: 0 files (of ' + nfiles + ')', hits.trim() === '', hits.trim());
    // positive control: the same grep DOES find the password when a file holds it (so 0 hits above means 0 copies)
    const canary = path.join(TMP, 'canary'); fs.mkdirSync(canary); fs.writeFileSync(path.join(canary, 'x.txt'), 'pw=' + PW);
    let ch = ''; try { ch = execFileSync('/usr/bin/grep', ['-r', '-l', '-a', '-F', PW, canary]).toString(); } catch (e) { ch = ''; }
    check('grep positive control finds a planted copy', ch.includes('x.txt'));
    const threadFiles = execFileSync('/bin/sh', ['-c', 'grep -rl -a -F "check my fake mail" "$1" | wc -l', 'sh', UD]).toString().trim();
    check('the threads of the runs are in the temp userData (so the grep covered them)', Number(threadFiles) >= 1, threadFiles + ' file(s)');
    console.log('grep proof: password length', PW.length, 'searched', nfiles, 'files under', UD, '-> hits:', JSON.stringify(hits.trim()));
    code = results.every((x) => x[1]) ? 0 : 1;
    srv.close();
  } catch (e) { console.log('ERROR', e && e.stack); code = 2; }
  finally {
    try { execFileSync('/usr/bin/security', ['delete-keychain', KC]); } catch (e) { /* gone */ }
    console.log('test keychain deleted:', !fs.existsSync(KC));
    console.log('RESULT ' + results.filter((x) => x[1]).length + '/' + results.length + ' passed');
    try { fs.rmSync(TMP, { recursive: true, force: true }); } catch (e) { /* ignore */ }
    app.exit(code);
  }
});
