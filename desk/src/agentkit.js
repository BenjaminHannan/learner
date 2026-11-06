'use strict';
// Track AGENT1 (Ben 2026-11-04: "it's being pretty dumb", "it just keeps repeating", "it didn't do what I asked it to").
// Harness changes that make the same small brain act better: what it is shown and how its choices become actions. No weights change.
// Each change has a name and was measured on the agent bench (test/agentbench, MARKS-agent-v1.md) before it got one.
// settings.agentKit: 'all', or a list of names. Missing: DEFAULTS (all off until the lead's real-app check flips them).
const FLAGS = ['sso', 'diet', 'pins', 'stuck', 'think'];
const DEFAULTS = { sso: false, diet: false, pins: false, stuck: false, think: false };
function on(settings, name) {
  const k = settings && settings.agentKit;
  if (k === 'all') return FLAGS.includes(name);
  if (Array.isArray(k)) return k.includes(name);
  return !!DEFAULTS[name];
}
function clean(v) {
  if (v === 'all') return 'all';
  if (typeof v === 'string') v = v.split(',');
  return [...new Set((Array.isArray(v) ? v : []).map((x) => String(x).trim()).filter((x) => FLAGS.includes(x)))];
}

// sso: a sign-in page offering "Sign in with Google / Microsoft / ..." needs no saved password; the provider usually knows Ben already.
// Ben's M3 run (Schoology + Google SSO) and the bench's school tasks: browser_sign_in found no saved login, so Glim handed the page back
// to Ben (or gave up) instead of clicking the Google button. The snapshot lines naming such a button, newest ids.
const SSO_RE = /\b(?:(?:sign|log)\s*(?:in|on)|continue|login)\s+(?:with|using|via)\s+(?:your\s+)?(?:google|microsoft|office\s*365|apple|facebook|github|clever|classlink|okta|school account|sso)\b/i;
function ssoLines(lines) { return (lines || []).filter((l) => /^\[\d+\]\s+(?:link|button)\b/.test(l) && SSO_RE.test(l)).slice(0, 3); }
function ssoNote(host, lines) {
  const b = ssoLines(lines);
  if (!b.length) return '';
  return 'No saved password is needed here: ' + host + ' signs in with another account (single sign-on): ' + b.map((l) => l.replace(/\s+->.*$/, '')).join('; ') +
    '. Click that button now (prefer the one Ben named, else Google). Ben\'s account is usually already signed in there; if it lists his account, pick it and continue.';
}

// diet: a web task gets only the tools a web task uses, with short descriptions, and a system prompt without the lines about the
// others (Motes, shell, tracking). Chosen once per task from Ben's words, so the prompt prefix stays byte-stable for the cache while
// the task runs. Ben's M3 log: system ~2.5k chars + tools ~5.9k chars + tool results 20-29k chars in one request.
const WEB_TOOLS = ['web_search', 'browser_go', 'browser_click', 'browser_type', 'browser_scroll', 'browser_back', 'browser_sign_in', 'ask_login', 'browser_read', 'memory_save', 'ask_user'];
const SHORT = {
  web_search: 'Search the web.', browser_go: 'Open a URL in your browser.', browser_click: 'Click element [id] of the newest page view.',
  browser_type: 'Type into field [id]; enter true presses Enter.', browser_scroll: 'Scroll the page.', browser_back: 'Go back a page.',
  browser_sign_in: "Sign in on this page with Ben's saved login (you never see it).", ask_login: "No saved login: open the app's private form for Ben (never ask in chat).", browser_read: 'Read the page text (dates, prices, lists).',
  memory_save: 'Save a lasting fact about Ben.', ask_user: 'Ask Ben one short question with 2-4 tap options.'
};
const WEBBY = /\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|edu|gov|io|co|us|uk|app|dev|test|me|info|ai)\b|https?:\/\/|\b(?:website|web ?site|site|portal|online|browser|internet|web|google|look (?:it )?up|search|find|check|price|cost|buy|order|cart|shop|sign ?in|log ?in|my (?:email|mail|bank|account|grades|school)|due|hours|phone number|news|recipe|form)\b/i;
const NOT_WEB = /\b(?:file|folder|terminal|shell|command|finder|desktop|app\b|screen|mote|remind|reminder|every day|every morning|schedule a|track)\b/i;
function isWebTask(text) { const t = String(text || ''); return WEBBY.test(t) && !NOT_WEB.test(t); }
function dietTools(defs) {
  const out = [];
  for (const n of WEB_TOOLS) {
    const d = (defs || []).find((x) => x && x.function && x.function.name === n);
    if (!d) continue;
    const f = JSON.parse(JSON.stringify(d.function));
    f.description = SHORT[n] || f.description;
    for (const v of Object.values((f.parameters && f.parameters.properties) || {})) if (v && v.description && v.description.length > 30) delete v.description;
    out.push({ type: 'function', function: f });
  }
  return out;
}
const OFF_TOPIC = /Motes|run_shell|"Keeping track of"|write yourself a reminder|open_app or screen_/;
function dietSystem(prompt) { return String(prompt || '').split('\n').filter((l) => !OFF_TOPIC.test(l)).join('\n'); }
// Older page views in the request (never in the stored chat): a page snapshot older than the newest `keepSnaps` tool results becomes
// its URL/title line (its [ids] are out of date anyway); a long read older than the newest `keepReads` is cut to its start.
const OLD_VIEW = ' [older page view: its [ids] are out of date]';
function dietHistory(msgs, taskFrom, keepSnaps, keepReads) {
  keepSnaps = keepSnaps === undefined ? 1 : keepSnaps; keepReads = keepReads === undefined ? 3 : keepReads;
  const idx = [];
  msgs.forEach((m, i) => { if (m && m.role === 'tool' && typeof m.content === 'string') idx.push(i); });
  const out = msgs.slice();
  idx.forEach((i, k) => {
    const age = idx.length - 1 - k, c = out[i].content;   // 0 = newest
    const before = i < taskFrom;
    if (/^URL: /.test(c) && (before || age >= keepSnaps)) {
      const tx = (c.match(/\nText: ([^\n]*)/) || [])[1] || '';
      out[i] = { ...out[i], content: c.split('\n')[0].slice(0, 200) + OLD_VIEW + (tx && !before ? '\nText: ' + tx.slice(0, 500) : '') };
    }
    else if (/^Page \d+ of \d+ \(/.test(c) && c.length > 1500 && (before || age >= keepReads)) out[i] = { ...out[i], content: c.slice(0, 1200) + '\n[rest of this older read left out]' };
    else if (before && c.length > 600) out[i] = { ...out[i], content: c.slice(0, 600) + '\n[older result cut]' };
  });
  return out;
}

// pins: a short "what Ben told you" block rebuilt every step from his own words in the chat (earlier turns, this task, corrections
// he sent while it worked), placed right before the model's turn. Ben on the M3: "I told you dresden.schoology.com".
// turns: [{ text, when: 'earlier'|'task'|'correction' }], oldest first. Empty when it would only repeat the task itself.
const PIN_MAX = 5, PIN_CHARS = 240;
const SITE_RE = /\b(?:https?:\/\/)?(?:[a-z0-9-]+\.)+(?:com|org|net|edu|gov|io|co|us|uk|app|dev|test|me|info|ai)\b(?:\/[^\s"')]*)?/gi;
function pinBlock(turns) {
  const t = (turns || []).filter((x) => x && String(x.text || '').trim()).slice(-PIN_MAX);
  const sites = [...new Set(t.flatMap((x) => String(x.text).match(SITE_RE) || []).map((x) => x.toLowerCase().replace(/^https?:\/\//, '').replace(/[/.,;:!?)]+$/, '')))].slice(0, 4);
  const siteLine = sites.length ? '\nWebsites Ben named (real sites: open them in your browser): ' + sites.join(', ') : '';
  if (!t.some((x) => x.when !== 'task')) return siteLine ? '[Glim app note, not a new message.' + siteLine + ']' : '';
  const q = (x) => { const v = String(x).replace(/\s+/g, ' ').trim(); return v.length > PIN_CHARS ? v.slice(0, PIN_CHARS - 1) + '…' : v; };
  return '[Glim app note, not a new message. What Ben told you, in his own words, oldest first. Use these facts instead of asking again; where they disagree, the newest wins:\n' +
    t.map((x) => '- ' + (x.when === 'correction' ? 'his correction while you worked' : x.when === 'task' ? 'this task' : 'earlier') + ': "' + q(x.text) + '"').join('\n') + siteLine + ']';
}

// stuck: (1) a reply that writes one line of intent and then only blank lines (the M1 UX test 2026-11-04: "Let me check what's on your
// screen." + ~2,000 newlines for 3 min; "I'll cancel the gym clothes reminder agent now." + newlines for 4 min; the bench: 139 s) is cut
// once the blank run starts; (2) a short reply that only says what it will do, with no tool call, at any step (the old guard ran only
// before the first tool of a turn, and only for some verbs). Either one goes back to the model with a plain note, at most STUCK_TRIES a task.
const STUCK_TRIES = 2;
const BLANK_RUN = /\S[\s\S]*?\s{40,}$/;
function blankRun(partial) { const t = String(partial || ''); return BLANK_RUN.test(t) || (t.length >= 200 && !t.trim()); }
const INTENT = /\b(?:I(?:'ll| will| am going to|'m going to)|let me|now I(?:'ll| will))\s+(?:now\s+|just\s+|quickly\s+|go ahead and\s+)?(?!know\b)[a-z]+/i;
const ASKS_BEN = /\?|\b(?:once|when|after|if) you\b|\blet me know\b|\bwould you like\b|\bshould I\b/i;
function onlyIntent(text) {
  const t = String(text || '').trim();
  if (!t || t.length > 300 || ASKS_BEN.test(t)) return false;
  const sentences = t.split(/(?<=[.!])\s+|\n+/).filter((x) => x.trim());
  return sentences.length <= 2 && INTENT.test(t);
}
const STUCK_NOTE = '[Self-check] Not done: your last reply only said what you will do, and nothing happened (no tool was called). Do that step now with a tool call, or, if you cannot, tell Ben in one short line why.';

module.exports = { FLAGS, DEFAULTS, on, clean, SSO_RE, ssoLines, ssoNote, WEB_TOOLS, isWebTask, dietTools, dietSystem, dietHistory, OLD_VIEW, pinBlock, STUCK_TRIES, blankRun, onlyIntent, STUCK_NOTE };
