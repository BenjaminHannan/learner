'use strict';
// Built-in gateway: a tiny OpenAI-compatible proxy in front of llama-server. The app talks to it exactly like it talks to the
// Premonition gateway on the Mac. It maps the model names fast / main / auto onto the one local model, passes streaming through,
// and writes the diary that sleep learns from:  <diaryDir>/YYYY-MM-DD.jsonl, one line {ts, model, messages:[{role, content}], response:{content}}.
// System prompts are never written to the diary; neither are warm-up requests (X-Premonition-Warm).
const http = require('http');
const fs = require('fs');
const path = require('path');

const MODEL_NAMES = ['fast', 'main', 'auto'];
const dayOf = (d) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');

const textOf = (c) => (typeof c === 'string' ? c : Array.isArray(c) ? c.filter((p) => p && p.type === 'text').map((p) => p.text || '').join('\n') : '');

// request messages -> diary messages (no system prompt, text only, no empty ones)
function diaryMessages(messages) {
  return (messages || []).filter((m) => m && m.role !== 'system').map((m) => ({ role: m.role, content: textOf(m.content) })).filter((m) => m.content !== '');
}
function diaryRecord({ ts, model, requestBody, content }) {
  return { ts: new Date(ts).toISOString(), model, messages: diaryMessages(requestBody && requestBody.messages), response: { content: content || '' } };
}
// the upstream request body: our model alias replaced by what llama-server wants (it ignores the name; "default" is conventional)
function mapRequest(body, upstreamModel) {
  return { ...body, model: upstreamModel || 'default' };
}
// accumulate assistant text from an SSE stream chunk by chunk
class SseText {
  constructor() { this.buf = ''; this.text = ''; }
  push(chunk) {
    this.buf += chunk;
    let i;
    while ((i = this.buf.indexOf('\n')) >= 0) {
      const line = this.buf.slice(0, i).trim(); this.buf = this.buf.slice(i + 1);
      if (!line.startsWith('data:')) continue;
      const d = line.slice(5).trim();
      if (!d || d === '[DONE]') continue;
      try { const j = JSON.parse(d); const c = j.choices && j.choices[0]; const t = c && c.delta && c.delta.content; if (typeof t === 'string') this.text += t; } catch (e) { /* partial */ }
    }
  }
}

function createGateway(o) {
  const upstream = o.upstream;                   // 'http://127.0.0.1:18090'
  const f = o.fetch || fetch;
  const now = o.now || (() => Date.now());
  const logDiary = (rec) => {
    if (!o.diaryDir || !rec.response.content || !rec.messages.length) return;
    try { fs.mkdirSync(o.diaryDir, { recursive: true }); fs.appendFileSync(path.join(o.diaryDir, dayOf(new Date(rec.ts)) + '.jsonl'), JSON.stringify(rec) + '\n'); } catch (e) { /* the diary never breaks chat */ }
  };
  const readBody = (req) => new Promise((resolve, reject) => { const b = []; req.on('data', (d) => b.push(d)); req.on('end', () => resolve(Buffer.concat(b).toString('utf8'))); req.on('error', reject); });

  async function handle(req, res) {
    const url = (req.url || '').split('?')[0].replace(/^\/v1/, '');
    try {
      if (req.method === 'GET' && (url === '/models' || url === '/health')) {
        let up = false;
        try { up = (await f(upstream + '/health')).ok; } catch (e) { /* down */ }
        if (!up) { res.writeHead(503, { 'content-type': 'application/json' }); return res.end(JSON.stringify({ error: { message: 'the local model is not running yet' } })); }
        res.writeHead(200, { 'content-type': 'application/json' });
        return res.end(JSON.stringify({ object: 'list', data: MODEL_NAMES.map((id) => ({ id, object: 'model', owned_by: 'premonition' })) }));
      }
      if (req.method === 'POST' && url === '/chat/completions') {
        const raw = await readBody(req);
        let body; try { body = JSON.parse(raw); } catch (e) { res.writeHead(400, { 'content-type': 'application/json' }); return res.end(JSON.stringify({ error: { message: 'bad JSON' } })); }
        const warm = req.headers['x-premonition-warm'] !== undefined;
        const ts = now();
        const ctl = new AbortController();
        res.on('close', () => { if (!res.writableEnded) { try { ctl.abort(); } catch (e) { /* ignore */ } } }); // the app pressed Stop (or went away): stop the model too
        const r = await f(upstream + '/v1/chat/completions', { signal: ctl.signal, method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(mapRequest(body, o.upstreamModel)) });
        const ct = r.headers.get('content-type') || 'application/json';
        res.writeHead(r.status, { 'content-type': ct, 'cache-control': 'no-cache' });
        if (body.stream && r.body) {
          const sse = new SseText(); const dec = new TextDecoder();
          const reader = r.body.getReader();
          for (;;) { const { value, done } = await reader.read(); if (done) break; res.write(value); sse.push(dec.decode(value, { stream: true })); }
          res.end();
          if (r.ok && !warm) logDiary(diaryRecord({ ts, model: body.model, requestBody: body, content: sse.text }));
        } else {
          const text = await r.text();
          res.end(text);
          if (r.ok && !warm) { let c = ''; try { c = JSON.parse(text).choices[0].message.content || ''; } catch (e) { /* not json */ } logDiary(diaryRecord({ ts, model: body.model, requestBody: body, content: c })); }
        }
        return;
      }
      res.writeHead(404, { 'content-type': 'application/json' }); res.end(JSON.stringify({ error: { message: 'not found' } }));
    } catch (e) {
      if (!res.headersSent) res.writeHead(502, { 'content-type': 'application/json' });
      try { res.end(JSON.stringify({ error: { message: 'local model unavailable: ' + (e && e.message || e) } })); } catch (e2) { /* closed */ }
    }
  }
  const server = http.createServer((req, res) => { handle(req, res); });
  return {
    server,
    listen: (port, host) => new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, host || '127.0.0.1', () => resolve(server.address().port)); }),
    close: () => new Promise((resolve) => { try { server.closeAllConnections && server.closeAllConnections(); server.close(() => resolve()); } catch (e) { resolve(); } })
  };
}

module.exports = { createGateway, diaryRecord, diaryMessages, mapRequest, SseText, MODEL_NAMES, dayOf };
