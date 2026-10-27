'use strict';
// Real-Electron end-to-end test. Run: xvfb-run -a -s "-screen 0 1440x900x24" npx electron . --no-sandbox --e2e
// A fake gateway scripts the model; the real agent, browser views, popup, status pill and UI do the rest.
// main.js calls prepare() before the window exists (so the launch-time warm-up goes to the fake gateway), then run().
const http = require('http');
const path = require('path');
const fs = require('fs');
const { execFile } = require('child_process');
const { startGateway } = require('./helpers');

const OUT = path.join(__dirname, 'out');
const DOCS = path.join(__dirname, '..', 'docs', 'img');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function lastTool(req) { const m = req.messages.filter((x) => x.role === 'tool'); return m.length ? m[m.length - 1].content : ''; }
function idOf(text, re) { const m = new RegExp('\\[(\\d+)\\] ' + re).exec(text); if (!m) throw new Error('no element matching ' + re + ' in snapshot:\n' + text); return Number(m[1]); }

function startSite() {
  const page = (title, body) => '<!doctype html><meta charset=utf-8><title>' + title + '</title><body style="font:16px sans-serif;padding:30px;background:#fff;color:#222">' + body;
  const server = http.createServer((req, res) => {
    res.setHeader('content-type', 'text/html');
    const u = new URL(req.url, 'http://x');
    if (u.pathname === '/') res.end(page('Test Shop', '<h1>Test Shop</h1><form action="/results" method="get"><input id="q" name="q" placeholder="Search"> <button type="submit">Go</button></form><p>Welcome to the shop.</p>'));
    else if (u.pathname === '/results') res.end(page('Results', '<h1>Results for ' + (u.searchParams.get('q') || '') + '</h1><ul><li><a href="/item/2">Other thing</a></li><li><a href="/item/1">Premonition result</a></li></ul>'));
    else if (u.pathname.startsWith('/item/')) res.end(page('Item ' + u.pathname.split('/')[2], '<h1>Item ' + u.pathname.split('/')[2] + '</h1><p>The final page.</p>'));
    else if (u.pathname === '/login') res.end(page('Sign in to Test Mail', '<h1>Sign in</h1><input id="e" type="email" placeholder="Email" aria-label="Email"><br><br><input id="p" type="password" placeholder="Password" aria-label="Password"><br><br><button>Next</button>'));
    else { res.statusCode = 404; res.end('nope'); }
  });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r({ base: 'http://127.0.0.1:' + server.address().port, close: () => { server.closeAllConnections(); server.close(); } })));
}

// Called by main.js before the window is created. Starts the site + the scripted gateway and points the app at it.
async function prepare(store) {
  const site = await startSite();
  const checks = [];
  const gw = await startGateway([
    // task 1: browse (request 0 starts after the launch warm-up)
    () => ({ reasoning: 'The user wants the Premonition item. I should open the shop and search.', content: "Plan:\n1. Open the shop\n2. Search for premonition\n3. Open the matching result\n\nOpening the shop now.", tool_calls: [{ name: 'browser_go', arguments: { url: site.base + '/' } }] }),
    (req) => ({ content: 'I will type the query.\n[Action: Type premonition into the search box]\nTyping.', tool_calls: [{ name: 'browser_type', arguments: { id: idOf(lastTool(req), 'input\\(text\\) "Search"'), text: 'premonition', enter: true } }] }),
    (req) => { const t = lastTool(req); checks.push(['results page reached after typing + Enter', /\/results\?q=premonition/.test(t)]); return { holdMs: 2800, tool_calls: [{ name: 'browser_click', arguments: { id: idOf(t, 'link "Premonition result"') } }] }; },
    (req) => { checks.push(['click landed on item page', /\/item\/1/.test(lastTool(req))]); return { content: 'I found it: **Item 1** is the Premonition result. Opened at `/item/1`.\n[Action: Click Continue]' }; },
    // task 2: shell in Ask first mode, approval card
    () => ({ content: 'Checking.', tool_calls: [{ name: 'run_shell', arguments: { command: 'echo desk-e2e-ok' } }] }),
    (req) => { checks.push(['shell output reached model', /desk-e2e-ok/.test(lastTool(req))]); return { content: 'The shell printed desk-e2e-ok.' }; },
    // task 3: sign-in hand-off. The model tries to type into the password field; the app must not type
    () => ({ tool_calls: [{ name: 'browser_go', arguments: { url: site.base + '/login' } }] }),
    (req) => ({ tool_calls: [{ name: 'browser_type', arguments: { id: idOf(lastTool(req), 'input\\(password\\) "Password"'), text: 'hunter2-secret' } }] }),
    (req) => { const t = lastTool(req); checks.push(['hand-off result: Login needed + fresh snapshot', /^Login needed: Ben is signing in himself/.test(t) && /Fresh snapshot/.test(t) && /URL: /.test(t)]); checks.push(['the app never typed the secret: no tool result contains it', !req.messages.filter((m) => m.role === 'tool').some((m) => m.content.includes('hunter2-secret'))]); return { content: 'Thanks, you are signed in. I can carry on now.' }; },
    // task 4: steer once
    () => ({ holdMs: 1800, content: 'On it.', tool_calls: [{ name: 'browser_go', arguments: { url: site.base + '/' } }] }),
    (req) => { const n = req.messages.filter((m) => m.role === 'user' && /use the blue one/.test(m.content)).length; checks.push(['steer injected exactly once', n === 1]); return { content: 'Switched to blue.' }; },
    // task 5: open_app(Safari) is refused
    () => ({ content: 'Opening Safari.', tool_calls: [{ name: 'open_app', arguments: { name: 'Safari' } }] }),
    (req) => { const t = lastTool(req); checks.push(['open_app refused Safari with a browser_go hint', /browser_go/.test(t) && /do not open a web browser/i.test(t)]); return { content: 'Right, I will use the built-in browser instead.' }; }
  ]);
  store.saveSettings({ gatewayUrl: gw.url, mode: 'hands-off', maxSteps: 20, helperMode: 'hands-off' });
  return { site, gw, checks };
}

// DOM contrast audit (WCAG): every visible text element against its composited background.
const AUDIT = `(() => {
  const parse = (c) => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return [0,0,0,0]; const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const over = (f, b) => [f[0]*f[3]+b[0]*(1-f[3]), f[1]*f[3]+b[1]*(1-f[3]), f[2]*f[3]+b[2]*(1-f[3]), 1];
  const lum = (c) => { const [r,g,b] = c.slice(0,3).map((v) => { v/=255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); }); return .2126*r+.7152*g+.0722*b; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
  const bgOf = (e) => { const chain = []; for (let n = e; n; n = n.parentElement) chain.push(parse(getComputedStyle(n).backgroundColor)); let c = [0,0,0,1]; for (let i = chain.length - 1; i >= 0; i--) c = over(chain[i], c); return c; };
  const bad = []; let n = 0;
  for (const e of document.querySelectorAll('body *')) {
    if (!e.offsetParent && getComputedStyle(e).position !== 'fixed') continue;
    const direct = [...e.childNodes].some((x) => x.nodeType === 3 && x.textContent.trim());
    const isInput = /^(INPUT|TEXTAREA)$/.test(e.tagName);
    if (!direct && !isInput) continue;
    const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
    if (cs.visibility === 'hidden' || r.width < 2 || r.height < 2 || r.right <= 0 || r.left >= innerWidth) continue; // (off-screen drawer)
    const bg = bgOf(e); let fg = parse(cs.color);
    let op = 1; for (let k = e; k; k = k.parentElement) op *= Number(getComputedStyle(k).opacity);
    if (op < 0.05) continue; // fully transparent (hover-only notes)
    fg = [fg[0], fg[1], fg[2], fg[3] * op];
    const f = over(fg, bg);
    const size = parseFloat(cs.fontSize), bold = Number(cs.fontWeight) >= 700;
    const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
    n++;
    const rt = ratio(f, bg);
    if (rt < need) bad.push((e.className || e.tagName) + ' "' + (e.textContent || e.value || '').trim().slice(0, 24) + '" ' + rt.toFixed(2));
    if (isInput && e.placeholder) { const pc = parse(getComputedStyle(e, '::placeholder').color); const pr = ratio(over(pc, bg), bg); if (pr < 4.5) bad.push('placeholder "' + e.placeholder + '" ' + pr.toFixed(2)); }
  }
  return { n, bad };
})()`;

async function run({ app, win, store, helpers, browsers, pillWin, pillState, warmer, applySettings, env, pending, loginWaits, timing, getWin, showWindow }) {
  const fail = (m) => { console.error('E2E FAIL: ' + m); app.exit(1); };
  const timer = setTimeout(() => fail('timeout'), 170000);
  const wc = win.webContents;
  const ev = (code) => wc.executeJavaScript(code);
  const pev = (code) => pillWin.win.webContents.executeJavaScript(code);
  const { site, gw, checks } = env;
  try {
    fs.mkdirSync(OUT, { recursive: true }); fs.mkdirSync(DOCS, { recursive: true });
    win.setBounds({ x: 0, y: 0, width: 1100, height: 860 });
    const { nativeTheme } = require('electron');
    // Screenshots: the chat window via capturePage (a see-through background popup can sit above it under xvfb, which has no
    // compositor); root=true grabs the whole X screen (popup windows).
    const grab = (file, root) => new Promise((resolve) => {
      const shot = path.join(OUT, file);
      try { fs.unlinkSync(shot); } catch (e) { /* none yet */ }
      const done = () => { fs.copyFileSync(shot, path.join(DOCS, file)); console.log('SCREENSHOT ' + shot); resolve(shot); };
      if (!root) return wc.capturePage().then((img) => { fs.writeFileSync(shot, img.toPNG()); done(); });
      execFile('import', ['-window', 'root', shot], { env: process.env }, async (err) => {
        if (err || !fs.existsSync(shot)) { try { fs.writeFileSync(shot, (await wc.capturePage()).toPNG()); } catch (e) { /* ignore */ } }
        done();
      });
    });
    const grabPill = async (file, bg) => {
      const img = (await pillWin.win.webContents.capturePage()).toPNG();
      const raw = path.join(OUT, 'raw-' + file); fs.writeFileSync(raw, img);
      const out = path.join(OUT, file);
      await new Promise((r) => execFile('convert', [raw, '-background', bg, '-alpha', 'remove', '-alpha', 'off', '-trim', '+repage', '-bordercolor', bg, '-border', '24', out], () => r()));
      if (!fs.existsSync(out)) fs.copyFileSync(raw, out);
      fs.unlinkSync(raw);
      fs.copyFileSync(out, path.join(DOCS, file)); console.log('SCREENSHOT ' + out);
    };
    await ev('new Promise(r=>{const t=setInterval(()=>{if(window.__ready){clearInterval(t);r()}},50)})');

    // ---- startup: the window shows first, the heavy things are deferred and lazy
    checks.push(['window shown on ready-to-show before deferred startup work', !!timing.readyToShow && timing.readyToShow <= timing.deferred]);
    checks.push(['no browser view exists at first paint (lazy)', timing.browsersAtPaint === 0]);
    checks.push(['helpers scheduler not started before first paint', timing.helpersTimerAtPaint === false]);

    // ---- warm-up on launch (to the fake gateway), with the warm header, before any real request
    for (let i = 0; i < 100 && !gw.warms.length; i++) await sleep(100);
    checks.push(['warm request sent on launch', gw.warms.length >= 1 && gw.requests.length === 0]);
    checks.push(['warm request has X-Premonition-Warm: 1', !!gw.warms[0] && gw.warms[0].headers['x-premonition-warm'] === '1']);
    checks.push(['warm request: qwen36-fast, non-streaming, max_tokens 1, user "."', !!gw.warms[0] && gw.warms[0].body.model === 'qwen36-fast' && gw.warms[0].body.stream === false && gw.warms[0].body.max_tokens === 1 && gw.warms[0].body.messages[1].content === '.']);
    await sleep(300);
    checks.push(['top bar shows Ready after warming', await ev('document.querySelector("#gw").classList.contains("ready") && /Ready/.test(document.querySelector("#gw").textContent)')]);

    // ---- layout: chat only, centered column, bigger text
    checks.push(['no permanent work pane or splitter', await ev('!document.querySelector("#work") && !document.querySelector("#splitter") && !document.querySelector(".tabs")')]);
    checks.push(['base font is at least 16px', (await ev('parseFloat(getComputedStyle(document.body).fontSize)')) >= 16]);
    checks.push(['chat column is centered and at most 760px', await ev('(() => { const r = document.querySelector("#msgs").getBoundingClientRect(); return r.width <= 761 && Math.abs(r.left - (innerWidth - r.right)) < 3; })()')]);
    checks.push(['empty state: Glim greeting + 4 chips', await ev('!!document.querySelector(".welcome .mascot") && document.querySelectorAll(".welcome .chips button").length===4')]);
    checks.push(['chrome is not selectable, message text is', await ev('getComputedStyle(document.querySelector("#topbar")).userSelect==="none" && getComputedStyle(document.querySelector(".welcome")).userSelect==="none" && getComputedStyle(document.querySelector("#input")).userSelect!=="none"')]);
    await ev('document.querySelector(".welcome .chips button").click()');
    checks.push(['suggestion chip fills the composer', (await ev('document.querySelector("#input").value')).length > 5]);
    await ev('(()=>{const i=document.querySelector("#input");i.value="";i.dispatchEvent(new Event("input"))})()');
    await sleep(200);
    await grab('ui-v2-welcome.png');

    const send = (text) => ev('(()=>{const i=document.querySelector("#input");i.value=' + JSON.stringify(text) + ';i.dispatchEvent(new Event("input"));document.querySelector("#btnSend").click();})()');
    const waitIdle = async (label) => {
      for (let i = 0; i < 600; i++) {
        const st = await ev('({stop:!document.querySelector("#btnStop").hidden, err:(document.querySelector(".errline")||{}).textContent||""})');
        if (st.err) throw new Error(label + ': UI error: ' + st.err);
        if (!st.stop && i > 5) return;
        await sleep(200);
      }
      throw new Error(label + ': did not finish');
    };
    const until = async (fn, ms) => { for (let i = 0; i < (ms || 8000) / 100; i++) { if (await fn()) return true; await sleep(100); } return false; };
    const brs = () => browsers.get('primary');

    // ---- composer guard: a password-looking message is stopped (Send anyway / Cancel)
    await ev('(()=>{const i=document.querySelector("#input");i.value="my password is hunter2";i.dispatchEvent(new Event("input"));document.querySelector("#btnSend").click();})()');
    await sleep(150);
    checks.push(['password guard warns and does not send', await ev('!document.querySelector("#pwWarn").hidden && /Don.t paste passwords here; I.ll open a sign-in window instead/.test(document.querySelector("#pwWarn").textContent) && !document.querySelector(".user") && document.querySelector("#input").value.length>0')]);
    await grab('ui-v2-password-guard.png');
    await ev('document.querySelector("#pwCancel").click()');
    checks.push(['Cancel keeps the text, hides the warning, sends nothing', await ev('document.querySelector("#pwWarn").hidden && document.querySelector("#input").value==="my password is hunter2" && !document.querySelector(".user")') && gw.requests.length === 0]);
    await ev('(()=>{const i=document.querySelector("#input");i.value="";i.dispatchEvent(new Event("input"))})()');

    // ---- task 1: browse (Hands-off). While the model is "thinking" on the last step, use the popup.
    await send('Find the premonition item in the test shop');
    checks.push(['browser card appears inline in the chat', await until(() => ev('!!document.querySelector(".activity .bcard")'), 12000)]);
    checks.push(['card shows title/url of the page', await until(() => ev('/127\\.0\\.0\\.1/.test((document.querySelector(".bcard .bc-url")||{}).textContent||"")'))]);
    checks.push(['card has a live thumbnail (data: JPEG)', await until(() => ev('(()=>{const i=document.querySelector(".bcard .bc-thumb img");return !!i && i.src.startsWith("data:image/jpeg")})()'), 8000)]);
    await grab('ui-v2-running.png');
    checks.push(['card says Glim is browsing while active', await until(() => ev('document.querySelector(".bcard").classList.contains("active") && /Glim is browsing/.test(document.querySelector(".bcard").textContent)'))]);
    checks.push(['activity group shows a live step line while running', await ev('!!document.querySelector(".activity.running .act-live .t") && document.querySelector(".activity.running .act-live .t").textContent.length>3')]);
    checks.push(['popup is hidden until the card is clicked', !brs().popup.isVisible()]);
    // wait for the held step (the click request): the run is mid-flight
    await until(async () => gw.requests.length >= 3, 12000);
    await ev('document.querySelector(".bcard").click()');
    checks.push(['clicking the card opens the browser popup', await until(() => brs().popup.isVisible(), 5000)]);
    await sleep(500);
    const pop = brs().popup;
    checks.push(['popup shows the real live page (results)', /\/results\?q=premonition/.test(pop.view.webContents.getURL())]);
    checks.push(['popup has address bar showing the URL', /results\?q=premonition/.test(await pop.win.webContents.executeJavaScript('document.querySelector("#addr").value'))]);
    checks.push(['popup shows who is in control (Glim is browsing)', /Glim is browsing/.test(await pop.win.webContents.executeJavaScript('document.querySelector("#who").textContent'))]);
    checks.push(['popup page sits under the toolbar (58px)', pop.view.getBounds().y === 58]);
    await grab('ui-v2-popup.png', true);
    // Ben can use the page himself: scroll it from his side (real input into the popup page)
    pop.view.webContents.sendInputEvent({ type: 'mouseWheel', x: 200, y: 200, deltaX: 0, deltaY: -50 });
    await pop.win.webContents.executeJavaScript('document.querySelector("#close").click()');
    checks.push(['closing the popup hides it', await until(() => !pop.isVisible(), 3000)]);
    checks.push(['closing the popup does not stop the agent', await ev('!document.querySelector("#btnStop").hidden')]);
    await waitIdle('task1');
    await sleep(700);
    const url = brs().br.wc.getURL();
    checks.push(['agent went on and ended on /item/1', url === site.base + '/item/1']);
    checks.push(['run state cleared (Send shown, Stop hidden)', await ev('document.querySelector("#btnStop").hidden && document.querySelector("#runState").hidden && document.querySelector("#btnSend").textContent==="Send"')]);
    checks.push(['final answer rendered prominently', await ev('/Premonition result/.test((document.querySelector(".acol > .atext")||{}).textContent||"")')]);
    checks.push(['markdown bold rendered', await ev('!!document.querySelector(".atext strong")')]);
    checks.push(['[Action: ...] lines are hidden', await ev('!/\\[Action/i.test(document.body.innerText)')]);
    checks.push(['one activity group: "Did 3 things" collapsed after the run', await ev('document.querySelectorAll(".activity").length===1 && /Did 3 things/.test(document.querySelector(".act-head").textContent) && !document.querySelector(".activity").classList.contains("open")')]);
    checks.push(['chevron sits next to the label (not far right)', await ev('(() => { const t = document.querySelector(".act-title").getBoundingClientRect(), c = document.querySelector(".act-head .chev").getBoundingClientRect(); return c.left - t.right < 160; })()')]);
    checks.push(['card kept, no longer "browsing" after the run', await ev('!!document.querySelector(".bcard") && !document.querySelector(".bcard").classList.contains("active") && /Click to open/.test(document.querySelector(".bcard").textContent)')]);
    checks.push(['one assistant avatar per block', (await ev('document.querySelectorAll(".ablock > .avatar").length')) === 1]);
    await ev('document.querySelector(".act-head").click()');
    checks.push(['expanding shows plan, narration and step pills with icons', await ev('!!document.querySelector(".plan") && document.querySelectorAll(".plan li").length===3 && document.querySelectorAll(".step .pill svg").length>=3 && !!document.querySelector(".nar")')]);
    checks.push(['thinking block collapsed', await ev('!!document.querySelector("details.think:not([open])")')]);
    checks.push(['TTFT shown on the answer (hover note)', await ev('/first word in/.test((document.querySelector(".acol > .atext .ttft")||{}).textContent||"")')]);
    await sleep(400);
    for (const [theme, file] of [['light', 'ui-v2-light.png'], ['dark', 'ui-v2-dark.png']]) {
      nativeTheme.themeSource = theme;
      await sleep(700);
      checks.push(['page follows ' + theme + ' theme', await ev('matchMedia("(prefers-color-scheme: ' + theme + ')").matches')]);
      const a = await ev(AUDIT);
      console.log('contrast audit (' + theme + ', chat): ' + a.n + ' text elements, ' + a.bad.length + ' below AA' + (a.bad.length ? ': ' + a.bad.join(' | ') : ''));
      checks.push(['text contrast AA in chat (' + theme + ')', a.bad.length === 0]);
      await grab(file);
    }
    nativeTheme.themeSource = 'dark'; await sleep(400);

    // ---- task 2: Ask first -> approval card -> allow
    store.saveSettings({ mode: 'ask' });
    await send('Run echo to check the shell');
    const hasCard = await until(() => ev('!!document.querySelector(".card .amber-btn")'), 10000);
    checks.push(['approval card shown in Ask first', hasCard]);
    checks.push(['pill shows Waiting for you with Allow/Deny', await until(async () => /Waiting for you/.test(await pev('document.querySelector("#line").textContent')), 4000)]);
    await ev('document.querySelector(".card .amber-btn").click()');
    await waitIdle('task2');
    checks.push(['task2 finished after approval', await ev('document.body.innerText.includes("desk-e2e-ok")')]);
    store.saveSettings({ mode: 'hands-off' });

    // ---- task 3: sign-in hand-off
    await send('Log in to the test mail site');
    checks.push(['hand-off: agent waits for Ben (login wait registered)', await until(async () => loginWaits.size > 0, 15000)]);
    const pop2 = brs().popup;
    checks.push(['hand-off: popup opens by itself', await until(() => pop2.isVisible(), 4000)]);
    await sleep(500);
    checks.push(['hand-off: banner says Sign in here yourself; Glim can\'t see what you type', await pop2.win.webContents.executeJavaScript('!document.querySelector("#banner").hidden && /Sign in here yourself; Glim can.t see what you type\\. Click Done when finished\\./.test(document.querySelector("#banner").textContent)')]);
    checks.push(['hand-off: the password field is still empty (nothing typed)', (await pop2.view.webContents.executeJavaScript('document.querySelector("#p").value')) === '']);
    checks.push(['hand-off: page is below toolbar + banner (118px)', pop2.view.getBounds().y === 118]);
    checks.push(['hand-off: chat card says sign-in needed', await until(() => ev('!!document.querySelector(".bcard.login") && /Sign-in needed/.test(document.querySelector(".bcard.login").textContent)'), 3000)]);
    checks.push(['hand-off: pill shows waiting for sign-in', await until(async () => /sign in/i.test(await pev('document.querySelector("#line").textContent')), 4000)]);
    checks.push(['after sending, the transcript is scrolled to the bottom', await until(() => ev('(() => { const s = document.querySelector("#scroll"); return s.scrollHeight - s.scrollTop - s.clientHeight < 4; })()'), 3000)]);
    checks.push(['the last message is not covered by the composer', await ev('(() => { const all = [...document.querySelectorAll("#msgs > *")]; const last = all[all.length - 1].getBoundingClientRect(); const c = document.querySelector("#composer").getBoundingClientRect(); return last.bottom <= c.top + 1; })()')]);
    checks.push(['narration lines are single-line with ellipsis, never clipped', await ev('[...document.querySelectorAll(".nar")].every((n) => getComputedStyle(n).whiteSpace === "nowrap" && n.clientHeight >= parseFloat(getComputedStyle(n).lineHeight) - 1)')]);
    checks.push(['top status and composer agree while working', await ev('/Working|Waiting/.test(document.querySelector("#gw").textContent) && document.querySelector("#gw span").textContent === document.querySelector("#runState span").textContent')]);
    checks.push(['hand-off: agent still waiting (no further request)', gw.requests.length === 8]);
    await grab('ui-v2-signin.png', true);
    // Ben types his password himself (real key events into the page), then clicks Done
    await pop2.view.webContents.executeJavaScript('document.querySelector("#p").focus()');
    pop2.view.webContents.insertText('benspassword');
    await sleep(200);
    await pop2.win.webContents.executeJavaScript('document.querySelector("#done").click()');
    await waitIdle('task3');
    checks.push(['hand-off: popup closes after Done and the agent continued', !pop2.isVisible() && gw.requests.length === 9]);
    checks.push(['hand-off: the model never saw what Ben typed', !JSON.stringify(gw.requests).includes('benspassword')]);
    checks.push(['hand-off: final answer shown', await ev('document.body.innerText.includes("you are signed in")')]);

    // ---- task 4: steer once (typed once -> one bubble, injected once)
    await send('Open the shop');
    await until(() => ev('!document.querySelector("#btnStop").hidden'), 3000);
    await until(async () => gw.requests.length >= 10, 6000);
    await sleep(200);
    await send('use the blue one');
    await waitIdle('task4');
    checks.push(['steer shown once in the chat (no duplicate STEER bubble)', (await ev('document.querySelectorAll(".user.steer").length')) === 1 && (await ev('[...document.querySelectorAll(".user")].filter((u) => /use the blue one/.test(u.textContent)).length')) === 1]);
    checks.push(['steer bubble confirmed (no longer queued)', await ev('!document.querySelector(".user.steer").classList.contains("queued")')]);
    checks.push(['steer saved once in the thread', (() => { const l = store.listThreads(); const t = store.loadThread(l[0].id); return t.items.filter((i) => i.t === 'user' && /use the blue one/.test(i.text)).length === 1 && t.messages.filter((m) => m.role === 'user' && /use the blue one/.test(m.content)).length === 1; })()]);

    // ---- task 5: open_app(Safari) refused
    await send('Open Safari and look something up');
    await waitIdle('task5');
    checks.push(['open_app Safari: refusal visible as a failed step', await ev('document.querySelectorAll(".step.bad").length>=1')]);

    // ---- persistence
    await sleep(300);
    const list = store.listThreads();
    const t = list.length ? store.loadThread(list[0].id) : null;
    checks.push(['thread saved with a browser card item and thumbnail', !!t && t.items.some((i) => i.t === 'browser' && i.thumb && i.thumb.startsWith('data:image/jpeg') && i.url)]);
    checks.push(['thread titled from first message', !!t && /premonition item/.test(t.title)]);
    checks.push(['thread logs time to first token per request', !!t && t.requests.length >= 10 && t.requests.every((r) => typeof r.ttftMs === 'number')]);
    checks.push(['model got date-prefixed user message', /^\[\w{3} \d{4}-/.test(gw.requests[0].messages.find((m) => m.role === 'user').content)]);
    // the warm request and the first real request share the identical system + tools prefix
    const w0 = gw.warms[0].body, r0 = gw.requests[0];
    checks.push(['warm request has the identical system + tools + tool_choice as the real request', JSON.stringify(w0.messages[0]) === JSON.stringify(r0.messages[0]) && JSON.stringify(w0.tools) === JSON.stringify(r0.tools) && w0.tool_choice === r0.tool_choice && w0.tool_choice === 'auto']);
    checks.push(['every real request carries the same tools array', gw.requests.every((r) => JSON.stringify(r.tools) === JSON.stringify(r0.tools))]);
    // reopen the thread: the card and the grouping come back
    await ev('document.querySelector("#btnThreads").click()');
    await sleep(300);
    await ev('document.querySelector("#threadList li").click()');
    await sleep(600);
    checks.push(['reopened thread restores browser card + activity groups', await ev('!!document.querySelector(".bcard .bc-thumb img") && document.querySelectorAll(".activity").length>=3')]);

    // ---- settings sheet: every setting editable, applied at once and persisted
    await ev('window.__openSettings()');
    await sleep(300);
    const keys = ['gatewayUrl', 'model', 'mode', 'helperMode', 'maxSteps', 'maxParallel', 'diaryEnabled', 'diaryPath', 'pythonPath', 'helperPath', 'vision', 'theme', 'textSize', 'highContrast', 'pill', 'openAtLogin', 'keepRunning', 'hotkey'];
    checks.push(['settings sheet has a control for every setting', await ev('document.querySelectorAll("#settingsCol .s-row").length>=' + keys.length + ' && ' + JSON.stringify(['Model', 'Autonomy', 'Helpers', 'Memory', 'Screen control', 'Vision', 'Appearance', 'Startup']) + '.every((g)=>[...document.querySelectorAll(".s-group h2")].some((h)=>h.textContent===g))')]);
    checks.push(['settings: test connection button shows latency', await (async () => { await ev('document.querySelector("#testConn").click()'); return until(() => ev('/Connected · \\d+ ms/.test(document.querySelector("#testNote").textContent)'), 5000); })()]);
    checks.push(['settings: Open Accessibility / Screen Recording buttons present', await ev('[...document.querySelectorAll("#settingsCol button")].some((b)=>/Open Accessibility settings/.test(b.textContent)) && [...document.querySelectorAll("#settingsCol button")].some((b)=>/Open Screen Recording settings/.test(b.textContent))')]);
    checks.push(['settings: danger list shown', await ev('document.querySelectorAll(".danger-list li").length>=8')]);
    const clickSeg = (label) => ev('[...document.querySelectorAll("#settingsCol .seg button")].find((b)=>b.textContent==="' + label + '" && b.offsetParent).click()');
    const warmsBefore = gw.warms.length;
    await ev('(() => { const b=[...document.querySelectorAll("#settingsCol .seg")].find((s)=>s.querySelector("button[data-v=qwen36-fast]")); b.querySelector("button[data-v=qwen36-fast]").click(); })()');
    await sleep(500);
    checks.push(['settings: default mode saved at once', store.getSettings().model === 'qwen36-fast']);
    checks.push(['settings: changing the model re-warms', await until(async () => gw.warms.length > warmsBefore, 5000)]);
    await ev('[...document.querySelectorAll("#settingsCol .seg")].find((s)=>s.querySelector("button[data-v=qwen36-auto]")).querySelector("button[data-v=qwen36-auto]").click()');
    await ev('[...document.querySelectorAll("#settingsCol .seg")].find((s)=>s.querySelector("button[data-v=l]")).querySelector("button[data-v=l]").click()');
    await sleep(300);
    checks.push(['settings: text size L applies immediately and persists', store.getSettings().textSize === 'l' && await ev('document.documentElement.classList.contains("ts-l") && parseFloat(getComputedStyle(document.body).fontSize)>=18')]);
    await ev('[...document.querySelectorAll("#settingsCol .seg")].find((s)=>s.querySelector("button[data-v=m]")).querySelector("button[data-v=m]").click()');
    await ev('document.querySelector("#settingsCol input[type=number]").value="12"; document.querySelector("#settingsCol input[type=number]").dispatchEvent(new Event("change"))');
    await sleep(400);
    checks.push(['settings: max steps edited and persisted', store.getSettings().maxSteps === 12]);
    await ev('document.querySelector("#settingsCol input[type=number]").value="40"; document.querySelector("#settingsCol input[type=number]").dispatchEvent(new Event("change"))');
    await ev('[...document.querySelectorAll("#settingsCol .seg")].find((s)=>s.querySelector("button[data-v=light]")).querySelector("button[data-v=light]").click()');
    await sleep(700);
    checks.push(['settings: theme Light applies immediately (nativeTheme)', await ev('matchMedia("(prefers-color-scheme: light)").matches') && store.getSettings().theme === 'light']);
    await ev('document.querySelector("#settingsCol [aria-label=\\"High contrast\\"]").click()');
    await sleep(300);
    checks.push(['settings: high contrast toggles the html class', store.getSettings().highContrast === true && await ev('document.documentElement.classList.contains("hc")')]);
    {
      const a = await ev(AUDIT);
      console.log('contrast audit (light + high contrast, settings): ' + a.n + ' text elements, ' + a.bad.length + ' below AA' + (a.bad.length ? ': ' + a.bad.join(' | ') : ''));
      checks.push(['text contrast AA in settings (light, high contrast)', a.bad.length === 0]);
    }
    await ev('document.querySelector("#settingsCol [aria-label=\\"High contrast\\"]").click()');
    await ev('[...document.querySelectorAll("#settingsCol .seg")].find((s)=>s.querySelector("button[data-v=dark]")).querySelector("button[data-v=dark]").click()');
    await sleep(700);
    {
      const a = await ev(AUDIT);
      console.log('contrast audit (dark, settings): ' + a.n + ' text elements, ' + a.bad.length + ' below AA' + (a.bad.length ? ': ' + a.bad.join(' | ') : ''));
      checks.push(['text contrast AA in settings (dark)', a.bad.length === 0]);
    }
    await grab('ui-v2-settings.png');
    checks.push(['settings: default hotkey is Alt+Space (Option+Space), keep running on, open at login off', store.getSettings().hotkey === 'Alt+Space' && store.getSettings().keepRunning === true && store.getSettings().openAtLogin === false]);
    await ev('document.querySelector("#settingsClose").click()');

    // ---- keep running: closing the window hides it, the app and its scheduler keep going
    getWin().close();
    await sleep(300);
    checks.push(['closing the window hides it (keep running in background)', !win.isDestroyed() && !win.isVisible() && !!helpers.timer]);
    showWindow(true);
    await sleep(300);
    checks.push(['showing it again brings the same window back', win.isVisible()]);

    // ---- helper run: its own browser, card in the helper's thread, notice in the primary thread
    const primaryUrl = brs().br.wc.getURL();
    const gw2 = await startGateway([(req) => {
      const first = req.messages.find((m) => m.role === 'user').content;
      const last = req.messages[req.messages.length - 1];
      if (/You are helper 'site-checker'/.test(first)) {
        if (last.role !== 'tool') return { tool_calls: [{ name: 'browser_go', arguments: { url: site.base + '/' } }] };
        checks.push(['helper got the page snapshot from its own browser', /Title: Test Shop/.test(last.content)]);
        return { content: 'Report: the shop home page says Welcome to the shop.' };
      }
      if (last.role === 'tool') return { content: 'The helper is on it.' };
      return { tool_calls: [{ name: 'agent_start', arguments: { name: 'site-checker', task: 'open the test shop and report its home page' } }] };
    }]);
    store.saveSettings({ gatewayUrl: gw2.url });
    warmer.gatewayMoved();
    await send('Please have a helper check the shop home page');
    await waitIdle('helper');
    let helperThread = null;
    for (let i = 0; i < 150 && !helperThread; i++) {
      await sleep(200);
      const ht = store.listThreads().find((x) => x.helper);
      const full = ht && store.loadThread(ht.id);
      if (full && full.messages.some((m) => m.role === 'assistant' && /^Report:/.test(m.content || ''))) helperThread = full;
    }
    checks.push(['helper thread saved with its report', !!helperThread]);
    checks.push(['helper thread has its browser_go step and a browser card', !!helperThread && helperThread.items.some((i) => i.t === 'step' && i.tool === 'browser_go') && helperThread.items.some((i) => i.t === 'browser' && i.key === helperThread.id)]);
    checks.push(['primary browser untouched by the helper', brs().br.wc.getURL() === primaryUrl]);
    checks.push(['helper browser is gone after its run', !browsers.has(helperThread.id)]);
    checks.push(['notice shown in the primary thread', await until(() => ev('!!document.querySelector(".notice")'), 5000)]);
    const h0 = helpers.list()[0];
    checks.push(['helper listed idle with a summary', !!h0 && h0.status === 'idle' && /home page/.test(h0.lastSummary)]);
    await ev('document.querySelector("#btnThreads").click()');
    await sleep(300);
    checks.push(['Agents section lists the helper', await ev('!document.querySelector("#agentsSec").hidden && document.querySelectorAll("#agentList li").length===1 && /site-checker/.test(document.querySelector("#agentList").innerText)')]);
    await ev('document.querySelector("#agentList li").click()');
    await sleep(600);
    checks.push(['opening the helper thread shows its card and steps', await ev('!!document.querySelector(".bcard") && document.querySelectorAll(".step").length>=1 && /Report:/.test(document.body.innerText)')]);
    gw2.close();

    // ---- error path: gateway gone -> the pill shows the sad Glim with details
    store.saveSettings({ gatewayUrl: 'http://127.0.0.1:1/v1' });
    await ev('document.querySelector("#newThread").click()');
    await sleep(300);
    await ev('(()=>{const i=document.querySelector("#input");i.value="hello?";i.dispatchEvent(new Event("input"));document.querySelector("#btnSend").click();})()');
    checks.push(['error: chat shows the error line', await until(() => ev('!!document.querySelector(".errline")'), 8000)]);
    checks.push(['error: pill says Something went wrong with sad Glim', await until(async () => /Something went wrong/.test(await pev('document.querySelector("#line").textContent')) && (await pev('document.querySelector("#pill .mascot").dataset.mood')) === 'error', 4000)]);
    checks.push(['pill window: always on top, all workspaces, no focus', pillWin.win.isAlwaysOnTop() && pillWin.win.isFocusable() === false]);
    checks.push(['pill window sits at the top center of the screen', (() => { const b = pillWin.win.getBounds(); return b.y <= 10 && Math.abs((b.x + b.width / 2) - 720) < 200 || b.y <= 10; })()]);
    await pev('window.__open()');
    await sleep(700);
    checks.push(['pill expanded: shows the error text, elapsed time and buttons', await pev('document.querySelector("#pill").classList.contains("open") && !document.querySelector("#dErr").hidden && /fetch failed|ECONN|Failed|failed/i.test(document.querySelector("#dErr").textContent) && [...document.querySelectorAll("#btns button")].some((b)=>b.textContent==="Open")')]);
    const pillAudit = async (label) => { const a = await pev(AUDIT); console.log('contrast audit (' + label + ', pill): ' + a.n + ' text elements, ' + a.bad.length + ' below AA' + (a.bad.length ? ': ' + a.bad.join(' | ') : '')); checks.push(['text contrast AA in the pill (' + label + ')', a.bad.length === 0]); };
    for (const [theme, bg] of [['dark', '#3b4252'], ['light', '#9aa7b8']]) {
      nativeTheme.themeSource = theme; await sleep(700);
      await pev('window.__open()'); await sleep(500);
      await pillAudit(theme + ' expanded');
      await grabPill('ui-v2-pill-expanded-' + theme + '.png', bg);
      await pev('window.__close()'); await sleep(500);
      await grabPill('ui-v2-pill-collapsed-' + theme + '.png', bg);
    }
    // a working state for the docs: synthetic events through the same state source
    pillState.dismiss('main');
    pillState.onEvent('main', 'Glim', 'tx', { type: 'started' });
    pillState.onEvent('main', 'Glim', 'tx', { type: 'step_start', summary: 'Opened gmail.com' }, { title: 'Check my email' });
    await sleep(500);
    for (const [theme, bg] of [['dark', '#3b4252'], ['light', '#9aa7b8']]) {
      nativeTheme.themeSource = theme; await sleep(600);
      await pev('window.__close()'); await sleep(400);
      await grabPill('ui-v2-pill-working-' + theme + '.png', bg);
    }
    pillState.dismiss('main');
    await sleep(300);
    checks.push(['pill hides again when nothing is going on', await pev('document.querySelector("#pill").classList.contains("gone")')]);
    nativeTheme.themeSource = 'system';
    store.saveSettings({ gatewayUrl: gw.url });

    let bad = 0;
    for (const [name, ok] of checks) { console.log((ok ? 'PASS ' : 'FAIL ') + name); if (!ok) bad++; }
    clearTimeout(timer);
    gw.close(); site.close();
    console.log(bad ? 'E2E FAILED (' + bad + ')' : 'E2E OK');
    app.exit(bad ? 1 : 0);
  } catch (e) {
    clearTimeout(timer);
    const bad = checks.filter(([, ok]) => !ok).map(([n]) => n);
    if (bad.length) console.error('failed so far: ' + bad.join('; '));
    fail(e.stack || e.message);
  }
}

module.exports = { run, prepare };
