'use strict';
// Constant system prompt + tool schemas. Nothing per-chat or per-time goes in here (speed rule).

const SYSTEM_PROMPT = [
  "You are Premonition, Ben's local assistant on his Mac. You act for him with tools instead of just talking.",
  "",
  "Rules:",
  "- Work autonomously: pick a tool, look at the result, continue until the job is done.",
  "- For jobs with several steps, first write a brief numbered plan (3-6 short lines), then start.",
  "- Use web_search and the browser_* tools for anything on the web. Use screen_* tools and open_app only for Mac apps.",
  "- Snapshots list elements as [id]; use those ids. Ids reset after every action, so use the newest snapshot.",
  "- Call ask_user BEFORE sending any message or email, buying, paying, deleting anything, or when you are stuck or unsure what Ben wants.",
  "- Delegate long or repeating jobs to helpers with agent_start; check on them with agent_list.",
  "- Use run_shell for files and system questions. Keep commands small and safe.",
  "- Each user message starts with a [date] line; trust it for today's date.",
  "- Keep the final answer short and plain: what you did and what Ben needs to know.",
  "Voice: warm, a little playful and curious, plainspoken, brief. An occasional light \"I had a feeling...\" is fine, never at the cost of clarity.",
  "No emoji spam, and never cutesy when Ben is stressed or the task is serious."
].join('\n');

const obj = (properties, required) => ({ type: 'object', properties, required: required || [] });
const S = (d) => ({ type: 'string', description: d });
const fn = (name, description, parameters) => ({ type: 'function', function: { name, description, parameters } });

const TOOL_DEFS = {
  web_search: fn('web_search', 'Search the web (top 8 results).', obj({ query: S('search terms') }, ['query'])),
  browser_go: fn('browser_go', 'Open a URL in the browser; returns a snapshot.', obj({ url: S('full URL') }, ['url'])),
  browser_click: fn('browser_click', 'Click element [id] from the latest snapshot.', obj({ id: { type: 'integer' } }, ['id'])),
  browser_type: fn('browser_type', 'Replace the text of input [id]; optionally press Enter.', obj({ id: { type: 'integer' }, text: S('text to type'), enter: { type: 'boolean' } }, ['id', 'text'])),
  browser_scroll: fn('browser_scroll', 'Scroll one screen.', obj({ direction: { type: 'string', enum: ['up', 'down'] } }, ['direction'])),
  browser_back: fn('browser_back', 'Go back in browser history.', obj({})),
  browser_read: fn('browser_read', 'Read the main text of the current page.', obj({ page: { type: 'integer', description: 'page number, default 1' } })),
  screen_look: fn('screen_look', 'List windows and numbered UI elements of a Mac app.', obj({ app: S('app name; default front app') })),
  screen_click: fn('screen_click', 'Click UI element [id] from screen_look, or a point.', obj({ id: { type: 'integer' }, x: { type: 'number' }, y: { type: 'number' }, double: { type: 'boolean' } })),
  screen_type: fn('screen_type', 'Type text into the focused Mac control.', obj({ text: S('text') }, ['text'])),
  screen_key: fn('screen_key', 'Press keys, e.g. "cmd+t" or "return".', obj({ keys: S('key combo') }, ['keys'])),
  open_app: fn('open_app', 'Launch or focus a Mac app.', obj({ name: S('app name') }, ['name'])),
  run_shell: fn('run_shell', 'Run a zsh command in the home folder (60 s limit).', obj({ command: S('shell command') }, ['command'])),
  diary_search: fn('diary_search', 'Search past chats and notes.', obj({ query: S('search terms') }, ['query'])),
  agent_start: fn('agent_start', 'Start a helper agent. Recurring: use at ("08:00") alone for a daily time, or every ("30m","2h") alone for an interval.', obj({ name: S('short name'), task: S('what to do'), every: S('interval'), at: S('daily time') }, ['name', 'task'])),
  agent_list: fn('agent_list', 'List helpers: status, schedule, next run, last result.', obj({})),
  agent_stop: fn('agent_stop', 'Stop a helper and cancel its schedule.', obj({ name_or_id: S('helper name or id') }, ['name_or_id'])),
  ask_user: fn('ask_user', 'Pause and ask Ben a question; his reply is the result.', obj({ question: S('question for Ben') }, ['question']))
};

const ORDER = Object.keys(TOOL_DEFS);

// Decided once per app run: diary tool is included only when the diary is available.
function buildTools(opts) {
  const diary = !!(opts && opts.diary);
  return ORDER.filter((n) => diary || n !== 'diary_search').map((n) => TOOL_DEFS[n]);
}

function promptSize(tools) {
  return SYSTEM_PROMPT.length + JSON.stringify(tools || buildTools({ diary: true })).length;
}

module.exports = { SYSTEM_PROMPT, TOOL_DEFS, buildTools, promptSize };
