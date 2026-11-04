'use strict';
// Track E1 (2026-11-04): real batching of Mote tries. Stock mlx_lm.server (0.32) batches requests that arrive together
// (continuous batching: a BatchGenerator decodes them side by side), so K tries sent at the SAME time cost far less than K sent one
// after another. This module turns MotePool's askBatch(listOfMessages, signal, opts) into K concurrent STREAMED requests.
//
// Why streamed: mlx_lm.server notices a hung-up client only when it writes to it. A non-streamed request keeps generating to the
// end after the app gives up on it; a streamed one is dropped from the batch at its next token. So "a batch stops when Ben types"
// (MotePool.stopAll -> the shared AbortController) really frees the model for his chat.
//
// benFirst: one AbortController (the pool's) covers every request of the batch; gateOk() is checked right before sending; any
// failure of one try leaves '' in its slot (the checker sees an unreadable try), an abort rejects the whole batch.
const { SseText } = require('./gateway');

// one streamed chat request -> the reply text. o: { fetch, url, headers, body, signal }
async function streamText(o) {
  const f = o.fetch || fetch;
  const r = await f(o.url, { method: 'POST', headers: o.headers, body: JSON.stringify({ ...o.body, stream: true }), signal: o.signal });
  if (!r.ok) throw new Error('gateway ' + r.status);
  const sse = new SseText();
  if (r.body && r.body.getReader) {
    const reader = r.body.getReader(); const dec = new TextDecoder();
    for (;;) { const { value, done } = await reader.read(); if (done) break; sse.push(dec.decode(value, { stream: true })); }
    sse.push('\n');
  } else { sse.push(await r.text()); sse.push('\n'); }
  return sse.text;
}

// o: { askOne(messages, signal, opts) -> Promise<text>, enabled() -> bool, maxConcurrent (default 8) }
// -> askBatch(listOfMessages, signal, opts) or null when batching is switched off (MotePool then runs tries back-to-back)
function makeAskBatch(o) {
  return async function askBatch(list, signal, opts) {
    if (signal && signal.aborted) throw Object.assign(new Error('gate'), { gate: true });
    const n = Math.min(list.length, o.maxConcurrent || 8);
    const tries = !!(opts && opts.tries);
    const out = await Promise.all(list.slice(0, n).map((m, i) => o.askOne(m, signal, tries ? { temperature: i === 0 ? 0.2 : 0.8, tryIndex: i } : {})
      .catch((e) => { if (signal && signal.aborted) throw e; return ''; })));
    if (signal && signal.aborted) throw Object.assign(new Error('stopped'), { gate: true });
    return out;
  };
}

module.exports = { streamText, makeAskBatch };
