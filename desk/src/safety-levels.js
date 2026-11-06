'use strict';
// Glim's safety levels (track I5, Ben 2026-11-04): every tool action maps to a category; each category is FREE, ASK first, or NEVER.
// The person running Glim sets them (Settings -> Safety, one row per category), or asks Glim in chat / by voice
// ("let Glim delete files without asking"): applied at once, one-line notice with Undo, no extra confirm.
//
// Injection guard: a level changes ONLY through set(..., {source}) with a source from BEN_SOURCES. main.js calls fromBenText() only
// with the text Ben typed in the main chat box or spoke on a call, never with web pages, files, emails, screen reading, tool results
// or another agent's words. There is no tool the model can call to change a level, and set() refuses any other source.
// Enforcement is in the tool runner (src/agent.js runTool), never only in the prompt.
const fs = require('fs');
const path = require('path');

const CATEGORIES = [
  { id: 'look', label: 'Look at the screen', def: 'free' },
  { id: 'read', label: 'Read files and web pages', def: 'free' },
  { id: 'search', label: 'Search the web', def: 'free' },
  { id: 'notes', label: 'Notes and memory', def: 'free' },
  { id: 'own-folder', label: 'Glim\'s own folder', def: 'free' },
  { id: 'open-apps', label: 'Open apps', def: 'free' },
  { id: 'browse', label: 'Use its own browser', def: 'free' },
  { id: 'hands', label: 'Use your mouse and keyboard (only when you are away)', def: 'ask' },
  { id: 'send', label: 'Send messages or email', def: 'ask' },
  { id: 'post', label: 'Post online', def: 'ask' },
  { id: 'delete', label: 'Delete files (always to the Trash)', def: 'ask' },
  { id: 'buy', label: 'Buy or pay', def: 'ask' },
  { id: 'install', label: 'Install apps', def: 'ask' },
  { id: 'system', label: 'Change system settings', def: 'ask' },
  // LOGIN1 (Ben 2026-11-04): Glim may sign in with logins Ben saved (Ben saving one is the consent). The app fills them; the model never
  // sees a password. Keychain / password-manager apps and dumping or exporting the keychain stay Never, fixed (the 'keychain' row).
  { id: 'passwords', label: 'Sign in with your saved logins', def: 'free' },
  { id: 'keychain', label: 'Keychain and password-manager apps', def: 'never', locked: true },
  { id: 'banking', label: 'Banking sites', def: 'never' },
  { id: 'glim-self', label: 'Edit Glim\'s own code, settings, logs or sleep checks', def: 'never' }
];
const LEVELS = ['free', 'ask', 'never'];
const BY_ID = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]));
const BEN_SOURCES = new Set(['ben-chat', 'ben-voice', 'settings', 'tap-card']);
// the hands' own knobs (Ben's rule; the judge can only make Glim wait longer, never shorter)
const HANDS_DEFAULTS = { idleMin: 2, askWaitS: 60, freeze: true, judge: false };

// ---- classification ---------------------------------------------------------------------------------------------------------------
const BANK = /(^|\.)((chase|wellsfargo|bankofamerica|bofa|citi|citibank|capitalone|usbank|pnc|tdbank|td|truist|ally|schwab|fidelity|vanguard|discover|americanexpress|amex|barclays|hsbc|santander|navyfederal|usaa|sofi|chime|wealthfront|robinhood|etrade|marcus|regions|keybank|huntington|citizensbank|firstrepublic|synchrony)\.com|[a-z-]*bank[a-z-]*\.(com|co\.uk|org)|[a-z-]*creditunion[a-z-]*\.(com|org)|[a-z-]*fcu\.(com|org))$/i;
const hostOf = (u) => { try { return new URL(/^[a-z]+:\/\//i.test(String(u)) ? String(u) : 'https://' + String(u)).hostname.toLowerCase(); } catch (e) { return ''; } };
const isBanking = (u) => { const h = hostOf(u); return !!h && BANK.test(h); };
// what a button / element label says it will do
function labelCategory(label) {
  const s = String(label || '').toLowerCase();
  if (!s) return null;
  if (/\b(place (your )?order|buy( now)?|purchase|checkout|check out|pay( now)?|subscribe|add payment|confirm (payment|purchase))\b/.test(s)) return 'buy';
  if (/\b(send|reply all|reply|forward)\b/.test(s)) return 'send';
  if (/\b(post|tweet|publish|share|upload|submit|comment)\b/.test(s)) return 'post';
  if (/\b(delete|remove|move to trash|empty trash|erase)\b/.test(s)) return 'delete';
  if (/\b(install|get app|download and install)\b/.test(s)) return 'install';
  return null;
}
const APP_CATS = [
  ['keychain', /^(keychain access|passwords|1password|bitwarden|lastpass|dashlane)(\.app)?$/i],
  ['system', /^(system settings|system preferences|disk utility|terminal|activity monitor)(\.app)?$/i],
  ['install', /^(app store)(\.app)?$/i]
];
const appCategory = (name) => { for (const [c, re] of APP_CATS) if (re.test(String(name || '').trim())) return c; return null; };
// shell: the strictest category the command touches (null = an ordinary command: the old shell gate decides)
const PERMANENT_DELETE = /(^|[;&|]\s*|\s)(sudo\s+)?(rm|rmdir|unlink|srm|shred)\s|\bfind\b[^;|&]*\s-delete\b|\bgit\s+clean\b/;
function shellCategory(cmd, o) {
  const c = String(cmd || '');
  const self = (o && o.selfPaths || []).filter(Boolean);
  const touchesSelf = self.some((p) => c.includes(p) || c.includes(p.replace(process.env.HOME || '\0', '~')));
  if (/\bsecurity\s+(find|dump|add|delete|unlock|export|set)-|\bkeychain\b|\.keychain(-db)?\b/i.test(c)) return 'keychain';
  if (touchesSelf && /(\brm\b|\bmv\b|\bcp\b|>|\bsed\s+-i|\btee\b|\bchmod\b|\btruncate\b|\btouch\b|\bln\b|\bperl\s+-[a-z]*i|\bpython\d?\b|\bnode\b|\bgit\b|\bdd\b)/.test(c)) return 'glim-self';
  if (/\b(curl|wget)\b[^|;]*\bhttps?:\/\/[^\s'"]*(\.|\/)?(chase|wellsfargo|bankofamerica|capitalone|usbank)\b/i.test(c)) return 'banking';
  if (/\bsudo\b|\bdefaults\s+write\b|\b(systemsetup|networksetup|pmset|scutil|launchctl|csrutil|spctl|tmutil|dscl|nvram|kextload|kmutil|profiles)\b/.test(c)) return 'system';
  if (/\b(brew|port|mas)\s+(install|reinstall|upgrade)\b|\bpip3?\s+install\b|\bnpm\s+(i|install)\s+(-g|--global)\b|\bgem\s+install\b|\bsoftwareupdate\b|\binstaller\s+-pkg\b|\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z)?sh\b/.test(c)) return 'install';
  if (/\bosascript\b[^\n]*(messages|mail)[^\n]*\bsend\b|\bsendmail\b|\bmail\s+-s\b/i.test(c)) return 'send';
  if (/\b(curl|wget)\b[^|;]*(\s-X\s*(POST|PUT|PATCH|DELETE)\b|\s(-d|--data[-\w]*|-F|--form|--post-data)\b)/.test(c)) return 'post';
  if (PERMANENT_DELETE.test(c) || /\bmv\b[^;|&]*\.Trash\b|\btrash\s/.test(c)) return 'delete';
  return null;
}
const TRASH_ONLY = 'Error: deleting never removes files for good. Move them to the Trash instead: mv <file> ~/.Trash/ (no rm, rmdir, unlink, shred, find -delete, git clean).';

// tool call -> {cat, why} (cat null = not covered: the old gates decide). ctx: {selfPaths, labelOf(id) -> text, pageUrl, frontApp}
function classify(name, args, ctx) {
  args = args || {}; ctx = ctx || {};
  const lab = (id) => { try { return ctx.labelOf ? ctx.labelOf(name, id) : ''; } catch (e) { return ''; } };
  switch (name) {
    case 'screen_look': return { cat: 'look' };
    case 'web_search': return { cat: 'search' };
    case 'browser_read': case 'diary_search': return { cat: isBanking(ctx.pageUrl) ? 'banking' : 'read' };
    case 'memory_save': case 'memory_forget': case 'track_add': case 'track_done': return { cat: 'notes' };
    case 'browser_go': return { cat: isBanking(args.url) ? 'banking' : 'browse' };
    case 'browser_sign_in': return { cat: isBanking(ctx.pageUrl) ? 'banking' : 'passwords' };
    case 'ask_login': return { cat: null };   // SECURE-LOGIN (Ben 2026-11-05): the private form opens with no "may I?" at any level   // LOGIN1: a bank keeps its own level
    case 'browser_back': case 'browser_scroll': return { cat: isBanking(ctx.pageUrl) ? 'banking' : 'browse' };
    case 'browser_click': case 'browser_type': {
      if (isBanking(ctx.pageUrl)) return { cat: 'banking' };
      const l = lab(args.id); return { cat: (name === 'browser_click' && labelCategory(l)) || 'browse', why: l };
    }
    case 'open_app': return { cat: appCategory(args.name) || 'open-apps' };
    case 'screen_click': case 'screen_type': case 'screen_key': {
      const front = appCategory(ctx.frontApp);
      if (front === 'keychain') return { cat: 'keychain' };
      let c = 'hands';
      const l = name === 'screen_click' && args.id != null ? lab(args.id) : '';
      const lc = labelCategory(l);
      if (name === 'screen_key' && /cmd\+(delete|backspace)/i.test(String(args.keys || ''))) return { cat: 'delete', hands: true };
      if (lc) return { cat: lc, hands: true, why: l };
      if (front === 'system') return { cat: 'system', hands: true };
      return { cat: c };
    }
    case 'run_shell': { const c = shellCategory(args.command, ctx); return { cat: c, permanentDelete: c === 'delete' && PERMANENT_DELETE.test(String(args.command || '')) }; }
    default: return { cat: null };
  }
}

// ---- the levels store ------------------------------------------------------------------------------------------------------------
class SafetyLevels {
  // o: {dir (userData; omit = in memory), now, onChange(levels)}
  constructor(o) {
    o = o || {}; this.o = o; this.now = o.now || Date.now;
    this.file = o.dir ? path.join(o.dir, 'safety-levels.json') : null;
    this.st = { levels: {}, hands: { ...HANDS_DEFAULTS }, history: [] };
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && typeof j === 'object') this.st = { levels: j.levels || {}, hands: { ...HANDS_DEFAULTS, ...(j.hands || {}) }, history: j.history || [] }; } catch (e) { /* defaults */ } }
    this.undos = new Map();
  }
  save() { if (!this.file) return; try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); const t = this.file + '.tmp'; fs.writeFileSync(t, JSON.stringify(this.st, null, 1)); fs.renameSync(t, this.file); } catch (e) { /* in memory */ } }
  level(cat) { if (BY_ID[cat] && BY_ID[cat].locked) return BY_ID[cat].def; const v = this.st.levels[cat]; return LEVELS.includes(v) ? v : (BY_ID[cat] ? BY_ID[cat].def : 'ask'); }
  levels() { return CATEGORIES.map((c) => ({ id: c.id, label: c.label, level: this.level(c.id), def: c.def, locked: !!c.locked })); }
  hands() { return { ...this.st.hands, idleMin: Math.max(HANDS_DEFAULTS.idleMin, Number(this.st.hands.idleMin) || HANDS_DEFAULTS.idleMin), askWaitS: Math.max(10, Number(this.st.hands.askWaitS) || HANDS_DEFAULTS.askWaitS) }; }
  // changes = [{cat, level}]; o.source must be one of BEN_SOURCES. -> {ok, notice, undo} (undo = a token for undo())
  set(changes, o) {
    const source = o && o.source;
    if (!BEN_SOURCES.has(source)) return { ok: false, error: 'Only you can change a safety level (from the chat, your voice, or Settings).' };
    changes = (Array.isArray(changes) ? changes : [changes]).filter((c) => c && BY_ID[c.cat] && !BY_ID[c.cat].locked && LEVELS.includes(c.level));
    if (!changes.length) return { ok: false, error: 'Nothing to change.' };
    const before = {}; for (const c of changes) before[c.cat] = this.st.levels[c.cat];
    for (const c of changes) this.st.levels[c.cat] = c.level;
    const token = 'u' + this.now().toString(36) + Math.random().toString(36).slice(2, 6);
    this.undos.set(token, before); if (this.undos.size > 20) this.undos.delete(this.undos.keys().next().value);
    this.st.history.push({ t: this.now(), source, changes }); if (this.st.history.length > 200) this.st.history.splice(0, this.st.history.length - 200);
    this.save(); try { if (this.o.onChange) this.o.onChange(this.levels()); } catch (e) { /* ui only */ }
    return { ok: true, notice: noticeOf(changes), undo: token, changes };
  }
  undo(token, o) {
    if (!BEN_SOURCES.has(o && o.source)) return { ok: false };
    const before = this.undos.get(token); if (!before) return { ok: false };
    this.undos.delete(token);
    for (const [cat, v] of Object.entries(before)) { if (v === undefined) delete this.st.levels[cat]; else this.st.levels[cat] = v; }
    this.st.history.push({ t: this.now(), source: o.source, undo: Object.keys(before) });
    this.save(); try { if (this.o.onChange) this.o.onChange(this.levels()); } catch (e) { /* ui only */ }
    return { ok: true, notice: 'Undone.' };
  }
  setHands(patch, o) {
    if (!BEN_SOURCES.has(o && o.source)) return { ok: false };
    const p = patch || {};
    if (p.idleMin != null) this.st.hands.idleMin = Math.max(HANDS_DEFAULTS.idleMin, Math.min(120, Number(p.idleMin) || HANDS_DEFAULTS.idleMin));   // never below Ben's 2 min
    if (p.askWaitS != null) this.st.hands.askWaitS = Math.max(10, Math.min(3600, Number(p.askWaitS) || HANDS_DEFAULTS.askWaitS));
    if (p.judge != null) this.st.hands.judge = !!p.judge;
    if (p.freeze != null) this.st.hands.freeze = !!p.freeze;
    this.save(); return { ok: true };
  }
  // the decision for one tool call: {cat, level, label, refuse?, need?}
  check(name, args, ctx) {
    const c = classify(name, args, ctx);
    if (!c.cat) return { cat: null, level: null };
    let level = this.level(c.cat);
    if (c.hands && c.cat !== 'hands' && this.level('hands') === 'never') level = 'never';   // a labelled click is still the real mouse
    const label = BY_ID[c.cat].label;
    const out = { cat: c.cat, level, label, why: c.why, hands: c.cat === 'hands' || !!c.hands };
    if (level === 'never') out.refuse = 'Not allowed: "' + label + '" is set to Never. Do not try another way. If it matters, tell Ben: he can change it in Settings > Safety or just ask.';
    else if (c.permanentDelete) out.refuse = TRASH_ONLY;
    return out;
  }
}
function noticeOf(changes) {
  const say = { free: 'without asking', ask: 'only after asking you', never: 'never' };
  return changes.map((c) => c.level === 'never' ? 'Glim will never ' + verbOf(c.cat) + '.' : 'Glim can now ' + verbOf(c.cat) + ' ' + say[c.level] + '.').join(' ');
}
const VERBS = { look: 'look at the screen', read: 'read files and pages', search: 'search the web', notes: 'keep notes', 'own-folder': 'use its own folder', 'open-apps': 'open apps', browse: 'use its own browser', hands: 'use your mouse and keyboard', send: 'send messages or email', post: 'post online', delete: 'delete files (to the Trash)', buy: 'buy or pay', install: 'install apps', system: 'change system settings', passwords: 'sign in with your saved logins', keychain: 'open the keychain or password apps', banking: 'open banking sites', 'glim-self': 'edit its own code, settings or logs' };
const verbOf = (cat) => VERBS[cat] || cat;

// ---- Ben's words -> level changes (deterministic; only ever called with Ben's own chat / voice text) ------------------------------------
const CAT_WORDS = [
  ['delete', /\b(delet\w*|remov\w* files?|trash\w*|throw\w* away)\b/],
  ['send', /\b(send\w*|email\w*|e-mail\w*|messag\w*|text\w* (people|someone|my friends)|imessage)\b/],
  ['post', /\b(post\w*|tweet\w*|publish\w*)\b/],
  ['buy', /\b(buy\w*|purchas\w*|pay\w*|order\w* (things|stuff)|spend\w* money|check\w* out)\b/],
  ['install', /\b(install\w*)\b/],
  ['system', /\b(system settings?|system preferences|mac settings|change (my )?settings)\b/],
  ['passwords', /\b(password\w*|saved logins?|logins?|sign(?:ing)? (?:me )?in|log(?:ging)? (?:me )?in)\b/],
  ['banking', /\b(bank\w*)\b/],
  ['hands', /\b(mouse|keyboard|click\w*|typ(e|ing) for me|control (my|the) (computer|mac)|use (my|the) (computer|mac))\b/],
  ['open-apps', /\b(open\w* apps?)\b/],
  ['look', /\b(look\w* at (my |the )?screen|see (my |the )?screen)\b/],
  ['search', /\b(search\w* the web|web search\w*)\b/],
  ['glim-self', /\b(your own code|edit (yourself|your code)|your (settings|logs))\b/]
];
// -> [{cat, level}] or []
function fromBenText(text) {
  const s = String(text || '').toLowerCase().replace(/[’']/g, '\'').replace(/\s+/g, ' ').trim();
  if (!s || s.length > 280 || /https?:\/\/|```|^>/.test(s)) return [];   // a pasted page or quote is not an instruction about levels
  if (/\?\s*$/.test(s) && !/^(can you|could you|please)/.test(s)) return [];   // a question about levels changes nothing
  let level = null;
  if (/\b(without asking|without checking|no need to ask|never ask|don't (need to |have to )?ask|do not (need to |have to )?ask|stop asking|always allow|you can (always )?(just )?\w+ (freely|anytime))\b/.test(s)) level = 'free';
  else if (/\b(ask (me )?(first|before)|always ask|check with me( first)?|ask permission|ask me)\b/.test(s)) level = 'ask';
  else if (/\b(never (let|allow)|don't (ever )?(let|allow)|do not (ever )?(let|allow)|stop (letting|allowing)|block|forbid|never)\b/.test(s)) level = 'never';
  if (!level) return [];
  if (!/\b(glim|you|your)\b/.test(s) && !/^(let|allow|never|always|stop|don't|do not|ask|block)\b/.test(s)) return [];
  const out = [];
  for (const [cat, re] of CAT_WORDS) if (re.test(s)) out.push({ cat, level });
  // "password" also matches banking text like "bank password": keep both; "send" inside "post or send" both apply
  return out;
}

module.exports = { SafetyLevels, CATEGORIES, LEVELS, BEN_SOURCES, HANDS_DEFAULTS, classify, shellCategory, labelCategory, appCategory, isBanking, fromBenText, noticeOf, TRASH_ONLY, PERMANENT_DELETE };
