'use strict';
// AGENT1 agent bench runner (Electron main process). Drives the REAL desk agent loop (src/agent.js + src/tools/browser.js, real system
// prompt and tool list, real gateway and model) on the fake sites in sites.js. Only what needs Ben or the Mac is stubbed: ask_user and
// sign-in waits answer from the task script, shell/screen/app tools say they are unavailable, web_search reads the fake index.
// Usage: electron test/agentbench/run.js --out DIR [--tasks id,id] [--label name] [--cap 240] [--maxSteps 25]
// Every request carries test: true / X-Test (llm.setTestProfile), so the gateway's diary marks it and sleep never trains on it.
const path = require('path');
const fs = require('fs');
const os = require('os');
const { app, BrowserWindow, WebContentsView, session } = require('electron');

const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; };
const OUT = arg('out', path.join(os.tmpdir(), 'agentbench-out'));
const LABEL = arg('label', 'run');
const CAP_S = Number(arg('cap', 240));
const MAX_STEPS = Number(arg('maxSteps', 25));
const KIT = arg('kit', '');   // AGENT1 harness changes on for this run (src/agentkit.js), e.g. 'sso' or 'sso,diet'
const PROFILE = arg('profile', path.join(os.tmpdir(), 'agentbench-profile'));
fs.mkdirSync(OUT, { recursive: true });
app.setPath('userData', PROFILE);
app.commandLine.appendSwitch('disable-renderer-backgrounding');

const llm = require('../../src/llm');
llm.setTestProfile(true);
const budget = require('../../src/context-budget');
const REQS = [];
const realStream = llm.streamChat;
llm.streamChat = async (o) => {   // patched before agent.js / creative.js take their copy
  const rec = { at: Date.now(), model: o.model, msgs: (o.messages || []).length, tools: (o.tools || []).length, toolChars: JSON.stringify(o.tools || []).length,
    sysChars: o.messages && o.messages[0] && o.messages[0].role === 'system' ? String(o.messages[0].content).length : 0, estTokens: budget.requestTokens(o.messages || [], o.tools || []),
    maxToolResult: Math.max(0, ...(o.messages || []).filter((m) => m.role === 'tool').map((m) => String(m.content || '').length)) };
  REQS.push(rec);
  try { const r = await realStream(o); rec.ms = Date.now() - rec.at; rec.ttft = r.firstTokenMs; rec.blankRun = /\s{40,}$/.test(String(r.content || '')); rec.out = { content: String(r.content || '').slice(0, 600), calls: (r.toolCalls || []).map((c) => c.name + ' ' + String(c.arguments).slice(0, 200)), reasoningChars: String(r.reasoning || '').length }; return r; }
  catch (e) { rec.ms = Date.now() - rec.at; rec.error = String(e && e.message || e).slice(0, 200); throw e; }
};
const { Agent, extractPlan } = require('../../src/agent');
const { buildTools } = require('../../src/prompt');
const { Browser } = require('../../src/tools/browser');
const { createMemory } = require('../../src/memory');
const L = require('../../src/logins');
const SafetyMod = require('../../src/safety-levels');
const Sites = require('./sites');
// --set aux: the separate tasks of tasks-aux.js (MARKS-agent-aux-v1.md); the registered 20 stay in tasks.js
const TASKS = (process.argv.includes('aux') && process.argv[process.argv.indexOf('aux') - 1] === '--set') ? require('./tasks-aux').TASKS : require('./tasks').TASKS;

const TOOL_RE = /\b(browser_(?:go|click|type|scroll|back|sign_in|read)|web_search|ask_user|memory_(?:save|forget)|run_shell|screen_(?:look|click|type|key)|open_app|agent_(?:start|list|update|stop)|diary_search|track_(?:add|done))\b/;
const UNAVAILABLE = 'Error: not available in this session. Use the built-in browser tools for websites.';

let state = Sites.newState();
const settings = () => ({ gatewayUrl: 'http://127.0.0.1:8090/v1', model: 'qwen36-fast', modelMain: 'qwen36', modelFast: 'qwen36-fast', modelAuto: 'qwen36-auto',
  verify: true, mode: 'hands-off', vision: 'off', contextTokens: 12000, compactTokens: 24000, maxToolChars: 8000, maxSteps: MAX_STEPS, uses: [], alwaysAllow: [], agentKit: KIT ? KIT.split(',') : [] });
for (const k of Object.keys(Sites.SAVED_LOGINS)) L.addSecret(Sites.SAVED_LOGINS[k].password);

function wireSites(ses) {
  for (const scheme of ['https', 'http']) {
    ses.protocol.handle(scheme, async (req) => {
      let form = {};
      if (req.method === 'POST') { try { form = Object.fromEntries(new URLSearchParams(await req.text())); } catch (e) { form = {}; } }
      const r = Sites.handle(state, req.url, req.method, form);
      return new Response(r.status === 302 ? null : r.body, { status: r.status, headers: r.headers });
    });
  }
}

// before each task: memory pressure normal (1) and the gateway answering (its watchdog restarts the model under memory pressure; a task
// that ran into that would be scored on the Mac, not on Glim)
async function ready() {
  const { execFileSync } = require('child_process');
  for (let i = 0; i < 90; i++) {
    let p = '4', up = false;
    try { p = execFileSync('sysctl', ['-n', 'kern.memorystatus_vm_pressure_level']).toString().trim(); } catch (e) { /* retry */ }
    // /models answers even with the model server stopped: a 1-token test chat is the real check
    try { up = (await fetch(settings().gatewayUrl + '/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json', 'x-test': '1' }, body: JSON.stringify({ model: 'qwen36-fast', test: true, max_tokens: 1, messages: [{ role: 'user', content: 'hi' }] }), signal: AbortSignal.timeout(60000) })).ok; } catch (e) { up = false; }
    if (p === '1' && up) return true;
    await new Promise((r) => setTimeout(r, 20000));
  }
  return false;
}

async function runTask(win, task, n) {
  await ready();
  state = Sites.newState(new Date());
  // offscreen: an on-screen window on a Mac whose display sleeps drops every sendInputEvent click (seen on the M1: no mousedown at all)
  const ow = new BrowserWindow({ show: false, width: 1280, height: 860, webPreferences: { offscreen: true, partition: 'persist:desk', backgroundThrottling: false, sandbox: true, contextIsolation: true } });
  ow.webContents.setFrameRate(10);
  const view = { webContents: ow.webContents, constructor: WebContentsView };
  const br = new Browser({ view, session });
  br.shouldFocus = () => true;
  const tr = { asks: 0, askLog: [], signInWaits: 0, stuckAsks: 0, unavailable: [], steered: false, events: 0 };
  const memDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agentbench-mem-'));
  const memory = createMemory(memDir);
  memory.save('Ben is a high-school senior in Dresden, Ohio.'); memory.save('Ben likes short, direct answers.');
  const signInWait = async () => { tr.signInWaits++; tr.asks++; return 'later'; };
  const afterSignIn = async (b, v) => (v === 'done' ? 'Login needed: Ben is signing in himself. He clicked Done. Fresh snapshot of the page now:\n' + (await b.snapshot())
    : 'Login needed: Ben is signing in himself, but he chose not to right now. Do not type credentials. Tell him what you could not finish.');
  const una = (name) => () => { tr.unavailable.push(name); return { text: UNAVAILABLE, error: true }; };
  const tools = {
    web_search: (x) => { const R = Sites.searchResults(x.query); return R.length ? R.map((r, i) => (i + 1) + '. ' + r.title + '\n   ' + r.url + '\n   ' + r.snippet).join('\n') : 'No results found.'; },
    browser_go: (x) => br.go(x.url),
    browser_click: (x) => br.click(x.id),
    browser_type: async (x, ctx) => {
      const why = await br.sensitiveReason(x.id);
      if (why) { const v = await ctx.waitForBen(() => signInWait()); return { text: await afterSignIn(br, v), summary: 'Waited while Ben signed in' }; }
      return br.type(x.id, x.text, x.enter);
    },
    browser_sign_in: async (x, ctx) => {
      let Kit = null; try { Kit = require('../../src/agentkit'); } catch (e) { /* older tree */ }
      const r = await br.signIn(async (u) => { const o = L.originOf(u); const s = o && Sites.SAVED_LOGINS[o]; return s ? { origin: o, user: s.user, password: s.password } : null; }, { sso: !!(Kit && Kit.on(settings(), 'sso')) });
      if (r.kind === 'none' || r.kind === 'code') {
        const v = await ctx.waitForBen(() => signInWait());
        const lead = r.kind === 'none' ? 'No saved login for ' + r.host + ', so the app asked Ben to sign in once himself (it then offers to save it). ' : 'A code was needed on ' + r.host + '. ';
        return { text: lead + (await afterSignIn(br, v)), summary: r.kind === 'none' ? 'Ben signed in once on ' + r.host : 'Ben entered the code' };
      }
      return r;
    },
    browser_scroll: (x) => br.scroll(x.direction),
    browser_back: () => br.back(),
    browser_read: (x) => br.read(x.page),
    run_shell: una('run_shell'), screen_look: una('screen_look'), screen_click: una('screen_click'), screen_type: una('screen_type'), screen_key: una('screen_key'), open_app: una('open_app'),
    diary_search: () => 'No matches in past chats.',
    agent_start: una('agent_start'), agent_list: () => 'No Motes.', agent_update: una('agent_update'),
    track_add: (x) => 'Now tracking: ' + (x.what || ''), track_done: () => 'Nothing to mark done', ask_user: () => ''
  };
  for (const [k, f] of Object.entries(task.tools ? task.tools(state, tr) : {})) tools[k] = f;   // aux tasks: a fake screen / Motes
  const thread = { id: 'bench-' + task.id + '-' + n, messages: [], items: [] };
  const base = new Date(Date.now() - 3600000);
  (task.preseed || []).forEach(([u, a], i) => {
    const d = new Date(base.getTime() + i * 300000), p = (x) => String(x).padStart(2, '0');
    const stamp = '[' + ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()] + ' ' + d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ']';
    thread.messages.push({ role: 'user', content: stamp + ' ' + u }, { role: 'assistant', content: a });
    thread.items.push({ t: 'user', text: u }, { t: 'assistant', text: a });
  });
  const itemStart = thread.items.length, msgStart = thread.messages.length, reqStart = REQS.length;
  let agent;
  agent = new Agent({
    memory, tracking: null, tools, toolDefs: () => buildTools({ diary: true }),
    getSettings: settings,
    emit: (ev) => {
      tr.events++;
      if (task.steer && !tr.steered && ev.type === 'step_end' && ev.tool !== 'verify') { tr.steered = true; setTimeout(() => agent.steer(task.steer), 0); }
    },
    // the app's safety levels (track I5, defaults) gate buying, sending and submitting with an approval card; Ben's tap is scripted
    safety: new SafetyMod.SafetyLevels({ dir: memDir }),
    safetyCtx: () => ({ selfPaths: [], frontApp: '', pageUrl: (() => { try { return br.state().url; } catch (e) { return ''; } })(),
      labelOf: (nm, id) => { const ls = (br.lastSnap && br.lastSnap.lines) || []; return ls.find((l) => l.startsWith('[' + id + ']')) || ''; } }),
    approve: async (req) => { tr.asks++; tr.approvals = (tr.approvals || 0) + 1; const v = task.approve ? task.approve(req) : (req.danger ? 'deny' : 'once'); tr.askLog.push({ q: 'APPROVE ' + (req.text || req.tool), ans: v }); return v; },
    askUser: async (q, signal, options) => { tr.asks++; const ans = task.ask ? task.ask(q, options) : (options || []).find((o) => /^(yes|ok|go|sure|continue)/i.test(o)) || 'Yes, go ahead.'; tr.askLog.push({ q, options, ans }); return ans; },
    onStuck: async (stuck) => { tr.stuckAsks++; tr.asks++; return 'You were stuck repeating ' + stuck.summary + '. Ben says: try a different way.'; },
    onThreadChange: () => {}
  });
  const t0 = Date.now();
  const timer = setTimeout(() => { tr.timedOut = true; agent.stop(); }, CAP_S * 1000);
  let res;
  // hard watchdog: a run still going 60 s after the cap (seen once: a step hung with the model idle) is scored as it stands
  let hard = null;
  const hardStop = new Promise((resolve) => { hard = setTimeout(() => { tr.timedOut = true; tr.hung = true; resolve({ error: 'hung past the cap' }); }, (CAP_S + 60) * 1000); });
  try { res = await Promise.race([agent.run(thread, task.text), hardStop]); } catch (e) { res = { error: String(e && e.message || e) }; }
  clearTimeout(hard);
  clearTimeout(timer);
  const secs = (Date.now() - t0) / 1000;
  const items = thread.items.slice(itemStart);
  const said = items.filter((i) => i.t === 'assistant' && i.text).map((i) => i.text);
  const answer = said.join('\n');
  const calls = [];
  for (const m of thread.messages.slice(msgStart)) if (m.role === 'assistant' && m.tool_calls) for (const c of m.tool_calls) calls.push({ name: c.function.name, args: c.function.arguments });
  let repeats = 0;
  for (let i = 1; i < calls.length; i++) if (calls[i].name === calls[i - 1].name && calls[i].args === calls[i - 1].args && !/^(browser_scroll|ask_user)$/.test(calls[i].name)) repeats++;
  const replans = said.filter((t) => extractPlan(t) || /(^|\n)\s*(\*\*)?plan\b\s*(\*\*)?\s*:/i.test(t)).length + items.filter((i) => i.t === 'plan').length;
  const leaks = said.filter((t) => TOOL_RE.test(t)).length + tr.askLog.filter((x) => TOOL_RE.test(x.q)).length;
  const reqs = REQS.slice(reqStart);
  tr.calls = calls; tr.blank = thread.messages.slice(msgStart).some((m) => m.role === 'assistant' && typeof m.content === 'string' && /\s{40,}$/.test(m.content)) || REQS.slice(reqStart).some((r) => r.blankRun);
  let ok = false; try { ok = !!task.score(state, answer, tr); } catch (e) { ok = false; }
  const out = { label: LABEL, task: task.id, kind: task.kind, run: n, ok, secs: Math.round(secs), modelCalls: reqs.length, toolCalls: calls.length, replans, leaks, repeats,
    asks: tr.asks, blank: !!tr.blank, unavailable: tr.unavailable.length, timedOut: !!tr.timedOut, hung: !!tr.hung, error: res && res.error || null,
    maxReqTokens: Math.max(0, ...reqs.map((r) => r.estTokens)), over8192: reqs.filter((r) => r.estTokens > 8192).length,
    maxToolResult: Math.max(0, ...reqs.map((r) => r.maxToolResult)), toolChars: reqs.length ? reqs[0].toolChars : 0, sysChars: reqs.length ? reqs[0].sysChars : 0,
    calls: calls.map((c) => c.name + ' ' + c.args), said,
    msgs: thread.messages.slice(msgStart).map((m) => ({ role: m.role, content: typeof m.content === 'string' ? m.content.slice(0, 4000) : '[parts]', calls: m.tool_calls ? m.tool_calls.map((c) => c.function.name + ' ' + c.function.arguments) : undefined })), asksLog: tr.askLog, visits: state.visits.slice(-40), reqs };
  fs.writeFileSync(path.join(OUT, task.id + '.json'), JSON.stringify(out, null, 1));
  fs.appendFileSync(path.join(OUT, 'summary.jsonl'), JSON.stringify({ ...out, said: undefined, reqs: undefined, calls: calls.length, visits: undefined, asksLog: undefined, msgs: undefined }) + '\n');
  br.destroy();
  try { ow.destroy(); } catch (e) { /* gone */ }
  fs.rmSync(memDir, { recursive: true, force: true });
  return out;
}

app.whenReady().then(async () => {
  wireSites(session.fromPartition('persist:desk'));
  const win = new BrowserWindow({ show: false, width: 1280, height: 860, webPreferences: { backgroundThrottling: false } });
  const ids = arg('tasks', '') ? arg('tasks').split(',') : TASKS.map((t) => t.id);
  const n = Number(arg('run', 1));
  for (const id of ids) {
    const task = TASKS.find((t) => t.id === id);
    if (!task) { console.log('unknown task', id); continue; }
    const r = await runTask(win, task, n);
    console.log([r.task, r.ok ? 'PASS' : 'fail', r.secs + 's', 'calls=' + r.modelCalls, 'tools=' + r.toolCalls, 'replans=' + r.replans, 'leaks=' + r.leaks, 'rep=' + r.repeats, 'maxTok=' + r.maxReqTokens, r.timedOut ? 'TIMEOUT' : '', r.error || ''].join(' '));
  }
  app.exit(0);
});
