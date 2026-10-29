'use strict';
// A request-local window for the known small built-in context and endpoints that
// explicitly report a context overflow. Nothing here edits the stored transcript.
const Platform = require('../renderer/platform');
const caps = new Map();
const REPLY_RESERVE = 2048;
const keyOf = (url, model) => String(url || '').replace(/\/+$/, '') + '\n' + String(model || '');
function contextLimit(settings, model) {
  const preset = Platform.presetFor(settings.gatewayUrl);
  return caps.get(keyOf(settings.gatewayUrl, model)) || (settings.backendModelFamily === 'lfm3' || (preset && preset.id === 'builtin') ? 8192 : null);
}
// Only accept an explicit HTTP 400 identifying both actual tokens and capacity.
function contextOverflow(error) {
  const detail = error && error.details && error.details.error;
  if (!error || error.status !== 400 || !detail || detail.type !== 'exceed_context_size_error') return null;
  const requested = detail.n_prompt_tokens, limit = detail.n_ctx;
  if (!Number.isInteger(requested) || !Number.isInteger(limit) || requested <= limit || limit < 512 || limit > 1048576) return null;
  return { requested, limit };
}
function learnLimit(settings, model, limit) {
  const key = keyOf(settings.gatewayUrl, model);
  caps.delete(key); caps.set(key, limit);
  if (caps.size > 64) caps.delete(caps.keys().next().value);
}
function requestTokens(messages, tools) {
  // Approximate the complete serialized template, not just chat text. Count images
  // as a bounded token allowance rather than as base64 bytes.
  const json = JSON.stringify({ messages, tools }, (key, value) => key === 'image_url' && value ? '[image token allowance: ' + 'x'.repeat(2500) + ']' : value);
  return Math.ceil(Buffer.byteLength(json, 'utf8') / 2.5) + messages.length * 8 + 128;
}
function isTurn(m) {
  return m && m.role === 'user' && typeof m.content === 'string' && !m.content.startsWith('[Self-check]') && !m.content.startsWith('[older screenshot omitted]') && !m.content.startsWith('[screenshot');
}
function fitRequest(messages, tools, inputBudget, protectedIndex, retainedContext = []) {
  const out = messages.map((m) => ({ ...m }));
  const count = () => requestTokens(out, tools);
  let removed = 0;
  let protect = Math.max(1, protectedIndex || 1);
  while (count() > inputBudget) {
    const turns = [];
    for (let i = 1; i < out.length; i++) if (isTurn(out[i])) turns.push(i);
    if (turns.length < 2 || turns[0] >= protect) break;
    const start = turns[0], end = Math.min(turns[1], protect);
    if (end <= start) break;
    out.splice(start, end - start); protect -= end - start; removed++;
    // Summaries and the memory snapshot that rode in a removed turn remain
    // visible to the model; this only changes the ephemeral request copy.
    const firstUser = out.findIndex((m) => m.role === 'user' && typeof m.content === 'string');
    if (firstUser >= 0) for (const note of retainedContext) {
      if (note && !out.some((m) => typeof m.content === 'string' && m.content.includes(note))) out[firstUser] = { ...out[firstUser], content: note + '\n' + out[firstUser].content };
    }
  }
  if (count() > inputBudget) {
    const indices = [];
    for (let i = 1; i < out.length; i++) if (out[i].role === 'tool') indices.push(i);
    // The newest result is needed for the next action. Never drop call/result pairs.
    for (const i of indices.slice(0, -1)) {
      if (count() <= inputBudget) break;
      if (out[i].content !== '[older result omitted]') { out[i] = { ...out[i], content: '[older result omitted]' }; removed++; }
    }
  }
  return { messages: out, tokens: count(), removed };
}
module.exports = { contextLimit, contextOverflow, learnLimit, requestTokens, fitRequest, REPLY_RESERVE };
