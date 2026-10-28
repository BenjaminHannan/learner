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
// LFM3 thinks by default, and on a laptop CPU that can cost 30 s+ before the answer: "fast" and "auto" turn thinking off,
// "main" keeps it. A chat_template_kwargs the app sent itself wins.
const NO_THINK = new Set(['fast', 'auto']);
function mapRequest(body, upstreamModel) {
  const out = { ...body, model: upstreamModel || 'default' };
  if (NO_THINK.has(body && body.model) && !(body.chat_template_kwargs && 'enable_thinking' in body.chat_template_kwargs)) {
    out.chat_template_kwargs = { ...(body.chat_template_kwargs || {}), enable_thinking: false };
  }
  return out;
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

// LFM3 often writes its reasoning and then "</think>" into the plain content even with thinking off (store test, Oct 27:
// 70 of 80 chats). Split it: everything up to the last "</think>" becomes reasoning_content, the rest stays the reply.
const THINK_END = '</think>';
function splitThink(text) {
  const i = (text || '').lastIndexOf(THINK_END);
  if (i < 0) return { reasoning: '', content: text || '' };
  return { reasoning: text.slice(0, i).replace(/^\s*<think>/, '').trim(), content: text.slice(i + THINK_END.length).replace(/^\s+/, '') };
}
// The same for a stream: content deltas are held back (and shown as reasoning_content, so the app's "thinking" line moves)
// until "</think>" appears, the stream ends, or HOLD_MAX chars pass with no "</think>" (then it was a plain reply).
const HOLD_MAX = 1200;
// Holding every reply would hide plain answers until the end, so decide from the opening: LFM3's stray reasoning reads
// like "The user wants…", "We need to…", "Okay, …". Anything else streams straight through (the app strips a late tag).
const DECIDE_AT = 24;
const LOOKS_LIKE_THINKING = /^\s*(<think>|the user|user (wants|asks|is)|we (need|have|should|must|are)|okay\b|ok,|alright|let me|let's|let us|i (need|should|will|think|must)|so,? (the|we)|hmm|first,|to answer)/i;
class SseThink {
  constructor() { this.buf = ''; this.held = ''; this.mode = 'hold'; this.last = null; }
  _line(obj) { return 'data: ' + JSON.stringify(obj) + '\n\n'; }
  _withDelta(j, delta) { const c = { ...j.choices[0], delta }; return { ...j, choices: [c] }; }
  // returns the SSE text to send for this chunk
  push(chunk) {
    this.buf += chunk; let out = ''; let i;
    while ((i = this.buf.indexOf('\n')) >= 0) {
      const raw = this.buf.slice(0, i + 1); this.buf = this.buf.slice(i + 1);
      const line = raw.trim();
      if (!line.startsWith('data:')) { out += raw; continue; }
      const d = line.slice(5).trim();
      if (d === '[DONE]') { out += this.flush() + raw; continue; }
      let j; try { j = JSON.parse(d); } catch (e) { out += raw; continue; }
      const c = j.choices && j.choices[0]; const t = c && c.delta && c.delta.content;
      if (this.mode !== 'hold' || typeof t !== 'string' || !t) { if (c && c.finish_reason) out += this.flush(j); out += raw; continue; }
      this.last = j; this.held += t;
      if (!this.held.includes(THINK_END) && this.held.length >= DECIDE_AT && !LOOKS_LIKE_THINKING.test(this.held)) { out += this.flush(j); continue; }
      const k = this.held.lastIndexOf(THINK_END);
      if (k >= 0) {
        const before = this.held.slice(0, k); const after = this.held.slice(k + THINK_END.length).replace(/^\s+/, '');
        const shown = this.shown || 0; const rest = before.slice(shown);
        this.mode = 'pass'; this.held = '';
        const { content, ...noContent } = c.delta;
        if (rest) out += this._line(this._withDelta(j, { ...noContent, reasoning_content: rest }));
        if (after) out += this._line(this._withDelta(j, { ...noContent, content: after }));
      } else if (this.held.length > HOLD_MAX) {
        out += this.flush(j);
      } else {
        // show it as thinking for now, minus a possible "</thi" tail
        const safe = this.held.length - (THINK_END.length - 1); const shown = this.shown || 0;
        if (safe > shown) { const { content, ...noContent } = c.delta; out += this._line(this._withDelta(j, { ...noContent, reasoning_content: this.held.slice(shown, safe) })); this.shown = safe; }
      }
    }
    return out;
  }
  // no "</think>" came: what was held is the reply after all
  flush(j) {
    if (this.mode !== 'hold' || !this.held) { this.mode = 'pass'; return ''; }
    const base = j || this.last; const text = this.held; this.held = ''; this.mode = 'pass';
    return base ? this._line(this._withDelta(base, { content: text })) : '';
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
          const think = new SseThink();
          for (;;) { const { value, done } = await reader.read(); if (done) break; const out = think.push(dec.decode(value, { stream: true })); if (out) { res.write(out); sse.push(out); } }
          const tail = think.push('\n') + think.flush(); if (tail) { res.write(tail); sse.push(tail); }
          res.end();
          if (r.ok && !warm) logDiary(diaryRecord({ ts, model: body.model, requestBody: body, content: splitThink(sse.text).content }));
        } else {
          let text = await r.text();
          try { const j = JSON.parse(text); const m = j.choices && j.choices[0] && j.choices[0].message; if (m && typeof m.content === 'string' && m.content.includes(THINK_END)) { const sp = splitThink(m.content); m.content = sp.content; m.reasoning_content = [m.reasoning_content, sp.reasoning].filter(Boolean).join('\n'); text = JSON.stringify(j); } } catch (e) { /* not json: pass through */ }
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

module.exports = { createGateway, splitThink, SseThink, diaryRecord, diaryMessages, mapRequest, SseText, MODEL_NAMES, dayOf };
