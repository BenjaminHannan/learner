'use strict';
// Ben Nov 4: "saying agent_list there is ugly". Plan text is the model's own words and may name a tool; wherever a plan is shown
// (the plan card, the side panel's Now tab) known tool ids become plain words. The list covers every tool in src/prompt.js
// TOOL_DEFS (checked by test/toolwords.test.js). The prompt also asks for plain-word plans; this is the safety net.
(function (root) {
  const WORDS = {
    agent_list: 'the Motes list', agent_start: 'a new Mote', agent_update: 'the Mote', ask_user: 'a quick question',
    browser_back: 'going back', browser_click: 'a click', browser_go: 'the browser', browser_read: 'reading the page',
    browser_scroll: 'scrolling', browser_sign_in: 'signing in', ask_login: 'a private sign-in form', browser_type: 'typing', diary_search: 'the diary', memory_forget: 'forgetting a note',
    memory_save: 'memory', open_app: 'opening the app', run_shell: 'the Terminal', screen_click: 'a click', screen_key: 'a key press',
    screen_look: 'a look at the screen', screen_type: 'typing', track_add: 'the tracking list', track_done: 'the tracking list',
    web_search: 'a web search'
  };
  const RE = new RegExp('`?\\b(' + Object.keys(WORDS).join('|') + ')\\b(?:\\(\\))?`?', 'g');
  const friendly = (s) => String(s == null ? '' : s).replace(RE, (_, id) => WORDS[id]).replace(/\*\*|__|`/g, '').replace(/\s{2,}/g, ' ').trim();
  // UI2 (Ben Nov 4, M3: "Use screen_look to see your Chrome windows" in the chat): reply text too. Only the tool ids change; markdown,
  // spacing and fenced code blocks stay as written.
  const inText = (s) => String(s == null ? '' : s).split(/(```[\s\S]*?(?:```|$))/).map((part, i) => (i % 2 ? part : part.replace(RE, (_, id) => WORDS[id]))).join('');
  const api = { WORDS, friendly, inText };
  root.ToolWords = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
