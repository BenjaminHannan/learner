'use strict';
// Streaming client for an OpenAI-compatible /chat/completions endpoint.

function extractFallbackCalls(content) {
  const calls = [];
  let rest = content || '';
  let n = 0;
  const mk = (name, args) => calls.push({ id: 'fb_' + Date.now().toString(36) + '_' + (n++), name, arguments: typeof args === 'string' ? args : JSON.stringify(args || {}) });

  // <tool_call>{"name":..., "arguments":{...}}</tool_call>   (closing tag optional at end of text)
  rest = rest.replace(/<tool_call>\s*([\s\S]*?)\s*(?:<\/tool_call>|$)/g, (all, body) => {
    const b = body.trim();
    try {
      const j = JSON.parse(b);
      const name = j.name || (j.function && j.function.name);
      const args = j.arguments !== undefined ? j.arguments : (j.parameters !== undefined ? j.parameters : (j.function && j.function.arguments));
      if (name) { mk(name, args); return ''; }
    } catch (e) { /* maybe the body is the XML form */ }
    if (/<function=/.test(b)) return all; // handled by the next pass
    return all;
  });

  // <function=name><parameter=k>v</parameter>...</function>
  rest = rest.replace(/<function=([\w.\-]+)>([\s\S]*?)(?:<\/function>|$)/g, (all, name, body) => {
    const args = {};
    const re = /<parameter=([\w.\-]+)>([\s\S]*?)(?:<\/parameter>|(?=<parameter=)|$)/g;
    let m;
    while ((m = re.exec(body))) {
      let v = m[2].replace(/^\n/, '').replace(/\n$/, '');
      if (/^(true|false)$/.test(v)) v = v === 'true';
      else if (/^-?\d+(\.\d+)?$/.test(v)) v = Number(v);
      args[m[1]] = v;
    }
    mk(name, args);
    return '';
  });
  // stray wrappers left from the XML form
  rest = rest.replace(/<\/?tool_call>/g, '');
  return { calls, content: calls.length ? rest.trim() : content };
}

// The ONE place a chat request body is built, for real requests and for the warm-up request, so the
// system prompt, tools, tool_choice and everything else that shapes the chat template are identical.
function buildChatBody({ model, messages, tools, stream, maxTokens }) {
  const body = { model, messages, stream: !!stream };
  if (tools && tools.length) { body.tools = tools; body.tool_choice = 'auto'; }
  if (maxTokens) body.max_tokens = maxTokens;
  return body;
}
const chatUrl = (gatewayUrl) => String(gatewayUrl).replace(/\/+$/, '') + '/chat/completions';

async function streamChat(opts) {
  const { gatewayUrl, model, messages, tools, signal, onText, onReasoning, apiKey, maxTokens } = opts;
  const url = chatUrl(gatewayUrl);
  const body = buildChatBody({ model, messages, tools, stream: true, maxTokens });
  const headers = { 'content-type': 'application/json', accept: 'text/event-stream' };
  if (apiKey) headers.authorization = 'Bearer ' + apiKey;
  const tStart = Date.now();
  let firstTokenMs = null;
  const firstToken = () => { if (firstTokenMs === null) firstTokenMs = Date.now() - tStart; };
  const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body), signal });
  if (!res.ok) {
    let t = '';
    try { t = (await res.text()).slice(0, 400); } catch (e) { /* ignore */ }
    throw new Error('Gateway error ' + res.status + (t ? ': ' + t : ''));
  }
  let content = '';
  let reasoning = '';
  let finishReason = null;
  const tc = []; // by index
  const dec = new TextDecoder();
  let buf = '';

  const handle = (line) => {
    line = line.trim();
    if (!line.startsWith('data:')) return;
    const data = line.slice(5).trim();
    if (!data || data === '[DONE]') return;
    let j;
    try { j = JSON.parse(data); } catch (e) { return; }
    if (j.error) throw new Error('Gateway error: ' + (j.error.message || JSON.stringify(j.error)));
    const ch = j.choices && j.choices[0];
    if (!ch) return;
    if (ch.finish_reason) finishReason = ch.finish_reason;
    const d = ch.delta || {};
    if (d.content || d.reasoning_content || d.reasoning || (Array.isArray(d.tool_calls) && d.tool_calls.length)) firstToken();
    if (d.content) { content += d.content; if (onText) onText(d.content); }
    const r = d.reasoning_content || d.reasoning;
    if (r) { reasoning += r; if (onReasoning) onReasoning(r); }
    if (Array.isArray(d.tool_calls)) {
      for (const t of d.tool_calls) {
        // Some servers omit `index`: a chunk with a new id (or the very first chunk) starts a new call, otherwise it continues the last one.
        let i = t.index;
        if (i === undefined) {
          const last = tc.length - 1;
          i = (last < 0 || (t.id && tc[last] && tc[last].id && tc[last].id !== t.id)) ? tc.length : last;
        }
        const cur = tc[i] || (tc[i] = { id: '', name: '', arguments: '' });
        if (t.id) cur.id = t.id;
        if (t.function) {
          if (t.function.name) cur.name += t.function.name;
          if (t.function.arguments) cur.arguments += t.function.arguments;
        }
      }
    }
  };

  if (/application\/json/i.test(res.headers.get('content-type') || '')) {
    // Server ignored stream:true and sent one JSON body.
    let j = null;
    try { j = JSON.parse(await res.text()); } catch (e) { /* fall through to empty result */ }
    if (j && j.error) throw new Error('Gateway error: ' + (j.error.message || JSON.stringify(j.error)));
    const m = j && j.choices && j.choices[0] && j.choices[0].message;
    if (m) {
      handle('data: ' + JSON.stringify({ choices: [{ finish_reason: j.choices[0].finish_reason, delta: {
        content: m.content, reasoning_content: m.reasoning_content,
        tool_calls: (m.tool_calls || []).map((t, k) => ({ index: k, id: t.id, function: { name: t.function && t.function.name, arguments: t.function && (typeof t.function.arguments === 'string' ? t.function.arguments : JSON.stringify(t.function.arguments || {})) } }))
      } }] }));
    }
  }
  const reader = (res.bodyUsed || !res.body) ? { read: async () => ({ done: true }) } : res.body.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, idx);
      buf = buf.slice(idx + 1);
      handle(line);
    }
  }
  if (buf) handle(buf);

  // LFM3 can leave its reasoning and a "</think>" in the reply itself (the built-in gateway catches most of it live)
  const te = content.lastIndexOf('</think>');
  if (te >= 0) { reasoning = [reasoning, content.slice(0, te).replace(/^\s*<think>/, '').trim()].filter(Boolean).join('\n'); content = content.slice(te + 8).replace(/^\s+/, ''); }
  let toolCalls = tc.filter(Boolean).filter((t) => t.name).map((t, i) => ({ id: t.id || 'call_' + Date.now().toString(36) + '_' + i, name: t.name, arguments: t.arguments || '{}' }));
  if (!toolCalls.length && content && /<tool_call>|<function=/.test(content)) {
    const fb = extractFallbackCalls(content);
    if (fb.calls.length) { toolCalls = fb.calls; content = fb.content; }
  }
  return { content, reasoning, toolCalls, finishReason, firstTokenMs: firstTokenMs === null ? Date.now() - tStart : firstTokenMs };
}

module.exports = { streamChat, extractFallbackCalls, buildChatBody, chatUrl };
