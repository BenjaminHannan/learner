'use strict';
// CHAT-FIRST (2026-11-05): the one door every always-on request (tick, Mote, truth check, quiz) goes through to the brain.
// A1 chat hold: nothing starts while Ben's chat is running or within HOLD_MS after his last chat message (independent of benFirst).
// B1 streamed: every ask is `stream: true`, so an abort (chat start, typing) closes the connection and the server stops the request
// (a non-streamed request ran to the end on the server whatever the Desk did). The joined text is returned, as before.
const { streamText } = require('./motebatch');

const HOLD_MS = 120000;

// -> null (free) or why it is held ('chat' | 'chat-hold')
function chatHeld(o, now) {
  if (o.chatRunning && o.chatRunning()) return 'chat';
  const at = o.lastChatAt ? o.lastChatAt() : 0;
  if (at && now - at < HOLD_MS) return 'chat-hold';
  return null;
}

// o: { settings(), model(s), url(s), held() -> null | reason, fetch?, killMs? }
function makeAsk(o) {
  return async function ask(messages, signal, opts) {
    const why = o.held();
    if (why) throw Object.assign(new Error('held: ' + why), { gate: true, held: why });
    if (signal && signal.aborted) throw Object.assign(new Error('stopped'), { gate: true });
    const { buildChatBody } = require('./llm');
    const s = o.settings();
    const body = buildChatBody({ model: o.model(s), messages, stream: true, maxTokens: (opts && opts.maxTokens) || 220,
      temperature: opts && opts.temperature != null ? opts.temperature : 0.2, test: true });
    const headers = { 'content-type': 'application/json', 'x-test': '1' };
    if (s.apiKey) headers.authorization = 'Bearer ' + s.apiKey;
    const ctl = new AbortController(); const kill = setTimeout(() => ctl.abort(), o.killMs || 90000);
    const stop = () => ctl.abort(); if (signal) signal.addEventListener('abort', stop);
    try { return await streamText({ url: o.url(s), headers, body, signal: ctl.signal, fetch: o.fetch }); }
    finally { clearTimeout(kill); if (signal) signal.removeEventListener('abort', stop); }
  };
}

module.exports = { HOLD_MS, chatHeld, makeAsk };
