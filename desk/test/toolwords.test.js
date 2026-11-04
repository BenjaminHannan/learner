'use strict';
// Ben Nov 4: the plan card showed "Check existing Motes with agent_list." Tool ids become plain words wherever a plan is shown.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { WORDS, friendly } = require('../renderer/toolwords');
const { TOOL_DEFS, SYSTEM_PROMPT } = require('../src/prompt');
const read = (f) => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');

test('every tool in the registry has plain words', () => {
  const names = (Array.isArray(TOOL_DEFS) ? TOOL_DEFS : Object.values(TOOL_DEFS)).map((d) => (d.function || d).name).filter(Boolean);
  assert.ok(names.length >= 20, names.length + ' tools');
  for (const n of names) assert.ok(WORDS[n], n);
});

test("Ben's plan line reads in plain words; other words are untouched", () => {
  assert.strictEqual(friendly('Check existing Motes with agent_list.'), 'Check existing Motes with the Motes list.');
  assert.strictEqual(friendly('Save it with `memory_save()`'), 'Save it with memory');
  assert.strictEqual(friendly('Then ask Ben before creating any new Motes (agent_start).'), 'Then ask Ben before creating any new Motes (a new Mote).');
  assert.strictEqual(friendly('read my_notes_file and agent_lister'), 'read my_notes_file and agent_lister');
  for (const id of Object.keys(WORDS)) assert.ok(!/_/.test(friendly('use ' + id)), id);
});

test('the plan card and the Now tab use it; the card shows at most 5 steps; the prompt asks for plain-word plans', () => {
  const app = read('renderer/app.js');
  assert.match(app, /function planItem\(text\) \{\n    const t = window\.ToolWords \? ToolWords\.friendly\(text\)/);
  assert.match(app, /const PLAN_SHOW = 5;/); assert.match(app, /items = items\.slice\(0, PLAN_SHOW\);/);
  assert.match(read('renderer/side.js'), /ToolWords\.friendly\(p\)/);
  const html = read('renderer/index.html');
  assert.ok(html.indexOf('<script src="toolwords.js">') > 0 && html.indexOf('<script src="toolwords.js">') < html.indexOf('<script src="app.js">'));
  assert.match(SYSTEM_PROMPT, /never name a tool in that line/);   // UI2: one line then act, no plan list
});

test('UI2 inText: tool ids in visible reply text become plain words; markdown, spacing and code blocks kept; wired into the renderer', () => {
  const { inText } = require('../renderer/toolwords');
  assert.strictEqual(inText('1. Use screen_look to see your Chrome windows and active tab.'), '1. Use a look at the screen to see your Chrome windows and active tab.');
  assert.strictEqual(inText('I ran `web_search` and **found** it.\n\nDone.'), 'I ran a web search and **found** it.\n\nDone.');
  assert.strictEqual(inText('```\nrun_shell ls\n```\nthen browser_go'), '```\nrun_shell ls\n```\nthen the browser');
  assert.strictEqual(inText('a screen_looker and my_web_search_x'), 'a screen_looker and my_web_search_x');
  const app = require('fs').readFileSync(require('path').join(__dirname, '../renderer/app.js'), 'utf8');
  assert.match(app, /const answerOf = [^\n]*ToolWords\.inText\(Doing\.cleanReply\(/);
});
