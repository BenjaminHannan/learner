'use strict';
const { streamChat } = require('./llm');
const { SYSTEM_PROMPT } = require('./prompt');
const { takeNotices } = require('./helpers');
const { NAME, P } = require('./user');
const { usesLine } = require('../renderer/uses');

const COMPACT_TOKENS = 24000;
const MAX_TOOL_CHARS = 8000;

// ---- verification layer ----------------------------------------------------------------------
// Tools that change something; a final answer after any of them gets one cheap check turn first.
const STATE_CHANGING = new Set(['browser_go', 'browser_click', 'browser_type', 'browser_back', 'screen_click', 'screen_type', 'screen_key', 'open_app']);
const RECHECK_TOOLS = new Set(['browser_go', 'browser_click', 'browser_type', 'browser_back', 'browser_scroll', 'screen_click', 'screen_type', 'screen_key', 'open_app']);
const MAX_VERIFY = 2;                 // check turns per task (so it can never loop)
// The gateway maps qwen36-fast to the same upstream model with thinking off, so the check shares the prompt cache with real turns.
const VERIFY_MODEL = 'qwen36-fast';
const VERIFY_MAX_TOKENS = 200;
const CHECK_MARK = '[Self-check]';
// a reply that asks Ben for a password / login details (the prompt forbids it; a small model still does it)
const SECRET_WORD = /\b(password|passcode|passphrase|credentials|login details|log-?in info|verification code|2fa code|one-time code)\b/i;
const ASK_WORD = /\b(need|provide|send|share|give|tell me|what is|what's|enter|type|could you|can you|please)\b/i;
function asksForSecret(text) { return String(text || '').split(/(?<=[.?!\n])\s+/).some((s) => SECRET_WORD.test(s) && (ASK_WORD.test(s) || /\?\s*$/.test(s))); }
const CHECK_MESSAGE = CHECK_MARK + ' Compare your last answer with the evidence in the tool results above (After lines, page text, command output). Reply VERIFIED if every claim is backed by that evidence, or NOT DONE: <what is missing>. One short line. Do not call tools.';
const RECHECK_HINT = '\n[That failed. Before retrying, re-read the page or screen (browser_read / screen_look) to see its real state, then try a different approach.]';
// "remember that ..." style asks: the small model sometimes says "saved" without calling memory_save, so the check catches it.
const REMEMBER_ASK = /\b(remember|don'?t forget|keep in mind|make a note|note that)\b/i;
// The fact in a "remember (that) ..." ask, in third person ("I take X" -> "Ben takes X" is too clever; "I" -> "Ben" is enough).
const VERB_KEEP = new Set(['can', 'will', 'should', 'could', 'would', 'might', 'must', 'was', 'had', 'did', 'used', "don't", "didn't", "can't", "won't", 'never', 'always', 'usually', 'often', 'also', 'only', 'really', 'still']);
function thirdPerson(v) {
  const l = v.toLowerCase();
  if (VERB_KEEP.has(l) || /ed$/.test(l)) return v;
  if (l === 'have') return 'has'; if (l === 'do') return 'does'; if (l === 'go') return 'goes'; if (l === "don't") return "doesn't";
  if (/[^aeiou]y$/.test(l)) return v.slice(0, -1) + 'ies';
  if (/(s|sh|ch|x|z|o)$/.test(l)) return v + 'es';
  return v + 's';
}
function rememberFact(text) {
  const m = String(text || '').match(/\b(?:remember|don'?t forget|keep in mind|make a note|note)\b[\s,:]*(?:that\s+|of\s+)?([\s\S]+)/i);
  if (!m) return '';
  return m[1].trim().replace(/[\s.!]+$/, '').replace(/\bI'm\b/gi, NAME + ' is').replace(/\bI am\b/gi, NAME + ' is').replace(/\bI (\w+)/g, (m0, v) => NAME + ' ' + thirdPerson(v)).replace(/\bI\b/g, NAME).replace(/\bmy\b/gi, NAME + "'s").replace(/\bme\b/gi, NAME).slice(0, 300);
}
const factWords = (s) => new Set((String(s || '').toLowerCase().match(/[a-z0-9]+/g) || []).filter((w) => w.length > 2 && ![NAME.toLowerCase(), 'ben', 'bens', 'that', 'the', 'and', 'remember'].includes(w)));
function relatesTo(fact, ask) { const a = factWords(fact), b = factWords(ask); if (!a.size || !b.size) return false; let n = 0; for (const w of b) if (a.has(w)) n++; return n / b.size >= 0.3; }
const verifyOn = (s) => !(s && (s.verify === false || s.verify === 'off'));
// 'VERIFIED' -> {ok:true}; 'NOT DONE: x' -> {ok:false, reason:x}; anything unclear -> null (accept the answer, never block on noise)
function parseCheck(text) {
  const t = String(text || '').trim();
  if (/^\W*VERIFIED\b/i.test(t)) return { ok: true };
  const m = /^\W*NOT\s+DONE\b\W*([\s\S]*)$/i.exec(t);
  if (m) return { ok: false, reason: short(m[1] || 'something is missing', 160) };
  return null;
}

// Empty content but some thinking text: look for the verdict at the end of it (the last NOT DONE / VERIFIED wins).
function parseCheckLoose(text) {
  const t = String(text || '');
  let last = null, m;
  const re = /\b(VERIFIED|NOT\s+DONE)\b\W*([^\n]*)/gi;
  while ((m = re.exec(t))) last = m;
  if (!last) return null;
  return /^VERIFIED/i.test(last[1]) ? { ok: true } : { ok: false, reason: short(last[2] || 'something is missing', 160) };
}

// ---- helpers (exported for tests) ------------------------------------------------------------
// a plain echo/printf of text only prints it (the model uses it to narrate): no approval card
const SAFE_ECHO = /^\s*(?:echo|printf)\s+(?:"[^"`$\\;&|<>]*"|'[^']*'|[\w .,:!?'-]*)\s*$/;
// commands that only look (list, read, count): no approval card. Pipes between them are fine; anything else (redirects, ;, &&, $(), find -exec) is not.
const READONLY = new Set(['ls', 'cat', 'pwd', 'date', 'whoami', 'head', 'tail', 'wc', 'grep', 'which', 'df', 'du', 'uptime', 'hostname', 'uname', 'file', 'stat', 'sw_vers', 'sort', 'uniq', 'basename', 'dirname', 'realpath', 'id', 'find', 'echo', 'printf']);
const SENSITIVE = /\.ssh\b|\.aws\b|\.gnupg\b|keychain|\.env\b|id_rsa|id_ed25519|\.netrc|passw|secret|token|cookies?\b|login data/i;
function isReadOnly(cmd) {
  const c = String(cmd || '').trim();
  if (!c || /[&;<>`$()\n\\]/.test(c) || SENSITIVE.test(c)) return false;
  return c.split('|').every((st) => {
    const w = st.trim().split(/\s+/)[0].toLowerCase();
    if (!READONLY.has(w)) return false;
    if (w === 'find' && /\s-(exec|execdir|ok|okdir|delete|fprint\w*|fls)\b/.test(st)) return false;
    return true;
  });
}
// the program a command runs ("ls -la" -> "ls"), or '' when it is a compound command (pipes, &&, ;, redirects): those are never "always allowed"
function shellProgram(cmd) {
  const c = String(cmd || '').trim();
  if (!c || /[|&;<>`$()\n]/.test(c)) return '';
  const w = c.split(/\s+/)[0].replace(/^.*[\\/]/, '');
  // programs that run anything they are given are never "always allowed" as a whole
  return /^[\w.+-]{1,30}$/.test(w) && !/^(?:sh|bash|zsh|fish|dash|python[\d.]*|node|ruby|perl|php|osascript|env|xargs|eval|exec|sudo|su|ssh|open|curl|wget|nc|powershell|pwsh|cmd)$/i.test(w) ? w.toLowerCase() : '';
}
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
  /\bkillall\b/i,
  // Windows / PowerShell twins of the above
  /\bRemove-Item\b[^;&|]*-Recurse/i,
  /\b(del|erase|rmdir|rd)\b[^;&|]*\s\/[sq]\b/i,
  /\b(Format-Volume|diskpart|Clear-Disk|Stop-Computer|Restart-Computer)\b/i,
  /\bformat\s+[a-z]:/i,
  /\bStart-Process\b[^;&|]*-Verb\s+RunAs/i,
  /\b(iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^;&]*\|\s*(iex|Invoke-Expression)\b/i
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
  'Removing launch agents, killing all processes (launchctl unload, killall)',
  'Windows: Remove-Item -Recurse, del /s, format, diskpart, Stop-Computer, running as administrator, piping a download into iex'
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

// The date stamp of a new turn, plus a plain warning when the thread's previous turn was on another day: a chat left open overnight
// otherwise makes the model treat last night's "tomorrow" as still tomorrow (seen: "Tomorrow (Wednesday Oct 28)" on Wed Oct 28).
const STAMP_RE = /\[(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat) (\d{4}-\d{2}-\d{2}) \d{2}:\d{2}\]/g;
function nowStamp(messages, d) {
  d = d || new Date();
  const stamp = datePrefix(d);
  let prev = null;
  for (let i = (messages || []).length - 1; i >= 0 && !prev; i--) {
    const m = messages[i];
    if (!m || m.role !== 'user' || typeof m.content !== 'string') continue;
    const all = [...m.content.matchAll(STAMP_RE)];
    if (all.length) prev = all[all.length - 1][1];
  }
  const today = stamp.slice(5, 15);
  if (!prev || prev === today) return stamp;
  const long = d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  return stamp + ' (New day: today is ' + long + '. The earlier messages here were on ' + prev + ', so their "today" and "tomorrow" are out of date.)';
}

// Ben Oct 28: "tell me what you plan to do and what you are doing, not straight into the task". Per-turn (user message), so the cached system prompt stays small.
const NARRATE = '[If this needs tools: first say your plan in 2 to 4 short lines, then before each step say in one short line what you do next. No tools needed: just answer.]';
const PLAN_STEP_MAX = 120;
function extractPlan(text) {
  const lines = String(text || '').split('\n').map((l) => l.trim());
  const items = lines.filter((l) => /^\d+[.)]\s+\S/.test(l)).map((l) => l.replace(/^\d+[.)]\s+/, '').replace(/\*\*|__|`/g, ''));
  // Steps are short. Long numbered items are reasons or caveats ("Login access - You mentioned ... I need the password"),
  // and a plan card would tick them off as done; leave those as text. The renderer's isPlan uses the same rule.
  return items.length >= 2 && items.every((s) => s.length <= PLAN_STEP_MAX) ? items : null;
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
    case 'memory_save': return 'Remembered: ' + short(a.fact, 50);
    case 'memory_forget': return 'Forgot: ' + short(a.match || a.id, 50);
    case 'track_add': return 'Tracking: ' + short(a.what, 50);
    case 'track_done': return 'Tracking done: ' + short(a.what, 50);
    case 'verify': return 'Checking its work';
    case 'ask_user': return P('Asked Ben');
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
const REPEAT_OK = new Set(['ask_user', 'agent_list', 'agent_start', 'agent_update', 'agent_stop', 'browser_scroll']);
const STUCK_REPEATS = 3; // the 3rd identical call in a row is refused

// ---- Agent -----------------------------------------------------------------------------------
class Agent {
  /**
   * @param {object} o
   *  getSettings(): {gatewayUrl, model, maxSteps, vision, mode:'ask'|'hands-off'}
   *  tools: { name: fn(args, ctx) | {run, gate?} }  results: string | {text, image?, summary?}
   *  toolDefs: array of OpenAI tool schemas (constant per run)
   *  emit(event), approve(req)->'once'|'task'|'always'|'deny', askUser(question, signal)->string
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
    this.usedState = false;
    this.usedWeb = false;
    this.verifyCount = 0;
    this.memBlock = '';
  }

  toolDefs() { return typeof this.o.toolDefs === 'function' ? this.o.toolDefs() : this.o.toolDefs; }

  emit(ev) { try { this.o.emit && this.o.emit(ev); } catch (e) { /* UI errors must not kill the loop */ } }

  steer(text) { if (this.running && text && text.trim()) { this.steerQueue.push(text.trim()); return true; } return false; }

  stop() { if (this.abort) this.abort.abort(); }

  state(s, info) { try { this.o.onState && this.o.onState(s, info); } catch (e) { /* ignore */ } }
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

  // opts.display: what the transcript shows as Ben's message when userText carries a hidden per-turn instruction (voice calls)
  async run(thread, userText, opts) {
    if (this.running) throw new Error('already running');
    this.running = true;
    this.abort = new AbortController();
    this.taskAllow = new Set();
    this.steerQueue = [];
    this.last = { key: '', count: 0, text: '' };
    this.strikes = 0;
    this.usedState = false; this.usedWeb = false;
    this.verifyCount = 0;
    this.memBlock = '';
    this.taskText = String(userText || ''); this.usedMemSave = false; this.memChecks = 0; this.secretChecks = 0;
    try { this.memBlock = this.o.memory ? this.o.memory.block() : ''; } catch (e) { this.memBlock = ''; }
    try { const tb = this.o.tracking ? this.o.tracking.block() : ''; if (tb) this.memBlock += (this.memBlock ? '\n' : '') + tb; } catch (e) { /* no tracking block */ }
    this.threadId = thread.id;
    const signal = this.abort.signal;
    thread.messages = thread.messages || [];
    thread.items = thread.items || [];
    const save = () => { try { this.o.onThreadChange && this.o.onThreadChange(thread); } catch (e) { /* ignore */ } };
    const pushUser = (text, shown) => {
      const notes = takeNotices(thread); // finished-helper updates ride along with Ben's next message
      // Ben's picks from first-run setup ride in the first user message of a thread, beside the date. Never in the system prompt or tools.
      let ctx = '';
      if (!thread.messages.some((m) => m.role === 'user')) { try { const s = this.o.getSettings && this.o.getSettings(); ctx = s ? usesLine(s.uses, s.usesOther) : ''; } catch (e) { ctx = ''; } }
      // The memory block is a snapshot written into this stored turn when the task starts: older turns keep theirs, so the history stays byte-stable (cache).
      thread.messages.push({ role: 'user', content: (this.memBlock ? this.memBlock + '\n' : '') + nowStamp(thread.messages) + ' ' + NARRATE + (ctx ? ' ' + ctx : '') + ' ' + (notes ? notes + '\n' : '') + text });
      thread.items.push({ t: 'user', text: shown || text });
    };
    repairHistory(thread.messages);
    pushUser(userText, opts && opts.display);
    save();
    let stopped = false;
    let failure = null;
    try {
      if (this.o.slot) {
        if (this.o.slot.full()) { this.state('queued', { running: this.o.slot.active }); this.emit({ type: 'queued' }); }
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
        const maxSteps = Number(s.maxSteps) || 0; // 0 = no limit
        if (maxSteps && step >= maxSteps) {
          const note = 'I reached the step limit (' + maxSteps + ') and stopped. Tell me to continue if you want me to keep going.';
          thread.messages.push({ role: 'assistant', content: note });
          thread.items.push({ t: 'assistant', text: note });
          this.emit({ type: 'text', delta: note });
          this.emit({ type: 'assistant_end', text: note });
          break;
        }
        step++;
        if (estimateTokens(thread.messages) > (Number(s.compactTokens) || COMPACT_TOKENS)) {
          if (compactMessages(thread.messages, 2)) this.emit({ type: 'compacted' });
        }
        dropOldImages(thread.messages);

        const t0 = Date.now();
        let res;
        try {
          res = await streamChat({
            gatewayUrl: s.gatewayUrl,
            model: s.model,
            messages: this.requestMessages(thread),
            tools: this.toolDefs(),
            signal,
            apiKey: s.apiKey,
            onText: (d) => this.emit({ type: 'text', delta: d }),
            onReasoning: () => this.emit({ type: 'reasoning', delta: '' }) // only that Glim is thinking; the text never leaves the main process
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
          thread.items.push({ t: 'assistant', text: res.content, thinking: !!res.reasoning, thinkSecs: res.reasoning ? secs : 0, ttftMs }); // Ben Oct 28: the reasoning is not kept for reading, only that Glim thought
        }
        // The check turn runs BEFORE assistant_end so its step lands inside the task's activity group, not after it.
        const verdict = (!res.toolCalls.length && !this.steerQueue.length) ? await this.verifyAnswer(thread, s, signal, res.content) : 'accept';
        this.emit({ type: 'assistant_end', text: res.content, thinkSecs: res.reasoning ? secs : 0, ttftMs, toolCalls: res.toolCalls.length });
        const plan = res.toolCalls.length ? extractPlan(res.content) : null; // a numbered list in a final answer is just the answer
        if (plan) { thread.items.push({ t: 'plan', items: plan }); this.emit({ type: 'plan', items: plan }); }
        save();

        if (!res.toolCalls.length) {
          if (this.steerQueue.length) continue; // Ben added something while we were answering
          if (verdict === 'continue') continue;
          if (verdict === 'stop') stopped = true;
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
          if (out.failed && RECHECK_TOOLS.has(call.name)) out.text += RECHECK_HINT;
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

  // Messages for one request: constant system prompt + the stored history (each task's memory snapshot is already in its user turn).
  requestMessages(thread) {
    return [{ role: 'system', content: SYSTEM_PROMPT }, ...thread.messages.map(cleanMsg)];
  }

  // One cheap check turn before accepting a final answer on a task that changed things. Same system prompt and tools (cache hit),
  // fast model, short reply. Returns 'continue' (NOT DONE: steer injected), 'stop' or 'accept'.
  async verifyAnswer(thread, s, signal, answer) {
    // Asked Ben for a password: send it back once to use the sign-in hand-off instead (no model call needed).
    if (asksForSecret(answer) && this.secretChecks < 1) {
      this.secretChecks++;
      const id = 'secretcheck_' + this.secretChecks;
      const summary = 'Re-checking: never ask for a password';
      thread.items.push({ t: 'step', id, tool: 'verify', args: {}, summary, ok: true, preview: 'the reply asked for login details' });
      this.emit({ type: 'step_start', id, tool: 'verify', args: {}, summary });
      this.emit({ type: 'step_end', id, tool: 'verify', ok: true, summary, preview: 'the reply asked for login details', result: '' });
      thread.messages.push({ role: 'user', content: CHECK_MARK + P(' Not done: never ask Ben for a password or login details. Open the site with browser_go instead; on its sign-in page click or type into the field as usual and the app lets Ben sign in himself. Then continue the task.') });
      return 'continue';
    }
    // A "remember ..." ask answered without a memory_save call: no model call needed, just send it back to save (counts toward the cap).
    if (this.o.memory && !this.usedMemSave && REMEMBER_ASK.test(this.taskText) && String(answer || '').trim()) {
      const fact = rememberFact(this.taskText);
      const n = ++this.memChecks;
      const id = 'memcheck_' + n;
      const step = (summary, ok, preview) => {
        thread.items.push({ t: 'step', id, tool: 'verify', args: {}, summary, ok, preview });
        this.emit({ type: 'step_start', id, tool: 'verify', args: {}, summary });
        this.emit({ type: 'step_end', id, tool: 'verify', ok, summary, preview, result: preview });
      };
      if (n === 1) {
        step('Re-checking: the fact was not saved yet', true, 'memory_save was not called for this');
        thread.messages.push({ role: 'user', content: CHECK_MARK + ' Not done yet: nothing new was saved. Call memory_save with this fact (not an old one): "' + (fact || this.taskText.slice(0, 300)) + '", then answer in one line.' });
        return 'continue';
      }
      // Second miss: save Ben's own words directly, so "remember ..." always works with the small model.
      if (fact) {
        let r; try { r = this.o.memory.save(fact); } catch (e) { r = { ok: false, error: String(e && e.message || e) }; }
        if (r.ok) { this.usedMemSave = true; step('Remembered: ' + short(r.fact.text, 50), true, P('Saved Ben\'s words directly')); }
        else step('Did not save: ' + short(String(r.error || '').replace(/^Not saved: /, ''), 60), false, r.error || '');
      }
    }
    if (!verifyOn(s) || !this.usedState || this.verifyCount >= MAX_VERIFY || !String(answer || '').trim()) return 'accept';
    const n = ++this.verifyCount;
    const id = 'verify_' + n;
    const item = { t: 'step', id, tool: 'verify', args: {}, summary: 'Checking its work', ok: true, preview: '' };
    thread.items.push(item);
    this.emit({ type: 'step_start', id, tool: 'verify', args: {}, summary: item.summary });
    const end = (summary, ok, preview) => {
      item.summary = summary; item.ok = ok; item.preview = ''; // the verifier's reasoning stays out of the chat
      this.emit({ type: 'step_end', id, tool: 'verify', ok, summary, preview: '', result: '' });
    };
    let verdict = null;
    try {
      const r = await streamChat({
        gatewayUrl: s.gatewayUrl, model: s.verifyModel || s.modelFast || VERIFY_MODEL,
        messages: [...this.requestMessages(thread), { role: 'user', content: CHECK_MESSAGE }],
        tools: this.toolDefs(), maxTokens: VERIFY_MAX_TOKENS, signal, apiKey: s.apiKey
      });
      if (!r.toolCalls.length) verdict = parseCheck(r.content) || (!String(r.content || '').trim() && r.reasoning ? parseCheckLoose(r.reasoning) : null);
    } catch (e) { if (signal.aborted) { end('Check stopped', false); return 'stop'; } }
    if (signal.aborted) { end('Check stopped', false); return 'stop'; }
    if (!verdict || verdict.ok) { end('Checked its work', true, verdict ? 'VERIFIED' : 'no verdict; accepted'); return 'accept'; }
    end('Re-checking: ' + short(verdict.reason, 80), true, verdict.reason);
    thread.messages.push({ role: 'user', content: CHECK_MARK + ' Not done yet: ' + verdict.reason + '. Look at the page or screen again, fix it with tools, then answer.' });
    return 'continue';
  }

  async runTool(call, thread, signal) {
    const name = call.name;
    const args = parseArgs(call.arguments);
    const stepId = call.id;
    const summaryStart = defaultSummary(name, args || {});
    const item = { t: 'step', id: stepId, tool: name, args: args || call.arguments, summary: summaryStart, ok: true, preview: '' };
    thread.items.push(item);
    this.emit({ type: 'step_start', id: stepId, tool: name, args: args || call.arguments, summary: summaryStart });
    const MAXC = (() => { try { return Number((this.o.getSettings() || {}).maxToolChars) || MAX_TOOL_CHARS; } catch (e) { return MAX_TOOL_CHARS; } })();
    const finish = (text, ok, summary) => {
      text = String(text == null ? '' : text);
      if (text.length > MAXC) text = text.slice(0, MAXC) + '\n[truncated]';
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
        return { text: finish(answer, !signal.aborted, P('Asked Ben: ') + short(args.question, 60)) };
      } catch (e) { return { text: finish('Error: ' + (e && e.message || e), false) }; }
    }
    if ((name === 'memory_save' || name === 'memory_forget') && this.o.memory) {
      try {
        if (name === 'memory_save') {
          // after reading web pages the "fact" may come from the page, not from Ben: Ask-first mode needs his OK, and the step says so
          const web = this.usedWeb;
          if (web && ctx.settings.mode !== 'hands-off' && !this.taskAllow.has('memory')) {
            const verdict = await this.waitingForBen(() => this.o.approve({ id: stepId, tool: name, args, kind: 'memory', danger: false, text: 'Remember this after reading the web? ' + short(args.fact, 200) }, signal), signal);
            if (signal.aborted) return { text: finish('[stopped by user]', false) };
            if (verdict === 'deny') return { text: finish(P('Ben did not want that saved. Do not retry it.'), false, 'Denied: remember ' + short(args.fact, 40)) };
            if (verdict === 'task') this.taskAllow.add('memory');
          }
          const r = this.o.memory.save(args.fact, args.topic);
          if (r.ok && (!REMEMBER_ASK.test(this.taskText) || relatesTo(r.fact.text, rememberFact(this.taskText)))) this.usedMemSave = true;
          return { text: finish(r.ok ? (r.replaced ? 'Updated memory: ' : 'Saved to memory: ') + r.fact.text : r.error, r.ok, r.ok ? 'Remembered' + (web ? ' (after reading the web)' : '') + ': ' + short(r.fact.text, 50) : 'Did not save: ' + short(r.error.replace(/^Not saved: /, ''), 60)) };
        }
        const r = this.o.memory.forget({ id: args.id, match: args.match });
        return { text: finish(r.ok ? 'Forgot ' + r.removed.length + ' fact(s): ' + r.removed.map((f) => f.text).join(' | ') : r.error, r.ok, r.ok ? 'Forgot ' + r.removed.length + ' fact(s)' : 'Nothing to forget') };
      } catch (e) { return { text: finish('Error: ' + (e && e.message || e), false) }; }
    }
    if ((name === 'track_add' || name === 'track_done') && this.o.tracking) {
      try {
        if (name === 'track_add') {
          const r = this.o.tracking.add({ what: args.what, source: args.source, until: args.until });
          return { text: finish(r.ok ? (r.replaced ? 'Updated tracked item: ' : 'Now tracking: ') + r.item.what + (r.item.until ? ' (until ' + r.item.until + ')' : '') : r.error, r.ok, r.ok ? 'Tracking: ' + short(r.item.what, 50) : 'Did not track: ' + short(r.error.replace(/^Not saved: /, ''), 60)) };
        }
        const r = this.o.tracking.done({ what: args.what });
        return { text: finish(r.ok ? 'Marked done: ' + r.item.what : r.error, r.ok, r.ok ? 'Tracking done: ' + short(r.item.what, 50) : 'Nothing to mark done') };
      } catch (e) { return { text: finish('Error: ' + (e && e.message || e), false) }; }
    }
    if (!entry) return { text: finish('Error: unknown tool ' + name, false) };
    if (STATE_CHANGING.has(name)) this.usedState = true;
    if (/^(web_|browser_)/.test(name) || name === 'screen_look') this.usedWeb = true;
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
          return { text: finish(reply, true, P('Asked Ben for help: stuck on ') + short(summaryStart, 40)) };
        }
        this.last.count++;
        return { text: finish('Stuck: you have made this exact call ' + this.last.count + ' times in a row and nothing changed. Do NOT repeat it. Try something different (another element, another page, a different tool) or call ask_user.', false, 'Stopped a loop: ' + short(summaryStart, 40)) };
      }
      // approvals
      const settings = ctx.settings;
      const hands = settings.mode === 'hands-off';
      let need = null; // {kind, danger, text, always: key for "Always allow", alwaysLabel}
      if (name === 'run_shell') {
        const danger = isDangerous(args.command);
        const prog = shellProgram(args.command);
        if (danger) need = { kind: 'shell', danger: true, text: String(args.command) };
        else if (!hands && !SAFE_ECHO.test(String(args.command)) && !isReadOnly(args.command)) need = { kind: 'shell', danger: false, text: String(args.command), always: prog ? 'shell:' + prog : '', alwaysLabel: prog ? '"' + prog + '" commands' : '' };
      } else if (SCREEN_GATED.has(name) && !hands) {
        need = { kind: 'screen', danger: false, text: summaryStart, always: 'screen', alwaysLabel: 'clicks and typing in apps' };
      }
      let allowed = [];
      try { const a = ctx.settings.alwaysAllow; if (Array.isArray(a)) allowed = a; } catch (e) { /* none */ }
      if (need && !need.danger && need.always && allowed.includes(need.always)) need = null; // Ben chose "Always allow" for this kind of action
      if (need && !(!need.danger && this.taskAllow.has(need.kind))) {
        const verdict = await this.waitingForBen(() => this.o.approve({ id: stepId, tool: name, args, ...need }, signal), signal);
        if (signal.aborted) return { text: finish('[stopped by user]', false) };
        if (verdict === 'deny') return { text: finish(P('Ben denied this action. Do not retry it; ask him what to do instead.'), false, 'Denied: ' + summaryStart) };
        if (verdict === 'task' && !need.danger) this.taskAllow.add(need.kind);
        if (verdict === 'always' && !need.danger) { this.taskAllow.add(need.kind); if (need.always && this.o.rememberAlways) { try { this.o.rememberAlways(need.always); } catch (e) { /* ignore */ } } }
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
      const out = { text: finish(text, ok, summary), failed: !ok };
      if (r && typeof r === 'object' && r.image) out.image = r.image;
      return out;
    } catch (e) {
      if (signal.aborted) return { text: finish('[stopped by user]', false) };
      return { text: finish('Error: ' + (e && e.message || e), false), failed: true };
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

module.exports = { isReadOnly, SAFE_ECHO, shellProgram, nowStamp, asksForSecret, rememberFact, relatesTo, parseCheckLoose, STATE_CHANGING, CHECK_MARK, CHECK_MESSAGE, MAX_VERIFY, parseCheck, DANGER_LABELS, STUCK_REPEATS, Agent, repairHistory, isDangerous, estimateTokens, compactMessages, dropOldImages, datePrefix, extractPlan, defaultSummary, DANGER_PATTERNS, COMPACT_TOKENS };
