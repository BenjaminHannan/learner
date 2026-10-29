'use strict';
// Real-Electron end-to-end test. Run: xvfb-run -a -s "-screen 0 1440x900x24" npx electron . --no-sandbox --e2e
// A fake gateway scripts the model; the real agent, browser views, in-window browser panel, status pill and UI do the rest.
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
    () => ({ content: 'Checking.', tool_calls: [{ name: 'run_shell', arguments: { command: 'mkdir -p /tmp/desk-e2e-dir && echo desk-e2e-ok' } }] }),
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
    (req) => { const t = lastTool(req); checks.push(['open_app refused Safari with a browser_go hint', /browser_go/.test(t) && /do not open a web browser/i.test(t)]); return { content: 'Right, I will use the built-in browser instead.' }; },
    // task 6: Glim asks a question; once Ben answers, only the question and his answer stay
    () => ({ content: 'Checking something.', tool_calls: [{ name: 'ask_user', arguments: { question: 'Which colour do you want?' } }] }),
    (req) => { checks.push(['ask: the answer reached the model', /teal please/.test(lastTool(req))]); return { content: 'Teal it is.' }; }
  ], { autoVerify: true }); // verify layer: the agent's self-check turn is answered VERIFIED without using up the script
  store.saveSettings({ gatewayUrl: gw.url, mode: 'hands-off', maxSteps: 20, helperMode: 'hands-off', onboarded: true }); // first-run setup has its own section at the end
  // sleep mode: a fake `python -m sleepmode` (test/fake-sleepmode.js) in the app's own temp dir, so nothing real is touched
  const sleepHome = path.join(store.dir, 'sleepmode');
  fs.mkdirSync(path.join(sleepHome, 'app'), { recursive: true });
  store.saveSettings({ sleepPython: path.join(__dirname, 'fake-sleepmode.js') });
  Object.assign(process.env, { FAKE_SLEEP_HOURS: '2.5', FAKE_SLEEP_CHECKIN: '1', FAKE_SLEEP_PERMISSION: '1' });
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

async function run({ app, win, ui, panel, holds, store, memory, sleeper, sl, autoSleepTick, helpers, browsers, pillWin, pillState, warmer, applySettings, env, pending, loginWaits, timing, getWin, showWindow, permsFake }) {
  const fail = (m) => { console.error('E2E FAIL: ' + m); app.exit(1); };
  const timer = setTimeout(() => fail('timeout'), 170000);
  const wc = ui.webContents;
  const { BrowserWindow } = require('electron');
  const ev = (code) => wc.executeJavaScript(code).catch((e) => { console.log('EV ERROR:', String(e.message).slice(0, 120), '|', String(code).slice(0, 220)); throw e; });
  const pev = (code) => pillWin.win.webContents.executeJavaScript(code);
  const { site, gw, checks } = env;
  try {
    fs.mkdirSync(OUT, { recursive: true }); fs.mkdirSync(DOCS, { recursive: true });
    win.setBounds({ x: 0, y: 0, width: 1100, height: 860 });
    const { nativeTheme } = require('electron');
    // Screenshots: the UI view via capturePage; root=true grabs the whole X screen (UI + the page view in the panel).
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
    checks.push(['top bar shows Glimmering after warming', await ev('document.querySelector("#gw").classList.contains("ready") && /Glimmering/.test(document.querySelector("#gw").textContent)')]);

    // ---- layout: chat only, centered column, bigger text
    checks.push(['no permanent work pane or splitter', await ev('!document.querySelector("#work") && !document.querySelector("#splitter") && !document.querySelector(".tabs")')]);
    checks.push(['base font is at least 16px', (await ev('parseFloat(getComputedStyle(document.body).fontSize)')) >= 16]);
    checks.push(['chat column is centered (beside the side panel when it is open) and at most 860px', await ev('(() => { const r = document.querySelector("#msgs").getBoundingClientRect(), c = document.querySelector("#chat"), cr = c.getBoundingClientRect(), pr = parseFloat(getComputedStyle(c).paddingRight) || 0; return r.width <= 861 && Math.abs((r.left - cr.left) - (cr.right - pr - r.right)) < 40; })()')]);
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
    const brs = () => browsers.get(store.listThreads()[0] && store.listThreads()[0].id) || [...browsers.values()].find((r) => !r.helper);
    const pv = (code) => ev(code);
    const panelOpen = () => ev('document.body.classList.contains("bp-open")');
    const inWin = (r) => { const [w, h] = win.getContentSize(); return r.x >= 0 && r.y >= 0 && r.x + r.width <= w + 1 && r.y + r.height <= h + 1 && r.width > 200 && r.height > 200; };
    const order = () => win.contentView.children;

    // ---- passwords may be pasted into the chat (local and private, Ben Oct 28): no composer guard
    await ev('(()=>{const i=document.querySelector("#input");i.value="";i.dispatchEvent(new Event("input"))})()');

    // ---- task 1: browse (Hands-off). While the model is "thinking" on the last step, use the popup.
    await send('Find the premonition item in the test shop');
    checks.push(['browser card appears inline in the chat', await until(() => ev('!!document.querySelector(".activity .bcard")'), 12000)]);
    checks.push(['card shows title/url of the page', await until(() => ev('/127\\.0\\.0\\.1/.test((document.querySelector(".bcard .bc-url")||{}).textContent||"")'))]);
    checks.push(['card has a live thumbnail (data: JPEG)', await until(() => ev('(()=>{const i=document.querySelector(".bcard .bc-thumb img");return !!i && i.src.startsWith("data:image/jpeg")})()'), 8000)]);
    await grab('ui-v2-running.png');
    checks.push(['card says Glim is browsing while active', await until(() => ev('document.querySelector(".bcard").classList.contains("active") && /Glim is browsing/.test(document.querySelector(".bcard").textContent)'))]);
    checks.push(['activity group shows a live step line while running', await ev('!!document.querySelector(".activity.running .act-live .t") && document.querySelector(".activity.running .act-live .t").textContent.length>3')]);
    const b0 = brs();
    checks.push(['browser panel is closed until the card is clicked', !(await panelOpen()) && !panel.open]);
    checks.push(['closed browser view stays attached below the UI (UI is above it)', order().indexOf(b0.view) >= 0 && order().indexOf(b0.view) < order().indexOf(ui)]);
    checks.push(['closed browser view has real panel size (not 0, not parked off-screen)', inWin(b0.view.getBounds())]);
    checks.push(['top bar shows the Browser button once a browser exists', await ev('!document.querySelector("#btnBrowser").hidden')]);
    // wait for the held step (the click request): the run is mid-flight
    await until(async () => gw.requests.length >= 3, 12000);
    await ev('document.querySelector(".bcard").click()');
    checks.push(['clicking the card opens the in-window browser panel', await until(() => panelOpen(), 5000)]);
    await sleep(600);
    const pop = brs();
    const vb = pop.view.getBounds();
    checks.push(['panel: browser view lies inside the main window and is above the UI', inWin(vb) && order().indexOf(pop.view) > order().indexOf(ui)]);
    checks.push(['panel: view sits on the right side (~58% wide) and fills the chrome slot', vb.x > 300 && vb.width >= 420 && Math.abs(vb.width - 1100 * 0.58) < 120 && (await ev('(() => { const r = document.querySelector("#bSlot").getBoundingClientRect(); return Math.abs(r.left - ' + vb.x + ') < 2 && Math.abs(r.top - ' + vb.y + ') < 2; })()'))]);
    checks.push(['panel: chrome visible (title, address, buttons, close)', await ev('(() => { const v = (s) => { const r = document.querySelector(s).getBoundingClientRect(); return r.width > 0 && r.height > 0; }; return ["#bTitle", "#bAddr", "#bBack", "#bFwd", "#bReload", "#bClose", "#bTake"].every(v); })()')]);
    checks.push(['panel: chat column reflowed to the left of the panel', await ev('document.querySelector("#msgs").getBoundingClientRect().right <= document.querySelector("#bpanel").getBoundingClientRect().left + 2')]);
    checks.push(['panel shows the real live page (results)', /\/results\?q=premonition/.test(pop.view.webContents.getURL())]);
    checks.push(['panel address bar shows the URL', /results\?q=premonition/.test(await ev('document.querySelector("#bAddr").value'))]);
    checks.push(['panel shows who is in control (Glim is browsing) and offers Take over', /Glim is browsing/.test(await ev('document.querySelector("#bWho").textContent')) && /Take over/.test(await ev('document.querySelector("#bTake").textContent'))]);
    checks.push(['only the main window and the status pill exist (no popup windows)', BrowserWindow.getAllWindows().length === 2 && BrowserWindow.getAllWindows().includes(win) && BrowserWindow.getAllWindows().includes(pillWin.win)]);
    // the divider: drag it and the view follows
    const before = pop.view.getBounds().width;
    // (synthetic pointer events: sendInputEvent mouse moves are not delivered as pointer moves under xvfb)
    await ev('(() => { const d = document.querySelector("#bdiv"), r = d.getBoundingClientRect(); const o = (t, x) => d.dispatchEvent(new PointerEvent(t, { bubbles: true, pointerId: 1, clientX: x, clientY: r.top + 20, button: 0 })); o("pointerdown", r.left + 5); for (let i = 1; i <= 6; i++) o("pointermove", r.left + 5 - i * 30); o("pointerup", r.left - 175); })()');
    await sleep(500);
    const after = pop.view.getBounds();
    checks.push(['dragging the divider widens the panel and the view follows', after.width > before + 100 && inWin(after) && order().indexOf(pop.view) > order().indexOf(ui)]);
    // Ben can use the page himself: scroll it from his side (real input into the panel page)
    pop.view.webContents.sendInputEvent({ type: 'mouseWheel', x: 200, y: 200, deltaX: 0, deltaY: -50 });
    // Take over pauses Glim's browser tools; Hand back lets him go on
    await ev('document.querySelector("#bTake").click()');
    checks.push(['Take over: label flips to Hand back to Glim and the hold is set', await until(async () => holds.has(pop.key) && /Hand back/.test(await ev('document.querySelector("#bTake").textContent')), 3000)]);
    await ev('document.querySelector("#bTake").click()');
    checks.push(['Hand back releases the hold', await until(async () => !holds.has(pop.key), 3000)]);
    const thumbBefore = await ev('(document.querySelector(".bcard .bc-thumb img")||{}).src||""');
    await ev('document.querySelector("#bClose").click()');
    checks.push(['closing the panel hides it and puts the view back under the UI', await until(async () => !(await panelOpen()) && !panel.open && order().indexOf(pop.view) < order().indexOf(ui), 3000)]);
    checks.push(['closed panel: view keeps its full size inside the window', inWin(pop.view.getBounds())]);
    checks.push(['closing the panel does not stop the agent', await ev('!document.querySelector("#btnStop").hidden')]);
    await waitIdle('task1');
    await sleep(700);
    const url = brs().br.wc.getURL();
    checks.push(['agent went on and ended on /item/1 (browsing continued with the panel closed)', url === site.base + '/item/1']);
    checks.push(['card thumbnail kept updating while the panel was closed', await ev('(document.querySelector(".bcard .bc-thumb img")||{}).src||""') !== thumbBefore && /item\/1/.test(await ev('document.querySelector(".bcard .bc-url").textContent') + (pop.br.wc.getURL()))]);
    const tb = await pop.br.thumb(360);
    checks.push(['capturePage works on the covered view (non-empty JPEG)', !!tb && tb.length > 1500]);
    checks.push(['run state cleared (Send shown, Stop hidden)', await ev('document.querySelector("#btnStop").hidden && document.querySelector("#runState").hidden && document.querySelector("#btnSend").textContent==="Send"')]);
    checks.push(['final answer rendered prominently', await ev('/Premonition result/.test((document.querySelector(".acol > .atext")||{}).textContent||"")')]);
    checks.push(['markdown bold rendered', await ev('!!document.querySelector(".atext strong")')]);
    checks.push(['thumbs up / down under the final answer, not under the narration', await ev('document.querySelectorAll(".acol > .atext + .stamp + .rate .rate-b").length===2 && !document.querySelector(".activity .rate")')]);
    {
      const fbFile = path.join(app.getPath('userData'), 'feedback.jsonl');
      const before = fs.existsSync(fbFile) ? fs.readFileSync(fbFile, 'utf8').split('\n').length : 1;
      await ev('document.querySelector(".acol > .atext + .stamp + .rate .rate-b").click()'); await sleep(300);
      const last = fs.existsSync(fbFile) ? fs.readFileSync(fbFile, 'utf8').trim().split('\n').pop() : '{}';
      checks.push(['thumbs up marks the answer and logs it for sleep', await ev('document.querySelector(".acol > .atext + .stamp + .rate .rate-b").getAttribute("aria-pressed")==="true"') && fs.readFileSync(fbFile, 'utf8').split('\n').length === before + 1 && JSON.parse(last).fb === 1 && /Premonition result/.test(JSON.parse(last).answer)]);
      await ev('document.querySelector(".acol > .atext + .stamp + .rate .rate-b").click()'); await sleep(300);
      checks.push(['a second tap takes it back (fb 0)', await ev('document.querySelector(".acol > .atext + .stamp + .rate .rate-b").getAttribute("aria-pressed")==="false"') && JSON.parse(fs.readFileSync(fbFile, 'utf8').trim().split('\n').pop()).fb === 0]);
    }
    checks.push(['[Action: ...] lines are hidden', await ev('!/\\[Action/i.test(document.body.innerText)')]);
    checks.push(['one activity group: "Did N things" collapsed after the run', await ev('document.querySelectorAll(".activity").length===1 && /Did [34] things/.test(document.querySelector(".act-head").textContent) && document.querySelector(".act-head").getAttribute("aria-expanded")==="false"')]);
    checks.push(['chevron sits next to the label (not far right)', await ev('(() => { const t = document.querySelector(".act-title").getBoundingClientRect(), c = document.querySelector(".act-head .chev").getBoundingClientRect(); return c.left - t.right < 160; })()')]);
    checks.push(['card kept, no longer "browsing" after the run', await ev('!!document.querySelector(".bcard") && !document.querySelector(".bcard").classList.contains("active") && /Click to open/.test(document.querySelector(".bcard").textContent)')]);
    checks.push(['one assistant avatar per block', (await ev('document.querySelectorAll(".ablock > .avatar").length')) === 1]);
    const vis = '(() => { const b = document.querySelector(".act-body"); return !!b && getComputedStyle(b).display !== "none"; })()';
    checks.push(['tool-use details are tucked away by default (one line per answer)', await ev('document.body.dataset.acts==="closed" && !(' + vis + ') && document.querySelector(".act-head").getAttribute("aria-expanded")==="false" && /Did [34] things/.test(document.querySelector(".act-head").textContent)')]);
    await ev('document.querySelector(".act-head").focus()');
    await ev('document.querySelector(".act-head").click()');
    await sleep(300);
    checks.push(['clicking the header expands the details of that group (button, so Enter/Space work)', await ev('document.querySelector(".activity.open") && ' + vis + ' && document.querySelector(".act-head").tagName==="BUTTON" && document.querySelector(".act-head").getAttribute("aria-expanded")==="true"')]);
    checks.push(['chevron turns down when expanded', await ev('getComputedStyle(document.querySelector(".act-head .chev")).transform!=="none"')]);
    checks.push(['expanding shows plan, narration and step pills with icons', await ev('!!document.querySelector(".plan") && document.querySelectorAll(".plan li").length===3 && document.querySelectorAll(".step .pill svg").length>=3 && !!document.querySelector(".nar")')]);
    await ev('(() => { const r = document.querySelectorAll(".activity.open .step > .pill"); r[0].click(); r[1].click(); })()');
    await sleep(200);
    checks.push(['only one step dropdown open at a time', await ev('document.querySelectorAll(".step.open").length===1 && document.querySelectorAll(".step .detail:not([hidden])").length===1 && document.querySelectorAll(".activity.open .step")[1].classList.contains("open")')]);
    await ev('document.querySelector(".step.open > .pill").click()');
    checks.push(['thinking block collapsed', await ev('!!document.querySelector("details.think:not([open])")')]);
    checks.push(['newest message shows Unread then Read', await ev('!!document.querySelector(".receipt")')]);
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
    const pop2 = brs();
    checks.push(['hand-off: the browser panel opens by itself', await until(() => panelOpen(), 4000)]);
    await sleep(700);
    checks.push(['hand-off: banner says Sign in here yourself; Glim can\'t see what you type', await ev('!document.querySelector("#bBanner").hidden && /Sign in here yourself; Glim can.t see what you type\\. Click Done when finished\\./.test(document.querySelector("#bBanner").textContent)')]);
    checks.push(['hand-off: the password field is still empty (nothing typed)', (await pop2.view.webContents.executeJavaScript('document.querySelector("#p").value')) === '']);
    checks.push(['hand-off: page view sits under the banner, inside the window', await ev('(() => { const r = document.querySelector("#bSlot").getBoundingClientRect(); const b = document.querySelector("#bBanner").getBoundingClientRect(); return r.top >= b.bottom - 1; })()') && inWin(pop2.view.getBounds()) && order().indexOf(pop2.view) > order().indexOf(ui)]);
    checks.push(['hand-off: chat card says sign-in needed', await until(() => ev('!!document.querySelector(".bcard.login") && /Sign-in needed/.test(document.querySelector(".bcard.login").textContent)'), 3000)]);
    checks.push(['hand-off: pill shows waiting for sign-in', await until(async () => /sign in/i.test(await pev('document.querySelector("#line").textContent')), 4000)]);
    checks.push(['after sending, the transcript is scrolled to the bottom', await until(() => ev('(() => { const s = document.querySelector("#scroll"); return s.scrollHeight - s.scrollTop - s.clientHeight < 4; })()'), 3000)]);
    checks.push(['the last message is not covered by the composer', await ev('(() => { const all = [...document.querySelectorAll("#msgs > *")]; const last = all[all.length - 1].getBoundingClientRect(); const c = document.querySelector("#composer").getBoundingClientRect(); return last.bottom <= c.top + 1; })()')]);
    checks.push(['narration lines are hidden inside the steps, or single-line with ellipsis', await ev('[...document.querySelectorAll(".nar")].every((n) => getComputedStyle(n).display === "none" || (getComputedStyle(n).whiteSpace === "nowrap" && n.clientHeight >= parseFloat(getComputedStyle(n).lineHeight) - 1))')]);
    checks.push(['typing bubble shows in the chat while working', await ev('!!document.querySelector(".typing-row") && !document.querySelector(".typing-row").hidden')]);
    checks.push(['hand-off: agent still waiting (no further request)', gw.requests.length === 8]);
    await grab('ui-v2-signin.png', true);
    const origTheme = nativeTheme.themeSource;
    for (const theme of ['light', 'dark']) {
      nativeTheme.themeSource = theme; await sleep(700);
      await grab('ui-v2-panel-wide-' + theme + '.png', true);
      const a = await ev(AUDIT);
      checks.push(['text contrast AA with the panel open (' + theme + ')', a.bad.length === 0]);
      if (a.bad.length) console.log('panel contrast: ' + a.bad.join(' | '));
      // narrow window: the panel becomes a full-window sheet with a Chat button
      win.setSize(900, 860); await sleep(900);
      const nb = pop2.view.getBounds();
      if (theme === 'light') checks.push(['narrow (<1000px): panel is a full-window sheet with a back-to-chat button', await ev('document.body.classList.contains("bp-narrow")') && nb.x === 0 && nb.width >= 890 && inWin(nb) && await ev('document.querySelector("#bChat").getBoundingClientRect().width > 0') && order().indexOf(pop2.view) > order().indexOf(ui)]);
      await grab('ui-v2-panel-narrow-' + theme + '.png', true);
      win.setSize(1100, 860); await sleep(900);
    }
    nativeTheme.themeSource = origTheme; await sleep(500);
    // Ben types his password himself (real key events into the page), then clicks Done
    await pop2.view.webContents.executeJavaScript('document.querySelector("#p").focus()');
    pop2.view.webContents.insertText('benspassword');
    await sleep(200);
    await ev('document.querySelector("#bDone").click()');
    await waitIdle('task3');
    checks.push(['hand-off: panel closes after Done and the agent continued', !(await panelOpen()) && gw.requests.length === 9]);
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

    // ---- task 6: Glim asks; answering removes the text box and buttons
    await send('Pick a colour for me');
    checks.push(['ask card shows a text box and buttons', await until(() => ev('!!document.querySelector(".card textarea") && document.querySelectorAll(".card .btns button").length===3'), 10000)]);
    checks.push(['answer box hides its scrollbar', await ev('getComputedStyle(document.querySelector(".card textarea")).scrollbarWidth==="none"')]);
    await ev('(()=>{const t=document.querySelector(".card textarea");t.value="teal please";t.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));})()');
    await waitIdle('task6');
    checks.push(['after answering, the question card leaves the dock and the chat keeps "You: ..."', await until(() => ev('!document.querySelector("#askDock .card") && /You: teal please/.test(document.querySelector("#msgs").textContent)'), 3000)]);

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
    checks.push(['first-run setup stays out of the way once onboarded', await ev('document.querySelector("#onboard").hidden')]);
    await ev('document.querySelector("#mainList li").click()');
    await sleep(600);
    checks.push(['message box and answer boxes hide their scrollbar', await ev('getComputedStyle(document.querySelector("#input")).scrollbarWidth==="none"')]);
    checks.push(['reopened thread: every tool-use group starts closed, and opening one opens only that one', await ev('(() => { const hs = [...document.querySelectorAll(".act-head")]; if (hs.length < 3 || !hs.every((h) => h.getAttribute("aria-expanded") === "false") || !([...document.querySelectorAll(".act-body")].every((b) => getComputedStyle(b).display === "none"))) return false; hs[1].click(); const open = document.querySelectorAll(".activity.open"); return open.length === 1 && open[0] === hs[1].closest(".activity"); })()')]);
    checks.push(['reopened thread restores browser card + activity groups', await ev('!!document.querySelector(".bcard .bc-thumb img") && document.querySelectorAll(".activity").length>=3')]);

    // ---- permissions card: rows with live status, Open Settings, a draggable app tile; flips green when macOS says yes
    await ev('window.Perms.show()');
    checks.push(['permissions card opens inside the main window with 3 rows (accessibility, screen recording, automation)', await until(() => ev('document.querySelectorAll("#perms .p-row").length===3'), 4000) && BrowserWindow.getAllWindows().length === 2]);
    checks.push(['permissions rows start Off with an Open Settings button each', await ev('[...document.querySelectorAll("#perms .p-row")].slice(0,2).every((r) => /Off/.test(r.querySelector(".p-stat").textContent) && !r.classList.contains("on") && /Open Settings/.test(r.textContent))')]);
    checks.push(['drag tile shows the app icon and name, with the hint and Finder label', await ev('(() => { const t = document.querySelector("#perms .p-tile"); return !!t && t.draggable && !!t.querySelector("img").src && /Premonition/.test(t.textContent) && /Drag this into the list, then switch it on/.test(document.querySelector("#perms").textContent) && /click to show it in Finder/.test(t.title); })()')]);
    await grab('ui-v2-permissions.png');
    permsFake.accessibility = true;
    checks.push(['row turns green when the permission flips (polled every 2 s)', await until(() => ev('(() => { const r = document.querySelector("#perms .p-row[data-id=accessibility]"); return !!r && r.classList.contains("on") && /On/.test(r.querySelector(".p-stat").textContent); })()'), 6000)]);
    checks.push(['the other row stays Off', await ev('!document.querySelector("#perms .p-row[data-id=screen]").classList.contains("on")')]);
    await ev('document.querySelector("#permsDone").click()');
    checks.push(['permissions card closes with Done', await ev('document.querySelector("#perms").hidden')]);

    // ---- settings sheet: every setting editable, applied at once and persisted
    await ev('window.__openSettings()');
    await sleep(300);
    const keys = ['gatewayUrl', 'model', 'mode', 'helperMode', 'maxSteps', 'maxParallel', 'verify', 'diaryEnabled', 'diaryPath', 'pythonPath', 'helperPath', 'vision', 'theme', 'textSize', 'highContrast', 'pill', 'openAtLogin', 'keepRunning', 'hotkey'];
    checks.push(['settings sheet has a control for every setting', await ev('document.querySelectorAll("#settingsCol .s-row").length>=' + keys.length + ' && ' + JSON.stringify(['Model', 'Autonomy', 'Running', 'Diary', 'Memory', 'Screen control', 'Vision', 'Appearance', 'Startup']) + '.every((g)=>[...document.querySelectorAll(".s-group h2")].some((h)=>h.textContent===g))')]);
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
    // ---- Settings > Memory: plain markdown editor for memory.md (type, Save, blur, Glim's additions appear, hand-written text survives)
    {
      const ta = (js) => ev('(() => { const t=document.querySelector("#memText"); ' + js + ' })()');
      const typeText = (v) => ta('t.focus(); t.value=' + JSON.stringify(v) + '; t.dispatchEvent(new Event("input",{bubbles:true}));');
      const fileText = () => memory.read().text;
      checks.push(['memory: editor and help text shown', await ev('/markdown file Glim reads/.test(document.querySelector("#settingsCol").innerText) && document.querySelector("#memText").tagName==="TEXTAREA" && !document.querySelector("#memList") && !document.querySelector("#memNew")')]);
      await typeText('# About Ben\n\nHe likes chess.\n\n- AP Chem is 3rd period with Mr. Phipps\n');
      await ev('document.querySelector("#memSave").click()');
      checks.push(['memory: Save button writes the text to memory.md', await until(() => fileText() === '# About Ben\n\nHe likes chess.\n\n- AP Chem is 3rd period with Mr. Phipps\n', 3000) && memory.list().length === 1 && memory.list()[0].text === 'AP Chem is 3rd period with Mr. Phipps']);
      checks.push(['memory: a Saved note is shown', await until(() => ev('/Saved/.test(document.querySelector("#memNote").textContent)'), 3000)]);
      await typeText('# About Ben\n\nHe likes chess.\n\n- AP Chem is 4th period with Mr. Phipps\n');
      await ev('document.querySelector("#memText").blur()');
      checks.push(['memory: leaving the box (blur) saves it', await until(() => /4th period/.test(fileText()) && !/3rd period/.test(fileText()), 3000)]);
      await typeText('- Prefers short answers\n');
      await ev('document.querySelector("#memText").dispatchEvent(new KeyboardEvent("keydown",{key:"s",metaKey:true,bubbles:true,cancelable:true}))');
      checks.push(['memory: Cmd+S saves', await until(() => fileText() === '- Prefers short answers\n', 3000)]);
      checks.push(['memory: previous version kept as memory.md.bak', require('fs').existsSync(memory.file + '.bak')]);
      // an edit in progress is never clobbered by a change on disk
      await typeText('- unsaved typing');
      memory.save('Ben takes Spanish 2 in 5th period', 'classes');
      await sleep(3600);
      checks.push(['memory: unsaved typing survives a change on disk', await ev('document.querySelector("#memText").value==="- unsaved typing"')]);
      await ev('document.querySelector("#memText").value="- Prefers short answers\\n"; document.querySelector("#memText").dispatchEvent(new Event("input",{bubbles:true})); document.activeElement && document.activeElement.blur()');
      await sleep(200);
      // with nothing unsaved, what Glim adds shows up on the next refresh
      await ev('window.__openSettings()'); await sleep(400);
      checks.push(['memory: text Glim added appears in the editor', await until(() => ev('/Spanish 2/.test(document.querySelector("#memText").value)'), 4000)]);
      checks.push(['memory: hand-written lines survive Glim\'s additions', /^- Prefers short answers$/m.test(fileText()) || /- Prefers short answers/.test(fileText())]);
      await ev('document.querySelector("#memText").value=""'); await ev('document.querySelector("#memText").blur()');
      for (const f of memory.list()) memory.delete(f.id);
      await ev('window.__openSettings()'); await sleep(300);
      checks.push(['memory: editor refreshes when Settings opens (file changed behind its back)', await until(() => ev('document.querySelector("#memText").value.indexOf("Spanish")<0'), 4000)]);

      checks.push(['settings: verify is on by default and the checkbox toggles it', store.getSettings().verify === true && await (async () => { await ev('document.querySelector("#settingsCol [aria-label^=\\"Double-check my work\\"]").click()'); const off = await until(() => store.getSettings().verify === false, 3000); await ev('document.querySelector("#settingsCol [aria-label^=\\"Double-check my work\\"]").click()'); return off && await until(() => store.getSettings().verify === true, 3000); })()]);
      await ev('document.querySelector("#memNote").textContent=""');
      await ev('document.querySelector("#memText").closest(".s-group").scrollIntoView({block:"start"})'); await sleep(400);
      await ev('document.activeElement && document.activeElement.blur()');
      await ev('(()=>{ let g=document.querySelector("#memText").closest(".s-group").nextElementSibling; while(g){ g.dataset.h="1"; g.style.display="none"; g=g.nextElementSibling; } })()'); // the screenshot is about Memory only
      await ev('document.querySelector("#memText").closest(".s-group").scrollIntoView({block:"start"})');
      await sleep(300);
      await grab('ui-v2-memory.png');
      await ev('document.querySelectorAll(".s-group[data-h]").forEach((g)=>{ g.style.display=""; delete g.dataset.h; })');
    }
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
    }], { autoVerify: true });
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
    checks.push(['helper report is not shown as a box in the chat', await ev('!document.querySelector(".notice")')]);
    const h0 = helpers.list()[0];
    checks.push(['helper listed idle with a summary', !!h0 && h0.status === 'idle' && /home page/.test(h0.lastSummary)]);
    await ev('document.querySelector("#btnThreads").click()');
    await sleep(300);
    checks.push(['Glims section lists the helper', await ev('!document.querySelector("#agentsSec").hidden && document.querySelectorAll("#agentList li").length===1 && /site-checker/.test(document.querySelector("#agentList").innerText)')]);
    await ev('document.querySelector("#agentList li").click()');
    await sleep(600);
    checks.push(['opening the helper thread shows its card and steps', await ev('!!document.querySelector(".bcard") && document.querySelectorAll(".step").length>=1 && /Report:/.test(document.body.innerText)')]);
    gw2.close();

    // ---- memory_save in a run: the fact appears in Settings > Memory
    {
      const gw3 = await startGateway([
        () => ({ content: 'Saving that.', tool_calls: [{ name: 'memory_save', arguments: { fact: 'Ben takes Spanish 2 in 5th period', topic: 'classes' } }] }),
        () => ({ content: 'Got it, I will remember that.' })
      ], { autoVerify: true });
      store.saveSettings({ gatewayUrl: gw3.url });
      warmer.gatewayMoved();
      await ev('document.querySelector("#newThread").click()'); await sleep(300);
      await send('Remember that I take Spanish 2 in 5th period');
      await waitIdle('memory_save');
      checks.push(['memory_save run: the step reads "Remembered: ..."', await ev('[...document.querySelectorAll(".step")].some((x)=>/Remembered: Ben takes Spanish 2/.test(x.innerText))')]);
      checks.push(['memory_save run: the fact is stored with its topic', memory.list().some((f) => /Spanish 2/.test(f.text) && f.topic === 'classes')]);
      await ev('window.__openSettings()'); await sleep(400);
      checks.push(['memory_save run: the fact shows in Settings > Memory', await until(() => ev('/Spanish 2/.test(document.querySelector("#memText").value) && /topic: classes/.test(document.querySelector("#memText").value)'), 4000)]);
      await ev('document.querySelector("#settingsClose").click()');
      for (const f of memory.list()) memory.delete(f.id);

    // ---- sleep mode (fake sleepmode app): confirm sheet, asleep state, blocked runs, check-in alerts, wake, summary card
    {
      const vis = (sel) => ev('(()=>{const e=document.querySelector("' + sel + '"); return !!e && !e.hidden && e.getClientRects().length>0;})()');
      await ev('window.__openSettings()'); await sleep(300);
      checks.push(['sleep: Settings has a Sleep group, an enabled Sleep now button and a plain status line', await ev('[...document.querySelectorAll(".s-group h2")].some((h)=>h.textContent==="Sleep") && !document.querySelector("#sleepNow").disabled && /Has not slept yet/.test(document.querySelector("#sleepStat").textContent)')]);
      await ev('document.querySelector("#settingsClose").click()');
      checks.push(['sleep: the top bar has a Sleep button', await vis('#btnSleep')]);
      await ev('document.querySelector("#btnSleep").click()'); await sleep(300);
      checks.push(['sleep: confirm sheet says what happens and offers the check-in option and the six lengths (checked)', await vis('#sleepSheet') && await ev('/stop answering while it learns from your chats/.test(document.querySelector("#sleepSheet").innerText) && /Wake it any time/.test(document.querySelector("#sleepSheet").innerText) && document.querySelector("#sleepPause").checked && /Hourly check-in/.test(document.querySelector("#sleepSheet").innerText) && document.querySelectorAll("#sleepDur button").length === 6 && document.querySelectorAll("#sleepDur button.on").length === 1 && /learns more/.test(document.querySelector("#sleepDurNote").innerText)')]);
      await ev('document.querySelector("#sleepGo").click()');
      checks.push(['sleep: confirming starts it and the sheet closes', await until(() => sl.asleep && sleeper.status().sleeping, 6000) && !(await vis('#sleepSheet'))]);
      await until(() => ev('!document.querySelector("#sleepBar").hidden'), 3000);
      checks.push(['sleep: composer shows a big Wake Glim button, Glim looks sleepy', await ev('document.querySelector("#btnWake").textContent==="Wake Glim" && document.querySelector("#btnSend").hidden && window.__mood()==="sleepy" && document.querySelector("#gw span").textContent==="Asleep"')]);
      checks.push(['sleep: the pill rests as "Sleeping · 2.5 h" (demo run labelled, no invented quiz)', await until(() => !!pillState.sleep && /^Sleeping · 2\.5 h · demo$/.test(pillState.sleep.line), 4000)]);
      checks.push(['sleep: scheduled Glim runs are held while asleep', helpers.o.hold() === true]);
      checks.push(['sleep: sending is refused with a friendly message', await ev('window.desk.agent.send(window.__threadId ? window.__threadId() : "x", "hello").then((r) => !!r.sleeping && /asleep/i.test(r.error))')]);
      checks.push(['sleep: a check-in alert flashes the pill and a notice appears; a missing permission is explained', await until(() => pillState.agents.has('sleep-alert') && /Quiz moved to today|check-in alert/.test(pillState.agents.get('sleep-alert').line), 5000) && await until(() => ev('/Check-in: .*Quiz moved/.test(document.body.innerText) && /need permission to read Calendar/.test(document.body.innerText) && /Automation/.test(document.body.innerText)'), 3000)]);
      await ev('(()=>{const i=document.querySelector("#input");i.value="what is due tomorrow?";i.dispatchEvent(new Event("input"));i.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true,cancelable:true}));})()');
      checks.push(['sleep: typing while asleep offers "Wake Glim and send this?" and keeps the text', await vis('#wakeAsk') && await ev('/Wake Glim and send this/.test(document.querySelector("#wakeAsk").innerText) && document.querySelector("#input").value==="what is due tomorrow?"')]);
      await ev('document.querySelector("#wakeAskNo").click(); document.querySelector("#input").value=""');
      await ev('document.querySelector("#scroll").scrollTop = 1e6'); await sleep(300);
      await grab('ui-v2-sleep-asleep.png');
      await ev('document.querySelector("#btnWake").click()');
      checks.push(['sleep: Wake shows Waking up… then Glim is awake again', await until(() => ev('document.querySelector("#sleepBar").hidden && !document.querySelector("#btnSend").hidden'), 12000) && !sl.asleep && !sleeper.status().sleeping]);
      checks.push(['sleep: a While you slept card shows the summary (rendered markdown, demo labelled)', await until(() => ev('(()=>{const c=document.querySelector(".wslept"); return !!c && /While you slept/.test(c.innerText) && /demo run/i.test(c.innerText) && c.querySelectorAll("li").length>=2 && !!c.querySelector("strong");})()'), 4000)]);
      checks.push(['sleep: scheduled runs are released after wake', helpers.o.hold() === false]);
      await ev('document.querySelector("#scroll").scrollTop = 1e6'); await sleep(400);
      await grab('ui-v2-sleep-summary.png');
      await ev('window.__openSettings()'); await sleep(300);
      checks.push(['sleep: Settings status line after waking is a demo-run note, no made-up numbers', await ev('/Last slept/.test(document.querySelector("#sleepStat").textContent) && /demo run/.test(document.querySelector("#sleepStat").textContent) && !/→|quiz/.test(document.querySelector("#sleepStat").textContent)')]);
      await ev('document.querySelector("#settingsClose").click()');
      // second night: type first, wake and send in one go
      await ev('document.querySelector("#btnSleep").click()'); await sleep(200); await ev('document.querySelector("#sleepGo").click()');
      await until(() => sl.asleep && sleeper.status().sleeping, 6000);
      await ev('(()=>{const i=document.querySelector("#input");i.value="good morning, Glim";i.dispatchEvent(new Event("input"));i.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true,cancelable:true}));})()');
      await ev('document.querySelector("#wakeAskYes").click()');
      checks.push(['sleep: Wake and send wakes Glim, then sends the message', await until(() => ev('[...document.querySelectorAll(".user")].some((u)=>/good morning, Glim/.test(u.innerText))'), 15000) && !sl.asleep]);
      await waitIdle('after wake and send');
      // an unavailable app is said plainly and disables the button
      store.saveSettings({ sleepApp: '/no/such/folder' });
      await ev('window.__openSettings()'); await sleep(300);
      checks.push(['sleep: a missing app is reported plainly and Sleep is disabled', await ev('/not found/.test(document.querySelector("#sleepStat").textContent) && document.querySelector("#sleepNow").disabled && document.querySelector("#btnSleep").disabled')]);
      store.saveSettings({ sleepApp: '' });
      await ev('document.querySelector("#settingsClose").click()');
      store.saveSettings({ autoSleep: false });
      checks.push(['sleep: with auto-sleep switched off nothing sleeps', autoSleepTick(new Date(2026, 9, 26, 23, 45), { idleMs: 3600000 }).action === 'none' && !sl.asleep]);
    }
      gw3.close();
    }

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

    // ---- first-run setup: Meet your Glims -> what for -> recurring Glims -> permissions. Everything else marks the app onboarded.
    {
      const nReq = gw.requests.length, nWin = BrowserWindow.getAllWindows().length;
      const key = async (k) => { for (const type of ['keyDown', 'char', 'keyUp']) wc.sendInputEvent({ type, keyCode: k }); await sleep(450); };
      const audit = async (label) => { const a = await ev(AUDIT); console.log('contrast audit (' + label + ', setup): ' + a.n + ' text elements, ' + a.bad.length + ' below AA' + (a.bad.length ? ': ' + a.bad.join(' | ') : '')); checks.push(['text contrast AA in setup (' + label + ')', a.bad.length === 0]); };
      const stepIs = (n) => ev('document.querySelector("#onboard .ob-page").dataset.step==="' + n + '" && !document.querySelector("#onboard").hidden');
      nativeTheme.themeSource = 'light'; await sleep(600);
      await ev('document.querySelector("#btnThreads").click()'); await sleep(100); await ev('document.querySelector("#drawerShade").click()');
      store.saveSettings({ onboarded: false, uses: [], usesOther: '' });
      await new Promise((r) => { wc.once('did-finish-load', r); wc.reload(); });
      await ev('new Promise(r=>{const t=setInterval(()=>{if(window.__ready){clearInterval(t);r()}},50)})');
      await sleep(800);
      checks.push(['setup: shows on first run (onboarded false), inside the main window', await stepIs(0) && BrowserWindow.getAllWindows().length === nWin]);
      checks.push(['setup step 1: Meet Glim with the main Glim and four small ones in different moods', await ev('/Meet Glim/.test(document.querySelector("#onboard h1").textContent) && document.querySelectorAll("#onboard .ob-glim .mascot").length===4 && new Set([...document.querySelectorAll("#onboard .mascot")].map((m)=>m.dataset.mood)).size>=4')]);
      checks.push(['setup: chrome text is not selectable', await ev('getComputedStyle(document.querySelector("#onboard .ob-lead")).userSelect==="none" && getComputedStyle(document.querySelector("#obNext")).userSelect==="none"')]);
      await audit('light, meet');
      await grab('ui-v2-onboard-a-meet.png');
      await key('Return');
      checks.push(['setup: Enter goes to the next step', await stepIs(1)]);
      checks.push(['setup step 2: 8 multi-select tiles and a Something else field', await ev('document.querySelectorAll("#onboard .ob-tile").length===8 && [...document.querySelectorAll("#onboard .ob-tile")].every((t)=>t.querySelector("svg") && t.querySelector("b") && t.querySelector(".ob-txt span")) && !!document.querySelector("#obOther")')]);
      await ev('document.querySelector("#onboard .ob-tile[data-id=email]").click(); document.querySelector("#onboard .ob-tile[data-id=briefing]").click()');
      await ev('(()=>{const i=document.querySelector("#obOther");i.value="keep track of my game releases";i.dispatchEvent(new Event("input"))})()');
      checks.push(['setup: tiles toggle (2 picked)', await ev('document.querySelectorAll("#onboard .ob-tile[aria-checked=true]").length===2')]);
      await ev('document.activeElement && document.activeElement.blur()'); await sleep(200);
      await audit('light, uses');
      await grab('ui-v2-onboard-b-uses-light.png');
      nativeTheme.themeSource = 'dark'; await sleep(700);
      await audit('dark, uses');
      await grab('ui-v2-onboard-b-uses-dark.png');
      nativeTheme.themeSource = 'light'; await sleep(600);
      await key('Return');
      checks.push(['setup: the Ask first / Hands-off question comes after the picks', await stepIs(4) && await ev('document.querySelectorAll("#onboard .ob-tile").length===2 && /ask first/i.test(document.querySelector("#onboard").innerText)')]);
      await ev('document.querySelectorAll("#onboard .ob-tile")[1].click()');
      await key('Return');
      checks.push(['setup: choosing Hands-off at onboarding saves mode', await until(() => store.getSettings().mode === 'hands-off', 3000)]);
      store.saveSettings({ mode: 'ask' });
      checks.push(['setup: a step explains the thumbs up / down and how sleep uses them', await stepIs(5) && await ev('/Teach Glim what you like/.test(document.querySelector("#onboard h1").textContent) && document.querySelectorAll("#onboard .ob-rate").length===2 && /sleeps/.test(document.querySelector("#onboard").innerText)')]);
      await key('Return');
      checks.push(['setup: Enter on step 2 saves the picks as uses + usesOther', await stepIs(2) && JSON.stringify(store.getSettings().uses) === '["email","briefing"]' && store.getSettings().usesOther === 'keep track of my game releases']);
      checks.push(['setup step 3: one row per recurring pick, each with a switch', await ev('document.querySelectorAll("#onboard .ob-row").length===2 && document.querySelectorAll("#onboard .ob-row .toggle[aria-checked=true]").length===2 && /Email watch/.test(document.body.innerText) && /every 30 min/.test(document.body.innerText) && /daily at 08:00/.test(document.body.innerText)')]);
      await ev('document.querySelector("#onboard .ob-row[data-id=email] .toggle").click()');
      checks.push(['setup: the button says how many routines it will create', await ev('document.querySelector("#obNext").textContent==="Create 1 routine"')]);
      await audit('light, recurring');
      await grab('ui-v2-onboard-c-recurring.png');
      await key('Return');
      checks.push(['setup: created the Morning briefing Glim (daily 08:00) and not the one switched off', await until(async () => !!helpers.find('Morning briefing'), 4000) && helpers.list().find((h) => h.name === 'Morning briefing').schedule === 'daily 08:00' && !helpers.find('Email watch')]);
      checks.push(['setup: creating a Glim made no model call', gw.requests.length === nReq]);
      checks.push(['setup step 4: the Permissions rows are embedded, with no sheet or Done of its own', await until(() => ev('document.querySelectorAll("#obPerms .p-row").length===3'), 4000) && await stepIs(3) && await ev('!document.querySelector("#obPerms #permsDone") && document.querySelector("#perms").hidden')]);
      await sleep(300);
      await audit('light, permissions');
      await grab('ui-v2-onboard-d-permissions.png');
      // macOS makes you quit and reopen after the Screen Recording switch: setup comes back on Permissions, Glims are not made twice
      checks.push(['setup: reaching Permissions is remembered', store.getSettings().onboardAt === 'perms' && store.getSettings().onboarded === false]);
      await new Promise((r) => { wc.once('did-finish-load', r); wc.reload(); });
      await ev('new Promise(r=>{const t=setInterval(()=>{if(window.__ready){clearInterval(t);r()}},50)})');
      await sleep(800);
      checks.push(['setup: a reopen mid-setup resumes on Permissions, not the start', await until(() => stepIs(3), 4000) && await ev('document.querySelectorAll("#obPerms .p-row").length===3')]);
      checks.push(['setup: resuming made no second Morning briefing', helpers.list().filter((h) => h.name === 'Morning briefing').length === 1]);
      await key('Return');
      checks.push(['setup: Enter on the last step finishes; onboarded saved', await until(() => ev('document.querySelector("#onboard").hidden'), 3000) && store.getSettings().onboarded === true && store.getSettings().onboardAt === '']);
      checks.push(['welcome chips follow the picks', await ev('(() => { const c=[...document.querySelectorAll(".welcome .chips button")].map((b)=>b.textContent); return c.length===4 && c[0]==="Check my email" && c[1]==="Give me a morning briefing"; })()')]);
      await grab('ui-v2-onboard-e-welcome.png');
      await ev('document.querySelector("#btnThreads").click()'); await sleep(400);
      checks.push(['sidebar section is called Glims and lists the new Glim', await ev('!document.querySelector("#agentsSec").hidden && /^Glims$/.test(document.querySelector("#agentsSec .drawer-label").textContent) && /Morning briefing/.test(document.querySelector("#agentList").innerText)')]);
      await grab('ui-v2-onboard-f-sidebar.png');
      await ev('document.querySelector("#drawerShade").click()');
      // Settings > Run setup again, then Esc skips
      await ev('window.__openSettings()'); await sleep(200);
      checks.push(['settings: Run setup again button', await ev('!!document.querySelector("#runSetup")')]);
      await ev('document.querySelector("#runSetup").click()'); await sleep(500);
      checks.push(['setup again: opens over a closed Settings, keeps the old picks, shows the existing Glim as Created', await stepIs(0) && await ev('document.querySelector("#settings").hidden') && (await key('Return'), await ev('document.querySelectorAll("#onboard .ob-tile[aria-checked=true]").length===2')) && (await key('Return'), await key('Return'), await key('Return'), await ev('!!document.querySelector("#onboard .ob-row.made") && /Created/.test(document.querySelector("#onboard").innerText)'))]);
      store.saveSettings({ onboarded: false });
      await key('Escape');
      checks.push(['setup: Esc skips (closes and counts as onboarded)', await until(() => ev('document.querySelector("#onboard").hidden'), 3000) && store.getSettings().onboarded === true]);
      checks.push(['setup: no extra window was opened', BrowserWindow.getAllWindows().length === nWin]);
      helpers.remove('Morning briefing');
      nativeTheme.themeSource = 'system';
    }

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
