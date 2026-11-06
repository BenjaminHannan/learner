'use strict';
// Pass mark 3 (always-on v2): the always-on loop and the Motes reach the SAME model, through the SAME gateway, as Ben's chat.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const A = require('../src/alwayson');
const Platform = require('../renderer/platform');
const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');

test('the always-on ask uses chat\'s gateway URL and chat\'s Fast model id, never a hard-coded lfm3 id', () => {
  const ask = m.slice(m.indexOf('const aoAskDoor = AoAsk.makeAsk('), m.indexOf('function mainChatId('));   // CHAT-FIRST: the one streamed door
  assert.match(ask, /chatUrl\(s\.gatewayUrl\)/);
  assert.match(ask, /model: \(s\) => AlwaysOnMod\.chatModel\(s\)/);
  assert.match(ask, /async function aoAsk\(messages, signal, opts\) \{ return aoAskDoor\(/);
  assert.doesNotMatch(ask, /lfm3/);
  assert.doesNotMatch(fs.readFileSync(path.join(__dirname, '..', 'src', 'alwayson.js'), 'utf8').replace(/\/\/.*$/gm, ''), /'lfm3-fast'/);
});

test('chatModel = the id behind chat\'s Fast pill (the default pill), for every preset', () => {
  for (const p of Platform.PRESETS || []) assert.strictEqual(A.chatModel(p), p.modelFast, p.id);
  // Ben's Mac: the Premonition gateway on :8090, whose big upstream is Nanbeige4.2-3B (assistant/config.sh ASSISTANT_ENGINE="nanbeige")
  assert.strictEqual(A.chatModel({ gatewayUrl: 'http://127.0.0.1:8090/v1', model: 'qwen36-auto', modelFast: 'qwen36-fast' }), 'qwen36-fast');
  assert.strictEqual(A.chatModel({ model: 'default' }), 'default');
});

test('Motes (helpers) get chat\'s own settings: the same gatewayUrl and model, only mode/compaction/thinkActing change', () => {
  const g = m.slice(m.indexOf('getSettings: isHelper ?'), m.indexOf(': () => {', m.indexOf('getSettings: isHelper ?')));
  assert.match(g, /const s = store\.getSettings\(\); return \{ \.\.\.s, mode:/);
  assert.doesNotMatch(g, /model:|gatewayUrl:/);
});
