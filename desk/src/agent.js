'use strict';
const { streamChat } = require('./llm');
const { SYSTEM_PROMPT } = require('./prompt');
const { takeNotices } = require('./helpers');

const COMPACT_TOKENS = 24000;
const MAX_TOOL_CHARS = 8000;

// ---- helpers (exported for tests) ------------------------------------------------------------
const DANGER_PATTERNS = [
  /\brm\s+(-[a-z]*\s+)*-[a-z]*[rf][a-z]*\b/i,          // rm -rf, rm -fr, rm -r, rm -f
  /\brm\s+--(recursive|force)\b/i,
  /\bsudo\b/i,
  /\bdiskutil\b/i,
  /\bmkfs(\.\w+)?\b/i,
  /\b(shutdown|reboot|halt)\b/i,
  />\s*\/dev\/(?!null\b|stdout\b|stderr\b)/i,
  /\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(ba|z|da)?sh\b/i,
  /\bgit\s+push\b[^;&|]*(--force\b|--force-with-lease\b|\s-f\b)/i,
  /\bgit\s+reset\s+--hard\b/i,
  /\bdd\s+[^;&|]*\bof=/i,
  /\bchmod\s+-R\s+0?777\b/i,
  /:\(\)\s*\{/,
  /\blaunchctl\s+(unload|remove)\b/i,
  /\bkillall\b/i
];
// Plain-language view of the list above (shown in Settings).
const DANGER_LABELS = [
  'Deleting files recursively or by force (rm -r, rm -f)',
  'Running anything as administrator (sudo)',
  'Disk tools (diskutil, mkfs, dd of=...)',
  'Shutting down or rebooting the Mac',
  'Writing to /dev devices',
  'Piping a download into a shell (curl ... | sh)',
  'Force-pushing or hard-resetting git',
  'Opening permissions wide (chmod -R 777)',
  'Fork bombs',
  'Removing launch agents, killing all processes (launchctl unload, killall)'
];
function isDangerous(cmd) {
  const c = String(cmd || '');
  return DANGER_PATTERNS.some((r) => r.test(c));
}

function estimateTokens(messages) {
  let chars = 0;
  for (const m of messages) {
    if (typeof m.content === 'string') chars += m.content.length;
    else if (Array.isArray(m.content)) for (const p of m.content) chars += p.type === 'text' ? (p.text || '').length : 300;
    if (m.tool_calls) chars += JSON.stringify(m.tool_calls).length;
  }
  return Math.ceil(chars / 3.5);
}

// Replace old tool results with a stub, keeping the newest `keep`. Returns number changed.
function compactMessages(messages, keep) {
  keep = keep === undefined ? 2 : keep;
  const idx = [];
  messages.forEach((m, i) => { if (m.role === 'tool') idx.push(i); });
  let n = 0;
  for (const i of idx.slice(0, Math.max(0, idx.length - keep))) {
    if (messages[i].content !== '[older result omitted]') { messages[i].content = '[older result omitted]'; n++; }
  }
  return n;
}

// Only the newest image message keeps its picture.
function dropOldImages(messages) {
  let seen = false;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === 'user' && Array.isArray(m.content) && m.content.some((p) => p.type === 'image_url')) {
      if (seen) m.content = '[older screenshot omitted]';
      seen = true;
    }
  }
}

function datePrefix(d) {
  d = d || new Date();
  const p = (n) => String(n).padStart(2, '0');
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  return '[' + days[d.getDay()] + ' ' + d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ']';
}

function extractPlan(text) {
  const lines = String(text || '').split('\n').map((l) => l.trim());
  const items = lines.filter((l) => /^\d+[.)]\s+\S/.test(l)).map((l) => l.replace(/^\d+[.)]\s+/, ''));
  return items.length >= 2 ? items : null;
}

function short(s, n) { s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
function host(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return short(u, 40); } }

function defaultSummary(name, a) {
  a = a || {};
  switch (name) {
    case 'web_search': return 'Searched “' + short(a.query, 50) + '”';
    case 'browser_go': return 'Opened ' + host(a.url);
    case 'browser_click': return 'Clicked [' + a.id + ']';
    case 'browser_type': return 'Typed into [' + a.id + ']' + (a.enter ? ' and pressed Enter' : '');
    case 'browser_scroll': return 'Scrolled ' + (a.direction || 'down');
    case 'browser_back': return 'Went back';
    case 'browser_read': return 'Read page' + (a.page > 1 ? ' ' + a.page : '');
    case 'screen_look': return 'Looked at ' + (a.app || 'the front app');
    case 'screen_click': return a.id !== undefined ? 'Pressed screen element [' + a.id + ']' : 'Clicked screen at ' + a.x + ',' + a.y;
    case 'screen_type': return 'Typed “' + short(a.text, 40) + '”';
    case 'screen_key': return 'Pressed ' + a.keys;
    case 'open_app': return 'Opened ' + a.name;
    case 'run_shell': return 'Ran ' + short(a.command, 60);
    case 'diary_search': return 'Searched diary “' + short(a.query, 40) + '”';
    case 'ask_user': return 'Asked Ben';
    default: return name;
  }
}

function parseArgs(s) {
  if (s && typeof s === 'object') return s;
  s = String(s || '').trim();
  if (!s) return {};
  try { return JSON.parse(s); } catch (e) { /* repair attempt */ }
  try { return JSON.parse(s.replace(/,\s*([}\]])/g, '$1')); } catch (e) { return null; }
}

const SCREEN_GATED = new Set(['screen_click', 'screen_type', 'screen_key']);
// Loop guard: tools where repeating the exact same call is normal.
const REPEAT_OK = new Set(['ask_user', 'agent_list', 'agent_start', 'agent_stop', 'browser_scroll']);
const STUCK_REPEATS = 3; // the 3rd identical call in a row is refused

// ---- Agent -----------------------------------------------------------------------------------
class Agent {
  /**
   * @param {object} o
   *  getSettings(): {gatewayUrl, model, maxSteps, vision, mode:'ask'|'hands-off'}
   *  tools: { name: fn(args, ctx) | {run, gate?} }  results: string | {text, image?, summary?}
   *  toolDefs: array of OpenAI tool schemas (constant per run)
   *  emit(event), approve(req)->'once'|'task'|'deny', askUser(question, signal)->string
   *  onThreadChange(thread) optional save hook
   *  slot: Limiter (shared run slots), onState('queued'|'running'|'waiting'), onEnd() optional
   */
  constructor(o) {
    this.o = o;
    this.running = false;
    this.steerQueue = [];
    this.abort = null;
    this.taskAllow = new Set();
    this.threadId = null;
    this.release = null;
    this.last = { key: '', count: 0, text: '' };
    this.strikes = 0;
  }

  toolDefs() { return typeof this.o.toolDefs === 'function' ? this.o.toolDefs() : this.o.toolDefs; }

  emit(ev) { try { this.o.emit && this.o.emit(ev); } catch (e) { /* UI errors must not kill the loop */ } }

  steer(text) { if (this.running && text && text.trim()) { this.steerQueue.push(text.trim()); return true; } return false; }

  stop() { if (this.abort) this.abort.abort(); }

  state(s) { try { this.o.onState && this.o.onState(s); } catch (e) { /* ignore */ } }
  free() { const r = this.release; this.release = null; if (r) r(); }
  // Waiting for Ben must not hold a run slot (two helpers waiting would block the primary forever).
  async waitingForBen(fn, signal) {
    this.state('waiting');
    return this.withoutSlot(fn, signal, true);
  }
  // Run fn (something that can block on others) without holding a run slot, then queue for a slot again.
  async withoutSlot(fn, signal, report) {
    this.free();
    try { return await fn(); } finally {
      if (this.o.slot && !signal.aborted) { try { this.release = await this.o.slot.acquire(signal); } catch (e) { /* aborted while queued */ } }
      if (report && !signal.aborted) this.state('running');
    }
  }

  async run(thread, userText) {
    if (this.running) throw new Error('already running');
    this.running = true;
    this.abort = new AbortController();
    this.taskAllow = new Set();
    this.steerQueue = [];
    this.last = { key: '', count: 0, text: '' };
    this.strikes = 0;
    this.threadId = thread.id;
    const signal = this.abort.signal;
    thread.messages = thread.messages || [];
    thread.items = thread.items || [];
    const save = () => { try { this.o.onThreadChange && this.o.onThreadChange(thread); } catch (e) { /* ignore */ } };
    const pushUser = (text) => {
      const notes = takeNotices(thread); // finished-helper updates ride along with Ben's next message
      thread.messages.push({ role: 'user', content: datePrefix() + ' ' + (notes ? notes + '\n' : '') + text });
      thread.items.push({ t: 'user', text });
    };
    repairHistory(thread.messages);
    pushUser(userText);
    save();
    let stopped = false;
    let failure = null;
    try {
      if (this.o.slot) {
        if (this.o.slot.full()) { this.state('queued'); this.emit({ type: 'queued' }); }
        try { this.release = await this.o.slot.acquire(signal); } catch (e) { /* aborted while queued: the loop below sees it */ }
        if (!signal.aborted) { this.state('running'); this.emit({ type: 'started' }); }
      }
      let step = 0;
      for (;;) {
        if (signal.aborted) { stopped = true; break; }
        // inject steering messages
        while (this.steerQueue.length) {
          const t = this.steerQueue.shift();
          pushUser(t);
          this.emit({ type: 'user', text: t, steer: true });
        }
        const s = this.o.getSettings();
        const maxSteps = Number(s.maxSteps) || 40;
        if (step >= maxSteps) {
          const note = 'I reached the step limit (' + maxSteps + ') and stopped. Tell me to continue if you want me to keep going.';
          thread.messages.push({ role: 'assistant', content: note });
          thread.items.push({ t: 'assistant', text: note });
          this.emit({ type: 'text', delta: note });
          this.emit({ type: 'assistant_end', text: note });
          break;
        }
        step++;
        if (estimateTokens(thread.messages) > COMPACT_TOKENS) {
          if (compactMessages(thread.messages, 2)) this.emit({ type: 'compacted' });
        }
        dropOldImages(thread.messages);

        const t0 = Date.now();
        let res;
        try {
          res = await streamChat({
            gatewayUrl: s.gatewayUrl,
            model: s.model,
            messages: [{ role: 'system', content: SYSTEM_PROMPT }, ...thread.messages.map(cleanMsg)],
            tools: this.toolDefs(),
            signal,
            apiKey: s.apiKey,
            onText: (d) => this.emit({ type: 'text', delta: d }),
            onReasoning: (d) => this.emit({ type: 'reasoning', delta: d })
          });
        } catch (e) {
          if (signal.aborted) { stopped = true; break; }
          failure = String(e && e.message || e);
          this.emit({ type: 'error', message: failure });
          break;
        }
        if (signal.aborted) {
          stopped = true;
          if (res && res.content) {
            thread.messages.push({ role: 'assistant', content: res.content });
            thread.items.push({ t: 'assistant', text: res.content });
          }
          break;
        }
        const secs = Math.max(1, Math.round((Date.now() - t0) / 1000));
        const ttftMs = Math.round(res.firstTokenMs || 0);
        (thread.requests = thread.requests || []).push({ at: Date.now(), model: s.model, ttftMs, step });
        if (thread.requests.length > 200) thread.requests.splice(0, thread.requests.length - 200);
        const msg = { role: 'assistant', content: res.content || '' };
        if (res.toolCalls.length) {
          msg.tool_calls = res.toolCalls.map((c) => ({ id: c.id, type: 'function', function: { name: c.name, arguments: c.arguments } }));
        }
        thread.messages.push(msg);
        if (res.content || res.reasoning) {
          thread.items.push({ t: 'assistant', text: res.content, thinking: res.reasoning || '', thinkSecs: res.reasoning ? secs : 0, ttftMs });
        }
        this.emit({ type: 'assistant_end', text: res.content, reasoning: res.reasoning, thinkSecs: res.reasoning ? secs : 0, ttftMs, toolCalls: res.toolCalls.length });
        const plan = extractPlan(res.content);
        if (plan) { thread.items.push({ t: 'plan', items: plan }); this.emit({ type: 'plan', items: plan }); }
        save();

        if (!res.toolCalls.length) {
          if (this.steerQueue.length) continue; // Ben added something while we were answering
          break;
        }

        let pendingImage = null;
        for (let ci = 0; ci < res.toolCalls.length; ci++) {
          const call = res.toolCalls[ci];
          if (signal.aborted) {
            thread.messages.push({ role: 'tool', tool_call_id: call.id, content: '[stopped by user]' });
            stopped = true;
            continue;
          }
          const out = await this.runTool(call, thread, signal);
          thread.messages.push({ role: 'tool', tool_call_id: call.id, content: out.text });
          if (out.image) pendingImage = out.image;
          if (signal.aborted) stopped = true;
        }
        if (pendingImage && (s.vision === 'on' || s.vision === true)) {
          thread.messages.push({ role: 'user', content: [{ type: 'text', text: '[screenshot of the result above]' }, { type: 'image_url', image_url: { url: pendingImage } }] });
        }
        save();
        if (stopped) break;
      }
    } catch (e) {
      failure = String(e && e.message || e);
      this.emit({ type: 'error', message: failure });
    } finally {
      repairHistory(thread.messages);
      this.free();
      try { this.o.onEnd && this.o.onEnd(); } catch (e) { /* ignore */ }
      this.running = false;
      this.abort = null;
      this.steerQueue = [];
      save();
      this.emit({ type: 'done', stopped });
    }
    return { stopped, error: failure };
  }

  async runTool(call, thread, signal) {
    const name = call.name;
    const args = parseArgs(call.arguments);
    const stepId = call.id;
    const summaryStart = defaultSummary(name, args || {});
    const item = { t: 'step', id: stepId, tool: name, args: args || call.arguments, summary: summaryStart, ok: true, preview: '' };
    thread.items.push(item);
    this.emit({ type: 'step_start', id: stepId, tool: name, args: args || call.arguments, summary: summaryStart });
    const finish = (text, ok, summary) => {
      text = String(text == null ? '' : text);
      if (text.length > MAX_TOOL_CHARS) text = text.slice(0, MAX_TOOL_CHARS) + '\n[truncated]';
      item.ok = ok; item.preview = short(text, 400); if (summary) item.summary = summary;
      this.emit({ type: 'step_end', id: stepId, tool: name, ok, summary: item.summary, preview: item.preview, result: text.slice(0, 2000) });
      return text;
    };
    if (args === null) return { text: finish('Error: arguments were not valid JSON.', false) };
    const entry = this.o.tools[name];
    const ctx = { signal, settings: this.o.getSettings(), thread, waitForBen: (fn) => this.waitingForBen(fn, signal), stepId };
    if (name === 'ask_user') {
      try {
        const answer = await this.waitingForBen(() => this.o.askUser(String(args.question || ''), signal), signal);
        return { text: finish(answer, !signal.aborted, 'Asked Ben: ' + short(args.question, 60)) };
      } catch (e) { return { text: finish('Error: ' + (e && e.message || e), false) }; }
    }
    if (!entry) return { text: finish('Error: unknown tool ' + name, false) };
    const run = typeof entry === 'function' ? entry : entry.run;
    try {
      // loop guard: the same call again and again is a stuck model, not progress
      const key = name + ':' + JSON.stringify(args);
      if (!REPEAT_OK.has(name) && this.last.key === key && this.last.count >= STUCK_REPEATS - 1) {
        this.strikes++;
        const stuck = { tool: name, args, summary: summaryStart, count: this.last.count };
        if (this.strikes >= 2 && this.o.onStuck) {
          this.strikes = 0; this.last = { key: '', count: 0, text: '' };
          const reply = await this.waitingForBen(() => this.o.onStuck(stuck, signal), signal);
          if (signal.aborted) return { text: finish('[stopped by user]', false) };
          return { text: finish(reply, true, 'Asked Ben for help: stuck on ' + short(summaryStart, 40)) };
        }
        this.last.count++;
        return { text: finish('Stuck: you have made this exact call ' + this.last.count + ' times in a row and nothing changed. Do NOT repeat it. Try something different (another element, another page, a different tool) or call ask_user.', false, 'Stopped a loop: ' + short(summaryStart, 40)) };
      }
      // approvals
      const settings = ctx.settings;
      const hands = settings.mode === 'hands-off';
      let need = null; // {kind, danger, text}
      if (name === 'run_shell') {
        const danger = isDangerous(args.command);
        if (danger) need = { kind: 'shell', danger: true, text: String(args.command) };
        else if (!hands) need = { kind: 'shell', danger: false, text: String(args.command) };
      } else if (SCREEN_GATED.has(name) && !hands) {
        need = { kind: 'screen', danger: false, text: summaryStart };
      }
      if (need && !(!need.danger && this.taskAllow.has(need.kind))) {
        const verdict = await this.waitingForBen(() => this.o.approve({ id: stepId, tool: name, args, ...need }, signal), signal);
        if (signal.aborted) return { text: finish('[stopped by user]', false) };
        if (verdict === 'deny') return { text: finish('Ben denied this action. Do not retry it; ask him what to do instead.', false, 'Denied: ' + summaryStart) };
        if (verdict === 'task' && !need.danger) this.taskAllow.add(need.kind);
      }
      const r = await run(args, ctx);
      let text = typeof r === 'string' ? r : (r && r.text) || '';
      if (this.last.key === key) {
        this.last.count++;
        if (!REPEAT_OK.has(name) && this.last.count === 2 && text === this.last.text && (name === 'browser_click' || name === 'screen_click')) text += '\n[Nothing changed after clicking the same thing twice. It is not responding: try something different.]';
      } else this.last = { key, count: 1, text: '' };
      this.last.text = typeof r === 'string' ? r : (r && r.text) || '';
      const summary = r && typeof r === 'object' && r.summary ? r.summary : null;
      const ok = !(r && typeof r === 'object' && r.error);
      const out = { text: finish(text, ok, summary) };
      if (r && typeof r === 'object' && r.image) out.image = r.image;
      return out;
    } catch (e) {
      if (signal.aborted) return { text: finish('[stopped by user]', false) };
      return { text: finish('Error: ' + (e && e.message || e), false) };
    }
  }
}

// Every assistant tool_call needs a tool message after it (a crash or error mid-run can leave one dangling,
// which makes the API reject the whole thread forever). Returns number of stubs added.
function repairHistory(messages) {
  let n = 0;
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (m.role !== 'assistant' || !m.tool_calls) continue;
    let j = i + 1;
    const have = new Set();
    while (j < messages.length && messages[j].role === 'tool') { have.add(messages[j].tool_call_id); j++; }
    const missing = m.tool_calls.filter((c) => !have.has(c.id));
    if (missing.length) {
      messages.splice(j, 0, ...missing.map((c) => ({ role: 'tool', tool_call_id: c.id, content: '[interrupted]' })));
      n += missing.length;
      i = j + missing.length - 1;
    }
  }
  return n;
}

function cleanMsg(m) {
  const o = { role: m.role, content: m.content };
  if (m.tool_calls) o.tool_calls = m.tool_calls;
  if (m.tool_call_id) o.tool_call_id = m.tool_call_id;
  return o;
}

module.exports = { DANGER_LABELS, STUCK_REPEATS, Agent, repairHistory, isDangerous, estimateTokens, compactMessages, dropOldImages, datePrefix, extractPlan, defaultSummary, DANGER_PATTERNS, COMPACT_TOKENS };
