'use strict';
// LOGIN1 real check in a bare Electron window (not part of the unit suite; it uses a THROWAWAY keychain file, never Ben's).
// Run: node_modules/.bin/electron test/login1-electron.js
// 1. "Ben" signs in on a local https one-page form in Glim's browser view -> the preload + LoginCapture offer one Save card -> Save
//    -> the login is in the test keychain.  2. browser_sign_in's fill (Browser.signIn) on a fresh page fills + submits it.
// 3. a two-step page (username, Next, password).  4. no saved login on another origin, and a plain-http page: nothing is filled.
const { app, BrowserWindow, WebContentsView, session, ipcMain } = require('electron');
const https = require('https');
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'login1-e2e-'));
app.setPath('userData', path.join(TMP, 'ud'));
const KC = path.join(TMP, 'login1-test.keychain-db');
const PW = 'Pw-' + Math.random().toString(36).slice(2, 10) + '!"\\x';
const USER = 'ben.test@example.org';
const L = require('../src/logins');
const { Browser } = require('../src/tools/browser');

const posts = [];
const page = (title, body) => '<!doctype html><html><head><title>' + title + '</title></head><body style="font:16px sans-serif;padding:20px">' + body + '</body></html>';
const ONE = page('Sign in', '<h1>Sign in</h1><form method="post" action="/done"><label for=u>Email</label> <input id=u name=username type=email autocomplete=username><br><label for=p>Password</label> <input id=p name=password type=password autocomplete=current-password><br><button type=submit>Sign in</button></form>');
const STEP = page('Sign in (two steps)', '<h1>Sign in</h1><form id=f method="post" action="/done"><div id=s1><input id=ident name=identifier type=email placeholder="Email or phone"> <button type=button id=next>Next</button></div>' +
  '<div id=s2 style="display:none"><input id=pw name=password type=password placeholder="Enter your password"> <button type=submit>Sign in</button></div></form>' +
  '<script>document.getElementById("next").onclick=function(){setTimeout(function(){document.getElementById("s1").style.display="none";document.getElementById("s2").style.display="block";},300)};</script>');
function handler(req, res) {
  if (req.method === 'POST') {
    let b = ''; req.on('data', (d) => { b += d; }); req.on('end', () => {
      const body = Object.fromEntries(new URLSearchParams(b)); posts.push({ host: req.headers.host, path: req.url, body });
      if (req.url === '/strict' && body.password !== PW) return res.end(ONE.replace('action="/done"', 'action="/strict"').replace('<h1>Sign in</h1>', '<h1>Sign in</h1><div role=alert>Wrong password. Try again.</div>'));
      res.end(page('Welcome', '<h1>Welcome back</h1><p>You are signed in.</p>'));
    });
    return;
  }
  res.setHeader('content-type', 'text/html'); res.end(req.url.startsWith('/step') ? STEP : req.url.startsWith('/strict') ? ONE.replace('action="/done"', 'action="/strict"') : ONE);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const check = (name, ok, extra) => { results.push([name, !!ok]); console.log((ok ? 'PASS ' : 'FAIL ') + name + (extra ? ' :: ' + extra : '')); };

app.commandLine.appendSwitch('ignore-certificate-errors');   // the local test server's self-signed certificate (this test process only)
app.on('certificate-error', (e, wc, url, err, cert, cb) => { if (/^https:\/\/(127\.0\.0\.1|localhost):/.test(url)) { e.preventDefault(); cb(true); } else cb(false); });

app.whenReady().then(async () => {
  let code = 1;
  try {
    execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', path.join(TMP, 'k.pem'), '-out', path.join(TMP, 'c.pem'), '-days', '1', '-subj', '/CN=localhost'], { stdio: 'ignore' });
    const srv = https.createServer({ key: fs.readFileSync(path.join(TMP, 'k.pem')), cert: fs.readFileSync(path.join(TMP, 'c.pem')) }, handler);
    await new Promise((r) => srv.listen(0, '127.0.0.1', r));
    const plain = http.createServer(handler); await new Promise((r) => plain.listen(0, '127.0.0.1', r));
    const port = srv.address().port, hport = plain.address().port;
    execFileSync('/usr/bin/security', ['create-keychain', '-p', 'login1-test', KC]);
    execFileSync('/usr/bin/security', ['unlock-keychain', '-p', 'login1-test', KC]);
    const listBefore = execFileSync('/usr/bin/security', ['list-keychains']).toString();
    check('the test keychain is not in Ben\'s search list', !listBefore.includes(KC));

    const store = new L.LoginStore({ dir: path.join(TMP, 'ud'), box: new L.MacKeychain({ keychain: KC }) });
    const offers = [];
    const capture = new L.LoginCapture({ store, offer: (ev) => offers.push(ev), delayMs: 1200 });
    const win = new BrowserWindow({ width: 900, height: 700, show: false });
    const view = new WebContentsView({ webPreferences: { partition: 'persist:desk', contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, '..', 'preload-browser.js') } });
    win.contentView.addChildView(view); view.setBounds({ x: 0, y: 0, width: 900, height: 700 }); win.showInactive();
    const br = new Browser({ view, session });
    br.shouldFocus = () => true;
    ipcMain.on('pm-login:submit', (e, d) => {
      if (e.sender !== br.wc) return;
      capture.submitted({ key: e.sender.id, url: (e.senderFrame && e.senderFrame.url) || e.sender.getURL(), user: d.user, password: d.password, filling: br.filling > Date.now(),
        probe: () => e.sender.executeJavaScript('(' + L.pageLoginProbe.toString() + ')()') }).catch((err) => console.log('capture error', err.message));
    });
    const wc = br.wc;
    const benTypes = async (sel, text) => { await wc.executeJavaScript('document.querySelector(' + JSON.stringify(sel) + ').focus()'); wc.focus(); wc.insertText(text); await sleep(100); };
    const benClicks = async (sel) => {
      const p = await wc.executeJavaScript('(function(){var r=document.querySelector(' + JSON.stringify(sel) + ').getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)}})()');
      wc.focus(); wc.sendInputEvent({ type: 'mouseMove', x: p.x, y: p.y }); wc.sendInputEvent({ type: 'mouseDown', x: p.x, y: p.y, button: 'left', clickCount: 1 }); wc.sendInputEvent({ type: 'mouseUp', x: p.x, y: p.y, button: 'left', clickCount: 1 });
    };
    const A = 'https://127.0.0.1:' + port, B = 'https://localhost:' + port;

    // 1. Ben signs in himself -> one Save card -> Save
    await br.go(A + '/one');
    console.log('page:', wc.getURL(), wc.getTitle());
    await benTypes('#u', USER); await benTypes('#p', PW);
    console.log('typed:', await wc.executeJavaScript('[document.querySelector("#u").value, document.querySelector("#p").value.length]'));
    await benClicks('button[type=submit]');
    await sleep(800); console.log('after click:', wc.getURL(), posts.length);
    if (!posts.length) { console.log('note: the synthetic mouse click did not land in this hidden test window; clicking the button from the page instead'); await wc.executeJavaScript('document.querySelector("button[type=submit]").click()'); await sleep(800); }
    for (let i = 0; i < 40 && !offers.length; i++) await sleep(150);
    check('Ben\'s own sign-in reached the site', posts.length === 1 && posts[0].body.password === PW);
    check('one Save card offered, naming host + user only', offers.length === 1 && offers[0].host === '127.0.0.1:' + port && offers[0].user === USER && !JSON.stringify(offers).includes(PW), JSON.stringify(offers));
    const saved = offers[0] ? await capture.answer(offers[0].token, 'save') : { ok: false };
    check('Save put it in the (test) keychain', saved.ok && (await new L.MacKeychain({ keychain: KC }).get(A, USER)) === PW);
    check('the index file holds no password', !fs.readFileSync(path.join(TMP, 'ud', 'logins.json'), 'utf8').includes(PW));

    // 2. Glim signs in by itself
    posts.length = 0; offers.length = 0;
    await br.go(A + '/one');
    const r1 = await br.signIn((u) => store.forPage(u));
    check('browser_sign_in filled + submitted the one-page form', posts.length === 1 && posts[0].body.username === USER && posts[0].body.password === PW, JSON.stringify(posts.map((p) => p.body.username)));
    check('result: "Signed in as <user> on <host>", no password', r1.kind === 'signed' && /^Signed in as ben\.test@example\.org on 127\.0\.0\.1:\d+\./.test(r1.text) && !r1.text.includes(PW), r1.text.split('\n')[0]);
    await sleep(1800);
    check('the app\'s own fill offered no Save card', offers.length === 0);

    // 3. two-step page on another origin (localhost): username, Next, password
    await store.save(B, 'two.step@example.org', PW + '2');
    posts.length = 0;
    await br.go(B + '/step');
    const r2 = await br.signIn((u) => store.forPage(u));
    check('two-step: username, Next, then password, submitted', posts.length === 1 && posts[0].body.identifier === 'two.step@example.org' && posts[0].body.password === PW + '2', r2.text.split('\n')[0]);
    check('two-step result names the user only', r2.kind === 'signed' && !r2.text.includes(PW));

    // 4. refusals: no saved login for this exact origin; plain http
    await store.remove(B);
    posts.length = 0;
    await br.go(B + '/one');
    const r3 = await br.signIn((u) => store.forPage(u));
    check('another origin without its own login gets nothing (localhost != 127.0.0.1)', r3.kind === 'none' && posts.length === 0 && /^No saved login for localhost:\d+: ask Ben to sign in once/.test(r3.text), r3.text);
    const typed = await wc.executeJavaScript('document.querySelector("#p").value');
    check('…and no password was typed into it', typed === '');
    await br.go('http://127.0.0.1:' + hport + '/one');
    const r4 = await br.signIn((u) => store.forPage(u));
    check('a plain-http page gets nothing', r4.kind === 'http' && posts.length === 0);
    // 5. a wrong saved password: the site says so -> "did not go through", never "signed in"
    await store.save(A, USER, 'wrong-pass-123');
    posts.length = 0;
    await br.go(A + '/strict');
    const r5 = await br.signIn((u) => store.forPage(u));
    check('a wrong saved password reports "did not go through" with the site\'s words', r5.kind === 'failed' && posts.length >= 1 && /did not go through: the page says "Wrong password/.test(r5.text) && !r5.text.includes('wrong-pass-123'), r5.text.split('\n')[0]);
    code = results.every((x) => x[1]) ? 0 : 1;
    srv.close(); plain.close();
  } catch (e) { console.log('ERROR', e && e.stack); code = 2; }
  finally {
    try { execFileSync('/usr/bin/security', ['delete-keychain', KC]); } catch (e) { /* gone */ }
    console.log('test keychain deleted:', !fs.existsSync(KC));
    try { fs.rmSync(TMP, { recursive: true, force: true }); } catch (e) { /* ignore */ }
    console.log('RESULT ' + results.filter((x) => x[1]).length + '/' + results.length + ' passed');
    app.exit(code);
  }
});
