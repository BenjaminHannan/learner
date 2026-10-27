'use strict';
// Real-Electron end-to-end test. Run: xvfb-run -a -s "-screen 0 1440x900x24" npx electron . --no-sandbox --e2e
// A fake gateway scripts the model; the real agent, browser view and UI do the rest.
const http = require('http');
const path = require('path');
const fs = require('fs');
const { execFile } = require('child_process');
const { startGateway } = require('./helpers');

const OUT = path.join(__dirname, 'out');

function startSite() {
  const page = (title, body) => '<!doctype html><meta charset=utf-8><title>' + title + '</title><body style="font:16px sans-serif;padding:30px">' + body;
  const server = http.createServer((req, res) => {
    res.setHeader('content-type', 'text/html');
    const u = new URL(req.url, 'http://x');
    if (u.pathname === '/') res.end(page('Test Shop', '<h1>Test Shop</h1><form action="/results" method="get"><input id="q" name="q" placeholder="Search"> <button type="submit">Go</button></form><p>Welcome to the shop.</p>'));
    else if (u.pathname === '/results') res.end(page('Results', '<h1>Results for ' + (u.searchParams.get('q') || '') + '</h1><ul><li><a href="/item/2">Other thing</a></li><li><a href="/item/1">Premonition result</a></li></ul>'));
    else if (u.pathname.startsWith('/item/')) res.end(page('Item ' + u.pathname.split('/')[2], '<h1>Item ' + u.pathname.split('/')[2] + '</h1><p>The final page.</p>'));
    else { res.statusCode = 404; res.end('nope'); }
  });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r({ base: 'http://127.0.0.1:' + server.address().port, close: () => { server.closeAllConnections(); server.close(); } })));
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function lastTool(req) { const m = req.messages.filter((x) => x.role === 'tool'); return m.length ? m[m.length - 1].content : ''; }
function idOf(text, re) { const m = new RegExp('\\[(\\d+)\\] ' + re).exec(text); if (!m) throw new Error('no element matching ' + re + ' in snapshot:\n' + text); return Number(m[1]); }

async function run({ app, win, store, browser }) {
  const fail = (m) => { console.error('E2E FAIL: ' + m); app.exit(1); };
  const timer = setTimeout(() => fail('timeout'), 120000);
  const wc = win.webContents;
  const ev = (code) => wc.executeJavaScript(code);
  try {
    fs.mkdirSync(OUT, { recursive: true });
    win.setBounds({ x: 0, y: 0, width: 1360, height: 860 });
    const site = await startSite();
    const checks = [];
    const gw = await startGateway([
      () => ({ reasoning: 'The user wants the Premonition item. I should open the shop and search.', content: "Plan:\n1. Open the shop\n2. Search for premonition\n3. Open the matching result\n\nOpening the shop now.", tool_calls: [{ name: 'browser_go', arguments: { url: site.base + '/' } }] }),
      (req) => ({ tool_calls: [{ name: 'browser_type', arguments: { id: idOf(lastTool(req), 'input\\(text\\) "Search"'), text: 'premonition', enter: true } }] }),
      (req) => { const t = lastTool(req); checks.push(['results page reached after typing + Enter', /\/results\?q=premonition/.test(t)]); return { tool_calls: [{ name: 'browser_click', arguments: { id: idOf(t, 'link "Premonition result"') } }] }; },
      (req) => { checks.push(['click landed on item page', /\/item\/1/.test(lastTool(req))]); return { content: 'I found it: **Item 1** is the Premonition result. Opened at `/item/1`.' }; },
      // second task: shell in Ask first mode, approval card
      () => ({ content: 'Checking.', tool_calls: [{ name: 'run_shell', arguments: { command: 'echo desk-e2e-ok' } }] }),
      (req) => { checks.push(['shell output reached model', /desk-e2e-ok/.test(lastTool(req))]); return { content: 'The shell printed desk-e2e-ok.' }; }
    ]);
    store.saveSettings({ gatewayUrl: gw.url, mode: 'hands-off', maxSteps: 20 });
    await ev('document.querySelector("#modeSeg [data-mode=hands-off]").click()');
    await ev('new Promise(r=>{const t=setInterval(()=>{if(window.__ready){clearInterval(t);r()}},50)})');

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

    // ---- task 1: browse (Hands-off)
    await send('Find the premonition item in the test shop');
    await waitIdle('task1');
    await sleep(600);
    const url = browser.wc.getURL();
    checks.push(['browser ended on /item/1', url === site.base + '/item/1']);
    checks.push(['run state cleared (Send shown, Stop hidden)', await ev('document.querySelector("#btnStop").hidden && document.querySelector("#runState").hidden && document.querySelector("#btnSend").textContent==="Send"')]);
    checks.push(['final answer rendered', await ev('document.body.innerText.includes("Premonition result")')]);
    checks.push(['markdown bold rendered', await ev('!!document.querySelector(".atext strong")')]);
    checks.push(['plan pinned', await ev('!document.querySelector("#plan").hidden && document.querySelectorAll("#planList li").length===3')]);
    checks.push(['3 steps in trail', (await ev('document.querySelectorAll(".step").length')) === 3]);
    checks.push(['thinking block collapsed', await ev('!!document.querySelector("details.think:not([open])")')]);
    await sleep(500);
    const shot = path.join(OUT, 'ui.png');
    await new Promise((resolve) => {
      execFile('import', ['-window', 'root', shot], { env: process.env }, async (err) => {
        if (err || !fs.existsSync(shot)) { try { fs.writeFileSync(shot, (await wc.capturePage()).toPNG()); } catch (e) { /* ignore */ } }
        resolve();
      });
    });
    console.log('SCREENSHOT ' + shot);

    // ---- task 2: Ask first -> approval card -> allow
    store.saveSettings({ mode: 'ask' });
    await send('Run echo to check the shell');
    let card = false;
    for (let i = 0; i < 100 && !card; i++) { await sleep(100); card = await ev('!!document.querySelector(".card .amber-btn")'); }
    checks.push(['approval card shown in Ask first', card]);
    await ev('document.querySelector(".card .amber-btn").click()');
    await waitIdle('task2');
    checks.push(['task2 finished after approval', await ev('document.body.innerText.includes("desk-e2e-ok")')]);

    // ---- persistence
    await sleep(300);
    const list = store.listThreads();
    const t = list.length ? store.loadThread(list[0].id) : null;
    checks.push(['thread saved', !!t && t.messages.length >= 10 && t.items.filter((i) => i.t === 'step').length === 4]);
    checks.push(['thread titled from first message', !!t && /premonition item/.test(t.title)]);
    checks.push(['model got date-prefixed user message', /^\[\w{3} \d{4}-/.test(gw.requests[0].messages.find((m) => m.role === 'user').content)]);

    let bad = 0;
    for (const [name, ok] of checks) { console.log((ok ? 'PASS ' : 'FAIL ') + name); if (!ok) bad++; }
    clearTimeout(timer);
    gw.close(); site.close();
    console.log(bad ? 'E2E FAILED (' + bad + ')' : 'E2E OK');
    app.exit(bad ? 1 : 0);
  } catch (e) {
    clearTimeout(timer);
    fail(e.stack || e.message);
  }
}

module.exports = { run };
